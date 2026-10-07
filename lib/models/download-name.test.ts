import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import type { Param } from "../scad-params/parse";
import { parseScadParams } from "../scad-params/parse";
import { loadBdModel } from "./bd-manifest";
import { downloadFilename } from "./download-name";

const scad = (stem: string) =>
  parseScadParams(
    fs.readFileSync(path.join(process.cwd(), "models", `${stem}.scad`), "utf8"),
  ).params;

describe("downloadFilename", () => {
  it("includes capture-bin width and depth flags from the real manifest", async () => {
    const model = await loadBdModel("gridfinity-capture-bin");
    expect(model).not.toBeNull();
    expect(downloadFilename(model!.slug, model!.params, {})).toBe(
      "gridfinity-capture-bin-width_units=4-depth_units=1.stl",
    );
    expect(downloadFilename(model!.slug, model!.params, {
      size_mode: "manual", width_units: 4, depth_units: 2,
    }, "3mf")).toBe("gridfinity-capture-bin-width_units=4-depth_units=2.3mf");
  });

  it("includes Gridfinity width, depth and style from the real manifest", async () => {
    const model = await loadBdModel("openconnect-gridfinity-shelf");
    expect(model).not.toBeNull();
    expect(downloadFilename(model!.slug, model!.params, {
      gridfinity_width_grids: 4,
      gridfinity_depth_grids: 2,
      baseplate_style: "Magnet - All",
    })).toBe("openconnect-gridfinity-shelf-baseplate_style=magnet---all-gridfinity_width_grids=4-gridfinity_depth_grids=2.stl");
  });

  it("names the spool cradle after its mount style (real manifest)", async () => {
    const model = await loadBdModel("holder-spool-cradle");
    expect(model).not.toBeNull();
    const params = model!.params;
    expect(params.find((p) => p.name === "mount_style")?.filename).toBe(true);
    // Defaults are always included so the name is stable.
    expect(downloadFilename(model!.slug, params, {})).toBe(
      "holder-spool-cradle-channel.stl",
    );
    for (const style of ["channel", "points", "openconnect"]) {
      expect(downloadFilename(model!.slug, params, { mount_style: style })).toBe(
        `holder-spool-cradle-${style}.stl`,
      );
    }
  });

  it("keeps slug.stl for an unflagged build123d model", async () => {
    const model = await loadBdModel("holder-spray-can");
    expect(model!.params.some((p) => p.filename)).toBe(false);
    expect(downloadFilename(model!.slug, model!.params, { d: 70 })).toBe(
      "holder-spray-can.stl",
    );
  });

  it("keeps stem.stl for an unflagged SCAD model", () => {
    expect(downloadFilename("popcorn_kernel", scad("popcorn_kernel"), {})).toBe(
      "popcorn_kernel.stl",
    );
  });

  it("matches export-all's single-flag name for a SCAD model", () => {
    const params = scad("multiconnect_connectors");
    expect(downloadFilename("multiconnect_connectors", params, {})).toBe(
      "multiconnect_connectors-snap-regular.stl",
    );
    expect(
      downloadFilename("multiconnect_connectors", params, { connector_type: "pushfit" }),
    ).toBe("multiconnect_connectors-pushfit.stl");
  });

  it("matches export-all's k=v join for a multi-flag SCAD model", () => {
    const params = scad("ryobi_p2860_strap_saddle");
    expect(
      downloadFilename("ryobi_p2860_strap_saddle", params, { side: "left" }),
    ).toBe("ryobi_p2860_strap_saddle-side=left-mount_type=opengrid.stl");
  });

  it("keeps underscores in values (baked names keep them) and sanitises the rest", () => {
    const enumP: Param = {
      name: "part", kind: "enum", default: "cap_left",
      choices: ["cap_left", "A B/\"c\""], filename: true,
    };
    expect(downloadFilename("m", [enumP], {})).toBe("m-cap_left.stl");
    expect(downloadFilename("m", [enumP], { part: 'A B/"c"' })).toBe("m-a-b-c.stl");
  });

  it("prefixes a single numeric flag with its name, unit-free", () => {
    const num: Param = {
      name: "spool_width", kind: "number", default: 50, unit: "mm", filename: true,
    };
    expect(downloadFilename("s", [num], { spool_width: 62.5 })).toBe(
      "s-spool_width62.5.stl",
    );
  });
});
