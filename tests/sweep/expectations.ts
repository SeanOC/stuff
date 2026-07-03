// Expected connected-component counts per model, as a function of the
// swept param values. Mirrors the topology claims in each model's
// invariants sidecar (models/<stem>.invariants.py) — keep the two in
// sync when a model's topology story changes.
//
// Most models are a single solid; entries here are only the exceptions.
// Returning null skips the component-count assert for that case (the
// render must still succeed and be watertight).

import type { ParamValue } from "@/lib/scad-params/parse";

type Values = Record<string, ParamValue>;
type Expectation = (values: Values) => number | null;

const EXCEPTIONS: Record<string, Expectation> = {
  // Sidecar: pod_gap > 0 separates the pods for slicer export; at
  // pod_gap == 0 the dovetailed pods form one connected assembly.
  goblu_filter_holder_3x90mm: (v) =>
    Number(v.pod_gap) > 0 ? Number(v.pod_count) : 1,

  // Sidecar: assembly view = one base + two caps.
  blu_black_tank_valve_mount: (v) => (v.part === "assembly" ? 3 : 1),

  // Sidecar pins assembly = 3 (base + two caps). assembly_with_meter
  // also renders 3 (observed): the meter dummy nests into the saddle
  // caps it rests in and merges with them rather than floating free.
  blu_flow_meter_mount_80mm: (v) =>
    v.part === "assembly" || v.part === "assembly_with_meter" ? 3 : 1,
};

export function expectedComponents(stem: string, values: Values): number | null {
  const fn = EXCEPTIONS[stem];
  return fn ? fn(values) : 1;
}
