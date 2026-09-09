import { sweepModel } from "./runner";

// Exercise corner clipping with Multiconnect selected; the generic sweep
// varies one parameter from the openGrid default and cannot cover this.
sweepModel("ego_powerhead_mount", [
  ...[1, 3].map((ext_fillet) => ({
    label: `mc corner radius=${ext_fillet}`,
    values: { mount_type: "multiconnect", ext_fillet },
  })),
  ...[5.5, 8].map((backer_thickness) => ({
    label: `mc slab thickness=${backer_thickness}`,
    values: { mount_type: "multiconnect", backer_thickness },
  })),
  { label: "mc largest corners, widest slots, thinnest slab",
    values: { mount_type: "multiconnect", ext_fillet: 3,
      slot_tolerance: 1.075, backer_thickness: 5.5 } },
  { label: "mc on-ramp closest to largest corner",
    values: { mount_type: "multiconnect", ext_fillet: 3, slot_tolerance: 1.005 } },
]);
