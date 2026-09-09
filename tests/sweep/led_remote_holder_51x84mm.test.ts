import { sweepModel, type SweepCase } from "./runner";

// The generic sweep varies one parameter on the default openGrid mount.
// Exercise the accepted square MC slab at every plate-footprint extreme too
// (pst-5fq5), including the narrow/wide aspects and slot-conflict case.
const extremes: Record<string, [number, number]> = {
  remote_w: [40, 70],
  remote_h: [70, 120],
  side_clearance: [0.2, 1],
  wall: [1.6, 4],
  plate_len_max: [60, 300],
};
const mcCases: SweepCase[] = Object.entries(extremes).flatMap(([name, values]) =>
  values.map((value) => ({
    label: `multiconnect ${name}=${value}`,
    values: { mount_type: "multiconnect", [name]: value },
  })),
);
mcCases.push(
  {
    label: "multiconnect narrow-tall",
    values: {
      mount_type: "multiconnect", remote_w: 40, remote_h: 120,
      side_clearance: 0.2, wall: 1.6, plate_len_max: 300,
    },
  },
  {
    label: "multiconnect wide-short",
    values: {
      mount_type: "multiconnect", remote_w: 70, remote_h: 70,
      side_clearance: 1, wall: 4, plate_len_max: 60,
    },
  },
  {
    label: "multiconnect accepted square corner slot conflict",
    values: {
      mount_type: "multiconnect", remote_w: 44, side_clearance: 0.6,
      plate_len_max: 67, slot_tolerance: 1.075, on_ramp: true,
    },
  },
);

sweepModel("led_remote_holder_51x84mm", mcCases);
