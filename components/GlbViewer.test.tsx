// Pure-math tests for GlbViewer's camera framing. No WebGL: fitCamera
// only does Box3 arithmetic. The point it pins is scale-agnosticism —
// a metre-scale build123d GLB (an 84mm part spans 0.084 units) must
// frame with near/far bracketing the model, not the mm-tuned 0.1 floor
// that StlViewer uses (which would clip the whole thing). (pst-0um9)

import * as THREE from "three";
import { describe, expect, it } from "vitest";
import { fitCamera } from "./GlbViewer";

function boxOfSize(x: number, y: number, z: number): THREE.Box3 {
  return new THREE.Box3(
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(x, y, z),
  );
}

describe("fitCamera", () => {
  it("centres the target on the box centre", () => {
    const fit = fitCamera(boxOfSize(0.084, 0.084, 0.062), 45);
    expect(fit.target.x).toBeCloseTo(0.042, 5);
    expect(fit.target.y).toBeCloseTo(0.042, 5);
    expect(fit.target.z).toBeCloseTo(0.031, 5);
  });

  it("brackets a metre-scale model: near < model distance < far", () => {
    const fit = fitCamera(boxOfSize(0.084, 0.084, 0.062), 45);
    const dist = fit.position.distanceTo(fit.target);
    // The whole model sits well inside the frustum.
    expect(fit.near).toBeGreaterThan(0);
    expect(fit.near).toBeLessThan(dist);
    expect(fit.far).toBeGreaterThan(dist);
    // Scale-agnostic: near tracks the model size, not a fixed 0.1 floor
    // (which would exceed this metre-scale model's ~0.11 camera distance).
    expect(fit.near).toBeLessThan(0.1);
  });

  it("scales cleanly for a millimetre-scale model too", () => {
    const fit = fitCamera(boxOfSize(84, 84, 62), 45);
    const dist = fit.position.distanceTo(fit.target);
    expect(fit.near).toBeLessThan(dist);
    expect(fit.far).toBeGreaterThan(dist);
  });

  it("puts the camera on the +++ iso diagonal", () => {
    const fit = fitCamera(boxOfSize(1, 1, 1), 45);
    expect(fit.position.x).toBeGreaterThan(fit.target.x);
    expect(fit.position.y).toBeGreaterThan(fit.target.y);
    expect(fit.position.z).toBeGreaterThan(fit.target.z);
  });
});
