# FreeCAD MBD Workbench Project Plan

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

Semantic point datum targets are modeled in FreeCAD and now export as AP242
placed datum target features. Semantic dimensions export for diameter, radius,
plane-to-plane thickness, and initial linear feature-location cases.

## Important Implementation Notes

- `MBDExporter.py` uses XCAF/AP242 semantic entities for datums and position
  tolerances.
- Keep the direct `TDataStd_Integer` and `TDataStd_Real` child-label workaround
  for geometric tolerances unless a replacement is verified against pythonocc
  and OCCT.
- Current visible PMI is FreeCAD-side display helper geometry, not AP242
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

## Milestones

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
| Visualization | Position FCF display below related feature dimension when possible | Done | Needs continued GUI testing across feature types. |
| Visualization | Exterior leader placement for surface FCFs | Done | Uses surface/solid probing to avoid drawing through the solid. |
| Tolerances | Parallelism FCF definition with a single datum-reference surface | Done | Display, validation, and semantic AP242 export are in place. |
| Testing | Headless smoke/regression harness using FreeCAD command line | Done | Used for exporter, validation, and display regressions. |

## Near-Term Priorities

| Priority | Milestone | Status | Notes |
| --- | --- | --- | --- |
| 1 | Add a top-level `MBD PMI` group | Done | GUI test passed; top-level group reduces model-tree congestion. |
| 1 | Put semantic PMI objects under `MBD PMI` | Done | GUI test passed; new and existing semantic PMI are organized under the group. |
| 1 | Keep helper display objects grouped under their semantic owner | Done | Current helper-object display paths are grouped under semantic owners; future custom view-provider work is tracked separately. |
| 2 | Add flatness semantic AP242 export | Done | Headless and GUI export logs confirm semantic flatness export. |
| 2 | Add parallelism semantic AP242 export | Done | Headless and GUI export logs confirm semantic parallelism export with a datum reference. |
| 2 | Add perpendicularity support | Done | Display, validation, and semantic AP242 export are in place; GUI export log confirms semantic perpendicularity export. |
| 2 | Add profile of a surface support | Done | Display, validation, body-level all-over handling, and semantic AP242 export are in place; GUI export log confirms semantic profile export. |
| 2 | Add remaining direct geometric FCF AP242 exports | Done | Line profile, angularity, straightness, circularity/roundness, cylindricity, circular runout, and total runout export semantically; headless and GUI export tests have passed. |
| 3 | Add robust linear dimensions between parallel planes | Done | Plane-to-plane size/thickness displays, validates, and exports as AP242 `DIMENSIONAL_SIZE('thickness')`; feature-location dimensions export as AP242 `DIMENSIONAL_LOCATION`. |
| 3 | Add diameter and radius dimensions | Done | Diameter/radius display, validation, GUI testing, and AP242 `DIMENSIONAL_SIZE` export are in place; annotation cosmetic cleanup is tracked separately. |
| 3 | Add axis-to-datum dimensions for holes and revolved features | Done | Through-hole, blind/countersunk hole, and external-cylinder GUI behavior passed; AP242 `DIMENSIONAL_LOCATION` export is verified on complex-hole cases. Remaining refinements are annotation cosmetics. |
| 3 | Add equal bilateral, unequal bilateral, and limits representation | Done | Equal bilateral, unequal bilateral, and limits are implemented and export for size dimensions; no separate min/max mode is planned. |
| 3 | Validate that basic dimensions do not define toleranced size without an associated FCF | Done | Basic size dimensions now require profile control; profile all-over satisfies this rule. |
| 4 | Stabilize text size across all visible PMI | In progress | Regressions exist for helper objects not affecting text scale; GUI test still showed oversize basic-dimension text. |
| 4 | Improve leader, arrow, box, and text placement | In progress | Continue aligning with ASME Y14.5 conventions. |
| 4 | Improve hole-axis dimension placement | In progress | Functional behavior passed; keep this open only for annotation/readability refinements. |

## AP242 Export Roadmap

| Milestone | Status | Notes |
| --- | --- | --- |
| Preserve current datum and position FCF export behavior | Ongoing | Regression tests should guard this as new tolerance types are added. |
| Add semantic export for flatness | Done | Implemented through XCAF geometric tolerance child labels and covered by STEP text checks. |
| Add semantic export for parallelism with a single datum reference | Done | Uses `DatumReference` and links the referenced datum to the geometric tolerance. |
| Add semantic export for perpendicularity and other orientation controls | Done | Perpendicularity implemented using the same one-datum-reference path as parallelism. |
| Add semantic export for profile controls | Done | Surface profile implemented for face-level and all-over profile; all-over currently targets the exported face set. |
| Add semantic export for remaining direct geometric tolerance controls | Done | Line profile, angularity, straightness, circularity/roundness, cylindricity, circular runout, and total runout are mapped through the same XCAF geometric tolerance path and covered by STEP text checks. |
| Add semantic dimension export | Done | GUI export `MBDTest01_AR.step` verified diameter, radius, plane-to-plane thickness, and linear location dimensions together with a position FCF and no null references. Directed/path dimension variants remain future AP242 coverage items. |
| Design angular semantic dimension workflow | Future | No current GUI workflow exists. Future work should decide how users select planar faces/edges, how nominal angular values are inferred from model geometry, how angular dimensions are displayed, and whether AP242 export should use `ANGULAR_SIZE` or `ANGULAR_LOCATION`. |
| Add semantic point datum target export | Done | Point datum targets export through OCCT/XCAF as `PLACED_DATUM_TARGET_FEATURE` with `FEATURE_FOR_DATUM_TARGET_RELATIONSHIP`; headless and GUI STEP checks passed. |
| Add common-datum and flexible datum-system definition/export | Done | Datum systems now contain one to three ordered compartments; each compartment accepts one datum or multiple simultaneous common datums such as `A-B`. XCAF/AP242 export writes `COMMON_DATUM_LIST` and the corresponding datum reference elements. |
| Add semantic line datum target definition/export | Future | Requires GUI support for selecting/defining target line length, direction, and attachment validation. |
| Add semantic circular/rectangular/area datum target definition/export | Future | Requires GUI support for target area size, shape, orientation, and validation on nominal surfaces. |
| Validate datum target constraint adequacy in datum systems | Partial | Conservative point-target count validation is implemented for primary/secondary/tertiary datum roles; richer point-line/area target combinations remain future work. |
| Add AP242 presentation PMI export | Future | Do after semantic model and display layout properties stabilize. |

## AP242 PMI Coverage Matrix

Source for this matrix: local OCCT AP242/STEP support in `RWStepAP214_ReadWriteModule.cxx`, `StepDimTol`, and `StepShape`. Status separates whether the add-on can define the concept in the FreeCAD model from whether it writes the corresponding semantic AP242 STEP entity.

### Geometric Tolerances

| AP242 entity | GD&T concept | FreeCAD model status | AP242 export status | Notes |
| --- | --- | --- | --- | --- |
| `POSITION_TOLERANCE` | Position | Done | Done | Supports datum system references and diameter tolerance zone. |
| `FLATNESS_TOLERANCE` | Flatness | Done | Done | Surface FCF with no datum reference. |
| `PARALLELISM_TOLERANCE` | Parallelism | Done | Done | One datum-reference feature supported. |
| `PERPENDICULARITY_TOLERANCE` | Perpendicularity | Done | Done | One datum-reference feature supported. |
| `SURFACE_PROFILE_TOLERANCE` | Profile of a surface | Done | Done | Face-level and all-over profile modeled; all-over export currently targets the exported face set. |
| `LINE_PROFILE_TOLERANCE` | Profile of a line | Partial | Done | Edge-attached line profile is modeled, validated, displayed with the profile-of-line symbol, and exported as AP242 `LINE_PROFILE_TOLERANCE`; richer section/curve semantics remain future work. |
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
| `DATUM_TARGET` | Datum target | Partial | Partial | Point targets export as the placed datum target subtype; area target support is tracked separately. |
| `PLACED_DATUM_TARGET_FEATURE` | Placed target feature | Partial | Partial | Point datum targets export with target axis/orientation parameters. Line, rectangle, and circle targets are future expansions. |
| `FEATURE_FOR_DATUM_TARGET_RELATIONSHIP` | Target-to-feature relationship | Partial | Partial | Exported for point datum targets to connect the target feature to the inspected datum feature. |

### Dimensions And Size/Location Controls

| AP242 entity | Dimension concept | FreeCAD model status | AP242 export status | Notes |
| --- | --- | --- | --- | --- |
| `DIMENSIONAL_SIZE` | Feature size such as diameter, radius, width, thickness | Done | Done | Diameter/radius and plane-to-plane thickness dimensions validate and export as AP242 `DIMENSIONAL_SIZE`; path-defined size remains a separate future entity family. |
| `DIMENSIONAL_SIZE_WITH_PATH` | Size with path | Not started | Not started | Needed for more complex path-defined size cases. |
| `DIMENSIONAL_LOCATION` | Location between features | Partial | Partial | Axis/plane/point location dimensions exist. Direct OCCT export produced a null second shape reference, so the exporter now appends a narrow face-backed AP242 `DIMENSIONAL_LOCATION` entity set after STEP write. GUI exports `MBDTest01_AN.step`, `MBDTest01_AP.step`, and `MBDTest01_AR.step` created location dimensions with no null references. Plane-to-plane size is handled separately as thickness. |
| `DIRECTED_DIMENSIONAL_LOCATION` | Directed linear location | Partial | Partial | Treat as an exporter-side AP242 representation choice, not a user-facing dimension mode. The workbench should continue letting users define the meaningful model dimension; the exporter may choose `DIRECTED_DIMENSIONAL_LOCATION` when the semantic dimension and AP242 mapping require it. |
| `DIMENSIONAL_LOCATION_WITH_PATH` | Location with path | Not started | Not started | Needed for path-dependent location dimensions. |
| `ANGULAR_SIZE` | Angular size | Not started | Not started | Angular dimension model is enumerated but intentionally rejected by validation until UI selection, display, and AP242 export semantics are designed. |
| `ANGULAR_LOCATION` | Angular location | Not started | Not started | Needed for angular basic/location dimensions that support controls such as angularity; do not encode this inside an FCF. |
| `SHAPE_DIMENSION_REPRESENTATION` | Dimension value representation | Done | Done | Exported for supported size and location dimensions and covered by STEP text regression. |
| `DIMENSIONAL_CHARACTERISTIC_REPRESENTATION` | Link from dimension characteristic to representation | Done | Done | Exported for supported size and location dimensions and covered by STEP text regression. |
| `PLUS_MINUS_TOLERANCE` | Equal/unequal bilateral tolerance | Done | Done | Equal and unequal bilateral dimensions validate semantically and export for supported size and location dimensions. |
| `TOLERANCE_VALUE` | Limit or plus/minus tolerance values | Done | Done | Equal bilateral, unequal bilateral, and limits values validate and export for the supported dimension families. |

### Geometric Tolerance Modifiers And Zones

| AP242 entity | Concept | FreeCAD model status | AP242 export status | Notes |
| --- | --- | --- | --- | --- |
| `GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE` | FCF with datum reference | Done | Done | Used for position, parallelism, perpendicularity, and profile with datum system. |
| `GEOMETRIC_TOLERANCE_WITH_MODIFIERS` | FCF modifiers | Partial | Partial | Profile all-over modifier is stored/exported through XCAF modifier child labels; broader modifier UI is pending. |
| `MODIFIED_GEOMETRIC_TOLERANCE` | Modified tolerance family | Not started | Not started | Needs modifier model design. |
| `UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE` | Unequally disposed tolerance zone | Not started | Not started | Separate from unequal bilateral dimensions. |
| `GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE` | Maximum tolerance modifier | Not started | Not started | Requires max-value modifier UI/model. |
| `GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT` | Defined-unit geometric tolerance | Not started | Not started | Needed for non-length tolerance units. |
| `GEOMETRIC_TOLERANCE_WITH_DEFINED_AREA_UNIT` | Area-unit tolerance | Not started | Not started | Specialized case. |
| `TOLERANCE_ZONE` | Tolerance zone | Partial | Partial | Position diameter zone exports a tolerance zone; broader zone support pending. |
| `TOLERANCE_ZONE_FORM` | Zone form | Partial | Partial | Cylindrical/circular form appears for diameter position tolerance. |
| `TOLERANCE_ZONE_DEFINITION` | Zone definition | Not started | Not started | Needed for richer zone geometry. |
| `RUNOUT_ZONE_DEFINITION` | Runout zone definition | Partial | Partial | Generated by OCCT for current position diameter-zone path; true runout controls not modeled. |
| `RUNOUT_ZONE_ORIENTATION` | Runout zone orientation | Partial | Partial | Generated by OCCT in current position diameter-zone path. |

### Presentation PMI

| AP242 entity family | Concept | FreeCAD model status | AP242 export status | Notes |
| --- | --- | --- | --- | --- |
| `DIMENSION_CURVE` / `DIMENSION_CURVE_TERMINATOR` | Visible dimension lines and arrows | View-provider display only | Not started | Current Coin3D dimension geometry is FreeCAD-native, not AP242 presentation PMI. |
| `PRESENTATION_SIZE` | Presentation text/symbol sizing | View-provider display only | Not started | Text size is stored in FreeCAD display-layout metadata; AP242 presentation sizing is not exported. |
| Draughting/presentation annotation entities | Visible PMI graphics | Helper display only | Future | Defer until semantic export and display-layout properties stabilize. |

## Annotation Architecture Roadmap

| Phase | Milestone | Status | Notes |
| --- | --- | --- | --- |
| Short term | Continue using helper objects for rapid iteration | Done | All current semantic annotation types now have owning view-provider rendering; helper creation remains only as migration/legacy cleanup code. |
| Short term | Organize helper objects so the model tree remains usable | Done | `MBD PMI` group and semantic-owner grouping remain available for annotation types that still use helpers. |
| Medium term | Define stable display-layout properties for each semantic PMI object | Done | Semantic PMI objects now store versioned origin, plane normal, reading direction, text height, layout mode, and a layout lock; save/reopen persistence is covered headlessly. |
| Medium term | Avoid storing derived visual geometry when it can be regenerated | Done | Datum features, FCFs, datum targets, and dimensions regenerate visible geometry through their owning view providers. |
| Long term | Replace helper display objects with custom FreeCAD view-provider rendering | Done | Current datum, target, FCF, and dimension annotations each have a single-tree-item implementation. |
| Long term | Draw lines, boxes, symbols, leaders, and text through the owning PMI view provider | Done | Current semantic annotation owners draw their complete visible annotation directly with Coin3D. |
| Long term | Allow manual annotation placement in the 3D view | In progress | Datum features, FCFs, targets, and dimensions share persistent planar movement behavior; datum-feature and datum-target GUI validation is required. |

## Import Roadmap

After semantic export is reliable:

| Milestone | Status | Notes |
| --- | --- | --- |
| Investigate AP242 import of semantic PMI into FreeCAD MBD objects | Future | Start after export semantics are more complete. |
| Reconstruct visible PMI from imported semantic and presentation data | Future | Requires display-layout architecture decisions. |
| Preserve imported PMI IDs/history where possible | Future | Depends on what source AP242 files provide. |
| Validate imported attachments against FreeCAD topology and geometry signatures | Future | Same principle as export validation. |

## Regression Test Goals

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
| Visible PMI helper objects do not affect PMI text-height scaling | Done | Covered by display regression. |
| Parallelism FCF validates with one datum reference | Done | Covered by headless smoke test. |
| Perpendicularity FCF validates with one datum reference | Done | Covered by headless smoke test. |
| Profile FCF validates with datum system references | Done | Covered by headless smoke test. |
| Profile all-over FCF validates without datum references | Done | Covered by headless smoke test with body-level attachment and `ALL OVER` display cell. |
| Flatness AP242 export entity checks | Done | Covered by all-FCF STEP text regression. |
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
| Size dimension AP242 export entity checks | Done | Headless regression confirms `DIMENSIONAL_SIZE`, `SHAPE_DIMENSION_REPRESENTATION`, `DIMENSIONAL_CHARACTERISTIC_REPRESENTATION`, `TOLERANCE_VALUE`, and `PLUS_MINUS_TOLERANCE` with no null references. |
| Linear location dimension AP242 export entity checks | Done | Headless regression confirms the post-write AP242 `DIMENSIONAL_LOCATION` path creates `SHAPE_ASPECT`, `GEOMETRIC_ITEM_SPECIFIC_USAGE`, `SHAPE_DIMENSION_REPRESENTATION`, `DIMENSIONAL_CHARACTERISTIC_REPRESENTATION`, `TOLERANCE_VALUE`, and `PLUS_MINUS_TOLERANCE` with no null references. |
| Directed linear location dimension AP242 export entity checks | Done | Headless regression confirms the exporter can write `DIRECTED_DIMENSIONAL_LOCATION` with no null references when that AP242 subtype is selected internally. |
| Point datum target AP242 export entity checks | Done | Headless regression confirms `PLACED_DATUM_TARGET_FEATURE`, `SHAPE_REPRESENTATION_WITH_PARAMETERS`, and `FEATURE_FOR_DATUM_TARGET_RELATIONSHIP` with no null references. |
| Datum target sufficiency validation | Done | Headless regression confirms underdefined primary and secondary point-target datum sets are reported and complete 3/2 target sets clear validation. |
| Stable semantic PMI display-layout metadata | Done | Headless regression confirms all semantic PMI types receive the layout schema, locked layouts reject automatic overwrite, and values survive FCStd save/reopen. |
| Dimension purpose and reference semantic rules | Done | Headless regression rejects unequal values marked equal bilateral, tolerance values on basic/reference dimensions, and diameter/radius dimensions with a second reference. |
| Global-scope links to Part Design geometry | Done | Model and construction geometry references use `App::PropertyLinkGlobal`; headless regression covers new datum, target, dimension, and FCF links, legacy-link migration, local PMI/display links, and FCStd save/reopen. |

## GUI Test Punch List

Use this section for manual FreeCAD testing. Update `Result` and `Notes` as
tests are completed.

| Test Case | Result | Notes |
| --- | --- | --- |
| `Show PMI Inspector` then `Copy Report` | Passed | Confirms the debugging handoff path still works. |
| MBD toolbar command icons | Passed | Restart FreeCAD and confirm all nine SVG icons render crisply, remain distinguishable at toolbar size, and have acceptable contrast with the current FreeCAD theme. |
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
| Native annotation double-click after callback cleanup | Not run | Double-click a visible datum, dimension, and FCF, move each annotation, and place it. Confirm native view-provider selection still starts movement now that permanent per-object 3D callbacks are no longer registered. Tree context `Move annotation` remains the fallback. |
| Move and persist an FCF annotation from the 3D view | Passed | Double-clicking the visible FCF picks it up, mouse movement repositions it, and another left click places it. Tree context `Move annotation` remains a fallback. Future refinement: make interaction behave like Sketcher constraints or TechDraw annotations with a conventional press-drag-release gesture. |
| FCF view-provider symbol and text check | Passed | Check position with diameter, flatness, line profile, surface profile, and a datum-referenced orientation FCF. Confirm boxes, symbols, tolerance text, and datum compartments remain readable and lie in the annotation plane. Cosmetic differences can be recorded for the later cleanup phase. |
| Part Design link-scope warning cleanup | Passed | Restart FreeCAD, activate MBD, and confirm the report view says existing MBD geometry links were updated to global scope. Create a datum, datum target, dimension, and FCF on Body features; the transient `go out of the allowed scope` warnings should no longer appear. Save and reopen the document to confirm links remain intact. |
| Readable datum-system names in FCF dialogs | Passed | Restart FreeCAD and open each FCF datum-system picker. Confirm common and compartment notation matches the model-tree label, for example `MBD_DatumSystem_A-B_C`, rather than the sanitized internal name `MBD_DatumSystem_A_B__C`. |
| `Show PMI Inspector` then `Select Suspect` | Passed | Confirms warning/error rows can drive selection/highlighting. |
| `Validate PMI` command | Passed | Confirms the non-docked validation path still reports useful results. |
| `Create GD&T Symbol Table` | Passed | Confirms drawn GD&T symbols render in the current FreeCAD session. |
| Diameter dimension on a hole or cylinder | Passed | Confirms diameter symbol display and cylinder-axis detection. |
| Radius dimension on a cylinder or arc-like face | Passed | Less central than diameter, but implemented as a dimension kind. |
| Unequal bilateral dimension | Passed | Separate path from equal bilateral dimensions. |
| Limits dimension | Passed | Separate display/string/value logic from plus/minus tolerances. |
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
| AP242 export with linear location dimensions present | Superseded | Earlier test confirmed unsupported linear dimensions were skipped safely. Replaced by the new `AP242 export of linear location dimensions` test. |
| AP242 export of linear location dimensions | Passed | GUI exports `MBDTest01_AN.step` and `MBDTest01_AP.step` reported post-write AP242 dimensional location entities; `MBDTest01_AP.step` contains eight `DIMENSIONAL_LOCATION` entities, four position tolerances, and no `NUL REF` or unknown references. |
| Combined semantic dimension AP242 export | Passed | GUI export `MBDTest01_AR.step` contains `DIMENSIONAL_SIZE` for diameter, radius, and thickness; two `DIMENSIONAL_LOCATION` entities; `PLUS_MINUS_TOLERANCE`; a position FCF; and no null/unknown references. |
| AP242 export of point datum targets | Passed | GUI export `MBDTest01_AT.step` created A1/A2/A3; STEP text contains three `PLACED_DATUM_TARGET_FEATURE` entities, three `SHAPE_REPRESENTATION_WITH_PARAMETERS` entities, and three `FEATURE_FOR_DATUM_TARGET_RELATIONSHIP` entities with no null references. |
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
| Line profile FCF on selected face is rejected | Passed | Select a face, choose `LineProfile`, and confirm the command reports that line profile must be attached to an edge or curve. |
| AP242 export with line profile FCF | Passed | GUI export `MBDTest01_AU.step` reported `Creating semantic lineprofile tolerance on Pad003.Edge13`. |
| Straightness FCF | Passed | GUI created straightness on `Pad003.Face20`; `MBDTest01_AG.step` contains `STRAIGHTNESS_TOLERANCE`. |
| Circularity FCF | Passed | GUI created circularity on `Pad003.Face20`; `MBDTest01_AG.step` contains AP242 `ROUNDNESS_TOLERANCE`. |
| Cylindricity FCF | Passed | GUI created cylindricity on `Pad003.Face20`; `MBDTest01_AG.step` contains `CYLINDRICITY_TOLERANCE`. |
| Circular runout FCF with one datum reference | Passed | GUI created circular runout on `Pad003.Face20` with datum A; `MBDTest01_AG.step` contains `CIRCULAR_RUNOUT_TOLERANCE`. |
| Total runout FCF with one datum reference | Passed | GUI created total runout on `Pad003.Face20` with datum A; `MBDTest01_AG.step` contains `TOTAL_RUNOUT_TOLERANCE`. |
| Circular or total runout with datum system containing an axis datum | Passed | GUI created total runout on `Pad003.Face19` using datum system `A | D | C`; export `MBDTest01_AV.step` reported `Creating semantic totalrunout tolerance on Pad003.Face19`. |
| Expanded AP242 FCF export set | Passed | `MBDTest01_AH.step` contains position, flatness, parallelism, perpendicularity, surface profile, angularity, straightness, roundness, cylindricity, circular runout, and total runout; expanded STEP text check passed. |

## Cosmetic final touches

| Milestone | Status | Notes |
| --- | --- | --- |
| Review dimension terminology in user-facing dialogs | Future | Equal bilateral, unequal bilateral, and limits are the current supported names; only revisit wording if GUI testing shows confusion. |
| Tweak appearance of view-provider text and symbols for readability (size, line thickness, text view direction) | Future | Start after the full workstream from model definition in FreeCAD to complete export to AP242 has been thoroughly tested and verified|
| Create graphical symbols for each tool in the toolbar | Done | Nine 64x64 SVG command icons in `mbd_command_icons` are wired to the MBD toolbar and menu commands. |
| Comment all the code cleanly to make it sustainable | Future | Start after code is done|
