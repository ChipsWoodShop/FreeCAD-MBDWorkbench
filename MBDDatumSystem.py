# MBDDatumSystem.py

import FreeCAD

from MBDPMI import ensure_pmi_identity


DATUM_COMPARTMENT_PROPERTIES = (
    ("PrimaryDatums", "Primary"),
    ("SecondaryDatums", "Secondary"),
    ("TertiaryDatums", "Tertiary"),
)


def datum_system_compartments(obj):
    compartments = []

    if obj is None:
        return compartments

    for prop_name, role_name in DATUM_COMPARTMENT_PROPERTIES:
        datums = list(getattr(obj, prop_name, []) or [])
        compartments.append((role_name, datums))

    return compartments


def datum_compartment_label(datums):
    return "-".join(
        str(datum.DatumLabel)
        for datum in datums
        if datum is not None and hasattr(datum, "DatumLabel")
    )


def datum_system_label(obj):
    labels = [
        datum_compartment_label(datums)
        for _role_name, datums in datum_system_compartments(obj)
    ]
    return " | ".join(label for label in labels if label)


def datum_system_object_label(obj):
    compartments = [
        datum_compartment_label(datums)
        for _role_name, datums in datum_system_compartments(obj)
    ]
    suffix = "_".join(label for label in compartments if label)

    if not suffix:
        return "MBD_DatumSystem"

    return "MBD_DatumSystem_" + suffix


def synchronize_datum_system_label(obj):
    if not is_datum_system_object(obj):
        return False

    expected = datum_system_object_label(obj)

    if obj.Label == expected:
        return False

    obj.Label = expected
    return True


def datum_system_datums(obj):
    datums = []

    for _role_name, compartment_datums in datum_system_compartments(obj):
        datums.extend(compartment_datums)

    return datums


def is_datum_system_object(obj):
    return (
        obj is not None
        and hasattr(obj, "PrimaryDatums")
        and hasattr(obj, "SecondaryDatums")
        and hasattr(obj, "TertiaryDatums")
        and getattr(obj, "IsSemanticPMI", False)
    )


class MBDDatumSystem:

    def __init__(self, obj):

        obj.Proxy = self

        for old_prop in ("PrimaryDatum", "SecondaryDatum", "TertiaryDatum"):
            if hasattr(obj, old_prop):
                obj.removeProperty(old_prop)

        for prop_name, role_name in DATUM_COMPARTMENT_PROPERTIES:
            if not hasattr(obj, prop_name):
                obj.addProperty(
                    "App::PropertyLinkList",
                    prop_name,
                    "MBDDatumSystem",
                    "{} datum-reference compartment".format(role_name)
                )

        if not hasattr(obj, "Standard"):
            obj.addProperty(
                "App::PropertyString",
                "Standard",
                "MBDDatumSystem",
                "GD&T standard"
            )

        obj.Standard = "ASME Y14.5"

        if not hasattr(obj, "IsSemanticPMI"):
            obj.addProperty(
                "App::PropertyBool",
                "IsSemanticPMI",
                "MBDDatumSystem",
                "Semantic PMI marker"
            )

        obj.IsSemanticPMI = True
        ensure_pmi_identity(obj, "datum-system-created")

    def execute(self, obj):
        pass


class ViewProviderMBDDatumSystem:

    def __init__(self, vobj):
        vobj.Proxy = self
