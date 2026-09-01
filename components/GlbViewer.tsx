"use client";

// Renders a baked build123d GLB in a three.js canvas (bead pst-0um9).
//
// Distinct from StlViewer on two axes that matter:
//   • Up-axis. build123d's glTF export embeds a root-node rotation
//     (-90° about X) that maps its native Z-up geometry into glTF's
//     Y-up convention. So we load into a standard Y-up scene (three.js
//     default camera.up) and trust the embedded transform — applying a
//     manual -PI/2 rotation here would DOUBLE-rotate and lay the model
//     on its side. (Confirmed by inspecting the exporter output: the
//     GLB's sole node carries quaternion [-0.707, 0, 0, 0.707].)
//   • Scale. OCP exports in metres (an 84 mm part spans 0.084 units),
//     where StlViewer's mm-tuned near/far (0.1 floor) would clip the
//     whole model. fitCamera derives near/far from the actual bbox, so
//     it is scale-agnostic — metres or millimetres both frame cleanly.
//
// Render-on-demand (no rAF loop), same as StlViewer: render() fires
// from OrbitControls 'change', from load, and from resize.

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  computeCameraAxes,
  type CameraAxes,
  type WorldBasis,
} from "./StlViewer";

export interface GlbBbox {
  /** World-space extents (width, height, depth) of the loaded scene. */
  size: [number, number, number];
}

// The baked GLB is Y-up: build123d authors its parts Z-up, and the OCP
// exporter bakes a -90°X root rotation so glTF's Y-up convention holds
// (see the file header). The orientation compass, however, must show the
// *part's* native axes so it matches the SCAD viewer's Z-up compass. That
// -90°X maps the part basis into this Y-up world as:
//   part X → world +X,  part Y → world -Z,  part Z → world +Y.
// Projecting these (rather than the raw world axes) keeps the X/Y/Z labels
// meaningful — Z reads as "up" here just as it does for a SCAD render.
const PART_BASIS_IN_WORLD: WorldBasis = {
  x: new THREE.Vector3(1, 0, 0),
  y: new THREE.Vector3(0, 0, -1),
  z: new THREE.Vector3(0, 1, 0),
};

/**
 * View-space projection of the GLB part's native X/Y/Z axes for a given
 * camera. Pure (delegates to computeCameraAxes with the fixed Z-up→Y-up
 * basis above); unit-tested in GlbViewer.test.
 */
export function partCameraAxes(camera: THREE.Camera): CameraAxes {
  return computeCameraAxes(camera, PART_BASIS_IN_WORLD);
}

interface Props {
  /** URL of the GLB to load (the /api/bd-asset serving route). */
  url: string;
  /**
   * Fired once per successful load with the loaded model's bbox. The
   * detail page uses it as an orientation guard: a double-rotation
   * regression would swap Y and Z and topple the model, which a
   * gross depth-over-height check surfaces in the console (the e2e
   * spec pins the exact upright envelope).
   */
  onLoaded?: (bbox: GlbBbox) => void;
  /** Fired if the GLB fails to load/parse. */
  onError?: (message: string) => void;
  /**
   * Fired on every OrbitControls change (and once on load) with the
   * part's native axes projected into view space. Drives the shared
   * AxesIndicator so the GLB viewer shows the same orientation compass
   * as the SCAD viewer. (pst-6ram)
   */
  onCameraChange?: (axes: CameraAxes) => void;
}

/**
 * Camera framing for a bounding box, scale-agnostic. Returns a camera
 * position on the iso diagonal plus near/far planes derived from the
 * model size (not a fixed floor), so a metre-scale GLB frames exactly
 * like a millimetre-scale one. Pure — unit-tested in GlbViewer.test.
 */
export function fitCamera(
  box: THREE.Box3,
  fovDeg: number,
): { position: THREE.Vector3; target: THREE.Vector3; near: number; far: number } {
  const size = new THREE.Vector3();
  box.getSize(size);
  const target = new THREE.Vector3();
  box.getCenter(target);
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const fov = fovDeg * (Math.PI / 180);
  const dist = (maxDim / 2 / Math.tan(fov / 2)) * 1.8;
  const dir = new THREE.Vector3(1, 1, 1).normalize();
  const position = target.clone().addScaledVector(dir, dist);
  return {
    position,
    target,
    near: dist / 100,
    far: dist * 100,
  };
}

export default function GlbViewer({
  url,
  onLoaded,
  onError,
  onCameraChange,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Latest callbacks in refs so the mount-once scene closure always
  // calls the current prop without re-registering.
  const onLoadedRef = useRef(onLoaded);
  const onErrorRef = useRef(onError);
  const onCameraChangeRef = useRef(onCameraChange);
  useEffect(() => {
    onLoadedRef.current = onLoaded;
    onErrorRef.current = onError;
    onCameraChangeRef.current = onCameraChange;
  }, [onLoaded, onError, onCameraChange]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    // Y-up (three.js default) — see the file header on why we do NOT
    // rotate the loaded model.
    const camera = new THREE.PerspectiveCamera(45, 1, 0.001, 10000);
    camera.position.set(1, 1, 1);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setClearColor(0x000000, 0);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    // Headlight parented to the camera (same pattern as StlViewer) so
    // form-defining shading orbits with the viewer.
    scene.add(camera);
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const key = new THREE.DirectionalLight(0xffffff, 0.9);
    key.position.set(0.5, 1, 0.5);
    camera.add(key);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = false;
    // Only emit axes once the model is on screen — before that the
    // orientation compass has no meaningful frame to point at, and the
    // Y-up world axes would flash the wrong labels.
    let modelLoaded = false;
    const emitAxes = () => {
      if (!modelLoaded) return;
      camera.updateMatrixWorld();
      onCameraChangeRef.current?.(partCameraAxes(camera));
    };
    const render = () => {
      renderer.render(scene, camera);
      emitAxes();
    };
    controls.addEventListener("change", render);

    function handleResize() {
      const { clientWidth: w, clientHeight: h } = container!;
      if (w === 0 || h === 0) return;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      render();
    }

    let model: THREE.Object3D | null = null;
    let disposed = false;
    const loader = new GLTFLoader();
    loader.load(
      url,
      (gltf) => {
        if (disposed) return;
        model = gltf.scene;
        scene.add(model);

        const box = new THREE.Box3().setFromObject(model);
        const fit = fitCamera(box, camera.fov);
        camera.position.copy(fit.position);
        camera.near = fit.near;
        camera.far = fit.far;
        camera.updateProjectionMatrix();
        controls.target.copy(fit.target);
        controls.update();
        modelLoaded = true;
        render();

        const size = new THREE.Vector3();
        box.getSize(size);
        onLoadedRef.current?.({ size: [size.x, size.y, size.z] });
      },
      undefined,
      (err) => {
        if (disposed) return;
        onErrorRef.current?.(
          err instanceof Error ? err.message : "failed to load GLB",
        );
      },
    );

    const ro = new ResizeObserver(handleResize);
    ro.observe(container);
    handleResize();

    return () => {
      disposed = true;
      ro.disconnect();
      controls.removeEventListener("change", render);
      controls.dispose();
      if (model) {
        model.traverse((obj) => {
          const mesh = obj as THREE.Mesh;
          if (mesh.geometry) mesh.geometry.dispose();
          const mat = mesh.material as THREE.Material | THREE.Material[];
          if (Array.isArray(mat)) mat.forEach((m) => m.dispose());
          else if (mat) mat.dispose();
        });
      }
      renderer.dispose();
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [url]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 overflow-hidden"
      data-testid="glb-viewer"
    />
  );
}
