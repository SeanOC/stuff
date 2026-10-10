"""Reproducible offline fixture generator and measurement runner.

Run from build123d: uv run --group capture python -m capture.synth --output DIR
CAD and Shapely are generation/evaluation dependencies only. Generation never
runs during pytest. All detector inputs are RGB pixels, not fixture metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

import cv2
import numpy as np

from scripts.thumbnail import _camera_basis
from . import detect_grid, rectify, segment, footprint
from .footprint import _region, ARUCO_POSITIONS, DetectionError


def render_topdown(mesh, mm_per_px, light, *, bounds=None):
    """Fixed-scale, z-buffered, Gouraud-shaded orthographic RGBA (uint8).

    bounds = (xmin,ymin,xmax,ymax), in world XY mm; row zero faces +Y.
    Uses only thumbnail's camera basis, never its auto-fit renderer.
    """
    if mm_per_px <= 0 or not np.isfinite(mm_per_px):
        raise ValueError('mm_per_px must be positive')
    right, up, to_eye = _camera_basis(np.array([0.,0.,1.]), np.array([0.,1.,0.]))
    v = np.asarray(mesh.vertices)
    if bounds is None:
        lo,hi = v[:,:2].min(0)-2, v[:,:2].max(0)+2
        bounds = (*lo,*hi)
    xmin,ymin,xmax,ymax = bounds
    w,h = np.ceil(np.array([xmax-xmin,ymax-ymin])/mm_per_px).astype(int)
    px,py = (v@right-xmin)/mm_per_px, (ymax-v@up)/mm_per_px
    depth = -(v@to_eye)
    light = np.asarray(light, float)
    if np.linalg.norm(light) == 0:
        raise ValueError('light vector cannot be zero')
    light /= np.linalg.norm(light)
    normals = mesh.vertex_normals
    normals = normals/(np.linalg.norm(normals,axis=1,keepdims=True)+1e-12)
    intensity = np.clip(.6 + .9*np.clip(normals@light,0,1),0,1)
    rgba = np.zeros((h,w,4),np.uint8)
    zbuf = np.full((h,w),np.inf)
    colors = np.asarray(mesh.visual.face_colors)[:,:3].astype(float)
    faces = np.asarray(mesh.faces)
    facing = np.cross(v[faces[:,1]]-v[faces[:,0]], v[faces[:,2]]-v[faces[:,0]])@to_eye
    for k in np.flatnonzero(facing > 0):
        tri = faces[k]
        x0,x1,x2 = px[tri]; y0,y1,y2 = py[tri]
        area = (x1-x0)*(y2-y0)-(x2-x0)*(y1-y0)
        if abs(area) < 1e-10:
            continue
        lx,hx = max(0,int(np.floor(min(px[tri])))),min(w-1,int(np.ceil(max(px[tri]))))
        ly,hy = max(0,int(np.floor(min(py[tri])))),min(h-1,int(np.ceil(max(py[tri]))))
        if lx > hx or ly > hy:
            continue
        ys,xs = np.mgrid[ly:hy+1,lx:hx+1]
        # Integer pixel coordinates are sample centres, matching OpenCV H.
        a = ((x1-xs)*(y2-ys)-(x2-xs)*(y1-ys))/area
        b = ((x2-xs)*(y0-ys)-(x0-xs)*(y2-ys))/area
        c = 1-a-b
        d = a*depth[tri[0]]+b*depth[tri[1]]+c*depth[tri[2]]
        selected = (a>=0)&(b>=0)&(c>=0)&(d<zbuf[ys,xs])
        shade = a*intensity[tri[0]]+b*intensity[tri[1]]+c*intensity[tri[2]]
        rows,cols = ys[selected],xs[selected]
        rgba[rows,cols,:3] = np.clip(shade[selected,None]*colors[k],0,255).astype(np.uint8)
        rgba[rows,cols,3] = 255
        zbuf[rows,cols] = d[selected]
    return rgba


def _mesh(part, color):
    import trimesh
    vertices, faces = part.tessellate(.08)
    mesh = trimesh.Trimesh(np.array([tuple(v) for v in vertices]),np.asarray(faces))
    mesh.visual.face_colors = np.array([*color,255],np.uint8)
    return mesh


def _objects():
    from holders import cup_lid, cylindrical, label_card
    from holders.registry import all_models
    specs = {s.name:s for s in all_models()}
    cases = [('label', 'holder_label_card', {'text':''}),
             ('cup84','holder_cup_lid',{'lid_diameter':84}),
             ('cup100','holder_cup_lid',{'lid_diameter':100})]
    cases += [(f'cylinder{d}','holder_spray_can',{'d':d,'h':30,'slot_count':1}) for d in (30,40,50)]
    for name,model,overrides in cases:
        spec = specs[model]
        values = spec.default_values() | overrides
        mesh = _mesh(spec.build(values), (45,85,175))
        mesh.vertices -= np.r_[mesh.bounds.mean(0)[:2],mesh.bounds[0,2]]
        yield name, model, overrides, mesh


def _baseplate():
    from build123d import Box, Pos, Align
    from gridfinity.baseplate import cell_positions, socket_cutout, PROFILE_HEIGHT
    # Actual 42 mm socket profile in a 4x4 blank, with a solid 1 mm floor.
    plate = Box(168,168,PROFILE_HEIGHT+1,align=(Align.CENTER,Align.CENTER,Align.MIN))
    cutter = socket_cutout()
    for x,y in cell_positions(4,4):
        plate -= Pos(x,y,1)*cutter
    mesh = _mesh(plate,(180,180,180))
    mesh.apply_translation([96,96,0])
    rgba = render_topdown(mesh,.25,(.7,.4,.5),bounds=(0,0,192,192))
    rgb = np.full(rgba.shape[:2]+(3,),40,np.uint8)
    rgb[rgba[:,:,3]>0] = rgba[rgba[:,:,3]>0,:3]
    return rgb


def skeleton_background():
    """Dark 4x4 frame with cross openings and dark corner pads, light surround."""
    rgb = np.full((768,768,3), 220, np.uint8)
    rgb[48:720,48:720] = 30
    for row in range(4):
        for col in range(4):
            x,y = 48+168*col,48+168*row
            # Two overlapping rectangles form a cross; retained corner pads
            # make a two-class frame/opening approximation insufficient.
            rgb[y+9:y+159,x+44:x+124] = 210
            rgb[y+44:y+124,x+9:x+159] = 210
    return rgb


def white_skeleton_image(illumination=False):
    """Small white item used for structural success/parity, generated in memory."""
    image = skeleton_background()
    image[340:388,320:440] = 248  # 30 x 12 mm, entirely inside the plate
    if illumination:
        for iy in range(4):
            for ix in range(4):
                cell = np.s_[48+iy*168:48+(iy+1)*168,48+ix*168:48+(ix+1)*168]
                image[cell] = np.clip(image[cell].astype(float)*(.65+.1*iy+.025*ix)+3*ix,0,255).astype(np.uint8)
    return image


def _background(kind, base):
    if kind == 'skeleton':
        return skeleton_background(),168.,12.
    if kind in ('bare','paper'):
        rgb = base.copy()
        if kind == 'paper':
            # 3/4-cell exposed border gives an independent scale reference.
            a,b = round((12+31.5)/.25),round((12+136.5)/.25)
            rgb[a:b,a:b] = 242
        return rgb,168.,12.
    rgb = np.full((432,432,3),40,np.uint8)
    rgb[48:384,48:384] = 242
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    for i,quad in enumerate(ARUCO_POSITIONS):
        x,y = np.rint((quad[0]+12)/.25).astype(int)
        marker = cv2.aruco.generateImageMarker(dictionary,i,40)
        rgb[y:y+40,x:x+40] = marker[:,:,None]
    return rgb,84.,12.


def _truth(mesh, extent):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    triangles = mesh.vertices[mesh.faces][:,:,:2]
    polygons = [Polygon(t) for t in triangles if abs((t[1,0]-t[0,0])*(t[2,1]-t[0,1])-(t[1,1]-t[0,1])*(t[2,0]-t[0,0])) > 1e-9]
    union = unary_union(polygons)
    if union.geom_type != 'Polygon':
        raise ValueError('fixture object projection must be connected')
    # Generator world centre sits at extent/2; pixel y runs downward.
    ring = np.asarray(union.simplify(.01, preserve_topology=True).exterior.coords)
    return np.c_[ring[:,0]+extent/2, extent/2-ring[:,1]].tolist()


def _phone_warp(rgb, tilt, seed):
    """Planar camera projection at distance 500 mm, exact known homography.

    The source scene is orthographic: this deliberately excludes height parallax.
    """
    h,w = rgb.shape[:2]
    angle = np.deg2rad(tilt)
    # Rotate plane about X, project with f=500/.25 pixels and principal centre.
    c,s = np.cos(angle),np.sin(angle)
    C = np.array([[1,0,-w/2],[0,1,-h/2],[0,0,1.]])
    P = np.array([[1,0,0],[0,c,0],[0,s*.25/500,1.]])
    H = np.linalg.inv(C)@P@C
    warped = cv2.warpPerspective(rgb,H,(w,h),borderValue=(40,40,40))
    warped = cv2.GaussianBlur(warped,(3,3),.45)
    rng = np.random.default_rng(seed)
    # Sparse +/-1 sensor noise keeps flat synthetics comfortably below 200 KB.
    noise = rng.choice([-1,0,1],size=(h,w,1),p=[.015,.97,.015])
    return np.clip(warped.astype(np.int16)+noise,0,255).astype(np.uint8),H


def measure(image, truth):
    """Record misses and wall time, never substitute ground-truth calibration."""
    from shapely.geometry import Polygon
    result = {}
    start = time.perf_counter()
    try:
        grid = detect_grid(image)
        rect = rectify(image,grid.H,size_mm=grid.size_mm,kind=grid.kind,polarity=grid.polarity)
    except (DetectionError,ValueError) as exc:
        elapsed = time.perf_counter()-start
        return {'detected':False,'failure':str(exc),'detection_seconds':elapsed,'methods':{}}
    detection_seconds = time.perf_counter()-start
    for method in ('threshold','periodic','grabcut','structural'):
        start = time.perf_counter()
        try:
            mask = segment(rect,method)
            ring = footprint(mask,mm_per_px=rect.mm_per_px,origin_mm=rect.origin_mm,
                             roi=_region(rect) if grid.polarity == 'dark' else None)
            recovered,expected = Polygon(ring),Polygon(truth)
            if not recovered.is_valid:
                raise DetectionError('recovered ring is not simple')
            entry = {'hausdorff_mm':recovered.hausdorff_distance(expected),
                     'area_error_pct':100*abs(recovered.area-expected.area)/expected.area,
                     'vertices':len(ring)-1}
        except (DetectionError,ValueError) as exc:
            entry = {'failure':str(exc)}
        entry['seconds'] = detection_seconds + time.perf_counter()-start
        result[method] = entry
    return {'detected':True,'polarity':grid.polarity,'confidence':grid.confidence,'size_mm':grid.size_mm,
            'detection_seconds':detection_seconds,'methods':result}


def generate(output):
    output.mkdir(parents=True,exist_ok=True)
    cv2.setNumThreads(1)
    base = _baseplate()
    records = []
    objects = list(_objects())
    for oi,(name,model,values,original) in enumerate(objects):
        for pose,(angle,dx,dy) in enumerate(((0,0,0),(27,3,-2),(-38,-2,3))):
            mesh = original.copy()
            a = np.deg2rad(angle)
            T = np.array([[np.cos(a),-np.sin(a),0,dx],[np.sin(a),np.cos(a),0,dy],[0,0,1,0],[0,0,0,1]])
            mesh.apply_transform(T)
            for kind in ('bare','paper','aruco','skeleton'):
                bg,extent,margin = _background(kind,base)
                truth = _truth(mesh,extent)
                placed = mesh.copy()
                side = extent+2*margin
                placed.apply_translation([side/2,side/2,6])
                rgba = render_topdown(placed,.25,(.7,.4,.5),bounds=(0,0,side,side))
                rgb = bg.copy()
                rgb[rgba[:,:,3]>0] = rgba[rgba[:,:,3]>0,:3]
                for tilt in (0,15):
                    name_id = f'{name}-p{pose}-{kind}-t{tilt}'
                    image,H = _phone_warp(rgb,tilt,1000+oi*100+pose*10+tilt)
                    result = measure(image,truth)
                    # 18 images: every object/background; poses and tilts spread
                    # deterministically. All 144 measurements/truths stay in JSON.
                    keep = kind != 'skeleton' and pose == oi%3 and tilt == (15 if oi%2 else 0)
                    filename = name_id+'.png' if keep else None
                    if keep:
                        cv2.imwrite(str(output/filename),cv2.cvtColor(image,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_PNG_COMPRESSION,9])
                        if (output/filename).stat().st_size > 200_000:
                            raise ValueError('fixture exceeds 200 KB')
                    metric_to_source = np.array([[4,0,margin*4],[0,4,margin*4],[0,0,1.]])
                    records.append({'id':name_id,'object':name,'model':model,'values':values,
                        'pose':{'rotation_deg':angle,'translation_mm':[dx,dy]},'background':kind,'tilt_deg':tilt,
                        'truth_mm':truth,'metric_to_image':(H@metric_to_source).tolist(),
                        'png':filename,'sha256':hashlib.sha256((output/filename).read_bytes()).hexdigest() if keep else None,
                        **result})
                    print(name_id, result['detected'],result['methods'].get('threshold',{}),flush=True)
    # Deliberately adverse images: accuracy failures are evidence, not omissions.
    stresses = []
    for mode in ('same-colour','shadow','edge-overhang'):
        mesh = objects[3][3].copy()  # cylinder30, independently known CAD outline
        if mode == 'edge-overhang':
            mesh.apply_translation([75,0,0])
        truth = _truth(mesh,168.)
        mesh.apply_translation([96,96,6])
        rgba = render_topdown(mesh,.25,(.7,.4,.5),bounds=(0,0,192,192))
        rgb = base.copy()
        selected = rgba[:,:,3] > 0
        if mode == 'shadow':
            silhouette = np.zeros(selected.shape,np.uint8)
            cv2.fillPoly(silhouette,[np.rint((np.asarray(truth)+12)*4).astype(np.int32)],1)
            shadow = cv2.warpAffine(silhouette,np.array([[1.,0,24],[0,1.,16]]),(768,768)) > 0
            rgb[shadow] = (rgb[shadow]*.28).astype(np.uint8)
        rgb[selected] = 180 if mode == 'same-colour' else rgba[selected,:3]
        image,H = _phone_warp(rgb,15,3000)
        name = 'stress-'+mode+'.png'
        cv2.imwrite(str(output/name),cv2.cvtColor(image,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_PNG_COMPRESSION,9])
        stresses.append({'id':mode,'png':name,'truth_mm':truth,**measure(image,truth)})
    import trimesh
    golden_mesh = trimesh.creation.box(extents=(8,6,2))
    golden_mesh.visual.face_colors = [60,120,180,255]
    golden = render_topdown(golden_mesh,.5,(.7,.4,.5),bounds=(-6,-6,6,6))
    cv2.imwrite(str(output/'renderer-golden.png'),cv2.cvtColor(golden,cv2.COLOR_RGBA2BGRA))
    metadata = {'source_main':subprocess.check_output(['git','rev-parse','origin/main'],text=True).strip(),'mm_per_source_pixel':.25,
                'opencv':cv2.__version__,'python':platform.python_version(),'machine':platform.machine(),
                'cpu':platform.processor(),'records':records,'stress_cases':stresses}
    (output/'measurements.json').write_text(json.dumps(metadata,indent=2)+'\n')


def sheet_background(sheet_id='letter-v1', *, print_scale=1.):
    """Rasterise nominal page geometry; print_scale changes ink, not the item."""
    from .footprint import sheet_profiles
    sheet = sheet_profiles()[sheet_id]
    width, height = sheet['page_mm']
    rgb = np.full((round(height*4), round(width*4), 3), 245, np.uint8)
    def px(value):
        return round(value*4*print_scale)
    x0, y0, x1, y1 = sheet['field_mm']
    rgb[px(y0):px(y1), px(x0):px(x1)] = sheet['field_gray_8bit']
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    size = px(sheet['marker_size_mm'])
    for i, (x, y) in sheet['markers_mm'].items():
        marker = cv2.aruco.generateImageMarker(dictionary, int(i), size)
        rgb[px(y):px(y)+size, px(x):px(x)+size] = marker[:, :, None]
    return rgb


def generate_sheet(output):
    """Independent sheet matrix: 18 CAD poses × two tilts × two illuminants.

    Sheet PNGs live in a subdirectory so the original fixture budget and matrix
    remain pinned. The same per-PNG 200 KB cap applies here.
    """
    from .footprint import sheet_profiles
    from .sheet_oracle import generate as sheet_oracle
    output.mkdir(parents=True, exist_ok=True)
    (output/'sheet').mkdir(exist_ok=True)
    cv2.setNumThreads(1)
    sheet = sheet_profiles()['letter-v1']
    x0, y0, x1, y1 = sheet['field_mm']
    width, height = sheet['page_mm']
    records = []
    for oi, (name, model, values, original) in enumerate(_objects()):
        for pose, (angle, dx, dy) in enumerate(((0,0,0), (27,3,-2), (-38,-2,3))):
            mesh = original.copy()
            a = np.deg2rad(angle)
            mesh.apply_transform(np.array([[np.cos(a),-np.sin(a),0,dx],
                [np.sin(a),np.cos(a),0,dy],[0,0,1,0],[0,0,0,1]]))
            truth = np.asarray(_truth(mesh, x1-x0))
            truth[:, 1] += ((y1-y0)-(x1-x0))/2
            placed = mesh.copy()
            placed.apply_translation([(x0+x1)/2, height-(y0+y1)/2, 0])
            rgba = render_topdown(placed, .25, (.7,.4,.5), bounds=(0,0,width,height))
            rgb = sheet_background()
            # render_topdown rounds its extent upward; crop the last sample.
            rgba = rgba[:rgb.shape[0], :rgb.shape[1]]
            selected = rgba[:, :, 3] > 0
            rgb[selected] = rgba[selected, :3]
            for light, gains in (('neutral', (1.,1.,1.)), ('warm', (1.12,1.,.85))):
                lit = np.clip(rgb.astype(float)*gains, 0, 255).astype(np.uint8)
                lit = cv2.copyMakeBorder(lit, 48, 48, 48, 48, cv2.BORDER_CONSTANT, value=(40,40,40))
                for tilt in (0, 15):
                    name_id = f'{name}-p{pose}-sheet-{light}-t{tilt}'
                    image, H = _phone_warp(lit, tilt, 4000+oi*100+pose*10+tilt)
                    filename = 'sheet/'+name_id+'.png'
                    path = output/filename
                    cv2.imwrite(str(path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR),
                                [cv2.IMWRITE_PNG_COMPRESSION, 9])
                    if path.stat().st_size > 200_000:
                        raise ValueError('fixture exceeds 200 KB')
                    grid = detect_grid(image)
                    rect = rectify(image, grid.H, size_mm=grid.size_mm, kind=grid.kind)
                    ring = footprint(segment(rect), roi=_region(rect),
                                     edge_message='item crosses the sheet field')
                    from shapely.geometry import Polygon
                    expected, recovered = Polygon(truth), Polygon(ring)
                    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
                    corners, ids, _ = cv2.aruco.ArucoDetector(dictionary).detectMarkers(
                        cv2.cvtColor(image, cv2.COLOR_RGB2GRAY))
                    records.append(dict(id=name_id, object=name, model=model, values=values,
                        pose=dict(rotation_deg=angle, translation_mm=[dx,dy]), background='sheet',
                        lighting=light, tilt_deg=tilt, truth_mm=truth.tolist(), png=filename,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        metric_to_image=(H@np.array([[4,0,x0*4+48],[0,4,y0*4+48],[0,0,1.]])).tolist(),
                        markers={str(int(i)):c.reshape(4,2).tolist() for i,c in zip(ids.ravel(),corners)},
                        detected=True, kind=grid.kind, sheet_id=grid.sheet_id,
                        reprojection_mm=grid.reprojection_mm,
                        hausdorff_mm=recovered.hausdorff_distance(expected),
                        area_error_pct=100*abs(recovered.area-expected.area)/expected.area))
    metadata = dict(source_main=subprocess.check_output(['git','rev-parse','origin/main'], text=True).strip(),
                    mm_per_source_pixel=.25, records=records)
    (output/'sheet-measurements.json').write_text(json.dumps(metadata, indent=2)+'\n')
    (output/'sheet-footprints.json').write_text(json.dumps(sheet_oracle(output), indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('tests/fixtures/capture'))
    parser.add_argument('--sheet', action='store_true', help='generate only the separate sheet matrix')
    args = parser.parse_args()
    (generate_sheet if args.sheet else generate)(args.output)
