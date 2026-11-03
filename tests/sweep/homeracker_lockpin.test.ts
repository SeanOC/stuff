import { checkHomeRackerPresets } from "./homeracker";
import { sweepModel } from "./runner";

sweepModel("homeracker_lockpin", [
  { label: "plate with largest grips and both necks", values: { grip: "extended", neck: "both", quantity: 20 } },
  { label: "gripless both necks slim", values: { grip: "none", neck: "both", strength: "slim" } },
]);

checkHomeRackerPresets("homeracker_lockpin");
