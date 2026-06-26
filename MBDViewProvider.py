import math
import time

import FreeCAD
import FreeCADGui
from pivy import coin
from PySide import QtCore, QtGui

from MBDDatumSystem import datum_compartment_label, datum_system_compartments
from MBDPMI import ensure_pmi_display_layout


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
    tolerance = FreeCAD.Units.Quantity(
        obj.ToleranceValue,
        FreeCAD.Units.Length
    ).UserString
    cells = [
        ("symbol", fcf_symbol_name(obj.ToleranceType)),
        ("diameter" if getattr(obj, "DiameterZone", False) else "text",
         tolerance),
    ]

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
            from MBDDimension import cylindrical_face_reference

            cylinder = cylindrical_face_reference(controlled, subelement)

            if cylinder is not None:
                return cylinder["point"]
        except Exception:
            pass

    if subelement:
        try:
            target = controlled.Shape.getElement(subelement)
            return target.CenterOfMass
        except Exception:
            return None

    try:
        from MBDDimension import nearest_point_on_shape

        bbox = controlled.Shape.BoundBox
        preferred_point = FreeCAD.Vector(
            (bbox.XMin + bbox.XMax) * 0.5,
            (bbox.YMin + bbox.YMax) * 0.5,
            bbox.ZMax
        )
        return nearest_point_on_shape(controlled, preferred_point)
    except Exception:
        return None


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
                    return []
    except Exception:
        pass

    leader_segments = [(attachment, origin)]

    if str(getattr(obj, "ToleranceType", "")) != "Position":
        return leader_segments

    controlled = getattr(obj, "ControlledObject", None)
    subelement = getattr(obj, "ControlledSubelement", "")

    try:
        from MBDDimension import cylindrical_face_reference

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
        timing_started = time.perf_counter()
        self.Object = vobj.Object
        self._initialize_runtime_state()
        self._suspend_rebuild = bool(
            suspend_rebuild
            or getattr(self, "_suspend_rebuild", False)
        )
        timing_initialized = time.perf_counter()
        vobj.Proxy = self
        timing_proxy_assigned = time.perf_counter()

        if timing_proxy_assigned - timing_started > 1.0:
            FreeCAD.Console.PrintMessage(
                "Annotation provider constructor for {}: initialize {:.3f}s, "
                "proxy assignment {:.3f}s\n".format(
                    self.Object.Name,
                    timing_initialized - timing_started,
                    timing_proxy_assigned - timing_initialized
                )
            )

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
        timing_started = time.perf_counter()
        self._ensure_runtime_state()
        self.Object = vobj.Object
        ensure_pmi_display_layout(self.Object)

        if float(self.Object.AnnotationTextHeight) <= 0:
            self.Object.AnnotationTextHeight = 3.0

        timing_layout_ready = time.perf_counter()
        self.root = make_selection_node()
        self.uses_selection_display_mode = self.root is not None
        timing_selection_ready = time.perf_counter()

        if self.root is None:
            self.root = coin.SoSeparator()

        self.geometry = coin.SoSeparator()
        self.root.addChild(self.geometry)
        timing_graph_ready = time.perf_counter()

        if self.uses_selection_display_mode:
            vobj.addDisplayMode(self.root, ANNOTATION_DISPLAY_MODE)

            try:
                vobj.DisplayMode = ANNOTATION_DISPLAY_MODE
            except Exception:
                pass
        else:
            vobj.RootNode.addChild(self.root)

        timing_mode_ready = time.perf_counter()
        if not getattr(self, "_suspend_rebuild", False):
            self.rebuild()
        timing_rebuilt = time.perf_counter()
        self.ensure_direct_interaction(vobj, verbose=False)
        timing_interaction_ready = time.perf_counter()

        if timing_interaction_ready - timing_started > 1.0:
            FreeCAD.Console.PrintMessage(
                "Annotation attach phases for {}: layout {:.3f}s, "
                "selection {:.3f}s, graph {:.3f}s, mode {:.3f}s, "
                "geometry {:.3f}s, interaction {:.3f}s\n".format(
                    self.Object.Name,
                    timing_layout_ready - timing_started,
                    timing_selection_ready - timing_layout_ready,
                    timing_graph_ready - timing_selection_ready,
                    timing_mode_ready - timing_graph_ready,
                    timing_rebuilt - timing_mode_ready,
                    timing_interaction_ready - timing_rebuilt
                )
            )

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
        origin = FreeCAD.Vector(obj.AnnotationOrigin)
        height = max(float(obj.AnnotationTextHeight), 1.0)
        x_axis, y_axis, _normal = annotation_basis(obj)
        cells = fcf_cells(obj)
        padding = height * 0.30
        spans = []

        for kind, text in cells:
            if kind == "symbol":
                width = height * 1.6
            elif kind == "diameter":
                width = max(
                    len(text) * height * TEXT_WIDTH_FACTOR + height,
                    height * 2.2
                )
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

        if attachment is not None:
            segments.extend(
                fcf_leader_segments(obj, attachment, origin, height)
            )

        x = 0.0

        for index, (kind, text) in enumerate(cells):
            span = spans[index]

            if kind in ("symbol", "diameter"):
                symbol = text if kind == "symbol" else "Diameter"
                symbol_size = height * (0.95 if kind == "symbol" else 0.75)
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

            if kind != "symbol":
                text_x = x + padding

                if kind == "diameter":
                    text_x += height

                text_origin = local_point(
                    origin,
                    x_axis,
                    y_axis,
                    text_x,
                    frame_height * 0.5
                )
                text_sep = coin.SoSeparator()
                transform = coin.SoTransform()
                transform.translation.setValue(
                    text_origin.x,
                    text_origin.y,
                    text_origin.z
                )
                rotation = FreeCAD.Rotation(
                    x_axis,
                    y_axis,
                    _normal,
                    "XYZ"
                )
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
                text_node.string = text
                text_node.fontStyle = font_style
                text_sep.addChild(transform)
                text_sep.addChild(text_node)
                self.geometry.addChild(text_sep)

            x += span

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
            "DatumSystem",
            "DatumReference",
            "ControlledObject",
            "ControlledSubelement",
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
        self.drag_x, self.drag_y, _normal = annotation_basis(self.Object)
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
        _x_axis, _y_axis, normal = annotation_basis(self.Object)
        denominator = normal.dot(view_direction)

        if abs(denominator) <= 1e-9:
            return None

        origin = FreeCAD.Vector(self.Object.AnnotationOrigin)
        distance = normal.dot(origin - cursor_point) / denominator
        return cursor_point + view_direction * distance

    def _direct_hit_is_owner(self, event):
        if self.direct_view is None:
            return False

        try:
            preselection = FreeCADGui.Selection.getPreselection()
            preselected_object = getattr(preselection, "Object", None)

            if (
                preselected_object is not None
                and preselected_object != self.Object
            ):
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

        if str(getattr(obj, "TargetType", "Point")) == "Line":
            start = FreeCAD.Vector(obj.TargetEndPoint1)
            end = FreeCAD.Vector(obj.TargetEndPoint2)
            segments.append((start, end))
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

        obj = self.Object
        self.geometry.removeAllChildren()
        attachment = referenced_attachment_point(obj)

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
        from MBDDimension import dimension_display_label, measurement_from_references

        measurement = measurement_from_references(
            obj.DimensionKind,
            obj.MeasurementType,
            obj.ReferenceObject1,
            obj.ReferenceSubelement1,
            obj.ReferenceObject2,
            obj.ReferenceSubelement2
        )
        return {
            "kind": str(obj.DimensionKind),
            "label": dimension_display_label(obj),
            "point1": measurement.get("point1"),
            "point2": measurement.get("point2"),
            "boxed": str(obj.DimensionPurpose) == "Basic",
        }

    from MBDBasicDimension import display_points_from_references

    point1, point2 = display_points_from_references(
        obj.ReferenceObject1,
        obj.ReferenceSubelement1,
        obj.ReferenceObject2,
        obj.ReferenceSubelement2
    )
    return {
        "kind": "Linear",
        "label": FreeCAD.Units.Quantity(
            obj.NominalValue,
            FreeCAD.Units.Length
        ).UserString,
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

        if data["kind"] == "Radius":
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
