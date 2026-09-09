import { sweepModel } from "./runner";

sweepModel("led_remote_holder_55x124mm", [{
  // pst-jvui: accepted square corners preserve the slot/on-ramp at
  // this audited conflict case; keep the shipped WASM preview viable.
  label: "multiconnect accepted square-corner slot conflict",
  values: {
    mount_type: "multiconnect",
    remote_w: 44.5,
    side_clearance: 0.45,
    wall: 2.4,
    remote_h: 124,
    plate_len_max: 67,
    slot_tolerance: 1.075,
    on_ramp: true,
  },
}]);
