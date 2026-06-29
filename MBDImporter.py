# MBDImporter.py

import re


SUPPORTED = "Supported"
PARTIAL = "Partial"
NOT_IMPLEMENTED = "Not implemented"
DEFERRED = "Deferred"
DO_NOT_IMPLEMENT = "Do not implement"


AP242_PMI_ENTITY_SUPPORT = {
    "POSITION_TOLERANCE": (SUPPORTED, "Position FCFs are modeled and exported."),
    "FLATNESS_TOLERANCE": (SUPPORTED, "Flatness FCFs are modeled and exported."),
    "PARALLELISM_TOLERANCE": (SUPPORTED, "Parallelism FCFs are modeled and exported."),
    "PERPENDICULARITY_TOLERANCE": (SUPPORTED, "Perpendicularity FCFs are modeled and exported."),
    "SURFACE_PROFILE_TOLERANCE": (SUPPORTED, "Surface profile FCFs are modeled and exported."),
    "LINE_PROFILE_TOLERANCE": (PARTIAL, "Line profile exists, but richer section/curve semantics remain future work."),
    "ANGULARITY_TOLERANCE": (PARTIAL, "Angularity exists; nominal angular-dimension workflow remains future work."),
    "STRAIGHTNESS_TOLERANCE": (PARTIAL, "Straightness exists; derived-axis/surface-element distinctions remain future work."),
    "ROUNDNESS_TOLERANCE": (SUPPORTED, "Circularity/roundness FCFs are modeled and exported."),
    "CYLINDRICITY_TOLERANCE": (SUPPORTED, "Cylindricity FCFs are modeled and exported."),
    "CIRCULAR_RUNOUT_TOLERANCE": (PARTIAL, "Runout exists; richer datum-axis semantics remain future work."),
    "TOTAL_RUNOUT_TOLERANCE": (PARTIAL, "Runout exists; richer datum-axis and full-surface semantics remain future work."),
    "COAXIALITY_TOLERANCE": (DO_NOT_IMPLEMENT, "AP242 supports this, but ASME Y14.5-2018 does not."),
    "CONCENTRICITY_TOLERANCE": (DO_NOT_IMPLEMENT, "AP242 supports this, but ASME Y14.5-2018 removed it."),
    "SYMMETRY_TOLERANCE": (DO_NOT_IMPLEMENT, "AP242 supports this, but ASME Y14.5-2018 removed it."),
    "DATUM_FEATURE": (SUPPORTED, "Whole-face datum feature attachments are modeled and exported."),
    "DATUM": (SUPPORTED, "Datum identifiers are modeled and exported."),
    "DATUM_SYSTEM": (SUPPORTED, "Ordered individual/common datum systems are modeled and exported."),
    "DATUM_REFERENCE_ELEMENT": (SUPPORTED, "Datum-reference elements are exported through datum systems."),
    "DATUM_REFERENCE_COMPARTMENT": (SUPPORTED, "Datum-reference compartments are exported through datum systems."),
    "COMMON_DATUM": (SUPPORTED, "Common datum compartments are modeled and exported."),
    "COMMON_DATUM_LIST": (SUPPORTED, "Common datum lists are exported through datum systems."),
    "DATUM_REFERENCE": (PARTIAL, "Covered through datum-system export; standalone advanced references are not modeled."),
    "GENERAL_DATUM_REFERENCE": (PARTIAL, "Individual/common datum references exist; modifiers remain future work."),
    "DATUM_TARGET": (PARTIAL, "Point, line, circle, rectangle, and arbitrary area targets are modeled; arbitrary area export remains future work."),
    "PLACED_DATUM_TARGET_FEATURE": (PARTIAL, "Point, line, circle, and rectangle placed targets export; arbitrary area export remains future work."),
    "FEATURE_FOR_DATUM_TARGET_RELATIONSHIP": (PARTIAL, "Target-to-feature relationships are exported for point, line, circle, and rectangle targets."),
    "DIMENSIONAL_SIZE": (PARTIAL, "Diameter, radius, and thickness are supported; path-defined size remains future work."),
    "DIMENSIONAL_SIZE_WITH_PATH": (NOT_IMPLEMENTED, "Path-defined size dimensions are not modeled yet."),
    "DIMENSIONAL_LOCATION": (PARTIAL, "Face-backed linear locations are supported; path variants remain future work."),
    "DIRECTED_DIMENSIONAL_LOCATION": (PARTIAL, "Exporter can emit directed locations internally; no user-facing mode exists."),
    "DIMENSIONAL_LOCATION_WITH_PATH": (NOT_IMPLEMENTED, "Path-defined location dimensions are not modeled yet."),
    "ANGULAR_SIZE": (PARTIAL, "Face-backed angular dimensions are modeled/exported; richer edge/axis and path cases remain future work."),
    "ANGULAR_LOCATION": (PARTIAL, "Face-backed angular locations are modeled/exported; richer edge/axis and path cases remain future work."),
    "SHAPE_DIMENSION_REPRESENTATION": (SUPPORTED, "Dimension value representations are supported for implemented dimensions."),
    "DIMENSIONAL_CHARACTERISTIC_REPRESENTATION": (SUPPORTED, "Dimension-characteristic representation links are supported."),
    "PLUS_MINUS_TOLERANCE": (SUPPORTED, "Plus/minus tolerances are supported for implemented dimension families."),
    "TOLERANCE_VALUE": (SUPPORTED, "Tolerance values are supported for implemented dimension families."),
    "GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE": (SUPPORTED, "Datum-referenced FCFs are modeled and exported."),
    "GEOMETRIC_TOLERANCE_WITH_MODIFIERS": (PARTIAL, "Profile all-over and MMC/LMC material modifiers export; projected-zone and unequal-disposition export remain future work."),
    "MODIFIED_GEOMETRIC_TOLERANCE": (PARTIAL, "MMC/LMC are modeled/displayed/validated for conservative position cases and export as material-requirement modifiers."),
    "UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE": (PARTIAL, "Unequally disposed profile zones are modeled/displayed/validated; export remains future work."),
    "GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE": (NOT_IMPLEMENTED, "Maximum tolerance modifier is not implemented yet."),
    "GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT": (NOT_IMPLEMENTED, "Defined-unit geometric tolerances are not implemented yet."),
    "GEOMETRIC_TOLERANCE_WITH_DEFINED_AREA_UNIT": (NOT_IMPLEMENTED, "Area-unit geometric tolerances are not implemented yet."),
    "TOLERANCE_ZONE": (PARTIAL, "Position diameter zones are supported; broader zone definitions remain future work."),
    "TOLERANCE_ZONE_FORM": (PARTIAL, "Cylindrical/circular position zones are supported; broader forms remain future work."),
    "TOLERANCE_ZONE_DEFINITION": (NOT_IMPLEMENTED, "Richer tolerance zone definitions are not implemented yet."),
    "RUNOUT_ZONE_DEFINITION": (PARTIAL, "Generated by OCCT in limited paths; true runout zone modeling remains future work."),
    "RUNOUT_ZONE_ORIENTATION": (PARTIAL, "Generated by OCCT in limited paths; true runout zone modeling remains future work."),
    "DIMENSION_CURVE": (DEFERRED, "AP242 presentation PMI is deferred."),
    "DIMENSION_CURVE_TERMINATOR": (DEFERRED, "AP242 presentation PMI is deferred."),
    "PRESENTATION_SIZE": (DEFERRED, "AP242 presentation sizing is deferred."),
}


STEP_ENTITY_PATTERN = re.compile(
    r"#\d+\s*=\s*(.*?);",
    re.IGNORECASE | re.DOTALL
)


def _known_entities_in_step_body(body):
    body_upper = body.upper()
    entities = []

    for entity in AP242_PMI_ENTITY_SUPPORT:
        if re.search(r"\b{}\s*\(".format(re.escape(entity)), body_upper):
            entities.append(entity)

    return entities


def scan_step_pmi_entities(filepath):
    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    counts = {}

    for match in STEP_ENTITY_PATTERN.finditer(text):
        body = match.group(1)

        for entity in _known_entities_in_step_body(body):
            counts[entity] = counts.get(entity, 0) + 1

    findings = []

    for entity in sorted(counts):
        status, note = AP242_PMI_ENTITY_SUPPORT[entity]
        findings.append({
            "entity": entity,
            "count": counts[entity],
            "status": status,
            "note": note,
        })

    partial = [
        finding for finding in findings
        if finding["status"] == PARTIAL
    ]
    unsupported = [
        finding for finding in findings
        if finding["status"] in {NOT_IMPLEMENTED, DEFERRED, DO_NOT_IMPLEMENT}
    ]
    status_counts = {}

    for finding in findings:
        status_counts[finding["status"]] = (
            status_counts.get(finding["status"], 0) + finding["count"]
        )

    return {
        "filepath": filepath,
        "findings": findings,
        "partial": partial,
        "unsupported": unsupported,
        "status_counts": status_counts,
    }


def format_step_pmi_scan_report(scan):
    lines = [
        "AP242 PMI Coverage Report",
        "",
        "File: {}".format(scan["filepath"]),
        "",
    ]

    if not scan["findings"]:
        lines.append("No known AP242 PMI entities were detected.")
        return "\n".join(lines)

    lines.append("Summary:")

    for status in [SUPPORTED, PARTIAL, NOT_IMPLEMENTED, DEFERRED, DO_NOT_IMPLEMENT]:
        count = scan["status_counts"].get(status, 0)

        if count:
            lines.append("- {}: {}".format(status, count))

    lines.append("")
    lines.append("Detected PMI entities:")

    for finding in scan["findings"]:
        lines.append(
            "- {} x{}: {} - {}".format(
                finding["entity"],
                finding["count"],
                finding["status"],
                finding["note"]
            )
        )

    if scan["unsupported"]:
        lines.extend([
            "",
            "Import warning:",
            "This file contains AP242 PMI entities this add-on does not model. "
            "An AP242 import should preserve the geometry, but unsupported PMI "
            "should be reported to the user rather than silently discarded.",
        ])
    elif scan["partial"]:
        lines.extend([
            "",
            "Import caution:",
            "This file contains AP242 PMI entities that are recognized but only "
            "partially modeled by the add-on. Import should report these limitations "
            "rather than implying full semantic fidelity.",
        ])
    else:
        lines.extend([
            "",
            "All detected PMI entities are in the currently supported set.",
        ])

    return "\n".join(lines)
