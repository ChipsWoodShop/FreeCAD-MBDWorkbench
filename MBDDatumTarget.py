# MBDDatumTarget.py

import json

import FreeCAD
import Part

from MBDPMI import ensure_global_link_property, ensure_pmi_identity
from MBDViewProvider import ViewProviderSingleItemDatumTarget


DATUM_TARGET_TYPES = ["Point", "Line"]


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
        current_target_type = (
            str(obj.TargetType)
            if hasattr(obj, "TargetType") and str(obj.TargetType)
            else "Point"
        )
        obj.TargetType = DATUM_TARGET_TYPES

        if current_target_type in DATUM_TARGET_TYPES:
            obj.TargetType = current_target_type

        add_property_if_missing(
            obj,
            "App::PropertyLink",
            "ParentDatum",
            "MBD_Target",
            "Semantic datum feature established by this target"
        )

        ensure_global_link_property(
            obj,
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

        ensure_global_link_property(
            obj,
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
            "App::PropertyString",
            "GeometryType",
            "MBD_Target",
            "Resolved datum target geometry type"
        )

        add_property_if_missing(
            obj,
            "App::PropertyVector",
            "TargetEndPoint1",
            "MBD_Target",
            "Resolved first endpoint for a line datum target"
        )

        add_property_if_missing(
            obj,
            "App::PropertyVector",
            "TargetEndPoint2",
            "MBD_Target",
            "Resolved second endpoint for a line datum target"
        )

        add_property_if_missing(
            obj,
            "App::PropertyVector",
            "TargetDirection",
            "MBD_Target",
            "Resolved direction for a line datum target"
        )

        add_property_if_missing(
            obj,
            "App::PropertyLength",
            "TargetLength",
            "MBD_Target",
            "Resolved length for a line datum target"
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
            "App::PropertyLink",
            "DisplayText",
            "MBD_Target",
            "Optional visible datum target label text helper"
        )

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


class ViewProviderMBDDatumTarget(ViewProviderSingleItemDatumTarget):
    pass


def _selected_construction_shape(obj):
    construction = obj.ConstructionObject

    if construction is None or not hasattr(construction, "Shape"):
        return None

    subelement = obj.ConstructionSubelement

    if subelement:
        try:
            return construction.Shape.getElement(subelement)
        except Exception:
            return None

    return construction.Shape


def _point_line_distance(point, start, direction):
    offset = point - start
    projected = direction * offset.dot(direction)
    return (offset - projected).Length


def straight_edge_geometry(edge):
    if edge is None or getattr(edge, "ShapeType", "") != "Edge":
        return None

    try:
        start = edge.valueAt(edge.FirstParameter)
        end = edge.valueAt(edge.LastParameter)
    except Exception:
        return None

    chord = end - start
    length = chord.Length

    if length <= 1e-9:
        return None

    direction = FreeCAD.Vector(chord)
    direction.normalize()
    tolerance = max(1e-6, length * 1e-6)

    try:
        for fraction in (0.25, 0.5, 0.75):
            parameter = (
                edge.FirstParameter
                + (edge.LastParameter - edge.FirstParameter) * fraction
            )
            point = edge.valueAt(parameter)

            if _point_line_distance(point, start, direction) > tolerance:
                return None
    except Exception:
        return None

    return {
        "type": "Line",
        "point": (start + end) * 0.5,
        "start": start,
        "end": end,
        "direction": direction,
        "length": length,
    }


def line_geometry_from_target(obj):
    shape = _selected_construction_shape(obj)

    if shape is None:
        return None

    if getattr(shape, "ShapeType", "") == "Edge":
        return straight_edge_geometry(shape)

    try:
        if len(shape.Edges) == 1:
            return straight_edge_geometry(shape.Edges[0])
    except Exception:
        pass

    return None


def get_point_from_target(obj):
    if str(obj.TargetType) == "Line":
        line = line_geometry_from_target(obj)
        return line["point"] if line else None

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
        if len(construction.Shape.Vertexes) > 0:
            return construction.Shape.Vertexes[0].Point
    except Exception:
        pass

    try:
        if hasattr(construction, "Placement"):
            return construction.Placement.Base
    except Exception:
        pass

    return None


def target_sample_points(obj):
    if str(obj.TargetType) == "Line":
        line = line_geometry_from_target(obj)

        if line is None:
            return []

        start = line["start"]
        end = line["end"]
        return [
            start,
            start + (end - start) * 0.25,
            line["point"],
            start + (end - start) * 0.75,
            end,
        ]

    point = get_point_from_target(obj)
    return [point] if point is not None else []


def target_surface_distance(obj):
    points = target_sample_points(obj)

    if not points:
        return None

    if obj.ReferencedObject is None or not obj.ReferencedSubelement:
        return None

    try:
        surface = obj.ReferencedObject.Shape.getElement(obj.ReferencedSubelement)
        return max(
            Part.Vertex(point).distToShape(surface)[0]
            for point in points
        )
    except Exception:
        return None


def update_datum_target_signature(obj):
    point = get_point_from_target(obj)

    if point is None:
        obj.GeometrySignatureValid = False
        return

    obj.TargetPoint = point
    obj.GeometryType = str(obj.TargetType)
    line = None

    if str(obj.TargetType) == "Line":
        line = line_geometry_from_target(obj)

        if line is None:
            obj.GeometrySignatureValid = False
            return

        obj.TargetEndPoint1 = line["start"]
        obj.TargetEndPoint2 = line["end"]
        obj.TargetDirection = line["direction"]
        obj.TargetLength = line["length"]

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

    if line is not None:
        signature["TargetEndPoint1"] = [
            round(line["start"].x, 6),
            round(line["start"].y, 6),
            round(line["start"].z, 6),
        ]
        signature["TargetEndPoint2"] = [
            round(line["end"].x, 6),
            round(line["end"].y, 6),
            round(line["end"].z, 6),
        ]
        signature["TargetDirection"] = [
            round(line["direction"].x, 6),
            round(line["direction"].y, 6),
            round(line["direction"].z, 6),
        ]
        signature["TargetLength"] = round(line["length"], 6)

    if distance is not None:
        signature["SurfaceDistance"] = round(distance, 6)

    obj.GeometrySignature = json.dumps(signature, sort_keys=True)
    obj.GeometrySignatureValid = True
