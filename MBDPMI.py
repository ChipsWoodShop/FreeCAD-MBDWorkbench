# MBDPMI.py

import json
import uuid


GLOBAL_GEOMETRY_LINK_PROPERTIES = {
    "ReferencedObject",
    "ControlledObject",
    "ConstructionObject",
    "ReferenceObject1",
    "ReferenceObject2",
}


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


def migrate_semantic_pmi_global_links(doc):
    migrated = []

    if doc is None:
        return migrated

    for obj in doc.Objects:
        if not getattr(obj, "IsSemanticPMI", False):
            continue

        for name in GLOBAL_GEOMETRY_LINK_PROPERTIES:
            if not hasattr(obj, name):
                continue

            try:
                group = obj.getGroupOfProperty(name)
            except Exception:
                group = "MBD"

            try:
                description = obj.getDocumentationOfProperty(name)
            except Exception:
                description = "Referenced model geometry"

            if ensure_global_link_property(
                obj,
                name,
                group or "MBD",
                description or "Referenced model geometry"
            ):
                migrated.append("{}.{}".format(obj.Name, name))

    return migrated


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
