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

def validate_document(doc):
    datum_objects = [obj for obj in doc.Objects if is_mbd_datum(obj)]

    if not datum_objects:
        return "No MBD datum features found."

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

    if total_errors:
        lines.append("Errors:")
        for err in total_errors:
            lines.append("- " + err)
    else:
        lines.append("No validation errors found.")

    return "\n".join(lines)

