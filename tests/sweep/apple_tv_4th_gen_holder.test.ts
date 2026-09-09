import { sweepModel } from "./runner";

sweepModel("apple_tv_4th_gen_holder", [
  ...Object.entries({
    device_w: [60, 140],
    device_h: [60, 140],
    fit_clearance: [0.3, 3],
    shelf_t: [2.5, 8],
    width_units: [4, 5, 6],
    height_units: [4, 5, 6],
    plate_t: [3, 6],
    slot_tolerance: [0.925, 1.075],
  }).flatMap(([name, values]) => values.map((value) => ({
    label: `multiconnect ${name}=${value}`,
    values: { mount_type: "multiconnect", [name]: value },
  }))),
  ...[[6, 6], [4, 6], [6, 4]].map(([width, height]) => ({
    label: `multiconnect aspect ${width}x${height}`,
    values: {
      mount_type: "multiconnect", width_units: width, height_units: height,
      device_w: 60, device_h: 60, slot_tolerance: 1.075,
    },
  })),
]);
