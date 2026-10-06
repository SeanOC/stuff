# Porting published geometry

Use this recipe with [design-guidelines §8](design-guidelines.md#8-published-geometry-ports).
The policy and test seams below were checked at main `a5bdcb1`.

1. **Resolve the licence and the grant separately.** Follow the
   [vendored-source grant check](provenance.md#vendored-source-grant-check).
   Record the exact permitted file set, date and granter before committing
   any upstream original. No existing port grants permission to a new one.
   Keep files without a grant in the private mirror described by
   [reference/FETCH.md](../reference/FETCH.md).
2. **Stage the author source read-only.** Pin the original commit or SHA256;
   keep a pristine copy outside the implementation tree. With a source grant,
   vendor verbatim SCAD under root `assets/<name>/`, preserving its relative
   include layout. Keep render wrappers and compatibility patches separate.
   NOTICE records URL, author, licence, retrieval date, source hashes,
   parameters, patches, engine/library pins and reproducible commands. Follow
   [assets/openConnect/NOTICE](../../assets/openConnect/NOTICE),
   [assets/opengrid-snap/NOTICE](../../assets/opengrid-snap/NOTICE) (meshes and
   NOTICE only; no source grant), or
   [assets/openConnect-gridfinity-shelf/NOTICE](../../assets/openConnect-gridfinity-shelf/NOTICE).
3. **Render independent reference meshes.** Use OpenSCAD
   **2025.06.12.ai25773**, binary STL (`--export-format=binstl`), and the
   **BOSL2 pin in that port's NOTICE**. openConnect and the shelf need
   `b86a7584db6d324eb856c2d19d041f94435e6c32`; the snap uses `456fcd8` plus
   its recorded QuackWorks patch. Do not silently use the repo's older pin
   for a source requiring BOSL2 structs. Keep the author's default and
   endpoint overrides reproducible; record hashes of the committed renders.
   Reference meshes with redistribution grants live in root `assets/` with
   bucket mirrors, per [provenance](provenance.md#committed-reference-artefacts).
4. **Mayor pre-flight, before assigning the port.** Render the default and
   numeric endpoints, run the production audit and mount-contract probes on
   the reference geometry, and put the measured exception inventory into the
   spec. Do not send the worker to discover the policy by trial and error.
   Authority: *plan-spec-authoring-rules.md*, rules **7–9** (“Port pre-flight”,
   “Param domains for ports have THREE outcomes”, “Backing, parity and frames
   are stated, not discovered”). This is the Gas City workspace file
   `assets/docs/plan-spec-authoring-rules.md`, **outside this repository**;
   it is cited by name, not as a repository-relative link. Record file,
   ray/point and direction, value, face-family selector and enforcing test
   for each exception. Specify pass / named unbuildable-geometry error /
   published exception for every endpoint and documented corner; pin
   parameter-driven thinning at the midpoint too.
5. **Implement in a declared model frame and print frame.** Mount fixtures
   and backing probes use model coordinates. Audit, review and exports use
   the declared print transform, including parameter-dependent
   `ModelSpec.print_frame` in [holders/registry.py](../holders/registry.py).
   State the reference-to-port transform separately. Use library mounts
   unchanged. Define backing from the uncut body minus mandatory treatment,
   never the finished part; declare any narrower envelope in the inventory.
6. **Pin parity and exceptions before opening the PR.** The shared helper
   bead is `pst-97unr`, “tests: one shared parity helper (tests/parity.py)
   replacing the per-port copies in test_opengrid_snap / test_gridfinity_shelf
   / test_openconnect / test_cartridge_holder — same assertions, same
   numbers (retrospective D2b)”. Until it lands, use
   [test_gridfinity_shelf.py](../tests/test_gridfinity_shelf.py)::`test_reference_parity`
   as the template: transform explicitly, assert pre-treatment bbox and
   analytic finished reduction, compare volume and sampled surface distance
   in both directions, and report/cap reference-band coverage and excluded
   fractions. Apply the [§8 caps](design-guidelines.md#what-never-yields)
   without loosening them. Assert manifold port output, exact exception
   membership and measurements, no new misses, and endpoint/corner audits
   plus exposed-edge classification for every preset.
7. **Include the evidence in the PR body.** Use the following rows, with
   file/test locators so the reviewer can reproduce them. Keep the ordinary
   §6 review requirements, including preset volume before/after and reasons
   for increases. Run `uv run pytest tests/ -q` from `build123d/`; regenerate
   the manifest when models, presets or tags change. A missing reference
   measurement is blocking under checklist item 9.

| PR evidence | Required columns |
| --- | --- |
| Parity table | preset; transform; reference / pre-treatment / finished bbox; analytic reduction; reference / port volume; both maximum surface distances; band coverage / excluded fraction / caps; result |
| Audit and endpoint table | preset or endpoint/corner; minimum wall; worst overhang; measured local bridge span; exposed-edge angle and classifier; mount-contract result; pass / named error / exception row |
| Exception inventory | face family and selector; source file/lines and NOTICE pin; reference mesh, ray/point and direction, value; allowed parameter cases; enforcing test; result |
| Licence line | port SPDX licence; attribution/NOTICE; exact vendored file set and register grant; any share-alike/non-commercial scope |
