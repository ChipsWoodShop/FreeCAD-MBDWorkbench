# FreeCAD MBD Workbench Project Plan

## Progress Dashboard

This dashboard is a planning snapshot, not an automated metric. Progress bars
use this convention: `Done`/`Passed` count as complete, `In progress`/`Ongoing`
/`Partial` count as partial progress, and `Future`/`Deferred`/`Not started`
remain open. When any item status changes in this plan, update this dashboard
in the same edit so the top-level summary stays current.

| Section | Progress | Status | Notes |
| --- | --- | --- | --- |
| Overall project roadmap | `[########--] 80%` | In progress | Semantic definition/export is mature; AP242 semantic import now creates datums, datum systems, datum targets, dimensions, exporter-safe native FCFs, and preserves imported multi-face datum/FCF bindings where the native/export path is safe. |
| Current semantic-export phase | `[#########-] 86%` | Mostly complete | Core datum, FCF, dimension, datum-target, validation, and AP242 semantic export workflows are working; remaining work is mostly edge cases and richer AP242 variants clarified by the v4.1 practices. |
| Completed Work Archive | `[##########] 100%` | Done/history | Completed milestones, roadmap records, regression goals, and passed GUI tests are archived at the bottom. |
| Active Implementation Priorities | `[#####-----] 45%` | Active queue | This is the live next-work queue below; completed items should be moved into their applicable roadmap/test sections rather than retained here. |
| Implementation Roadmap Details | `[#########-] 85%` | Mostly done | Core semantic export is broad; maximum tolerance, unit-basis tolerance, non-uniform profile zones, scoped datum target shapes, imported multi-face bindings, first-pass AP242 semantic import, and first-pass AP242 annotation placeholders are working. Remaining gaps are mostly explicit future workflows: path dimensions, richer zone geometry, exact presentation graphics, and derived/path semantics. |
| AP242 PMI Coverage Matrix | `[########--] 75%` | Partial | Many AP242 concepts are done or partially covered; the v4.1 review added more explicit tracking for placeholders, affected planes, non-uniform zones, and composite tolerances. |
| Annotation Architecture | `[##########] 100%` | Done | Single-item view-provider architecture and direct annotation movement are in place; details are archived at the bottom. |
| Import Roadmap | `[#########-] 97%` | In progress | Lightweight inspection/warning exists; semantic import preview and native datum/datum-system/placed-target/dimension import exist. Imported dimensions now read AP242 nominal and plus/minus tolerance values with per-measure unit scaling, and native import records AP242 source ids on created PMI. One-face and safe multi-face Flatness/Profile/LineProfile/Position/Parallelism/Perpendicularity/Angularity plus one-face Straightness/Circularity/Cylindricity/CircularRunout/TotalRunout imports can re-export through post-write AP242 tolerance entities. Supported modifier-rich imported FCFs parse and re-export material condition, tangent plane, statistical tolerance, common zone, projected zone height, unequal disposition, maximum tolerance, unit basis, non-uniform zone, edge-resolved affected-plane values, and runout orientation angles when the native validation/export path is safe. Broader derived-axis/path and unsupported modifier combinations remain preview-only. The NIST AP242 preview sweep now resolves all recognized datums, datum systems, dimensions, FCFs, and relationships in the current sample folder; the only native-ready count gap is four FTC10 area datum targets, which are intentionally out of scope. Headless FreeCADCmd import/export smoke passes for target-backed NIST CTC05, mixed-unit NIST CTC03, multi-attachment and MMC orientation NIST FTC08, and project `MBDTest01_BT.step` with no null semantic references. |
| Open GUI Requests | `[#########-] 92%` | Visual tests pending | Most GUI tests are passed and archived below; remaining open items are visual annotation checks. |
| Addon Publication Readiness | `[#######---] 70%` | In progress | FreeCAD Addon Manager/GitHub publication requirements have been captured below, the workbench code now uses a namespaced `freecad/mbd_workbench` layout, first-pass release artifacts exist, package metadata has a repeatable validator, and clean-profile FreeCAD package-layout smoke passes. Remaining work is Addon Manager Developer Mode validation, true clone/install testing, repository topics, release/tag workflow, and Addon Index submission. |
| Cosmetic Final Touches | `[###-------] 30%` | Future/Ongoing | Icons are wired and maintainability cleanup has started; ASME-style annotation polish remains intentionally late-stage. |

## Active Implementation Priorities

This is the live priority queue. Completed work should be recorded in the
applicable roadmap, coverage, regression, or GUI-test section and removed from
this queue so it always answers: "What should we implement next?"

| Priority | Workstream | Status | Notes |
| --- | --- | --- | --- |
| 1 | Finish FCF modifier and richer tolerance-zone coverage | Mostly done | MMC/LMC, projected tolerance zone, tangent plane, statistical tolerance, common tolerance, maximum tolerance, unit basis, non-uniform zone, unequally disposed profile, affected plane, and runout orientation are modeled and exported where the native/export path is safe. One-face imported runout FCFs now create and re-export when their controlled topology validates. Remaining work is broader AP242 zone geometry, richer projected-zone projection-end semantics, and known derived/path edge cases. |
| 2 | Improve rectangular datum target placement workflow | Future | Point, line, circle, and rectangle targets work. Arbitrary/freeform area targets are out of scope unless a concrete standards/customer need appears. Rectangles need a better surface-local definition workflow, likely point plus dimensions plus explicit in-plane orientation. |
| 3 | Decide and implement path-defined dimensions | Future | AP242 supports size/location with path. Do not expose this until there is a clear user workflow for selecting and storing a measurement path. |
| 4 | Continue AP242 semantic PMI import | Mostly done | Preview and native creation are implemented for datums, datum systems, scoped datum targets, dimensions, and exporter-safe FCFs, including safe multi-face datum and FCF controls. The NIST preview sweep resolves all recognized PMI candidate counts except intentionally out-of-scope area targets. Next work is richer derived-axis/path semantics and unsupported modifier combinations listed in the Import Roadmap. |
| 5 | Export AP242 visible annotation/presentation PMI | Partial | First-pass `ANNOTATION_PLACEHOLDER_OCCURRENCE` export is implemented as lightweight presentation/layout hints with semantic links where datums and FCFs can be resolved. Exact leader-line placeholders, dimension curves, arrows, frames, text runs, and full graphic presentation remain future work. |
| 6 | Cosmetic annotation and interaction polish | Future/Ongoing | Improve ASME-style placement/readability and more natural drag interaction after semantic/export work is stable. |
| 7 | Prepare GitHub/Add-on Manager publication package | Future | Create and validate FreeCAD addon metadata, repository documentation, license files, dependency declarations, and release-quality installation checks before submitting to the FreeCAD Addon Index. |

### Open Decisions

These are the places where implementation should pause for product/standards
direction rather than guessing.

| Decision Area | Needed Decision | Why It Blocks |
| --- | --- | --- |
| None | No open product/standards decisions at this time. | Continue through the active priorities until a GUI test or standards choice is needed. |

## Open GUI Requests

Use this short table for manual FreeCAD checks that still need action. Move rows
to the completed GUI archive after results are reported.

| Test Case | Result | Notes |
| --- | --- | --- |
| Runout orientation angle FCF | Needs retest | Create circular or total runout on a revolved feature with an axis-capable datum and enter a nonzero orientation angle such as `30`. Confirm the FCF borrows the matching diameter dimension's annotation plane, so the FCF, datum-axis diameter callout, datum symbol, runout leader, and angle arc/arrowheads/degree text are all coplanar. Existing saved runout FCFs should also draw in that diameter plane after rebuild/reopen. Confirm there is an explicit leader from the FCF to the controlled surface, and that the entered orientation angle defines the surface-leader ray from the referenced datum axis. The angle arc should be centered where that surface leader intersects the referenced datum axis, spanning only between the datum-axis direction and the surface-leader direction. AP242 export should preserve the runout FCF and, where OCCT emits `RUNOUT_ZONE_ORIENTATION`, write the entered angle rather than zero. |
| Hole datum feature on diameter dimension | Needs retest | Create a diameter dimension on a cylindrical/hole face, then create a datum feature on the same cylindrical face. With no FCF on that diameter, confirm the datum letter appears as a boxed datum identifier below the diameter text, directly against the feature-side diameter leader/extension line in the diameter annotation plane. Then add an FCF controlled by the same diameter and confirm a datum triangle sits where the datum leader meets the FCF frame, with the datum box connected below the triangle as in ASME Y14.5 internal-diameter examples, rather than appearing at the far end of the dimension/FCF row. |

## Implementation Roadmap Details

### Remaining Feature Implementation Order

| Order | Workstream | Status | Notes |
| --- | --- | --- | --- |
| 1 | Angular semantic dimensions | Done | Two-reference angular dimension creation, validation, degree-symbol display, and AP242 post-write angular export passed GUI testing for face-backed references. Richer edge/axis cases remain future refinements. |
| 2 | Point, line, circular, and rectangular datum targets | Mostly done | Point, line, circular, and rectangular target areas are implemented and passed GUI export testing. Per CAx-IF AP242 recommended practices, circle uses `target diameter`, rectangle uses `target length` along placement X and `target width` along derived Y, and placement Z is the outward datum-surface normal. Arbitrary/freeform area targets are out of scope for now. Rectangular target orientation is currently inferred from the datum plane frame; explicit user-controlled in-plane orientation remains future work. |
| 3 | FCF modifiers and richer tolerance zones | Mostly done | MMC/LMC material-condition modifiers, projected tolerance zone, tangent plane, statistical tolerance, common tolerance `CT`, maximum tolerance value, unit-basis tolerance, non-uniform zone, unequally disposed profile, affected-plane association, and runout orientation angle fields now exist in the FreeCAD model. MMC/LMC, tangent plane, statistical tolerance, and common tolerance export through AP242 `GEOMETRIC_TOLERANCE_WITH_MODIFIERS`; projected-zone height exports through `PROJECTED_ZONE_DEFINITION`; unequal disposition exports through `UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE`; maximum tolerance exports through `GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE`; unit-basis tolerances export through `GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT` and `GEOMETRIC_TOLERANCE_WITH_DEFINED_AREA_UNIT`; non-uniform profile zones export through `NON_UNIFORM_ZONE_DEFINITION`; affected planes export/import through edge-resolved `SHAPE_ASPECT_RELATIONSHIP('affected plane association', ...)`; runout orientation patches existing AP242 `RUNOUT_ZONE_ORIENTATION` angle values and is parsed during import preview. Remaining future work is richer zone geometry, richer projected-zone projection-end semantics, and multiple edge-backed line-profile mapping. |
| 4 | Path-defined dimensions | Future | CAx-IF AP242 practice defines path dimensions as specialized size/location subtypes with an additional `path` attribute pointing to a path `shape_aspect`. Add `DIMENSIONAL_SIZE_WITH_PATH` and `DIMENSIONAL_LOCATION_WITH_PATH` only after normal size/location dimensions and target areas are stable and after we have a user workflow for selecting/storing the measurement path. |
| 5 | AP242 presentation PMI export | Partial | First-pass `ANNOTATION_PLACEHOLDER_OCCURRENCE` export writes one placeholder per native datum, datum target, dimension, and FCF using stored annotation origin/text-height/layout metadata. It emits a draughting model and links placeholders to semantic datum/FCF entities when they can be resolved without guessing. Exact leader-line placeholders, dimension curves, arrows, frames, text runs, and graphic presentation remain future work. |
| 6 | AP242 semantic PMI import | Mostly done | `Inspect AP242 PMI` now appends a semantic import preview. The preview parses STEP entities, recognizes native-ready datums, datum systems, point/line/circle/rectangle datum targets, supported dimensions, supported FCFs, records limitations for deferred/partial concepts, and maps AP242 geometry item ids to tentative Face/Edge names. Conservative native creation exists for datums, datum systems, datum targets, dimensions, and exporter-safe FCFs, including multi-face datum bindings and multi-face controls for the FCF families whose native validation/export path is safe. |

### Future Rectangular Datum Target Placement Workflow

Point, line, circle, and rectangle cover the datum target shapes currently in
scope. Arbitrary/freeform area targets are intentionally out of scope unless a
specific standards/customer example makes them necessary later.

Rectangular datum targets need a better user workflow because their in-plane
orientation is meaningful. Intended workflow:

1. User selects an existing MBD datum feature and a datum point on that feature.
2. User chooses `Rectangle` in the datum target command.
3. The dialog asks for length, width, and orientation.
4. Orientation can initially be an angle in the datum feature's local surface
   frame; a later refinement could allow selecting a datum line or model edge
   on the surface as the rectangle X direction.
5. The workbench validates that the rectangle lies on the datum feature surface.
6. The view provider displays the rectangle target area, leader, and target
   identifier on the datum surface.
7. AP242 export writes `target length`, `target width`, and placement axes so
   the rectangle's orientation is explicit instead of inferred.

## Addon Publication Readiness

The direct `https://wiki.freecad.org/Package_Metadata` page was protected by
Anubis during automated browsing, but a local saved copy exists at
`docs/Package Metadata - FreeCAD Documentation.mhtml` and was reviewed. The
saved page metadata shows it was saved from `https://wiki.freecad.org/Package_Metadata`
on 2026-08-02 and the wiki page reports a 2026-04-24 modification date. Before
publication, manually re-open the wiki page in a browser and reconcile this
checklist against the current official page.

### Required Release Artifacts

| Item | Status | Requirement / Action |
| --- | --- | --- |
| `package.xml` manifest | Done | Added a well-formed XML 1.0 manifest named exactly `package.xml` in the repository base directory, using `<package format="1" xmlns="https://wiki.freecad.org/Package_Metadata">` as the root element. |
| Required manifest tags | Done | The manifest includes `<name>`, `<version>`, `<date>`, `<description>`, `<maintainer>`, `<license>`, `<icon>`, and `<content>`. |
| Package name | Done | Uses filename-safe package name `MBDWorkbench`. |
| Package version | Resolved | Use Semantic Versioning with initial version `<version>0.1.0</version>`. Treat `0.x` as public-preview API/schema territory; reserve `1.0.0` for stable saved-document compatibility and mature AP242 workflows. |
| Package date | Done | Manifest date is `2026-08-02` in `YYYY-MM-DD` format. |
| Description | Done | Manifest contains a concise Addon Manager description. |
| Maintainer | Resolved | Use `<maintainer email="Chip@chipswoodshop.com">Chip</maintainer>`. If the package becomes orphaned, the wiki uses `<maintainer email="no-one@freecad.org">No current maintainer</maintainer>`. |
| License file | Done | Added `LICENSE` using LGPL-2.1 text and set `<license file="LICENSE">LGPL-2.1-only</license>` in `package.xml`. |
| README | Done | Added user-facing `README.md` with install/use instructions, FreeCAD/Python support, AP242 scope, known limitations, testing, privacy, issue reporting, and license notes. |
| Top-level icon | Done | Manifest points to `freecad/mbd_workbench/mbd_command_icons/create_datum_feature.svg` with `/` separators. |
| Workbench content metadata | Done | Manifest includes a `<content>` section with one `<workbench>` child, name, version, description, subdirectory, classname, and icon. |
| Workbench classname | Resolved | Use `<classname>MBDWorkbench</classname>` to match `freecad/mbd_workbench/InitGui.py`. Root `InitGui.py` remains only as a FreeCAD Mod-directory registration shim. |
| Workbench subdirectory | Done | Source modules and command icons live under `freecad/mbd_workbench/`; `package.xml` uses `<subdirectory>./</subdirectory>` so FreeCAD discovers the root `Init.py` and `InitGui.py` shims. |
| Repository URL and branch metadata | Resolved | Use `<url type="repository" branch="main">https://github.com/ChipsWoodShop/FreeCAD-MBDWorkbench</url>`. |
| Stable indexed branch | Resolved for preview | The first preview manifest points Addon Index metadata at `main`. Revisit a long-lived `stable`/`release` branch before a compatibility-focused `1.0.0` release. |
| README URL | Done | Manifest includes a GitHub README URL. |
| Additional URLs | Done | Manifest includes repository and bugtracker URLs. Add documentation/discussion URLs later if dedicated pages are created. |
| Dependency declaration | Done | No external Python or addon dependencies are currently required, so no `<depend>` entries are declared. |
| Python dependency policy | Done | README states that no external Python package dependencies are required. |
| FreeCAD compatibility | Done | Manifest declares `<freecadmin>1.1.0</freecadmin>`. |
| Python compatibility | Done | Manifest declares `<pythonmin>3.11</pythonmin>`. |
| Tags | Done | Manifest includes `MBD`, `PMI`, `GD&T`, `AP242`, `STEP`, and `manufacturing` tags. |
| Conflict / replacement metadata | Not checked | Add `<conflict>` only for packages that should not be installed at the same time, and `<replace>` only if this package replaces another addon. These support the same version/condition attributes as dependencies. |
| Author metadata | Optional | Add `<author email="...">...</author>` entries if there are authors distinct from maintainers; email is optional for authors. |
| File entries | Optional | Use `<file>` only if another tool or content item needs explicit file listing. It is mainly useful for macro content. |
| GitHub repository hygiene | Partial | `.gitignore` excludes local PDFs, FreeCAD documents, STEP exports, screenshots, and generated caches; `CONTRIBUTING.md` and GitHub issue templates now exist. Remaining work is repository cleanup review after the migration commit, pushed history, and release tags. |
| GitHub topics | Missing | Add at least the `freecad` and `addon` repository topics before submitting to the Addon Index. Add project-specific topics such as `mbd`, `pmi`, `gdandt`, `ap242`, or `step` if useful. |

### Addon Index Quality Requirements

| Area | Status | Requirement / Action |
| --- | --- | --- |
| Maintainer / governance | Mostly done | Manifest and README identify Chip as maintainer, README points users to GitHub Issues, `CONTRIBUTING.md` defines reporting and PR guidance, and bug/feature issue templates exist. |
| Privacy / external connections | Done | README documents that the workbench is intended to run locally and does not intentionally perform network access or send model data to external services. |
| Security handling | Done | Added `SECURITY.md` with private reporting guidance and scope notes. |
| Python 3 / FreeCAD APIs | Mostly done | Workbench is Python 3 code and uses FreeCAD/PySide/pivy APIs. No external Python package dependencies are declared. Final release should still get a real FreeCAD Addon Manager smoke pass. |
| Startup behavior | Mostly done | Static audit found no network libraries, subprocess calls, AP242 parsing, or export work at import/registration time. Workbench activation only organizes existing PMI tree objects in the active document; watch this if very large documents show activation delay. |
| UI containment | Done | Commands are registered under the MBD workbench toolbar/menu, and no preferences or global FreeCAD behavior changes are added by the release artifacts. |
| Namespacing / layout | Done | Workbench source now lives under `freecad/mbd_workbench/`; root `Init.py` and `InitGui.py` are thin FreeCAD discovery shims. Python imports and tests were updated to use `freecad.mbd_workbench`. |
| Manifest validation | Mostly done | Added `tests/validate_package_metadata.py`; it checks XML well-formedness, required tags, version/date format, maintainer email, referenced files/paths, workbench metadata, URLs, and release artifacts. Still needs Addon Manager Developer Mode validation before submission. |
| Clean install test | Partial | Clean-profile FreeCAD package-layout smoke passes using isolated `/tmp/mbd-freecad-cli` config/cache paths. True install-from-GitHub clone, activation, smoke commands, and uninstall remain to run after the migration/release artifacts are committed and pushed. |
| Pre-submission user testing | Not started | Addon Academy recommends asking a small set of users to test before submission, for example through FreeCAD Discord, Forum, Reddit, or direct project contacts. Mark proof-of-concept/work-in-progress status clearly if submitting before full maturity. |
| Release packaging test | Not started | After Addon Index review compliance, make a new release/tag and verify Addon Manager/cache-style discovery can read the manifest, icon, version, description, and branch metadata. |
| Addon Index submission | Not started | Once the addon is public, compliant, and basically functional, request indexing by opening an `Addon - Addition` issue on the GitHub Addon Index, opening the equivalent Codeberg mirror issue, or posting a request on the FreeCAD Addons forum. Expect a review loop before acceptance. |

### Publication Sources To Recheck

- `docs/Package Metadata - FreeCAD Documentation.mhtml`: local saved copy of the official package metadata page reviewed for the checklist above.
- `https://wiki.freecad.org/Package_Metadata`: official package metadata page; direct automated access was blocked during this review, but the local saved copy should be manually refreshed before publication.
- `https://freecad.github.io/Addon-Academy/Guides/Publishing/Indexed`: FreeCAD Addon Academy guide for publishing through the Addon Index. It adds maintenance expectations, pre-submission testing, `freecad`/`addon` repository topics, submission channels, review flow, and release/tag timing.
- `https://freecad.github.io/Addon-Academy/Topics/Addon-Index/Index/Qualities`: FreeCAD Addon Index quality requirements.
- `https://freecad.github.io/SourceDoc/db/dfe/classApp_1_1Metadata.html`: FreeCAD source documentation for metadata fields such as name, version, description, maintainer, license, dependency, content, classname, icon, url, FreeCAD version limits, and arbitrary tags.
- FreeCAD workbench distribution guidance: Addon Manager install requires package metadata and can use metadata to describe icons, descriptions, version numbers, dependencies, conflicts, and replacements.

## Reference Sources

- `rec_pracs_pmi_v41.pdf`: CAx-IF Recommended Practices for the Representation and Presentation of Product Manufacturing Information (PMI) (AP242), Version 4.1, June 20, 2024. This supersedes the earlier v4.0 reference for semantic PMI, datum target parameterization, projected zones, unequally disposed tolerances, dimension-with-path entities, and future presentation PMI.

### AP242 v4.1 Findings Relevant To Open Decisions

| Topic | v4.1 clarification | Project impact |
| --- | --- | --- |
| Datum targets | Point, line, circle, circular curve, and rectangle are implicit placed target types using `PLACED_DATUM_TARGET_FEATURE`, `axis2_placement_3d`, and size parameters such as `target length`, `target width`, and `target diameter`. Area and curve targets are explicit geometry. | Confirms the current point/line/circle/rectangle path. Arbitrary/freeform area targets are out of scope for now. |
| Rectangular target orientation | Rectangle target length is along placement X, width is along derived Y, and placement Z is the outward surface normal. | Current inferred datum-plane frame is acceptable as a first implementation; explicit in-plane rotation remains a future UI refinement. |
| Movable datum targets | A `direction` entity with `direction.name = 'movable direction'` marks target mobility. | Add movable targets only after normal target area workflows are complete. |
| Shape aspect reuse | The `shape_aspect`, `geometric_item_specific_usage`, and represented geometry combination should be unique and reused when multiple PMI items reference the same topology. | Export/import should continue moving toward reusable semantic feature handles rather than one-off duplicate shape aspects. |
| Projected zones | `PROJECTED_ZONE_DEFINITION` stores projected length and a `projection_end` feature, often the planar face intersecting a cylindrical hole. | Current projected-height export is useful but should eventually map the projection-origin feature more explicitly. |
| Runout zones | Runout uses `RUNOUT_ZONE_DEFINITION` plus `RUNOUT_ZONE_ORIENTATION` with an angular orientation. | User-entered runout orientation angle is now stored on runout FCFs, displayed with a centerline/angle cue, and exported by patching the AP242 `PLANE_ANGLE_MEASURE_WITH_UNIT` referenced by `RUNOUT_ZONE_ORIENTATION` when OCCT emits the base runout-zone entities. Import preview now parses the referenced angle value, but native runout FCF creation remains deferred until the runout family export path is safe. |
| Affected planes | Affected/intersection planes are represented through a shape-aspect relationship whose description is `affected plane association`; an `axis2_placement_3d` may represent the plane element. | The FCF command can now store a controlled face plus selected datum line/edge as an affected-plane definition; AP242 export emits a conservative `SHAPE_ASPECT_RELATIONSHIP('affected plane association', ...)` for face-backed mapped cases. Import preview resolves edge-backed affected-plane relationships and native FCF creation stores them when exactly one edge is resolved. |
| Non-uniform zones | `NON_UNIFORM_ZONE_DEFINITION` references a `TOLERANCE_ZONE`. | Modeled/displayed/validated in FreeCAD for profile tolerances; AP242 post-write export now emits `NON_UNIFORM_ZONE_DEFINITION`, creating a `TOLERANCE_ZONE` when OCCT did not write one. |
| Maximum tolerance | `GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE` applies when another modifier, including MMC or LMC, can otherwise increase the effective tolerance; it stores `maximum_upper_tolerance`. | Modeled/displayed/validated in FreeCAD; AP242 post-write export now patches the controlled tolerance with `GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE`. |
| Unit-basis tolerance | Length unit basis uses `GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT.unit_size`; area basis adds `area_type` and `second_unit_size`. | Modeled/displayed/validated in FreeCAD for length, circular, rectangular, and square unit-basis cases; AP242 post-write export now emits defined-unit and defined-area-unit tolerance subtypes for face-backed FCFs. |
| Composite tolerances | Multiple FCF frames are separate geometric tolerances related by `GEOMETRIC_TOLERANCE_RELATIONSHIP('composite', ...)`. | Composite FCFs should be a new semantic object/workflow, not a formatting trick inside one FCF row. |
| Presentation PMI | CAx-IF puts character-based presentation on hold; AP242 Edition 3 adds `ANNOTATION_PLACEHOLDER_OCCURRENCE`, with leader-line variants and links to semantic PMI. | First-pass placeholder export is implemented. Future work should add leader-line placeholders and richer graphic/tessellated presentation after annotation routing is stable. |

## Architecture Boundary

FreeCAD is responsible for:

- topology generation
- topology naming
- shape recomputation
- model editing

The MBD workbench is responsible for:

- semantic PMI definition
- attachment validation
- export integrity checking
- AP242 semantic mapping
- user warning and repair workflow

Do not auto-reassign PMI attachments when topology changes. Store geometry
signatures, validate them before export, warn the user, and allow export
cancellation.

## Current Status

The workbench can define and display:

- datum features
- datum systems
- datum targets
- standard and basic dimensions
- feature control frames for position, flatness, parallelism,
  perpendicularity, profile, angularity, straightness, circularity,
  cylindricity, circular runout, total runout, and profile of a line
- drawn GD&T symbols for visible annotation display

The AP242 exporter currently writes:

- body shape geometry
- semantic datum features
- semantic FCFs for position, flatness, parallelism, perpendicularity,
  surface profile, line profile, angularity, straightness,
  circularity/roundness, cylindricity, circular runout, and total runout
- datum references for supported datum-referenced FCFs

Semantic point, line, circular, and rectangular datum targets are modeled in
FreeCAD and export as AP242 placed datum target features. Semantic dimensions
export for diameter, radius, plane-to-plane thickness, linear feature-location,
and face-backed angular cases.

## Important Implementation Notes

- `MBDExporter.py` uses XCAF/AP242 semantic entities for datums and position
  tolerances.
- Keep the direct `TDataStd_Integer` and `TDataStd_Real` child-label workaround
  for geometric tolerances unless a replacement is verified against pythonocc
  and OCCT.
- Current visible PMI is FreeCAD-side view-provider geometry, not AP242
  presentation PMI.
- STEP validation should use STEP text/entity checks and headless FreeCAD
  tests, not GUI viewer appearance alone.
- The nominal CAD model is treated as basic geometry unless explicitly
  overridden by semantic dimensions or tolerances. FCFs do not carry basic
  dimensions inside the FCF; required basic size, location, or angle values
  should be modeled as separate semantic dimensions or inferred from nominal
  geometry when a profile or other FCF controls the feature.
- Datum-target locations are nominal model geometry and are basic by default.
  Do not generate a separate set of target-location dimensions automatically.
  When an explicit displayed or exported dimension is needed, create it with
  the unified `Create Dimension` tool and select the Basic purpose.

## AP242 PMI Coverage Matrix

Source for this matrix: local OCCT AP242/STEP support in `RWStepAP214_ReadWriteModule.cxx`, `StepDimTol`, and `StepShape`, cross-checked against `rec_pracs_pmi_v41.pdf`. Status separates whether the add-on can define the concept in the FreeCAD model from whether it writes the corresponding semantic AP242 STEP entity.

### Geometric Tolerances

| AP242 entity | GD&T concept | FreeCAD model status | AP242 export status | Notes |
| --- | --- | --- | --- | --- |
| `POSITION_TOLERANCE` | Position | Done | Done | Supports datum system references and diameter tolerance zone. |
| `FLATNESS_TOLERANCE` | Flatness | Done | Done | Surface FCF with no datum reference. |
| `PARALLELISM_TOLERANCE` | Parallelism | Done | Done | One datum-reference feature supported. |
| `PERPENDICULARITY_TOLERANCE` | Perpendicularity | Done | Done | One datum-reference feature supported. |
| `SURFACE_PROFILE_TOLERANCE` | Profile of a surface | Done | Done | Face-level and all-over profile modeled; all-over export currently targets the exported face set. |
| `LINE_PROFILE_TOLERANCE` | Profile of a line | Partial | Done | Edge-attached line profile and ASME-style face-plus-direction-line profile are modeled, validated, and displayed with the profile-of-line symbol. AP242 export writes the line-profile tolerance on the controlled edge/face; exporting the stored section direction line as richer AP242 section semantics remains future work. |
| `ANGULARITY_TOLERANCE` | Angularity | Partial | Done | Conservative validation requires planar or axis-capable controlled geometry and a plane/axis-capable datum reference. The nominal basic angle belongs in a separate basic/angular dimension, not in the FCF. |
| `STRAIGHTNESS_TOLERANCE` | Straightness | Partial | Done | Conservative validation now accepts line-like, cylindrical, or conical controlled geometry and rejects obvious planar misuse; future work is distinguishing surface-element straightness from derived-axis straightness. |
| `ROUNDNESS_TOLERANCE` | Circularity / roundness | Done | Done | UI uses Circularity; AP242 writes `ROUNDNESS_TOLERANCE`; conservative validation requires circular or revolved controlled geometry. |
| `CYLINDRICITY_TOLERANCE` | Cylindricity | Done | Done | Validation now requires a cylindrical controlled face; display and AP242 export are in place. |
| `CIRCULAR_RUNOUT_TOLERANCE` | Circular runout | Partial | Done | Conservative validation requires a surface of revolution and either an axis-capable datum reference or a datum system containing an axis-capable datum. Future work is richer derived-axis/common-datum semantics. |
| `TOTAL_RUNOUT_TOLERANCE` | Total runout | Partial | Done | Conservative validation requires a surface of revolution and either an axis-capable datum reference or a datum system containing an axis-capable datum. Future work is richer derived-axis/common-datum semantics and full-surface scope refinement. |
| `COAXIALITY_TOLERANCE` | Coaxiality | Do not implement | Do not implement | AP242 supports it; ASME Y14.5-2018 does not include it. |
| `CONCENTRICITY_TOLERANCE` | Concentricity | Do not implement  | Do not implement  | AP242 supports it; ASME Y14.5-2018 removed it. |
| `SYMMETRY_TOLERANCE` | Symmetry | Do not implement | Do not implement  | AP242 supports it; ASME Y14.5-2018 removed it. |

### Datum And Datum Target Structure

| AP242 entity | Concept | FreeCAD model status | AP242 export status | Notes |
| --- | --- | --- | --- | --- |
| `DATUM_FEATURE` | Datum feature attachment | Done | Done | Whole-face datum feature export is working. |
| `DATUM` | Datum identifier | Done | Done | Datum labels A/B/C etc. export. |
| `DATUM_SYSTEM` | Ordered datum reference frame | Done | Done | Supports one to three ordered compartments, including primary-only systems and mixed individual/common datum systems. |
| `DATUM_REFERENCE_ELEMENT` | Individual datum reference | Done | Done | Exported for position and other datum-referenced FCFs. |
| `DATUM_REFERENCE_COMPARTMENT` | Datum reference compartment | Done | Done | Each primary/secondary/tertiary compartment may contain one datum or a common datum group. |
| `DATUM_REFERENCE` | Datum reference select/entity family | Partial | Partial | Covered through OCCT datum system export path, not directly modeled as a standalone object. |
| `COMMON_DATUM` | Common datum | Done | Done | Multiple datums selected in one compartment display as `A-B` and export through AP242 `COMMON_DATUM_LIST` with `DATUM_REFERENCE_ELEMENT` members. |
| `GENERAL_DATUM_REFERENCE` | General datum reference | Partial | Partial | Individual and common datum references are modeled through datum-system compartments; advanced modifiers and richer general-reference semantics remain future work. |
| `DATUM_TARGET` | Datum target | Done | Done | Scoped implementation covers point, line, circle, and rectangle targets using the CAx-IF AP242 descriptions `point`, `line`, `circle`, and `rectangle`. Arbitrary/freeform area targets are intentionally out of scope for now. |
| `PLACED_DATUM_TARGET_FEATURE` | Placed target feature | Done | Done | Point, line, circle, and rectangle targets export with placement and size parameters where applicable: `target length`, `target width`, and `target diameter`. Future rectangle work is explicit in-plane orientation UI, not a semantic export blocker. |
| `FEATURE_FOR_DATUM_TARGET_RELATIONSHIP` | Target-to-feature relationship | Done | Done | Exported for scoped point, line, circle, and rectangle datum targets to connect each target feature to the inspected datum feature. |

### Dimensions And Size/Location Controls

| AP242 entity | Dimension concept | FreeCAD model status | AP242 export status | Notes |
| --- | --- | --- | --- | --- |
| `DIMENSIONAL_SIZE` | Feature size such as diameter, radius, width, thickness | Partial | Partial | Diameter, radius, and plane-to-plane thickness dimensions validate and export as AP242 `DIMENSIONAL_SIZE`. Path-defined size remains a separate future entity family. |
| `DIMENSIONAL_SIZE_WITH_PATH` | Size with path | Not started | Not started | Needs a user-selected path shape aspect for measurements that follow a curve/surface path instead of the shortest straight-line distance. |
| `DIMENSIONAL_LOCATION` | Location between features | Partial | Partial | Axis/plane/point location dimensions exist. Direct OCCT export produced a null second shape reference, so the exporter now appends a narrow face-backed AP242 `DIMENSIONAL_LOCATION` entity set after STEP write. GUI exports `MBDTest01_AN.step`, `MBDTest01_AP.step`, and `MBDTest01_AR.step` created location dimensions with no null references. Plane-to-plane size is handled separately as thickness. |
| `DIRECTED_DIMENSIONAL_LOCATION` | Directed linear location | Partial | Partial | Treat as an exporter-side AP242 representation choice, not a user-facing dimension mode. The workbench should continue letting users define the meaningful model dimension; the exporter may choose `DIRECTED_DIMENSIONAL_LOCATION` when the semantic dimension and AP242 mapping require it. |
| `DIMENSIONAL_LOCATION_WITH_PATH` | Location with path | Not started | Not started | Needs a user-selected path shape aspect for path-dependent locations; do not expose as a separate user mode until a real path-selection workflow exists. |
| `ANGULAR_SIZE` | Angular size | Partial | Partial | Angular dimension model exists and can infer nominal angles from planes/axes. AP242 export is initially available for face-backed references; GUI angular-size workflow and richer edge/axis export mapping remain. |
| `ANGULAR_LOCATION` | Angular location | Partial | Partial | Angular dimensions are defined separately from FCFs and export through a post-write AP242 angular entity path for face-backed references. GUI testing passed for a planar-face case; richer edge/axis reference mapping remains. |
| `SHAPE_DIMENSION_REPRESENTATION` | Dimension value representation | Done | Done | Exported for supported size and location dimensions and covered by STEP text regression. |
| `DIMENSIONAL_CHARACTERISTIC_REPRESENTATION` | Link from dimension characteristic to representation | Done | Done | Exported for supported size and location dimensions and covered by STEP text regression. |
| `PLUS_MINUS_TOLERANCE` | Equal/unequal bilateral tolerance | Done | Done | Equal and unequal bilateral dimensions validate semantically and export for supported size and location dimensions. |
| `TOLERANCE_VALUE` | Limit or plus/minus tolerance values | Done | Done | Equal bilateral, unequal bilateral, and limits values validate and export for the supported dimension families. |

### Geometric Tolerance Modifiers And Zones

| AP242 entity | Concept | FreeCAD model status | AP242 export status | Notes |
| --- | --- | --- | --- | --- |
| `GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE` | FCF with datum reference | Done | Done | Used for position, parallelism, perpendicularity, and profile with datum system. |
| `GEOMETRIC_TOLERANCE_WITH_MODIFIERS` | FCF modifiers | Partial | Partial | Profile all-over, MMC/LMC material-condition modifiers, tangent plane, statistical tolerance, common tolerance `CT`, and projected-zone definitions export through AP242 modifier/zone paths where supported by OCCT. Broader modifier coverage remains future work. MMC/LMC are modifiers even though OCCT also stores them in the material requirement field. |
| `MODIFIED_GEOMETRIC_TOLERANCE` | Modified tolerance family | Partial | Partial | MMC/LMC are modeled/displayed/validated for conservative position-with-diameter-zone cases and export as AP242 maximum/least material requirement modifiers. |
| `UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE` | Unequally disposed tolerance zone | Partial | Partial | Surface profile, face-backed line profile, and single edge-backed line profile can store/display/validate a positive unequal-disposition offset and export it as AP242 `UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE` with a displacement value. Multiple edge-backed line-profile and all-over mappings remain future work. |
| `GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE` | Maximum tolerance modifier | Done | Done | FreeCAD model/display/validation exist; face-backed FCFs export `maximum_upper_tolerance` through a post-write AP242 complex-entity patch. |
| `GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT` | Defined-unit geometric tolerance | Done | Done | FreeCAD model/display/validation exist for length unit-basis tolerance; face-backed FCFs export `unit_size` through a post-write AP242 complex-entity patch. |
| `GEOMETRIC_TOLERANCE_WITH_DEFINED_AREA_UNIT` | Area-unit tolerance | Done | Done | FreeCAD model/display/validation exist for circular, rectangular, and square unit-basis tolerance; face-backed FCFs export `area_type` and `second_unit_size` through a post-write AP242 complex-entity patch. |
| `TOLERANCE_ZONE` | Tolerance zone | Partial | Partial | Position diameter zone exports a tolerance zone; broader zone support pending. |
| `TOLERANCE_ZONE_FORM` | Zone form | Partial | Partial | Cylindrical/circular form appears for diameter position tolerance. AP242 v4.1 recommends `unknown` unless the zone form is defined by geometry or known from user input. |
| `TOLERANCE_ZONE_DEFINITION` | Zone definition | Not started | Not started | Needed for richer zone geometry. |
| `PROJECTED_ZONE_DEFINITION` | Projected tolerance zone | Partial | Partial | Position FCF projected-zone height exports through a post-write AP242 entity pass that references the base `TOLERANCE_ZONE`; richer projected-zone cases should map the projection-origin feature. |
| `RUNOUT_ZONE_DEFINITION` | Runout zone definition | Partial | Partial | Runout FCFs are modeled and exported through OCCT; explicit user-defined runout-zone geometry remains a future refinement. |
| `RUNOUT_ZONE_ORIENTATION` | Runout zone orientation | Partial | Partial | User-entered orientation angle is stored and displayed; AP242 post-write export updates existing `RUNOUT_ZONE_ORIENTATION` angle entities when OCCT emits the base runout-zone records. |
| `NON_UNIFORM_ZONE_DEFINITION` | Non-uniform tolerance zone | Done | Done | FreeCAD model/display/validation exist for profile tolerances; face-backed FCFs export `NON_UNIFORM_ZONE_DEFINITION`, creating a `TOLERANCE_ZONE` when the base STEP writer did not emit one. |
| Affected plane association | Affected/intersection plane tolerance zone | Done | Done | FCFs can store a selected datum line/edge for affected-plane controls; AP242 export emits `SHAPE_ASPECT_RELATIONSHIP('affected plane association', ...)` for mapped face-plus-line cases. Import preview resolves edge-backed affected-plane relationships and native FCF import stores them when exactly one edge is resolved. GUI export `MBDTest01_BU.step` passed for line profile on `Fillet001.Face7`; parser regression covers AP242 affected-plane import. |
| `GEOMETRIC_TOLERANCE_RELATIONSHIP` | Composite tolerance frames | Not started | Not started | AP242 v4.1 represents composite FCFs as separate geometric tolerances related by `GEOMETRIC_TOLERANCE_RELATIONSHIP('composite', ...)`. |

### Presentation PMI

| AP242 entity family | Concept | FreeCAD model status | AP242 export status | Notes |
| --- | --- | --- | --- | --- |
| `DIMENSION_CURVE` / `DIMENSION_CURVE_TERMINATOR` | Visible dimension lines and arrows | View-provider display only | Not started | Current Coin3D dimension geometry is FreeCAD-native, not AP242 presentation PMI. |
| `PRESENTATION_SIZE` | Presentation text/symbol sizing | View-provider display only | Not started | Text size is stored in FreeCAD display-layout metadata; AP242 presentation sizing is not exported. |
| Draughting/presentation annotation entities | Visible PMI graphics | View-provider display only | Partial | First-pass placeholder draughting model export exists. Exact visible frames, symbols, leader curves, arrows, and text runs remain future work. |
| `ANNOTATION_PLACEHOLDER_OCCURRENCE` | Presentation placeholder | Partial | Partial | One placeholder exports for each native datum, datum target, dimension, and FCF using stored annotation origin/text-height/layout metadata; semantic links are emitted for resolvable datums and FCFs. Import and exact graphics remain future work. |
| `ANNOTATION_PLACEHOLDER_OCCURRENCE_WITH_LEADER_LINE` | Placeholder leader lines | Not started | Not started | Captures leader, dimension, extension, or witness line routing for a placeholder; useful after annotation leader routing is stable enough to exchange. |

## Import Roadmap

After semantic export is reliable:

| Milestone | Status | Notes |
| --- | --- | --- |
| Inspect imported AP242 PMI coverage and warn on unsupported entities | Done | Temporary guardrail only. `Inspect AP242 PMI` scans STEP text for known AP242 PMI entity families, reports supported/partial/unsupported/deferred coverage, and copies the report to the clipboard. Do not expand this into a full importer warning system until feature implementation catches up. |
| Build AP242 semantic PMI preview | Done | `MBDImporter.semantic_import_preview()` parses STEP Part 21 records into non-destructive native import candidates and limitations. `Inspect AP242 PMI` appends this preview to the coverage report. |
| Build tentative AP242 topology binding preview | Done | The importer resolves `GEOMETRIC_ITEM_SPECIFIC_USAGE`, datum-feature relationships, composite shape-aspect relationships, composite-group shape aspects, and dimensional-size-backed datum features into tentative `#geometry -> FaceN/EdgeN` bindings for imported-object creation. |
| Create native datum and datum-system objects from previewed AP242 PMI | Mostly done | `Import AP242 Datums` imports STEP geometry and creates native datum features and datum systems from previewed topology bindings. The preview now resolves directly-bound, composite, common, target-backed, composite-group, and dimensional-size-backed datum-feature bindings across the NIST sweep. Imported multi-face datum features now preserve all resolved face bindings in `ReferencedSubelementList` while using the first face as the visible annotation anchor; STC10 re-export writes datum D on three faces and datum J on two faces, and FTC08 re-export writes datum G on two faces. Remaining work is richer validation/display for multi-face datum features and unsupported area-target cases. |
| Create native datum target objects from previewed AP242 PMI | Mostly done | CTC05-style placed rectangle datum targets now import from AP242 `PLACED_DATUM_TARGET_FEATURE`, `SHAPE_DEFINITION_REPRESENTATION`, target placement/size parameters, and `SHAPE_ASPECT_RELATIONSHIP(..., 'datum target', target, datum)`. Headless CTC05 smoke creates C1/D1 and validates cleanly. Headless FreeCAD-backed unit coverage exercises placed point, line, circle, and rectangle target import, including line length and circle diameter parameters. Remaining work is broader real-file examples for non-rectangle target types and explicit rectangular in-plane orientation handling. The only unresolved NIST target count is FTC10's four area targets, which are intentionally out of scope. |
| Create native dimension objects from previewed AP242 PMI | Partial | AP242 `DIMENSIONAL_SIZE`, `DIMENSIONAL_LOCATION`, `ANGULAR_SIZE`, and `ANGULAR_LOCATION` candidates now import as native dimensions when their resolved topology can be measured by the existing dimension engine. The importer reads AP242 nominal values from `SHAPE_DIMENSION_REPRESENTATION` and plus/minus tolerance bands from `PLUS_MINUS_TOLERANCE` / `TOLERANCE_VALUE`; each measure is scaled using its referenced AP242 length unit, which fixes mixed-unit files such as NIST CTC03. Imported AP242 `DIMENSIONAL_LOCATION`, imported diameter dimensions, and linear `DIMENSIONAL_SIZE('thickness')` now route through post-write entities on re-export to avoid OCCT null references. Bindings whose measured geometry does not match the imported nominal within tolerance are skipped instead of creating invalid native PMI. Headless CTC03 import/export now round-trips 10 dimensions with no null semantic references; CTC05 import/export round-trips the AP242-toleranced diameter dimension and target-backed datum systems. The importer now has a conservative line/trimmed-curve-to-edge resolver, but CTC05 construction-curve location dimensions still do not map to unique imported FreeCAD edges, so they remain preview-only until a construction-curve/path dimension workflow exists. |
| Create native FCF objects from previewed AP242 PMI | Mostly done | The importer now creates native FCFs for one-face Flatness/Profile/LineProfile/Straightness/Circularity/Cylindricity/Position/Parallelism/Perpendicularity/Angularity/CircularRunout/TotalRunout cases and safe multi-face Flatness/Profile/LineProfile/Position/Parallelism/Perpendicularity/Angularity cases, including supported modifier-rich profile, position, orientation, and runout-orientation cases. These bypass OCCT's direct FCF writer and re-export through post-write AP242 tolerance entities; focused FreeCADCmd smoke confirms flatness/profile/profile-with-datum/line-profile-with-common-datum/straightness/circularity/cylindricity/runout/position/parallelism/perpendicularity/angularity and modifier-rich profile/position export with no null semantic references. Imported position FCFs get a conservative cylindrical/circular `TOLERANCE_ZONE_FORM` and `TOLERANCE_ZONE`; imported runout FCFs get `TOLERANCE_ZONE`, `RUNOUT_ZONE_DEFINITION`, and `RUNOUT_ZONE_ORIENTATION` where a plane-angle unit is available. CTC03 imports/re-exports 13 FCFs, including multi-face profile/position/perpendicularity; FTC08 imports/re-exports 33 FCFs, including large multi-face profile/position sets and perpendicularity with MMC on an axis-capable controlled feature. Remaining native FCF import work is richer derived-axis/path semantics and modifier combinations not yet represented in the native model. |
| Close imported FCF re-export gap: datum-referenced tolerances | Mostly done | Imported datum-referenced Profile/LineProfile/Position/Parallelism/Perpendicularity/Angularity/CircularRunout/TotalRunout tolerances whose AP242 datum-system references resolve to individual or common-datum compartments have first-pass native creation and post-write re-export support. Multi-face controls are preserved by storing all controlled subelements and writing multiple `GEOMETRIC_ITEM_SPECIFIC_USAGE` links for one tolerance shape aspect. Remaining datum-reference work is mostly modifier-rich, revolved/derived, and path/axis cases that fail native validation rather than clean AP242 references. |
| Close imported FCF re-export gap: revolved and derived geometry tolerances | Partial | Imported circularity/roundness, cylindricity, straightness, circular runout, and total runout now create native FCFs only when the resolved FreeCAD face passes the same geometry-capability checks used by validation, and they re-export through post-write AP242 tolerance entities with no null references. CTC05 proves a mixed real file can import/re-export two circular runout FCFs and one total runout FCF; two other CTC05 runout candidates still stay preview-only because their AP242 topology resolves to planar FreeCAD faces. Remaining work is richer derived-axis/path semantics for cases whose controlled topology is not itself a revolved face. |
| Close imported FCF re-export gap: multi-attachment controlled geometry | Mostly done | Imported safe multi-face Flatness/Profile/LineProfile/Position/Parallelism/Perpendicularity/Angularity controls now keep a `ControlledSubelementList` for all controlled faces while anchoring the visible annotation to the first face. AP242 re-export writes multiple `GEOMETRIC_ITEM_SPECIFIC_USAGE` records against one tolerance `SHAPE_ASPECT`, preserving the controlled set without null references. CTC03 and FTC08 FreeCADCmd smoke tests pass, including profile sets with dozens of faces and position patterns with many cylindrical faces. Remaining work: edge-backed multi-line-profile section direction, derived-axis/path semantics, and richer validation/display for grouped controls. |
| Close imported FCF re-export gap: modifier and zone value preservation | Partial | The importer now parses/stores AP242 material condition, tangent plane, statistical tolerance, common zone, projected zone height, unequally disposed profile displacement, maximum tolerance, unit-basis tolerance, non-uniform zone values, edge-resolved affected-plane associations, and runout orientation angles. Supported native FCF families re-export these values through the imported-FCF post-write exporter; imported runout FCFs re-export `RUNOUT_ZONE_DEFINITION` and `RUNOUT_ZONE_ORIENTATION` angle entities when the STEP context provides a plane-angle unit. Native validation now accepts MMC/LMC on position and axis-capable orientation/straightness controls with a diametrical zone. Focused FreeCADCmd smoke, CTC03/CTC05/FTC08 import/export, and project `MBDTest01_BT.step` import/export pass with no null references. Remaining modifier/zone import work: broader projected-zone projection-end semantics and modifier combinations not yet represented in the native model. |
| Investigate AP242 import of semantic PMI into FreeCAD MBD objects | Done | Initial investigation produced the semantic preview layer; remaining work is implementation of topology binding and object creation. |
| Reconstruct visible PMI from imported semantic and presentation data | Future | Requires display-layout architecture decisions. |
| Preserve imported PMI IDs/history where possible | Partial | Native AP242 import now records `AP242SourceFile`, `AP242SourceId`, `AP242SourceType`, and `AP242ImportStatus` on created datums, datum targets, datum systems, dimensions, and FCFs. Full round-trip preservation of AP242 semantic ids remains future work because STEP entity ids are file-local and can change on re-export. |
| Validate imported attachments against FreeCAD topology and geometry signatures | Done | Native AP242 import records geometry signatures for created datum features, datum targets, dimensions, and FCFs. Validation rechecks those signatures like hand-authored PMI, and imported multi-face datum features now store/check each preserved face binding rather than only the display anchor. |

### Headless AP242 Import Preview Sweep

`tests/ap242_import_preview_sweep.py` runs the semantic-import preview over a
STEP file or folder without requiring FreeCAD. It exercises the parser,
native-ready classification, and tentative topology binding logic, but it does
not create FreeCAD objects or verify GUI import/re-export behavior.

`tests/freecad_ap242_import_smoke.py` runs with FreeCADCmd and exercises STEP
geometry import, semantic preview, native datum/datum-system creation, and
validation. With the FreeCAD AppImage extracted under `/tmp/squashfs-root`, the
known-good command is:

`tests/run_headless_smoke.py --mode datum-only`

The headless runner now sets `XDG_CACHE_HOME` and `XDG_CONFIG_HOME` under
`/tmp/mbd-freecad-cli`, plus offscreen AppImage flags, so CLI smoke tests do not
need to read or write the user's normal FreeCAD profile.

Latest FreeCADCmd smoke result for `nist_ctc_05_asme1_ap242-e1.stp`: passed.
The script created four native datum features, two native rectangle datum
targets, five native datum systems, and two native dimensions including an AP242-toleranced diameter
dimension with no validation issues. An ambiguous edge-location dimension whose
measured binding did not match the AP242 nominal is skipped with an explicit
message. FCF candidates were recognized but deferred where the imported topology
family has not proven clean AP242 re-export.
Import/export smoke on the same file also passed and confirmed the re-exported
STEP contains no null semantic references. CTC01 semantic preview still parses
quickly, but a full FreeCADCmd geometry-import smoke stalled in FreeCAD
import/recompute before producing script output and should be treated as an
import-performance follow-up rather than a PMI parser failure.

Latest sweep of `/home/chip/Projects/FreeCAD MBD/NIST-PMI-STEP-Files`:

| File | Datums | Datum systems | Datum targets | Dimensions | FCFs | Relationships | Limitations | Seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `nist_ctc_01_asme1_ap242-e1.stp` | 3/3 | 2/2 | 0/0 | 12/12 | 6/6 | 0/0 | 3 | 0.10 |
| `nist_ctc_02_asme1_ap242-e2.stp` | 10/10 | 14/14 | 9/9 | 7/7 | 22/22 | 0/0 | 9 | 0.50 |
| `nist_ctc_03_asme1_ap242-e2.stp` | 6/6 | 6/6 | 0/0 | 10/10 | 13/13 | 0/0 | 7 | 0.14 |
| `nist_ctc_04_asme1_ap242-e1.stp` | 8/8 | 5/5 | 0/0 | 10/10 | 7/7 | 0/0 | 6 | 0.45 |
| `nist_ctc_05_asme1_ap242-e1.stp` | 4/4 | 5/5 | 2/2 | 6/6 | 9/9 | 2/2 | 9 | 0.32 |
| `nist_ftc_06_asme1_ap242-e2.stp` | 10/10 | 12/12 | 6/6 | 24/24 | 28/28 | 0/0 | 8 | 0.28 |
| `nist_ftc_07_asme1_ap242-e2.stp` | 5/5 | 5/5 | 0/0 | 17/17 | 27/27 | 0/0 | 6 | 0.41 |
| `nist_ftc_08_asme1_ap242-e1-tg.stp` | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0 | 0.35 |
| `nist_ftc_08_asme1_ap242-e2.stp` | 11/11 | 9/9 | 0/0 | 10/10 | 33/33 | 22/22 | 5 | 0.48 |
| `nist_ftc_09_asme1_ap242-e1.stp` | 8/8 | 8/8 | 0/0 | 22/22 | 31/31 | 0/0 | 6 | 0.55 |
| `nist_ftc_10_asme1_ap242-e2.stp` | 11/11 | 12/12 | 0/4 | 26/26 | 39/39 | 4/4 | 13 | 0.55 |
| `nist_ftc_11_asme1_ap242-e2.stp` | 2/2 | 1/1 | 0/0 | 6/6 | 4/4 | 4/4 | 4 | 0.18 |
| `nist_stc_06_asme1_ap242-e3.stp` | 6/6 | 9/9 | 0/0 | 17/17 | 25/25 | 0/0 | 7 | 0.32 |
| `nist_stc_07_asme1_ap242-e3.stp` | 5/5 | 5/5 | 0/0 | 43/43 | 22/22 | 0/0 | 7 | 0.49 |
| `nist_stc_08_asme1_ap242-e3.stp` | 8/8 | 9/9 | 0/0 | 7/7 | 30/30 | 0/0 | 6 | 0.39 |
| `nist_stc_09_asme1_ap242-e3.stp` | 8/8 | 8/8 | 0/0 | 22/22 | 27/27 | 0/0 | 5 | 0.56 |
| `nist_stc_10_asme1_ap242-e2.stp` | 9/9 | 12/12 | 0/0 | 27/27 | 36/36 | 18/18 | 9 | 0.59 |

Immediate importer findings from this sweep:

- The sweep now resolves every recognized datum, datum system, dimension, FCF, and relationship candidate in the current NIST folder.
- The only native-ready count gap is `nist_ftc_10_asme1_ap242-e2.stp`, where four AP242 area datum targets are recognized but intentionally out of scope because current datum-target scope is point, line, circle, and rectangle.
- The preview parser now completes the whole NIST folder in seconds rather than minutes; remaining import work is semantic coverage and native object creation/export proof, not STEP text scanning speed.
- The headless sweep cannot replace GUI testing of visible native FreeCAD annotations, but it does cover parser, candidate classification, and tentative topology binding regressions.

## Cosmetic Final Touches

| Milestone | Status | Notes |
| --- | --- | --- |
| Review dimension terminology in user-facing dialogs | Future | Equal bilateral, unequal bilateral, and limits are the current supported names; only revisit wording if GUI testing shows confusion. |
| Tweak appearance of view-provider text and symbols for readability (size, line thickness, text view direction) | Future | Start after the full workstream from model definition in FreeCAD to complete export to AP242 has been thoroughly tested and verified|
| Refine annotation placement interaction | Future | Current double-click/click placement is functional; later work can make movement feel more like Sketcher constraints or TechDraw annotations with conventional press-drag-release behavior. |
| Create graphical symbols for each tool in the toolbar | Done | Ten 64x64 SVG command icons in `mbd_command_icons` are wired to the MBD toolbar and menu commands. |
| Comment all the code cleanly to make it sustainable | Ongoing | Initial maintainability pass removed obsolete timing diagnostics and documented the view-provider architecture, post-write AP242 dimension paths, datum-target geometry, and validation rules. Broader cleanup should continue as features stabilize. |

## Completed Work Archive

This section holds completed milestones, completed roadmap records, regression
coverage, and passed GUI tests. Keep the active plan and open requests above so
the top of this document stays useful during day-to-day work.

### Completed Milestones

| Area | Milestone | Status | Notes |
| --- | --- | --- | --- |
| AP242 export | Stable semantic datum export | Done | STEP output includes semantic datum entities attached to faces. |
| AP242 export | Stable position FCF export | Done | Position tolerance exports semantically with datum references. |
| Validation | Attachment signature recording | Done | Used to detect topology/name drift before export. |
| Validation | Export-time integrity validation with user warning/cancel workflow | Done | Do not auto-reassign PMI attachments. |
| Validation | PMI Inspector with copyable validation report | Done | User can copy test/debug reports from the GUI. |
| Visualization | Visible datum labels, datum targets, basic dimensions, dimensions, and FCFs | Done | Helper-object display is good enough for the current phase and can be refined in the final cosmetic phase as needed. |
| Visualization | Drawn GD&T symbol geometry for FreeCAD display | Done | Unicode symbol text did not render reliably, so symbols are drawn. |
| Visualization | FCF tolerance input with units | Done | Supports entries such as `0.005 in` and `0.1 mm`. |
| Visualization | Position FCF display below related feature dimension when possible | Done | GUI testing passed for the current diameter/position workflow. |
| Visualization | Exterior leader placement for surface FCFs | Done | Uses surface/solid probing to avoid drawing through the solid. |
| Tolerances | Parallelism FCF definition with a single datum-reference surface | Done | Display, validation, and semantic AP242 export are in place. |
| Testing | Headless smoke/regression harness using FreeCAD command line | Done | Used for exporter, validation, and display regressions. |


### Completed AP242 Export Records

| Milestone | Status | Notes |
| --- | --- | --- |
| Add semantic export for flatness | Done | Implemented through XCAF geometric tolerance child labels and covered by STEP text checks. |
| Add semantic export for parallelism with a single datum reference | Done | Uses `DatumReference` and links the referenced datum to the geometric tolerance. |
| Add semantic export for perpendicularity and other orientation controls | Done | Perpendicularity implemented using the same one-datum-reference path as parallelism. |
| Add semantic export for profile controls | Done | Surface profile implemented for face-level and all-over profile; all-over currently targets the exported face set. |
| Add semantic export for remaining direct geometric tolerance controls | Done | Line profile, angularity, straightness, circularity/roundness, cylindricity, circular runout, and total runout are mapped through the same XCAF geometric tolerance path and covered by STEP text checks. |
| Add semantic dimension export | Done | Core semantic dimension export is implemented for diameter, radius, plane-to-plane thickness, and linear location dimensions with no null references. Directed/path dimension variants remain future items. |
| Add semantic radius dimension export | Done | Radius dimensions export through a post-write AP242 `DIMENSIONAL_SIZE('radius')` entity pass with `SHAPE_DIMENSION_REPRESENTATION`, `DIMENSIONAL_CHARACTERISTIC_REPRESENTATION`, and plus/minus tolerance support, avoiding the native OCCT null-reference path. |
| Design angular semantic dimension workflow | Done | Two-reference angular dimensions are available through `Create Dimension`; GUI validation/display/export passed for a face-backed angular location case. Richer angular-size and edge/axis mapping are tracked as future AP242 coverage refinements. |
| Add semantic point datum target export | Done | Point datum targets export through OCCT/XCAF as `PLACED_DATUM_TARGET_FEATURE` with `FEATURE_FOR_DATUM_TARGET_RELATIONSHIP`; headless and GUI STEP checks passed. |
| Add common-datum and flexible datum-system definition/export | Done | Datum systems now contain one to three ordered compartments; each compartment accepts one datum or multiple simultaneous common datums such as `A-B`. XCAF/AP242 export writes `COMMON_DATUM_LIST` and the corresponding datum reference elements. |
| Add semantic line datum target definition/export | Done | Straight construction edges define line targets with stored center, direction, and length; full-segment validation, single-item display, mixed point/line sufficiency, creation-time rejection for off-surface lines, and native OCCT/AP242 export have passed GUI testing. |
| Validate datum target constraint adequacy in datum systems | Done | Point targets count as one constraint and line targets as two; validation now rejects underdefined, duplicate, and collinear point/line target sets for primary/secondary/tertiary datum systems. Circle and rectangle target support is tracked under the scoped datum-target workflow. |
| Add first-pass AP242 annotation placeholder export | Done | STEP export now appends `ANNOTATION_PLACEHOLDER_OCCURRENCE` records for native datum, datum target, dimension, and FCF objects, grouped in a draughting model with semantic datum/FCF links where resolvable. Exact leader-line placeholder export remains a future presentation PMI refinement. |

### Completed Annotation Architecture Roadmap

| Phase | Milestone | Status | Notes |
| --- | --- | --- | --- |
| Short term | Continue using helper objects for rapid iteration | Done | Superseded. Current semantic annotation types use owning view-provider rendering; compatibility-only helper display branches have been removed. |
| Short term | Organize helper objects so the model tree remains usable | Done | `MBD PMI` group organizes semantic owners. Current annotation workflows should not create helper display children for datum features, datum targets, dimensions, or FCFs. |
| Medium term | Define stable display-layout properties for each semantic PMI object | Done | Semantic PMI objects now store versioned origin, plane normal, reading direction, text height, layout mode, and a layout lock; save/reopen persistence is covered headlessly. |
| Medium term | Avoid storing derived visual geometry when it can be regenerated | Done | Datum features, FCFs, datum targets, and dimensions regenerate visible geometry through their owning view providers. |
| Long term | Replace helper display objects with custom FreeCAD view-provider rendering | Done | Current datum, target, FCF, and dimension annotations each have a single-tree-item implementation. |
| Long term | Draw lines, boxes, symbols, leaders, and text through the owning PMI view provider | Done | Current semantic annotation owners draw their complete visible annotation directly with Coin3D. |
| Long term | Allow manual annotation placement in the 3D view | Done | Datum features, FCFs, targets, and dimensions share persistent planar movement behavior. More natural Sketcher/TechDraw-like drag behavior is deferred to cosmetic interaction refinement. |


### Completed Regression Test Goals

Keep or add tests for:

| Test Goal | Status | Notes |
| --- | --- | --- |
| Datum A/B/C semantic STEP entities | Done | Covered by STEP text checks. |
| Datum usage attached to `ADVANCED_FACE` | Done | Covered by STEP text checks. |
| Position FCF creates `POSITION_TOLERANCE` | Done | Covered by STEP text checks. |
| Position FCF creates datum-reference entities | Done | Covered by STEP text checks. |
| Tolerance value is nonzero and matches the FreeCAD object | Done | Covered by STEP text checks. |
| Stale attachment validation catches changed geometry | Done | Covered by headless smoke test. |
| Canceling an export warning prevents STEP file write | Done | Covered by headless smoke test. |
| Non-position FCFs do not export as position tolerances | Done | Exporter skips unsupported FCFs with a warning. |
| View-provider PMI display does not affect PMI text-height scaling | Done | Covered by display regression. |
| Parallelism FCF validates with one datum reference | Done | Covered by headless smoke test. |
| Perpendicularity FCF validates with one datum reference | Done | Covered by headless smoke test. |
| Profile FCF validates with datum system references | Done | Covered by headless smoke test. |
| Profile all-over FCF validates without datum references | Done | Covered by headless smoke test with body-level attachment and `ALL OVER` display cell. |
| Flatness AP242 export entity checks | Done | Covered by all-FCF STEP text regression. |
| AP242 annotation placeholder occurrence export | Done | Covered by import/export smoke test; re-exported STEP must contain `ANNOTATION_PLACEHOLDER_OCCURRENCE` for created native PMI and no null semantic references. |
| Parallelism AP242 export entity checks | Done | Covered by all-FCF STEP text regression. |
| Perpendicularity AP242 export entity checks | Done | Covered by all-FCF STEP text regression. |
| Surface profile AP242 export entity checks | Done | Covered by all-FCF STEP text regression. |
| Line profile AP242 export entity checks | Done | Covered by all-FCF STEP text regression using an edge-controlled `LINE_PROFILE_TOLERANCE`. |
| Angularity AP242 export entity checks | Done | Covered by all-FCF STEP text regression. |
| Straightness AP242 export entity checks | Done | Covered by all-FCF STEP text regression. |
| Circularity/roundness AP242 export entity checks | Done | Covered by all-FCF STEP text regression. |
| Cylindricity AP242 export entity checks | Done | Covered by all-FCF STEP text regression. |
| Circular runout AP242 export entity checks | Done | Covered by all-FCF STEP text regression. |
| Total runout AP242 export entity checks | Done | Covered by all-FCF STEP text regression. |
| FCF tolerance-specific semantic validation rules | Done | Headless regression covers valid/invalid line profile, angularity, straightness, circularity, cylindricity, direct-datum runout, and datum-system runout rule cases. |
| FCF modifier semantic validation rules | Done | Headless regression covers conservative MMC/projected-zone position validation, rejection of modifiers on unsupported FCF types, and unequal-disposition validation for profile tolerances. |
| FCF material-condition, projected-zone, and unequal-disposition AP242 export | Done | Headless regression confirms an MMC position FCF exports `GEOMETRIC_TOLERANCE_WITH_MODIFIERS((.MAXIMUM_MATERIAL_REQUIREMENT.))` and `PROJECTED_ZONE_DEFINITION`; surface profile, face-backed line profile, and single edge-backed line profile with circled `U` export `UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE`. |
| Size dimension AP242 export entity checks | Done | Headless regression confirms diameter, radius, and thickness `DIMENSIONAL_SIZE`, `SHAPE_DIMENSION_REPRESENTATION`, `DIMENSIONAL_CHARACTERISTIC_REPRESENTATION`, `TOLERANCE_VALUE`, and `PLUS_MINUS_TOLERANCE` with no null references. |
| Linear location dimension AP242 export entity checks | Done | Headless regression confirms the post-write AP242 `DIMENSIONAL_LOCATION` path creates `SHAPE_ASPECT`, `GEOMETRIC_ITEM_SPECIFIC_USAGE`, `SHAPE_DIMENSION_REPRESENTATION`, `DIMENSIONAL_CHARACTERISTIC_REPRESENTATION`, `TOLERANCE_VALUE`, and `PLUS_MINUS_TOLERANCE` with no null references. |
| Directed linear location dimension AP242 export entity checks | Done | Headless regression confirms the exporter can write `DIRECTED_DIMENSIONAL_LOCATION` with no null references when that AP242 subtype is selected internally. |
| Point datum target AP242 export entity checks | Done | Headless regression confirms `PLACED_DATUM_TARGET_FEATURE`, `SHAPE_REPRESENTATION_WITH_PARAMETERS`, and `FEATURE_FOR_DATUM_TARGET_RELATIONSHIP` with no null references. |
| Circular and rectangular datum target AP242 export checks | Done | Headless regression confirms circular and rectangular datum targets validate and export as AP242 `PLACED_DATUM_TARGET_FEATURE` entities with no null references. Arbitrary/freeform area targets are out of scope. |
| Datum target sufficiency validation | Done | Headless regression confirms underdefined, duplicate, and collinear primary/secondary point-target datum sets are reported and complete independent target sets clear validation. |
| Stable semantic PMI display-layout metadata | Done | Headless regression confirms all semantic PMI types receive the layout schema, locked layouts reject automatic overwrite, and values survive FCStd save/reopen. |
| Dimension purpose and reference semantic rules | Done | Headless regression rejects unequal values marked equal bilateral, tolerance values on basic/reference dimensions, and diameter/radius dimensions with a second reference. |
| Global-scope links to Part Design geometry | Done | Model and construction geometry references use `App::PropertyLinkGlobal`; old project-file link migration has been removed because backward compatibility with earlier experimental MBDWorkbench files is intentionally out of scope. |
| AP242 PMI import coverage warning | Done | Headless regression confirms the STEP scanner reports supported/partial PMI and flags unsupported/deferred PMI entities such as presentation curves and ASME-excluded tolerance types. |
| Angular semantic dimension export | Done | Headless regression creates an angular dimension between planar faces and confirms AP242 `ANGULAR_LOCATION`, `PLANE_ANGLE_MEASURE`, dimension representation links, tolerance values, and no null references. |
| Imported multi-face datum binding preservation | Done | Native AP242 import stores all resolved datum-face bindings in `ReferencedSubelementList` while keeping the first face as the visible annotation anchor. Geometry signatures now store and validate each preserved face binding, and PMI Inspector/validation attachment text lists the full face set. STC10 smoke confirms datum D re-exports on Face7/Face4/Face49 and datum J on Face44/Face40; FTC08 smoke confirms datum G re-exports on Face68/Face67, with no null semantic references. |
| Imported simple and supported modifier-rich FCF AP242 re-export | Done | Headless FreeCADCmd smoke creates imported native flatness, datum-free profile, datum-referenced profile, common-datum line-profile, straightness, circularity/roundness, cylindricity, circular runout, total runout, position, parallelism, perpendicularity, angularity, modifier-rich profile, and projected MMC position FCFs, then re-exports them through post-write AP242 tolerance entities with `GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE`, `DATUM_SYSTEM`, `COMMON_DATUM_LIST`, position `TOLERANCE_ZONE`, `ROUNDNESS_TOLERANCE`, `CYLINDRICITY_TOLERANCE`, `STRAIGHTNESS_TOLERANCE`, `CIRCULAR_RUNOUT_TOLERANCE`, `TOTAL_RUNOUT_TOLERANCE`, `RUNOUT_ZONE_DEFINITION`, `RUNOUT_ZONE_ORIENTATION`, `GEOMETRIC_TOLERANCE_WITH_MODIFIERS`, `GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE`, `GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT`, `GEOMETRIC_TOLERANCE_WITH_DEFINED_AREA_UNIT`, `UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE`, `NON_UNIFORM_ZONE_DEFINITION`, `PROJECTED_ZONE_DEFINITION`, and no null semantic references. CTC05 import/export smoke confirms two real-file circular runout FCFs, two real-file perpendicularity FCFs, one real-file circularity FCF, and one real-file total runout FCF round-trip cleanly; `MBDTest01_BT.step` round-trips four imported FCFs including a modifier-rich profile. |
| AP242 import performance pass | Done | Headless timing showed native dimension creation, validation, and early STEP preview scanning were the main costs. AP242 import now uses lightweight semantic cylinder measurement for imported diameter/radius dimensions, direct plane-definition measurement for imported plane-to-plane linear dimensions, cached geometry classification in validation, and indexed STEP entity parsing. Project `MBDTest01_BT.step` import/export dropped from about `5.1s` to roughly `0.4s`; NIST CTC05 dropped from about `36.9s` to roughly `2.5s`; NIST STC10 now passes import/export in about `2.6s` after non-planar face-backed linear size dimensions were kept preview-only instead of falling into FreeCAD's expensive generic distance solver. The full NIST preview sweep now completes in seconds, with individual files typically under `0.6s`. |


### Completed GUI Test Archive

These rows are retained as the test history. New manual test requests should
stay in `Open GUI Requests` until they pass, fail, or are explicitly deferred.

| Test Case | Result | Notes |
| --- | --- | --- |
| `Show PMI Inspector` then `Copy Report` | Passed | Confirms the debugging handoff path still works. |
| `Inspect AP242 PMI` command | Passed | GUI scan of `MBDTest01_BH.step` listed detected PMI entities in Report view and copied the report to the clipboard. Follow-up refinement separates partial-coverage cautions from truly unsupported/deferred PMI warnings. |
| Inspect AP242 semantic import preview | Passed | GUI import preview on `tests/MBDTest01_BT.step` reported native-ready topology bindings for 3 datums, 4 datum systems, 6 dimensions, and 4 FCFs, with expected partial-coverage notes for richer AP242 modifiers, runout zones, and tolerance-zone forms. |
| Import AP242 datums, target-backed datums, and datum systems | Passed | GUI import of `tests/MBDTest01_BT.step` created datum features A/B/C and four datum systems with no validation issues. GUI import of NIST `nist_ctc_03_asme1_ap242-e2.stp` created 6 datum features and 6 datum systems. GUI and headless import of NIST `nist_ctc_05_asme1_ap242-e1.stp` now create 4 datum features, 2 rectangle datum targets, and 5 datum systems, including target-backed C/D and common datum A-B; PMI Inspector reports 0 errors and 0 warnings. The headless smoke now prints the same Inspector-style table so this import/inspector check does not require manual GUI testing. |
| Re-export after AP242 datum import | Passed | Headless import/export smoke now covers NIST CTC05 and CTC03. CTC05 imports target-backed C/D rectangle datum targets, re-exports one shape, writes datum targets, and has no null semantic references. CTC03 re-export now filters the compound wrapper, exports one shape, reports six XCAF datum labels rather than twelve, and has no null semantic references. |
| MBD toolbar command icons | Passed | Restart FreeCAD and confirm all ten SVG icons, including the new `Inspect AP242 PMI` icon, render crisply, remain distinguishable at toolbar size, and have acceptable contrast with the current FreeCAD theme. Earlier nine-icon set had passed. |
| Single-item FCF view provider | Passed | Restart FreeCAD and open a model containing FCFs. Confirm each FCF is one model-tree item with no `_Text`, `_Frame`, `_Leader`, or symbol children, while its complete annotation remains visible. Create a new FCF and repeat. |
| Single-item datum feature view provider | Passed | Datum features are single model-tree items. Follow-up correction centers datum letters vertically in their boxes. |
| Move and persist a datum feature annotation | Passed | Double-click a visible datum feature annotation, move it, and left-click to place it. Save, close, reopen, and confirm the placement persists while the triangle remains attached to the datum surface. |
| Single-item datum target view provider | Passed | Restart FreeCAD and open or create datum targets. Confirm each target is one model-tree item with no separate `_Text` child, while its point marker, leader, and identifier remain visible. |
| Single-item dimension view provider | Passed | Restart FreeCAD and open a model containing linear, diameter, radius, and basic dimensions. Confirm each dimension is one model-tree item with no `_Text`, `_Display`, `_TextBox`, or diameter-symbol children, while the complete annotation remains visible. Create one new dimension of each kind and repeat. |
| Move and persist a dimension annotation | Passed | Double-click a visible linear dimension, move it, and left-click to place it. Repeat with diameter, radius, and basic dimensions. Save, close, reopen, and confirm the placements persist. |
| Dimension view-provider geometry check | Passed | Confirm linear dimensions retain extension lines and arrows, diameter dimensions retain the diameter symbol, radius dimensions retain an `R` leader callout, and Basic dimensions retain their enclosing box. |
| Position FCF below single-item diameter dimension | Passed | Diameter and FCF share one plane with centered text. The redundant FCF-to-axis leader is now suppressed when a matching diameter dimension exists, and the FCF upper-left corner attaches directly to the diameter extension line. |
| Dimension creation performance | Passed | Creating three dimensions in the developed GUI model measured 0.040-0.043 seconds for creation, reduced from 15-26 seconds. The fix attaches a suspended view provider to the empty single-item object before populating semantic properties, then performs one final rebuild. Geometry resolution still measured 0.919-1.599 seconds. |
| FCF creation performance | Passed | Position FCF creation completed without a slow constructor or attach phase after adopting the suspended single-item `App::FeaturePython` lifecycle. |
| Direct annotation movement after performance fix | Passed | Direct 3D movement and placement passed for a position FCF and diameter dimension while dimension creation remained 0.041 seconds and FCF creation remained responsive. |
| Direct annotation movement | Passed | Double-click or use the tree context menu `Move annotation` on a dimension and an FCF, move the cursor, and click/release to place. Annotations commit to the new location and remain movable after a workbench restart/reopen. Include a runout FCF whose display plane is borrowed from a matching diameter dimension in future regression checks. |
| Move and persist an FCF annotation from the 3D view | Passed | Double-clicking the visible FCF picks it up, mouse movement repositions it, and another left click places it. Tree context `Move annotation` remains a fallback. Future refinement: make interaction behave like Sketcher constraints or TechDraw annotations with a conventional press-drag-release gesture. |
| FCF view-provider symbol and text check | Passed | Check position with diameter, flatness, line profile, surface profile, and a datum-referenced orientation FCF. Confirm boxes, symbols, tolerance text, and datum compartments remain readable and lie in the annotation plane. Cosmetic differences can be recorded for the later cleanup phase. |
| FCF modifier dialog, display, validation, and MMC/LMC export | Passed | Previous test confirmed the modifier dialog path but found plain-text modifier display. Create a position FCF with a diameter zone, choose `MMC`, enable `ProjectedToleranceZone`, and give `ProjectedToleranceHeight` a positive value. Confirm the FCF cell displays ASME-style circled `M` and circled `P` symbols, and Validate PMI passes. AP242 export should include `GEOMETRIC_TOLERANCE_WITH_MODIFIERS((.MAXIMUM_MATERIAL_REQUIREMENT.))`; repeat with `LMC` if practical and confirm a circled `L`. Then set `MaterialConditionModifier=MMC` on flatness or set `UnequallyDisposedZone=True` on position and confirm Validate PMI rejects it. For profile or line profile, choose an unequal-disposition offset and confirm a circled `U` plus offset displays and validation passes. |
| Optional common tolerance, maximum value, unit-basis, and non-uniform FCF options | Passed | GUI/export `MBDTest01_BT.step` passed validation and exported maximum tolerance, unit-basis tolerance, and non-uniform zone AP242 entities. Retest after the latest display/dialog fixes: common tolerance should display as `CT`; maximum value should display in a separate FCF block as `<value> MAX`; unit-basis should ask for one size for length, circular diameter, and square side length, and two sizes only for rectangular basis; unit-basis display should omit unit suffixes and show slash notation such as `/ 1.000`, `/ ⌀1.000`, `/ 1.000 x 1.000`; `NON-UNIFORM` should fit within its FCF cell; dimensions and FCF numeric values should not show unit suffixes such as `in`. |
| Optional tangent plane and statistical FCF modifiers | Passed | Create an FCF and use the optional modifier checkbox dialog to select tangent plane and statistical tolerance. Confirm the FCF displays a circled `T` and `<ST>` in the tolerance cell, Validate PMI passes, and AP242 export either writes the corresponding `GEOMETRIC_TOLERANCE_WITH_MODIFIERS` entries or reports a clear OCCT-binding warning if the enum is unavailable. |
| Affected-plane FCF from controlled face plus datum line | Passed | GUI export `MBDTest01_BU.step` created a face-backed line-profile tolerance on `Fillet001.Face7`; AP242 export reported `Added 1 AP242 affected-plane associations after STEP write` with no null-reference warning. |
| Projected-zone and unequal-disposition AP242 export | Passed | Create a position FCF with MMC and projected-zone height, plus a face-backed surface profile FCF with a circled `U` unequal-disposition offset. Export should report `Added ... projected zone definitions` and `Added ... unequally disposed profile tolerance entities`; STEP text should contain `PROJECTED_ZONE_DEFINITION`, `GEOMETRIC_TOLERANCE_WITH_MODIFIERS`, and `UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE` with no null-reference warning. |
| Line-profile FCF from controlled face plus direction line | Passed | GUI created `lineprofile tolerance on Fillet001.Face7` from a controlled face plus direction line. FreeCAD reported attachment ambiguity warnings while creating/attaching the line, but the MBD command created the FCF on the face and export proceeded. |
| Line-profile FCF from whole DatumLine selection | Passed | GUI created `lineprofile tolerance on Fillet001.Edge51`; export `MBDTest01_BR.step` reported `Creating semantic lineprofile tolerance on Fillet001.Edge51`. This is useful for curve-profile cases, but the preferred surface-section workflow is face plus direction line. |
| Line-profile unequal-disposition AP242 export | Passed | GUI export `MBDTest01_BQ.step` reported `Creating semantic lineprofile tolerance on Fillet001.Face7` and `Added 1 AP242 unequally disposed profile tolerance entities after STEP write` with no null-reference warning. The direction line is preserved in FreeCAD metadata; AP242 section-direction export remains a future refinement. Export `MBDTest01_BR.step` showed multiple line profiles; face-backed line-profile unequal-disposition mapping now matches by controlled face, while multiple edge-backed mappings remain deferred because STEP edge numbering is ambiguous after writer edge sharing. |
| Part Design link-scope warning cleanup | Passed | Restart FreeCAD, activate MBD, and confirm the report view says existing MBD geometry links were updated to global scope. Create a datum, datum target, dimension, and FCF on Body features; the transient `go out of the allowed scope` warnings should no longer appear. Save and reopen the document to confirm links remain intact. |
| Readable datum-system names in FCF dialogs | Passed | Restart FreeCAD and open each FCF datum-system picker. Confirm common and compartment notation matches the model-tree label, for example `MBD_DatumSystem_A-B_C`, rather than the sanitized internal name `MBD_DatumSystem_A_B__C`. |
| `Show PMI Inspector` then `Select Suspect` | Passed | Confirms warning/error rows can drive selection/highlighting. |
| `Validate PMI` command | Passed | Confirms the non-docked validation path still reports useful results. |
| `Create GD&T Symbol Table` | Removed | Development-only symbol-rendering test command removed from the final workbench UI; FCF symbols continue to render through the normal annotation view providers. |
| Diameter dimension on a hole or cylinder | Passed | Confirms diameter symbol display and cylinder-axis detection. |
| Radius dimension on a cylinder or arc-like face | Passed | Less central than diameter, but implemented as a dimension kind. |
| Unequal bilateral dimension | Passed | Separate path from equal bilateral dimensions. |
| Limits dimension | Passed | Separate display/string/value logic from plus/minus tolerances. |
| Angular dimension creation, display, and AP242 export | Passed | GUI validation and export passed with `MBD_Dimension007: EqualBilateral Angular 45.0000` and `MBDTest01_BK.step`; export reported `Creating semantic angular dimension ... using AP242 post-write entities` and `Added 1 AP242 angular dimension entities after STEP write.` Display now uses the degree symbol `°` rather than `deg`. |
| Equal bilateral validation after manual property edit | Passed | GUI validation lists the dimension and reports that equal bilateral tolerance requires equal upper and lower values after a one-sided tolerance edit. |
| Basic/reference dimension tolerance rejection | Passed | GUI validation reports that a Basic dimension must not carry plus/minus tolerance values. The tested basic size dimension also correctly reported the separate requirement for profile FCF control. |
| Equal bilateral diameter dimension export | Passed | GUI export log for `MBDTest01_AL.step` says `Creating semantic diameter dimension on Fillet001.Face17`. Export continued after stale datum warning. |
| Unequal bilateral radius dimension export | Passed | GUI export log for `MBDTest01_AL.step` says `Creating semantic radius dimension on Fillet001.Face14`. Export continued after stale datum warning. |
| Limits-style diameter, radius, or thickness dimension export | Passed | GUI export `MBDTest01_AM.step` contains AP242 `DIMENSIONAL_SIZE` entities for diameter, radius, and thickness with no `DIMENSIONAL_LOCATION` or `NUL REF` hits. |
| Radius annotation on fillet/round face | Passed | Confirm radius callout uses `R`, points to the visible curved feature from outside the solid, and does not render as a center-to-interior linear width. |
| Hole-axis location dimension on through hole | Passed | Create axis-to-datum dimensions for a through hole and confirm leader lines/display identify the visible hole axis clearly. |
| Hole-axis location dimension on blind drilled/countersunk hole | Passed | Repeat on a blind/countersunk/drill-point hole; confirm the preferred display side is the opening side. |
| External cylinder axis-to-datum dimension | Passed | Create an axis-to-datum dimension for an external boss/cylinder and confirm the axis and display direction are reasonable. |
| Linear plane-to-plane size/thickness dimension export | Passed | GUI export `MBDTest01_AM.step` contains `DIMENSIONAL_SIZE(...,'thickness')`; axis/location linear dimensions still skip as intended. |
| Linear location dimension export remains intentionally skipped | Superseded | Replaced by initial AP242 `DIMENSIONAL_LOCATION` export. |
| Basic size dimension without profile control | Passed | Validation reported the expected basic-size-without-profile error; adding profile all-over cleared the issue. |
| AP242 export of diameter or radius size dimension with plus/minus tolerance | Passed | GUI export created a semantic diameter dimension; `MBDTest01_AJ.step` contains `DIMENSIONAL_SIZE`, `SHAPE_DIMENSION_REPRESENTATION`, `DIMENSIONAL_CHARACTERISTIC_REPRESENTATION`, and `PLUS_MINUS_TOLERANCE` with no null/unknown references. |
| AP242 export of radius dimension through post-write size path | Passed | GUI export `MBDTest01_BH.step` reported two fillet radius dimensions using AP242 post-write entities and `Added 2 AP242 dimensional size entities after STEP write.` |
| AP242 export with linear location dimensions present | Superseded | Earlier test confirmed unsupported linear dimensions were skipped safely. Replaced by the new `AP242 export of linear location dimensions` test. |
| AP242 export of linear location dimensions | Passed | GUI exports `MBDTest01_AN.step` and `MBDTest01_AP.step` reported post-write AP242 dimensional location entities; `MBDTest01_AP.step` contains eight `DIMENSIONAL_LOCATION` entities, four position tolerances, and no `NUL REF` or unknown references. |
| Combined semantic dimension AP242 export | Passed | GUI export `MBDTest01_BH.step` reported semantic diameter, radius, and linear dimensions; radius dimensions used the post-write AP242 size path and export completed cleanly. |
| AP242 export of dimensions attached to upstream PartDesign feature faces | Passed | Create diameter/radius/linear dimensions on faces selected from an upstream feature such as `Fillet001`, then export the final Body. Export should resolve matching faces on the final Body or skip unsupported dimensions with warnings; STEP text must not contain `NUL REF` or `DIMENSIONAL_SIZE($`. |
| AP242 export of point datum targets | Passed | GUI export `MBDTest01_AT.step` created A1/A2/A3; STEP text contains three `PLACED_DATUM_TARGET_FEATURE` entities, three `SHAPE_REPRESENTATION_WITH_PARAMETERS` entities, and three `FEATURE_FOR_DATUM_TARGET_RELATIONSHIP` entities with no null references. |
| Create and validate a line datum target | Passed | Select an MBD datum feature and one finite straight construction edge on its inspected face. Create the target and confirm the PMI Inspector reports a `Line` target with no error. Repeat with a curved edge and confirm creation is rejected. |
| Reject off-surface line datum target at creation | Passed | Select an MBD datum feature and a straight construction line that is perpendicular to, or otherwise not coincident with, the datum face. `Create Datum Target` should reject it immediately instead of creating a target that validation later flags. |
| Line datum target full-segment surface validation | Passed | Create a straight construction edge with one end off the inspected datum surface. Validation should report the line target's maximum distance from the surface rather than accepting it because one point touches. |
| AP242 export of a line datum target | Passed | GUI exports `MBDTest01_BF.step` and `MBDTest01_BG.step` reported `Creating semantic datum target C1 on Face7` and line-plus-point targets `A1/A2` on Face1. STEP text should still be checked before using these as permanent references. |
| Circular datum target creation and AP242 export | Passed | Select an MBD datum feature and one datum point lying on the datum face. Run `Create Datum Target`, choose `Circle` as the target shape, and enter a diameter with units. Confirm PMI Inspector reports `Circle`; the 3D view should show a circular target area centered on the point. AP242 export should report `Creating semantic datum target ...` and STEP text should contain `PLACED_DATUM_TARGET_FEATURE('','circle'` with no `NUL REF`. |
| Rectangular datum target creation and AP242 export | Passed | GUI export `MBDTest01_BL.step` created rectangle target A1 from a datum point and reported `Creating semantic datum target A1 on Face1`; export completed with no null-reference warning. CAx-IF AP242 practice defines rectangle length along placement X and width along derived Y, so the current inferred datum-plane frame is acceptable as a first implementation. Future refinement: add explicit user control for rectangular target in-plane orientation. |
| Mixed point/line datum-target sufficiency | Passed | For a primary datum, confirm one line target alone is underdefined and one line plus one point clears the sufficiency error. For a secondary datum, confirm one line target clears the conservative sufficiency check. |
| Target-based primary datum with only two point targets | Passed | Validation reported `target-based primary datum A, but 3 point targets are required and 2 are defined.` |
| Target-based primary/secondary/tertiary datum sufficiency | Passed | Create A1/A2/A3, B1/B2, and C1 for an A|B|C datum system; validation should not report target-count sufficiency errors. |
| Primary-only individual datum system | Passed | GUI angularity FCF displayed one `A` datum cell. `MBDTest01_BA.step` contains a one-compartment `DATUM_SYSTEM` referencing A and an `ANGULARITY_TOLERANCE`, with no null or unknown references. |
| Primary-only common datum system | Passed | GUI created `A-B` as one primary compartment; the PMI Inspector reports attachment `A-B` with no validation issues. |
| Mixed common/individual datum system | Passed | GUI created `A-B | C`; the position FCF displayed `A-B` in one primary cell and `C` in the next compartment. |
| Common secondary datum system | Passed | GUI created `A | B-C`; the PMI Inspector preserves B-C as one common secondary compartment and reports no validation issues. |
| Datum system duplicate rejection | Passed | Put the same datum in more than one compartment. Confirm creation is rejected with `A datum feature cannot appear in more than one compartment.` |
| Datum system gap rejection | Passed | Define Primary and Tertiary while leaving Secondary empty. Confirm creation is rejected. |
| AP242 export with common datum | Passed | GUI export `MBDTest01_AW.step` contains two `DATUM_REFERENCE_ELEMENT`s in one `COMMON_DATUM_LIST`, a separate C compartment, and one `DATUM_SYSTEM`, with no null or unknown references. |
| Orientation FCF using a common datum system | Passed | GUI created perpendicularity on `Pad003.Face19` using `A-B | C`; the FCF displayed separate `A-B` and `C` cells. `MBDTest01_AY.step` contains `PERPENDICULARITY_TOLERANCE`, the common-datum structure, and no null or unknown references. |
| Position FCF attached to a hole with diameter zone | Passed | Confirms FCF below-dimension display and diameter/position symbols together. |
| Position FCF defaults to the visible hole opening | Passed | On a blind or countersunk hole, create a position FCF before manually moving it. Confirm the FCF and its leader are placed out the open end of the hole, matching the preferred side used by the hole diameter dimension. |
| AP242 export of a clean model with datums and position FCF | Passed | Confirms known-good semantic export path remains intact. |
| AP242 export with flatness, parallelism, perpendicularity, or profile present | Passed | These FCFs now export semantically instead of warning/skipping; GUI export should confirm no null references and expected Report view messages. |
| Stale/topology-drift warning and cancel | Passed | Export warned about stale `MBD_FCF_Flatness`; cancel produced `AP242 export cancelled by user.` |
| Profile FCF all-over with no selection | Passed | With one body and datum system `<none>`, attached to `Body (all over)`, geometry `Whole body`, and validated cleanly. |
| Profile FCF all-over with whole body selected | Passed | Whole-body selection with datum system `<none>` attached to `Body (all over)`, geometry `Whole body`, and validated cleanly. |
| Profile FCF all-over with datum system selected | Passed | Body-level all-over with `MBD_DatumSystem_A_B_C` validated cleanly and showed datum-system reference in the report. |
| Profile FCF not all-over on a selected face | Passed | Face-level profile validated cleanly with both an existing datum system and datum system `<none>`. |
| Profile FCF not all-over with no selection | Passed | Rejected with `Select exactly one controlled feature.` |
| Profile FCF all-over in a multi-body document with no selection | Passed | Rejected with `Select one body, or leave nothing selected only when the document has exactly one body.` |
| Angularity FCF with one datum reference | Passed | GUI created angularity on `Pad003.Face6` with datum A; `MBDTest01_AG.step` contains `ANGULARITY_TOLERANCE`. |
| Line profile FCF on selected edge | Passed | GUI created line profile on `Pad003.Edge13` after adding the missing `⌒` display mapping. |
| Line profile FCF on selected face without direction is rejected | Passed | Select only a face, choose `LineProfile`, and confirm the command reports that line profile must be attached to an edge/curve or to a face with a direction line. |
| AP242 export with line profile FCF | Passed | GUI export `MBDTest01_AU.step` reported `Creating semantic lineprofile tolerance on Pad003.Edge13`. |
| Straightness FCF | Passed | GUI created straightness on `Pad003.Face20`; `MBDTest01_AG.step` contains `STRAIGHTNESS_TOLERANCE`. |
| Circularity FCF | Passed | GUI created circularity on `Pad003.Face20`; `MBDTest01_AG.step` contains AP242 `ROUNDNESS_TOLERANCE`. |
| Cylindricity FCF | Passed | GUI created cylindricity on `Pad003.Face20`; `MBDTest01_AG.step` contains `CYLINDRICITY_TOLERANCE`. |
| Circular runout FCF with one datum reference | Passed | GUI created circular runout on `Pad003.Face20` with datum A; `MBDTest01_AG.step` contains `CIRCULAR_RUNOUT_TOLERANCE`. |
| Total runout FCF with one datum reference | Passed | GUI created total runout on `Pad003.Face20` with datum A; `MBDTest01_AG.step` contains `TOTAL_RUNOUT_TOLERANCE`. |
| Circular or total runout with datum system containing an axis datum | Passed | GUI created total runout on `Pad003.Face19` using datum system `A | D | C`; export `MBDTest01_AV.step` reported `Creating semantic totalrunout tolerance on Pad003.Face19`. |
| Expanded AP242 FCF export set | Passed | `MBDTest01_AH.step` contains position, flatness, parallelism, perpendicularity, surface profile, angularity, straightness, roundness, cylindricity, circular runout, and total runout; expanded STEP text check passed. |
