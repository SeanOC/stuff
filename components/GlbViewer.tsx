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

export interface GlbBbox {
  /** World-space extents (width, height, depth) of the loaded scene. */
  size: [number, number, number];
}

interface Props {
  /** URL of the GLB to load (the /api/bd-asset serving route). */
  url: string;
  /**
   * Fired once per successful load with the loaded model's bbox. The
   * detail page uses it as an orientation assertion: height (Y) must be
   * the tallest axis for these upright holders — a double-rotation
   * regression would swap Y and Z and trip a test/console check.
   */
  onLoaded?: (bbox: GlbBbox) => void;
  /** Fired if the GLB fails to load/parse. */
  onError?: (message: string) => void;
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

export default function GlbViewer({ url, onLoaded, onError }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Latest callbacks in refs so the mount-once scene closure always
  // calls the current prop without re-registering.
  const onLoadedRef = useRef(onLoaded);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onLoadedRef.current = onLoaded;
    onErrorRef.current = onError;
  }, [onLoaded, onError]);

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
    const render = () => renderer.render(scene, camera);
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
