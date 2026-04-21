"use client";

// Renders an STL byte array in a three.js canvas. Iso-style camera
// with OrbitControls (left-drag rotate, right/shift-drag pan, wheel
// zoom). Auto-fits to the model bbox on each STL update. Reuses the
// renderer/scene across updates so we only rebuild geometry.
//
// Render-on-demand: no rAF loop. renderer.render() is called from the
// OrbitControls 'change' event and from setStl/handleResize. Damping
// is off — enabling it would require a rAF loop to animate inertia.

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

interface Props {
  stl: Uint8Array;
}

export default function StlViewer({ stl }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<SceneHandle | null>(null);

  // Bootstrap scene once on mount.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const handle = bootstrapScene(container);
    sceneRef.current = handle;
    const ro = new ResizeObserver(() => handle.handleResize());
    ro.observe(container);
    return () => {
      ro.disconnect();
      handle.dispose();
      sceneRef.current = null;
    };
  }, []);

  // Update geometry whenever the STL bytes change.
  useEffect(() => {
    const handle = sceneRef.current;
    if (!handle) return;
    handle.setStl(stl);
  }, [stl]);

  return (
    <div
      ref={containerRef}
      style={{
        height: 480,
        background: "#161b22",
        border: "1px solid #30363d",
        borderRadius: 4,
        overflow: "hidden",
      }}
    />
  );
}

interface SceneHandle {
  setStl(data: Uint8Array): void;
  handleResize(): void;
  dispose(): void;
}

function bootstrapScene(container: HTMLDivElement): SceneHandle {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x161b22);

  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 5000);
  // OpenSCAD STLs are Z-up; three.js defaults to Y-up. Without this the
  // model lies on its side and OrbitControls rotates around the wrong axis.
  camera.up.set(0, 0, 1);
  camera.position.set(120, 120, 120);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  container.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const key = new THREE.DirectionalLight(0xffffff, 0.9);
  key.position.set(1, 1, 1);
  scene.add(key);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = false;
  const onControlsChange = () => renderer.render(scene, camera);
  controls.addEventListener("change", onControlsChange);

  // Expose camera/controls on the canvas for e2e tests (see
  // tests/e2e/preview-controls.spec.ts). Cheap — single property — and
  // keeps the component API unchanged. Not part of the public contract.
  (renderer.domElement as unknown as { __stlViewer: unknown }).__stlViewer = {
    camera,
    controls,
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

  return {
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
