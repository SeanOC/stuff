"""Reproduce pst-g7npe rev-3 structural-mask ambiguity on the real fixture.

Run from build123d: uv run python scripts/probe_capture_structural.py
Diagnostic only: compare full-band/half-band and eroded/full residual masks.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cv2,numpy as np
from capture.footprint import detect_grid,rectify,_region,footprint
im=cv2.cvtColor(cv2.imread(str(ROOT/'tests/fixtures/capture/real/sharpie-daylight.png')),cv2.COLOR_BGR2RGB)
g=detect_grid(im); r=rectify(im,g.H,size_mm=g.size_mm,kind=g.kind,polarity=g.polarity)
roi=_region(r).astype(bool); rgb=r.image; h,w=rgb.shape[:2]; pitch=210
lab=cv2.cvtColor(rgb.astype(np.float32)/255,cv2.COLOR_RGB2LAB)
yy,xx=np.indices((h,w)); d=np.minimum(np.minimum(xx%pitch,pitch-xx%pitch),np.minimum(yy%pitch,pitch-yy%pitch))*.2
gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
print('boundary medians:',[(round(float(t),1),round(float(np.median(gray[(d>=t)&(d<t+.2)&roi])),1)) for t in np.arange(0,5.01,.2)])
for half in (True,False):
 for wf in (2,4,6,8,10):
  cls=(d <= wf/(2 if half else 1)).astype(np.uint8)
  res=np.zeros((h,w)); valid=np.zeros((h,w),bool)
  missing=False
  for mask in (cls,1-cls):
   er=cv2.erode(mask,np.ones((17,17),np.uint8)).astype(bool);valid |= er
   for y in range(0,h,pitch):
    for x in range(0,w,pitch):
     c=np.s_[y:y+pitch,x:x+pitch]; samples=er[c]&roi[c]
     if not samples.any():missing=True;continue
     ref=np.median(lab[c][samples],axis=0);delta=np.linalg.norm(lab[c]-ref,axis=2); chosen=mask[c].astype(bool);res[c][chosen]=delta[chosen]
  if missing: print('half',half,'wf',wf,'empty eroded reference');continue
  for eroded in (False,True):
   region=roi&valid if eroded else roi; vals=res[region];med=np.median(vals);mad=np.median(abs(vals-med))
   for k in (3,5,8):
    mask=((res>med+k*mad)&region).astype(np.uint8);mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);c=max(contours,key=cv2.contourArea)
    x,y,bw,bh=cv2.boundingRect(c)
    print('half',half,'wf',wf,'eroded',eroded,'k',k,'coverage',round(mask.sum()/roi.sum(),4),'bbox',tuple(round(v*.2,1) for v in (x,y,bw,bh)))
