# MBDDatum.py

import FreeCAD
import json

from MBDPMI import (
    ensure_global_link_property,
    ensure_pmi_display_layout,
    ensure_pmi_identity,
)
from MBDViewProvider import ViewProviderSingleItemDatumFeature

class MBDDatumFeature:
    """
    Semantic datum feature object.

    This is not merely construction geometry.
    It represents an MBD datum feature attached to model geometry.
    """

    def __init__(self, obj):
        obj.Proxy = self

        obj.addProperty(
            "App::PropertyString",
            "DatumLabel",
            "MBD",
            "Datum label, such as A, B, or C"
        )
        obj.DatumLabel = "A"

        ensure_global_link_property(
            obj,
            "ReferencedObject",
            "MBD",
            "FreeCAD object containing the referenced geometry"
        )

        obj.addProperty(
            "App::PropertyString",
            "ReferencedSubelement",
            "MBD",
            "Referenced subelement name, such as Face3, Edge2, or Vertex1"
        )

        obj.addProperty(
            "App::PropertyEnumeration",
            "DatumType",
            "MBD",
            "Type of semantic datum feature"
        )
        obj.DatumType = ["Plane", "Axis", "Point", "Feature"]

        obj.addProperty(
            "App::PropertyString",
            "Standard",
            "MBD",
            "GD&T standard basis"
        )
        obj.Standard = "ASME Y14.5"

        obj.addProperty(
            "App::PropertyBool",
            "IsSemanticPMI",
            "MBD",
            "Marks this object as semantic PMI"
        )
        obj.IsSemanticPMI = True

        obj.addProperty(
            "App::PropertyLink",
            "DisplayText",
            "MBD",
            "Optional visible datum label text helper"
        )

        obj.addProperty(
            "App::PropertyLink",
            "DisplayFrame",
            "MBD",
            "Optional visible datum label frame helper"
        )

        obj.addProperty(
            "App::PropertyLink",
            "DisplayMarker",
            "MBD",
            "Optional visible datum triangle marker helper"
        )

        obj.addProperty(
            "App::PropertyLink",
            "DisplayLeader",
            "MBD",
            "Optional visible datum leader helper"
        )
        
        obj.addProperty(
            "App::PropertyVector",
            "CenterOfMass",
            "GeometrySignature",
            "Center of mass of referenced geometry"
        )

        obj.addProperty(
            "App::PropertyFloat",
            "Area",
            "GeometrySignature",
            "Area of referenced face"
        )

        obj.addProperty(
            "App::PropertyFloat",
            "FacePerimeter",
            "GeometrySignature",
            "Perimeter of referenced face"
        )

        obj.addProperty(
            "App::PropertyFloat",
            "EdgeLength",
            "GeometrySignature",
            "Length of referenced edge"
        )

        obj.addProperty(
            "App::PropertyString",
            "GeometryType",
            "GeometrySignature",
            "Underlying geometry type"
        )
        obj.addProperty(
            "App::PropertyString",
            "GeometrySignature",
            "MBD",
            "Stored geometric signature of referenced feature"
        )

        obj.addProperty(
            "App::PropertyBool",
            "GeometrySignatureValid",
            "MBD",
            "Whether current referenced geometry matches stored signature"
        )
        obj.GeometrySignatureValid = True
        ensure_pmi_display_layout(obj)
        ensure_pmi_identity(obj, "datum-created")
    def execute(self, obj):
        pass


class ViewProviderMBDDatumFeature(ViewProviderSingleItemDatumFeature):
    pass

def update_geometry_signature(obj):

    if not obj.ReferencedObject:
        return

    shape = obj.ReferencedObject.Shape
    sub = obj.ReferencedSubelement

    target = None

    try:
        target = shape.getElement(sub)
    except Exception:
        target = None

    if target is None:
        return

    signature = {
        "ReferencedObjectName": obj.ReferencedObject.Name,
        "ReferencedSubelement": sub,
        "GeometryType": "Unknown",
    }

    try:
        obj.CenterOfMass = target.CenterOfMass
        signature["CenterOfMass"] = [
            round(target.CenterOfMass.x, 6),
            round(target.CenterOfMass.y, 6),
            round(target.CenterOfMass.z, 6),
        ]
    except Exception:
        pass

    try:
        obj.Area = target.Area
        signature["Area"] = round(target.Area, 6)
    except Exception:
        pass

    try:
        if sub.startswith("Face"):
            obj.FacePerimeter = target.Length
            signature["FacePerimeter"] = round(target.Length, 6)
        elif sub.startswith("Edge"):
            obj.EdgeLength = target.Length
            signature["EdgeLength"] = round(target.Length, 6)
    except Exception:
        pass

    try:
        surf = target.Surface
        obj.GeometryType = surf.__class__.__name__
        signature["GeometryType"] = obj.GeometryType
    except Exception:
        try:
            curve = target.Curve
            obj.GeometryType = curve.__class__.__name__
            signature["GeometryType"] = obj.GeometryType
        except Exception:
            obj.GeometryType = "Unknown"
            signature["GeometryType"] = "Unknown"

    try:
        obj.GeometrySignature = json.dumps(signature, sort_keys=True)
        obj.GeometrySignatureValid = True
    except Exception:
        obj.GeometrySignatureValid = False
