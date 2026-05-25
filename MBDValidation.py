# MBDValidation.py

import FreeCAD
import json

import MBDBasicDimension
import MBDDatumTarget
from MBDPMI import ensure_pmi_identity, pmi_id


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

    if not obj.TargetId:
        errors.append("{} has no target ID.".format(obj.Name))

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
            "{} construction reference does not resolve to a point.".format(
                obj.Name
            )
        )
    else:
        obj.TargetPoint = point

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
                "{} target point is {:.6f} mm from {}.{}.".format(
                    obj.Name,
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

    if obj.ReferenceObject2 is None:
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

    return (
        hasattr(obj, "PrimaryDatum")
        and hasattr(obj, "IsSemanticPMI")
    )

def validate_datum_system(obj):

    errors = []

    datums = []

    if obj.PrimaryDatum:
        datums.append(obj.PrimaryDatum)

    if obj.SecondaryDatum:
        datums.append(obj.SecondaryDatum)

    if obj.TertiaryDatum:
        datums.append(obj.TertiaryDatum)

    labels = []

    for datum in datums:

        if not hasattr(datum, "DatumLabel"):

            errors.append(
                "{} references invalid datum object {}.".format(
                    obj.Name,
                    datum.Name
                )
            )

            continue

        labels.append(datum.DatumLabel)

    if len(labels) != len(set(labels)):

        errors.append(
            "{} contains duplicate datum references.".format(
                obj.Name
            )
        )

    return errors


def datum_targets_for(doc, datum_obj):
    return [
        obj for obj in doc.Objects
        if is_mbd_datum_target(obj) and obj.ParentDatum == datum_obj
    ]


def validate_datum_system_target_sufficiency(doc, obj):
    errors = []
    datum_roles = [
        ("PrimaryDatum", "primary", 3),
        ("SecondaryDatum", "secondary", 2),
        ("TertiaryDatum", "tertiary", 1),
    ]

    for prop_name, role_name, required_count in datum_roles:
        if not hasattr(obj, prop_name):
            continue

        datum_obj = getattr(obj, prop_name)

        if not datum_obj:
            continue

        targets = datum_targets_for(doc, datum_obj)

        if not targets:
            continue

        point_targets = [
            target for target in targets
            if str(target.TargetType) == "Point"
        ]

        if len(point_targets) < required_count:
            errors.append(
                "{} uses target-based {} datum {}, but {} point targets are required and {} are defined.".format(
                    obj.Name,
                    role_name,
                    datum_obj.DatumLabel,
                    required_count,
                    len(point_targets)
                )
            )

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


def attachment_text(obj):
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
        "datum_systems": datum_systems,
        "fcfs": fcf_objects,
        "issues": issues,
    }


def validate_fcf(obj):

    errors = []

    if obj.ToleranceValue <= 0:

        errors.append(
            "{} has non-positive tolerance value.".format(
                obj.Name
            )
        )

    if obj.DatumSystem is None:

        errors.append(
            "{} has no datum system.".format(
                obj.Name
            )
        )

    if obj.ControlledObject is None:

        errors.append(
            "{} has no controlled object.".format(
                obj.Name
            )
        )

    if not obj.ControlledSubelement:

        errors.append(
            "{} has no controlled subelement.".format(
                obj.Name
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

    return errors

def validate_document(doc):
    structured = validate_document_structured(doc)
    datum_objects = [obj for obj in doc.Objects if is_mbd_datum(obj)]

    if not datum_objects:
        return "No MBD datum features found."

    datum_systems = [
        obj for obj in doc.Objects
        if is_mbd_datum_system(obj)
    ]

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
    lines.append(
        "Datum systems found: {}".format(len(datum_systems))
    )
    lines.append("")

    for ds in datum_systems:

        lines.append(
            "{}: {} | {} | {}".format(
                ds.Name,
                ds.PrimaryDatum.DatumLabel
                    if ds.PrimaryDatum else "-",
                ds.SecondaryDatum.DatumLabel
                    if ds.SecondaryDatum else "-",
                ds.TertiaryDatum.DatumLabel
                    if ds.TertiaryDatum else "-"
            )
        )

        errors = validate_datum_system(ds)

        if errors:
            total_errors.extend(errors)

    lines.append("")

    fcf_objects = [
        obj for obj in doc.Objects
        if is_mbd_fcf(obj)
    ]
    lines.append(
        "Feature control frames found: {}".format(
            len(fcf_objects)
        )
    )
    lines.append("")
    for fcf in fcf_objects:

        ds_name = "<none>"

        if fcf.DatumSystem:
            ds_name = fcf.DatumSystem.Name

        lines.append(
            "{}: {} {:.4f} -> {}.{} [{}]".format(
                fcf.Name,
                fcf.ToleranceType,
                fcf.ToleranceValue,
                fcf.ControlledObject.Name
                    if fcf.ControlledObject else "<none>",
                fcf.ControlledSubelement,
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
