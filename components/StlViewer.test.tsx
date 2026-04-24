// Pure-math unit tests for the camera-axes projector. No WebGL needed:
// computeCameraAxes only reads camera.matrixWorld, which Three.js
// computes on its own from position/quaternion/scale. (st-oc3)

import * as THREE from "three";
import { describe, expect, it } from "vitest";
import { computeCameraAxes } from "./StlViewer";

function makeCamera(
  position: [number, number, number],
  lookAt: [number, number, number],
): THREE.PerspectiveCamera {
  const cam = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
  // OpenSCAD world is Z-up, same as the live app.
  cam.up.set(0, 0, 1);
  cam.position.set(...position);
  cam.lookAt(new THREE.Vector3(...lookAt));
  cam.updateMatrixWorld();
  return cam;
}

describe("computeCameraAxes", () => {
  it("front view (+Y looking at origin): world-X is screen-right", () => {
    // Camera at (0, -100, 0) looking at origin, Z-up. World-X projects
    // to screen-right (view-space x ≈ +1), world-Z to screen-up (view-
    // space y ≈ +1). World-Y points away from the camera into the
    // scene; three.js cameras look down -Z in view space, so "into the
    // scene" is negative view-z.
    const cam = makeCamera([0, -100, 0], [0, 0, 0]);
    const axes = computeCameraAxes(cam);
    expect(axes.x[0]).toBeCloseTo(1, 3);
    expect(axes.x[1]).toBeCloseTo(0, 3);
    expect(axes.z[0]).toBeCloseTo(0, 3);
    expect(axes.z[1]).toBeCloseTo(1, 3);
    expect(axes.y[2]).toBeLessThan(-0.9);
  });

  it("top view (+Z looking down): world-X is screen-right, world-Y is screen-up", () => {
    // Camera at (0, 0, 100) looking at origin. With Z-up and +Z camera
    // position, up and forward become colinear — use Y-up so the
    // camera's screen-up maps to world +Y.
    const cam = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    cam.up.set(0, 1, 0);
    cam.position.set(0, 0, 100);
    cam.lookAt(0, 0, 0);
    cam.updateMatrixWorld();

    const axes = computeCameraAxes(cam);
    expect(axes.x[0]).toBeCloseTo(1, 3);
    expect(axes.y[1]).toBeCloseTo(1, 3);
    // World-Z extends toward the viewer (out of screen) → view-z > 0.
    expect(axes.z[2]).toBeGreaterThan(0.9);
  });

  it("returns unit-length direction components", () => {
    const cam = makeCamera([50, 50, 50], [0, 0, 0]);
    const axes = computeCameraAxes(cam);
    for (const a of [axes.x, axes.y, axes.z]) {
      const mag = Math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]);
      // transformDirection normalizes, so the projected vector stays unit.
      expect(mag).toBeCloseTo(1, 5);
    }
  });
});
