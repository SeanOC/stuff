"use client";

// Renders an STL byte array in a three.js canvas. Iso-style camera
// with OrbitControls (left-drag rotate, right/shift-drag pan, wheel
// zoom). Auto-fits to the model bbox on each STL update. Reuses the
// renderer/scene across updates so we only rebuild geometry.
//
// Render-on-demand: no rAF loop. renderer.render() is called from the
// OrbitControls 'change' event and from setStl/handleResize. Damping
// is off — enabling it would require a rAF loop to animate inertia.
//
// Phase 3 (st-1j9): imperative API via forwardRef. Callers grab the
// handle to drive setCameraPreset / resetCamera without reaching for
// a DOM escape hatch. A dev-only shim still writes the handle to
// `canvas.__stlViewer` so `tests/e2e/preview-controls.spec.ts`
// assertions keep working; the shim short-circuits in production so
// the attribute doesn't ship.

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

interface Props {
  stl: Uint8Array;
  onCameraChange?: (axes: CameraAxes) => void;
}

export type CameraPreset = "top" | "front" | "iso";

// Projected world basis vectors in view space. Each entry is the tuple
// [screen_right, screen_up, depth] — screen_right/up are unit direction
// components in the screen plane (range roughly -1..1; use with SVG Y
// flipped). depth>0 means the axis tip extends toward the viewer (out
// of the screen); depth<0 means it extends into the scene (behind the
// origin relative to the camera). Three.js cameras look down -Z in
// view space, hence the sign. (st-oc3)
export interface CameraAxes {
  x: [number, number, number];
  y: [number, number, number];
  z: [number, number, number];
}

export interface StlViewerHandle {
  camera: THREE.PerspectiveCamera;
  controls: OrbitControls;
  setCameraPreset(preset: CameraPreset): void;
  resetCamera(): void;
}

const StlViewer = forwardRef<StlViewerHandle, Props>(function StlViewer(
  { stl, onCameraChange },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const sceneRef = useRef<SceneHandle | null>(null);
  const handleRef = useRef<StlViewerHandle | null>(null);
  // Prop stored in a ref so the scene's long-lived OrbitControls 'change'
  // handler can call the latest callback without re-registering when the
  // parent passes a new function identity on re-render.
  const onCameraChangeRef = useRef(onCameraChange);
  useEffect(() => {
    onCameraChangeRef.current = onCameraChange;
  }, [onCameraChange]);

  // Bootstrap scene once on mount.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const emitAxes = (cam: THREE.PerspectiveCamera) =>
      onCameraChangeRef.current?.(computeCameraAxes(cam));
    const handle = bootstrapScene(container, emitAxes);
    sceneRef.current = handle;
    canvasRef.current = handle.canvas;
    handleRef.current = handle.imperative;

    // E2E compatibility shim. `tests/e2e/preview-controls.spec.ts`
    // reads `canvas.__stlViewer.camera.position` to verify wheel and
    // tab-click reach the camera. The forwardRef is the supported
    // API for app code — the shim is just a test-only bridge we
    // keep attached so specs don't have to reach into React refs.
    // Ships in prod (CI's playwright webServer is `next start`);
    // it's one DOM property on a canvas, no security/size concern.
    (handle.canvas as unknown as { __stlViewer?: StlViewerHandle })
      .__stlViewer = handle.imperative;

    const ro = new ResizeObserver(() => handle.handleResize());
    ro.observe(container);
    return () => {
      ro.disconnect();
      handle.dispose();
      sceneRef.current = null;
      handleRef.current = null;
      canvasRef.current = null;
    };
  }, []);

  useImperativeHandle(
    ref,
    (): StlViewerHandle => {
      // Delegate to whatever handleRef currently points at; never
      // returns a stale reference because handleRef is updated on
      // mount and cleared on unmount.
      return {
        get camera() {
          return handleRef.current!.camera;
        },
        get controls() {
          return handleRef.current!.controls;
        },
        setCameraPreset(preset) {
          handleRef.current?.setCameraPreset(preset);
        },
        resetCamera() {
          handleRef.current?.resetCamera();
        },
      };
    },
    [],
  );

  // Update geometry whenever the STL bytes change.
  useEffect(() => {
    const handle = sceneRef.current;
    if (!handle) return;
    handle.setStl(stl);
  }, [stl]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 overflow-hidden"
      data-testid="stl-viewer"
    />
  );
});

StlViewer.displayName = "StlViewer";

export default StlViewer;

interface SceneHandle {
  canvas: HTMLCanvasElement;
  imperative: StlViewerHandle;
  setStl(data: Uint8Array): void;
  handleResize(): void;
  dispose(): void;
}

export function computeCameraAxes(camera: THREE.Camera): CameraAxes {
  // World→view rotation: inverse of the camera's world matrix applied
  // to a direction. `transformDirection` ignores translation + scale.
  // Caller is responsible for the camera's matrixWorld being current
  // (OrbitControls.update() calls camera.updateMatrixWorld).
  const inv = new THREE.Matrix4().copy(camera.matrixWorld).invert();
  const project = (x: number, y: number, z: number): [number, number, number] => {
    const r = new THREE.Vector3(x, y, z).transformDirection(inv);
    return [r.x, r.y, r.z];
  };
  return {
    x: project(1, 0, 0),
    y: project(0, 1, 0),
    z: project(0, 0, 1),
  };
}

function bootstrapScene(
  container: HTMLDivElement,
  emitAxes: (camera: THREE.PerspectiveCamera) => void,
): SceneHandle {
  const scene = new THREE.Scene();
  // No scene.background — the WebGL canvas clears to alpha=0 so the
  // DOM GridOverlay (rendered as an earlier sibling under the same
  // relative parent) shows through where the model doesn't cover.
  // The viewer section's bg-panel2 is the true background color.
  // (st-lpt)

  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 5000);
  // OpenSCAD STLs are Z-up; three.js defaults to Y-up. Without this the
  // model lies on its side and OrbitControls rotates around the wrong axis.
  camera.up.set(0, 0, 1);
  camera.position.set(120, 120, 120);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(window.devicePixelRatio);
  container.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const key = new THREE.DirectionalLight(0xffffff, 0.9);
  key.position.set(1, 1, 1);
  scene.add(key);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = false;
  const onControlsChange = () => {
    renderer.render(scene, camera);
    // OrbitControls emits 'change' on mouse drag, wheel zoom, and any
    // controls.update() call (including the ones from setCameraPreset,
    // resetCamera, and fitCameraToBbox). Piping the axes here keeps
    // the consumer's indicator in sync regardless of input source. (st-oc3)
    emitAxes(camera);
  };
  controls.addEventListener("change", onControlsChange);

  // Snapshot of the auto-fit orientation captured on each setStl.
  // resetCamera() restores this — user can wheel/drag all they like
  // and `r` brings them home.
  let lastFit: { position: THREE.Vector3; target: THREE.Vector3 } | null = null;

  function setCameraPreset(preset: CameraPreset) {
    const center = controls.target.clone();
    const dist = camera.position.distanceTo(center);
    // Direction vectors in the Z-up world. "front" looks back toward -Y,
    // so the camera sits on +Y; "top" sits on +Z; "iso" matches the
    // initial fitCameraToBbox orientation.
    const dir =
      preset === "top"
        ? new THREE.Vector3(0, 0, 1)
        : preset === "front"
          ? new THREE.Vector3(0, 1, 0)
          : new THREE.Vector3(1, 1, 1).normalize();
    camera.position.copy(center).addScaledVector(dir, dist);
    camera.up.set(0, 0, 1);
    camera.lookAt(center);
    camera.updateProjectionMatrix();
    controls.update();
    renderer.render(scene, camera);
  }

  function resetCamera() {
    if (!lastFit) return;
    camera.position.copy(lastFit.position);
    controls.target.copy(lastFit.target);
    camera.up.set(0, 0, 1);
    camera.lookAt(lastFit.target);
    camera.updateProjectionMatrix();
    controls.update();
    renderer.render(scene, camera);
  }

  const imperative: StlViewerHandle = {
    camera,
    controls,
    setCameraPreset,
    resetCamera,
  };

  let mesh: THREE.Mesh | null = null;
  const loader = new STLLoader();

  function fitCameraToBbox(box: THREE.Box3) {
    const size = new THREE.Vector3();
    box.getSize(size);
    const center = new THREE.Vector3();
    box.getCenter(center);
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = camera.fov * (Math.PI / 180);
    const dist = (maxDim / 2) / Math.tan(fov / 2) * 1.8;
    const dir = new THREE.Vector3(1, 1, 1).normalize();
    camera.position.copy(center).addScaledVector(dir, dist);
    camera.up.set(0, 0, 1);
    camera.lookAt(center);
    camera.near = Math.max(dist / 1000, 0.1);
    camera.far = dist * 10;
    camera.updateProjectionMatrix();
    controls.target.copy(center);
    controls.update();
    lastFit = {
      position: camera.position.clone(),
      target: controls.target.clone(),
    };
  }

  function setStl(data: Uint8Array) {
    if (mesh) {
      scene.remove(mesh);
      mesh.geometry.dispose();
      (mesh.material as THREE.Material).dispose();
      mesh = null;
    }
    // STLLoader wants a plain ArrayBuffer. Copy into a fresh one — the
    // Emscripten heap may be a SharedArrayBuffer-ish view and the
    // underlying bytes can move when the WASM instance is disposed.
    const buffer = new ArrayBuffer(data.byteLength);
    new Uint8Array(buffer).set(data);
    const geom = loader.parse(buffer);
    geom.computeVertexNormals();
    geom.computeBoundingBox();
    const mat = new THREE.MeshStandardMaterial({
      color: 0x7ee787,
      metalness: 0.1,
      roughness: 0.7,
      flatShading: true,
    });
    mesh = new THREE.Mesh(geom, mat);
    scene.add(mesh);
    if (geom.boundingBox) fitCameraToBbox(geom.boundingBox);
    renderer.render(scene, camera);
  }

  function handleResize() {
    const { clientWidth: w, clientHeight: h } = container;
    if (w === 0 || h === 0) return;
    // `setSize(w, h)` (default updateStyle=true) applies CSS width/height
    // to the canvas. Without this, on retina displays (devicePixelRatio>1)
    // the canvas attribute size becomes w*DPR and — with no CSS size — the
    // canvas renders at that attribute size, overflowing the container and
    // being clipped by overflow:hidden. The viewport ends up showing only
    // empty space at the top-left of the too-large canvas: blank.
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
  }

  handleResize();
  // Seed the consumer with the initial camera orientation so the axes
  // indicator has something to render before the first OrbitControls
  // 'change' event (which only fires on user input or an update() that
  // saw a delta — the initial fit will fire, but emitting here makes
  // it explicit and defensive against future OrbitControls semantics
  // changes). (st-oc3)
  camera.updateMatrixWorld();
  emitAxes(camera);

  return {
    canvas: renderer.domElement,
    imperative,
    setStl,
    handleResize,
    dispose() {
      controls.removeEventListener("change", onControlsChange);
      controls.dispose();
      renderer.dispose();
      if (mesh) {
        mesh.geometry.dispose();
        (mesh.material as THREE.Material).dispose();
      }
      container.removeChild(renderer.domElement);
    },
  };
}
