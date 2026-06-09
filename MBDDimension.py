# MBDDimension.py

import json

import FreeCAD
import Part

import MBDBasicDimension
from MBDPMI import ensure_global_link_property, ensure_pmi_identity


DIMENSION_PURPOSES = [
    "Basic",
    "Reference",
    "EqualBilateral",
    "UnequalBilateral",
    "Limits",
]

DIMENSION_PURPOSE_CHOICES = [
    "Basic",
    "Reference",
    "EqualBilateral",
    "UnequalBilateral",
    "Limits",
]

DIMENSION_KINDS = [
    "Linear",
    "Angular",
    "Diameter",
    "Radius",
]

MEASUREMENT_TYPES = [
    "Distance",
    "X",
    "Y",
    "Z",
]

LINEAR_DIMENSION_KINDS = [
    "Linear",
    "Diameter",
    "Radius",
]


def add_property_if_missing(obj, prop_type, name, group, description):
    if hasattr(obj, name):
        return

    obj.addProperty(
        prop_type,
        name,
        group,
        description
    )


class MBDDimension:

    def __init__(self, obj):
        obj.Proxy = self

        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "DimensionPurpose",
            "MBD_Dimension",
            "Semantic dimension purpose"
        )
        obj.DimensionPurpose = DIMENSION_PURPOSES

        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "DimensionKind",
            "MBD_Dimension",
            "Semantic dimension kind"
        )
        obj.DimensionKind = DIMENSION_KINDS

        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "MeasurementType",
            "MBD_Dimension",
            "Linear measurement direction"
        )
        obj.MeasurementType = MEASUREMENT_TYPES

        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "NominalValue",
            "MBD_Dimension",
            "Nominal dimension value"
        )

        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "MeasuredValue",
            "MBD_Dimension",
            "Current measured value between references"
        )

        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "UpperTolerance",
            "MBD_Dimension",
            "Upper plus/minus tolerance"
        )

        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "LowerTolerance",
            "MBD_Dimension",
            "Lower plus/minus tolerance"
        )

        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "UpperLimit",
            "MBD_Dimension",
            "Upper limit dimension value"
        )

        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "LowerLimit",
            "MBD_Dimension",
            "Lower limit dimension value"
        )

        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "ValidationTolerance",
            "MBD_Dimension",
            "Allowed difference between nominal and measured value"
        )
        obj.ValidationTolerance = 0.001

        ensure_global_link_property(
            obj,
            "ReferenceObject1",
            "MBD_Dimension",
            "First reference object"
        )

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "ReferenceSubelement1",
            "MBD_Dimension",
            "First reference subelement"
        )

        ensure_global_link_property(
            obj,
            "ReferenceObject2",
            "MBD_Dimension",
            "Second reference object"
        )

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "ReferenceSubelement2",
            "MBD_Dimension",
            "Second reference subelement"
        )

        add_property_if_missing(
            obj,
            "App::PropertyLink",
            "DisplayDimension",
            "MBD_Dimension",
            "Optional visible dimension line helper"
        )

        add_property_if_missing(
            obj,
            "App::PropertyLink",
            "DisplayText",
            "MBD_Dimension",
            "Optional visible dimension text helper"
        )

        add_property_if_missing(
            obj,
            "App::PropertyLink",
            "DisplayTextBox",
            "MBD_Dimension",
            "Optional visible box around basic dimension text"
        )

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "ReferencePattern",
            "MBD_Dimension",
            "Resolved dimension reference pattern"
        )

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "ValidationMessage",
            "MBD_Dimension",
            "Last dimension reference validation message"
        )

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "AP242Entity",
            "MBD_Dimension",
            "Intended AP242 semantic dimension entity"
        )
        obj.AP242Entity = "DIMENSIONAL_LOCATION"

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "GeometrySignature",
            "MBD",
            "Stored signature of dimension references"
        )

        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "GeometrySignatureValid",
            "MBD",
            "Whether current dimension references match stored signature"
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

        ensure_pmi_identity(obj, "dimension-created")

    def execute(self, obj):
        pass


class ViewProviderMBDDimension:

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


def measured_value_from_references(obj):
    if str(obj.DimensionKind) not in LINEAR_DIMENSION_KINDS:
        return None

    result = measurement_from_references(
        obj.DimensionKind,
        obj.MeasurementType,
        obj.ReferenceObject1,
        obj.ReferenceSubelement1,
        obj.ReferenceObject2,
        obj.ReferenceSubelement2
    )

    obj.ReferencePattern = result.get("pattern", "")
    obj.ValidationMessage = result.get("message", "")

    return result.get("value")


def display_points_from_references(obj):
    result = measurement_from_references(
        obj.DimensionKind,
        obj.MeasurementType,
        obj.ReferenceObject1,
        obj.ReferenceSubelement1,
        obj.ReferenceObject2,
        obj.ReferenceSubelement2
    )

    return result.get("point1"), result.get("point2")


def empty_measurement(message):
    return {
        "value": None,
        "point1": None,
        "point2": None,
        "pattern": "",
        "message": message,
    }


def good_measurement(value, point1, point2, pattern):
    return {
        "value": value,
        "point1": point1,
        "point2": point2,
        "pattern": pattern,
        "message": "",
    }


def shape_element(obj, subelement=""):
    if obj is None:
        return None

    if subelement:
        try:
            return obj.Shape.getElement(subelement)
        except Exception:
            return None

    if MBDBasicDimension.is_datum_feature(obj):
        return MBDBasicDimension.surface_from_datum_reference(obj)

    try:
        return obj.Shape
    except Exception:
        return None


def nearest_point_on_shape(obj, point):
    if obj is None or point is None:
        return None

    try:
        shape = obj.Shape

        if shape.isNull():
            return None

        distance, point_pairs, _support = Part.Vertex(
            FreeCAD.Vector(point)
        ).distToShape(shape)

        if distance < 0 or not point_pairs:
            return None

        return FreeCAD.Vector(point_pairs[0][1])
    except Exception:
        return None


def vector_is_parallel(v1, v2, tolerance=1e-6):
    if v1 is None or v2 is None:
        return False

    if v1.Length == 0 or v2.Length == 0:
        return False

    a = FreeCAD.Vector(v1)
    b = FreeCAD.Vector(v2)
    a.normalize()
    b.normalize()
    return a.cross(b).Length <= tolerance


def vector_is_perpendicular(v1, v2, tolerance=1e-6):
    if v1 is None or v2 is None:
        return False

    if v1.Length == 0 or v2.Length == 0:
        return False

    a = FreeCAD.Vector(v1)
    b = FreeCAD.Vector(v2)
    a.normalize()
    b.normalize()
    return abs(a.dot(b)) <= tolerance


def planar_face_reference(obj, subelement=""):
    shape = shape_element(obj, subelement)

    if shape is None or not hasattr(shape, "Surface"):
        return None

    try:
        surface_name = shape.Surface.__class__.__name__.lower()
    except Exception:
        surface_name = ""

    if "plane" not in surface_name:
        return None

    try:
        point = shape.CenterOfMass
    except Exception:
        try:
            point = shape.Surface.Position
        except Exception:
            return None

    try:
        u_min, u_max, v_min, v_max = shape.ParameterRange
        normal = shape.normalAt(
            (u_min + u_max) * 0.5,
            (v_min + v_max) * 0.5
        )
    except Exception:
        try:
            normal = shape.Surface.Axis
        except Exception:
            return None

    if normal.Length == 0:
        return None

    normal.normalize()

    return {
        "shape": shape,
        "point": point,
        "normal": normal,
    }


def point_reference(obj, subelement=""):
    return MBDBasicDimension.point_from_reference(obj, subelement)


def edge_reference(obj, subelement=""):
    shape = shape_element(obj, subelement)

    if shape is None:
        return None

    try:
        if getattr(shape, "ShapeType", "") == "Edge":
            edge = shape
        elif hasattr(shape, "Edges") and len(shape.Edges) == 1:
            edge = shape.Edges[0]
        else:
            return None
    except Exception:
        return None

    try:
        vertexes = edge.Vertexes

        if len(vertexes) < 2:
            return None

        p1 = vertexes[0].Point
        p2 = vertexes[-1].Point
        direction = p2 - p1

        if direction.Length == 0:
            return None

        direction.normalize()
        midpoint = p1 + ((p2 - p1) * 0.5)

        return {
            "shape": edge,
            "point": midpoint,
            "direction": direction,
        }
    except Exception:
        return None


def cylindrical_face_reference(obj, subelement=""):
    shape = shape_element(obj, subelement)

    if shape is None or not hasattr(shape, "Surface"):
        return None

    try:
        surface_name = shape.Surface.__class__.__name__.lower()
    except Exception:
        surface_name = ""

    if "cylinder" not in surface_name:
        return None

    try:
        axis = FreeCAD.Vector(shape.Surface.Axis)
        point = FreeCAD.Vector(shape.Surface.Center)
        radius = float(shape.Surface.Radius)
    except Exception:
        try:
            axis = FreeCAD.Vector(shape.Surface.Axis)
            point = FreeCAD.Vector(shape.Surface.Position)
            radius = float(shape.Surface.Radius)
        except Exception:
            return None

    if axis.Length == 0 or radius <= 0:
        return None

    axis.normalize()

    try:
        center = shape.CenterOfMass
    except Exception:
        center = point

    axis_point = point + axis * ((center - point).dot(axis))
    axis_point = cylinder_display_axis_point(obj, shape, axis, axis_point)
    opening_direction = cylinder_opening_direction(shape, axis, point, axis_point)

    return {
        "shape": shape,
        "point": axis_point,
        "direction": axis,
        "opening_direction": opening_direction,
        "radius": radius,
    }


def bound_box_corners(bbox):
    return [
        FreeCAD.Vector(x, y, z)
        for x in [bbox.XMin, bbox.XMax]
        for y in [bbox.YMin, bbox.YMax]
        for z in [bbox.ZMin, bbox.ZMax]
    ]


def cylinder_display_axis_point(obj, shape, axis, default_point):
    opening_choice = cylinder_opening_by_solid_probe(obj, shape, axis, default_point)

    if opening_choice is not None:
        return opening_choice

    exit_choice = cylinder_exit_axis_point(obj, shape, axis, default_point)

    if exit_choice is not None:
        return exit_choice

    edge_choice = cylinder_opening_axis_point(obj, shape, axis, default_point)

    if edge_choice is not None:
        return edge_choice

    candidates = []

    try:
        for vertex in shape.Vertexes:
            candidates.append(vertex.Point)
    except Exception:
        pass

    if len(candidates) < 2:
        try:
            candidates.extend(bound_box_corners(shape.BoundBox))
        except Exception:
            pass

    if not candidates:
        return default_point

    projections = [
        (point - default_point).dot(axis)
        for point in candidates
    ]

    min_projection = min(projections)
    max_projection = max(projections)
    end1 = default_point + axis * min_projection
    end2 = default_point + axis * max_projection

    try:
        model_center = obj.Shape.CenterOfMass
    except Exception:
        return end2

    if (end1 - model_center).Length > (end2 - model_center).Length:
        return end1

    return end2


def cylinder_opening_direction(shape, axis, default_point, opening_point):
    ends = cylinder_axis_ends(shape, axis, default_point)

    if ends is None:
        return None

    end1, end2 = ends

    if (opening_point - end1).Length <= (opening_point - end2).Length:
        direction = end1 - end2
    else:
        direction = end2 - end1

    if direction.Length == 0:
        return None

    direction.normalize()
    return direction


def cylinder_opening_by_solid_probe(obj, shape, axis, default_point):
    ends = cylinder_axis_ends(shape, axis, default_point)

    if ends is None:
        return None

    end1, end2 = ends
    hit1 = distance_to_enter_solid(obj, end1, axis.negative())
    hit2 = distance_to_enter_solid(obj, end2, axis)

    if hit1 is None and hit2 is None:
        return None

    if hit1 is None:
        return end1

    if hit2 is None:
        return end2

    if abs(hit1 - hit2) <= max(hit1, hit2) * 0.05:
        return None

    if hit1 > hit2:
        return end1

    return end2


def distance_to_enter_solid(obj, start_point, direction):
    if direction is None or direction.Length == 0:
        return None

    try:
        solid_shape = obj.Shape
        bbox = solid_shape.BoundBox
    except Exception:
        return None

    step = max(
        min(max(bbox.XLength, bbox.YLength, bbox.ZLength) * 0.01, 1.0),
        0.025
    )
    max_distance = max(bbox.XLength, bbox.YLength, bbox.ZLength) * 2.0 + step

    probe_direction = FreeCAD.Vector(direction)
    probe_direction.normalize()
    distance = step

    while distance <= max_distance:
        point = start_point + probe_direction * distance

        if point_inside_shape(solid_shape, point):
            return distance

        distance += step

    return None


def cylinder_exit_axis_point(obj, shape, axis, default_point):
    ends = cylinder_axis_ends(shape, axis, default_point)

    if ends is None:
        return None

    end1, end2 = ends
    distance1 = distance_to_exit_solid(obj, end1, axis.negative(), shape)
    distance2 = distance_to_exit_solid(obj, end2, axis, shape)

    if distance1 is None and distance2 is None:
        return None

    if distance1 is None:
        return end2

    if distance2 is None:
        return end1

    if distance1 <= distance2:
        return end1

    return end2


def cylinder_axis_ends(shape, axis, default_point):
    candidates = []

    try:
        for vertex in shape.Vertexes:
            candidates.append(vertex.Point)
    except Exception:
        pass

    if len(candidates) < 2:
        try:
            candidates.extend(bound_box_corners(shape.BoundBox))
        except Exception:
            pass

    if not candidates:
        return None

    projections = [
        (point - default_point).dot(axis)
        for point in candidates
    ]

    return (
        default_point + axis * min(projections),
        default_point + axis * max(projections),
    )


def distance_to_exit_solid(obj, start_point, direction, cylinder_shape):
    if direction is None or direction.Length == 0:
        return None

    try:
        solid_shape = obj.Shape
        bbox = solid_shape.BoundBox
    except Exception:
        return None

    step = max(
        min(max(bbox.XLength, bbox.YLength, bbox.ZLength) * 0.02, 2.0),
        0.05
    )
    max_distance = max(bbox.XLength, bbox.YLength, bbox.ZLength) * 2.0 + step

    probe_direction = FreeCAD.Vector(direction)
    probe_direction.normalize()

    # Start slightly away from the exact cylindrical boundary. Boundary
    # classification is unstable; the first samples intentionally skip the
    # selected cylinder wall itself and ask about the owning solid volume.
    distance = step

    while distance <= max_distance:
        point = start_point + probe_direction * distance

        if not point_inside_shape(solid_shape, point):
            return distance

        distance += step

    return None


def point_inside_shape(shape, point):
    try:
        return shape.isInside(point, 1e-5, True)
    except Exception:
        try:
            distance = FreeCAD.Vector(point)
            return shape.distToShape(Part.Vertex(distance))[0] <= 1e-5
        except Exception:
            return False


def cylinder_opening_axis_point(obj, cylinder_face, axis, default_point):
    end_edges = cylinder_end_edges(cylinder_face, axis, default_point)

    if len(end_edges) < 2:
        return None

    scored = []

    for edge_data in end_edges:
        area = adjacent_non_cylindrical_face_area(obj, cylinder_face, edge_data["edge"])
        scored.append((area, edge_data))

    scored = [item for item in scored if item[0] is not None]

    if len(scored) < 2:
        return None

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]["point"]


def cylinder_end_edges(cylinder_face, axis, default_point):
    edge_data = []

    try:
        edges = list(cylinder_face.Edges)
    except Exception:
        return edge_data

    for edge in edges:
        try:
            point = edge.CenterOfMass
        except Exception:
            continue

        projection = (point - default_point).dot(axis)
        edge_data.append({
            "edge": edge,
            "point": default_point + axis * projection,
            "projection": projection,
        })

    if len(edge_data) <= 2:
        return edge_data

    edge_data.sort(key=lambda item: item["projection"])
    return [edge_data[0], edge_data[-1]]


def adjacent_non_cylindrical_face_area(obj, cylinder_face, edge):
    best_area = None

    try:
        faces = list(obj.Shape.Faces)
    except Exception:
        return None

    for face in faces:
        if same_shape(face, cylinder_face):
            continue

        try:
            surface_name = face.Surface.__class__.__name__.lower()
        except Exception:
            surface_name = ""

        if "cylinder" in surface_name:
            continue

        if not face_contains_edge(face, edge):
            continue

        try:
            area = float(face.Area)
        except Exception:
            continue

        if best_area is None or area > best_area:
            best_area = area

    return best_area


def same_shape(shape1, shape2):
    try:
        return shape1.isSame(shape2)
    except Exception:
        return False


def face_contains_edge(face, target_edge, tolerance=1e-5):
    try:
        target_length = float(target_edge.Length)
    except Exception:
        target_length = None

    try:
        edges = list(face.Edges)
    except Exception:
        return False

    for edge in edges:
        try:
            distance = edge.distToShape(target_edge)[0]
        except Exception:
            continue

        if distance > tolerance:
            continue

        if target_length is not None:
            try:
                if abs(float(edge.Length) - target_length) > tolerance:
                    continue
            except Exception:
                pass

        return True

    return False


def line_reference(obj, subelement=""):
    cylinder = cylindrical_face_reference(obj, subelement)

    if cylinder is not None:
        return cylinder

    edge = edge_reference(obj, subelement)

    if edge is not None:
        return edge

    return None


def signed_distance_to_plane(point, plane):
    return (point - plane["point"]).dot(plane["normal"])


def plane_projection_point(point, plane):
    signed = signed_distance_to_plane(point, plane)
    return point - (plane["normal"] * signed)


def plane_to_plane_measurement(plane1, plane2):
    if not vector_is_parallel(plane1["normal"], plane2["normal"]):
        return empty_measurement(
            "Selected planar faces are not parallel. Use an angular dimension, or select a plane and a vertex or parallel edge for a directed linear dimension."
        )

    signed = signed_distance_to_plane(plane2["point"], plane1)
    normal = FreeCAD.Vector(plane1["normal"])

    if signed < 0:
        normal = normal.negative()

    p1 = plane1["point"]
    p2 = p1 + (normal * abs(signed))
    return good_measurement(abs(signed), p1, p2, "PlaneToPlane")


def plane_to_point_measurement(plane, point):
    signed = signed_distance_to_plane(point, plane)
    projected = point - (plane["normal"] * signed)
    return good_measurement(abs(signed), projected, point, "PlaneToPoint")


def plane_to_edge_measurement(plane, edge):
    if not vector_is_perpendicular(plane["normal"], edge["direction"]):
        return empty_measurement(
            "Selected edge is not parallel to the selected planar face."
        )

    signed = signed_distance_to_plane(edge["point"], plane)
    projected = edge["point"] - (plane["normal"] * signed)
    return good_measurement(abs(signed), projected, edge["point"], "PlaneToEdge")


def point_to_point_measurement(measurement_type, point1, point2):
    value = MBDBasicDimension.measured_dimension_value(
        measurement_type,
        point1,
        point2
    )
    return good_measurement(value, point1, point2, "PointToPoint")


def cylinder_size_measurement(dimension_kind, cylinder):
    if dimension_kind == "Diameter":
        value = cylinder["radius"] * 2.0
        pattern = "CylinderDiameter"
    else:
        value = cylinder["radius"]
        pattern = "CylinderRadius"

    axis = cylinder["direction"]
    axis_point = cylinder["point"]
    helper = None

    try:
        center_of_mass = cylinder["shape"].CenterOfMass
        radial = center_of_mass - axis_point
        radial = radial - axis * radial.dot(axis)

        if radial.Length > cylinder["radius"] * 0.1:
            radial.normalize()
            helper = radial
    except Exception:
        helper = None

    if helper is None:
        helper = axis.cross(FreeCAD.Vector(0, 0, 1))

    if helper.Length == 0:
        helper = axis.cross(FreeCAD.Vector(0, 1, 0))

    if helper.Length == 0:
        return empty_measurement("Could not resolve a radius direction.")

    helper.normalize()
    p1 = axis_point - helper * cylinder["radius"]
    p2 = axis_point + helper * cylinder["radius"]

    if dimension_kind == "Radius":
        p1 = axis_point
        p2 = axis_point + helper * cylinder["radius"]

    result = good_measurement(value, p1, p2, pattern)
    result["text_normal"] = axis

    return result


def axis_to_plane_measurement(axis, plane):
    if not vector_is_perpendicular(axis["direction"], plane["normal"]):
        return empty_measurement(
            "Selected axis is not parallel to the selected planar face."
        )

    signed = signed_distance_to_plane(axis["point"], plane)
    projected = axis["point"] - (plane["normal"] * signed)
    result = good_measurement(abs(signed), projected, axis["point"], "AxisToPlane")
    result["display_direction"] = axis.get("opening_direction")
    return result


def axis_to_point_measurement(axis, point):
    delta = point - axis["point"]
    along_axis = axis["direction"] * delta.dot(axis["direction"])
    axis_point = axis["point"] + along_axis
    result = good_measurement((point - axis_point).Length, axis_point, point, "AxisToPoint")
    result["display_direction"] = axis.get("opening_direction")
    return result


def axis_to_axis_measurement(axis1, axis2):
    p1 = axis1["point"]
    p2 = axis2["point"]
    d1 = FreeCAD.Vector(axis1["direction"])
    d2 = FreeCAD.Vector(axis2["direction"])

    d1.normalize()
    d2.normalize()
    normal = d1.cross(d2)
    delta = p2 - p1

    if normal.Length <= 1e-6:
        offset = delta - d1 * delta.dot(d1)
        closest1 = p1 + d1 * delta.dot(d1)
        closest2 = p2
        pattern = "AxisToAxisCoincident" if offset.Length <= 1e-6 else "AxisToAxisParallel"
        return good_measurement(offset.Length, closest1, closest2, pattern)

    normal.normalize()
    distance = abs(delta.dot(normal))

    a = d1.dot(d1)
    b = d1.dot(d2)
    c = d2.dot(d2)
    d = d1.dot(p1 - p2)
    e = d2.dot(p1 - p2)
    denominator = (a * c) - (b * b)

    if abs(denominator) <= 1e-12:
        return empty_measurement("Could not resolve axis-to-axis distance.")

    s = ((b * e) - (c * d)) / denominator
    t = ((a * e) - (b * d)) / denominator
    closest1 = p1 + d1 * s
    closest2 = p2 + d2 * t
    pattern = "AxisToAxisIntersecting" if distance <= 1e-6 else "AxisToAxisSkew"
    return good_measurement(distance, closest1, closest2, pattern)


def measurement_from_references(
    dimension_kind,
    measurement_type,
    ref_obj_1,
    ref_sub_1,
    ref_obj_2,
    ref_sub_2
):
    dimension_kind = str(dimension_kind)

    cylinder1 = cylindrical_face_reference(ref_obj_1, ref_sub_1)
    cylinder2 = cylindrical_face_reference(ref_obj_2, ref_sub_2)

    if dimension_kind in ("Diameter", "Radius"):
        if cylinder1 is None:
            return empty_measurement(
                "{} dimensions require a cylindrical face reference.".format(
                    dimension_kind
                )
            )

        return cylinder_size_measurement(dimension_kind, cylinder1)

    plane1 = planar_face_reference(ref_obj_1, ref_sub_1)
    plane2 = planar_face_reference(ref_obj_2, ref_sub_2)

    axis1 = line_reference(ref_obj_1, ref_sub_1)
    axis2 = line_reference(ref_obj_2, ref_sub_2)

    if axis1 is not None and axis2 is not None:
        return axis_to_axis_measurement(axis1, axis2)

    if axis1 is not None and plane2 is not None:
        result = axis_to_plane_measurement(axis1, plane2)

        if result["value"] is None:
            return result

        flipped = good_measurement(
            result["value"],
            result["point2"],
            result["point1"],
            "AxisToPlane"
        )
        flipped["display_direction"] = result.get("display_direction")
        return flipped

    if plane1 is not None and axis2 is not None:
        return axis_to_plane_measurement(axis2, plane1)

    if plane1 is not None and plane2 is not None:
        return plane_to_plane_measurement(plane1, plane2)

    edge1 = edge_reference(ref_obj_1, ref_sub_1)
    edge2 = edge_reference(ref_obj_2, ref_sub_2)

    if plane1 is not None and edge2 is not None:
        return plane_to_edge_measurement(plane1, edge2)

    if plane2 is not None and edge1 is not None:
        result = plane_to_edge_measurement(plane2, edge1)

        if result["value"] is None:
            return result

        return good_measurement(
            result["value"],
            result["point2"],
            result["point1"],
            "EdgeToPlane"
        )

    point1 = point_reference(ref_obj_1, ref_sub_1)
    point2 = point_reference(ref_obj_2, ref_sub_2)

    if axis1 is not None and point2 is not None:
        return axis_to_point_measurement(axis1, point2)

    if axis2 is not None and point1 is not None:
        result = axis_to_point_measurement(axis2, point1)
        flipped = good_measurement(
            result["value"],
            result["point2"],
            result["point1"],
            "PointToAxis"
        )
        flipped["display_direction"] = result.get("display_direction")
        return flipped

    if plane1 is not None and point2 is not None:
        return plane_to_point_measurement(plane1, point2)

    if plane2 is not None and point1 is not None:
        result = plane_to_point_measurement(plane2, point1)
        return good_measurement(
            result["value"],
            result["point2"],
            result["point1"],
            "PointToPlane"
        )

    if point1 is not None and point2 is not None:
        return point_to_point_measurement(measurement_type, point1, point2)

    return empty_measurement(
        "References must resolve to compatible plane, axis, cylinder, edge, or point geometry."
    )


def update_dimension_signature(obj):
    measured = measured_value_from_references(obj)

    if measured is None:
        obj.GeometrySignatureValid = False
        return

    obj.MeasuredValue = measured
    p1, p2 = display_points_from_references(obj)

    signature = {
        "DimensionPurpose": str(obj.DimensionPurpose),
        "DimensionKind": str(obj.DimensionKind),
        "MeasurementType": str(obj.MeasurementType),
        "ReferencePattern": str(obj.ReferencePattern),
        "NominalValue": round(obj.NominalValue, 6),
        "MeasuredValue": round(obj.MeasuredValue, 6),
        "UpperTolerance": round(obj.UpperTolerance, 6),
        "LowerTolerance": round(obj.LowerTolerance, 6),
        "UpperLimit": round(obj.UpperLimit, 6),
        "LowerLimit": round(obj.LowerLimit, 6),
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


def dimension_display_label(obj):
    purpose = str(obj.DimensionPurpose)
    prefix = ""

    if str(getattr(obj, "DimensionKind", "")) == "Radius":
        prefix = "R "

    if purpose == "Reference":
        return "({}{})".format(
            prefix,
            FreeCAD.Units.Quantity(
                obj.NominalValue,
                FreeCAD.Units.Length
            ).UserString
        )

    if purpose == "UnequalBilateral":
        nominal = FreeCAD.Units.Quantity(
            obj.NominalValue,
            FreeCAD.Units.Length
        ).UserString
        upper = FreeCAD.Units.Quantity(
            obj.UpperTolerance,
            FreeCAD.Units.Length
        ).UserString
        lower = FreeCAD.Units.Quantity(
            abs(obj.LowerTolerance),
            FreeCAD.Units.Length
        ).UserString
        return "{}{} +{} -{}".format(prefix, nominal, upper, lower)

    if purpose == "EqualBilateral":
        nominal = FreeCAD.Units.Quantity(
            obj.NominalValue,
            FreeCAD.Units.Length
        ).UserString
        tolerance = FreeCAD.Units.Quantity(
            obj.UpperTolerance,
            FreeCAD.Units.Length
        ).UserString
        return "{}{} +/- {}".format(prefix, nominal, tolerance)

    if purpose == "Limits":
        lower = FreeCAD.Units.Quantity(
            obj.LowerLimit,
            FreeCAD.Units.Length
        ).UserString
        upper = FreeCAD.Units.Quantity(
            obj.UpperLimit,
            FreeCAD.Units.Length
        ).UserString
        return "{}{} / {}{}".format(prefix, lower, prefix, upper)

    return prefix + FreeCAD.Units.Quantity(
        obj.NominalValue,
        FreeCAD.Units.Length
    ).UserString
