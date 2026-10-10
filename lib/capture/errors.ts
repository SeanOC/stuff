/** Reachable threshold/lattice errors: build123d/capture/footprint.py:54,67,98,102,106,221,225. */
export const DETECTION_ERRORS = [
  "no perimeter lattice contrast",
  "perimeter does not support a 42 mm lattice",
  "no board boundary",
  "board boundary is not a visible rectangle",
  "board touches image edge",
  "no item contour",
  "board obstructed by an object crossing its edge",
  "item too large for the plate or background not modelled",
  "item crosses the plate edge",
  "contour cannot meet the 0.3 mm / 256 vertex contract",
  "sheet is not flat or the print is scaled",
  "a reference marker is hidden — keep all four corners visible and uncovered",
  "item crosses the sheet field",
] as const;

export class DetectionError extends Error {
  constructor(message: (typeof DETECTION_ERRORS)[number]) {
    super(message);
    this.name = "DetectionError";
  }
}
