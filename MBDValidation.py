# MBDValidation.py

import FreeCAD


def is_mbd_datum(obj):
    return (
        hasattr(obj, "IsSemanticPMI")
        and hasattr(obj, "DatumLabel")
        and hasattr(obj, "ReferencedObject")
        and hasattr(obj, "ReferencedSubelement")
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

def is_mbd_fcf(obj):

    return (
        hasattr(obj, "ToleranceType")
        and hasattr(obj, "ToleranceValue")
        and hasattr(obj, "ControlledObject")
    )

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
    if total_errors:
        lines.append("Errors:")
        for err in total_errors:
            lines.append("- " + err)
    else:
        lines.append("No validation errors found.")

    return "\n".join(lines)

