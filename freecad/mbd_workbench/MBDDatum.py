# MBDDatum.py

import FreeCAD
import json

from .MBDPMI import (
    ensure_global_link_property,
    ensure_pmi_display_layout,
    ensure_pmi_identity,
)
from .MBDViewProvider import ViewProviderSingleItemDatumFeature

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
            "App::PropertyStringList",
            "ReferencedSubelementList",
            "MBD",
            "All referenced subelements for imported multi-face datum features"
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

def geometry_signature_for_subelement(ref_obj, sub):
    if ref_obj is None or not sub:
        return None

    try:
        target = ref_obj.Shape.getElement(sub)
    except Exception:
        return None

    signature = {
        "ReferencedObjectName": ref_obj.Name,
        "ReferencedSubelement": sub,
        "GeometryType": "Unknown",
    }

    try:
        signature["CenterOfMass"] = [
            round(target.CenterOfMass.x, 6),
            round(target.CenterOfMass.y, 6),
            round(target.CenterOfMass.z, 6),
        ]
    except Exception:
        pass

    try:
        signature["Area"] = round(target.Area, 6)
    except Exception:
        pass

    try:
        if sub.startswith("Face"):
            signature["FacePerimeter"] = round(target.Length, 6)
        elif sub.startswith("Edge"):
            signature["EdgeLength"] = round(target.Length, 6)
    except Exception:
        pass

    try:
        signature["GeometryType"] = target.Surface.__class__.__name__
    except Exception:
        try:
            signature["GeometryType"] = target.Curve.__class__.__name__
        except Exception:
            pass

    return signature


def update_geometry_signature(obj):

    if not obj.ReferencedObject:
        return

    sub = obj.ReferencedSubelement
    signature = geometry_signature_for_subelement(obj.ReferencedObject, sub)

    if signature is None:
        return

    try:
        target = obj.ReferencedObject.Shape.getElement(sub)
    except Exception:
        target = None

    try:
        if target is not None:
            obj.CenterOfMass = target.CenterOfMass
    except Exception:
        pass

    try:
        if target is not None:
            obj.Area = target.Area
    except Exception:
        pass

    try:
        if target is not None:
            if sub.startswith("Face"):
                obj.FacePerimeter = target.Length
            elif sub.startswith("Edge"):
                obj.EdgeLength = target.Length
    except Exception:
        pass

    try:
        obj.GeometryType = signature["GeometryType"]
    except Exception:
        pass

    referenced_subelements = [
        str(item)
        for item in getattr(obj, "ReferencedSubelementList", [])
        if str(item)
    ]

    if sub and sub not in referenced_subelements:
        referenced_subelements.insert(0, sub)

    if len(referenced_subelements) > 1:
        signatures = []

        for referenced_sub in referenced_subelements:
            sub_signature = geometry_signature_for_subelement(
                obj.ReferencedObject,
                referenced_sub
            )

            if sub_signature is not None:
                signatures.append(sub_signature)

        if signatures:
            signature["ReferencedSubelements"] = signatures

    try:
        obj.GeometrySignature = json.dumps(signature, sort_keys=True)
        obj.GeometrySignatureValid = True
    except Exception:
        obj.GeometrySignatureValid = False
