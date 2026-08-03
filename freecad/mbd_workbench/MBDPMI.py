# MBDPMI.py

import json
import uuid


def _add_property_if_missing(obj, prop_type, name, group, description):
    if hasattr(obj, name):
        return False

    obj.addProperty(
        prop_type,
        name,
        group,
        description
    )
    return True


def ensure_global_link_property(obj, name, group, description):
    if not hasattr(obj, name):
        obj.addProperty(
            "App::PropertyLinkGlobal",
            name,
            group,
            description
        )
        return True

    try:
        property_type = obj.getTypeIdOfProperty(name)
    except Exception:
        return False

    if property_type == "App::PropertyLinkGlobal":
        return False

    if property_type != "App::PropertyLink":
        return False

    linked_object = getattr(obj, name, None)

    try:
        property_group = obj.getGroupOfProperty(name) or group
    except Exception:
        property_group = group

    try:
        property_description = obj.getDocumentationOfProperty(name) or description
    except Exception:
        property_description = description

    obj.removeProperty(name)
    obj.addProperty(
        "App::PropertyLinkGlobal",
        name,
        property_group,
        property_description
    )
    setattr(obj, name, linked_object)
    return True


def strip_quantity_unit_suffix(text):
    """Return a displayed quantity without the trailing unit designator."""
    parts = str(text).replace("\xa0", " ").strip().split()

    if len(parts) < 2:
        return str(text).strip()

    unit = parts[-1]

    if any(char.isalpha() or char in "°µ" for char in unit):
        return " ".join(parts[:-1])

    return str(text).strip()


def format_length_for_annotation(value):
    """Format a model-space length for ASME-style annotation display."""
    import FreeCAD

    return strip_quantity_unit_suffix(
        FreeCAD.Units.Quantity(value, FreeCAD.Units.Length).UserString
    )


def ensure_pmi_display_layout(obj):
    created_version = _add_property_if_missing(
        obj,
        "App::PropertyInteger",
        "DisplayLayoutVersion",
        "MBD_Display",
        "Version of the stored semantic PMI display layout"
    )
    _add_property_if_missing(
        obj,
        "App::PropertyVector",
        "AnnotationOrigin",
        "MBD_Display",
        "Nominal annotation origin in model coordinates"
    )
    _add_property_if_missing(
        obj,
        "App::PropertyVector",
        "AnnotationNormal",
        "MBD_Display",
        "Normal of the annotation plane"
    )
    _add_property_if_missing(
        obj,
        "App::PropertyVector",
        "AnnotationDirection",
        "MBD_Display",
        "Primary reading direction in the annotation plane"
    )
    _add_property_if_missing(
        obj,
        "App::PropertyFloat",
        "AnnotationTextHeight",
        "MBD_Display",
        "Nominal model-space annotation text height"
    )
    created_mode = _add_property_if_missing(
        obj,
        "App::PropertyString",
        "DisplayLayoutMode",
        "MBD_Display",
        "Automatic or manually adjusted display layout"
    )
    _add_property_if_missing(
        obj,
        "App::PropertyBool",
        "DisplayLayoutLocked",
        "MBD_Display",
        "Prevent automatic display regeneration from replacing stored layout"
    )

    if created_version or obj.DisplayLayoutVersion <= 0:
        obj.DisplayLayoutVersion = 1

    if created_mode or not obj.DisplayLayoutMode:
        obj.DisplayLayoutMode = "Automatic"


def update_pmi_display_layout(
    obj,
    origin=None,
    normal=None,
    direction=None,
    text_height=None,
    mode="Automatic",
    force=False
):
    ensure_pmi_display_layout(obj)

    if obj.DisplayLayoutLocked and not force:
        return False

    if origin is not None:
        obj.AnnotationOrigin = origin

    if normal is not None:
        obj.AnnotationNormal = normal

    if direction is not None:
        obj.AnnotationDirection = direction

    if text_height is not None:
        obj.AnnotationTextHeight = float(text_height)

    obj.DisplayLayoutMode = str(mode)
    return True


def ensure_pmi_identity(obj, event="created"):
    _add_property_if_missing(
        obj,
        "App::PropertyString",
        "PMIId",
        "MBD",
        "Persistent semantic PMI identifier"
    )
    _add_property_if_missing(
        obj,
        "App::PropertyString",
        "PMIHistory",
        "MBD",
        "JSON history for semantic PMI identity and attachment changes"
    )

    created_id = False

    if not obj.PMIId:
        obj.PMIId = "pmi-" + str(uuid.uuid4())
        created_id = True

    if created_id or not obj.PMIHistory:
        append_pmi_history(obj, event)

    ensure_pmi_display_layout(obj)


def ensure_pmi_import_metadata(obj):
    _add_property_if_missing(
        obj,
        "App::PropertyString",
        "AP242SourceFile",
        "MBD_Import",
        "AP242 STEP file used to create this PMI object"
    )
    _add_property_if_missing(
        obj,
        "App::PropertyString",
        "AP242SourceId",
        "MBD_Import",
        "Source AP242 STEP entity id for this PMI object"
    )
    _add_property_if_missing(
        obj,
        "App::PropertyString",
        "AP242SourceType",
        "MBD_Import",
        "Source AP242 STEP entity type for this PMI object"
    )
    _add_property_if_missing(
        obj,
        "App::PropertyString",
        "AP242ImportStatus",
        "MBD_Import",
        "Native import status for this PMI object"
    )


def set_pmi_import_metadata(
    obj,
    source_file="",
    source_id="",
    source_type="",
    import_status="Native"
):
    ensure_pmi_import_metadata(obj)
    obj.AP242SourceFile = str(source_file or "")
    obj.AP242SourceId = str(source_id or "")
    obj.AP242SourceType = str(source_type or "")
    obj.AP242ImportStatus = str(import_status or "")


def append_pmi_history(obj, event):
    if not hasattr(obj, "PMIHistory"):
        return

    try:
        history = json.loads(obj.PMIHistory) if obj.PMIHistory else []
    except Exception:
        history = []

    entry = {
        "event": event,
        "name": obj.Name,
    }

    if hasattr(obj, "ReferencedObject") and obj.ReferencedObject:
        entry["referenced_object"] = obj.ReferencedObject.Name

    if hasattr(obj, "ReferencedSubelement"):
        entry["referenced_subelement"] = obj.ReferencedSubelement

    if hasattr(obj, "ControlledObject") and obj.ControlledObject:
        entry["controlled_object"] = obj.ControlledObject.Name

    if hasattr(obj, "ControlledSubelement"):
        entry["controlled_subelement"] = obj.ControlledSubelement

    history.append(entry)
    obj.PMIHistory = json.dumps(history, sort_keys=True)


def pmi_id(obj):
    if hasattr(obj, "PMIId") and obj.PMIId:
        return obj.PMIId

    return ""
