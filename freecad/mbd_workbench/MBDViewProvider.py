import math
import time

import FreeCAD
import FreeCADGui
import Part
from pivy import coin
from PySide import QtCore, QtGui

from .MBDDatumSystem import datum_compartment_label, datum_system_compartments
from .MBDPMI import ensure_pmi_display_layout, format_length_for_annotation


TEXT_WIDTH_FACTOR = 0.62
ANNOTATION_DISPLAY_MODE = "MBD Annotation"


def _normalized(vector, fallback):
    result = FreeCAD.Vector(vector)

    if result.Length <= 1e-9:
        result = FreeCAD.Vector(fallback)

    result.normalize()
    return result


def annotation_basis(obj):
    normal = _normalized(
        getattr(obj, "AnnotationNormal", FreeCAD.Vector(0, 0, 1)),
        FreeCAD.Vector(0, 0, 1)
    )
    direction = _normalized(
        getattr(obj, "AnnotationDirection", FreeCAD.Vector(1, 0, 0)),
        FreeCAD.Vector(1, 0, 0)
    )
    direction = direction - normal * direction.dot(normal)

    if direction.Length <= 1e-9:
        direction = normal.cross(FreeCAD.Vector(0, 0, 1))

    if direction.Length <= 1e-9:
        direction = normal.cross(FreeCAD.Vector(0, 1, 0))

    direction.normalize()
    up = normal.cross(direction)
    up.normalize()
    return direction, up, normal


def local_point(origin, x_axis, y_axis, x, y, z=0.0):
    return origin + x_axis * x + y_axis * y + FreeCAD.Vector(0, 0, z)


def add_line_geometry(parent, segments):
    coordinates = []

    for start, end in segments:
        coordinates.extend([
            (start.x, start.y, start.z),
            (end.x, end.y, end.z),
        ])

    coordinate_node = coin.SoCoordinate3()
    coordinate_node.point.setValues(0, len(coordinates), coordinates)
    line_node = coin.SoLineSet()
    line_node.numVertices.setValues(0, len(segments), [2] * len(segments))
    parent.addChild(coordinate_node)
    parent.addChild(line_node)


def arc_points(cx, cy, rx, ry, start_degrees, end_degrees, segments=24):
    return [
        (
            cx + rx * math.cos(math.radians(
                start_degrees
                + (end_degrees - start_degrees) * index / segments
            )),
            cy + ry * math.sin(math.radians(
                start_degrees
                + (end_degrees - start_degrees) * index / segments
            )),
        )
        for index in range(segments + 1)
    ]


def symbol_segments(symbol_name):
    segments = []

    def line(x1, y1, x2, y2):
        segments.append(((x1, y1), (x2, y2)))

    def poly(points):
        for start, end in zip(points, points[1:]):
            segments.append((start, end))

    def arc(cx, cy, rx, ry, start, end):
        poly(arc_points(cx, cy, rx, ry, start, end))

    def circle(cx, cy, radius):
        points = arc_points(cx, cy, radius, radius, 0, 360, 40)
        points.append(points[0])
        poly(points)

    def arrow(x1, y1, x2, y2):
        line(x1, y1, x2, y2)
        direction = FreeCAD.Vector(x2 - x1, y2 - y1, 0)

        if direction.Length <= 1e-9:
            return

        direction.normalize()
        side = FreeCAD.Vector(-direction.y, direction.x, 0)
        tip = FreeCAD.Vector(x2, y2, 0)
        base = tip - direction * 0.16
        left = base + side * 0.06
        right = base - side * 0.06
        line(tip.x, tip.y, left.x, left.y)
        line(tip.x, tip.y, right.x, right.y)

    if symbol_name == "Straightness":
        line(0.15, 0.50, 0.85, 0.50)
    elif symbol_name == "Flatness":
        poly([(0.18, 0.38), (0.82, 0.38), (0.70, 0.62),
              (0.06, 0.62), (0.18, 0.38)])
    elif symbol_name == "Circularity":
        circle(0.50, 0.50, 0.28)
    elif symbol_name == "Cylindricity":
        circle(0.50, 0.50, 0.18)
        line(0.18, 0.18, 0.46, 0.82)
        line(0.54, 0.18, 0.82, 0.82)
    elif symbol_name == "Profile of a Line":
        arc(0.50, 0.28, 0.35, 0.35, 25, 155)
    elif symbol_name == "Profile of a Surface":
        arc(0.50, 0.35, 0.35, 0.30, 20, 160)
        line(0.18, 0.35, 0.82, 0.35)
    elif symbol_name == "Angularity":
        line(0.18, 0.25, 0.82, 0.25)
        line(0.28, 0.25, 0.70, 0.75)
    elif symbol_name == "Perpendicularity":
        line(0.18, 0.25, 0.82, 0.25)
        line(0.50, 0.25, 0.50, 0.78)
    elif symbol_name == "Parallelism":
        line(0.28, 0.22, 0.50, 0.78)
        line(0.50, 0.22, 0.72, 0.78)
    elif symbol_name == "Position":
        circle(0.50, 0.50, 0.26)
        line(0.18, 0.50, 0.82, 0.50)
        line(0.50, 0.18, 0.50, 0.82)
    elif symbol_name == "Circular Runout":
        arrow(0.22, 0.28, 0.78, 0.72)
    elif symbol_name == "Total Runout":
        line(0.22, 0.28, 0.42, 0.28)
        arrow(0.22, 0.28, 0.58, 0.72)
        arrow(0.42, 0.28, 0.78, 0.72)
    elif symbol_name == "Diameter":
        circle(0.50, 0.50, 0.26)
        line(0.28, 0.22, 0.72, 0.78)
    elif symbol_name == "Modifier M":
        circle(0.50, 0.50, 0.34)
        line(0.28, 0.28, 0.28, 0.72)
        line(0.28, 0.72, 0.50, 0.42)
        line(0.50, 0.42, 0.72, 0.72)
        line(0.72, 0.72, 0.72, 0.28)
    elif symbol_name == "Modifier L":
        circle(0.50, 0.50, 0.34)
        line(0.34, 0.72, 0.34, 0.28)
        line(0.34, 0.28, 0.68, 0.28)
    elif symbol_name == "Modifier P":
        circle(0.50, 0.50, 0.34)
        line(0.34, 0.28, 0.34, 0.72)
        line(0.34, 0.72, 0.62, 0.72)
        line(0.62, 0.72, 0.72, 0.62)
        line(0.72, 0.62, 0.62, 0.52)
        line(0.62, 0.52, 0.34, 0.52)
    elif symbol_name == "Modifier U":
        circle(0.50, 0.50, 0.34)
        line(0.30, 0.72, 0.30, 0.38)
        arc(0.50, 0.38, 0.20, 0.16, 180, 360)
        line(0.70, 0.38, 0.70, 0.72)
    elif symbol_name == "Modifier T":
        circle(0.50, 0.50, 0.34)
        line(0.28, 0.72, 0.72, 0.72)
        line(0.50, 0.72, 0.50, 0.28)

    return segments


def fcf_symbol_name(tolerance_type):
    return {
        "Position": "Position",
        "Flatness": "Flatness",
        "Parallelism": "Parallelism",
        "Perpendicularity": "Perpendicularity",
        "LineProfile": "Profile of a Line",
        "Profile": "Profile of a Surface",
        "Angularity": "Angularity",
        "Circularity": "Circularity",
        "Cylindricity": "Cylindricity",
        "Straightness": "Straightness",
        "CircularRunout": "Circular Runout",
        "TotalRunout": "Total Runout",
    }.get(str(tolerance_type), str(tolerance_type))


def fcf_cells(obj):
    tolerance = format_length_for_annotation(obj.ToleranceValue)
    tolerance_parts = []

    if getattr(obj, "DiameterZone", False):
        tolerance_parts.append(("symbol", "Diameter"))

    tolerance_parts.append(("text", tolerance))

    material_modifier = str(
        getattr(obj, "MaterialConditionModifier", "None")
    )

    if material_modifier == "MMC":
        tolerance_parts.append(("symbol", "Modifier M"))
    elif material_modifier == "LMC":
        tolerance_parts.append(("symbol", "Modifier L"))

    if getattr(obj, "ProjectedToleranceZone", False):
        projected_height = format_length_for_annotation(
            getattr(obj, "ProjectedToleranceHeight", 0.0),
        )
        tolerance_parts.append(("symbol", "Modifier P"))
        tolerance_parts.append(("text", projected_height))

    if getattr(obj, "UnequallyDisposedZone", False):
        offset = format_length_for_annotation(
            getattr(obj, "UnequallyDisposedOffset", 0.0),
        )
        tolerance_parts.append(("symbol", "Modifier U"))
        tolerance_parts.append(("text", offset))

    if getattr(obj, "TangentPlaneModifier", False):
        tolerance_parts.append(("symbol", "Modifier T"))

    if getattr(obj, "StatisticalToleranceModifier", False):
        tolerance_parts.append(("text", "<ST>"))

    if getattr(obj, "CommonZoneModifier", False):
        tolerance_parts.append(("text", "CT"))

    if getattr(obj, "UnitBasisToleranceEnabled", False):
        unit_type = str(getattr(obj, "UnitBasisType", "Length"))
        primary = format_length_for_annotation(
            getattr(obj, "UnitBasisPrimaryLength", 0.0),
        )

        if unit_type == "Length":
            tolerance_parts.append(("text", "/ {}".format(primary)))
        elif unit_type == "Circular":
            tolerance_parts.append(("text", "/"))
            tolerance_parts.append(("symbol", "Diameter"))
            tolerance_parts.append(("text", primary))
        elif unit_type == "Square":
            tolerance_parts.append(("text", "/ {} x {}".format(
                primary,
                primary
            )))
        else:
            secondary = format_length_for_annotation(
                getattr(obj, "UnitBasisSecondaryLength", 0.0),
            )
            tolerance_parts.append(("text", "/ {} x {}".format(
                primary,
                secondary
            )))

    if getattr(obj, "NonUniformToleranceZone", False):
        tolerance_parts.append(("text", "NON-UNIFORM"))

    cells = [
        ("symbol", fcf_symbol_name(obj.ToleranceType)),
        ("tolerance", tolerance_parts),
    ]

    if getattr(obj, "MaximumToleranceValueEnabled", False):
        maximum_value = format_length_for_annotation(
            getattr(obj, "MaximumToleranceValue", 0.0),
        )
        cells.append(("text", "{} MAX".format(maximum_value)))

    if (
        str(obj.ToleranceType) == "Profile"
        and getattr(obj, "ProfileAllOver", False)
    ):
        cells.append(("text", "ALL OVER"))

    if getattr(obj, "DatumReference", None) is not None:
        datum = obj.DatumReference
        cells.append(("text", getattr(datum, "DatumLabel", datum.Label)))
    elif getattr(obj, "DatumSystem", None) is not None:
        for _role, datums in datum_system_compartments(obj.DatumSystem):
            label = datum_compartment_label(datums)

            if label:
                cells.append(("text", label))

    return cells


def fcf_attachment_point(obj):
    controlled = getattr(obj, "ControlledObject", None)
    subelement = getattr(obj, "ControlledSubelement", "")

    if controlled is None:
        return None

    if (
        str(getattr(obj, "ToleranceType", "")) == "Position"
        and subelement
    ):
        try:
            from .MBDDimension import cylindrical_face_reference

            cylinder = cylindrical_face_reference(controlled, subelement)

            if cylinder is not None:
                return cylinder["point"]
        except Exception:
            pass

    if str(getattr(obj, "ToleranceType", "")) in (
        "CircularRunout",
        "TotalRunout",
    ):
        axis_reference = revolved_surface_axis_reference(controlled, subelement)

        if axis_reference is not None:
            origin = FreeCAD.Vector(
                getattr(obj, "AnnotationOrigin", FreeCAD.Vector(0, 0, 0))
            )
            surface_point = runout_surface_attachment_point(
                axis_reference,
                origin,
                None
            )

            if surface_point is not None:
                return surface_point

    if subelement:
        try:
            target = controlled.Shape.getElement(subelement)
            return target.CenterOfMass
        except Exception:
            return None

    try:
        from .MBDDimension import nearest_point_on_shape

        bbox = controlled.Shape.BoundBox
        preferred_point = FreeCAD.Vector(
            (bbox.XMin + bbox.XMax) * 0.5,
            (bbox.YMin + bbox.YMax) * 0.5,
            bbox.ZMax
        )
        return nearest_point_on_shape(controlled, preferred_point)
    except Exception:
        return None


# Tolerance cells mix Coin text with stroke-drawn symbols. Coin text has broad
# font metrics, so these factors intentionally use the apparent visual width
# rather than TEXT_WIDTH_FACTOR; otherwise MMC/projected-zone cells develop
# large gaps between symbols and numbers.
FCF_TOLERANCE_SYMBOL_WIDTH_FACTOR = 0.62
FCF_TOLERANCE_TEXT_WIDTH_FACTOR = 0.36
FCF_TOLERANCE_PART_GAP_FACTOR = 0.05


def fcf_tolerance_part_width(part, height):
    kind, value = part

    if kind == "symbol":
        return height * FCF_TOLERANCE_SYMBOL_WIDTH_FACTOR

    width_factor = FCF_TOLERANCE_TEXT_WIDTH_FACTOR

    if len(str(value)) > 8:
        width_factor = 0.50

    return max(
        len(str(value)) * height * width_factor,
        height * 0.6
    )


def fcf_tolerance_part_gap(height):
    return height * FCF_TOLERANCE_PART_GAP_FACTOR


def fcf_tolerance_width(parts, height):
    if not parts:
        return height * 1.6

    gap = fcf_tolerance_part_gap(height)
    return sum(
        fcf_tolerance_part_width(part, height)
        for part in parts
    ) + gap * (len(parts) - 1)


def add_inline_text(parent, text, origin, x_axis, y_axis, normal, height):
    text_sep = coin.SoSeparator()
    transform = coin.SoTransform()
    transform.translation.setValue(origin.x, origin.y, origin.z)
    rotation = FreeCAD.Rotation(x_axis, y_axis, normal, "XYZ")
    quaternion = rotation.Q
    transform.rotation.setValue(
        quaternion[0],
        quaternion[1],
        quaternion[2],
        quaternion[3]
    )
    font_style = coin.SoVRMLFontStyle()
    font_style.size = height * 0.72
    font_style.justify.setValues(0, 2, ["BEGIN", "MIDDLE"])
    text_node = coin.SoVRMLText()
    text_node.string = str(text)
    text_node.fontStyle = font_style
    text_sep.addChild(transform)
    text_sep.addChild(text_node)
    parent.addChild(text_sep)


def fcf_leader_segments(obj, attachment, origin, height):
    try:
        for candidate in obj.Document.Objects:
            if not hasattr(candidate, "DimensionKind"):
                continue

            if str(candidate.DimensionKind) != "Diameter":
                continue

            for object_property, subelement_property in (
                ("ReferenceObject1", "ReferenceSubelement1"),
                ("ReferenceObject2", "ReferenceSubelement2"),
            ):
                if (
                    getattr(candidate, object_property, None)
                    == getattr(obj, "ControlledObject", None)
                    and getattr(candidate, subelement_property, "")
                    == getattr(obj, "ControlledSubelement", "")
                ):
                    if str(getattr(obj, "ToleranceType", "")) == "Position":
                        return []
    except Exception:
        pass

    leader_segments = [(attachment, origin)]

    if str(getattr(obj, "ToleranceType", "")) != "Position":
        return leader_segments

    controlled = getattr(obj, "ControlledObject", None)
    subelement = getattr(obj, "ControlledSubelement", "")

    try:
        from .MBDDimension import cylindrical_face_reference

        cylinder = cylindrical_face_reference(controlled, subelement)
        opening_direction = cylinder.get("opening_direction")

        if (
            opening_direction is None
            or opening_direction.Length <= 1e-9
        ):
            return leader_segments

        opening_direction = FreeCAD.Vector(opening_direction)
        opening_direction.normalize()
        distance = max(
            (origin - attachment).dot(opening_direction),
            height * 2.0
        )
        elbow = attachment + opening_direction * distance
        leader_segments = [(attachment, elbow)]

        if (origin - elbow).Length > 1e-9:
            leader_segments.append((elbow, origin))
    except Exception:
        pass

    return leader_segments


def revolved_surface_axis_reference(obj, subelement):
    if obj is None:
        return None

    try:
        shape = obj.Shape.getElement(subelement) if subelement else obj.Shape
    except Exception:
        return None

    if shape is None:
        return None

    candidates = []

    if hasattr(shape, "Surface"):
        candidates.append(shape)
    else:
        try:
            candidates.extend(list(shape.Faces))
        except Exception:
            pass

    for candidate in candidates:
        surface = getattr(candidate, "Surface", None)

        if surface is None:
            continue

        try:
            surface_name = surface.__class__.__name__.lower()
        except Exception:
            surface_name = ""

        if not any(
            token in surface_name
            for token in ("cylinder", "cone", "torus", "sphere")
        ):
            continue

        try:
            axis = FreeCAD.Vector(surface.Axis)
        except Exception:
            continue

        if axis.Length <= 1e-9:
            continue

        axis.normalize()
        point = None

        for attr in ("Center", "Position", "Apex"):
            try:
                point = FreeCAD.Vector(getattr(surface, attr))
                break
            except Exception:
                pass

        if point is None:
            try:
                point = FreeCAD.Vector(candidate.CenterOfMass)
            except Exception:
                point = FreeCAD.Vector(0, 0, 0)

        try:
            center = FreeCAD.Vector(candidate.CenterOfMass)
            point = point + axis * ((center - point).dot(axis))
        except Exception:
            pass

        result = {
            "shape": candidate,
            "point": point,
            "direction": axis,
        }

        try:
            result["radius"] = float(surface.Radius)
        except Exception:
            pass

        return result

    return None


def point_distance_from_axis(point, axis_point, axis_direction):
    vector = FreeCAD.Vector(point) - FreeCAD.Vector(axis_point)
    radial = vector - axis_direction * vector.dot(axis_direction)
    return radial.Length


def estimated_revolved_radius(axis_reference):
    try:
        radius = float(axis_reference.get("radius", 0.0))

        if radius > 1e-9:
            return radius
    except Exception:
        pass

    shape = axis_reference.get("shape")
    axis_point = FreeCAD.Vector(axis_reference["point"])
    axis_direction = FreeCAD.Vector(axis_reference["direction"])

    if axis_direction.Length <= 1e-9:
        return 0.0

    axis_direction.normalize()
    distances = []

    try:
        for vertex in shape.Vertexes:
            distances.append(
                point_distance_from_axis(
                    vertex.Point,
                    axis_point,
                    axis_direction
                )
            )
    except Exception:
        pass

    try:
        bbox = shape.BoundBox

        for x in (bbox.XMin, bbox.XMax):
            for y in (bbox.YMin, bbox.YMax):
                for z in (bbox.ZMin, bbox.ZMax):
                    distances.append(
                        point_distance_from_axis(
                            FreeCAD.Vector(x, y, z),
                            axis_point,
                            axis_direction
                        )
                    )
    except Exception:
        pass

    distances = [distance for distance in distances if distance > 1e-9]
    return min(distances) if distances else 0.0


def runout_surface_attachment_point(axis_reference, origin, fallback):
    """Pick a real surface-side point for runout leaders.

    Full cylindrical faces often report their center of mass on the axis. A
    leader to that point reads as if it controls the axis directly, so runout
    callouts deliberately step from the axis out to the visible surface in the
    direction of the annotation.
    """
    try:
        axis_point = FreeCAD.Vector(axis_reference["point"])
        axis_direction = FreeCAD.Vector(axis_reference["direction"])

        if axis_direction.Length <= 1e-9:
            return fallback

        axis_direction.normalize()
        origin = FreeCAD.Vector(origin)
        station = axis_point + axis_direction * (
            (origin - axis_point).dot(axis_direction)
        )
        radial = origin - station
        radial = radial - axis_direction * radial.dot(axis_direction)

        if radial.Length <= 1e-9 and fallback is not None:
            radial = FreeCAD.Vector(fallback) - axis_point
            radial = radial - axis_direction * radial.dot(axis_direction)

        if radial.Length <= 1e-9:
            radial = axis_direction.cross(FreeCAD.Vector(0, 0, 1))

        if radial.Length <= 1e-9:
            radial = axis_direction.cross(FreeCAD.Vector(0, 1, 0))

        if radial.Length <= 1e-9:
            return fallback

        radial.normalize()
        radius = estimated_revolved_radius(axis_reference)

        if radius <= 1e-9:
            return fallback

        return station + radial * radius
    except Exception:
        return fallback


def runout_surface_attachment_point_in_plane(axis_reference, origin, normal, fallback):
    """Choose the section point where the FCF plane meets the controlled surface."""
    try:
        axis_point = FreeCAD.Vector(axis_reference["point"])
        axis_direction = FreeCAD.Vector(axis_reference["direction"])
        origin = FreeCAD.Vector(origin)
        normal = FreeCAD.Vector(normal)

        if axis_direction.Length <= 1e-9 or normal.Length <= 1e-9:
            return fallback

        axis_direction.normalize()
        normal.normalize()
        station = axis_point + axis_direction * (
            (origin - axis_point).dot(axis_direction)
        )
        radial = normal.cross(axis_direction)

        if radial.Length <= 1e-9:
            return runout_surface_attachment_point(axis_reference, origin, fallback)

        radial.normalize()

        if radial.dot(origin - station) < 0.0:
            radial = radial.negative()

        radius = estimated_revolved_radius(axis_reference)

        if radius <= 1e-9:
            return fallback

        return station + radial * radius
    except Exception:
        return fallback


def datum_axis_reference(datum_obj):
    if datum_obj is None:
        return None

    referenced = getattr(datum_obj, "ReferencedObject", None)
    subelement = getattr(datum_obj, "ReferencedSubelement", "")

    if referenced is None or not subelement:
        return None

    axis_reference = revolved_surface_axis_reference(referenced, subelement)

    if axis_reference is not None:
        return axis_reference

    try:
        shape = referenced.Shape.getElement(subelement)

        if hasattr(shape, "Curve"):
            try:
                start = shape.Vertexes[0].Point
                end = shape.Vertexes[-1].Point
                direction = FreeCAD.Vector(end) - FreeCAD.Vector(start)

                if direction.Length > 1e-9:
                    direction.normalize()
                    return {
                        "shape": shape,
                        "point": FreeCAD.Vector(start),
                        "direction": direction,
                    }
            except Exception:
                pass
    except Exception:
        pass

    return None


def runout_datum_axis_reference(obj):
    datum_reference = getattr(obj, "DatumReference", None)

    if datum_reference is not None:
        axis_reference = datum_axis_reference(datum_reference)

        if axis_reference is not None:
            return axis_reference

    datum_system = getattr(obj, "DatumSystem", None)

    if datum_system is not None:
        for _role, datums in datum_system_compartments(datum_system):
            for datum in datums:
                axis_reference = datum_axis_reference(datum)

                if axis_reference is not None:
                    return axis_reference

    return None


def project_point_to_plane(point, plane_origin, plane_normal):
    point = FreeCAD.Vector(point)
    plane_origin = FreeCAD.Vector(plane_origin)
    plane_normal = FreeCAD.Vector(plane_normal)

    if plane_normal.Length <= 1e-9:
        return point

    plane_normal.normalize()
    return point - plane_normal * ((point - plane_origin).dot(plane_normal))


def line_intersection_in_plane(point_a, direction_a, point_b, direction_b, normal):
    direction_a = FreeCAD.Vector(direction_a)
    direction_b = FreeCAD.Vector(direction_b)
    normal = FreeCAD.Vector(normal)

    if (
        direction_a.Length <= 1e-9
        or direction_b.Length <= 1e-9
        or normal.Length <= 1e-9
    ):
        return None

    direction_a.normalize()
    direction_b.normalize()
    normal.normalize()
    denominator = direction_a.cross(direction_b).dot(normal)

    if abs(denominator) <= 1e-9:
        return None

    offset = FreeCAD.Vector(point_b) - FreeCAD.Vector(point_a)
    parameter = offset.cross(direction_b).dot(normal) / denominator
    return FreeCAD.Vector(point_a) + direction_a * parameter


def shape_element_from_reference(obj, subelement):
    try:
        if subelement:
            return obj.Shape.getElement(subelement)

        return obj.Shape
    except Exception:
        return None


def surface_point_near_plane_line(controlled, subelement, line_point, line_direction, length):
    shape = shape_element_from_reference(controlled, subelement)

    if shape is None:
        return None, None

    try:
        direction = FreeCAD.Vector(line_direction)

        if direction.Length <= 1e-9:
            return None, None

        direction.normalize()
        line_point = FreeCAD.Vector(line_point)
        probe = Part.makeLine(
            line_point - direction * length,
            line_point + direction * length
        )
        distance, point_pairs, _support = probe.distToShape(shape)

        if distance < 0 or not point_pairs:
            return None, None

        return FreeCAD.Vector(point_pairs[0][1]), float(distance)
    except Exception:
        return None, None


def nearest_controlled_surface_point_in_plane(controlled, subelement, origin, normal):
    shape = shape_element_from_reference(controlled, subelement)

    if shape is None:
        return None

    try:
        distance, point_pairs, _support = Part.Vertex(
            FreeCAD.Vector(origin)
        ).distToShape(shape)

        if distance < 0 or not point_pairs:
            return None

        return project_point_to_plane(point_pairs[0][1], origin, normal)
    except Exception:
        return None


def runout_display_geometry(obj, attachment, origin, height, x_axis, normal):
    """Resolve the shared datum-axis, surface leader, and arc geometry.

    Runout orientation annotations have several dependent pieces: the FCF
    leader, the controlled-surface contact point, the datum axis shown in the
    annotation plane, and the orientation arc.  Keeping those values in one
    helper prevents the leader from pointing at one place while the arc is
    constructed from another.
    """
    if str(getattr(obj, "ToleranceType", "")) not in (
        "CircularRunout",
        "TotalRunout",
    ):
        return None

    controlled = getattr(obj, "ControlledObject", None)
    subelement = getattr(obj, "ControlledSubelement", "")

    try:
        from .MBDDimension import cylindrical_face_reference

        cylinder = cylindrical_face_reference(controlled, subelement)

        if cylinder is None:
            cylinder = revolved_surface_axis_reference(controlled, subelement)

        if cylinder is None:
            return None

        origin_on_plane = FreeCAD.Vector(origin)
        normal = FreeCAD.Vector(normal)

        if normal.Length <= 1e-9:
            return None

        normal.normalize()
        base_attachment = runout_surface_attachment_point_in_plane(
            cylinder,
            origin_on_plane,
            normal,
            attachment
        )
        base_attachment = project_point_to_plane(
            base_attachment,
            origin_on_plane,
            normal
        )
        datum_axis = runout_datum_axis_reference(obj)

        if datum_axis is None:
            datum_axis = cylinder

        axis = FreeCAD.Vector(
            datum_axis.get("direction", FreeCAD.Vector(0, 0, 1))
        )

        if axis.Length <= 1e-9:
            return None

        axis.normalize()
        datum_point = FreeCAD.Vector(
            datum_axis.get("point", base_attachment)
        )
        datum_point_on_plane = project_point_to_plane(
            datum_point,
            origin_on_plane,
            normal
        )
        axis_on_plane = axis - normal * axis.dot(normal)

        if axis_on_plane.Length <= 1e-9:
            axis_on_plane = FreeCAD.Vector(x_axis)

        if axis_on_plane.Length <= 1e-9:
            return None

        axis_on_plane.normalize()
        oriented_leader = runout_leader_from_orientation_angle(
            obj,
            origin_on_plane,
            datum_point_on_plane,
            axis_on_plane,
            normal,
            height,
            base_attachment
        )
        nearest_surface_point = nearest_controlled_surface_point_in_plane(
            controlled,
            subelement,
            origin_on_plane,
            normal
        )

        if oriented_leader is not None:
            arc_center = oriented_leader["arc_center"]
            attachment_on_plane = oriented_leader["surface_point"]
            leader_to_surface = oriented_leader["leader_direction"]
            signed_angle = oriented_leader["signed_angle"]
        else:
            attachment_on_plane = (
                nearest_surface_point
                if nearest_surface_point is not None
                else base_attachment
            )
            leader_on_plane = attachment_on_plane - origin_on_plane

            if leader_on_plane.Length <= 1e-9:
                return None

            leader_on_plane.normalize()
            arc_center = line_intersection_in_plane(
                origin_on_plane,
                leader_on_plane,
                datum_point_on_plane,
                axis_on_plane,
                normal
            )

            if arc_center is None:
                arc_center = datum_point_on_plane + axis_on_plane * (
                    (attachment_on_plane - datum_point_on_plane).dot(axis_on_plane)
                )

            leader_to_surface = attachment_on_plane - arc_center

            if leader_to_surface.Length <= 1e-9:
                return None

            leader_to_surface.normalize()

            if axis_on_plane.dot(leader_to_surface) < 0.0:
                axis_on_plane = axis_on_plane.negative()

            signed_angle = math.atan2(
                axis_on_plane.cross(leader_to_surface).dot(normal),
                axis_on_plane.dot(leader_to_surface)
            )

        return {
            "origin": origin_on_plane,
            "attachment": attachment_on_plane,
            "datum_point": datum_point_on_plane,
            "axis": axis_on_plane,
            "arc_center": arc_center,
            "leader": leader_to_surface,
            "signed_angle": signed_angle,
            "normal": normal,
        }
    except Exception:
        return None


def runout_leader_from_orientation_angle(
    obj,
    origin,
    datum_point_on_plane,
    axis_on_plane,
    normal,
    height,
    fallback_attachment
):
    angle_degrees = float(getattr(obj, "RunoutOrientationAngle", 0.0))

    if abs(angle_degrees) <= 1e-9:
        return None

    controlled = getattr(obj, "ControlledObject", None)
    subelement = getattr(obj, "ControlledSubelement", "")
    origin = FreeCAD.Vector(origin)
    datum_point_on_plane = FreeCAD.Vector(datum_point_on_plane)
    axis_on_plane = FreeCAD.Vector(axis_on_plane)
    normal = FreeCAD.Vector(normal)

    if axis_on_plane.Length <= 1e-9 or normal.Length <= 1e-9:
        return None

    axis_on_plane.normalize()
    normal.normalize()
    probe_length = max(
        height * 25.0,
        (FreeCAD.Vector(fallback_attachment) - origin).Length * 3.0
        if fallback_attachment is not None else height * 25.0
    )
    candidates = []

    for signed_angle in (
        math.radians(angle_degrees),
        -math.radians(angle_degrees),
    ):
        leader_direction = FreeCAD.Rotation(
            normal,
            math.degrees(signed_angle)
        ).multVec(axis_on_plane)

        if leader_direction.Length <= 1e-9:
            continue

        leader_direction.normalize()
        arc_center = line_intersection_in_plane(
            origin,
            leader_direction,
            datum_point_on_plane,
            axis_on_plane,
            normal
        )

        if arc_center is None:
            continue

        surface_point, distance = surface_point_near_plane_line(
            controlled,
            subelement,
            arc_center,
            leader_direction,
            probe_length
        )

        if surface_point is None:
            continue

        surface_point = project_point_to_plane(surface_point, origin, normal)

        if (surface_point - arc_center).dot(leader_direction) < 0.0:
            leader_direction = leader_direction.negative()
            signed_angle = -signed_angle

        surface_distance = (surface_point - arc_center).Length

        if surface_distance <= 1e-9:
            continue

        candidates.append((
            distance,
            (origin - arc_center).Length,
            signed_angle,
            arc_center,
            surface_point,
            leader_direction,
        ))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1]))
    _distance, _origin_distance, signed_angle, arc_center, surface_point, leader_direction = candidates[0]
    return {
        "signed_angle": signed_angle,
        "arc_center": arc_center,
        "surface_point": surface_point,
        "leader_direction": leader_direction,
    }


def effective_annotation_basis(obj):
    x_axis, y_axis, normal = annotation_basis(obj)

    if str(getattr(obj, "ToleranceType", "")) in (
        "CircularRunout",
        "TotalRunout",
    ):
        dim_obj = matching_diameter_dimension_for_runout_fcf(obj)

        if dim_obj is not None:
            return annotation_basis(dim_obj)

    return x_axis, y_axis, normal


def effective_annotation_origin(obj):
    origin = FreeCAD.Vector(obj.AnnotationOrigin)

    if str(getattr(obj, "ToleranceType", "")) in (
        "CircularRunout",
        "TotalRunout",
    ):
        dim_obj = matching_diameter_dimension_for_runout_fcf(obj)

        if dim_obj is not None:
            _x_axis, _y_axis, normal = annotation_basis(dim_obj)
            return project_point_to_plane(
                origin,
                FreeCAD.Vector(dim_obj.AnnotationOrigin),
                normal
            )

    return origin


def dashed_line_segments(start, end, short_length, long_length, gap_length):
    start = FreeCAD.Vector(start)
    end = FreeCAD.Vector(end)
    direction = end - start
    total = direction.Length

    if total <= 1e-9:
        return []

    direction.normalize()
    pattern = [short_length, long_length]
    pattern_index = 0
    cursor = 0.0
    segments = []

    while cursor < total - 1e-9:
        dash_length = min(pattern[pattern_index % len(pattern)], total - cursor)
        dash_start = start + direction * cursor
        dash_end = start + direction * (cursor + dash_length)
        segments.append((dash_start, dash_end))
        cursor += dash_length + gap_length
        pattern_index += 1

    return segments


def arrowhead_3d_segments(tip, tangent, plane_normal, size):
    tangent = FreeCAD.Vector(tangent)

    if tangent.Length <= 1e-9:
        return []

    tangent.normalize()
    side = FreeCAD.Vector(plane_normal).cross(tangent)

    if side.Length <= 1e-9:
        return []

    side.normalize()
    tip = FreeCAD.Vector(tip)
    base = tip - tangent * size
    width = size * 0.45
    return [
        (tip, base + side * width),
        (tip, base - side * width),
    ]


def runout_orientation_segments_and_labels(obj, attachment, origin, height, x_axis, y_axis, normal):
    if str(getattr(obj, "ToleranceType", "")) not in (
        "CircularRunout",
        "TotalRunout",
    ):
        return [], []

    try:
        geometry = runout_display_geometry(
            obj,
            attachment,
            origin,
            height,
            x_axis,
            normal
        )

        if geometry is None:
            return [], []

        origin_on_plane = geometry["origin"]
        attachment_on_plane = geometry["attachment"]
        arc_center = geometry["arc_center"]
        axis_on_plane = geometry["axis"]
        leader_to_surface = geometry["leader"]
        signed_angle = geometry["signed_angle"]
        normal = geometry["normal"]

        centerline_length = max(
            height * 8.0,
            (origin_on_plane - arc_center).Length * 1.2,
            (attachment_on_plane - arc_center).Length * 1.2
        )
        segments = dashed_line_segments(
            arc_center - axis_on_plane * centerline_length * 0.5,
            arc_center + axis_on_plane * centerline_length * 0.5,
            height * 0.55,
            height * 1.80,
            height * 0.38
        )

        if leader_to_surface.Length <= 1e-9:
            leader_to_surface = origin_on_plane - arc_center

        if leader_to_surface.Length <= 1e-9:
            return segments, []

        segments.append((arc_center, attachment_on_plane))
        leader_to_surface.normalize()
        angle_degrees = float(getattr(obj, "RunoutOrientationAngle", 0.0))

        if abs(signed_angle) <= math.radians(1.0):
            signed_angle = math.radians(angle_degrees)

        if abs(signed_angle) <= math.radians(1.0):
            return segments, []

        leader_extent_from_axis = (attachment_on_plane - arc_center).Length
        radius = max(height * 2.8, leader_extent_from_axis * 0.55)

        if leader_extent_from_axis > height * 4.0:
            radius = min(radius, leader_extent_from_axis - height * 0.8)
        else:
            radius = min(
                radius,
                max(leader_extent_from_axis * 0.85, height * 1.5)
            )

        if radius <= height * 0.8:
            radius = height * 2.8

        arc_points_3d = []

        for index in range(17):
            t = signed_angle * index / 16.0
            direction = (
                axis_on_plane * math.cos(t)
                + normal.cross(axis_on_plane) * math.sin(t)
            )

            if direction.Length <= 1e-9:
                continue

            direction.normalize()
            arc_points_3d.append(arc_center + direction * radius)

        for start, end in zip(arc_points_3d, arc_points_3d[1:]):
            segments.append((start, end))

        if len(arc_points_3d) >= 2:
            segments.extend(arrowhead_3d_segments(
                arc_points_3d[0],
                arc_points_3d[1] - arc_points_3d[0],
                normal,
                height * 0.45
            ))
            segments.extend(arrowhead_3d_segments(
                arc_points_3d[-1],
                arc_points_3d[-2] - arc_points_3d[-1],
                normal,
                height * 0.45
            ))

        mid_angle = signed_angle * 0.5
        mid_direction = (
            axis_on_plane * math.cos(mid_angle)
            + normal.cross(axis_on_plane) * math.sin(mid_angle)
        )

        if mid_direction.Length <= 1e-9:
            mid_direction = leader_to_surface

        mid_direction.normalize()
        label_radius = radius + height * 0.9

        if abs(math.degrees(signed_angle)) < 25.0:
            label_radius = radius + height * 1.5

        label_point = arc_center + mid_direction * label_radius
        labels = [
            ("{:.3g}°".format(angle_degrees), label_point)
        ]
        return segments, labels
    except Exception:
        return [], []


def referenced_attachment_point(obj):
    referenced = getattr(obj, "ReferencedObject", None)
    subelement = getattr(obj, "ReferencedSubelement", "")

    if referenced is None or not subelement:
        return None

    try:
        target = referenced.Shape.getElement(subelement)
        return FreeCAD.Vector(target.CenterOfMass)
    except Exception:
        return None


def matching_diameter_dimension_for_datum(datum_obj):
    if str(getattr(datum_obj, "DatumType", "")) != "Axis":
        return None

    referenced = getattr(datum_obj, "ReferencedObject", None)
    subelement = getattr(datum_obj, "ReferencedSubelement", "")

    if referenced is None or not subelement:
        return None

    try:
        document = datum_obj.Document
    except Exception:
        return None

    for candidate in document.Objects:
        if str(getattr(candidate, "DimensionKind", "")) != "Diameter":
            continue

        for object_property, subelement_property in (
            ("ReferenceObject1", "ReferenceSubelement1"),
            ("ReferenceObject2", "ReferenceSubelement2"),
        ):
            if (
                getattr(candidate, object_property, None) == referenced
                and getattr(candidate, subelement_property, "") == subelement
            ):
                return candidate

    return None


def dimension_references_object_subelement(dim_obj, referenced, subelement):
    if dim_obj is None or referenced is None or not subelement:
        return False

    for object_property, subelement_property in (
        ("ReferenceObject1", "ReferenceSubelement1"),
        ("ReferenceObject2", "ReferenceSubelement2"),
    ):
        if (
            getattr(dim_obj, object_property, None) == referenced
            and getattr(dim_obj, subelement_property, "") == subelement
        ):
            return True

    return False


def matching_diameter_dimension_for_runout_fcf(fcf_obj):
    try:
        document = fcf_obj.Document
    except Exception:
        return None

    controlled = getattr(fcf_obj, "ControlledObject", None)
    controlled_sub = getattr(fcf_obj, "ControlledSubelement", "")

    for candidate in reversed(document.Objects):
        if str(getattr(candidate, "DimensionKind", "")) != "Diameter":
            continue

        if dimension_references_object_subelement(
            candidate,
            controlled,
            controlled_sub
        ):
            return candidate

    axis_datum = None
    datum_reference = getattr(fcf_obj, "DatumReference", None)

    if (
        datum_reference is not None
        and str(getattr(datum_reference, "DatumType", "")) == "Axis"
    ):
        axis_datum = datum_reference

    if axis_datum is None:
        datum_system = getattr(fcf_obj, "DatumSystem", None)

        if datum_system is not None:
            for _role, datums in datum_system_compartments(datum_system):
                for datum in datums:
                    if str(getattr(datum, "DatumType", "")) == "Axis":
                        axis_datum = datum
                        break

                if axis_datum is not None:
                    break

    if axis_datum is None:
        return None

    referenced = getattr(axis_datum, "ReferencedObject", None)
    subelement = getattr(axis_datum, "ReferencedSubelement", "")

    for candidate in reversed(document.Objects):
        if str(getattr(candidate, "DimensionKind", "")) != "Diameter":
            continue

        if dimension_references_object_subelement(
            candidate,
            referenced,
            subelement
        ):
            return candidate

    return None


def matching_fcf_for_datum_feature(datum_obj):
    if str(getattr(datum_obj, "DatumType", "")) != "Axis":
        return None

    referenced = getattr(datum_obj, "ReferencedObject", None)
    subelement = getattr(datum_obj, "ReferencedSubelement", "")

    if referenced is None or not subelement:
        return None

    try:
        document = datum_obj.Document
    except Exception:
        return None

    for candidate in document.Objects:
        if not hasattr(candidate, "ToleranceType"):
            continue

        if (
            getattr(candidate, "ControlledObject", None) == referenced
            and getattr(candidate, "ControlledSubelement", "") == subelement
        ):
            return candidate

    return None


def datum_box_geometry_on_fcf(datum_obj, fcf_obj):
    try:
        label = str(getattr(datum_obj, "DatumLabel", ""))
        origin = FreeCAD.Vector(fcf_obj.AnnotationOrigin)
        height = max(float(fcf_obj.AnnotationTextHeight), 1.0)
        x_axis, y_axis, normal = annotation_basis(fcf_obj)
    except Exception:
        return None

    padding = height * 0.30
    spans = []

    for kind, text in fcf_cells(fcf_obj):
        if kind == "symbol":
            width = height * 1.6
        elif kind == "tolerance":
            width = max(fcf_tolerance_width(text, height), height * 2.2)
        else:
            width = max(
                len(text) * height * TEXT_WIDTH_FACTOR,
                height * 1.6
            )

        spans.append(width + padding * 2.0)

    if not spans:
        return None

    total_width = sum(spans)
    datum_padding = height * 0.25
    box_height = height + datum_padding * 2.0
    label_width = max(
        len(label) * height * TEXT_WIDTH_FACTOR,
        height
    )
    box_width = label_width + datum_padding * 2.0
    attach_x = min(
        max(height * 1.2, box_width * 0.5),
        max(total_width - box_width * 0.5, box_width * 0.5)
    )
    frame_bottom = origin + x_axis * attach_x
    triangle_width = height * 0.9
    triangle_length = height * 0.9
    triangle_left = frame_bottom - x_axis * (triangle_width * 0.5)
    triangle_right = frame_bottom + x_axis * (triangle_width * 0.5)
    triangle_apex = frame_bottom - y_axis * triangle_length
    connector_gap = height * 0.30
    box_center = triangle_apex - y_axis * (
        connector_gap
        + box_height * 0.5
    )
    lower_left = (
        box_center
        - x_axis * (box_width * 0.5)
        - y_axis * (box_height * 0.5)
    )
    box_top_midpoint = local_point(
        lower_left,
        x_axis,
        y_axis,
        box_width * 0.5,
        box_height
    )
    box_points = [
        local_point(lower_left, x_axis, y_axis, 0, 0),
        local_point(lower_left, x_axis, y_axis, box_width, 0),
        local_point(lower_left, x_axis, y_axis, box_width, box_height),
        local_point(lower_left, x_axis, y_axis, 0, box_height),
        local_point(lower_left, x_axis, y_axis, 0, 0),
    ]
    segments = [
        (triangle_left, triangle_right),
        (triangle_right, triangle_apex),
        (triangle_apex, triangle_left),
        (triangle_apex, box_top_midpoint),
    ]
    segments.extend(zip(box_points, box_points[1:]))
    text_origin = local_point(
        lower_left,
        x_axis,
        y_axis,
        max((box_width - label_width) * 0.5, datum_padding),
        box_height * 0.5
    )

    return {
        "segments": segments,
        "text_origin": text_origin,
        "label": label,
        "height": height,
        "x_axis": x_axis,
        "y_axis": y_axis,
        "normal": normal,
    }


def datum_box_geometry_on_diameter_dimension(datum_obj, dim_obj):
    try:
        label = str(getattr(datum_obj, "DatumLabel", ""))
        dim_data = dimension_display_data(dim_obj)
        dim_origin = FreeCAD.Vector(dim_obj.AnnotationOrigin)
        height = max(float(dim_obj.AnnotationTextHeight), 1.0)
        x_axis, y_axis, normal = annotation_basis(dim_obj)
        point1 = FreeCAD.Vector(dim_data["point1"])
        point2 = FreeCAD.Vector(dim_data["point2"])
    except Exception:
        return None

    datum_padding = height * 0.25
    box_height = height + datum_padding * 2.0
    label_width = max(
        len(label) * height * TEXT_WIDTH_FACTOR,
        height
    )
    box_width = label_width + datum_padding * 2.0
    line_point1 = dim_origin + x_axis * (point1 - dim_origin).dot(x_axis)
    line_point2 = dim_origin + x_axis * (point2 - dim_origin).dot(x_axis)
    extension1 = line_point1 - point1
    extension2 = line_point2 - point2
    candidates = []

    for model_point, line_point, extension in (
        (point1, line_point1, extension1),
        (point2, line_point2, extension2),
    ):
        if extension.Length <= 1e-9:
            continue

        direction = FreeCAD.Vector(extension)
        direction.normalize()
        x_offset = (line_point - dim_origin).dot(x_axis)
        candidates.append((x_offset, line_point, direction))

    if not candidates:
        return None

    _score, leader_point, _leader_direction = min(
        candidates,
        key=lambda item: item[0]
    )

    # For an axis datum applied to an internal diameter, ASME-style model views
    # show the datum identifier below the diameter callout and attached to one
    # diameter extension/leader line.  Use the feature-side extension line as a
    # vertical datum stem instead of continuing in the extension direction,
    # which can place the datum above the dimension text.
    box_center = (
        leader_point
        - y_axis * (height * 1.45 + box_height * 0.5)
    )
    stem_contact = box_center + y_axis * (box_height * 0.5)
    lower_left = (
        box_center
        - x_axis * (box_width * 0.5)
        - y_axis * (box_height * 0.5)
    )
    box_points = [
        local_point(lower_left, x_axis, y_axis, 0, 0),
        local_point(lower_left, x_axis, y_axis, box_width, 0),
        local_point(lower_left, x_axis, y_axis, box_width, box_height),
        local_point(lower_left, x_axis, y_axis, 0, box_height),
        local_point(lower_left, x_axis, y_axis, 0, 0),
    ]
    segments = [(leader_point, stem_contact)]
    segments.extend(zip(box_points, box_points[1:]))
    text_origin = local_point(
        lower_left,
        x_axis,
        y_axis,
        max((box_width - label_width) * 0.5, datum_padding),
        box_height * 0.5
    )

    return {
        "segments": segments,
        "text_origin": text_origin,
        "label": label,
        "height": height,
        "x_axis": x_axis,
        "y_axis": y_axis,
        "normal": normal,
    }


def dragged_annotation_origin(initial_origin, x_axis, y_axis, translation):
    return (
        FreeCAD.Vector(initial_origin)
        + FreeCAD.Vector(x_axis) * float(translation[0])
        + FreeCAD.Vector(y_axis) * float(translation[1])
    )


def make_selection_node():
    node_type = coin.SoType.fromName("SoFCSelection")

    if node_type.isBad():
        return None

    return node_type.createInstance()


class ViewProviderSingleItemFCF:

    def __init__(self, vobj, suspend_rebuild=False):
        self.Object = vobj.Object
        self._initialize_runtime_state()
        self._suspend_rebuild = bool(
            suspend_rebuild
            or getattr(self, "_suspend_rebuild", False)
        )
        vobj.Proxy = self

    def _initialize_runtime_state(self):
        self.root = None
        self.geometry = None
        self.uses_selection_display_mode = False
        self.drag_x = None
        self.drag_y = None
        self.move_view = None
        self.move_gui_document = None
        self.move_location_callback = None
        self.move_button_callback = None
        self.move_active = False
        self.move_has_moved = False
        self.move_anchor = None
        self.move_original_origin = None
        self.direct_view = None
        self.direct_location_callback = None
        self.direct_button_callback = None
        self.direct_active = False
        self.direct_has_moved = False
        self.direct_anchor = None
        self.direct_original_origin = None
        self.direct_start_position = None
        self.direct_hit_warning_reported = False

    def _ensure_runtime_state(self):
        defaults = {
            "root": None,
            "geometry": None,
            "uses_selection_display_mode": False,
            "drag_x": None,
            "drag_y": None,
            "move_view": None,
            "move_gui_document": None,
            "move_location_callback": None,
            "move_button_callback": None,
            "move_active": False,
            "move_has_moved": False,
            "move_anchor": None,
            "move_original_origin": None,
            "direct_view": None,
            "direct_location_callback": None,
            "direct_button_callback": None,
            "direct_active": False,
            "direct_has_moved": False,
            "direct_anchor": None,
            "direct_original_origin": None,
            "direct_start_position": None,
            "direct_hit_warning_reported": False,
        }

        for name, value in defaults.items():
            if not hasattr(self, name):
                setattr(self, name, value)

    def start_edit(self, vobj):
        self._ensure_runtime_state()

        try:
            vobj.Document.setEdit(vobj.Object, 0)
            return True
        except Exception as error:
            FreeCAD.Console.PrintWarning(
                "Could not enter annotation move mode for {}: {}\n".format(
                    self.Object.Name,
                    error
                )
            )
            return False

    def attach(self, vobj):
        self._ensure_runtime_state()
        self.Object = vobj.Object
        ensure_pmi_display_layout(self.Object)

        if float(self.Object.AnnotationTextHeight) <= 0:
            self.Object.AnnotationTextHeight = 3.0

        self.root = make_selection_node()
        self.uses_selection_display_mode = self.root is not None

        if self.root is None:
            self.root = coin.SoSeparator()

        self.geometry = coin.SoSeparator()
        self.root.addChild(self.geometry)

        if self.uses_selection_display_mode:
            vobj.addDisplayMode(self.root, ANNOTATION_DISPLAY_MODE)

            try:
                vobj.DisplayMode = ANNOTATION_DISPLAY_MODE
            except Exception:
                pass
        else:
            vobj.RootNode.addChild(self.root)

        if not getattr(self, "_suspend_rebuild", False):
            self.rebuild()

        self.ensure_direct_interaction(vobj, verbose=False)

    def ensure_direct_interaction(self, vobj, verbose=False):
        self._ensure_runtime_state()

        try:
            view = vobj.Document.activeView()

            if view is None:
                raise RuntimeError("no active 3D view")

            if self.direct_view is view:
                return True

            self._remove_direct_move_callbacks()
            self.direct_view = view
            self.direct_location_callback = (
                self.direct_view.addEventCallbackPivy(
                    coin.SoLocation2Event.getClassTypeId(),
                    self._direct_move_location
                )
            )
            self.direct_button_callback = (
                self.direct_view.addEventCallbackPivy(
                    coin.SoMouseButtonEvent.getClassTypeId(),
                    self._direct_move_button
                )
            )
            if verbose:
                FreeCAD.Console.PrintMessage(
                    "Direct 3D annotation movement enabled for {}.\n".format(
                        self.Object.Name
                    )
                )
            return True
        except Exception as error:
            self.direct_view = None
            self.direct_location_callback = None
            self.direct_button_callback = None
            if verbose:
                FreeCAD.Console.PrintWarning(
                    "Could not enable direct 3D annotation movement for {}: "
                    "{}\n".format(
                        self.Object.Name,
                        error
                    )
                )
            return False

    def _remove_direct_move_callbacks(self):
        if self.direct_view is not None:
            if self.direct_location_callback is not None:
                self.direct_view.removeEventCallbackPivy(
                    coin.SoLocation2Event.getClassTypeId(),
                    self.direct_location_callback
                )

            if self.direct_button_callback is not None:
                self.direct_view.removeEventCallbackPivy(
                    coin.SoMouseButtonEvent.getClassTypeId(),
                    self.direct_button_callback
                )

        self.direct_view = None
        self.direct_location_callback = None
        self.direct_button_callback = None
        self.direct_active = False
        self.direct_has_moved = False
        self.direct_anchor = None
        self.direct_original_origin = None
        self.direct_start_position = None

    def rebuild(self):
        if self.geometry is None or self.Object is None:
            return

        obj = self.Object
        self.geometry.removeAllChildren()
        origin = effective_annotation_origin(obj)
        height = max(float(obj.AnnotationTextHeight), 1.0)
        x_axis, y_axis, _normal = effective_annotation_basis(obj)
        cells = fcf_cells(obj)
        padding = height * 0.30
        spans = []

        for kind, text in cells:
            if kind == "symbol":
                width = height * 1.6
            elif kind == "tolerance":
                width = max(fcf_tolerance_width(text, height), height * 2.2)
            else:
                width = max(
                    len(text) * height * TEXT_WIDTH_FACTOR,
                    height * 1.6
                )

            spans.append(width + padding * 2.0)

        frame_height = height + padding * 2.0
        total_width = sum(spans)
        segments = [
            (
                local_point(origin, x_axis, y_axis, 0, 0),
                local_point(origin, x_axis, y_axis, total_width, 0)
            ),
            (
                local_point(origin, x_axis, y_axis, total_width, 0),
                local_point(origin, x_axis, y_axis, total_width, frame_height)
            ),
            (
                local_point(origin, x_axis, y_axis, total_width, frame_height),
                local_point(origin, x_axis, y_axis, 0, frame_height)
            ),
            (
                local_point(origin, x_axis, y_axis, 0, frame_height),
                local_point(origin, x_axis, y_axis, 0, 0)
            ),
        ]
        x = 0.0

        for span in spans[:-1]:
            x += span
            segments.append((
                local_point(origin, x_axis, y_axis, x, 0),
                local_point(origin, x_axis, y_axis, x, frame_height)
            ))

        attachment = fcf_attachment_point(obj)
        extra_labels = []

        if attachment is not None:
            if str(getattr(obj, "ToleranceType", "")) in (
                "CircularRunout",
                "TotalRunout",
            ):
                runout_geometry = runout_display_geometry(
                    obj,
                    attachment,
                    origin,
                    height,
                    x_axis,
                    _normal
                )

                if runout_geometry is not None:
                    attachment = runout_geometry["attachment"]

            segments.extend(
                fcf_leader_segments(obj, attachment, origin, height)
            )
            runout_segments, runout_labels = runout_orientation_segments_and_labels(
                obj,
                attachment,
                origin,
                height,
                x_axis,
                y_axis,
                _normal
            )
            segments.extend(runout_segments)
            extra_labels.extend(runout_labels)

        x = 0.0

        for index, (kind, text) in enumerate(cells):
            span = spans[index]

            if kind == "symbol":
                symbol = text
                symbol_size = height * 0.95
                symbol_x = x + padding * 0.5
                symbol_y = (frame_height - symbol_size) * 0.5

                for start, end in symbol_segments(symbol):
                    segments.append((
                        local_point(
                            origin, x_axis, y_axis,
                            symbol_x + start[0] * symbol_size,
                            symbol_y + start[1] * symbol_size
                        ),
                        local_point(
                            origin, x_axis, y_axis,
                            symbol_x + end[0] * symbol_size,
                            symbol_y + end[1] * symbol_size
                        )
                    ))

            if kind == "tolerance":
                cursor = x + padding
                gap = fcf_tolerance_part_gap(height)

                for part_kind, part_value in text:
                    part_width = fcf_tolerance_part_width(
                        (part_kind, part_value),
                        height
                    )

                    if part_kind == "symbol":
                        symbol_size = height * 0.75
                        symbol_y = (frame_height - symbol_size) * 0.5

                        for start, end in symbol_segments(part_value):
                            segments.append((
                                local_point(
                                    origin, x_axis, y_axis,
                                    cursor + start[0] * symbol_size,
                                    symbol_y + start[1] * symbol_size
                                ),
                                local_point(
                                    origin, x_axis, y_axis,
                                    cursor + end[0] * symbol_size,
                                    symbol_y + end[1] * symbol_size
                                )
                            ))
                    else:
                        text_origin = local_point(
                            origin,
                            x_axis,
                            y_axis,
                            cursor,
                            frame_height * 0.5
                        )
                        add_inline_text(
                            self.geometry,
                            part_value,
                            text_origin,
                            x_axis,
                            y_axis,
                            _normal,
                            height
                        )

                    cursor += part_width + gap

            elif kind != "symbol":
                text_x = x + padding

                text_origin = local_point(
                    origin,
                    x_axis,
                    y_axis,
                    text_x,
                    frame_height * 0.5
                )
                add_inline_text(
                    self.geometry,
                    text,
                    text_origin,
                    x_axis,
                    y_axis,
                    _normal,
                    height
                )

            x += span

        for label_text, label_origin in extra_labels:
            add_inline_text(
                self.geometry,
                label_text,
                label_origin,
                x_axis,
                y_axis,
                _normal,
                height * 0.8
            )

        material = coin.SoMaterial()
        material.diffuseColor.setValue(1.0, 1.0, 1.0)
        draw_style = coin.SoDrawStyle()
        draw_style.lineWidth = 1.0
        self.geometry.insertChild(material, 0)
        self.geometry.insertChild(draw_style, 1)
        add_line_geometry(self.geometry, segments)

    def updateData(self, obj, prop):
        if getattr(self, "_suspend_rebuild", False):
            return

        if prop in {
            "ToleranceType",
            "ToleranceValue",
            "DiameterZone",
            "ProfileAllOver",
            "MaterialConditionModifier",
            "ProjectedToleranceZone",
            "ProjectedToleranceHeight",
            "UnequallyDisposedZone",
            "UnequallyDisposedOffset",
            "TangentPlaneModifier",
            "StatisticalToleranceModifier",
            "CommonZoneModifier",
            "MaximumToleranceValueEnabled",
            "MaximumToleranceValue",
            "UnitBasisToleranceEnabled",
            "UnitBasisType",
            "UnitBasisPrimaryLength",
            "UnitBasisSecondaryLength",
            "NonUniformToleranceZone",
            "DatumSystem",
            "DatumReference",
            "ControlledObject",
            "ControlledSubelement",
            "AffectedPlaneObject",
            "AffectedPlaneSubelement",
            "RunoutOrientationAngle",
            "AnnotationOrigin",
            "AnnotationNormal",
            "AnnotationDirection",
            "AnnotationTextHeight",
        }:
            self.rebuild()

    def onChanged(self, vobj, prop):
        pass

    def getDisplayModes(self, obj):
        if getattr(self, "uses_selection_display_mode", False):
            return [ANNOTATION_DISPLAY_MODE]

        return []

    def getDefaultDisplayMode(self):
        if getattr(self, "uses_selection_display_mode", False):
            return ANNOTATION_DISPLAY_MODE

        return "Flat Lines"

    def setDisplayMode(self, mode):
        return mode

    def setEdit(self, vobj, mode=0):
        self._ensure_runtime_state()

        if mode != 0:
            return False

        self.move_original_origin = FreeCAD.Vector(
            self.Object.AnnotationOrigin
        )
        self.move_active = False
        self.move_has_moved = False
        self.move_anchor = None
        self.drag_x, self.drag_y, _normal = effective_annotation_basis(self.Object)
        self.move_view = vobj.Document.activeView()
        self.move_gui_document = vobj.Document
        self.move_location_callback = self.move_view.addEventCallbackPivy(
            coin.SoLocation2Event.getClassTypeId(),
            self._move_location
        )
        self.move_button_callback = self.move_view.addEventCallbackPivy(
            coin.SoMouseButtonEvent.getClassTypeId(),
            self._move_button
        )
        FreeCAD.Console.PrintMessage(
            "Move annotation mode active for {}. Press and move with the "
            "left mouse button; release or click again to place. "
            "Right-click to cancel.\n".format(
                self.Object.Name
            )
        )
        return True

    def _cursor_on_annotation_plane(self, event):
        return self._event_point_on_annotation_plane(
            event,
            self.move_view
        )

    def _event_point_on_annotation_plane(self, event, view):
        position = event.getPosition()
        cursor_point = view.getPoint(
            int(position[0]),
            int(position[1])
        )
        view_direction = FreeCAD.Vector(
            view.getViewDirection()
        )
        _x_axis, _y_axis, normal = effective_annotation_basis(self.Object)
        denominator = normal.dot(view_direction)

        if abs(denominator) <= 1e-9:
            return None

        origin = effective_annotation_origin(self.Object)
        distance = normal.dot(origin - cursor_point) / denominator
        return cursor_point + view_direction * distance

    def _direct_hit_is_owner(self, event):
        if self.direct_view is None:
            return False

        try:
            selection = FreeCADGui.Selection.getSelection()

            if self.Object in selection:
                return True
        except Exception:
            pass

        try:
            preselection = FreeCADGui.Selection.getPreselection()
            preselected_object = getattr(preselection, "Object", None)

            if preselected_object == self.Object:
                return True

            if (
                preselected_object is not None
                and preselected_object != self.Object
            ):
                selection = FreeCADGui.Selection.getSelection()

                if self.Object not in selection:
                    return False
        except Exception:
            pass

        position = event.getPosition()
        info = self.direct_view.getObjectInfo((
            int(position[0]),
            int(position[1])
        ))

        if not info:
            return False

        object_name = str(info.get("Object", ""))
        parent = info.get("ParentObject")
        parent_name = getattr(parent, "Name", "")
        sub_name = str(info.get("SubName", ""))
        owner_names = {
            self.Object.Name,
            getattr(self.Object, "Label", ""),
        }
        matches = (
            object_name in owner_names
            or parent_name in owner_names
            or sub_name == self.Object.Name
            or sub_name.startswith(self.Object.Name + ".")
        )

        if matches:
            self.direct_hit_warning_reported = False
            return True

        return False

    def _direct_move_location(self, callback):
        if (
            not self.direct_active
            or self.direct_anchor is None
            or self.move_view is not None
        ):
            return

        event = callback.getEvent()
        position = event.getPosition()

        if self.direct_start_position is not None:
            dx = float(position[0] - self.direct_start_position[0])
            dy = float(position[1] - self.direct_start_position[1])

            if not self.direct_has_moved and dx * dx + dy * dy < 9.0:
                return

        point = self._event_point_on_annotation_plane(
            event,
            self.direct_view
        )

        if point is None:
            return

        delta = point - self.direct_anchor

        if delta.Length <= 1e-9:
            return

        self.Object.AnnotationOrigin = (
            self.direct_original_origin + delta
        )
        self.Object.DisplayLayoutMode = "Manual"
        self.Object.DisplayLayoutLocked = True

        if not self.direct_has_moved:
            FreeCAD.Console.PrintMessage(
                "Moving annotation {} directly in the 3D view.\n".format(
                    self.Object.Name
                )
            )

        self.direct_has_moved = True
        callback.setHandled()

    def _direct_move_button(self, callback):
        if self.move_view is not None:
            return

        event = callback.getEvent()
        button = event.getButton()
        state = event.getState()

        if button == coin.SoMouseButtonEvent.BUTTON2:
            if (
                state == coin.SoMouseButtonEvent.DOWN
                and self.direct_active
                and self.direct_has_moved
            ):
                self.Object.AnnotationOrigin = self.direct_original_origin
                self._finish_direct_move(False)
                callback.setHandled()
            return

        if button != coin.SoMouseButtonEvent.BUTTON1:
            return

        if state == coin.SoMouseButtonEvent.DOWN:
            if self.direct_active and self.direct_has_moved:
                self._finish_direct_move(True)
                callback.setHandled()
                return

            if self.direct_active:
                self.direct_active = False
                self.direct_anchor = None
                self.direct_original_origin = None
                self.direct_start_position = None

            if not self._direct_hit_is_owner(event):
                return

            if hasattr(FreeCADGui, "Selection"):
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(self.Object)
            self.direct_original_origin = FreeCAD.Vector(
                self.Object.AnnotationOrigin
            )
            self.direct_anchor = self._event_point_on_annotation_plane(
                event,
                self.direct_view
            )
            self.direct_active = self.direct_anchor is not None
            self.direct_has_moved = False
            self.direct_start_position = event.getPosition()
            callback.setHandled()
            return

        if (
            state == coin.SoMouseButtonEvent.UP
            and self.direct_active
        ):
            if self.direct_has_moved:
                self._direct_move_location(callback)
                self._finish_direct_move(True)
            else:
                self.direct_active = False
                self.direct_anchor = None
                self.direct_original_origin = None
                self.direct_start_position = None

            callback.setHandled()

    def _finish_direct_move(self, committed):
        if committed:
            FreeCAD.Console.PrintMessage(
                "Annotation position committed for {}.\n".format(
                    self.Object.Name
                )
            )
        else:
            FreeCAD.Console.PrintMessage(
                "Annotation move cancelled for {}.\n".format(
                    self.Object.Name
                )
            )

        self.direct_active = False
        self.direct_has_moved = False
        self.direct_anchor = None
        self.direct_original_origin = None
        self.direct_start_position = None

    def _move_location(self, callback):
        if not self.move_active or self.move_anchor is None:
            return

        point = self._cursor_on_annotation_plane(callback.getEvent())

        if point is None:
            return

        delta = point - self.move_anchor
        self.Object.AnnotationOrigin = self.move_original_origin + delta
        self.Object.DisplayLayoutMode = "Manual"
        self.Object.DisplayLayoutLocked = True
        self.move_has_moved = delta.Length > 1e-9

    def _move_button(self, callback):
        event = callback.getEvent()
        button = event.getButton()
        state = event.getState()

        if button == coin.SoMouseButtonEvent.BUTTON2:
            if state == coin.SoMouseButtonEvent.DOWN:
                self.Object.AnnotationOrigin = self.move_original_origin
                FreeCAD.Console.PrintMessage(
                    "Annotation move cancelled for {}.\n".format(
                        self.Object.Name
                    )
                )
                self._finish_move_mode()
            return

        if button != coin.SoMouseButtonEvent.BUTTON1:
            return

        if state == coin.SoMouseButtonEvent.DOWN:
            if self.move_active and self.move_has_moved:
                self.move_active = False
                self.move_has_moved = False
                self.move_anchor = None
                FreeCAD.Console.PrintMessage(
                    "Annotation position committed for {}.\n".format(
                        self.Object.Name
                    )
                )
                self._finish_move_mode()
                return

            self.move_anchor = self._cursor_on_annotation_plane(event)
            self.move_active = self.move_anchor is not None
            self.move_has_moved = False
            return

        if (
            state == coin.SoMouseButtonEvent.UP
            and self.move_active
            and self.move_has_moved
        ):
            self._move_location(callback)
            self.move_active = False
            self.move_has_moved = False
            self.move_anchor = None
            FreeCAD.Console.PrintMessage(
                "Annotation position committed for {}.\n".format(
                    self.Object.Name
                )
            )
            self._finish_move_mode()

    def _finish_move_mode(self):
        gui_document = self.move_gui_document

        if gui_document is not None:
            QtCore.QTimer.singleShot(0, gui_document.resetEdit)

    def unsetEdit(self, vobj, mode=0):
        self._ensure_runtime_state()

        if self.move_view is not None:
            if self.move_location_callback is not None:
                self.move_view.removeEventCallbackPivy(
                    coin.SoLocation2Event.getClassTypeId(),
                    self.move_location_callback
                )

            if self.move_button_callback is not None:
                self.move_view.removeEventCallbackPivy(
                    coin.SoMouseButtonEvent.getClassTypeId(),
                    self.move_button_callback
                )

        self.move_view = None
        self.move_gui_document = None
        self.move_location_callback = None
        self.move_button_callback = None
        self.move_active = False
        self.move_has_moved = False
        self.move_anchor = None
        return True

    def doubleClicked(self, vobj):
        return self.start_edit(vobj)

    def setupContextMenu(self, vobj, menu):
        action = QtGui.QAction("Move annotation", menu)
        action.triggered.connect(lambda: self.start_edit(vobj))
        menu.addAction(action)

    def claimChildren(self):
        return []

    def onDelete(self, vobj, subelements):
        self._remove_direct_move_callbacks()
        return True

    def getIcon(self):
        return ""

    def dumps(self):
        return None

    def loads(self, state):
        return None


class ViewProviderSingleItemDatumTarget(ViewProviderSingleItemFCF):

    def rebuild(self):
        if self.geometry is None or self.Object is None:
            return

        obj = self.Object
        self.geometry.removeAllChildren()
        origin = FreeCAD.Vector(obj.AnnotationOrigin)
        point = FreeCAD.Vector(obj.TargetPoint)
        height = max(float(obj.AnnotationTextHeight), 1.0)
        x_axis, y_axis, normal = annotation_basis(obj)
        marker_radius = height * 0.28
        segments = [(point, origin)]

        target_type = str(getattr(obj, "TargetType", "Point"))

        if target_type == "Line":
            start = FreeCAD.Vector(obj.TargetEndPoint1)
            end = FreeCAD.Vector(obj.TargetEndPoint2)
            segments.append((start, end))
        elif target_type == "Circle":
            radius = max(float(getattr(obj, "TargetDiameter", 0.0)) * 0.5, marker_radius)
            marker_points = arc_points(
                0,
                0,
                radius,
                radius,
                0,
                360,
                48
            )

            for start, end in zip(marker_points, marker_points[1:]):
                segments.append((
                    local_point(
                        point,
                        x_axis,
                        y_axis,
                        start[0],
                        start[1]
                    ),
                    local_point(
                        point,
                        x_axis,
                        y_axis,
                        end[0],
                        end[1]
                    )
                ))
        elif target_type == "Rectangle":
            length = max(float(getattr(obj, "TargetLength", 0.0)), marker_radius * 2.0)
            width = max(float(getattr(obj, "TargetWidth", 0.0)), marker_radius * 2.0)
            corners = [
                local_point(point, x_axis, y_axis, -length * 0.5, -width * 0.5),
                local_point(point, x_axis, y_axis, length * 0.5, -width * 0.5),
                local_point(point, x_axis, y_axis, length * 0.5, width * 0.5),
                local_point(point, x_axis, y_axis, -length * 0.5, width * 0.5),
            ]

            for start, end in zip(corners, corners[1:] + corners[:1]):
                segments.append((start, end))
        elif target_type == "Area":
            marker_points = arc_points(
                0,
                0,
                marker_radius * 1.4,
                marker_radius * 1.4,
                0,
                360,
                32
            )

            for start, end in zip(marker_points, marker_points[1:]):
                segments.append((
                    local_point(
                        point,
                        x_axis,
                        y_axis,
                        start[0],
                        start[1]
                    ),
                    local_point(
                        point,
                        x_axis,
                        y_axis,
                        end[0],
                        end[1]
                    )
                ))
        else:
            segments.extend([
                (
                    point - x_axis * marker_radius,
                    point + x_axis * marker_radius
                ),
                (
                    point - y_axis * marker_radius,
                    point + y_axis * marker_radius
                ),
            ])
            marker_points = arc_points(
                0,
                0,
                marker_radius,
                marker_radius,
                0,
                360,
                32
            )

            for start, end in zip(marker_points, marker_points[1:]):
                segments.append((
                    local_point(
                        point,
                        x_axis,
                        y_axis,
                        start[0],
                        start[1]
                    ),
                    local_point(
                        point,
                        x_axis,
                        y_axis,
                        end[0],
                        end[1]
                    )
                ))

        material = coin.SoMaterial()
        material.diffuseColor.setValue(1.0, 1.0, 1.0)
        draw_style = coin.SoDrawStyle()
        draw_style.lineWidth = 1.0
        self.geometry.addChild(material)
        self.geometry.addChild(draw_style)
        add_line_geometry(self.geometry, segments)

        transform = coin.SoTransform()
        transform.translation.setValue(origin.x, origin.y, origin.z)
        rotation = FreeCAD.Rotation(x_axis, y_axis, normal, "XYZ")
        quaternion = rotation.Q
        transform.rotation.setValue(
            quaternion[0],
            quaternion[1],
            quaternion[2],
            quaternion[3]
        )
        font_style = coin.SoVRMLFontStyle()
        font_style.size = height * 0.85
        font_style.justify.setValues(0, 2, ["BEGIN", "MIDDLE"])
        text_node = coin.SoVRMLText()
        text_node.string = str(obj.TargetId)
        text_node.fontStyle = font_style
        text_separator = coin.SoSeparator()
        text_separator.addChild(transform)
        text_separator.addChild(text_node)
        self.geometry.addChild(text_separator)

    def updateData(self, obj, prop):
        if prop in {
            "TargetId",
            "TargetType",
            "TargetPoint",
            "TargetEndPoint1",
            "TargetEndPoint2",
            "TargetDiameter",
            "TargetLength",
            "TargetWidth",
            "AnnotationOrigin",
            "AnnotationNormal",
            "AnnotationDirection",
            "AnnotationTextHeight",
        }:
            self.rebuild()


class ViewProviderSingleItemDatumFeature(ViewProviderSingleItemFCF):

    def rebuild(self):
        if self.geometry is None or self.Object is None:
            return

        started = time.perf_counter()
        obj = self.Object
        self.geometry.removeAllChildren()
        cleared = time.perf_counter()
        datum_box = None
        fcf_obj = matching_fcf_for_datum_feature(obj)
        fcf_lookup_done = time.perf_counter()

        if fcf_obj is not None:
            datum_box = datum_box_geometry_on_fcf(obj, fcf_obj)
        fcf_geometry_done = time.perf_counter()

        dim_obj = matching_diameter_dimension_for_datum(obj)
        dimension_lookup_done = time.perf_counter()

        if datum_box is None and dim_obj is not None:
            datum_box = datum_box_geometry_on_diameter_dimension(obj, dim_obj)
        dimension_geometry_done = time.perf_counter()

        if datum_box is not None:
            material = coin.SoMaterial()
            material.diffuseColor.setValue(1.0, 1.0, 1.0)
            draw_style = coin.SoDrawStyle()
            draw_style.lineWidth = 1.0
            self.geometry.addChild(material)
            self.geometry.addChild(draw_style)
            add_line_geometry(self.geometry, datum_box["segments"])
            add_world_text(
                self.geometry,
                datum_box["text_origin"],
                datum_box["label"],
                datum_box["height"],
                datum_box["x_axis"],
                datum_box["y_axis"],
                datum_box["normal"]
            )
            finished = time.perf_counter()

            if finished - started > 0.25:
                FreeCAD.Console.PrintMessage(
                    "Datum feature rebuild phases for {}: clear {:.3f}s,"
                    " fcf lookup {:.3f}s, fcf geometry {:.3f}s,"
                    " diameter lookup {:.3f}s, diameter geometry {:.3f}s,"
                    " draw {:.3f}s\n".format(
                        obj.Name,
                        cleared - started,
                        fcf_lookup_done - cleared,
                        fcf_geometry_done - fcf_lookup_done,
                        dimension_lookup_done - fcf_geometry_done,
                        dimension_geometry_done - dimension_lookup_done,
                        finished - dimension_geometry_done
                    )
                )
            return

        attachment = referenced_attachment_point(obj)
        attachment_done = time.perf_counter()

        if attachment is None:
            return

        origin = FreeCAD.Vector(obj.AnnotationOrigin)
        height = max(float(obj.AnnotationTextHeight), 1.0)
        x_axis, y_axis, normal = annotation_basis(obj)
        triangle_length = height * 1.2
        triangle_width = height * 0.9
        box_padding = height * 0.25
        box_height = height + box_padding * 2.0
        label = str(getattr(obj, "DatumLabel", ""))
        box_width = max(
            len(label) * height * TEXT_WIDTH_FACTOR,
            height
        ) + box_padding * 2.0
        apex = attachment + x_axis * triangle_length
        leader_end = origin
        box_points = [
            local_point(origin, x_axis, y_axis, 0, 0),
            local_point(origin, x_axis, y_axis, box_width, 0),
            local_point(origin, x_axis, y_axis, box_width, box_height),
            local_point(origin, x_axis, y_axis, 0, box_height),
            local_point(origin, x_axis, y_axis, 0, 0),
        ]
        segments = [
            (
                attachment - y_axis * (triangle_width * 0.5),
                attachment + y_axis * (triangle_width * 0.5)
            ),
            (
                attachment + y_axis * (triangle_width * 0.5),
                apex
            ),
            (
                apex,
                attachment - y_axis * (triangle_width * 0.5)
            ),
            (apex, leader_end),
        ]
        segments.extend(zip(box_points, box_points[1:]))

        material = coin.SoMaterial()
        material.diffuseColor.setValue(1.0, 1.0, 1.0)
        draw_style = coin.SoDrawStyle()
        draw_style.lineWidth = 1.0
        self.geometry.addChild(material)
        self.geometry.addChild(draw_style)
        add_line_geometry(self.geometry, segments)
        text_width = len(label) * height * TEXT_WIDTH_FACTOR
        text_origin = local_point(
            origin,
            x_axis,
            y_axis,
            max((box_width - text_width) * 0.5, box_padding),
            box_height * 0.5
        )
        add_world_text(
            self.geometry,
            text_origin,
            label,
            height,
            x_axis,
            y_axis,
            normal
        )
        finished = time.perf_counter()

        if finished - started > 0.25:
            FreeCAD.Console.PrintMessage(
                "Datum feature rebuild phases for {}: clear {:.3f}s,"
                " fcf lookup {:.3f}s, fcf geometry {:.3f}s,"
                " diameter lookup {:.3f}s, diameter geometry {:.3f}s,"
                " attachment {:.3f}s, draw {:.3f}s\n".format(
                    obj.Name,
                    cleared - started,
                    fcf_lookup_done - cleared,
                    fcf_geometry_done - fcf_lookup_done,
                    dimension_lookup_done - fcf_geometry_done,
                    dimension_geometry_done - dimension_lookup_done,
                    attachment_done - dimension_geometry_done,
                    finished - attachment_done
                )
            )

    def updateData(self, obj, prop):
        if prop in {
            "DatumLabel",
            "ReferencedObject",
            "ReferencedSubelement",
            "AnnotationOrigin",
            "AnnotationNormal",
            "AnnotationDirection",
            "AnnotationTextHeight",
        }:
            self.rebuild()


def dimension_display_data(obj):
    if hasattr(obj, "DimensionKind"):
        from .MBDDimension import dimension_display_label, measurement_from_references

        measurement = measurement_from_references(
            obj.DimensionKind,
            obj.MeasurementType,
            obj.ReferenceObject1,
            obj.ReferenceSubelement1,
            obj.ReferenceObject2,
            obj.ReferenceSubelement2
        )
        data = {
            "kind": str(obj.DimensionKind),
            "label": dimension_display_label(obj),
            "point1": measurement.get("point1"),
            "point2": measurement.get("point2"),
            "boxed": str(obj.DimensionPurpose) == "Basic",
        }

        if str(obj.DimensionKind) == "Angular":
            for key in (
                "angle_vertex",
                "angle_ray1",
                "angle_ray2",
                "angle_normal",
            ):
                data[key] = measurement.get(key)

        return data

    from .MBDBasicDimension import display_points_from_references

    point1, point2 = display_points_from_references(
        obj.ReferenceObject1,
        obj.ReferenceSubelement1,
        obj.ReferenceObject2,
        obj.ReferenceSubelement2
    )
    return {
        "kind": "Linear",
        "label": format_length_for_annotation(obj.NominalValue),
        "point1": point1,
        "point2": point2,
        "boxed": True,
    }


def arrow_segments(tip, direction, side, length, width):
    arrow_direction = FreeCAD.Vector(direction)
    side_direction = FreeCAD.Vector(side)

    if arrow_direction.Length <= 1e-9 or side_direction.Length <= 1e-9:
        return []

    arrow_direction.normalize()
    side_direction.normalize()
    base = tip + arrow_direction * length
    half_width = side_direction * (width * 0.5)
    return [
        (tip, base + half_width),
        (tip, base - half_width),
    ]


def arc_world_points(vertex, ray1, ray2, normal, radius, steps=32):
    start = FreeCAD.Vector(ray1)
    end = FreeCAD.Vector(ray2)
    axis = FreeCAD.Vector(normal)

    if start.Length <= 1e-9 or end.Length <= 1e-9 or axis.Length <= 1e-9:
        return []

    start.normalize()
    end.normalize()
    axis.normalize()
    dot = max(min(start.dot(end), 1.0), -1.0)
    angle = math.acos(dot)

    if angle <= 1e-9:
        return []

    if start.cross(end).dot(axis) < 0.0:
        axis = axis.negative()

    count = max(int(steps), 4)
    points = []

    for index in range(count + 1):
        theta = angle * index / count
        rotated = FreeCAD.Rotation(axis, math.degrees(theta)).multVec(start)
        points.append(vertex + rotated * radius)

    return points


def angular_dimension_segments(data, height, origin=None):
    vertex = data.get("angle_vertex")
    ray1 = data.get("angle_ray1")
    ray2 = data.get("angle_ray2")
    normal = data.get("angle_normal")

    if vertex is None or ray1 is None or ray2 is None or normal is None:
        return None

    vertex = FreeCAD.Vector(vertex)
    ray1 = FreeCAD.Vector(ray1)
    ray2 = FreeCAD.Vector(ray2)
    normal = FreeCAD.Vector(normal)

    if ray1.Length <= 1e-9 or ray2.Length <= 1e-9 or normal.Length <= 1e-9:
        return None

    ray1.normalize()
    ray2.normalize()
    normal.normalize()

    if ray1.cross(ray2).dot(normal) < 0.0:
        normal = normal.negative()

    p1 = data.get("point1")
    p2 = data.get("point2")
    extent = max(height * 8.0, 1.0)

    if p1 is not None:
        extent = max(extent, (FreeCAD.Vector(p1) - vertex).Length)

    if p2 is not None:
        extent = max(extent, (FreeCAD.Vector(p2) - vertex).Length)

    desired_text_origin = None
    if origin is not None:
        desired_text_origin = FreeCAD.Vector(origin)
        offset = desired_text_origin - vertex
        offset = offset - normal * offset.dot(normal)

        if offset.Length > height * 2.0:
            desired_text_origin = vertex + offset
            radius = max(offset.Length - height * 1.5, height * 5.0)
        else:
            desired_text_origin = None

    if desired_text_origin is None:
        radius = max(extent * 0.45, height * 5.0)

    extension_end = max(extent, radius + height * 2.5)
    gap = height * 0.5
    segments = [
        (vertex + ray1 * gap, vertex + ray1 * extension_end),
        (vertex + ray2 * gap, vertex + ray2 * extension_end),
    ]
    arc_points = arc_world_points(vertex, ray1, ray2, normal, radius)

    if len(arc_points) < 2:
        return None

    segments.extend(zip(arc_points, arc_points[1:]))
    arrow_length = height * 1.0
    arrow_width = height * 0.38
    tangent_start = normal.cross(ray1)
    tangent_end = normal.cross(ray2)

    if tangent_start.Length > 1e-9:
        segments.extend(arrow_segments(
            arc_points[0],
            tangent_start,
            ray1,
            arrow_length,
            arrow_width
        ))

    if tangent_end.Length > 1e-9:
        segments.extend(arrow_segments(
            arc_points[-1],
            tangent_end.negative(),
            ray2,
            arrow_length,
            arrow_width
        ))

    text_direction = ray1 + ray2

    if desired_text_origin is not None:
        text_origin = desired_text_origin
    elif text_direction.Length <= 1e-9:
        text_origin = vertex + ray1 * (radius + height * 1.5)
    else:
        text_direction.normalize()
        text_origin = vertex + text_direction * (radius + height * 1.5)

    return {
        "segments": segments,
        "text_origin": text_origin,
        "x_axis": ray1,
        "y_axis": normal.cross(ray1),
        "normal": normal,
    }


def add_world_text(parent, origin, text, height, x_axis, y_axis, normal):
    transform = coin.SoTransform()
    transform.translation.setValue(origin.x, origin.y, origin.z)
    rotation = FreeCAD.Rotation(x_axis, y_axis, normal, "XYZ")
    quaternion = rotation.Q
    transform.rotation.setValue(
        quaternion[0],
        quaternion[1],
        quaternion[2],
        quaternion[3]
    )
    font_style = coin.SoVRMLFontStyle()
    font_style.size = height * 0.85
    font_style.justify.setValues(0, 2, ["BEGIN", "MIDDLE"])
    text_node = coin.SoVRMLText()
    text_node.string = str(text)
    text_node.fontStyle = font_style
    separator = coin.SoSeparator()
    separator.addChild(transform)
    separator.addChild(text_node)
    parent.addChild(separator)


class ViewProviderSingleItemDimension(ViewProviderSingleItemFCF):

    def __init__(
        self,
        vobj,
        resolved_display_data=None,
        suspend_rebuild=False
    ):
        self._resolved_display_data = resolved_display_data
        self._suspend_rebuild = bool(suspend_rebuild)
        super().__init__(vobj)

    def rebuild(self):
        if self.geometry is None or self.Object is None:
            return

        obj = self.Object
        self.geometry.removeAllChildren()
        data = getattr(self, "_resolved_display_data", None)

        if data is None:
            data = dimension_display_data(obj)
        else:
            self._resolved_display_data = None

        point1 = data["point1"]
        point2 = data["point2"]

        if point1 is None or point2 is None:
            return

        origin = FreeCAD.Vector(obj.AnnotationOrigin)
        height = max(float(obj.AnnotationTextHeight), 1.0)
        x_axis, y_axis, normal = annotation_basis(obj)
        measured = point2 - point1

        if measured.Length <= 1e-9:
            return

        measured.normalize()

        if x_axis.dot(measured) < 0:
            x_axis = x_axis.negative()
            y_axis = y_axis.negative()

        segments = []
        arrow_length = height * 1.3
        arrow_width = height * 0.45
        text_origin = origin
        text_width = max(
            len(data["label"]) * height * TEXT_WIDTH_FACTOR,
            height * 2.0
        )

        if data["kind"] == "Angular":
            angular_data = angular_dimension_segments(data, height, origin)

            if angular_data is None:
                return

            segments.extend(angular_data["segments"])
            text_origin = angular_data["text_origin"]
            x_axis = angular_data["x_axis"]
            y_axis = angular_data["y_axis"]
            normal = angular_data["normal"]
        elif data["kind"] == "Radius":
            surface_point = point2
            leader_direction = origin - surface_point

            if leader_direction.Length <= 1e-9:
                leader_direction = point2 - point1

            leader_direction.normalize()
            segments.append((surface_point, origin))
            segments.extend(arrow_segments(
                surface_point,
                leader_direction,
                y_axis,
                arrow_length,
                arrow_width
            ))
        else:
            line_point1 = origin + x_axis * (point1 - origin).dot(x_axis)
            line_point2 = origin + x_axis * (point2 - origin).dot(x_axis)
            extension1 = line_point1 - point1
            extension2 = line_point2 - point2
            gap = height * 0.7
            overshoot = height * 0.8

            if extension1.Length > 1e-9:
                direction1 = FreeCAD.Vector(extension1)
                direction1.normalize()
                segments.append((
                    point1 + direction1 * gap,
                    line_point1 + direction1 * overshoot
                ))

            if extension2.Length > 1e-9:
                direction2 = FreeCAD.Vector(extension2)
                direction2.normalize()
                segments.append((
                    point2 + direction2 * gap,
                    line_point2 + direction2 * overshoot
                ))

            segments.append((line_point1, line_point2))
            line_direction = line_point2 - line_point1

            if line_direction.Length > 1e-9:
                line_direction.normalize()
                segments.extend(arrow_segments(
                    line_point1,
                    line_direction,
                    y_axis,
                    arrow_length,
                    arrow_width
                ))
                segments.extend(arrow_segments(
                    line_point2,
                    line_direction.negative(),
                    y_axis,
                    arrow_length,
                    arrow_width
                ))

        if data["boxed"]:
            padding = height * 0.35
            box_points = [
                local_point(text_origin, x_axis, y_axis, -padding, -padding),
                local_point(
                    text_origin, x_axis, y_axis,
                    text_width + padding, -padding
                ),
                local_point(
                    text_origin, x_axis, y_axis,
                    text_width + padding, height + padding
                ),
                local_point(
                    text_origin, x_axis, y_axis,
                    -padding, height + padding
                ),
                local_point(text_origin, x_axis, y_axis, -padding, -padding),
            ]
            segments.extend(zip(box_points, box_points[1:]))

        if data["kind"] == "Diameter":
            symbol_size = height * 0.85

            for start, end in symbol_segments("Diameter"):
                segments.append((
                    local_point(
                        text_origin, x_axis, y_axis,
                        start[0] * symbol_size,
                        start[1] * symbol_size
                    ),
                    local_point(
                        text_origin, x_axis, y_axis,
                        end[0] * symbol_size,
                        end[1] * symbol_size
                    )
                ))

            text_origin = text_origin + x_axis * (height * 1.15)
            text_origin = text_origin + y_axis * (symbol_size * 0.5)

        material = coin.SoMaterial()
        material.diffuseColor.setValue(1.0, 1.0, 1.0)
        draw_style = coin.SoDrawStyle()
        draw_style.lineWidth = 1.0
        self.geometry.addChild(material)
        self.geometry.addChild(draw_style)
        add_line_geometry(self.geometry, segments)
        add_world_text(
            self.geometry,
            text_origin,
            data["label"],
            height,
            x_axis,
            y_axis,
            normal
        )

    def updateData(self, obj, prop):
        if getattr(self, "_suspend_rebuild", False):
            return

        if prop in {
            "DimensionPurpose",
            "DimensionKind",
            "DimensionType",
            "MeasurementType",
            "NominalValue",
            "UpperTolerance",
            "LowerTolerance",
            "UpperLimit",
            "LowerLimit",
            "ReferenceObject1",
            "ReferenceSubelement1",
            "ReferenceObject2",
            "ReferenceSubelement2",
            "AnnotationOrigin",
            "AnnotationNormal",
            "AnnotationDirection",
            "AnnotationTextHeight",
        }:
            self.rebuild()
