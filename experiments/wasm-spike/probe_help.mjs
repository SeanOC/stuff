import { createOpenSCAD } from "openscad-wasm-prebuilt";
const stderr = [];
const openscad = await createOpenSCAD({
  print: (s) => console.log("OUT:", s),
  printErr: (s) => stderr.push(s),
});
const inst = openscad.getInstance();
const rc = inst.callMain(["--help"]);
console.log("rc:", rc);
console.log("---stderr---");
console.log(stderr.join("\n"));
