# MBDDatumTarget.py

import json

import FreeCAD
import Part

from MBDPMI import ensure_pmi_identity


def add_property_if_missing(obj, prop_type, name, group, description):
    if hasattr(obj, name):
        return

    obj.addProperty(
        prop_type,
        name,
        group,
        description
    )


class MBDDatumTarget:

    def __init__(self, obj):
        obj.Proxy = self

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "TargetId",
            "MBD_Target",
            "Datum target identifier such as A1"
        )

        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "TargetType",
            "MBD_Target",
            "Datum target type"
        )
        obj.TargetType = ["Point"]

        add_property_if_missing(
            obj,
            "App::PropertyLink",
            "ParentDatum",
            "MBD_Target",
            "Semantic datum feature established by this target"
        )

        add_property_if_missing(
            obj,
            "App::PropertyLink",
            "ConstructionObject",
            "MBD_Target",
            "FreeCAD construction object defining the nominal target"
        )

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "ConstructionSubelement",
            "MBD_Target",
            "Optional selected subelement of the construction object"
        )

        add_property_if_missing(
            obj,
            "App::PropertyLink",
            "ReferencedObject",
            "MBD",
            "Object containing the inspected datum surface"
        )

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "ReferencedSubelement",
            "MBD",
            "Inspected surface subelement inherited from the parent datum"
        )

        add_property_if_missing(
            obj,
            "App::PropertyVector",
            "TargetPoint",
            "MBD_Target",
            "Resolved nominal target point"
        )

        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "SurfaceDistance",
            "MBD_Target",
            "Distance from target point to inspected datum surface"
        )

        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "SurfaceTolerance",
            "MBD_Target",
            "Allowed distance from target point to inspected datum surface"
        )
        obj.SurfaceTolerance = 0.001

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "GeometrySignature",
            "MBD",
            "Stored signature of target attachment"
        )

        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "GeometrySignatureValid",
            "MBD",
            "Whether current target attachment matches stored signature"
        )
        obj.GeometrySignatureValid = True

        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "IsSemanticPMI",
            "MBD",
            "Semantic PMI marker"
        )
        obj.IsSemanticPMI = True

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "Standard",
            "MBD",
            "GD&T standard"
        )
        obj.Standard = "ASME Y14.5"

        ensure_pmi_identity(obj, "datum-target-created")

    def execute(self, obj):
        pass


class ViewProviderMBDDatumTarget:

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return ""

    def attach(self, vobj):
        pass

    def updateData(self, obj, prop):
        pass

    def onChanged(self, vobj, prop):
        pass

    def getDisplayModes(self, obj):
        return []

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def setDisplayMode(self, mode):
        return mode


def get_point_from_target(obj):
    construction = obj.ConstructionObject

    if construction is None:
        return None

    subelement = obj.ConstructionSubelement

    if subelement:
        try:
            target = construction.Shape.getElement(subelement)

            if hasattr(target, "Point"):
                return target.Point

            if hasattr(target, "CenterOfMass"):
                return target.CenterOfMass
        except Exception:
            pass

    try:
        if hasattr(construction, "Placement"):
            return construction.Placement.Base
    except Exception:
        pass

    try:
        if len(construction.Shape.Vertexes) > 0:
            return construction.Shape.Vertexes[0].Point
    except Exception:
        pass

    return None


def target_surface_distance(obj):
    point = get_point_from_target(obj)

    if point is None:
        return None

    if obj.ReferencedObject is None or not obj.ReferencedSubelement:
        return None

    try:
        surface = obj.ReferencedObject.Shape.getElement(obj.ReferencedSubelement)
        vertex = Part.Vertex(point)
        return vertex.distToShape(surface)[0]
    except Exception:
        return None


def update_datum_target_signature(obj):
    point = get_point_from_target(obj)

    if point is None:
        obj.GeometrySignatureValid = False
        return

    obj.TargetPoint = point
    distance = target_surface_distance(obj)

    if distance is not None:
        obj.SurfaceDistance = distance

    signature = {
        "TargetId": obj.TargetId,
        "TargetType": obj.TargetType,
        "ConstructionObjectName": (
            obj.ConstructionObject.Name
            if obj.ConstructionObject
            else ""
        ),
        "ConstructionSubelement": obj.ConstructionSubelement,
        "ReferencedObjectName": (
            obj.ReferencedObject.Name
            if obj.ReferencedObject
            else ""
        ),
        "ReferencedSubelement": obj.ReferencedSubelement,
        "TargetPoint": [
            round(point.x, 6),
            round(point.y, 6),
            round(point.z, 6),
        ],
    }

    if distance is not None:
        signature["SurfaceDistance"] = round(distance, 6)

    obj.GeometrySignature = json.dumps(signature, sort_keys=True)
    obj.GeometrySignatureValid = True
