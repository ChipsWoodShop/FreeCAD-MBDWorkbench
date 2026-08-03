# MBDBasicDimension.py

import json

import FreeCAD
import Part

from .MBDPMI import ensure_pmi_identity
from .MBDViewProvider import ViewProviderSingleItemDimension


def add_property_if_missing(obj, prop_type, name, group, description):
    if hasattr(obj, name):
        return

    obj.addProperty(
        prop_type,
        name,
        group,
        description
    )


class MBDBasicDimension:

    def __init__(self, obj):
        obj.Proxy = self

        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "DimensionType",
            "MBD_BasicDimension",
            "Basic dimension measurement type"
        )
        obj.DimensionType = ["Distance", "X", "Y", "Z"]

        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "NominalValue",
            "MBD_BasicDimension",
            "Nominal basic dimension value"
        )

        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "MeasuredValue",
            "MBD_BasicDimension",
            "Current measured value between references"
        )

        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "ValidationTolerance",
            "MBD_BasicDimension",
            "Allowed difference between nominal and measured value"
        )
        obj.ValidationTolerance = 0.001

        add_property_if_missing(
            obj,
            "App::PropertyLink",
            "ReferenceObject1",
            "MBD_BasicDimension",
            "First reference object"
        )

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "ReferenceSubelement1",
            "MBD_BasicDimension",
            "First reference subelement"
        )

        add_property_if_missing(
            obj,
            "App::PropertyLink",
            "ReferenceObject2",
            "MBD_BasicDimension",
            "Second reference object"
        )

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "ReferenceSubelement2",
            "MBD_BasicDimension",
            "Second reference subelement"
        )

        add_property_if_missing(
            obj,
            "App::PropertyLink",
            "DisplayDimension",
            "MBD_BasicDimension",
            "Optional visible dimension line helper"
        )

        add_property_if_missing(
            obj,
            "App::PropertyLink",
            "DisplayText",
            "MBD_BasicDimension",
            "Optional visible dimension text helper"
        )

        add_property_if_missing(
            obj,
            "App::PropertyLink",
            "DisplayTextBox",
            "MBD_BasicDimension",
            "Optional visible box around basic dimension text"
        )

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "GeometrySignature",
            "MBD",
            "Stored signature of basic dimension references"
        )

        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "GeometrySignatureValid",
            "MBD",
            "Whether current basic dimension references match stored signature"
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

        ensure_pmi_identity(obj, "basic-dimension-created")

    def execute(self, obj):
        pass


class ViewProviderMBDBasicDimension(ViewProviderSingleItemDimension):
    pass


def point_from_reference(obj, subelement=""):
    if obj is None:
        return None

    if subelement:
        try:
            target = obj.Shape.getElement(subelement)

            if hasattr(target, "Point"):
                return target.Point

            if hasattr(target, "CenterOfMass"):
                return target.CenterOfMass
        except Exception:
            pass

    try:
        if hasattr(obj, "TargetPoint"):
            return obj.TargetPoint
    except Exception:
        pass

    try:
        if len(obj.Shape.Vertexes) > 0:
            return obj.Shape.Vertexes[0].Point
    except Exception:
        pass

    try:
        if hasattr(obj, "Shape") and hasattr(obj.Shape, "CenterOfMass"):
            return obj.Shape.CenterOfMass
    except Exception:
        pass

    try:
        if hasattr(obj, "Placement"):
            return obj.Placement.Base
    except Exception:
        pass

    return None


def is_datum_feature(obj):
    return (
        obj is not None
        and hasattr(obj, "DatumLabel")
        and hasattr(obj, "ReferencedObject")
        and hasattr(obj, "ReferencedSubelement")
    )


def surface_from_datum_reference(obj):
    if not is_datum_feature(obj):
        return None

    if obj.ReferencedObject is None or not obj.ReferencedSubelement:
        return None

    try:
        return obj.ReferencedObject.Shape.getElement(obj.ReferencedSubelement)
    except Exception:
        return None


def closest_point_on_surface(surface_shape, point):
    try:
        surface = surface_shape.Surface
        u, v = surface.parameter(point)

        try:
            u_min, u_max, v_min, v_max = surface_shape.ParameterRange
            u = max(u_min, min(u, u_max))
            v = max(v_min, min(v, v_max))
        except Exception:
            pass

        return surface.value(u, v)
    except Exception:
        return None


def projected_point_on_surface_normal_plane(surface_shape, point):
    if surface_shape is None or point is None:
        return None

    try:
        u_min, u_max, v_min, v_max = surface_shape.ParameterRange
        normal = surface_shape.normalAt(
            (u_min + u_max) * 0.5,
            (v_min + v_max) * 0.5
        )
    except Exception:
        return None

    if normal.Length == 0:
        return None

    normal.normalize()

    try:
        datum_point = surface_shape.CenterOfMass
    except Exception:
        try:
            datum_point = surface_shape.Surface.Position
        except Exception:
            return None

    offset = point - datum_point
    return point - (normal * offset.dot(normal))


def closest_point_on_datum_surface(datum_obj, point):
    surface = surface_from_datum_reference(datum_obj)

    if surface is None or point is None:
        return None

    projected_point = projected_point_on_surface_normal_plane(surface, point)

    if projected_point is not None:
        return projected_point

    return closest_point_on_surface(surface, point)


def datum_to_point_distance(datum_obj, point_obj, point_subelement=""):
    surface = surface_from_datum_reference(datum_obj)
    point = point_from_reference(point_obj, point_subelement)

    if surface is None or point is None:
        return None

    try:
        return Part.Vertex(point).distToShape(surface)[0]
    except Exception:
        return None


def display_points_from_references(
    ref_obj_1,
    ref_sub_1,
    ref_obj_2,
    ref_sub_2
):
    if is_datum_feature(ref_obj_1):
        point = point_from_reference(ref_obj_2, ref_sub_2)
        surface_point = closest_point_on_datum_surface(ref_obj_1, point)

        if surface_point is not None and point is not None:
            return surface_point, point

    if is_datum_feature(ref_obj_2):
        point = point_from_reference(ref_obj_1, ref_sub_1)
        surface_point = closest_point_on_datum_surface(ref_obj_2, point)

        if surface_point is not None and point is not None:
            return point, surface_point

    p1 = point_from_reference(ref_obj_1, ref_sub_1)
    p2 = point_from_reference(ref_obj_2, ref_sub_2)

    if p1 is None or p2 is None:
        return None, None

    return p1, p2


def measured_dimension_value(dimension_type, p1, p2):
    delta = p2 - p1
    dim_type = str(dimension_type)

    if dim_type == "X":
        return abs(delta.x)

    if dim_type == "Y":
        return abs(delta.y)

    if dim_type == "Z":
        return abs(delta.z)

    return delta.Length


def measured_value_from_references(
    dimension_type,
    ref_obj_1,
    ref_sub_1,
    ref_obj_2,
    ref_sub_2
):
    if is_datum_feature(ref_obj_1):
        value = datum_to_point_distance(ref_obj_1, ref_obj_2, ref_sub_2)

        if value is not None:
            return value

    if is_datum_feature(ref_obj_2):
        value = datum_to_point_distance(ref_obj_2, ref_obj_1, ref_sub_1)

        if value is not None:
            return value

    p1 = point_from_reference(ref_obj_1, ref_sub_1)
    p2 = point_from_reference(ref_obj_2, ref_sub_2)

    if p1 is None or p2 is None:
        return None

    return measured_dimension_value(dimension_type, p1, p2)


def reference_point_for_display(obj, subelement=""):
    point = point_from_reference(obj, subelement)

    if point is not None:
        return point

    surface = surface_from_datum_reference(obj)

    if surface is not None:
        try:
            return surface.CenterOfMass
        except Exception:
            pass

    return None


def update_basic_dimension_signature(obj):
    p1, p2 = display_points_from_references(
        obj.ReferenceObject1,
        obj.ReferenceSubelement1,
        obj.ReferenceObject2,
        obj.ReferenceSubelement2
    )

    measured = measured_value_from_references(
        obj.DimensionType,
        obj.ReferenceObject1,
        obj.ReferenceSubelement1,
        obj.ReferenceObject2,
        obj.ReferenceSubelement2
    )

    if measured is None:
        obj.GeometrySignatureValid = False
        return

    obj.MeasuredValue = measured

    signature = {
        "DimensionType": str(obj.DimensionType),
        "NominalValue": round(obj.NominalValue, 6),
        "MeasuredValue": round(obj.MeasuredValue, 6),
        "ReferenceObject1": obj.ReferenceObject1.Name if obj.ReferenceObject1 else "",
        "ReferenceSubelement1": obj.ReferenceSubelement1,
        "ReferenceObject2": obj.ReferenceObject2.Name if obj.ReferenceObject2 else "",
        "ReferenceSubelement2": obj.ReferenceSubelement2,
    }

    if p1 is not None:
        signature["Point1"] = [round(p1.x, 6), round(p1.y, 6), round(p1.z, 6)]

    if p2 is not None:
        signature["Point2"] = [round(p2.x, 6), round(p2.y, 6), round(p2.z, 6)]

    obj.GeometrySignature = json.dumps(signature, sort_keys=True)
    obj.GeometrySignatureValid = True
