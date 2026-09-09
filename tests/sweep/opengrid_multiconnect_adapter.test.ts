import { sweepModel } from "./runner";

sweepModel("opengrid_multiconnect_adapter", [
  ...["single", "double"].flatMap((size) => [3, 6].map((plate_t) => ({
    label: `corner clip ${size}, plate=${plate_t}, widest slots`,
    values: { size, plate_t, slot_tolerance: 1.075 },
  }))),
]);
