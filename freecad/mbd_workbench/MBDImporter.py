# MBDImporter.py

import math
import os
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
    "ANGULARITY_TOLERANCE": (PARTIAL, "Angularity exists; nominal angular dimensions are modeled/exported for face-backed references, with richer edge/axis mapping still future work."),
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
    "DATUM_TARGET": (PARTIAL, "Point, line, circle, and rectangle targets are modeled/exported; arbitrary area targets need a future bounded-sketch workflow."),
    "PLACED_DATUM_TARGET_FEATURE": (PARTIAL, "Point, line, circle, and rectangle placed targets export; arbitrary area export remains deferred."),
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
    "GEOMETRIC_TOLERANCE_WITH_MODIFIERS": (PARTIAL, "Profile all-over, MMC/LMC material modifiers, tangent plane, statistical tolerance, common tolerance, and projected-zone definitions export; broader modifier coverage remains future work."),
    "MODIFIED_GEOMETRIC_TOLERANCE": (PARTIAL, "MMC/LMC are modeled/displayed/validated for conservative position cases and export as material-requirement modifiers."),
    "UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE": (PARTIAL, "Unequally disposed surface-profile, face-backed line-profile, and single edge-backed line-profile zones are modeled/displayed/validated and export; all-over and multiple edge-backed line-profile mapping remain future work."),
    "GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE": (SUPPORTED, "Maximum tolerance value is modeled, displayed, validated, and exported for mapped FCFs."),
    "GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT": (SUPPORTED, "Length unit-basis tolerance is modeled, displayed, validated, and exported for mapped FCFs."),
    "GEOMETRIC_TOLERANCE_WITH_DEFINED_AREA_UNIT": (SUPPORTED, "Circular, square, and rectangular area unit-basis tolerances are modeled, displayed, validated, and exported for mapped FCFs."),
    "TOLERANCE_ZONE": (PARTIAL, "Position diameter zones are supported; broader zone definitions remain future work."),
    "TOLERANCE_ZONE_FORM": (PARTIAL, "Cylindrical/circular position zones are supported; broader forms remain future work."),
    "TOLERANCE_ZONE_DEFINITION": (NOT_IMPLEMENTED, "Richer tolerance zone definitions are not implemented yet."),
    "PROJECTED_ZONE_DEFINITION": (PARTIAL, "Projected tolerance zone height exports for position FCFs; broader projected-zone cases remain future work."),
    "RUNOUT_ZONE_DEFINITION": (PARTIAL, "Runout FCFs are modeled/exported; explicit AP242 runout-zone geometry remains future work."),
    "RUNOUT_ZONE_ORIENTATION": (PARTIAL, "Runout FCFs are modeled/exported; explicit AP242 runout-zone orientation remains future work."),
    "NON_UNIFORM_ZONE_DEFINITION": (SUPPORTED, "Non-uniform profile zones are modeled, displayed, validated, and exported for mapped FCFs."),
    "SHAPE_ASPECT_RELATIONSHIP": (PARTIAL, "Used for affected-plane associations and many generic AP242 relationships; only affected-plane relationships are recognized semantically today."),
    "ANNOTATION_PLACEHOLDER_OCCURRENCE": (PARTIAL, "AP242 presentation PMI placeholders export as first-pass layout hints; native import and exact graphics remain future work."),
    "ANNOTATION_PLACEHOLDER_OCCURRENCE_WITH_LEADER_LINE": (DEFERRED, "AP242 presentation PMI placeholders with explicit leader geometry remain deferred until leader routing is stable."),
    "DIMENSION_CURVE": (DEFERRED, "AP242 presentation PMI is deferred."),
    "DIMENSION_CURVE_TERMINATOR": (DEFERRED, "AP242 presentation PMI is deferred."),
    "PRESENTATION_SIZE": (DEFERRED, "AP242 presentation sizing is deferred."),
}


STEP_ENTITY_PATTERN = re.compile(
    r"#(\d+)\s*=\s*(.*?);",
    re.IGNORECASE | re.DOTALL
)
STEP_TYPE_PATTERN = re.compile(r"\b([A-Z][A-Z0-9_]*)\s*\(", re.IGNORECASE)
STEP_REF_PATTERN = re.compile(r"#(\d+)")
STEP_STRING_PATTERN = re.compile(r"'((?:''|[^'])*)'")
STEP_NUMBER_PATTERN = re.compile(
    r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"
)


FCF_TYPE_BY_STEP_ENTITY = {
    "ANGULARITY_TOLERANCE": "Angularity",
    "CIRCULAR_RUNOUT_TOLERANCE": "CircularRunout",
    "CYLINDRICITY_TOLERANCE": "Cylindricity",
    "FLATNESS_TOLERANCE": "Flatness",
    "LINE_PROFILE_TOLERANCE": "LineProfile",
    "PARALLELISM_TOLERANCE": "Parallelism",
    "PERPENDICULARITY_TOLERANCE": "Perpendicularity",
    "POSITION_TOLERANCE": "Position",
    "ROUNDNESS_TOLERANCE": "Circularity",
    "STRAIGHTNESS_TOLERANCE": "Straightness",
    "SURFACE_PROFILE_TOLERANCE": "Profile",
    "TOTAL_RUNOUT_TOLERANCE": "TotalRunout",
}

DIMENSION_ENTITY_TYPES = {
    "ANGULAR_LOCATION",
    "ANGULAR_SIZE",
    "DIMENSIONAL_LOCATION",
    "DIMENSIONAL_SIZE",
    "DIRECTED_DIMENSIONAL_LOCATION",
    "DIMENSIONAL_LOCATION_WITH_PATH",
    "DIMENSIONAL_SIZE_WITH_PATH",
}

DIMENSION_KIND_BY_DESCRIPTOR = {
    "diameter": "Diameter",
    "radius": "Radius",
    "thickness": "Linear",
    "angle": "Angular",
}

DATUM_TARGET_TYPES = {
    "DATUM_TARGET",
    "PLACED_DATUM_TARGET_FEATURE",
}

NATIVE_FCF_IMPORT_TYPES = {
    "Angularity",
    "Circularity",
    "CircularRunout",
    "Cylindricity",
    "Flatness",
    "LineProfile",
    "Parallelism",
    "Perpendicularity",
    "Position",
    "Profile",
    "Straightness",
    "TotalRunout",
}

MULTI_ATTACHMENT_FCF_IMPORT_TYPES = {
    "Angularity",
    "Flatness",
    "LineProfile",
    "Parallelism",
    "Perpendicularity",
    "Position",
    "Profile",
}


def _known_entities_in_step_body(body):
    body_upper = body.upper()
    entities = []

    for entity in AP242_PMI_ENTITY_SUPPORT:
        if re.search(r"\b{}\s*\(".format(re.escape(entity)), body_upper):
            entities.append(entity)

    return entities


def _step_type_names(body):
    return sorted({
        match.group(1).upper()
        for match in STEP_TYPE_PATTERN.finditer(body)
    })


def _step_refs(body):
    return [
        "#{}".format(match.group(1))
        for match in STEP_REF_PATTERN.finditer(body)
    ]


def _step_strings(body):
    return [
        match.group(1).replace("''", "'")
        for match in STEP_STRING_PATTERN.finditer(body)
    ]


def parse_step_entities(filepath):
    """Parse STEP Part 21 entity records into lightweight dictionaries.

    This text parser deliberately stops short of topology import.  It is a
    semantic PMI discovery layer: it records entity types, references, and
    string descriptors so a later import pass can bind recognized PMI to
    FreeCAD topology without guessing.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    records = {}
    type_index = {}

    for match in STEP_ENTITY_PATTERN.finditer(text):
        entity_id = "#{}".format(match.group(1))
        body = match.group(2).strip()
        types = _step_type_names(body)
        records[entity_id] = {
            "id": entity_id,
            "body": body,
            "body_upper": body.upper(),
            "types": types,
            "refs": _step_refs(body),
            "strings": _step_strings(body),
        }

        for type_name in types:
            type_index.setdefault(type_name, []).append(records[entity_id])

    records["_type_index"] = type_index
    return records


def _records_of_type(records, type_name):
    return records.get("_type_index", {}).get(type_name, [])


def _step_records(records):
    return (
        record
        for ref, record in records.items()
        if str(ref).startswith("#")
    )


def _step_record_items(records):
    return (
        (ref, record)
        for ref, record in records.items()
        if str(ref).startswith("#")
    )


def _record_by_ref(records, ref):
    return records.get(ref)


def _last_nonempty_string(record, fallback=""):
    for value in reversed(record.get("strings", [])):
        if value:
            return value

    return fallback


def _first_nonempty_string(record, fallback=""):
    for value in record.get("strings", []):
        if value:
            return value

    return fallback


def _relationship_description(record):
    strings = record.get("strings", [])

    if len(strings) > 1:
        return strings[1]

    return ""


def _is_shape_aspect_like(record):
    return any(
        type_name == "SHAPE_ASPECT" or type_name.endswith("_SHAPE_ASPECT")
        for type_name in record.get("types", [])
    )


def _is_datum_feature_carrier(record):
    """Return True for AP242 records that can carry datum-feature topology."""
    types = record.get("types", [])

    return (
        "DATUM_FEATURE" in types
        or "DIMENSIONAL_SIZE_WITH_DATUM_FEATURE" in types
    )


def _datum_label_from_record(record):
    return _last_nonempty_string(record, record["id"].lstrip("#"))


def _datum_ref_label(records, ref):
    record = _record_by_ref(records, ref)

    if record is None:
        return ref

    if "DATUM" in record["types"]:
        return _datum_label_from_record(record)

    if "DATUM_REFERENCE_ELEMENT" in record["types"]:
        for child_ref in record.get("refs", []):
            child = _record_by_ref(records, child_ref)

            if child is not None and "DATUM" in child["types"]:
                return _datum_label_from_record(child)

    return ref


def _datum_compartment_members(records, compartment_ref):
    compartment = _record_by_ref(records, compartment_ref)

    if compartment is None:
        return [compartment_ref]

    members = []

    for ref in compartment.get("refs", []):
        referenced = _record_by_ref(records, ref)

        if referenced is None:
            continue

        if "DATUM" in referenced["types"]:
            members.append(_datum_label_from_record(referenced))
            continue

        if "DATUM_REFERENCE_ELEMENT" in referenced["types"]:
            member = _datum_ref_label(records, ref)

            if member and member != ref:
                members.append(member)

            continue

        if "COMMON_DATUM_LIST" in referenced["types"]:
            common_members = [
                _datum_ref_label(records, member_ref)
                for member_ref in referenced.get("refs", [])
            ]
            members.extend(
                member for member in common_members
                if member
            )

    if members:
        return [
            member
            for index, member in enumerate(members)
            if member not in members[:index]
        ]

    return [compartment_ref]


def _dimension_ap242_entity(record):
    for entity_type in sorted(DIMENSION_ENTITY_TYPES):
        if entity_type in record["types"]:
            return entity_type

    return ""


def _dimension_kind(record):
    descriptor = _last_nonempty_string(record, "").lower()

    for token, kind in DIMENSION_KIND_BY_DESCRIPTOR.items():
        if token in descriptor:
            return kind

    if "ANGULAR_SIZE" in record["types"] or "ANGULAR_LOCATION" in record["types"]:
        return "Angular"

    return "Linear"


def _fcf_tolerance_type(record):
    for entity_type, tolerance_type in FCF_TYPE_BY_STEP_ENTITY.items():
        if entity_type in record["types"]:
            return tolerance_type

    return None


def _fcf_modifiers(record):
    return [
        modifier_type
        for modifier_type in (
            "GEOMETRIC_TOLERANCE_WITH_MODIFIERS",
            "GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE",
            "GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT",
            "GEOMETRIC_TOLERANCE_WITH_DEFINED_AREA_UNIT",
            "UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE",
            "PROJECTED_ZONE_DEFINITION",
            "NON_UNIFORM_ZONE_DEFINITION",
        )
        if modifier_type in record["types"]
    ]


def _subtype_refs(record, subtype_name):
    match = re.search(
        r"{}\s*\((.*?)\)".format(re.escape(subtype_name)),
        record.get("body", ""),
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return []

    return [
        "#{}".format(ref)
        for ref in STEP_REF_PATTERN.findall(match.group(1))
    ]


def _defined_area_unit(record):
    match = re.search(
        r"GEOMETRIC_TOLERANCE_WITH_DEFINED_AREA_UNIT\s*\(\s*\.([A-Z_]+)\.\s*,\s*(#\d+)\s*\)",
        record.get("body", ""),
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return None, ""

    area_type = match.group(1).replace("_", " ").title().replace(" ", "")
    return area_type, match.group(2)


def _tolerance_zone_refs_for_tolerance(records, tolerance_ref):
    return [
        record["id"]
        for record in _records_of_type(records, "TOLERANCE_ZONE")
        if tolerance_ref in record.get("refs", [])
    ]


def _projected_zone_for_tolerance(records, tolerance_ref, scale):
    zone_refs = set(_tolerance_zone_refs_for_tolerance(records, tolerance_ref))

    for record in _records_of_type(records, "PROJECTED_ZONE_DEFINITION"):
        refs = record.get("refs", [])

        if not refs or refs[0] not in zone_refs:
            continue

        for ref in reversed(refs):
            measure = _scaled_length_from_record(
                records,
                _record_by_ref(records, ref),
                scale
            )

            if measure is not None:
                return measure

    return None


def _has_non_uniform_zone(records, tolerance_ref):
    zone_refs = set(_tolerance_zone_refs_for_tolerance(records, tolerance_ref))

    for record in _records_of_type(records, "NON_UNIFORM_ZONE_DEFINITION"):
        if any(ref in zone_refs for ref in record.get("refs", [])):
            return True

    return False


def _runout_orientation_angle_for_tolerance(records, tolerance_ref):
    zone_refs = set(_tolerance_zone_refs_for_tolerance(records, tolerance_ref))

    if not zone_refs:
        return None

    for record in _records_of_type(records, "RUNOUT_ZONE_DEFINITION"):
        refs = record.get("refs", [])

        if not refs or refs[0] not in zone_refs:
            continue

        orientation_refs = _subtype_refs(record, "RUNOUT_ZONE_ORIENTATION")

        if not orientation_refs:
            continue

        angle_record = _record_by_ref(records, orientation_refs[0])

        if angle_record is None:
            return None

        angle_value = _measure_value_from_record(angle_record)

        if angle_value is None:
            return None

        # AP242 plane-angle measures are usually represented in radians.  The
        # native FCF property is user-facing degrees, matching the runout
        # orientation dialog.
        return math.degrees(float(angle_value))

    return None


def _fcf_modifier_values(records, record, scale):
    values = {}
    unsupported = []
    body_upper = record.get("body_upper", "")

    if ".MAXIMUM_MATERIAL_REQUIREMENT." in body_upper:
        values["material_condition"] = "MMC"
    elif ".LEAST_MATERIAL_REQUIREMENT." in body_upper:
        values["material_condition"] = "LMC"

    if ".TANGENT_PLANE." in body_upper:
        values["tangent_plane"] = True

    if ".STATISTICAL_TOLERANCE." in body_upper:
        values["statistical_tolerance"] = True

    if ".COMMON_ZONE." in body_upper:
        values["common_zone"] = True

    max_refs = _subtype_refs(
        record,
        "GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE"
    )

    if max_refs:
        maximum_value = _scaled_length_from_record(
            records,
            _record_by_ref(records, max_refs[0]),
            scale
        )

        if maximum_value is None:
            unsupported.append("maximum tolerance value")
        else:
            values["maximum_tolerance"] = maximum_value

    unit_refs = _subtype_refs(
        record,
        "GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT"
    )

    if unit_refs:
        primary = _scaled_length_from_record(
            records,
            _record_by_ref(records, unit_refs[0]),
            scale
        )

        if primary is None:
            unsupported.append("unit-basis primary length")
        else:
            values["unit_basis"] = {
                "type": "Length",
                "primary": primary,
                "secondary": 0.0,
            }

    area_type, area_ref = _defined_area_unit(record)

    if area_ref:
        secondary = _scaled_length_from_record(
            records,
            _record_by_ref(records, area_ref),
            scale
        )

        if secondary is None:
            unsupported.append("unit-basis area length")
        else:
            unit_basis = values.setdefault(
                "unit_basis",
                {"type": "Length", "primary": secondary, "secondary": 0.0}
            )
            unit_basis["type"] = area_type
            unit_basis["secondary"] = secondary

    unequal_refs = _subtype_refs(
        record,
        "UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE"
    )

    if unequal_refs:
        displacement = _scaled_length_from_record(
            records,
            _record_by_ref(records, unequal_refs[0]),
            scale
        )

        if displacement is None:
            unsupported.append("unequally disposed displacement")
        else:
            values["unequally_disposed"] = displacement

    projected_height = _projected_zone_for_tolerance(
        records,
        record["id"],
        scale
    )

    if projected_height is not None:
        values["projected_zone_height"] = projected_height

    if _has_non_uniform_zone(records, record["id"]):
        values["non_uniform_zone"] = True

    runout_angle = _runout_orientation_angle_for_tolerance(records, record["id"])

    if runout_angle is not None:
        values["runout_orientation_angle"] = runout_angle

    values["unsupported"] = unsupported
    return values


def _datum_system_refs_from_fcf(records, record):
    return [
        ref
        for ref in record.get("refs", [])
        if (
            _record_by_ref(records, ref) is not None
            and "DATUM_SYSTEM" in _record_by_ref(records, ref).get("types", [])
        )
    ]


def _datum_target_kind(record):
    strings = [
        value.lower()
        for value in record.get("strings", [])
        if value
    ]

    for target_kind in ("point", "line", "circle", "rectangle", "area"):
        if target_kind in strings:
            return target_kind.title()

    return "Unknown"


def _datum_target_kind_from_parameters(record, parameters):
    target_kind = _datum_target_kind(record)

    if target_kind != "Unknown":
        return target_kind

    if parameters.get("diameter") is not None:
        return "Circle"

    if (
        parameters.get("length") is not None
        and parameters.get("width") is not None
    ):
        return "Rectangle"

    if parameters.get("length") is not None:
        return "Line"

    if parameters.get("placement"):
        return "Point"

    return "Unknown"


def _numbers_from_record(record):
    return [
        float(value)
        for value in STEP_NUMBER_PATTERN.findall(record.get("body", ""))
    ]


def _vector_tuple_from_record(record):
    numbers = _numbers_from_record(record)

    if len(numbers) < 3:
        return None

    return numbers[:3]


def _step_cartesian_point(records, ref, scale):
    record = _record_by_ref(records, ref)

    if record is None or "CARTESIAN_POINT" not in record.get("types", []):
        return None

    coordinates = _vector_tuple_from_record(record)

    if coordinates is None:
        return None

    return [
        float(coordinate) * float(scale)
        for coordinate in coordinates
    ]


def _step_direction_vector(records, ref):
    record = _record_by_ref(records, ref)

    if record is None or "DIRECTION" not in record.get("types", []):
        return None

    coordinates = _vector_tuple_from_record(record)

    if coordinates is None:
        return None

    return [
        float(coordinate)
        for coordinate in coordinates
    ]


def _step_line_segment_endpoints(records, geometry_ref, scale):
    """Return millimeter endpoints for finite AP242 line/trimmed-curve items.

    AP242 import preview can see representation items such as TRIMMED_CURVE
    even when they are not topological EDGE_CURVE records.  Native FreeCAD MBD
    dimensions still need selectable subelements, so later import code uses
    these endpoints only to find a unique matching FreeCAD edge.
    """
    record = _record_by_ref(records, geometry_ref)

    if record is None:
        return None

    line_record = record

    if "TRIMMED_CURVE" in record.get("types", []):
        line_record = None

        for ref in record.get("refs", []):
            candidate = _record_by_ref(records, ref)

            if candidate is not None and "LINE" in candidate.get("types", []):
                line_record = candidate
                break

    if line_record is None or "LINE" not in line_record.get("types", []):
        return None

    refs = line_record.get("refs", [])

    if len(refs) < 2:
        return None

    start = _step_cartesian_point(records, refs[0], scale)
    vector_record = _record_by_ref(records, refs[1])

    if (
        start is None
        or vector_record is None
        or "VECTOR" not in vector_record.get("types", [])
    ):
        return None

    vector_refs = vector_record.get("refs", [])

    if not vector_refs:
        return None

    direction = _step_direction_vector(records, vector_refs[0])
    numbers = _numbers_from_record(vector_record)

    if direction is None or not numbers:
        return None

    magnitude = float(numbers[-1]) * float(scale)
    end = [
        start[index] + direction[index] * magnitude
        for index in range(3)
    ]
    return start, end


def _measure_value_from_record(record):
    numbers = _numbers_from_record(record)

    if not numbers:
        return None

    return numbers[0]


def _length_unit_scale_to_mm(records, unit_ref, fallback_scale, visited=None):
    if visited is None:
        visited = set()

    if not unit_ref or unit_ref in visited:
        return fallback_scale

    visited.add(unit_ref)
    unit_record = _record_by_ref(records, unit_ref)

    if unit_record is None:
        return fallback_scale

    body_upper = unit_record.get("body_upper", "")

    if "SI_UNIT(.MILLI.,.METRE.)" in body_upper:
        return 1.0

    if "SI_UNIT($,.METRE.)" in body_upper:
        return 1000.0

    if "CONVERSION_BASED_UNIT" in unit_record.get("types", []):
        strings = [
            value.lower()
            for value in unit_record.get("strings", [])
            if value
        ]
        default_conversion = 25.4 if "inch" in strings else fallback_scale

        for ref in unit_record.get("refs", []):
            referenced = _record_by_ref(records, ref)

            if referenced is None or "MEASURE_WITH_UNIT" not in referenced["types"]:
                continue

            value = _measure_value_from_record(referenced)
            base_unit_ref = _length_unit_ref_from_record(records, referenced)

            if value is None or not base_unit_ref:
                continue

            base_scale = _length_unit_scale_to_mm(
                records,
                base_unit_ref,
                fallback_scale,
                visited
            )
            return float(value) * float(base_scale)

        return default_conversion

    return fallback_scale


def _length_unit_ref_from_record(records, record):
    for ref in record.get("refs", []):
        referenced = _record_by_ref(records, ref)

        if referenced is None:
            continue

        if (
            "LENGTH_UNIT" in referenced.get("types", [])
            or "CONVERSION_BASED_UNIT" in referenced.get("types", [])
            or "SI_UNIT" in referenced.get("types", [])
        ):
            return ref

    return ""


def _scaled_length_from_record(records, record, fallback_scale):
    if record is None:
        return None

    if "LENGTH_MEASURE_WITH_UNIT" not in record.get("types", []):
        return None

    value = _measure_value_from_record(record)

    if value is None:
        return None

    unit_scale = fallback_scale
    unit_ref = _length_unit_ref_from_record(records, record)

    if unit_ref:
        unit_scale = _length_unit_scale_to_mm(
            records,
            unit_ref,
            fallback_scale
        )

    return float(value) * float(unit_scale)


def dimension_value_map(records, scale):
    """Return nominal/tolerance values keyed by AP242 dimension entity id."""
    values = {}

    for record in _records_of_type(records, "DIMENSIONAL_CHARACTERISTIC_REPRESENTATION"):
        refs = record.get("refs", [])

        if len(refs) < 2:
            continue

        dimension_ref = refs[0]
        representation_ref = refs[1]
        representation = _record_by_ref(records, representation_ref)

        if representation is None:
            continue

        for ref in representation.get("refs", []):
            measure = _scaled_length_from_record(
                records,
                _record_by_ref(records, ref),
                scale
            )

            if measure is None:
                continue

            values.setdefault(dimension_ref, {})["nominal_value"] = measure
            break

    for record in _records_of_type(records, "PLUS_MINUS_TOLERANCE"):
        refs = record.get("refs", [])

        if len(refs) < 2:
            continue

        tolerance = _record_by_ref(records, refs[0])

        if tolerance is None or "TOLERANCE_VALUE" not in tolerance.get("types", []):
            continue

        tolerance_refs = tolerance.get("refs", [])

        if len(tolerance_refs) < 2:
            continue

        lower = _scaled_length_from_record(
            records,
            _record_by_ref(records, tolerance_refs[0]),
            scale
        )
        upper = _scaled_length_from_record(
            records,
            _record_by_ref(records, tolerance_refs[1]),
            scale
        )

        if lower is None or upper is None:
            continue

        values.setdefault(refs[1], {})["lower_tolerance"] = lower
        values.setdefault(refs[1], {})["upper_tolerance"] = upper

    return values


def _axis2_placement_from_ref(records, placement_ref):
    record = _record_by_ref(records, placement_ref)

    if record is None or "AXIS2_PLACEMENT_3D" not in record["types"]:
        return None

    refs = record.get("refs", [])

    if not refs:
        return None

    location = _record_by_ref(records, refs[0])
    axis = _record_by_ref(records, refs[1]) if len(refs) > 1 else None
    ref_direction = _record_by_ref(records, refs[2]) if len(refs) > 2 else None

    return {
        "location": _vector_tuple_from_record(location) if location else None,
        "axis": _vector_tuple_from_record(axis) if axis else None,
        "ref_direction": (
            _vector_tuple_from_record(ref_direction)
            if ref_direction else None
        ),
    }


def datum_target_relationship_map(records):
    target_to_datum = {}
    datum_to_targets = {}

    for relationship in _records_of_type(records, "SHAPE_ASPECT_RELATIONSHIP"):
        description = _first_nonempty_string(relationship, "").lower()

        if description != "datum target":
            continue

        refs = relationship.get("refs", [])

        if len(refs) < 2:
            continue

        target_ref, datum_ref = refs[0], refs[1]
        target_to_datum[target_ref] = datum_ref
        datum_to_targets.setdefault(datum_ref, []).append(target_ref)

    return target_to_datum, datum_to_targets


def datum_target_parameter_map(records):
    """Return AP242 placed-target size and placement data by target id.

    AP242 datum targets often carry their selectable geometry through
    `SHAPE_DEFINITION_REPRESENTATION`: the property definition points at the
    target feature, while the parameter representation contains width/length
    measures and an `AXIS2_PLACEMENT_3D`.
    """
    property_to_target = {}

    for record in _records_of_type(records, "PROPERTY_DEFINITION"):
        target_ref = None

        for ref in record.get("refs", []):
            referenced = _record_by_ref(records, ref)

            if (
                referenced is not None
                and any(
                    type_name in referenced["types"]
                    for type_name in DATUM_TARGET_TYPES
                )
            ):
                target_ref = ref
                break

        if target_ref:
            property_to_target[record["id"]] = target_ref

    target_parameters = {}

    for record in _records_of_type(records, "SHAPE_DEFINITION_REPRESENTATION"):
        refs = record.get("refs", [])

        if len(refs) < 2:
            continue

        target_ref = property_to_target.get(refs[0])

        if not target_ref:
            continue

        representation = _record_by_ref(records, refs[1])

        if representation is None:
            continue

        parameters = target_parameters.setdefault(target_ref, {})

        for parameter_ref in representation.get("refs", []):
            parameter = _record_by_ref(records, parameter_ref)

            if parameter is None:
                continue

            if "AXIS2_PLACEMENT_3D" in parameter["types"]:
                parameters["placement"] = _axis2_placement_from_ref(
                    records,
                    parameter_ref
                )
                continue

            value = _measure_value_from_record(parameter)

            if value is None:
                continue

            name = _first_nonempty_string(parameter, "").lower()

            if "width" in name:
                parameters["width"] = value
            elif "length" in name:
                parameters["length"] = value
            elif "diameter" in name:
                parameters["diameter"] = value

    return target_parameters


def step_length_scale_to_mm(records):
    """Return the scale from STEP length coordinates to FreeCAD millimeters."""
    for record in _records_of_type(records, "LENGTH_UNIT"):
        body_upper = record.get("body_upper", "")

        if "CONVERSION_BASED_UNIT" in record["types"]:
            strings = [
                value.lower()
                for value in record.get("strings", [])
                if value
            ]

            if "inch" in strings:
                for ref in record.get("refs", []):
                    referenced = _record_by_ref(records, ref)

                    if (
                        referenced is not None
                        and "MEASURE_WITH_UNIT" in referenced["types"]
                    ):
                        value = _measure_value_from_record(referenced)

                        if value is not None:
                            return value

                return 25.4

        if "SI_UNIT(.MILLI.,.METRE.)" in body_upper:
            return 1.0

        if "SI_UNIT($,.METRE.)" in body_upper:
            return 1000.0

    return 1.0


def _scaled_target_parameters(parameters, scale):
    if scale == 1.0:
        return parameters

    scaled = dict(parameters)

    for key in ("width", "length", "diameter"):
        if key in scaled and scaled[key] is not None:
            scaled[key] = scaled[key] * scale

    placement = dict(scaled.get("placement", {}) or {})

    if placement.get("location"):
        placement["location"] = [
            coordinate * scale
            for coordinate in placement["location"]
        ]

    scaled["placement"] = placement
    return scaled


def shape_aspect_geometry_usage_map(records):
    """Map AP242 shape-aspect ids to geometric item usage records.

    `GEOMETRIC_ITEM_SPECIFIC_USAGE` is the practical bridge from PMI shape
    aspects to representation items such as advanced faces and edges.  Native
    import later uses this map to bind semantic PMI to imported FreeCAD
    topology.
    """
    usage_map = {}

    for record in _records_of_type(records, "GEOMETRIC_ITEM_SPECIFIC_USAGE"):
        refs = record.get("refs", [])

        if len(refs) < 3:
            continue

        aspect_ref = refs[0]
        usage_map.setdefault(aspect_ref, []).append({
            "step_id": record["id"],
            "name": _first_nonempty_string(record, ""),
            "representation_ref": refs[1],
            "geometry_ref": refs[2],
        })

    return usage_map


def topology_order_map(records):
    """Return a tentative STEP geometry-id to FreeCAD subelement-name map."""
    mapping = {}
    face_index = 1
    edge_index = 1

    for entity_id, record in _step_record_items(records):
        if "ADVANCED_FACE" in record["types"]:
            mapping[entity_id] = "Face{}".format(face_index)
            face_index += 1
        elif "EDGE_CURVE" in record["types"]:
            mapping[entity_id] = "Edge{}".format(edge_index)
            edge_index += 1

    return mapping


def shape_aspect_relationship_map(records):
    relationship_map = {}

    for relationship in _records_of_type(records, "SHAPE_ASPECT_RELATIONSHIP"):
        refs = [
            ref for ref in relationship.get("refs", [])
            if _record_by_ref(records, ref) is not None
        ]

        if len(refs) < 2:
            continue

        description = _relationship_description(relationship)

        if description:
            continue

        first, second = refs[0], refs[1]
        relationship_map.setdefault(first, []).append(second)

    return relationship_map


def affected_plane_usage_map(records, usage_map):
    """Map tolerance shape-aspect ids to their AP242 affected-plane line usage.

    The exporter writes this as a named `SHAPE_ASPECT_RELATIONSHIP` from the
    tolerance's shape aspect to a separate line shape aspect.  Import keeps that
    narrow convention explicit so generic shape-aspect relationships do not get
    mistaken for affected-plane semantics.
    """
    affected_map = {}

    for relationship in _records_of_type(records, "SHAPE_ASPECT_RELATIONSHIP"):
        description = _first_nonempty_string(relationship, "").lower()

        if description != "affected plane association":
            continue

        refs = relationship.get("refs", [])

        if len(refs) < 2:
            continue

        tolerance_aspect_ref, plane_line_ref = refs[0], refs[1]
        affected_map.setdefault(tolerance_aspect_ref, []).extend(
            usage_map.get(plane_line_ref, [])
        )

    return affected_map


def _geometry_usage_refs_for_records(
    records,
    usage_map,
    refs,
    relationship_map=None
):
    if relationship_map is None:
        relationship_map = shape_aspect_relationship_map(records)

    usages = []
    visited = set()

    def add_ref(ref):
        if ref in visited:
            return

        visited.add(ref)
        usages.extend(usage_map.get(ref, []))

        for child_ref in relationship_map.get(ref, []):
            add_ref(child_ref)

    for ref in refs:
        add_ref(ref)

    return usages


def _datum_feature_refs_for_datum(records, datum_ref):
    feature_refs = []
    related_shape_aspect_refs = []

    for relationship in _records_of_type(records, "SHAPE_ASPECT_RELATIONSHIP"):
        refs = relationship.get("refs", [])
        description = _first_nonempty_string(relationship, "").lower()

        if datum_ref not in refs:
            continue

        for ref in refs:
            referenced = _record_by_ref(records, ref)

            if referenced is not None and _is_datum_feature_carrier(referenced):
                feature_refs.append(ref)

    for feature_ref in feature_refs:
        feature_record = _record_by_ref(records, feature_ref)
        feature_types = feature_record.get("types", []) if feature_record else []

        for relationship in _records_of_type(records, "SHAPE_ASPECT_RELATIONSHIP"):
            refs = relationship.get("refs", [])
            description = _first_nonempty_string(relationship, "").lower()

            if feature_ref not in refs:
                continue

            if description == "datum feature":
                for ref in refs:
                    if ref == feature_ref:
                        continue

                    referenced = _record_by_ref(records, ref)

                    if referenced is None:
                        continue

                    if _is_shape_aspect_like(referenced):
                        related_shape_aspect_refs.append(ref)

            if "DIMENSIONAL_SIZE_WITH_DATUM_FEATURE" not in feature_types:
                continue

            if _relationship_description(relationship):
                continue

            # Some STEP files define a datum through a dimensional size aspect.
            # The size aspect is topology-free, while the composite groups that
            # point back to it contain the surface aspects with topology usages.
            for ref in refs:
                if ref == feature_ref:
                    continue

                referenced = _record_by_ref(records, ref)

                if referenced is not None and _is_shape_aspect_like(referenced):
                    related_shape_aspect_refs.append(ref)

    refs = feature_refs + related_shape_aspect_refs

    return [
        ref for index, ref in enumerate(refs)
        if ref not in refs[:index]
    ]


def _fallback_datum_geometry_usages(records, usage_map, datum_records, used_geometry_refs):
    """Resolve AP242 datum geometry from related composite datum aspects.

    Some AP242 files, including NIST CTC examples, attach simple datums to
    `DATUM_FEATURE` records that have no direct `GEOMETRIC_ITEM_SPECIFIC_USAGE`.
    The actual topology binding is carried by nearby composite shape aspects
    marked with the string `DATUM`.  This fallback pairs unresolved DATUM
    records with those still-unused composite datum usage sets in STEP order.
    It deliberately excludes geometry already used by explicitly-bound datums
    so duplicate helper aspects do not steal the topology for later datums.
    """
    relationship_map = shape_aspect_relationship_map(records)
    datum_usage_sets = []

    for aspect_ref, record in _step_record_items(records):
        if "COMPOSITE_SHAPE_ASPECT" not in record["types"]:
            continue

        strings = [
            value.upper()
            for value in record.get("strings", [])
            if value
        ]

        if "DATUM" not in strings:
            continue

        usages = _geometry_usage_refs_for_records(
            records,
            usage_map,
            relationship_map.get(aspect_ref, []),
            relationship_map
        )

        if not usages:
            continue

        usage_geometry_refs = {
            usage.get("geometry_ref", "")
            for usage in usages
        }

        if usage_geometry_refs and usage_geometry_refs <= used_geometry_refs:
            continue

        datum_usage_sets.append((aspect_ref, usages))

    if not datum_usage_sets:
        for aspect_ref, usages in usage_map.items():
            usage_geometry_refs = {
                usage.get("geometry_ref", "")
                for usage in usages
            }

            if usage_geometry_refs and usage_geometry_refs <= used_geometry_refs:
                continue

            aspect = _record_by_ref(records, aspect_ref)

            if aspect is None:
                continue

            strings = [
                value.upper()
                for value in aspect.get("strings", [])
                if value
            ]

            if "DATUM" not in strings:
                continue

            datum_usage_sets.append((aspect_ref, usages))

    datum_usage_sets.sort(
        key=lambda item: int(item[0].lstrip("#"))
    )
    unresolved_datums = []

    for record in datum_records:
        feature_refs = _datum_feature_refs_for_datum(records, record["id"])
        explicit_usages = _geometry_usage_refs_for_records(
            records,
            usage_map,
            feature_refs,
            relationship_map
        )

        if not explicit_usages:
            unresolved_datums.append(record)

    fallback = {}
    index = 0
    assigned_geometry_refs = set(used_geometry_refs)

    for record in unresolved_datums:
        while index < len(datum_usage_sets):
            _aspect_ref, usages = datum_usage_sets[index]
            index += 1

            usage_geometry_refs = {
                usage.get("geometry_ref", "")
                for usage in usages
                if usage.get("geometry_ref", "")
            }

            if not usages or usage_geometry_refs <= assigned_geometry_refs:
                continue

            fallback[record["id"]] = usages
            assigned_geometry_refs.update(usage_geometry_refs)
            break

    return fallback


def semantic_import_preview(filepath):
    """Return native-MBD import candidates from an AP242 STEP file.

    The preview is intentionally non-destructive.  It does not create FreeCAD
    objects, but it separates records we can later map into native MBD objects
    from records that should remain warnings or deferred work.
    """
    records = parse_step_entities(filepath)
    scan = scan_step_pmi_entities(filepath, records)
    usage_map = shape_aspect_geometry_usage_map(records)
    topology_map = topology_order_map(records)
    relationship_map = shape_aspect_relationship_map(records)
    affected_plane_map = affected_plane_usage_map(records, usage_map)
    target_to_datum, datum_to_targets = datum_target_relationship_map(records)
    target_parameters = datum_target_parameter_map(records)
    length_scale_to_mm = step_length_scale_to_mm(records)
    dimension_values = dimension_value_map(records, length_scale_to_mm)

    for usages in usage_map.values():
        for usage in usages:
            usage["subelement"] = topology_map.get(usage["geometry_ref"], "")

    candidates = {
        "datums": [],
        "datum_systems": [],
        "datum_targets": [],
        "dimensions": [],
        "fcfs": [],
        "relationships": [],
    }
    limitations = []

    datum_records = _records_of_type(records, "DATUM")
    datum_geometry = {}
    used_datum_geometry_refs = set()

    for record in datum_records:
        datum_feature_refs = _datum_feature_refs_for_datum(records, record["id"])
        geometry_usages = _geometry_usage_refs_for_records(
            records,
            usage_map,
            datum_feature_refs,
            relationship_map
        )
        datum_geometry[record["id"]] = {
            "datum_feature_refs": datum_feature_refs,
            "geometry_usages": geometry_usages,
        }

        if geometry_usages:
            used_datum_geometry_refs.update(
                usage.get("geometry_ref", "")
                for usage in geometry_usages
                if usage.get("geometry_ref", "")
            )

    fallback_datum_usages = _fallback_datum_geometry_usages(
        records,
        usage_map,
        datum_records,
        used_datum_geometry_refs
    )

    for record in datum_records:
        datum_feature_refs = datum_geometry[record["id"]]["datum_feature_refs"]
        geometry_usages = datum_geometry[record["id"]]["geometry_usages"]

        if not geometry_usages:
            geometry_usages = fallback_datum_usages.get(record["id"], [])

        target_refs = datum_to_targets.get(record["id"], [])
        target_backed = any(
            target_parameters.get(target_ref, {}).get("placement")
            for target_ref in target_refs
        )
        candidates["datums"].append({
            "step_id": record["id"],
            "label": _datum_label_from_record(record),
            "source_refs": record["refs"],
            "datum_feature_refs": datum_feature_refs,
            "geometry_usages": geometry_usages,
            "target_refs": target_refs,
            "can_create_native": bool(geometry_usages) or target_backed,
        })

    for record in _records_of_type(records, "DATUM_SYSTEM"):
        compartments = []

        for ref in record.get("refs", []):
            referenced = _record_by_ref(records, ref)

            if (
                referenced is not None
                and "DATUM_REFERENCE_COMPARTMENT" in referenced["types"]
            ):
                compartments.append(_datum_compartment_members(records, ref))

        candidates["datum_systems"].append({
            "step_id": record["id"],
            "compartments": compartments,
            "label": " | ".join("-".join(item) for item in compartments),
            "can_create_native": bool(compartments),
        })

    for record in _step_records(records):
        if not any(
            type_name in record["types"]
            for type_name in DATUM_TARGET_TYPES
        ):
            continue

        parameters = _scaled_target_parameters(
            target_parameters.get(record["id"], {}),
            length_scale_to_mm
        )
        target_kind = _datum_target_kind_from_parameters(record, parameters)
        can_create = target_kind in {"Point", "Line", "Circle", "Rectangle"}
        parent_datum_ref = target_to_datum.get(record["id"], "")
        candidates["datum_targets"].append({
            "step_id": record["id"],
            "target_kind": target_kind,
            "target_number": _last_nonempty_string(record, "1"),
            "source_refs": record["refs"],
            "parent_datum_ref": parent_datum_ref,
            "parent_datum_label": (
                _datum_ref_label(records, parent_datum_ref)
                if parent_datum_ref else ""
            ),
            "parameters": parameters,
            "geometry_usages": _geometry_usage_refs_for_records(
                records,
                usage_map,
                record["refs"],
                relationship_map
            ),
            "can_create_native": (
                can_create
                and (
                    bool(parameters.get("placement"))
                    or bool(
                        _geometry_usage_refs_for_records(
                            records,
                            usage_map,
                            record["refs"],
                            relationship_map
                        )
                    )
                )
            ),
        })

        if not can_create:
            limitations.append(
                "{} datum target {} needs a bounded-area workflow before native import.".format(
                    target_kind,
                    record["id"]
                )
            )

    for record in _step_records(records):
        if not any(
            entity_type in record["types"]
            for entity_type in DIMENSION_ENTITY_TYPES
        ):
            continue

        entity_type = _dimension_ap242_entity(record)
        path_variant = entity_type.endswith("_WITH_PATH")
        dimension_kind = _dimension_kind(record)
        geometry_usages = _geometry_usage_refs_for_records(
            records,
            usage_map,
            record["refs"],
            relationship_map
        )
        grouped_linear_dimension = (
            dimension_kind in ("Linear", "Angular")
            and len([
                usage
                for usage in geometry_usages
                if usage.get("subelement", "")
            ]) > 2
        )
        candidates["dimensions"].append({
            "step_id": record["id"],
            "ap242_entity": entity_type,
            "dimension_kind": dimension_kind,
            "descriptor": _last_nonempty_string(record, ""),
            "values": dimension_values.get(record["id"], {}),
            "source_refs": record["refs"],
            "geometry_usages": geometry_usages,
            "can_create_native": (
                not path_variant
                and not grouped_linear_dimension
            ),
        })

        if path_variant:
            limitations.append(
                "{} {} needs a path-selection workflow before native import.".format(
                    entity_type,
                    record["id"]
                )
            )
        elif grouped_linear_dimension:
            limitations.append(
                "{} {} has grouped {} geometry; native import is deferred until grouped linear/angular dimensions have an explicit semantic grouping model.".format(
                    entity_type,
                    record["id"],
                    dimension_kind.lower()
                )
            )

    for record in _step_records(records):
        tolerance_type = _fcf_tolerance_type(record)

        if tolerance_type is None:
            continue

        affected_plane_usages = []

        for ref in [record["id"]] + record.get("refs", []):
            affected_plane_usages.extend(affected_plane_map.get(ref, []))

        candidates["fcfs"].append({
            "step_id": record["id"],
            "tolerance_type": tolerance_type,
            "modifiers": _fcf_modifiers(record),
            "modifier_values": _fcf_modifier_values(
                records,
                record,
                length_scale_to_mm
            ),
            "datum_system_refs": _datum_system_refs_from_fcf(records, record),
            "source_refs": record["refs"],
            "geometry_usages": _geometry_usage_refs_for_records(
                records,
                usage_map,
                record["refs"],
                relationship_map
            ),
            "affected_plane_usages": affected_plane_usages,
            "can_create_native": True,
        })

    for record in _records_of_type(records, "SHAPE_ASPECT_RELATIONSHIP"):
        description = _relationship_description(record)
        can_create = description.lower() in (
            "affected plane association",
            "datum feature",
            "datum target",
        )

        if not description and not can_create:
            continue

        candidates["relationships"].append({
            "step_id": record["id"],
            "description": description,
            "source_refs": record["refs"],
            "can_create_native": can_create,
        })

        if not can_create:
            limitations.append(
                "Shape-aspect relationship {} is not a recognized native MBD relationship.".format(
                    record["id"]
                )
            )

    for finding in scan["unsupported"]:
        limitations.append(
            "{} x{} is {}: {}".format(
                finding["entity"],
                finding["count"],
                finding["status"],
                finding["note"]
            )
        )

    for finding in scan["partial"]:
        if finding["entity"] == "SHAPE_ASPECT_RELATIONSHIP":
            continue

        limitations.append(
            "{} x{} is partial: {}".format(
                finding["entity"],
                finding["count"],
                finding["note"]
            )
        )

    return {
        "filepath": filepath,
        "length_scale_to_mm": length_scale_to_mm,
        "records": records,
        "scan": scan,
        "candidates": candidates,
        "geometry_usage_map": usage_map,
        "topology_map": topology_map,
        "limitations": limitations,
    }


def format_semantic_import_preview(preview):
    lines = [
        "AP242 Semantic PMI Import Preview",
        "",
        "File: {}".format(preview["filepath"]),
        "",
        "Native import candidates:",
    ]
    candidate_specs = [
        ("Datums", "datums"),
        ("Datum systems", "datum_systems"),
        ("Datum targets", "datum_targets"),
        ("Dimensions", "dimensions"),
        ("FCFs", "fcfs"),
        ("Relationships", "relationships"),
    ]

    for label, key in candidate_specs:
        records = preview["candidates"][key]
        native_ready = [
            record for record in records
            if record.get("can_create_native", False)
        ]
        lines.append(
            "- {}: {} recognized, {} native-ready".format(
                label,
                len(records),
                len(native_ready)
            )
        )

    geometry_usage_count = sum(
        len(usages)
        for usages in preview.get("geometry_usage_map", {}).values()
    )
    lines.append(
        "- Topology usage links: {} shape aspects, {} geometric item usages".format(
            len(preview.get("geometry_usage_map", {})),
            geometry_usage_count
        )
    )

    def usage_label(usage):
        subelement = usage.get("subelement", "")

        if subelement:
            return "{}->{}".format(usage["geometry_ref"], subelement)

        return usage["geometry_ref"]

    if preview["candidates"]["datums"]:
        lines.extend(["", "Datums:"])

        for datum in preview["candidates"]["datums"]:
            usage_text = (
                " geometry={}".format(
                    ",".join(
                        usage_label(usage)
                        for usage in datum.get("geometry_usages", [])
                    )
                )
                if datum.get("geometry_usages") else ""
            )
            lines.append(
                "- {}: {}{}".format(
                    datum["step_id"],
                    datum["label"],
                    usage_text
                )
            )

    if preview["candidates"]["datum_systems"]:
        lines.extend(["", "Datum systems:"])

        for datum_system in preview["candidates"]["datum_systems"]:
            lines.append(
                "- {}: {}".format(
                    datum_system["step_id"],
                    datum_system["label"] or "<unresolved>"
                )
            )

    if preview["candidates"]["fcfs"]:
        lines.extend(["", "Feature control frames:"])

        for fcf in preview["candidates"]["fcfs"]:
            modifier_text = (
                " modifiers={}".format(",".join(fcf["modifiers"]))
                if fcf["modifiers"] else ""
            )
            structured_notes = []
            modifier_values = fcf.get("modifier_values", {})

            if "runout_orientation_angle" in modifier_values:
                structured_notes.append(
                    "runout angle={:.6g} deg".format(
                        modifier_values["runout_orientation_angle"]
                    )
                )

            if fcf.get("affected_plane_usages"):
                structured_notes.append(
                    "affected plane={}".format(
                        ",".join(
                            usage_label(usage)
                            for usage in fcf.get("affected_plane_usages", [])
                        )
                    )
                )

            structured_text = (
                " {}".format("; ".join(structured_notes))
                if structured_notes else ""
            )
            usage_text = (
                " geometry={}".format(
                    ",".join(
                        usage_label(usage)
                        for usage in fcf.get("geometry_usages", [])
                    )
                )
                if fcf.get("geometry_usages") else ""
            )
            lines.append(
                "- {}: {}{}{}{}".format(
                    fcf["step_id"],
                    fcf["tolerance_type"],
                    modifier_text,
                    structured_text,
                    usage_text
                )
            )

    if preview["candidates"]["dimensions"]:
        lines.extend(["", "Dimensions:"])

        for dimension in preview["candidates"]["dimensions"]:
            usage_text = (
                " geometry={}".format(
                    ",".join(
                        usage_label(usage)
                        for usage in dimension.get("geometry_usages", [])
                    )
                )
                if dimension.get("geometry_usages") else ""
            )
            value_text = ""
            values = dimension.get("values", {})

            if "nominal_value" in values:
                value_text = " value={:.6g}".format(values["nominal_value"])

            if (
                "lower_tolerance" in values
                and "upper_tolerance" in values
            ):
                value_text += " tol={:+.6g}/{:+.6g}".format(
                    values["lower_tolerance"],
                    values["upper_tolerance"]
                )

            lines.append(
                "- {}: {} {}{}{}".format(
                    dimension["step_id"],
                    dimension["ap242_entity"],
                    dimension["dimension_kind"],
                    value_text,
                    usage_text
                )
            )

    if preview["limitations"]:
        lines.extend(["", "Import limitations:"])

        for limitation in preview["limitations"]:
            lines.append("- " + limitation)
    else:
        lines.extend(["", "No import limitations were detected in recognized PMI."])

    return "\n".join(lines)


def _first_subelement_from_candidate(candidate):
    for usage in candidate.get("geometry_usages", []):
        subelement = usage.get("subelement", "")

        if subelement:
            return subelement

    return ""


def _datum_type_from_subelement(subelement):
    if subelement.startswith("Face"):
        return "Plane"

    if subelement.startswith("Edge"):
        return "Axis"

    if subelement.startswith("Vertex"):
        return "Point"

    return "Feature"


def _vector_from_coordinates(coordinates):
    if not coordinates:
        return None

    import FreeCAD

    if len(coordinates) < 3:
        return None

    return FreeCAD.Vector(
        float(coordinates[0]),
        float(coordinates[1]),
        float(coordinates[2])
    )


def _nearest_face_subelement(shape_obj, point):
    if shape_obj is None or point is None:
        return ""

    try:
        import Part

        vertex = Part.Vertex(point)
    except Exception:
        return ""

    nearest_name = ""
    nearest_distance = None

    try:
        faces = shape_obj.Shape.Faces
    except Exception:
        return ""

    for index, face in enumerate(faces, 1):
        try:
            distance = vertex.distToShape(face)[0]
        except Exception:
            continue

        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_name = "Face{}".format(index)

    return nearest_name


def _distance_between_vectors(first, second):
    return (first - second).Length


def _edge_endpoint_error(edge, start_point, end_point):
    try:
        vertices = edge.Vertexes

        if len(vertices) < 2:
            return None

        edge_start = vertices[0].Point
        edge_end = vertices[-1].Point
    except Exception:
        return None

    forward_error = max(
        _distance_between_vectors(edge_start, start_point),
        _distance_between_vectors(edge_end, end_point)
    )
    reverse_error = max(
        _distance_between_vectors(edge_start, end_point),
        _distance_between_vectors(edge_end, start_point)
    )
    return min(forward_error, reverse_error)


def _matching_edge_subelement(shape_obj, start_coordinates, end_coordinates):
    if shape_obj is None or start_coordinates is None or end_coordinates is None:
        return ""

    import FreeCAD

    start_point = FreeCAD.Vector(*start_coordinates)
    end_point = FreeCAD.Vector(*end_coordinates)

    try:
        edges = list(shape_obj.Shape.Edges)
        bbox = shape_obj.Shape.BoundBox
    except Exception:
        return ""

    if not edges:
        return ""

    tolerance = max(
        0.01,
        max(bbox.XLength, bbox.YLength, bbox.ZLength) * 1e-5
    )
    matches = []

    for index, edge in enumerate(edges, 1):
        error = _edge_endpoint_error(edge, start_point, end_point)

        if error is None or error > tolerance:
            continue

        matches.append((error, "Edge{}".format(index)))

    if len(matches) != 1:
        return ""

    return matches[0][1]


def _resolve_curve_usages_to_edges(shape_obj, dimension, records, scale):
    resolved = 0

    for usage in dimension.get("geometry_usages", []):
        if usage.get("subelement", ""):
            continue

        endpoints = _step_line_segment_endpoints(
            records,
            usage.get("geometry_ref", ""),
            scale
        )

        if endpoints is None:
            continue

        subelement = _matching_edge_subelement(
            shape_obj,
            endpoints[0],
            endpoints[1]
        )

        if not subelement:
            continue

        usage["subelement"] = subelement
        resolved += 1

    return resolved


def _datum_target_candidates_by_parent(preview):
    by_label = {}

    for target in preview["candidates"].get("datum_targets", []):
        label = target.get("parent_datum_label", "")

        if not label:
            continue

        by_label.setdefault(label, []).append(target)

    return by_label


def _next_unique_object_name(doc, base_name):
    if doc.getObject(base_name) is None:
        return base_name

    for index in range(1, 10000):
        candidate = "{}{:03d}".format(base_name, index)

        if doc.getObject(candidate) is None:
            return candidate

    return base_name


def _dimension_measurement_candidate(shape_obj, dimension):
    """Return a measured native dimension binding for an AP242 preview record.

    AP242 dimensions can bind to one feature, two features, or a composite
    group of faces.  The native workbench dimension object still represents a
    single resolved measurement, so this importer tries only geometry pairings
    the existing measurement engine can prove.  Anything more ambiguous is
    skipped with an explicit message instead of creating a misleading PMI item.
    """
    from .MBDDimension import measurement_from_references

    kind = dimension.get("dimension_kind", "Linear")
    usages = [
        usage
        for usage in dimension.get("geometry_usages", [])
        if usage.get("subelement", "")
    ]

    if not usages:
        return None, "{} has no resolved geometry binding.".format(
            dimension["step_id"]
        )

    if kind in ("Diameter", "Radius"):
        for usage in usages:
            subelement = usage.get("subelement", "")
            measurement = _simple_cylindrical_size_measurement(
                kind,
                shape_obj,
                subelement,
                ""
            )

            if measurement.get("value") is None:
                measurement = measurement_from_references(
                    kind,
                    "Distance",
                    shape_obj,
                    subelement,
                    None,
                    ""
                )

            if measurement.get("value") is not None:
                return {
                    "measurement": measurement,
                    "ref_sub_1": subelement,
                    "ref_sub_2": "",
                }, ""

        return None, "{} {} did not resolve to a cylindrical face.".format(
            dimension["step_id"],
            kind.lower()
        )

    if len(usages) < 2:
        return None, "{} {} needs at least two resolved geometry bindings.".format(
            dimension["step_id"],
            kind.lower()
        )

    if kind in ("Linear", "Angular") and len(usages) > 2:
        return None, "{} {} has {} resolved geometry bindings; grouped linear/angular dimensions are preview-only until the native model can preserve the whole controlled set.".format(
            dimension["step_id"],
            kind.lower(),
            len(usages)
        )

    if kind == "Linear" and len(usages) == 2:
        ref_sub_1 = usages[0].get("subelement", "")
        ref_sub_2 = usages[1].get("subelement", "")
        measurement = _simple_plane_to_plane_measurement(
            shape_obj,
            ref_sub_1,
            ref_sub_2
        )

        if measurement.get("value") is not None:
            return {
                "measurement": measurement,
                "ref_sub_1": ref_sub_1,
                "ref_sub_2": ref_sub_2,
            }, ""

        if ref_sub_1.startswith("Face") and ref_sub_2.startswith("Face"):
            return None, "{} linear face-backed import requires two planar faces; non-planar face pairs stay preview-only.".format(
                dimension["step_id"]
            )

    for first_index, first_usage in enumerate(usages):
        for second_usage in usages[first_index + 1:]:
            ref_sub_1 = first_usage.get("subelement", "")
            ref_sub_2 = second_usage.get("subelement", "")
            measurement = measurement_from_references(
                kind,
                "Distance",
                shape_obj,
                ref_sub_1,
                shape_obj,
                ref_sub_2
            )

            if measurement.get("value") is not None:
                return {
                    "measurement": measurement,
                    "ref_sub_1": ref_sub_1,
                    "ref_sub_2": ref_sub_2,
                }, ""

    return None, "{} {} geometry did not resolve to a supported native dimension.".format(
        dimension["step_id"],
        kind.lower()
    )


def _simple_plane_to_plane_measurement(shape_obj, subelement_1, subelement_2):
    """Fast semantic plane-to-plane measurement for AP242 import.

    The normal interactive dimension path uses richer face helpers so it can
    find display points on arbitrary selections. Imported AP242 thickness and
    location dimensions already identify their topology, so we can use the
    underlying plane definitions directly and avoid costly face mass/normal
    calculations on large STEP faces.
    """
    try:
        import FreeCAD
    except Exception:
        return {"value": None, "message": ""}

    try:
        face_1 = shape_obj.Shape.getElement(subelement_1)
        face_2 = shape_obj.Shape.getElement(subelement_2)
    except Exception:
        return {"value": None, "message": ""}

    try:
        surface_1 = face_1.Surface
        surface_2 = face_2.Surface
        name_1 = surface_1.__class__.__name__.lower()
        name_2 = surface_2.__class__.__name__.lower()
    except Exception:
        return {"value": None, "message": ""}

    if "plane" not in name_1 or "plane" not in name_2:
        return {"value": None, "message": ""}

    try:
        point_1 = FreeCAD.Vector(surface_1.Position)
        point_2 = FreeCAD.Vector(surface_2.Position)
        normal_1 = FreeCAD.Vector(surface_1.Axis)
        normal_2 = FreeCAD.Vector(surface_2.Axis)
    except Exception:
        return {"value": None, "message": ""}

    if normal_1.Length == 0 or normal_2.Length == 0:
        return {"value": None, "message": ""}

    normal_1.normalize()
    normal_2.normalize()

    if abs(normal_1.dot(normal_2)) < 0.999:
        return {"value": None, "message": ""}

    signed = (point_2 - point_1).dot(normal_1)
    direction = FreeCAD.Vector(normal_1)

    if signed < 0:
        direction = direction.negative()

    distance = abs(float(signed))
    return {
        "value": distance,
        "point1": point_1,
        "point2": point_1 + direction * distance,
        "pattern": "PlaneToPlane",
        "message": "",
    }


def _simple_cylindrical_size_measurement(kind, shape_obj, subelement, message):
    """Fast semantic diameter/radius measurement for AP242 import.

    The interactive dimension path intentionally finds a nice display point and
    open-end direction for leaders, including solid probes.  Import only needs
    a stable semantic size and signature points, so it can avoid that expensive
    display-oriented analysis.
    """
    import FreeCAD

    try:
        face = shape_obj.Shape.getElement(subelement)
    except Exception:
        return {"value": None, "message": message}

    if face is None or not hasattr(face, "Surface"):
        return {"value": None, "message": message}

    try:
        surface_name = face.Surface.__class__.__name__.lower()
    except Exception:
        surface_name = ""

    if "cylinder" not in surface_name:
        return {"value": None, "message": message}

    try:
        axis = FreeCAD.Vector(face.Surface.Axis)
        center = FreeCAD.Vector(face.Surface.Center)
        radius = float(face.Surface.Radius)
    except Exception:
        try:
            axis = FreeCAD.Vector(face.Surface.Axis)
            center = FreeCAD.Vector(face.Surface.Position)
            radius = float(face.Surface.Radius)
        except Exception:
            return {"value": None, "message": message}

    if axis.Length == 0 or radius <= 0:
        return {"value": None, "message": message}

    axis.normalize()

    try:
        face_center = face.CenterOfMass
        axis_point = center + axis * ((face_center - center).dot(axis))
    except Exception:
        axis_point = center

    helper = axis.cross(FreeCAD.Vector(0, 0, 1))

    if helper.Length == 0:
        helper = axis.cross(FreeCAD.Vector(0, 1, 0))

    if helper.Length == 0:
        return {"value": None, "message": message}

    helper.normalize()

    if kind == "Radius":
        value = radius
        pattern = "CylinderRadius"
        point1 = axis_point
        point2 = axis_point + helper * radius
    else:
        value = radius * 2.0
        pattern = "CylinderDiameter"
        point1 = axis_point - helper * radius
        point2 = axis_point + helper * radius

    return {
        "value": value,
        "point1": point1,
        "point2": point2,
        "pattern": pattern,
        "message": "",
    }


def _create_native_dimension_from_candidate(
    doc,
    shape_obj,
    dimension,
    records=None,
    scale=1.0
):
    from .MBDDimension import MBDDimension, update_dimension_signature
    from .MBDPMI import append_pmi_history
    import time

    started = time.perf_counter()

    if records:
        _resolve_curve_usages_to_edges(shape_obj, dimension, records, scale)
    resolve_done = time.perf_counter()

    candidate, message = _dimension_measurement_candidate(shape_obj, dimension)
    measurement_done = time.perf_counter()

    if candidate is None:
        return None, message

    measurement = candidate["measurement"]
    measured = measurement.get("value")

    if measured is None:
        return None, message or "{} has no measured value.".format(
            dimension["step_id"]
        )

    values = dimension.get("values", {})
    nominal_value = values.get("nominal_value", measured)
    upper_tolerance = values.get("upper_tolerance", 0.0)
    lower_tolerance = values.get("lower_tolerance", 0.0)
    lower_tolerance_magnitude = abs(float(lower_tolerance))
    upper_tolerance_magnitude = abs(float(upper_tolerance))
    validation_band = max(
        0.001,
        lower_tolerance_magnitude,
        upper_tolerance_magnitude
    )

    if (
        "nominal_value" in values
        and abs(float(measured) - float(nominal_value)) > validation_band
    ):
        return None, "{} measured value {:.6f} does not match AP242 nominal {:.6f}; skipped to avoid an invalid native dimension from an ambiguous binding.".format(
            dimension["step_id"],
            float(measured),
            float(nominal_value)
        )

    purpose = "Reference"

    if "upper_tolerance" in values and "lower_tolerance" in values:
        if abs(upper_tolerance_magnitude - lower_tolerance_magnitude) <= 1e-9:
            purpose = "EqualBilateral"
        else:
            purpose = "UnequalBilateral"

    object_started = time.perf_counter()
    obj = doc.addObject(
        "App::FeaturePython",
        _next_unique_object_name(doc, "MBD_Dimension")
    )
    MBDDimension(obj)
    object_done = time.perf_counter()
    obj.Label = obj.Name
    obj.DimensionPurpose = purpose
    obj.DimensionKind = dimension.get("dimension_kind", "Linear")
    obj.MeasurementType = "Distance"
    obj.NominalValue = nominal_value
    obj.MeasuredValue = measured
    obj.UpperTolerance = upper_tolerance_magnitude
    obj.LowerTolerance = lower_tolerance_magnitude
    obj.UpperLimit = 0.0
    obj.LowerLimit = 0.0
    obj.ReferenceObject1 = shape_obj
    obj.ReferenceSubelement1 = candidate["ref_sub_1"]
    obj.ReferenceObject2 = shape_obj if candidate["ref_sub_2"] else None
    obj.ReferenceSubelement2 = candidate["ref_sub_2"]
    obj.ReferencePattern = measurement.get("pattern", "")
    obj.ValidationMessage = measurement.get("message", "")
    obj.AP242Entity = dimension.get("ap242_entity", "")
    properties_done = time.perf_counter()
    update_dimension_signature(obj, measurement)
    signature_done = time.perf_counter()
    append_pmi_history(obj, "ap242-dimension-imported")
    history_done = time.perf_counter()

    if history_done - started > 0.25:
        try:
            import FreeCAD
            FreeCAD.Console.PrintMessage(
                "Imported dimension {} phases: resolve {:.3f}s, measurement "
                "{:.3f}s, object {:.3f}s, properties {:.3f}s, signature "
                "{:.3f}s, history {:.3f}s, total {:.3f}s\n".format(
                    dimension["step_id"],
                    resolve_done - started,
                    measurement_done - resolve_done,
                    object_done - object_started,
                    properties_done - object_done,
                    signature_done - properties_done,
                    history_done - signature_done,
                    history_done - started
                )
            )
        except Exception:
            pass

    return obj, ""


def _scaled_length_measure_from_refs(records, refs, scale):
    for ref in refs:
        record = _record_by_ref(records, ref)

        if record is None:
            continue

        if "LENGTH_MEASURE_WITH_UNIT" not in record.get("types", []):
            continue

        value = _scaled_length_from_record(records, record, scale)

        if value is not None:
            return value

    return None


def _imported_fcf_geometry_is_supported(shape_obj, subelement, tolerance_type):
    try:
        from .MBDValidation import geometry_kind
    except Exception:
        return False, "geometry classifier is not available"

    kind = geometry_kind(shape_obj, subelement)
    class_name = kind.get("class_name", "Unknown")

    if tolerance_type == "Straightness":
        if kind.get("is_straightness_capable", False):
            return True, ""

        return (
            False,
            "straightness requires line-like, cylindrical, or conical geometry; {} is {}".format(
                subelement,
                class_name
            )
        )

    if tolerance_type == "Circularity":
        if kind.get("is_roundness_capable", False):
            return True, ""

        return (
            False,
            "circularity/roundness requires circular or revolved geometry; {} is {}".format(
                subelement,
                class_name
            )
        )

    if tolerance_type == "Cylindricity":
        if kind.get("is_cylinder", False):
            return True, ""

        return (
            False,
            "cylindricity requires cylindrical geometry; {} is {}".format(
                subelement,
                class_name
            )
        )

    if tolerance_type in ("CircularRunout", "TotalRunout"):
        if kind.get("is_surface_of_revolution", False):
            return True, ""

        return (
            False,
            "{} requires a surface of revolution; {} is {}".format(
                tolerance_type,
                subelement,
                class_name
            )
        )

    return True, ""


def _imported_fcf_material_condition_is_supported(
    shape_obj,
    controlled_subelements,
    tolerance_type
):
    if tolerance_type not in (
        "Angularity",
        "Parallelism",
        "Perpendicularity",
        "Position",
        "Straightness",
    ):
        return (
            False,
            "the native model supports material-condition modifiers only on feature-of-size position, orientation, and axis straightness tolerances"
        )

    try:
        from .MBDValidation import geometry_kind
    except Exception:
        return False, "geometry classifier is not available"

    for subelement in controlled_subelements:
        kind = geometry_kind(shape_obj, subelement)

        if not kind.get("is_axis_capable", False):
            return (
                False,
                "{} is {}, not an axis-capable feature of size".format(
                    subelement,
                    kind.get("class_name", "Unknown")
                )
            )

    return True, ""


def _create_native_fcf_from_candidate(
    doc,
    shape_obj,
    fcf,
    records,
    datum_system_by_step,
    length_scale_to_mm
):
    from .MBDDatum import update_geometry_signature
    from .MBDFeatureControlFrame import MBDFeatureControlFrame
    from .MBDPMI import append_pmi_history

    tolerance_type = fcf.get("tolerance_type", "")

    if tolerance_type not in NATIVE_FCF_IMPORT_TYPES:
        return None, "{} {} native import is deferred until its imported topology can be re-exported without null AP242 references.".format(
            fcf["step_id"],
            tolerance_type
        )

    if fcf.get("datum_system_refs", []) and tolerance_type not in (
        "Angularity",
        "LineProfile",
        "Parallelism",
        "Perpendicularity",
        "Position",
        "Profile",
        "CircularRunout",
        "TotalRunout",
    ):
        return None, "{} {} native import is deferred because this datum-referenced FCF family still needs an exporter-safe datum-reference path.".format(
            fcf["step_id"],
            tolerance_type
        )

    modifier_values = fcf.get("modifier_values", {})
    unsupported_modifiers = modifier_values.get("unsupported", [])

    if unsupported_modifiers:
        return None, "{} {} native import is deferred because these modifier values could not be parsed: {}.".format(
            fcf["step_id"],
            tolerance_type,
            ", ".join(unsupported_modifiers)
        )

    geometry_usages = [
        usage
        for usage in fcf.get("geometry_usages", [])
        if usage.get("subelement", "")
    ]

    if len(geometry_usages) != 1:
        if (
            len(geometry_usages) < 1
            or tolerance_type not in MULTI_ATTACHMENT_FCF_IMPORT_TYPES
        ):
            return None, "{} {} has {} controlled geometry bindings; native import for this tolerance family currently requires exactly one.".format(
                fcf["step_id"],
                tolerance_type,
                len(geometry_usages)
            )

    tolerance_value = _scaled_length_measure_from_refs(
        records,
        fcf.get("source_refs", []),
        length_scale_to_mm
    )

    if tolerance_value is None:
        return None, "{} {} has no parsed AP242 tolerance value.".format(
            fcf["step_id"],
            tolerance_type
        )

    if tolerance_value <= 0.0:
        return None, "{} {} has non-positive AP242 tolerance value.".format(
            fcf["step_id"],
            tolerance_type
        )

    datum_system = None

    for ref in fcf.get("datum_system_refs", []):
        datum_system = datum_system_by_step.get(ref)

        if datum_system is not None:
            break

    if fcf.get("datum_system_refs", []) and datum_system is None:
        return None, "{} {} has no resolved datum-system reference.".format(
            fcf["step_id"],
            tolerance_type
        )

    if tolerance_type in (
        "Position",
        "Parallelism",
        "Perpendicularity",
        "Angularity",
        "CircularRunout",
        "TotalRunout",
    ) and datum_system is None:
        return None, "{} {} has no resolved datum-system reference.".format(
            fcf["step_id"],
            tolerance_type
        )

    controlled_subelements = [
        str(usage.get("subelement", ""))
        for usage in geometry_usages
    ]
    subelement = controlled_subelements[0]

    if any(not sub.startswith("Face") for sub in controlled_subelements):
        return None, "{} {} native import is deferred because imported FCF round-trip currently requires face-backed controlled attachments.".format(
            fcf["step_id"],
            tolerance_type
        )

    for controlled_subelement in controlled_subelements:
        geometry_supported, geometry_message = _imported_fcf_geometry_is_supported(
            shape_obj,
            controlled_subelement,
            tolerance_type
        )

        if not geometry_supported:
            return None, "{} {} native import is deferred because {}.".format(
                fcf["step_id"],
                tolerance_type,
                geometry_message
            )

    if modifier_values.get("material_condition"):
        material_supported, material_message = (
            _imported_fcf_material_condition_is_supported(
                shape_obj,
                controlled_subelements,
                tolerance_type
            )
        )

        if not material_supported:
            return None, "{} {} native import is deferred because {}.".format(
                fcf["step_id"],
                tolerance_type,
                material_message
            )

    affected_plane_usages = [
        usage
        for usage in fcf.get("affected_plane_usages", [])
        if str(usage.get("subelement", "")).startswith("Edge")
    ]

    if fcf.get("affected_plane_usages", []) and len(affected_plane_usages) != 1:
        return None, "{} {} has an affected-plane association, but it does not resolve to exactly one edge.".format(
            fcf["step_id"],
            tolerance_type
        )

    obj = doc.addObject(
        "App::FeaturePython",
        _next_unique_object_name(doc, "MBD_FCF_" + tolerance_type)
    )
    MBDFeatureControlFrame(obj)
    obj.Label = obj.Name
    obj.ToleranceType = tolerance_type
    obj.ToleranceValue = tolerance_value
    obj.DiameterZone = (
        tolerance_type == "Position"
        or bool(modifier_values.get("material_condition"))
    )
    obj.ProfileAllOver = False
    obj.MaterialConditionModifier = modifier_values.get(
        "material_condition",
        "None"
    )
    obj.ProjectedToleranceZone = "projected_zone_height" in modifier_values
    obj.ProjectedToleranceHeight = modifier_values.get(
        "projected_zone_height",
        0.0
    )
    obj.UnequallyDisposedZone = "unequally_disposed" in modifier_values
    obj.UnequallyDisposedOffset = modifier_values.get(
        "unequally_disposed",
        0.0
    )
    obj.TangentPlaneModifier = bool(modifier_values.get("tangent_plane"))
    obj.StatisticalToleranceModifier = bool(
        modifier_values.get("statistical_tolerance")
    )
    obj.CommonZoneModifier = bool(modifier_values.get("common_zone"))
    obj.MaximumToleranceValueEnabled = "maximum_tolerance" in modifier_values
    obj.MaximumToleranceValue = modifier_values.get("maximum_tolerance", 0.0)
    unit_basis = modifier_values.get("unit_basis", {})
    obj.UnitBasisToleranceEnabled = bool(unit_basis)
    obj.UnitBasisType = unit_basis.get("type", "Length")
    obj.UnitBasisPrimaryLength = unit_basis.get("primary", 0.0)
    obj.UnitBasisSecondaryLength = unit_basis.get("secondary", 0.0)
    obj.NonUniformToleranceZone = bool(
        modifier_values.get("non_uniform_zone")
    )
    obj.RunoutOrientationAngle = modifier_values.get(
        "runout_orientation_angle",
        0.0
    )
    obj.DatumSystem = datum_system
    obj.DatumReference = None
    obj.ControlledObject = shape_obj
    obj.ControlledSubelement = subelement
    obj.ControlledSubelementList = controlled_subelements
    obj.ReferencedObject = shape_obj
    obj.ReferencedSubelement = subelement

    if affected_plane_usages:
        obj.AffectedPlaneObject = shape_obj
        obj.AffectedPlaneSubelement = affected_plane_usages[0]["subelement"]

    update_geometry_signature(obj)
    append_pmi_history(obj, "ap242-fcf-imported")
    return obj, ""


def create_native_datums_and_systems_from_preview(doc, shape_obj, preview):
    """Create native PMI objects from an import preview.

    This is deliberately conservative: it creates only objects whose previewed
    topology bindings can be resolved against the imported shape without
    guessing. Imported PMI families stay preview-only until their native
    objects can validate and re-export without null AP242 references.
    """
    from .MBDDatum import MBDDatumFeature, update_geometry_signature
    from .MBDDatumTarget import (
        MBDDatumTarget,
        update_datum_target_signature,
    )
    from .MBDDatumSystem import (
        MBDDatumSystem,
        datum_system_object_label,
        synchronize_datum_system_label,
    )
    from .MBDPMI import set_pmi_import_metadata
    import time

    try:
        import FreeCAD
    except Exception:
        FreeCAD = None

    created = {
        "datums": [],
        "datum_targets": [],
        "datum_systems": [],
        "dimensions": [],
        "fcfs": [],
    }
    skipped = []
    warnings = []
    datum_by_label = {}
    datum_system_by_step = {}
    target_candidates_by_parent = _datum_target_candidates_by_parent(preview)
    source_file = preview.get("filepath", "")
    timing = {
        "datum_object": 0.0,
        "datum_signature": 0.0,
        "datum_metadata": 0.0,
        "target_object": 0.0,
        "target_signature": 0.0,
        "target_metadata": 0.0,
        "datum_system": 0.0,
        "dimension": 0.0,
        "fcf": 0.0,
    }
    progress_log_path = os.environ.get("MBD_IMPORT_PROGRESS_LOG", "")

    def progress(message):
        if not progress_log_path:
            return

        line = "{:.3f} {}\n".format(time.perf_counter(), message)

        try:
            with open(progress_log_path, "a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
        except Exception:
            pass

    for datum in preview["candidates"]["datums"]:
        subelement = _first_subelement_from_candidate(datum)
        geometry_usages = datum.get("geometry_usages", [])
        referenced_subelements = [
            str(usage.get("subelement", ""))
            for usage in geometry_usages
            if str(usage.get("subelement", ""))
        ]
        target_candidates = target_candidates_by_parent.get(datum["label"], [])
        target_candidate = target_candidates[0] if target_candidates else None
        target_point = None

        if target_candidate is not None:
            placement = target_candidate.get("parameters", {}).get("placement", {})
            target_point = _vector_from_coordinates(placement.get("location"))

            if not subelement:
                subelement = _nearest_face_subelement(shape_obj, target_point)

        if not subelement:
            skipped.append(
                "{} datum {} has no resolved topology binding.".format(
                    datum["step_id"],
                    datum["label"]
                )
            )
            continue

        if not referenced_subelements and subelement:
            referenced_subelements = [subelement]

        if len(referenced_subelements) > 1:
            warnings.append(
                "{} datum {} has {} resolved topology bindings; imported first binding {} as the display anchor and preserved all bindings for export.".format(
                    datum["step_id"],
                    datum["label"],
                    len(referenced_subelements),
                    subelement
                )
            )

        phase_start = time.perf_counter()
        obj = doc.addObject(
            "App::DocumentObjectGroupPython",
            "MBD_DatumFeature_" + datum["label"]
        )
        MBDDatumFeature(obj)
        obj.DatumLabel = datum["label"]
        obj.DatumType = _datum_type_from_subelement(subelement)
        obj.ReferencedObject = shape_obj
        obj.ReferencedSubelement = subelement
        obj.ReferencedSubelementList = referenced_subelements
        timing["datum_object"] += time.perf_counter() - phase_start
        phase_start = time.perf_counter()
        update_geometry_signature(obj)
        timing["datum_signature"] += time.perf_counter() - phase_start
        phase_start = time.perf_counter()
        set_pmi_import_metadata(
            obj,
            source_file,
            datum["step_id"],
            "DATUM",
            "Native"
        )
        timing["datum_metadata"] += time.perf_counter() - phase_start
        datum_by_label[obj.DatumLabel] = obj
        created["datums"].append(obj)

        if target_candidate is None:
            continue

        target_type = target_candidate.get("target_kind", "Unknown")

        if target_type not in ("Point", "Line", "Circle", "Rectangle"):
            warnings.append(
                "{} datum target {} is not imported natively yet.".format(
                    target_candidate["step_id"],
                    target_type
                )
            )
            continue

        parameters = target_candidate.get("parameters", {})
        placement = parameters.get("placement", {})
        point = target_point

        if point is None:
            warnings.append(
                "{} datum target has no AP242 placement point.".format(
                    target_candidate["step_id"]
                )
            )
            continue

        target_number = target_candidate.get("target_number", "1")
        target_id = "{}{}".format(obj.DatumLabel, target_number)
        phase_start = time.perf_counter()
        target_obj = doc.addObject(
            "App::DocumentObjectGroupPython",
            "MBD_DatumTarget_" + target_id
        )
        MBDDatumTarget(target_obj)
        target_obj.TargetId = target_id
        target_obj.TargetType = target_type
        target_obj.ParentDatum = obj
        target_obj.ReferencedObject = shape_obj
        target_obj.ReferencedSubelement = subelement
        target_obj.TargetPoint = point

        direction = _vector_from_coordinates(placement.get("ref_direction"))

        if direction is not None:
            target_obj.TargetDirection = direction

        if target_type == "Line":
            target_obj.TargetLength = float(parameters.get("length", 0.0) or 0.0)
        elif target_type == "Rectangle":
            target_obj.TargetLength = float(parameters.get("length", 0.0) or 0.0)
            target_obj.TargetWidth = float(parameters.get("width", 0.0) or 0.0)
        elif target_type == "Circle":
            target_obj.TargetDiameter = float(parameters.get("diameter", 0.0) or 0.0)
            target_obj.TargetLength = target_obj.TargetDiameter

        timing["target_object"] += time.perf_counter() - phase_start
        phase_start = time.perf_counter()
        update_datum_target_signature(target_obj)
        timing["target_signature"] += time.perf_counter() - phase_start
        phase_start = time.perf_counter()
        set_pmi_import_metadata(
            target_obj,
            source_file,
            target_candidate["step_id"],
            "DATUM_TARGET",
            "Native"
        )
        timing["target_metadata"] += time.perf_counter() - phase_start
        created["datum_targets"].append(target_obj)

    for datum_system in preview["candidates"]["datum_systems"]:
        phase_start = time.perf_counter()
        primary = []
        secondary = []
        tertiary = []
        target_compartments = [primary, secondary, tertiary]

        for index, compartment in enumerate(datum_system.get("compartments", [])):
            if index >= len(target_compartments):
                break

            for label in compartment:
                datum_obj = datum_by_label.get(label)

                if datum_obj is not None:
                    target_compartments[index].append(datum_obj)

        if not any(target_compartments):
            skipped.append(
                "{} datum system has no resolved datum references.".format(
                    datum_system["step_id"]
                )
            )
            continue

        obj = doc.addObject("App::FeaturePython", "MBD_DatumSystem")
        MBDDatumSystem(obj)
        obj.PrimaryDatums = primary
        obj.SecondaryDatums = secondary
        obj.TertiaryDatums = tertiary
        synchronize_datum_system_label(obj)
        obj.Label = datum_system_object_label(obj)
        set_pmi_import_metadata(
            obj,
            source_file,
            datum_system["step_id"],
            "DATUM_SYSTEM",
            "Native"
        )
        created["datum_systems"].append(obj)
        datum_system_by_step[datum_system["step_id"]] = obj
        timing["datum_system"] += time.perf_counter() - phase_start

    for dimension in preview["candidates"]["dimensions"]:
        phase_start = time.perf_counter()
        progress("dimension start {} {}".format(
            dimension.get("step_id", ""),
            dimension.get("ap242_entity", "")
        ))
        if not dimension.get("can_create_native", False):
            skipped.append(
                "{} {} is not imported natively yet.".format(
                    dimension["step_id"],
                    dimension.get("ap242_entity", "dimension")
                )
            )
            continue

        dim_obj, message = _create_native_dimension_from_candidate(
            doc,
            shape_obj,
            dimension,
            preview.get("records", {}),
            preview.get("length_scale_to_mm", 1.0)
        )

        if dim_obj is None:
            skipped.append(message)
            continue

        set_pmi_import_metadata(
            dim_obj,
            source_file,
            dimension["step_id"],
            dimension.get("ap242_entity", "DIMENSION"),
            "Native"
        )
        created["dimensions"].append(dim_obj)

        timing["dimension"] += time.perf_counter() - phase_start
        progress("dimension done {} {:.3f}s".format(
            dimension.get("step_id", ""),
            time.perf_counter() - phase_start
        ))

    records = preview.get("records", {})
    length_scale_to_mm = preview.get("length_scale_to_mm", 1.0)

    for fcf in preview["candidates"]["fcfs"]:
        phase_start = time.perf_counter()
        progress("fcf start {} {} bindings={}".format(
            fcf.get("step_id", ""),
            fcf.get("tolerance_type", "FCF"),
            len(fcf.get("geometry_usages", []))
        ))
        if not fcf.get("can_create_native", False):
            skipped.append(
                "{} {} is not imported natively yet.".format(
                    fcf["step_id"],
                    fcf.get("tolerance_type", "FCF")
                )
            )
            continue

        fcf_obj, message = _create_native_fcf_from_candidate(
            doc,
            shape_obj,
            fcf,
            records,
            datum_system_by_step,
            length_scale_to_mm
        )

        if fcf_obj is None:
            skipped.append(message)
            continue

        set_pmi_import_metadata(
            fcf_obj,
            source_file,
            fcf["step_id"],
            fcf.get("tolerance_type", "FCF"),
            "Native"
        )
        created["fcfs"].append(fcf_obj)
        timing["fcf"] += time.perf_counter() - phase_start
        progress("fcf done {} {:.3f}s".format(
            fcf.get("step_id", ""),
            time.perf_counter() - phase_start
        ))

    if FreeCAD is not None:
        FreeCAD.Console.PrintMessage(
            "AP242 native PMI creation phases: datum object {:.3f}s, "
            "datum signature {:.3f}s, datum metadata {:.3f}s, target object "
            "{:.3f}s, target signature {:.3f}s, target metadata {:.3f}s, "
            "datum systems {:.3f}s, dimensions {:.3f}s, FCFs {:.3f}s\n".format(
                timing["datum_object"],
                timing["datum_signature"],
                timing["datum_metadata"],
                timing["target_object"],
                timing["target_signature"],
                timing["target_metadata"],
                timing["datum_system"],
                timing["dimension"],
                timing["fcf"],
            )
        )

    return {
        "created": created,
        "skipped": skipped,
        "warnings": warnings,
    }


def scan_step_pmi_entities(filepath, records=None):
    counts = {}

    if records is None:
        records = parse_step_entities(filepath)

    for record in _step_records(records):
        for entity in record.get("types", []):
            if entity not in AP242_PMI_ENTITY_SUPPORT:
                continue

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
