# MBDValidation.py

import FreeCAD
import json

import MBDBasicDimension
import MBDDimension
import MBDDatumTarget
from MBDDatumSystem import (
    datum_system_compartments,
    datum_system_datums,
    datum_system_label,
    is_datum_system_object,
)
from MBDPMI import ensure_pmi_identity, pmi_id


SEMANTIC_VALUE_EPSILON = 1e-9


class ValidationIssue:

    def __init__(self, severity, obj, message, subelement=""):
        self.severity = severity
        self.obj = obj
        self.message = message
        self.subelement = subelement

    def object_name(self):
        if self.obj is None:
            return "<document>"

        return self.obj.Name

    def pmi_id(self):
        if self.obj is None:
            return ""

        return pmi_id(self.obj)

    def line(self):
        return "{}: {}: {}".format(
            self.severity.upper(),
            self.object_name(),
            self.message
        )


def is_mbd_datum(obj):
    return (
        hasattr(obj, "IsSemanticPMI")
        and hasattr(obj, "DatumLabel")
        and hasattr(obj, "ReferencedObject")
        and hasattr(obj, "ReferencedSubelement")
    )

def is_mbd_datum_target(obj):
    return (
        hasattr(obj, "IsSemanticPMI")
        and hasattr(obj, "TargetId")
        and hasattr(obj, "ParentDatum")
        and hasattr(obj, "ConstructionObject")
    )


def is_mbd_basic_dimension(obj):
    return (
        hasattr(obj, "IsSemanticPMI")
        and hasattr(obj, "DimensionType")
        and hasattr(obj, "NominalValue")
        and hasattr(obj, "ReferenceObject1")
        and hasattr(obj, "ReferenceObject2")
    )


def is_mbd_dimension(obj):
    return (
        hasattr(obj, "IsSemanticPMI")
        and hasattr(obj, "DimensionPurpose")
        and hasattr(obj, "DimensionKind")
        and hasattr(obj, "MeasurementType")
        and hasattr(obj, "ReferenceObject1")
        and hasattr(obj, "ReferenceObject2")
    )


def validate_datum(obj):
    errors = []

    if not obj.DatumLabel:
        errors.append("{} has no datum label.".format(obj.Name))

    if obj.ReferencedObject is None:
        errors.append("{} has no referenced object.".format(obj.Name))

    if not obj.ReferencedSubelement:
        errors.append("{} has no referenced subelement.".format(obj.Name))

    if obj.ReferencedObject and obj.ReferencedSubelement:
        sub_names = []

        try:
            shape = obj.ReferencedObject.Shape

            sub_names.extend(
                ["Face{}".format(i + 1) for i in range(len(shape.Faces))]
            )
            sub_names.extend(
                ["Edge{}".format(i + 1) for i in range(len(shape.Edges))]
            )
            sub_names.extend(
                ["Vertex{}".format(i + 1) for i in range(len(shape.Vertexes))]
            )

            if obj.ReferencedSubelement not in sub_names:
                errors.append(
                    "{} references {}, but that subelement no longer exists on {}.".format(
                        obj.Name,
                        obj.ReferencedSubelement,
                        obj.ReferencedObject.Name
                    )
                )

        except Exception as e:
            errors.append(
                "{} could not validate referenced geometry: {}".format(
                    obj.Name,
                    str(e)
                )
            )

    return errors


def validate_datum_target(obj):
    errors = []
    target_type = str(obj.TargetType)

    if not obj.TargetId:
        errors.append("{} has no target ID.".format(obj.Name))

    if target_type not in MBDDatumTarget.DATUM_TARGET_TYPES:
        errors.append(
            "{} has unsupported target type {}.".format(
                obj.Name,
                target_type
            )
        )

    if obj.ParentDatum is None:
        errors.append("{} has no parent datum.".format(obj.Name))
    elif not is_mbd_datum(obj.ParentDatum):
        errors.append("{} references an invalid parent datum.".format(obj.Name))

    if obj.ConstructionObject is None:
        errors.append("{} has no construction object.".format(obj.Name))

    if obj.ReferencedObject is None:
        errors.append("{} has no inspected surface object.".format(obj.Name))

    if not obj.ReferencedSubelement:
        errors.append("{} has no inspected surface subelement.".format(obj.Name))

    point = MBDDatumTarget.get_point_from_target(obj)

    if point is None:
        errors.append(
            "{} construction reference does not resolve to a supported {} target.".format(
                obj.Name,
                target_type.lower()
            )
        )
    else:
        obj.TargetPoint = point
        obj.GeometryType = target_type

    if target_type == "Line":
        line = MBDDatumTarget.line_geometry_from_target(obj)

        if line is None:
            errors.append(
                "{} line target requires one finite straight construction edge.".format(
                    obj.Name
                )
            )
        else:
            obj.TargetEndPoint1 = line["start"]
            obj.TargetEndPoint2 = line["end"]
            obj.TargetDirection = line["direction"]
            obj.TargetLength = line["length"]

    distance = MBDDatumTarget.target_surface_distance(obj)

    if distance is None:
        if obj.ReferencedObject and obj.ReferencedSubelement:
            errors.append(
                "{} could not measure target distance to inspected surface.".format(
                    obj.Name
                )
            )
    else:
        obj.SurfaceDistance = distance

        if distance > obj.SurfaceTolerance:
            errors.append(
                "{} target {} is {:.6f} mm from {}.{}.".format(
                    obj.Name,
                    target_type.lower(),
                    distance,
                    obj.ReferencedObject.Name,
                    obj.ReferencedSubelement
                )
            )

    return errors


def validate_basic_dimension(obj):
    errors = []

    if obj.ReferenceObject1 is None:
        errors.append("{} has no first reference.".format(obj.Name))

    if obj.ReferenceObject2 is None and str(obj.DimensionKind) == "Linear":
        errors.append("{} has no second reference.".format(obj.Name))

    if errors:
        return errors

    measured = MBDBasicDimension.measured_value_from_references(
        obj.DimensionType,
        obj.ReferenceObject1,
        obj.ReferenceSubelement1,
        obj.ReferenceObject2,
        obj.ReferenceSubelement2
    )

    if measured is None:
        errors.append(
            "{} references do not resolve to a supported basic dimension.".format(
                obj.Name
            )
        )
        return errors

    obj.MeasuredValue = measured

    if abs(measured - obj.NominalValue) > obj.ValidationTolerance:
        errors.append(
            "{} nominal basic dimension {:.6f} differs from measured {:.6f}.".format(
                obj.Name,
                obj.NominalValue,
                measured
            )
        )

    return errors


DIMENSION_SIZE_PATTERNS = (
    "PlaneToPlane",
    "CylinderDiameter",
    "CylinderRadius",
)


def dimension_appears_to_define_size(obj):
    if str(getattr(obj, "DimensionKind", "")) in ("Diameter", "Radius"):
        return True

    return str(getattr(obj, "ReferencePattern", "")) in DIMENSION_SIZE_PATTERNS


def same_reference(controlled_obj, controlled_sub, ref_obj, ref_sub):
    return (
        controlled_obj is not None
        and ref_obj is not None
        and controlled_obj == ref_obj
        and str(controlled_sub) == str(ref_sub)
    )


def profile_all_over_exists(fcf_objects):
    for fcf in fcf_objects:
        if not is_profile_all_over_fcf(fcf):
            continue

        if getattr(fcf, "ControlledObject", None) is not None:
            return True

    return False


def profile_controls_dimension_reference(fcf, dimension):
    if str(getattr(fcf, "ToleranceType", "")) != "Profile":
        return False

    if is_profile_all_over_fcf(fcf):
        return True

    controlled_obj = getattr(fcf, "ControlledObject", None)
    controlled_sub = getattr(fcf, "ControlledSubelement", "")

    if same_reference(
        controlled_obj,
        controlled_sub,
        dimension.ReferenceObject1,
        dimension.ReferenceSubelement1
    ):
        return True

    if same_reference(
        controlled_obj,
        controlled_sub,
        dimension.ReferenceObject2,
        dimension.ReferenceSubelement2
    ):
        return True

    return False


def basic_size_dimension_has_profile_control(obj, fcf_objects):
    if profile_all_over_exists(fcf_objects):
        return True

    for fcf in fcf_objects:
        if profile_controls_dimension_reference(fcf, obj):
            return True

    return False


def validate_basic_size_dimension_control(obj, fcf_objects):
    if str(getattr(obj, "DimensionPurpose", "")) != "Basic":
        return []

    if not dimension_appears_to_define_size(obj):
        return []

    if basic_size_dimension_has_profile_control(obj, fcf_objects):
        return []

    return [
        "{} is a basic size dimension but no profile FCF controls its surfaces. Basic dimensions can locate or define size only when the geometry is controlled by an FCF such as profile.".format(
            obj.Name
        )
    ]


def validate_dimension(obj, fcf_objects=None):
    errors = []
    fcf_objects = fcf_objects or []
    dimension_kind = str(obj.DimensionKind)
    purpose = str(obj.DimensionPurpose)

    if obj.ReferenceObject1 is None:
        errors.append("{} has no first reference.".format(obj.Name))

    if obj.ReferenceObject2 is None and dimension_kind == "Linear":
        errors.append("{} has no second reference.".format(obj.Name))

    if dimension_kind in ("Diameter", "Radius") and (
        obj.ReferenceObject2 is not None
        or bool(obj.ReferenceSubelement2)
    ):
        errors.append(
            "{} {} dimensions must use exactly one cylindrical face reference.".format(
                obj.Name,
                dimension_kind.lower()
            )
        )

    if dimension_kind not in ("Linear", "Diameter", "Radius"):
        errors.append(
            "{} uses unsupported dimension kind {}.".format(
                obj.Name,
                obj.DimensionKind
            )
        )

    if errors:
        return errors

    measured = MBDDimension.measured_value_from_references(obj)

    if measured is None:
        errors.append(
            "{} references do not resolve to a supported dimension.".format(
                obj.Name
            )
        )
        return errors

    obj.MeasuredValue = measured

    expected_pattern = {
        "Diameter": "CylinderDiameter",
        "Radius": "CylinderRadius",
    }.get(dimension_kind)

    if expected_pattern and str(obj.ReferencePattern) != expected_pattern:
        errors.append(
            "{} {} dimension did not resolve to cylindrical size geometry.".format(
                obj.Name,
                dimension_kind.lower()
            )
        )

    errors.extend(
        validate_basic_size_dimension_control(obj, fcf_objects)
    )

    if purpose in ("Basic", "Reference", "UnequalBilateral", "EqualBilateral"):
        if abs(measured - obj.NominalValue) > obj.ValidationTolerance:
            errors.append(
                "{} nominal dimension {:.6f} differs from measured {:.6f}.".format(
                    obj.Name,
                    obj.NominalValue,
                    measured
                )
            )

    if purpose in ("UnequalBilateral", "EqualBilateral"):
        if obj.UpperTolerance < 0 or obj.LowerTolerance < 0:
            errors.append(
                "{} bilateral tolerances must be non-negative.".format(
                    obj.Name
                )
            )

    if (
        purpose == "EqualBilateral"
        and abs(obj.UpperTolerance - obj.LowerTolerance)
        > SEMANTIC_VALUE_EPSILON
    ):
        errors.append(
            "{} equal bilateral tolerance must have equal upper and lower values.".format(
                obj.Name
            )
        )

    if purpose in ("Basic", "Reference") and (
        abs(obj.UpperTolerance) > SEMANTIC_VALUE_EPSILON
        or abs(obj.LowerTolerance) > SEMANTIC_VALUE_EPSILON
    ):
        errors.append(
            "{} {} dimension must not carry plus/minus tolerance values.".format(
                obj.Name,
                purpose.lower()
            )
        )

    if purpose == "Limits":
        if obj.LowerLimit > obj.UpperLimit:
            errors.append(
                "{} lower limit is greater than upper limit.".format(
                    obj.Name
                )
            )

        if measured < obj.LowerLimit or measured > obj.UpperLimit:
            errors.append(
                "{} measured value {:.6f} is outside limits {:.6f} to {:.6f}.".format(
                    obj.Name,
                    measured,
                    obj.LowerLimit,
                    obj.UpperLimit
                )
            )

    return errors

def validate_unique_datum_labels(datum_objects):
    errors = []
    labels = {}

    for obj in datum_objects:
        label = obj.DatumLabel.strip().upper()

        if label in labels:
            errors.append(
                "Duplicate datum label {} used by {} and {}.".format(
                    label,
                    labels[label].Name,
                    obj.Name
                )
            )
        else:
            labels[label] = obj

    return errors
def is_mbd_datum_system(obj):
    return is_datum_system_object(obj)

def validate_datum_system(obj):
    errors = []
    compartments = datum_system_compartments(obj)

    if not compartments[0][1]:
        errors.append(
            "{} has no primary datum-reference compartment.".format(obj.Name)
        )

    if compartments[2][1] and not compartments[1][1]:
        errors.append(
            "{} defines a tertiary compartment without a secondary compartment.".format(
                obj.Name
            )
        )

    datum_names = []

    for role_name, datums in compartments:
        for datum in datums:
            if datum is None or not hasattr(datum, "DatumLabel"):
                errors.append(
                    "{} references an invalid datum object in its {} compartment.".format(
                        obj.Name,
                        role_name.lower()
                    )
                )
                continue

            datum_names.append(datum.Name)

    if len(datum_names) != len(set(datum_names)):
        errors.append(
            "{} contains a datum feature in more than one compartment.".format(
                obj.Name
            )
        )

    return errors


def datum_targets_for(doc, datum_obj):
    return [
        obj for obj in doc.Objects
        if is_mbd_datum_target(obj) and obj.ParentDatum == datum_obj
    ]


def _distinct_target_points(points, tolerance=1e-6):
    distinct = []

    for point in points:
        if point is None:
            continue

        if not any((point - existing).Length <= tolerance for existing in distinct):
            distinct.append(point)

    return distinct


def _target_support_points(target):
    if str(target.TargetType) == "Line":
        line = MBDDatumTarget.line_geometry_from_target(target)

        if line is None:
            return []

        return [line["start"], line["end"]]

    point = MBDDatumTarget.get_point_from_target(target)
    return [point] if point is not None else []


def _points_are_collinear(points, tolerance=1e-6):
    if len(points) < 3:
        return True

    origin = points[0]
    direction = None

    for point in points[1:]:
        vector = point - origin

        if vector.Length > tolerance:
            direction = vector
            break

    if direction is None:
        return True

    for point in points[1:]:
        if direction.cross(point - origin).Length > tolerance:
            return False

    return True


def _target_independence_error(obj, role_name, datum_obj, targets):
    support_points = []

    for target in targets:
        support_points.extend(_target_support_points(target))

    distinct_points = _distinct_target_points(support_points)

    if role_name == "Primary":
        if len(distinct_points) < 3:
            return (
                "{} uses target-based primary datum {}, but its targets do not provide three distinct support points.".format(
                    obj.Name,
                    datum_obj.DatumLabel
                )
            )

        if _points_are_collinear(distinct_points):
            return (
                "{} uses target-based primary datum {}, but its targets are collinear and do not establish a datum plane.".format(
                    obj.Name,
                    datum_obj.DatumLabel
                )
            )

    if role_name == "Secondary" and len(distinct_points) < 2:
        return (
            "{} uses target-based secondary datum {}, but its targets do not provide two distinct support points.".format(
                obj.Name,
                datum_obj.DatumLabel
            )
        )

    if role_name == "Tertiary" and len(distinct_points) < 1:
        return (
            "{} uses target-based tertiary datum {}, but no usable target support point was found.".format(
                obj.Name,
                datum_obj.DatumLabel
            )
        )

    return None


def validate_datum_system_target_sufficiency(doc, obj):
    errors = []
    required_counts = {
        "Primary": 3,
        "Secondary": 2,
        "Tertiary": 1,
    }

    for role_name, datums in datum_system_compartments(obj):
        required_count = required_counts[role_name]

        for datum_obj in datums:
            targets = datum_targets_for(doc, datum_obj)

            if not targets:
                continue

            constraint_count = sum(
                2 if str(target.TargetType) == "Line" else 1
                for target in targets
                if str(target.TargetType) in {"Point", "Line"}
            )

            if constraint_count < required_count:
                errors.append(
                    "{} uses target-based {} datum {}, but {} point-equivalent constraints are required and {} are defined.".format(
                        obj.Name,
                        role_name.lower(),
                        datum_obj.DatumLabel,
                        required_count,
                        constraint_count
                    )
                )
                continue

            independence_error = _target_independence_error(
                obj,
                role_name,
                datum_obj,
                targets
            )

            if independence_error:
                errors.append(independence_error)

    return errors

def is_mbd_fcf(obj):

    return (
        hasattr(obj, "ToleranceType")
        and hasattr(obj, "ToleranceValue")
        and hasattr(obj, "ControlledObject")
    )

def is_semantic_pmi(obj):
    return hasattr(obj, "IsSemanticPMI") and obj.IsSemanticPMI


def semantic_pmi_objects(doc):
    return [
        obj for obj in doc.Objects
        if is_semantic_pmi(obj)
    ]


def is_profile_all_over_fcf(obj):
    return (
        is_mbd_fcf(obj)
        and str(getattr(obj, "ToleranceType", "")) == "Profile"
        and getattr(obj, "ProfileAllOver", False)
    )


def fcf_geometry_text(obj):
    if is_profile_all_over_fcf(obj) and not getattr(obj, "ControlledSubelement", ""):
        return "Whole body"

    return getattr(obj, "GeometryType", "")


def attachment_text(obj):
    if is_mbd_datum_system(obj):
        return datum_system_label(obj)

    if is_mbd_dimension(obj):
        ref1 = "<none>"
        ref2 = "<none>"

        if obj.ReferenceObject1:
            ref1 = obj.ReferenceObject1.Name

            if obj.ReferenceSubelement1:
                ref1 += "." + obj.ReferenceSubelement1

        if obj.ReferenceObject2:
            ref2 = obj.ReferenceObject2.Name

            if obj.ReferenceSubelement2:
                ref2 += "." + obj.ReferenceSubelement2

        return "{} to {}".format(ref1, ref2)

    if is_mbd_basic_dimension(obj):
        ref1 = "<none>"
        ref2 = "<none>"

        if obj.ReferenceObject1:
            ref1 = obj.ReferenceObject1.Name

            if obj.ReferenceSubelement1:
                ref1 += "." + obj.ReferenceSubelement1

        if obj.ReferenceObject2:
            ref2 = obj.ReferenceObject2.Name

            if obj.ReferenceSubelement2:
                ref2 += "." + obj.ReferenceSubelement2

        return "{} to {}".format(ref1, ref2)

    if is_mbd_datum_target(obj):
        inspected = "<none>"

        if obj.ReferencedObject:
            inspected = "{}.{}".format(
                obj.ReferencedObject.Name,
                obj.ReferencedSubelement
            )

        construction = "<none>"

        if obj.ConstructionObject:
            construction = obj.ConstructionObject.Name

            if obj.ConstructionSubelement:
                construction += "." + obj.ConstructionSubelement

        return "{} on {}".format(construction, inspected)

    if hasattr(obj, "ControlledObject"):
        controlled_object = (
            obj.ControlledObject.Name
            if obj.ControlledObject
            else "<none>"
        )

        if is_profile_all_over_fcf(obj) and not getattr(obj, "ControlledSubelement", ""):
            return "{} (all over)".format(controlled_object)

        return "{}.{}".format(
            controlled_object,
            obj.ControlledSubelement
        )

    if hasattr(obj, "ReferencedObject"):
        referenced_object = (
            obj.ReferencedObject.Name
            if obj.ReferencedObject
            else "<none>"
        )
        return "{}.{}".format(
            referenced_object,
            obj.ReferencedSubelement
        )

    return ""


def pmi_type(obj):
    if is_mbd_dimension(obj):
        return "Dimension"

    if is_mbd_basic_dimension(obj):
        return "Basic Dimension"

    if is_mbd_datum_target(obj):
        return "Datum Target"

    if is_mbd_datum(obj):
        return "Datum"

    if is_mbd_fcf(obj):
        return "FCF"

    if is_mbd_datum_system(obj):
        return "Datum System"

    return "PMI"


def validate_geometry_signature(obj):
    if not hasattr(obj, "GeometrySignature"):
        return []

    if not obj.GeometrySignature:
        return []

    if not hasattr(obj, "ReferencedObject"):
        return []

    if not hasattr(obj, "ReferencedSubelement"):
        return []

    try:
        old_sig = json.loads(obj.GeometrySignature)
    except Exception as e:
        obj.GeometrySignatureValid = False
        return [
            ValidationIssue(
                "warning",
                obj,
                "stored geometry signature could not be parsed: {}".format(e)
            )
        ]

    ref_obj = obj.ReferencedObject
    sub = obj.ReferencedSubelement

    try:
        target = ref_obj.Shape.getElement(sub)
    except Exception as e:
        obj.GeometrySignatureValid = False
        return [
            ValidationIssue(
                "warning",
                obj,
                "referenced subelement {} could not be resolved: {}".format(
                    sub,
                    e
                ),
                sub
            )
        ]

    warnings = []

    try:
        new_com = [
            round(target.CenterOfMass.x, 6),
            round(target.CenterOfMass.y, 6),
            round(target.CenterOfMass.z, 6),
        ]

        old_com = old_sig.get("CenterOfMass")
        if old_com:
            dx = new_com[0] - old_com[0]
            dy = new_com[1] - old_com[1]
            dz = new_com[2] - old_com[2]
            dist = (dx * dx + dy * dy + dz * dz) ** 0.5

            if dist > 0.5:
                warnings.append(
                    "center of mass moved {:.3f} mm".format(dist)
                )
    except Exception:
        pass

    try:
        old_area = old_sig.get("Area")
        new_area = target.Area

        if old_area:
            pct = abs(new_area - old_area) / old_area * 100.0

            if pct > 5.0:
                warnings.append(
                    "area changed by {:.1f}%".format(pct)
                )
    except Exception:
        pass

    try:
        old_type = old_sig.get("GeometryType")
        new_type = "Unknown"

        try:
            new_type = target.Surface.__class__.__name__
        except Exception:
            try:
                new_type = target.Curve.__class__.__name__
            except Exception:
                pass

        if old_type and old_type != new_type:
            warnings.append(
                "geometry type changed from {} to {}".format(
                    old_type,
                    new_type
                )
            )
    except Exception:
        pass

    obj.GeometrySignatureValid = len(warnings) == 0

    return [
        ValidationIssue(
            "warning",
            obj,
            warning,
            sub
        )
        for warning in warnings
    ]


def validate_document_structured(doc):
    issues = []
    datum_objects = [obj for obj in doc.Objects if is_mbd_datum(obj)]
    datum_targets = [obj for obj in doc.Objects if is_mbd_datum_target(obj)]
    basic_dimensions = [obj for obj in doc.Objects if is_mbd_basic_dimension(obj)]
    dimensions = [obj for obj in doc.Objects if is_mbd_dimension(obj)]
    datum_systems = [obj for obj in doc.Objects if is_mbd_datum_system(obj)]
    fcf_objects = [obj for obj in doc.Objects if is_mbd_fcf(obj)]

    for obj in semantic_pmi_objects(doc):
        ensure_pmi_identity(obj, "validated")
        issues.extend(validate_geometry_signature(obj))

    for error in validate_unique_datum_labels(datum_objects):
        issues.append(ValidationIssue("error", None, error))

    for obj in datum_objects:
        for error in validate_datum(obj):
            issues.append(ValidationIssue("error", obj, error))

    for obj in datum_targets:
        for error in validate_datum_target(obj):
            issues.append(ValidationIssue("error", obj, error))

    for obj in basic_dimensions:
        for error in validate_basic_dimension(obj):
            issues.append(ValidationIssue("error", obj, error))

    for obj in dimensions:
        for error in validate_dimension(obj, fcf_objects):
            issues.append(ValidationIssue("error", obj, error))

    for obj in datum_systems:
        for error in validate_datum_system(obj):
            issues.append(ValidationIssue("error", obj, error))

        for error in validate_datum_system_target_sufficiency(doc, obj):
            issues.append(ValidationIssue("error", obj, error))

    for obj in fcf_objects:
        for error in validate_fcf(obj):
            issues.append(ValidationIssue("error", obj, error))

    return {
        "datums": datum_objects,
        "datum_targets": datum_targets,
        "basic_dimensions": basic_dimensions,
        "dimensions": dimensions,
        "datum_systems": datum_systems,
        "fcfs": fcf_objects,
        "issues": issues,
    }


def subshape_from_reference(ref_obj, subelement):
    if ref_obj is None or not subelement:
        return None

    try:
        return ref_obj.Shape.getElement(subelement)
    except Exception:
        return None


def geometry_class_name(shape):
    if shape is None:
        return "Unknown"

    try:
        return shape.Surface.__class__.__name__
    except Exception:
        pass

    try:
        return shape.Curve.__class__.__name__
    except Exception:
        pass

    if hasattr(shape, "Point"):
        return "Point"

    return "Unknown"


def geometry_kind(ref_obj, subelement):
    shape = subshape_from_reference(ref_obj, subelement)
    class_name = geometry_class_name(shape)
    lowered = class_name.lower()
    sub = str(subelement)

    result = {
        "shape": shape,
        "class_name": class_name,
        "is_face": sub.startswith("Face"),
        "is_edge": sub.startswith("Edge"),
        "is_vertex": sub.startswith("Vertex"),
        "is_plane": "plane" in lowered,
        "is_cylinder": "cylinder" in lowered,
        "is_cone": "cone" in lowered,
        "is_sphere": "sphere" in lowered,
        "is_torus": "torus" in lowered,
        "is_line": "line" in lowered,
        "is_circle": "circle" in lowered or "ellipse" in lowered,
    }
    result["is_surface_of_revolution"] = (
        result["is_cylinder"]
        or result["is_cone"]
        or result["is_sphere"]
        or result["is_torus"]
    )
    result["is_axis_capable"] = (
        result["is_cylinder"]
        or result["is_cone"]
        or result["is_line"]
        or result["is_circle"]
    )
    result["is_roundness_capable"] = (
        result["is_cylinder"]
        or result["is_cone"]
        or result["is_sphere"]
        or result["is_torus"]
        or result["is_circle"]
    )
    result["is_straightness_capable"] = (
        result["is_line"]
        or result["is_cylinder"]
        or result["is_cone"]
    )

    return result


def datum_geometry_kind(datum_obj):
    if datum_obj is None:
        return None

    return geometry_kind(
        getattr(datum_obj, "ReferencedObject", None),
        getattr(datum_obj, "ReferencedSubelement", "")
    )


def datum_is_axis_capable(datum_obj):
    if datum_obj is None:
        return False

    if str(getattr(datum_obj, "DatumType", "")) == "Axis":
        return True

    kind = datum_geometry_kind(datum_obj)

    if kind is None:
        return False

    return kind["is_axis_capable"]


def datum_is_plane_capable(datum_obj):
    if datum_obj is None:
        return False

    if str(getattr(datum_obj, "DatumType", "")) == "Plane":
        return True

    kind = datum_geometry_kind(datum_obj)

    if kind is None:
        return False

    return kind["is_plane"]


def datum_system_is_axis_capable(datum_system):
    if datum_system is None:
        return False

    for datum in datum_system_datums(datum_system):
        if datum_is_axis_capable(datum):
            return True

    return False


def datum_system_is_plane_or_axis_capable(datum_system):
    if datum_system is None:
        return False

    return any(
        datum_is_plane_capable(datum) or datum_is_axis_capable(datum)
        for datum in datum_system_datums(datum_system)
    )


def fcf_has_datum_reference(obj):
    return (
        hasattr(obj, "DatumReference")
        and obj.DatumReference is not None
    )


def validate_fcf_rule_set(obj):
    errors = []
    tolerance_type = str(getattr(obj, "ToleranceType", ""))

    if is_profile_all_over_fcf(obj):
        return errors

    controlled_kind = geometry_kind(
        getattr(obj, "ControlledObject", None),
        getattr(obj, "ControlledSubelement", "")
    )

    if controlled_kind["shape"] is None:
        return errors

    no_datum_allowed = (
        "Flatness",
        "Straightness",
        "Circularity",
        "Cylindricity",
    )

    if (
        tolerance_type in no_datum_allowed
        and (
            fcf_has_datum_reference(obj)
            or getattr(obj, "DatumSystem", None) is not None
        )
    ):
        errors.append(
            "{} {} tolerance should not reference a datum.".format(
                obj.Name,
                tolerance_type
            )
        )

    if tolerance_type == "Flatness" and not controlled_kind["is_plane"]:
        errors.append(
            "{} flatness must control a planar face; {} is {}.".format(
                obj.Name,
                obj.ControlledSubelement,
                controlled_kind["class_name"]
            )
        )

    if tolerance_type in ("Parallelism", "Perpendicularity"):
        if not (
            controlled_kind["is_plane"]
            or controlled_kind["is_axis_capable"]
        ):
            errors.append(
                "{} {} must control a planar or axis-capable feature; {} is {}.".format(
                    obj.Name,
                    tolerance_type,
                    obj.ControlledSubelement,
                    controlled_kind["class_name"]
                )
            )

        if (
            not fcf_has_datum_reference(obj)
            and getattr(obj, "DatumSystem", None) is None
        ):
            return errors

        if fcf_has_datum_reference(obj):
            datum_ref = obj.DatumReference

            if not (
                datum_is_plane_capable(datum_ref)
                or datum_is_axis_capable(datum_ref)
            ):
                errors.append(
                    "{} datum reference {} does not establish a plane or axis for {}.".format(
                        obj.Name,
                        datum_ref.DatumLabel,
                        tolerance_type
                    )
                )
        elif not datum_system_is_plane_or_axis_capable(obj.DatumSystem):
            errors.append(
                "{} datum system does not establish a plane or axis for {}.".format(
                    obj.Name,
                    tolerance_type
                )
            )

    if tolerance_type == "Angularity":
        if not (
            controlled_kind["is_plane"]
            or controlled_kind["is_axis_capable"]
        ):
            errors.append(
                "{} angularity must control a planar or axis-capable feature; {} is {}.".format(
                    obj.Name,
                    obj.ControlledSubelement,
                    controlled_kind["class_name"]
                )
            )

        if fcf_has_datum_reference(obj):
            datum_ref = obj.DatumReference

            if not (
                datum_is_plane_capable(datum_ref)
                or datum_is_axis_capable(datum_ref)
            ):
                errors.append(
                    "{} datum reference {} does not establish a plane or axis for angularity.".format(
                        obj.Name,
                        datum_ref.DatumLabel
                    )
                )
        elif (
            getattr(obj, "DatumSystem", None) is not None
            and not datum_system_is_plane_or_axis_capable(obj.DatumSystem)
        ):
            errors.append(
                "{} datum system does not establish a plane or axis for angularity.".format(
                    obj.Name
                )
            )

    if tolerance_type == "Straightness":
        if not controlled_kind["is_straightness_capable"]:
            errors.append(
                "{} straightness must control a line-like, cylindrical, or conical feature; {} is {}.".format(
                    obj.Name,
                    obj.ControlledSubelement,
                    controlled_kind["class_name"]
                )
            )

    if tolerance_type == "Circularity":
        if not controlled_kind["is_roundness_capable"]:
            errors.append(
                "{} circularity/roundness must control a circular or revolved feature; {} is {}.".format(
                    obj.Name,
                    obj.ControlledSubelement,
                    controlled_kind["class_name"]
                )
            )

    if tolerance_type == "Cylindricity":
        if not controlled_kind["is_cylinder"]:
            errors.append(
                "{} cylindricity must control a cylindrical face; {} is {}.".format(
                    obj.Name,
                    obj.ControlledSubelement,
                    controlled_kind["class_name"]
                )
            )

    if tolerance_type == "LineProfile":
        if not controlled_kind["is_edge"]:
            errors.append(
                "{} line profile must control an edge or curve; {} is {}.".format(
                    obj.Name,
                    obj.ControlledSubelement,
                    controlled_kind["class_name"]
                )
            )

    if tolerance_type in ("CircularRunout", "TotalRunout"):
        if not controlled_kind["is_surface_of_revolution"]:
            errors.append(
                "{} {} must control a surface of revolution; {} is {}.".format(
                    obj.Name,
                    tolerance_type,
                    obj.ControlledSubelement,
                    controlled_kind["class_name"]
                )
            )

        if fcf_has_datum_reference(obj):
            datum_ref = obj.DatumReference

            if not datum_is_axis_capable(datum_ref):
                errors.append(
                    "{} datum reference {} must establish an axis for {}.".format(
                        obj.Name,
                        datum_ref.DatumLabel,
                        tolerance_type
                    )
                )
        elif getattr(obj, "DatumSystem", None) is not None:
            if not datum_system_is_axis_capable(obj.DatumSystem):
                errors.append(
                    "{} datum system must include an axis-capable datum for {}.".format(
                        obj.Name,
                        tolerance_type
                    )
                )

    return errors


def validate_fcf(obj):

    errors = []

    if obj.ToleranceValue <= 0:

        errors.append(
            "{} has non-positive tolerance value.".format(
                obj.Name
            )
        )

    tolerance_type = str(getattr(obj, "ToleranceType", ""))

    if tolerance_type == "Position" and obj.DatumSystem is None:

        errors.append(
            "{} has no datum system.".format(
                obj.Name
            )
        )

    if (
        tolerance_type in ("Parallelism", "Perpendicularity", "Angularity")
        and not fcf_has_datum_reference(obj)
        and getattr(obj, "DatumSystem", None) is None
    ):

        errors.append(
            "{} has no referenced datum feature or datum system.".format(
                obj.Name
            )
        )

    if (
        tolerance_type in ("CircularRunout", "TotalRunout")
        and not fcf_has_datum_reference(obj)
        and getattr(obj, "DatumSystem", None) is None
    ):
        errors.append(
            "{} has no referenced datum feature or datum system.".format(
                obj.Name
            )
        )

    profile_all_over = (
        tolerance_type == "Profile"
        and getattr(obj, "ProfileAllOver", False)
    )

    if obj.ControlledObject is None:

        errors.append(
            "{} has no controlled object.".format(
                obj.Name
            )
        )

    if not obj.ControlledSubelement and not profile_all_over:

        errors.append(
            "{} has no controlled subelement.".format(
                obj.Name
            )
        )

    if profile_all_over and obj.ControlledObject:

        try:

            if not hasattr(obj.ControlledObject, "Shape"):
                errors.append(
                    "{} all-over profile is not attached to a shape object.".format(
                        obj.Name
                    )
                )

        except Exception as e:

            errors.append(
                "{} all-over profile geometry validation failed: {}".format(
                    obj.Name,
                    str(e)
                )
            )

    if obj.ControlledObject and obj.ControlledSubelement:

        try:

            shape = obj.ControlledObject.Shape

            valid_names = []

            valid_names.extend(
                ["Face{}".format(i + 1)
                 for i in range(len(shape.Faces))]
            )

            valid_names.extend(
                ["Edge{}".format(i + 1)
                 for i in range(len(shape.Edges))]
            )

            valid_names.extend(
                ["Vertex{}".format(i + 1)
                 for i in range(len(shape.Vertexes))]
            )

            if obj.ControlledSubelement not in valid_names:

                errors.append(
                    "{} references missing subelement {}.".format(
                        obj.Name,
                        obj.ControlledSubelement
                    )
                )

        except Exception as e:

            errors.append(
                "{} geometry validation failed: {}".format(
                    obj.Name,
                    str(e)
                )
            )

    errors.extend(validate_fcf_rule_set(obj))

    return errors

def validate_document(doc):
    structured = validate_document_structured(doc)
    datum_objects = structured["datums"]
    dimensions = structured["dimensions"]
    datum_systems = structured["datum_systems"]
    fcf_objects = structured["fcfs"]

    lines = []
    total_errors = []

    total_errors = validate_unique_datum_labels(datum_objects)

    lines.append("MBD Validation Report")
    lines.append("")
    lines.append("Datum features found: {}".format(len(datum_objects)))
    lines.append("")

    for obj in datum_objects:
        lines.append(
            "{}: Datum {} -> {}.{}".format(
                obj.Name,
                obj.DatumLabel,
                obj.ReferencedObject.Name if obj.ReferencedObject else "<none>",
                obj.ReferencedSubelement
            )
        )

        errors = validate_datum(obj)

        if errors:
            total_errors.extend(errors)

    lines.append("")
    lines.append("Dimensions found: {}".format(len(dimensions)))
    lines.append("")

    for dimension in dimensions:
        lines.append(
            "{}: {} {} {:.4f} -> {}".format(
                dimension.Name,
                dimension.DimensionPurpose,
                dimension.DimensionKind,
                dimension.NominalValue,
                attachment_text(dimension)
            )
        )

    lines.append("")
    lines.append(
        "Datum systems found: {}".format(len(datum_systems))
    )
    lines.append("")

    for ds in datum_systems:
        lines.append(
            "{}: {}".format(
                ds.Name,
                datum_system_label(ds)
            )
        )

        errors = validate_datum_system(ds)

        if errors:
            total_errors.extend(errors)

    lines.append("")

    lines.append(
        "Feature control frames found: {}".format(
            len(fcf_objects)
        )
    )
    lines.append("")
    for fcf in fcf_objects:

        ds_name = "<none>"

        if getattr(fcf, "DatumSystem", None):
            ds_name = fcf.DatumSystem.Name
        elif getattr(fcf, "DatumReference", None):
            ds_name = fcf.DatumReference.Name

        lines.append(
            "{}: {} {:.4f} -> {} [{}]".format(
                fcf.Name,
                fcf.ToleranceType,
                fcf.ToleranceValue,
                attachment_text(fcf),
                ds_name
            )
        )

        errors = validate_fcf(fcf)

        if errors:
            total_errors.extend(errors)

    lines.append("")
    structured_issues = structured["issues"]
    structured_lines = set([issue.line() for issue in structured_issues])

    for err in total_errors:
        structured_lines.add("ERROR: <document>: " + err)

    if structured_lines:
        lines.append("Issues:")
        for line in sorted(structured_lines):
            lines.append("- " + line)
    else:
        lines.append("No validation issues found.")

    return "\n".join(lines)
