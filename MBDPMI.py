# MBDPMI.py

import json
import uuid


def _add_property_if_missing(obj, prop_type, name, group, description):
    if hasattr(obj, name):
        return

    obj.addProperty(
        prop_type,
        name,
        group,
        description
    )


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
