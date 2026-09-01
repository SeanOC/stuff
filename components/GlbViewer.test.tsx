// Pure-math tests for GlbViewer's camera framing. No WebGL: fitCamera
// only does Box3 arithmetic. The point it pins is scale-agnosticism —
// a metre-scale build123d GLB (an 84mm part spans 0.084 units) must
// frame with near/far bracketing the model, not the mm-tuned 0.1 floor
// that StlViewer uses (which would clip the whole thing). (pst-0um9)

import * as THREE from "three";
import { describe, expect, it } from "vitest";
import { fitCamera, partCameraAxes } from "./GlbViewer";
import { computeCameraAxes } from "./StlViewer";

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

// The GLB scene is Y-up (the OCP export bakes a -90°X root rotation onto
// Z-up parts), so the orientation compass must project the *part's*
// native axes, not the raw world axes, to stay label-consistent with the
// SCAD viewer's Z-up compass. partCameraAxes pins that Z-up→Y-up mapping.
// computeCameraAxes only reads camera.matrixWorld, so no WebGL is needed.
describe("partCameraAxes (GLB Z-up→Y-up compass, pst-6ram)", () => {
  function isoCamera(): THREE.PerspectiveCamera {
    // The Y-up iso camera GlbViewer boots with, framed at the origin.
    const cam = new THREE.PerspectiveCamera(45, 1, 0.001, 10000);
    cam.up.set(0, 1, 0);
    cam.position.set(1, 1, 1);
    cam.lookAt(0, 0, 0);
    cam.updateMatrixWorld();
    return cam;
  }

  it("maps the part basis into the Y-up world: X→+X, Y→−Z, Z→+Y", () => {
    // Camera-independent: the mapping is a fixed relabelling of the world
    // axes, so partCameraAxes must equal the world projection with Y and
    // Z swapped (and part-Y negated). Comparing to computeCameraAxes pins
    // exactly that basis without depending on the camera pose.
    const cam = isoCamera();
    const world = computeCameraAxes(cam);
    const part = partCameraAxes(cam);
    for (const i of [0, 1, 2] as const) {
      expect(part.x[i]).toBeCloseTo(world.x[i], 5); // part X = world +X
      expect(part.z[i]).toBeCloseTo(world.y[i], 5); // part Z = world +Y
      expect(part.y[i]).toBeCloseTo(-world.z[i], 5); // part Y = world −Z
    }
  });

  it("reads Z as up at the iso view, matching the SCAD compass", () => {
    // Part Z is the authored up-axis; it maps to world +Y which the Y-up
    // iso camera projects to screen-up (view-space y > 0). Part X points
    // to screen-right. This is what makes the compass a useful reference.
    const part = partCameraAxes(isoCamera());
    expect(part.z[1]).toBeGreaterThan(0.3); // Z tip points up
    expect(part.x[0]).toBeGreaterThan(0.3); // X tip points right
  });

  it("returns unit-length direction components", () => {
    const part = partCameraAxes(isoCamera());
    for (const a of [part.x, part.y, part.z]) {
      const mag = Math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]);
      expect(mag).toBeCloseTo(1, 5);
    }
  });
});
