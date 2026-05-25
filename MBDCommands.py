# MBDCommands.py

import math

import FreeCAD
import FreeCADGui
import Part
from PySide import QtGui

from MBDBasicDimension import (
    MBDBasicDimension,
    ViewProviderMBDBasicDimension,
    point_from_reference,
    reference_point_for_display,
    measured_value_from_references,
    display_points_from_references,
    surface_from_datum_reference,
    measured_dimension_value,
    update_basic_dimension_signature
)
from MBDDatum import MBDDatumFeature, ViewProviderMBDDatumFeature
import MBDValidation
from MBDDatum import (
    MBDDatumFeature,
    ViewProviderMBDDatumFeature,
    update_geometry_signature
)
import MBDInspector
from MBDPMI import append_pmi_history
from MBDDatumTarget import (
    MBDDatumTarget,
    ViewProviderMBDDatumTarget,
    update_datum_target_signature
)
from MBDDatumSystem import (
    MBDDatumSystem,
    ViewProviderMBDDatumSystem
)
from MBDFeatureControlFrame import (
    MBDFeatureControlFrame,
    ViewProviderMBDFeatureControlFrame
)
import MBDExporter
VALID_DATUM_LETTERS = [
    "A","B","C","D","E","F","G","H",
    "J","K","L","M","N",
    "P","R","S","T","U","V","W","Y"
]

MAX_DISPLAY_OFFSET = 1000.0
TEXT_HEIGHT_FACTOR = 0.12
TEXT_STAGGER_FACTOR = 1.35


def finite_number(value):
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def finite_vector(vector):
    return (
        finite_number(vector.x)
        and finite_number(vector.y)
        and finite_number(vector.z)
    )


def sane_bound_box(bbox):
    values = [
        bbox.XMin, bbox.XMax,
        bbox.YMin, bbox.YMax,
        bbox.ZMin, bbox.ZMax,
        bbox.XLength, bbox.YLength, bbox.ZLength,
    ]

    if not all(finite_number(value) for value in values):
        return False

    if max(bbox.XLength, bbox.YLength, bbox.ZLength) > MAX_DISPLAY_OFFSET:
        return False

    return True

def get_existing_datum_labels(doc):
    labels = set()

    for obj in doc.Objects:
        if hasattr(obj, "IsSemanticPMI") and hasattr(obj, "DatumLabel"):
            labels.add(obj.DatumLabel.strip().upper())

    return labels


def get_next_available_datum_label(doc):

    used = get_existing_datum_labels(doc)

    # Single-letter labels
    for letter in VALID_DATUM_LETTERS:
        if letter not in used:
            return letter

    # Double-letter labels
    for first in VALID_DATUM_LETTERS:
        for second in VALID_DATUM_LETTERS:

            label = first + second

            if label not in used:
                return label

    raise Exception("Ran out of datum labels.")

def get_datum_system_objects(doc):

    systems = []

    for obj in doc.Objects:

        if hasattr(obj, "PrimaryDatum"):
            systems.append(obj)

    return systems


def get_datum_target_objects(doc, datum_obj=None):

    targets = []

    for obj in doc.Objects:
        if not hasattr(obj, "TargetId"):
            continue

        if datum_obj is not None and obj.ParentDatum != datum_obj:
            continue

        targets.append(obj)

    return targets


def get_next_datum_target_id(doc, datum_obj):
    prefix = datum_obj.DatumLabel.strip().upper()
    used = set()

    for target in get_datum_target_objects(doc, datum_obj):
        used.add(target.TargetId.strip().upper())

    index = 1

    while True:
        target_id = "{}{}".format(prefix, index)

        if target_id not in used:
            return target_id

        index += 1


def selection_subelement(selection):
    if selection.SubElementNames:
        return selection.SubElementNames[0]

    return ""


def semantic_datum_for_selection(doc, selection):
    obj = selection.Object
    subelement = selection_subelement(selection)

    if hasattr(obj, "DatumLabel"):
        return obj, ""

    if not subelement:
        return obj, subelement

    for candidate in doc.Objects:
        if not hasattr(candidate, "DatumLabel"):
            continue

        try:
            if (
                candidate.ReferencedObject == obj
                and candidate.ReferencedSubelement == subelement
            ):
                return candidate, ""
        except Exception:
            pass

    return obj, subelement


def document_shape_center_and_size(doc):
    bbox = None

    for obj in doc.Objects:
        try:
            if (
                obj.Name.startswith("MBD_BasicDimension_Display")
                or "_Display" in obj.Name
                or obj.Label.endswith("_Display")
            ):
                continue

            if not hasattr(obj, "Shape") or obj.Shape.isNull():
                continue

            obj_box = obj.Shape.BoundBox

            if not sane_bound_box(obj_box):
                continue

            if bbox is None:
                bbox = obj_box
            else:
                bbox.add(obj_box)
        except Exception:
            pass

    if bbox is None:
        return None, 10.0

    center = FreeCAD.Vector(
        (bbox.XMin + bbox.XMax) * 0.5,
        (bbox.YMin + bbox.YMax) * 0.5,
        (bbox.ZMin + bbox.ZMax) * 0.5
    )
    size = max(bbox.XLength, bbox.YLength, bbox.ZLength, 10.0)
    size = min(size, MAX_DISPLAY_OFFSET)

    return center, size


def display_offset_for_dimension(doc, p1, p2):
    return display_offset_for_dimension_with_preference(doc, p1, p2, None)


def display_offset_for_dimension_with_preference(doc, p1, p2, preferred_offset):
    midpoint = p1 + ((p2 - p1) * 0.5)
    measured_direction = p2 - p1
    doc_center, doc_size = document_shape_center_and_size(doc)
    offset_length = min(max(doc_size * 0.75, 15.0), MAX_DISPLAY_OFFSET * 0.1)
    offset = FreeCAD.Vector(0, 0, offset_length)
    using_preferred_offset = False

    if preferred_offset is not None and finite_vector(preferred_offset):
        offset = FreeCAD.Vector(preferred_offset)
        using_preferred_offset = True
    elif doc_center is not None and finite_vector(doc_center):
        offset = midpoint - doc_center

    if not finite_vector(offset) or offset.Length > MAX_DISPLAY_OFFSET:
        offset = FreeCAD.Vector(0, 0, offset_length)

    if measured_direction.Length > 0 and offset.Length > 0:
        measured_unit = FreeCAD.Vector(measured_direction)
        measured_unit.normalize()
        offset = offset - measured_unit * offset.dot(measured_unit)

    if not finite_vector(offset) or offset.Length > MAX_DISPLAY_OFFSET:
        offset = FreeCAD.Vector(0, 0, offset_length)

    if offset.Length == 0 and measured_direction.Length > 0:
        offset = measured_direction.cross(FreeCAD.Vector(0, 0, 1))

        if offset.Length == 0:
            offset = measured_direction.cross(FreeCAD.Vector(0, 1, 0))

    if offset.Length == 0:
        offset = FreeCAD.Vector(0, 0, offset_length)
    elif using_preferred_offset:
        if offset.Length < offset_length:
            offset.normalize()
            offset.multiply(offset_length)

        if offset.Length > MAX_DISPLAY_OFFSET * 0.25:
            offset.normalize()
            offset.multiply(MAX_DISPLAY_OFFSET * 0.25)
    else:
        offset.normalize()
        offset.multiply(offset_length)

    return offset


def make_basic_dimension_display(
    doc,
    p1,
    p2,
    label,
    preferred_offset=None,
    text_normal=None,
    owner_name="MBD_BasicDimension"
):
    try:
        midpoint = p1 + ((p2 - p1) * 0.5)
        offset = display_offset_for_dimension_with_preference(
            doc,
            p1,
            p2,
            preferred_offset
        )
        measured_direction = p2 - p1

        if measured_direction.Length == 0:
            return None

        p1_display = p1 + offset
        p2_display = p2 + offset
        text_lift = FreeCAD.Vector(0, 0, max(offset.Length * 0.08, 2.0))

        if text_normal is not None and finite_vector(text_normal):
            text_lift = FreeCAD.Vector(text_normal)

            if text_lift.Length > 0:
                text_lift.normalize()
                text_lift.multiply(max(offset.Length * 0.08, 2.0))

        text_point = midpoint + offset + text_lift

        if not finite_vector(p1_display) or not finite_vector(p2_display):
            FreeCAD.Console.PrintWarning(
                "Skipped basic dimension display because display coordinates were invalid.\n"
            )
            return None

        shapes = [
            Part.makePolygon([p1, p1_display, p2_display, p2]),
        ]

        dim = doc.addObject("Part::Feature", owner_name + "_Display")
        dim.Shape = Part.makeCompound(shapes)
        dim.Label = dim.Name

        view_obj = getattr(dim, "ViewObject", None)

        if view_obj is not None:
            for prop, value in [
                ("LineColor", (1.0, 1.0, 1.0)),
                ("PointColor", (1.0, 1.0, 1.0)),
                ("LineWidth", 1.0),
                ("PointSize", 2.0),
            ]:
                if hasattr(view_obj, prop):
                    try:
                        setattr(view_obj, prop, value)
                    except Exception:
                        pass

        text_obj = make_basic_dimension_text(
            text_point,
            label,
            max(offset.Length * 0.12, 3.0),
            text_rotation_for_display_line(p1_display, p2_display, text_normal),
            owner_name + "_Text"
        )
        doc.recompute()
        FreeCAD.Console.PrintMessage(
            "Created basic dimension display {}: "
            "display line ({:.6f}, {:.6f}, {:.6f}) to "
            "({:.6f}, {:.6f}, {:.6f})\n".format(
                dim.Name,
                p1_display.x, p1_display.y, p1_display.z,
                p2_display.x, p2_display.y, p2_display.z
            )
        )
        return dim, text_obj
    except Exception as e:
        FreeCAD.Console.PrintWarning(
            "Could not create basic dimension display: {}\n".format(e)
        )
        return None


def make_basic_dimension_text(point, text, height, rotation=None, object_name="MBD_BasicDimension_Text"):
    try:
        import Draft

        placement = point

        if rotation is not None:
            placement = FreeCAD.Placement(point, rotation)

        text_obj = Draft.make_text(
            text,
            placement=placement,
            screen=False,
            height=height
        )

        if text_obj is None:
            return None

        text_obj.Label = object_name

        view_obj = getattr(text_obj, "ViewObject", None)

        if view_obj is not None:
            for prop, value in [
                ("TextColor", (1.0, 0.0, 0.0)),
                ("LineColor", (1.0, 0.0, 0.0)),
                ("FontSize", height),
            ]:
                if hasattr(view_obj, prop):
                    try:
                        setattr(view_obj, prop, value)
                    except Exception:
                        pass

        FreeCAD.Console.PrintMessage(
            "Created basic dimension text {} at "
            "({:.6f}, {:.6f}, {:.6f}) value {}\n".format(
                text_obj.Name,
                point.x, point.y, point.z,
                text
            )
        )
        return text_obj
    except Exception as e:
        FreeCAD.Console.PrintWarning(
            "Could not create basic dimension text: {}\n".format(e)
        )
        return None


def datum_outward_normal(doc, datum_obj):
    surface = surface_from_datum_reference(datum_obj)
    doc_center, _ = document_shape_center_and_size(doc)

    if surface is None:
        return None

    try:
        u_min, u_max, v_min, v_max = surface.ParameterRange
        normal = surface.normalAt(
            (u_min + u_max) * 0.5,
            (v_min + v_max) * 0.5
        )
    except Exception:
        return None

    if normal.Length == 0:
        return None

    normal.normalize()

    try:
        surface_point = surface.CenterOfMass
    except Exception:
        surface_point = FreeCAD.Vector(0, 0, 0)

    if doc_center is not None and finite_vector(doc_center):
        if (surface_point - doc_center).dot(normal) < 0:
            normal = normal.negative()

    return normal


def text_rotation_for_display_line(p1_display, p2_display, outward_normal):
    if outward_normal is None or not finite_vector(outward_normal):
        return None

    normal = FreeCAD.Vector(outward_normal)

    if normal.Length == 0:
        return None

    normal.normalize()
    x_axis = p2_display - p1_display

    if x_axis.Length == 0:
        return None

    x_axis = x_axis - normal * x_axis.dot(normal)

    if x_axis.Length == 0:
        x_axis = normal.cross(FreeCAD.Vector(0, 0, 1))

        if x_axis.Length == 0:
            x_axis = normal.cross(FreeCAD.Vector(0, 1, 0))

    if x_axis.Length == 0:
        return None

    x_axis.normalize()

    if abs(x_axis.x) >= abs(x_axis.y):
        if x_axis.x < 0:
            x_axis = x_axis.negative()
    elif x_axis.y < 0:
        x_axis = x_axis.negative()

    y_axis = normal.cross(x_axis)

    if y_axis.Length == 0:
        return None

    y_axis.normalize()

    return FreeCAD.Rotation(x_axis, y_axis, normal, "XYZ")


def datum_display_offset(doc, datum_obj, stack_index=0):
    surface = surface_from_datum_reference(datum_obj)
    doc_center, doc_size = document_shape_center_and_size(doc)
    offset_length = min(max(doc_size * 0.75, 15.0), MAX_DISPLAY_OFFSET * 0.1)
    stack_spacing = max(doc_size * 0.12, 3.0)

    if surface is None:
        return None

    try:
        u_min, u_max, v_min, v_max = surface.ParameterRange
        normal = surface.normalAt(
            (u_min + u_max) * 0.5,
            (v_min + v_max) * 0.5
        )
    except Exception:
        return None

    if normal.Length == 0:
        return None

    normal.normalize()

    try:
        surface_point = surface.CenterOfMass
    except Exception:
        surface_point = FreeCAD.Vector(0, 0, 0)

    if doc_center is not None and finite_vector(doc_center):
        if (surface_point - doc_center).dot(normal) < 0:
            normal = normal.negative()

    stack_direction = normal.cross(FreeCAD.Vector(0, 0, 1))

    if stack_direction.Length == 0:
        stack_direction = normal.cross(FreeCAD.Vector(0, 1, 0))

    if stack_direction.Length > 0:
        stack_direction.normalize()
        stack_direction.multiply(stack_spacing * stack_index)
    else:
        stack_direction = FreeCAD.Vector(0, 0, 0)

    return normal * offset_length + stack_direction


def datum_plane_display_offset(doc, datum_obj, p1, p2, stack_index=0):
    normal = datum_outward_normal(doc, datum_obj)
    doc_center, doc_size = document_shape_center_and_size(doc)
    offset_length = min(max(doc_size * 0.75, 15.0), MAX_DISPLAY_OFFSET * 0.1)
    text_height = max(offset_length * TEXT_HEIGHT_FACTOR, 3.0)
    stack_spacing = text_height * TEXT_STAGGER_FACTOR

    if normal is None:
        return None

    midpoint = p1 + ((p2 - p1) * 0.5)
    offset = FreeCAD.Vector(0, 0, 0)

    if doc_center is not None and finite_vector(doc_center):
        offset = midpoint - doc_center
        offset = offset - normal * offset.dot(normal)

    if offset.Length == 0:
        measured_direction = p2 - p1
        offset = normal.cross(measured_direction)

    if offset.Length == 0:
        offset = normal.cross(FreeCAD.Vector(0, 0, 1))

        if offset.Length == 0:
            offset = normal.cross(FreeCAD.Vector(0, 1, 0))

    if offset.Length == 0:
        return None

    offset.normalize()
    offset.multiply(offset_length + (stack_spacing * stack_index))

    return offset


def staggered_offset_from_base(base_offset, stack_index):
    if base_offset is None or not finite_vector(base_offset):
        return None

    offset = FreeCAD.Vector(base_offset)

    if offset.Length == 0:
        return None

    text_height = max(offset.Length * TEXT_HEIGHT_FACTOR, 3.0)
    stagger = text_height * TEXT_STAGGER_FACTOR * stack_index
    direction = FreeCAD.Vector(offset)
    direction.normalize()

    return offset + direction * stagger


def existing_basic_dimension_key(obj):
    refs = [
        (
            obj.ReferenceObject1.Name if obj.ReferenceObject1 else "",
            obj.ReferenceSubelement1,
        ),
        (
            obj.ReferenceObject2.Name if obj.ReferenceObject2 else "",
            obj.ReferenceSubelement2,
        ),
    ]
    refs.sort()
    return tuple(refs)


def basic_dimension_key(ref_obj_1, ref_sub_1, ref_obj_2, ref_sub_2):
    refs = [
        (ref_obj_1.Name if ref_obj_1 else "", ref_sub_1),
        (ref_obj_2.Name if ref_obj_2 else "", ref_sub_2),
    ]
    refs.sort()
    return tuple(refs)


def object_name_exists(doc, name):
    try:
        return doc.getObject(name) is not None
    except Exception:
        return False


def next_basic_dimension_name(doc):
    index = 1

    while True:
        name = "MBD_BasicDimension{:03d}".format(index)

        if not object_name_exists(doc, name):
            return name

        index += 1


def create_basic_dimension_object(
    doc,
    ref_obj_1,
    ref_sub_1,
    ref_obj_2,
    ref_sub_2,
    nominal=None,
    preferred_offset=None,
    text_normal=None,
    dimension_type="Distance"
):
    measured = measured_value_from_references(
        dimension_type,
        ref_obj_1,
        ref_sub_1,
        ref_obj_2,
        ref_sub_2
    )

    if measured is None:
        return None

    if nominal is None:
        nominal = measured

    dimension_name = next_basic_dimension_name(doc)
    dim_obj = doc.addObject(
        "App::DocumentObjectGroupPython",
        dimension_name
    )

    MBDBasicDimension(dim_obj)
    dim_obj.Label = dim_obj.Name
    dim_obj.DimensionType = str(dimension_type)
    dim_obj.NominalValue = nominal
    dim_obj.ReferenceObject1 = ref_obj_1
    dim_obj.ReferenceSubelement1 = ref_sub_1
    dim_obj.ReferenceObject2 = ref_obj_2
    dim_obj.ReferenceSubelement2 = ref_sub_2
    update_basic_dimension_signature(dim_obj)
    append_pmi_history(dim_obj, "basic-dimension-attached")

    display_label = "[{}]".format(
        FreeCAD.Units.Quantity(
            nominal,
            FreeCAD.Units.Length
        ).UserString
    )

    if FreeCAD.GuiUp:
        if not hasattr(dim_obj, "addObject"):
            ViewProviderMBDBasicDimension(dim_obj.ViewObject)

        p1, p2 = display_points_from_references(
            ref_obj_1,
            ref_sub_1,
            ref_obj_2,
            ref_sub_2
        )

        if p1 is not None and p2 is not None:
            FreeCAD.Console.PrintMessage(
                "Basic dimension display endpoints: "
                "({:.6f}, {:.6f}, {:.6f}) to "
                "({:.6f}, {:.6f}, {:.6f})\n".format(
                    p1.x, p1.y, p1.z,
                    p2.x, p2.y, p2.z
                )
            )
            display_objects = make_basic_dimension_display(
                doc,
                p1,
                p2,
                display_label,
                preferred_offset,
                text_normal,
                dim_obj.Name
            )

            if display_objects is not None:
                display_geometry, display_text = display_objects
                dim_obj.DisplayDimension = display_geometry
                dim_obj.DisplayText = display_text

                try:
                    if display_geometry is not None:
                        dim_obj.addObject(display_geometry)
                        display_geometry.Label = display_geometry.Name

                    if display_text is not None:
                        dim_obj.addObject(display_text)
                        display_text.Label = dim_obj.Name + "_Text"
                except Exception:
                    pass

                dim_obj.Label = dim_obj.Name

    return dim_obj


def target_parent_datum_for_references(ref_obj_1, ref_obj_2):
    if hasattr(ref_obj_1, "ParentDatum") and ref_obj_1.ParentDatum is not None:
        return ref_obj_1.ParentDatum

    if hasattr(ref_obj_2, "ParentDatum") and ref_obj_2.ParentDatum is not None:
        return ref_obj_2.ParentDatum

    return None


class CreateDatumFeatureCommand:
    def GetResources(self):
        return {
            "MenuText": "Create Datum Feature",
            "ToolTip": "Create a semantic MBD datum feature from selected geometry",
            "Pixmap": ""
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        sel = FreeCADGui.Selection.getSelectionEx()

        if len(sel) != 1:
            QtGui.QMessageBox.warning(
                None,
                "MBD Datum Feature",
                "Select exactly one face, edge, or vertex."
            )
            return

        selection = sel[0]

        if not selection.SubElementNames:
            QtGui.QMessageBox.warning(
                None,
                "MBD Datum Feature",
                "Select a subelement such as a face, edge, or vertex."
            )
            return

        ref_obj = selection.Object
        ref_sub = selection.SubElementNames[0]

        used_labels = get_existing_datum_labels(doc)
        suggested_label = get_next_available_datum_label(doc)

        while True:
            label, ok = QtGui.QInputDialog.getText(
                None,
                "Datum Label",
                "Enter datum label:",
                text=suggested_label
            )

            if not ok:
                return

            label = str(label).strip().upper()

            if not label:
                QtGui.QMessageBox.warning(
                    None,
                    "MBD Datum Feature",
                    "Datum label cannot be blank."
                )
                continue

            if label in used_labels:
                QtGui.QMessageBox.warning(
                    None,
                    "MBD Datum Feature",
                    "Datum label {} is already used. Choose another label.".format(label)
                )
                continue

            break

        label = str(label).strip().upper()

        datum_obj = doc.addObject("App::FeaturePython", "MBD_DatumFeature_" + label)
        MBDDatumFeature(datum_obj)

        datum_obj.DatumLabel = label
        datum_obj.ReferencedObject = ref_obj
        datum_obj.ReferencedSubelement = ref_sub
        update_geometry_signature(datum_obj)
        append_pmi_history(datum_obj, "datum-attached")
        
        if ref_sub.startswith("Face"):
            datum_obj.DatumType = "Plane"
        elif ref_sub.startswith("Edge"):
            datum_obj.DatumType = "Axis"
        elif ref_sub.startswith("Vertex"):
            datum_obj.DatumType = "Point"
        else:
            datum_obj.DatumType = "Feature"

        if FreeCAD.GuiUp:
            ViewProviderMBDDatumFeature(datum_obj.ViewObject)

        doc.recompute()

        FreeCAD.Console.PrintMessage(
            "Created MBD datum feature {} attached to {}.{}\n".format(
                label,
                ref_obj.Name,
                ref_sub
            )
        )


class ValidatePMICommand:
    def GetResources(self):
        return {
            "MenuText": "Validate PMI",
            "ToolTip": "Validate semantic MBD PMI objects",
            "Pixmap": ""
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        report = MBDValidation.validate_document(FreeCAD.ActiveDocument)

        QtGui.QMessageBox.information(
            None,
            "MBD Validation Report",
            report
        )

class ShowPMIInspectorCommand:

    def GetResources(self):
        return {
            "MenuText": "Show PMI Inspector",
            "ToolTip": "Show semantic PMI inspector",
            "Pixmap": ""
        }

    def IsActive(self):
        return True

    def Activated(self):
        MBDInspector.show_inspector()


class CreateDatumTargetCommand:

    def GetResources(self):
        return {
            "MenuText": "Create Datum Target",
            "ToolTip": "Create a semantic datum target from a datum and construction point",
            "Pixmap": ""
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        selection = FreeCADGui.Selection.getSelectionEx()

        if len(selection) != 2:
            QtGui.QMessageBox.warning(
                None,
                "Datum Target",
                "Select one MBD datum feature and one construction point."
            )
            return

        parent_datum = None
        construction_selection = None

        for item in selection:
            if hasattr(item.Object, "DatumLabel"):
                parent_datum = item.Object
            else:
                construction_selection = item

        if parent_datum is None or construction_selection is None:
            QtGui.QMessageBox.warning(
                None,
                "Datum Target",
                "Selection must include one MBD datum feature and one construction point."
            )
            return

        if parent_datum.ReferencedObject is None or not parent_datum.ReferencedSubelement:
            QtGui.QMessageBox.warning(
                None,
                "Datum Target",
                "The parent datum must be attached to an inspected face."
            )
            return

        suggested_id = get_next_datum_target_id(doc, parent_datum)

        target_id, ok = QtGui.QInputDialog.getText(
            None,
            "Datum Target",
            "Enter datum target ID:",
            text=suggested_id
        )

        if not ok:
            return

        target_id = str(target_id).strip().upper()

        if not target_id:
            QtGui.QMessageBox.warning(
                None,
                "Datum Target",
                "Datum target ID cannot be blank."
            )
            return

        target_obj = doc.addObject(
            "App::FeaturePython",
            "MBD_DatumTarget_" + target_id
        )

        MBDDatumTarget(target_obj)

        target_obj.TargetId = target_id
        target_obj.TargetType = "Point"
        target_obj.ParentDatum = parent_datum
        target_obj.ConstructionObject = construction_selection.Object

        if construction_selection.SubElementNames:
            target_obj.ConstructionSubelement = construction_selection.SubElementNames[0]

        target_obj.ReferencedObject = parent_datum.ReferencedObject
        target_obj.ReferencedSubelement = parent_datum.ReferencedSubelement

        update_datum_target_signature(target_obj)
        append_pmi_history(target_obj, "datum-target-attached")

        if FreeCAD.GuiUp:
            ViewProviderMBDDatumTarget(target_obj.ViewObject)

        doc.recompute()

        FreeCAD.Console.PrintMessage(
            "Created datum target {} for datum {} using {}\n".format(
                target_id,
                parent_datum.DatumLabel,
                construction_selection.Object.Name
            )
        )


class CreateBasicDimensionCommand:

    def GetResources(self):
        return {
            "MenuText": "Create Basic Dimension",
            "ToolTip": "Create a semantic basic dimension between two point-like references",
            "Pixmap": ""
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        selection = FreeCADGui.Selection.getSelectionEx()

        if len(selection) != 2:
            QtGui.QMessageBox.warning(
                None,
                "Basic Dimension",
                "Select exactly two point-like references."
            )
            return

        ref1 = selection[0]
        ref2 = selection[1]
        ref_obj_1, sub1 = semantic_datum_for_selection(doc, ref1)
        ref_obj_2, sub2 = semantic_datum_for_selection(doc, ref2)

        dim_type, ok = QtGui.QInputDialog.getItem(
            None,
            "Basic Dimension",
            "Dimension type:",
            ["Distance", "X", "Y", "Z"],
            0,
            False
        )

        if not ok:
            return

        measured = measured_value_from_references(
            dim_type,
            ref_obj_1,
            sub1,
            ref_obj_2,
            sub2
        )

        if measured is None:
            QtGui.QMessageBox.warning(
                None,
                "Basic Dimension",
                "References must be point-to-point or datum-to-point."
            )
            return

        measured_text = FreeCAD.Units.Quantity(
            measured,
            FreeCAD.Units.Length
        ).UserString

        nominal_text, ok = QtGui.QInputDialog.getText(
            None,
            "Basic Dimension",
            "Nominal value:",
            text=measured_text
        )

        if not ok:
            return

        try:
            nominal = FreeCAD.Units.Quantity(str(nominal_text)).Value
        except Exception:
            QtGui.QMessageBox.warning(
                None,
                "Basic Dimension",
                "Enter a length value such as 1.250 in or 31.75 mm."
            )
            return

        preferred_offset = None
        text_normal = None
        target_parent_datum = target_parent_datum_for_references(
            ref_obj_1,
            ref_obj_2
        )

        if target_parent_datum is not None:
            p1, p2 = display_points_from_references(
                ref_obj_1,
                sub1,
                ref_obj_2,
                sub2
            )

            if p1 is not None and p2 is not None:
                preferred_offset = datum_plane_display_offset(
                    doc,
                    target_parent_datum,
                    p1,
                    p2,
                    0
                )
                text_normal = datum_outward_normal(doc, target_parent_datum)

        dim_obj = create_basic_dimension_object(
            doc,
            ref_obj_1,
            sub1,
            ref_obj_2,
            sub2,
            nominal,
            preferred_offset=preferred_offset,
            text_normal=text_normal,
            dimension_type=str(dim_type)
        )

        if dim_obj is None:
            QtGui.QMessageBox.warning(
                None,
                "Basic Dimension",
                "Could not create the basic dimension."
            )
            return

        doc.recompute()

        FreeCAD.Console.PrintMessage(
            "Created basic dimension {} between {} and {}\n".format(
                dim_obj.Name,
                ref_obj_1.Name,
                ref_obj_2.Name
            )
        )


class CreateTargetBasicDimensionsCommand:

    def GetResources(self):
        return {
            "MenuText": "Create Target Basic Dimensions",
            "ToolTip": "Create basic dimensions from datum targets to the other datums in a selected datum system",
            "Pixmap": ""
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        selection = FreeCADGui.Selection.getSelection()

        if len(selection) != 1 or not hasattr(selection[0], "PrimaryDatum"):
            QtGui.QMessageBox.warning(
                None,
                "Target Basic Dimensions",
                "Select exactly one MBD datum system."
            )
            return

        datum_system = selection[0]
        datums = [
            datum_system.PrimaryDatum,
            datum_system.SecondaryDatum,
            datum_system.TertiaryDatum,
        ]
        datums = [datum for datum in datums if datum is not None]

        if len(datums) < 2:
            QtGui.QMessageBox.warning(
                None,
                "Target Basic Dimensions",
                "The selected datum system must contain at least two datums."
            )
            return

        existing_keys = set()

        for obj in doc.Objects:
            if hasattr(obj, "DimensionType") and hasattr(obj, "ReferenceObject1"):
                existing_keys.add(existing_basic_dimension_key(obj))

        stack_counts = {}
        stack_base_offsets = {}
        created = 0
        skipped = 0
        failed = 0

        for target_datum in datums:
            targets = get_datum_target_objects(doc, target_datum)

            for target in targets:
                for reference_datum in datums:
                    if reference_datum == target_datum:
                        continue

                    key = basic_dimension_key(target, "", reference_datum, "")

                    if key in existing_keys:
                        skipped += 1
                        continue

                    p1, p2 = display_points_from_references(
                        target,
                        "",
                        reference_datum,
                        ""
                    )

                    if p1 is None or p2 is None:
                        failed += 1
                        continue

                    stack_key = (target_datum.Name, reference_datum.Name)
                    stack_index = stack_counts.get(stack_key, 0)

                    if stack_key not in stack_base_offsets:
                        stack_base_offsets[stack_key] = datum_plane_display_offset(
                            doc,
                            target_datum,
                            p1,
                            p2,
                            0
                        )

                    preferred_offset = staggered_offset_from_base(
                        stack_base_offsets[stack_key],
                        stack_index
                    )
                    text_normal = datum_outward_normal(doc, target_datum)

                    dim_obj = create_basic_dimension_object(
                        doc,
                        target,
                        "",
                        reference_datum,
                        "",
                        preferred_offset=preferred_offset,
                        text_normal=text_normal
                    )

                    if dim_obj is None:
                        failed += 1
                        continue

                    existing_keys.add(key)
                    stack_counts[stack_key] = stack_index + 1
                    created += 1

        doc.recompute()

        message = (
            "Created {} target basic dimensions. "
            "Skipped {} existing dimensions. "
            "Failed {} dimensions."
        ).format(created, skipped, failed)

        FreeCAD.Console.PrintMessage(message + "\n")

        if FreeCAD.GuiUp:
            QtGui.QMessageBox.information(
                None,
                "Target Basic Dimensions",
                message
            )


class CreateDatumSystemCommand:

    def GetResources(self):
        return {
            "MenuText": "Create Datum System",
            "ToolTip": "Create a semantic datum system from selected datum features",
            "Pixmap": ""
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):

        doc = FreeCAD.ActiveDocument

        selection = FreeCADGui.Selection.getSelection()

        if len(selection) < 1 or len(selection) > 3:

            QtGui.QMessageBox.warning(
                None,
                "Datum System",
                "Select 1 to 3 datum features in precedence order."
            )

            return

        datum_objects = []

        for obj in selection:

            if not hasattr(obj, "IsSemanticPMI"):

                QtGui.QMessageBox.warning(
                    None,
                    "Datum System",
                    "{} is not semantic PMI.".format(obj.Name)
                )

                return

            if not hasattr(obj, "DatumLabel"):

                QtGui.QMessageBox.warning(
                    None,
                    "Datum System",
                    "{} is not a datum feature.".format(obj.Name)
                )

                return

            datum_objects.append(obj)

        labels = [obj.DatumLabel for obj in datum_objects]

        if len(labels) != len(set(labels)):

            QtGui.QMessageBox.warning(
                None,
                "Datum System",
                "Duplicate datums are not allowed in a datum system."
            )

            return

        name = "MBD_DatumSystem"

        if len(labels) > 0:
            name += "_" + "_".join(labels)

        ds_obj = doc.addObject(
            "App::FeaturePython",
            name
        )

        MBDDatumSystem(ds_obj)

        if len(datum_objects) >= 1:
            ds_obj.PrimaryDatum = datum_objects[0]

        if len(datum_objects) >= 2:
            ds_obj.SecondaryDatum = datum_objects[1]

        if len(datum_objects) >= 3:
            ds_obj.TertiaryDatum = datum_objects[2]

        if FreeCAD.GuiUp:
            ViewProviderMBDDatumSystem(ds_obj.ViewObject)

        doc.recompute()

        FreeCAD.Console.PrintMessage(
            "Created datum system: {}\n".format(
                " | ".join(labels)
            )
        )

class CreateFeatureControlFrameCommand:

    def GetResources(self):
        return {
            "MenuText": "Create Feature Control Frame",
            "ToolTip": "Create semantic feature control frame",
            "Pixmap": ""
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):

        doc = FreeCAD.ActiveDocument

        sel = FreeCADGui.Selection.getSelectionEx()

        if len(sel) != 1:

            QtGui.QMessageBox.warning(
                None,
                "Feature Control Frame",
                "Select exactly one controlled feature."
            )

            return

        selection = sel[0]

        if not selection.SubElementNames:

            QtGui.QMessageBox.warning(
                None,
                "Feature Control Frame",
                "Select a subelement such as a face or edge."
            )

            return

        controlled_obj = selection.Object
        controlled_sub = selection.SubElementNames[0]

        datum_systems = get_datum_system_objects(doc)

        if not datum_systems:

            QtGui.QMessageBox.warning(
                None,
                "Feature Control Frame",
                "No datum systems exist."
            )

            return

        tolerance, ok = QtGui.QInputDialog.getDouble(
            None,
            "Tolerance Value",
            "Enter tolerance value:",
            0.1,
            0.0001,
            9999,
            4
        )

        if not ok:
            return

        names = [obj.Name for obj in datum_systems]

        ds_name, ok = QtGui.QInputDialog.getItem(
            None,
            "Datum System",
            "Select datum system:",
            names,
            0,
            False
        )

        if not ok:
            return

        datum_system = doc.getObject(ds_name)

        fcf_obj = doc.addObject(
            "App::FeaturePython",
            "MBD_FCF_Position"
        )

        MBDFeatureControlFrame(fcf_obj)

        fcf_obj.ToleranceType = "Position"
        fcf_obj.ToleranceValue = tolerance

        fcf_obj.DatumSystem = datum_system

        fcf_obj.ControlledObject = controlled_obj
        fcf_obj.ControlledSubelement = controlled_sub
        fcf_obj.ReferencedObject = controlled_obj
        fcf_obj.ReferencedSubelement = controlled_sub
        update_geometry_signature(fcf_obj)
        append_pmi_history(fcf_obj, "fcf-attached")

        if FreeCAD.GuiUp:
            ViewProviderMBDFeatureControlFrame(
                fcf_obj.ViewObject
            )

        doc.recompute()

        FreeCAD.Console.PrintMessage(
            "Created position tolerance on {}.{}\n".format(
                controlled_obj.Name,
                controlled_sub
            )
        )
class ExportAP242Command:

    def GetResources(self):
        return {
            "MenuText": "Export AP242",
            "ToolTip": "Export AP242 STEP with semantic infrastructure",
            "Pixmap": ""
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):

        filename, _ = QtGui.QFileDialog.getSaveFileName(
            None,
            "Export AP242",
            "",
            "STEP Files (*.step *.stp)"
        )

        if not filename:
            return

        try:

            MBDExporter.export_ap242(filename)

            QtGui.QMessageBox.information(
                None,
                "AP242 Export",
                "Export complete."
            )

        except Exception as e:

            QtGui.QMessageBox.critical(
                None,
                "AP242 Export Failed",
                str(e)
            )

if hasattr(FreeCADGui, "addCommand"):
    FreeCADGui.addCommand("MBD_CreateDatumFeature", CreateDatumFeatureCommand())
    FreeCADGui.addCommand("MBD_ValidatePMI", ValidatePMICommand())
    FreeCADGui.addCommand(
        "MBD_ShowPMIInspector",
        ShowPMIInspectorCommand()
    )
    FreeCADGui.addCommand(
        "MBD_CreateDatumTarget",
        CreateDatumTargetCommand()
    )
    FreeCADGui.addCommand(
        "MBD_CreateBasicDimension",
        CreateBasicDimensionCommand()
    )
    FreeCADGui.addCommand(
        "MBD_CreateTargetBasicDimensions",
        CreateTargetBasicDimensionsCommand()
    )
    FreeCADGui.addCommand(
        "MBD_CreateDatumSystem",
        CreateDatumSystemCommand()
    )
    FreeCADGui.addCommand(
        "MBD_CreateFeatureControlFrame",
        CreateFeatureControlFrameCommand()
    )
    FreeCADGui.addCommand(
        "MBD_ExportAP242",
        ExportAP242Command()
    )
