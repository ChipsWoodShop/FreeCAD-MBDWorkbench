#!/usr/bin/env python3

import argparse
import os
import sys


WORKBENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKBENCH_DIR)

import FreeCAD
import Part
from pivy import coin
from PySide import QtCore

import MBDExporter
import MBDBasicDimension
import MBDDimension
import MBDDatumTarget
import MBDValidation
from MBDDatum import MBDDatumFeature, update_geometry_signature
from MBDDatumSystem import (
    MBDDatumSystem,
    datum_system_label,
    datum_system_object_label,
    synchronize_datum_system_label,
)
from MBDFeatureControlFrame import MBDFeatureControlFrame
from MBDPMI import (
    migrate_semantic_pmi_global_links,
    update_pmi_display_layout,
)
from MBDViewProvider import (
    ViewProviderSingleItemFCF,
    ViewProviderSingleItemDatumFeature,
    ViewProviderSingleItemDatumTarget,
    ViewProviderSingleItemDimension,
    annotation_basis,
    dragged_annotation_origin,
    fcf_attachment_point,
    fcf_cells as view_provider_fcf_cells,
    fcf_leader_segments,
    symbol_segments,
)


class AcceptMessageBox:
    Warning = 1
    Yes = 1
    Cancel = 2

    def setIcon(self, *args):
        pass

    def setWindowTitle(self, *args):
        pass

    def setText(self, *args):
        pass

    def setInformativeText(self, *args):
        pass

    def setStandardButtons(self, *args):
        pass

    def exec_(self):
        return self.Yes


class CancelMessageBox(AcceptMessageBox):
    def exec_(self):
        return self.Cancel


def make_doc(name):
    doc = FreeCAD.newDocument(name)
    box_obj = doc.addObject("Part::Feature", "SmokeBox")
    box_obj.Shape = Part.makeBox(10, 20, 30)
    doc.recompute()
    return doc, box_obj


def make_datum(doc, box_obj, label, subelement):
    obj = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_DatumFeature_" + label
    )
    MBDDatumFeature(obj)
    obj.DatumLabel = label
    obj.ReferencedObject = box_obj
    obj.ReferencedSubelement = subelement
    update_geometry_signature(obj)
    return obj


def make_datum_set(doc, box_obj):
    datum_a = make_datum(doc, box_obj, "A", "Face1")
    datum_b = make_datum(doc, box_obj, "B", "Face3")
    datum_c = make_datum(doc, box_obj, "C", "Face5")

    datum_system = doc.addObject("App::FeaturePython", "MBD_DatumSystem_A_B_C")
    MBDDatumSystem(datum_system)
    datum_system.PrimaryDatums = [datum_a]
    datum_system.SecondaryDatums = [datum_b]
    datum_system.TertiaryDatums = [datum_c]

    return datum_a, datum_b, datum_c, datum_system


def add_position_fcf(doc, box_obj, datum_system, diameter_zone, controlled_subelement):
    fcf = doc.addObject("App::FeaturePython", "MBD_FCF_Position")
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Position"
    fcf.ToleranceValue = 0.01
    fcf.DiameterZone = diameter_zone
    fcf.DatumSystem = datum_system
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = controlled_subelement
    fcf.ReferencedObject = box_obj
    fcf.ReferencedSubelement = controlled_subelement
    update_geometry_signature(fcf)
    return fcf


def add_export_fcf(
    doc,
    box_obj,
    tolerance_type,
    controlled_subelement,
    datum_system=None,
    datum_reference=None,
    profile_all_over=False
):
    fcf = doc.addObject("App::FeaturePython", "MBD_FCF_" + tolerance_type)
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = tolerance_type
    fcf.ToleranceValue = 0.01
    fcf.DiameterZone = tolerance_type == "Position"
    fcf.ProfileAllOver = profile_all_over
    fcf.DatumSystem = datum_system
    fcf.DatumReference = datum_reference
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = controlled_subelement
    fcf.ReferencedObject = box_obj
    fcf.ReferencedSubelement = controlled_subelement

    if controlled_subelement:
        update_geometry_signature(fcf)

    return fcf


def export_smoke(mode, output_path, controlled_subelement):
    MBDExporter.QtGui.QMessageBox = AcceptMessageBox

    doc, box_obj = make_doc("MBDHeadlessSmoke")
    datum_a, _, _, datum_system = make_datum_set(doc, box_obj)

    if mode == "fcf-no-diameter":
        add_position_fcf(doc, box_obj, datum_system, False, controlled_subelement)
    elif mode == "fcf-diameter":
        add_position_fcf(doc, box_obj, datum_system, True, controlled_subelement)
    elif mode == "all-fcfs":
        add_export_fcf(
            doc,
            box_obj,
            "Position",
            controlled_subelement,
            datum_system=datum_system
        )
        add_export_fcf(doc, box_obj, "Flatness", "Face1")
        add_export_fcf(
            doc,
            box_obj,
            "Parallelism",
            "Face3",
            datum_reference=datum_a
        )
        add_export_fcf(
            doc,
            box_obj,
            "Perpendicularity",
            "Face5",
            datum_reference=datum_a
        )
        add_export_fcf(
            doc,
            box_obj,
            "Profile",
            "",
            datum_system=datum_system,
            profile_all_over=True
        )
        add_export_fcf(
            doc,
            box_obj,
            "LineProfile",
            "Edge1",
            datum_system=datum_system
        )
        add_export_fcf(
            doc,
            box_obj,
            "Angularity",
            "Face1",
            datum_reference=datum_a
        )
        add_export_fcf(doc, box_obj, "Straightness", "Face3")
        add_export_fcf(doc, box_obj, "Circularity", "Face5")
        add_export_fcf(doc, box_obj, "Cylindricity", "Face1")
        add_export_fcf(
            doc,
            box_obj,
            "CircularRunout",
            "Face3",
            datum_reference=datum_a
        )
        add_export_fcf(
            doc,
            box_obj,
            "TotalRunout",
            "Face5",
            datum_reference=datum_a
        )

    doc.recompute()

    if os.path.exists(output_path):
        os.remove(output_path)

    result = MBDExporter.export_ap242(output_path)
    exists = os.path.exists(output_path)
    size = os.path.getsize(output_path) if exists else 0
    FreeCAD.closeDocument(doc.Name)

    if result is not True:
        raise AssertionError("export_ap242 returned {}".format(result))

    if not exists or size <= 0:
        raise AssertionError("export did not create a non-empty STEP file")

    print("headless smoke export passed:", mode, output_path, size)


def stale_cancel_smoke(output_path):
    MBDExporter.QtGui.QMessageBox = CancelMessageBox

    doc, box_obj = make_doc("MBDHeadlessCancelSmoke")
    datum_a, _, _, _ = make_datum_set(doc, box_obj)

    datum_a.GeometrySignature = (
        '{"CenterOfMass": [999, 999, 999], "Area": 1, "GeometryType": "Plane"}'
    )
    doc.recompute()

    if os.path.exists(output_path):
        os.remove(output_path)

    result = MBDExporter.export_ap242(output_path)
    exists = os.path.exists(output_path)
    FreeCAD.closeDocument(doc.Name)

    if result is not None:
        raise AssertionError("cancelled export returned {}".format(result))

    if exists:
        raise AssertionError("cancelled export wrote {}".format(output_path))

    print("stale attachment cancellation passed")


def dimension_export_smoke(output_path):
    MBDExporter.QtGui.QMessageBox = AcceptMessageBox

    doc, box_obj = make_doc("MBDDimensionExportSmoke")
    _datum_a, _datum_b, _datum_c, datum_system = make_datum_set(doc, box_obj)
    add_position_fcf(doc, box_obj, datum_system, False, "Face1")

    diameter_dim = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_Dimension_Diameter"
    )
    MBDDimension.MBDDimension(diameter_dim)
    diameter_dim.DimensionPurpose = "EqualBilateral"
    diameter_dim.DimensionKind = "Diameter"
    diameter_dim.MeasurementType = "Distance"
    diameter_dim.NominalValue = 10.0
    diameter_dim.UpperTolerance = 0.1
    diameter_dim.LowerTolerance = 0.1
    diameter_dim.ReferenceObject1 = box_obj
    diameter_dim.ReferenceSubelement1 = "Face3"
    MBDDimension.update_dimension_signature(diameter_dim)

    radius_dim = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_Dimension_Radius"
    )
    MBDDimension.MBDDimension(radius_dim)
    radius_dim.DimensionPurpose = "UnequalBilateral"
    radius_dim.DimensionKind = "Radius"
    radius_dim.MeasurementType = "Distance"
    radius_dim.NominalValue = 5.0
    radius_dim.UpperTolerance = 0.2
    radius_dim.LowerTolerance = 0.1
    radius_dim.ReferenceObject1 = box_obj
    radius_dim.ReferenceSubelement1 = "Face3"
    MBDDimension.update_dimension_signature(radius_dim)

    limits_dim = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_Dimension_Limits"
    )
    MBDDimension.MBDDimension(limits_dim)
    limits_dim.DimensionPurpose = "Limits"
    limits_dim.DimensionKind = "Diameter"
    limits_dim.MeasurementType = "Distance"
    limits_dim.NominalValue = 10.0
    limits_dim.LowerLimit = 9.9
    limits_dim.UpperLimit = 10.1
    limits_dim.ReferenceObject1 = box_obj
    limits_dim.ReferenceSubelement1 = "Face3"
    MBDDimension.update_dimension_signature(limits_dim)

    linear_dim = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_Dimension_Linear"
    )
    MBDDimension.MBDDimension(linear_dim)
    linear_dim.DimensionPurpose = "EqualBilateral"
    linear_dim.DimensionKind = "Linear"
    linear_dim.MeasurementType = "Distance"
    linear_dim.NominalValue = 10.0
    linear_dim.UpperTolerance = 0.1
    linear_dim.LowerTolerance = 0.1
    linear_dim.ReferencePattern = "PlaneToPlane"
    linear_dim.ReferenceObject1 = box_obj
    linear_dim.ReferenceSubelement1 = "Face1"
    linear_dim.ReferenceObject2 = box_obj
    linear_dim.ReferenceSubelement2 = "Face2"
    MBDDimension.update_dimension_signature(linear_dim)

    location_dim = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_Dimension_Location"
    )
    MBDDimension.MBDDimension(location_dim)
    location_dim.DimensionPurpose = "EqualBilateral"
    location_dim.DimensionKind = "Linear"
    location_dim.MeasurementType = "X"
    location_dim.ReferencePattern = "PlaneToPoint"
    location_dim.NominalValue = 20.0
    location_dim.UpperTolerance = 0.1
    location_dim.LowerTolerance = 0.1
    location_dim.ReferenceObject1 = box_obj
    location_dim.ReferenceSubelement1 = "Face1"
    location_dim.ReferenceObject2 = box_obj
    location_dim.ReferenceSubelement2 = "Face4"
    MBDDimension.update_dimension_signature(location_dim)

    doc.recompute()

    if os.path.exists(output_path):
        os.remove(output_path)

    result = MBDExporter.export_ap242(output_path)
    exists = os.path.exists(output_path)
    size = os.path.getsize(output_path) if exists else 0
    FreeCAD.closeDocument(doc.Name)

    if result is not True:
        raise AssertionError("dimension export returned {}".format(result))

    if not exists or size <= 0:
        raise AssertionError("dimension export did not create a non-empty STEP file")

    print("semantic dimension export passed:", output_path, size)


def datum_target_export_smoke(output_path):
    MBDExporter.QtGui.QMessageBox = AcceptMessageBox

    doc, box_obj = make_doc("MBDDatumTargetExportSmoke")
    datum_a, _datum_b, _datum_c, datum_system = make_datum_set(doc, box_obj)
    add_position_fcf(doc, box_obj, datum_system, False, "Face1")

    point = doc.addObject("Part::Feature", "DatumTargetPointA1")
    point.Shape = Part.Vertex(0, 10, 15)
    doc.recompute()

    target = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_DatumTarget_A1"
    )
    MBDDatumTarget.MBDDatumTarget(target)
    target.TargetId = "A1"
    target.TargetType = "Point"
    target.ParentDatum = datum_a
    target.ConstructionObject = point
    target.ReferencedObject = box_obj
    target.ReferencedSubelement = "Face1"
    MBDDatumTarget.update_datum_target_signature(target)

    doc.recompute()

    if os.path.exists(output_path):
        os.remove(output_path)

    result = MBDExporter.export_ap242(output_path)
    exists = os.path.exists(output_path)
    size = os.path.getsize(output_path) if exists else 0
    FreeCAD.closeDocument(doc.Name)

    if result is not True:
        raise AssertionError("datum target export returned {}".format(result))

    if not exists or size <= 0:
        raise AssertionError("datum target export did not create a non-empty STEP file")

    print("semantic datum target export passed:", output_path, size)


def datum_target_sufficiency_smoke():
    doc, box_obj = make_doc("MBDDatumTargetSufficiencySmoke")
    datum_a, datum_b, _datum_c, _datum_system = make_datum_set(doc, box_obj)

    def add_target(datum, target_id, point):
        construction = doc.addObject(
            "Part::Feature",
            "Construction_" + target_id
        )
        construction.Shape = Part.Vertex(point)
        target = doc.addObject(
            "App::DocumentObjectGroupPython",
            "MBD_DatumTarget_" + target_id
        )
        MBDDatumTarget.MBDDatumTarget(target)
        target.TargetId = target_id
        target.TargetType = "Point"
        target.ParentDatum = datum
        target.ConstructionObject = construction
        target.ReferencedObject = box_obj
        target.ReferencedSubelement = datum.ReferencedSubelement
        target.SurfaceTolerance = 999.0
        MBDDatumTarget.update_datum_target_signature(target)
        return target

    def messages():
        report = MBDValidation.validate_document_structured(doc)
        return [issue.message for issue in report["issues"]]

    add_target(datum_a, "A1", FreeCAD.Vector(0, 0, 0))
    add_target(datum_a, "A2", FreeCAD.Vector(0, 10, 0))
    underdefined_primary = messages()

    if not any("primary datum A" in message for message in underdefined_primary):
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError("underdefined primary datum targets were not rejected")

    add_target(datum_a, "A3", FreeCAD.Vector(0, 20, 0))
    primary_complete = messages()

    if any("primary datum A" in message for message in primary_complete):
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError("three primary datum targets did not clear validation")

    add_target(datum_b, "B1", FreeCAD.Vector(10, 0, 0))
    underdefined_secondary = messages()

    if not any("secondary datum B" in message for message in underdefined_secondary):
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError("underdefined secondary datum targets were not rejected")

    add_target(datum_b, "B2", FreeCAD.Vector(10, 20, 0))
    secondary_complete = messages()
    FreeCAD.closeDocument(doc.Name)

    if any("secondary datum B" in message for message in secondary_complete):
        raise AssertionError("two secondary datum targets did not clear validation")

    FreeCAD.Console.PrintMessage(
        "datum target sufficiency validation passed\n"
    )


def common_datum_system_validation_smoke():
    import MBDCommands

    doc, box_obj = make_doc("MBDCommonDatumSystemValidationSmoke")
    datum_a = make_datum(doc, box_obj, "A", "Face1")
    datum_b = make_datum(doc, box_obj, "B", "Face3")
    datum_c = make_datum(doc, box_obj, "C", "Face5")

    datum_system = doc.addObject(
        "App::FeaturePython",
        "MBD_DatumSystem_A_B__C"
    )
    MBDDatumSystem(datum_system)
    datum_system.PrimaryDatums = [datum_a, datum_b]
    datum_system.SecondaryDatums = [datum_c]
    datum_system.TertiaryDatums = []

    if datum_system_object_label(datum_system) != "MBD_DatumSystem_A-B_C":
        raise AssertionError(
            "unexpected datum system object label {}".format(
                datum_system_object_label(datum_system)
            )
        )

    datum_system.Label = datum_system.Name

    if not synchronize_datum_system_label(datum_system):
        raise AssertionError("sanitized datum system label was not synchronized")

    if datum_system.Label != "MBD_DatumSystem_A-B_C":
        raise AssertionError(
            "synchronized datum system label was {}".format(
                datum_system.Label
            )
        )

    if datum_system_label(datum_system) != "A-B | C":
        raise AssertionError(
            "unexpected common datum label {}".format(
                datum_system_label(datum_system)
            )
        )

    if MBDValidation.attachment_text(datum_system) != "A-B | C":
        raise AssertionError(
            "datum system inspector text was {}".format(
                MBDValidation.attachment_text(datum_system)
            )
        )

    errors = MBDValidation.validate_datum_system(datum_system)

    if errors:
        raise AssertionError(
            "valid common datum system failed validation: {}".format(errors)
        )

    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_Parallelism_CommonDatum"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Parallelism"
    fcf.ToleranceValue = 0.01
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = "Face2"
    fcf.DatumSystem = datum_system
    fcf_errors = MBDValidation.validate_fcf(fcf)
    cells = MBDCommands.fcf_cells(fcf)

    if fcf_errors:
        raise AssertionError(
            "orientation FCF rejected common datum system: {}".format(
                fcf_errors
            )
        )

    if cells[-2:] != ["A-B", "C"]:
        raise AssertionError(
            "common datum FCF cells were {}".format(cells)
        )

    datum_system.SecondaryDatums = []
    datum_system.TertiaryDatums = [datum_c]
    gap_errors = MBDValidation.validate_datum_system(datum_system)

    if not any("tertiary compartment" in error for error in gap_errors):
        raise AssertionError("tertiary-without-secondary was not rejected")

    datum_system.SecondaryDatums = [datum_c]
    datum_system.TertiaryDatums = [datum_a]
    duplicate_errors = MBDValidation.validate_datum_system(datum_system)
    FreeCAD.closeDocument(doc.Name)

    if not any("more than one compartment" in error for error in duplicate_errors):
        raise AssertionError("cross-compartment duplicate datum was not rejected")

    print("common datum system validation passed")


def display_layout_metadata_smoke():
    output_path = "/tmp/mbd_display_layout_metadata.FCStd"

    if os.path.exists(output_path):
        os.remove(output_path)

    doc, box_obj = make_doc("MBDDisplayLayoutMetadataSmoke")
    datum_a = make_datum(doc, box_obj, "A", "Face1")
    datum_system = doc.addObject(
        "App::FeaturePython",
        "MBD_DatumSystem_A"
    )
    MBDDatumSystem(datum_system)
    datum_system.PrimaryDatums = [datum_a]

    dimension = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_Dimension_Layout"
    )
    MBDDimension.MBDDimension(dimension)
    dimension.ReferenceObject1 = box_obj
    dimension.ReferenceSubelement1 = "Face1"
    dimension.ReferenceObject2 = box_obj
    dimension.ReferenceSubelement2 = "Face2"

    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_Layout"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = "Face1"

    semantic_objects = [datum_a, datum_system, dimension, fcf]
    required_properties = [
        "DisplayLayoutVersion",
        "AnnotationOrigin",
        "AnnotationNormal",
        "AnnotationDirection",
        "AnnotationTextHeight",
        "DisplayLayoutMode",
        "DisplayLayoutLocked",
    ]

    for obj in semantic_objects:
        missing = [
            prop for prop in required_properties
            if not hasattr(obj, prop)
        ]

        if missing:
            raise AssertionError(
                "{} missing display layout properties {}".format(
                    obj.Name,
                    missing
                )
            )

    origin = FreeCAD.Vector(1, 2, 3)
    normal = FreeCAD.Vector(0, 0, 1)
    direction = FreeCAD.Vector(1, 0, 0)
    update_pmi_display_layout(
        dimension,
        origin,
        normal,
        direction,
        4.0
    )

    if (dimension.AnnotationOrigin - origin).Length > 1e-9:
        raise AssertionError("display layout origin was not stored")

    dimension.DisplayLayoutLocked = True
    changed = update_pmi_display_layout(
        dimension,
        FreeCAD.Vector(9, 9, 9),
        text_height=8.0
    )

    if changed:
        raise AssertionError("locked display layout reported an update")

    if (dimension.AnnotationOrigin - origin).Length > 1e-9:
        raise AssertionError("locked display layout origin was overwritten")

    dimension_name = dimension.Name
    doc.recompute()
    doc.saveAs(output_path)
    FreeCAD.closeDocument(doc.Name)

    reopened = FreeCAD.openDocument(output_path)
    reopened_dimension = reopened.getObject(dimension_name)

    if reopened_dimension is None:
        raise AssertionError("saved dimension was not restored")

    if (reopened_dimension.AnnotationOrigin - origin).Length > 1e-9:
        raise AssertionError("display layout origin did not survive save/reopen")

    if not reopened_dimension.DisplayLayoutLocked:
        raise AssertionError("display layout lock did not survive save/reopen")

    if reopened_dimension.DisplayLayoutVersion != 1:
        raise AssertionError("display layout version did not survive save/reopen")

    FreeCAD.closeDocument(reopened.Name)
    os.remove(output_path)
    print("display layout metadata passed")


def single_item_fcf_layout_smoke():
    doc, box_obj = make_doc("MBDSingleItemFCFLayoutSmoke")
    datum_a = make_datum(doc, box_obj, "A", "Face1")
    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_Position"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Position"
    fcf.ToleranceValue = 0.127
    fcf.DiameterZone = True
    fcf.DatumReference = datum_a
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = "Face2"
    update_pmi_display_layout(
        fcf,
        FreeCAD.Vector(10, 20, 30),
        FreeCAD.Vector(0, 0, 1),
        FreeCAD.Vector(1, 0, 0),
        4.0
    )

    cells = view_provider_fcf_cells(fcf)

    if [kind for kind, _text in cells] != [
        "symbol",
        "diameter",
        "text",
    ]:
        raise AssertionError("unexpected single-item FCF cells: {}".format(cells))

    for symbol_name in (
        "Position",
        "Flatness",
        "Parallelism",
        "Perpendicularity",
        "Profile of a Line",
        "Profile of a Surface",
        "Angularity",
        "Circularity",
        "Cylindricity",
        "Straightness",
        "Circular Runout",
        "Total Runout",
        "Diameter",
    ):
        if not symbol_segments(symbol_name):
            raise AssertionError(
                "single-item renderer has no strokes for {}".format(
                    symbol_name
                )
            )

    x_axis, y_axis, normal = annotation_basis(fcf)

    if abs(x_axis.dot(y_axis)) > 1e-9:
        raise AssertionError("annotation basis axes are not perpendicular")

    if abs(x_axis.dot(normal)) > 1e-9 or abs(y_axis.dot(normal)) > 1e-9:
        raise AssertionError("annotation basis is not in the annotation plane")

    moved = dragged_annotation_origin(
        fcf.AnnotationOrigin,
        x_axis,
        y_axis,
        (5.0, -2.0, 0.0)
    )
    expected = FreeCAD.Vector(15, 18, 30)

    if (moved - expected).Length > 1e-9:
        raise AssertionError(
            "dragged annotation origin was {}, expected {}".format(
                moved,
                expected
            )
        )

    class FakeViewObject:

        def __init__(self, obj):
            self.Object = obj
            self.RootNode = coin.SoSeparator()
            self.Proxy = None
            self.display_modes = {}

        def addDisplayMode(self, node, name):
            self.display_modes[name] = node

    fake_view = FakeViewObject(fcf)
    edit_calls = []
    reset_calls = []

    class FakeMoveView:

        def __init__(self):
            self.callbacks = {}
            self.removed = []
            self.next_callback = 1

        def addEventCallbackPivy(self, event_type, callback):
            callback_id = self.next_callback
            self.next_callback += 1
            self.callbacks[callback_id] = (event_type, callback)
            return callback_id

        def removeEventCallbackPivy(self, event_type, callback_id):
            self.removed.append((event_type, callback_id))
            self.callbacks.pop(callback_id, None)

        def getPoint(self, x, y):
            return FreeCAD.Vector(x, y, 30)

        def getViewDirection(self):
            return FreeCAD.Vector(0, 0, -1)

        def getObjectInfo(self, position):
            return {
                "Object": fcf.Name,
                "ParentObject": fcf,
                "SubName": fcf.Name,
            }

    fake_move_view = FakeMoveView()

    class FakeGuiDocument:

        def setEdit(self, obj, mode):
            edit_calls.append((obj, mode))

        def activeView(self):
            return fake_move_view

        def resetEdit(self):
            reset_calls.append(True)

    class FakeEvent:

        def __init__(self, position, button=None, state=None):
            self.position = position
            self.button = button
            self.state = state

        def getPosition(self):
            return self.position

        def getButton(self):
            return self.button

        def getState(self):
            return self.state

    class FakeCallback:

        def __init__(self, event):
            self.event = event

        def getEvent(self):
            return self.event

        def setHandled(self):
            pass

    fake_view.Document = FakeGuiDocument()
    view_provider = ViewProviderSingleItemFCF(fake_view)
    view_provider.attach(fake_view)

    if not view_provider.ensure_direct_interaction(fake_view):
        raise AssertionError("direct FCF interaction did not register")

    direct_callback_ids = set(fake_move_view.callbacks)
    view_provider.ensure_direct_interaction(fake_view)

    if set(fake_move_view.callbacks) != direct_callback_ids:
        raise AssertionError("direct FCF interaction registered twice")

    if (
        fake_view.RootNode.getNumChildren() != 1
        and not fake_view.display_modes
    ):
        raise AssertionError("single-item FCF scene graph was not attached")

    if view_provider.geometry.getNumChildren() < 3:
        raise AssertionError("single-item FCF scene graph is incomplete")

    view_provider._direct_move_button(FakeCallback(FakeEvent(
        (10, 20),
        coin.SoMouseButtonEvent.BUTTON1,
        coin.SoMouseButtonEvent.DOWN
    )))
    view_provider._direct_move_location(FakeCallback(FakeEvent((15, 25))))
    view_provider._direct_move_button(FakeCallback(FakeEvent(
        (15, 25),
        coin.SoMouseButtonEvent.BUTTON1,
        coin.SoMouseButtonEvent.DOWN
    )))

    if (fcf.AnnotationOrigin - FreeCAD.Vector(15, 25, 30)).Length > 1e-9:
        raise AssertionError("direct 3D FCF drag did not update annotation origin")

    if view_provider.direct_active:
        raise AssertionError("second click did not commit direct 3D FCF drag")

    fcf.AnnotationOrigin = FreeCAD.Vector(10, 20, 30)
    fcf.DisplayLayoutMode = "Automatic"
    fcf.DisplayLayoutLocked = False

    if not view_provider.start_edit(fake_view):
        raise AssertionError("single-item FCF edit request failed")

    if edit_calls != [(fcf, 0)]:
        raise AssertionError(
            "FCF edit mode used the wrong GUI document call: {}".format(
                edit_calls
            )
        )

    if not view_provider.setEdit(fake_view, 0):
        raise AssertionError("single-item FCF did not enter drag edit mode")

    view_provider._move_button(FakeCallback(FakeEvent(
        (10, 20),
        coin.SoMouseButtonEvent.BUTTON1,
        coin.SoMouseButtonEvent.DOWN
    )))
    view_provider._move_location(FakeCallback(FakeEvent((13, 24))))
    view_provider._move_button(FakeCallback(FakeEvent(
        (13, 24),
        coin.SoMouseButtonEvent.BUTTON1,
        coin.SoMouseButtonEvent.DOWN
    )))
    QtCore.QCoreApplication.processEvents()

    if (fcf.AnnotationOrigin - FreeCAD.Vector(13, 24, 30)).Length > 1e-9:
        raise AssertionError("FCF mouse move did not update annotation origin")

    if (
        fcf.DisplayLayoutMode != "Manual"
        or not fcf.DisplayLayoutLocked
    ):
        raise AssertionError("FCF mouse move did not persist manual layout state")

    if view_provider.move_active:
        raise AssertionError("second left click did not commit FCF movement")

    if not view_provider.unsetEdit(fake_view, 0):
        raise AssertionError("single-item FCF did not leave drag edit mode")

    if len(fake_move_view.callbacks) != 2:
        raise AssertionError("direct FCF callbacks were removed with edit mode")

    view_provider.onDelete(fake_view, [])

    if fake_move_view.callbacks:
        raise AssertionError("direct FCF callbacks were not removed on delete")

    restored_provider = ViewProviderSingleItemFCF.__new__(
        ViewProviderSingleItemFCF
    )
    restored_provider.Object = fcf
    restored_root = coin.SoSeparator()
    restored_provider.root = restored_root
    restored_provider._ensure_runtime_state()

    if restored_provider.root is not restored_root:
        raise AssertionError("restored FCF scene graph state was overwritten")

    if not hasattr(restored_provider, "move_active"):
        raise AssertionError("restored FCF move state was not initialized")

    import MBDCommands

    MBDCommands.create_fcf_display(doc, fcf)
    helper_names = [child.Name for child in fcf.Group]

    if len(helper_names) < 4:
        raise AssertionError("legacy FCF helper fixture was not created")

    removed = MBDCommands.clear_fcf_display_helpers(doc, fcf)

    if removed != len(helper_names):
        raise AssertionError(
            "removed {} FCF helpers, expected {}".format(
                removed,
                len(helper_names)
            )
        )

    if fcf.Group:
        raise AssertionError("legacy FCF helper group was not emptied")

    if any(doc.getObject(name) is not None for name in helper_names):
        raise AssertionError("legacy FCF helper objects remain in the document")

    if any(
        getattr(fcf, property_name, None) is not None
        for property_name in ("DisplayFrame", "DisplayText", "DisplayLeader")
    ):
        raise AssertionError("legacy FCF helper links were not cleared")

    target = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_DatumTarget_A1"
    )
    MBDDatumTarget.MBDDatumTarget(target)
    target.TargetId = "A1"
    target.ParentDatum = datum_a
    target.ConstructionObject = box_obj
    target.ReferencedObject = box_obj
    target.ReferencedSubelement = "Face1"
    target.TargetPoint = FreeCAD.Vector(0, 10, 15)
    update_pmi_display_layout(
        target,
        FreeCAD.Vector(-5, 10, 15),
        FreeCAD.Vector(0, 0, 1),
        FreeCAD.Vector(1, 0, 0),
        4.0
    )
    fake_target_view = FakeViewObject(target)
    fake_target_view.Document = FakeGuiDocument()
    target_view_provider = ViewProviderSingleItemDatumTarget(
        fake_target_view
    )
    target_view_provider.attach(fake_target_view)

    if target_view_provider.geometry.getNumChildren() < 5:
        raise AssertionError("single-item datum target scene graph is incomplete")

    if target_view_provider.claimChildren():
        raise AssertionError("single-item datum target claims helper children")

    MBDCommands.create_datum_target_display_text(doc, target)
    target_helper_names = [child.Name for child in target.Group]

    if not target_helper_names:
        raise AssertionError("legacy datum target helper fixture was not created")

    removed_targets = MBDCommands.clear_datum_target_display_helpers(
        doc,
        target
    )

    if removed_targets != len(target_helper_names):
        raise AssertionError(
            "removed {} target helpers, expected {}".format(
                removed_targets,
                len(target_helper_names)
            )
        )

    if target.Group or target.DisplayText is not None:
        raise AssertionError("legacy datum target helper state was not cleared")

    FreeCAD.closeDocument(doc.Name)
    print("single-item FCF layout passed")


def single_item_datum_feature_layout_smoke():
    doc, box_obj = make_doc("MBDSingleItemDatumFeatureLayoutSmoke")
    datum = make_datum(doc, box_obj, "A", "Face1")
    update_pmi_display_layout(
        datum,
        FreeCAD.Vector(0, 0, -12),
        FreeCAD.Vector(0, 1, 0),
        FreeCAD.Vector(0, 0, -1),
        4.0
    )

    class FakeViewObject:

        def __init__(self, obj):
            self.Object = obj
            self.RootNode = coin.SoSeparator()
            self.Proxy = None
            self.display_modes = {}

        def addDisplayMode(self, node, name):
            self.display_modes[name] = node

    fake_view = FakeViewObject(datum)
    view_provider = ViewProviderSingleItemDatumFeature(fake_view)
    view_provider.attach(fake_view)

    if view_provider.geometry.getNumChildren() < 5:
        raise AssertionError(
            "single-item datum feature scene graph is incomplete"
        )

    if view_provider.claimChildren():
        raise AssertionError("single-item datum feature claims helper children")

    helper_names = []

    for property_name, suffix in (
        ("DisplayText", "_Text"),
        ("DisplayFrame", "_Frame"),
        ("DisplayMarker", "_Marker"),
        ("DisplayLeader", "_Leader"),
    ):
        helper = doc.addObject("Part::Feature", datum.Name + suffix)
        helper.Shape = Part.makeLine(
            FreeCAD.Vector(0, 0, 0),
            FreeCAD.Vector(1, 0, 0)
        )
        setattr(datum, property_name, helper)
        datum.addObject(helper)
        helper_names.append(helper.Name)

    import MBDCommands

    removed = MBDCommands.clear_datum_display_helpers(doc, datum)

    if removed != len(helper_names):
        raise AssertionError(
            "removed {} datum helpers, expected {}".format(
                removed,
                len(helper_names)
            )
        )

    if datum.Group:
        raise AssertionError("legacy datum helper group was not emptied")

    if any(doc.getObject(name) is not None for name in helper_names):
        raise AssertionError("legacy datum helper objects remain")

    if any(
        getattr(datum, property_name, None) is not None
        for property_name in (
            "DisplayText",
            "DisplayFrame",
            "DisplayMarker",
            "DisplayLeader",
        )
    ):
        raise AssertionError("legacy datum helper links were not cleared")

    legacy = make_datum(doc, box_obj, "B", "Face2")

    for property_name in (
        "AnnotationOrigin",
        "AnnotationNormal",
        "AnnotationDirection",
        "AnnotationTextHeight",
    ):
        legacy.removeProperty(property_name)

    legacy_fake_view = FakeViewObject(legacy)
    legacy_provider = ViewProviderSingleItemDatumFeature(legacy_fake_view)
    legacy_provider.attach(legacy_fake_view)

    if not hasattr(legacy, "AnnotationOrigin"):
        raise AssertionError("legacy datum display layout was not initialized")

    FreeCAD.closeDocument(doc.Name)
    print("single-item datum feature layout passed")


def single_item_dimension_layout_smoke():
    doc, box_obj = make_doc("MBDSingleItemDimensionLayoutSmoke")

    import MBDCommands

    object_count = len(doc.Objects)
    layout = MBDCommands.dimension_display_layout(
        doc,
        FreeCAD.Vector(0, 0, 0),
        FreeCAD.Vector(10, 0, 0),
        "10.000 mm +/- 0.100 mm",
        "Linear",
        preferred_offset=FreeCAD.Vector(0, 10, 0),
        text_normal=FreeCAD.Vector(0, 0, 1),
        text_height=3.0
    )

    if layout is None:
        raise AssertionError("pure dimension layout was not resolved")

    if len(doc.Objects) != object_count:
        raise AssertionError(
            "dimension layout created temporary document objects"
        )

    dimension = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_Dimension001"
    )
    MBDDimension.MBDDimension(dimension)
    dimension.DimensionPurpose = "EqualBilateral"
    dimension.DimensionKind = "Linear"
    dimension.MeasurementType = "Distance"
    dimension.NominalValue = 10.0
    dimension.UpperTolerance = 0.1
    dimension.LowerTolerance = 0.1
    dimension.ReferenceObject1 = box_obj
    dimension.ReferenceSubelement1 = "Face1"
    dimension.ReferenceObject2 = box_obj
    dimension.ReferenceSubelement2 = "Face2"
    update_pmi_display_layout(
        dimension,
        FreeCAD.Vector(5, -8, 15),
        FreeCAD.Vector(0, 0, 1),
        FreeCAD.Vector(1, 0, 0),
        3.0
    )

    class FakeGuiDocument:

        def activeView(self):
            return None

    class FakeViewObject:

        def __init__(self, obj):
            self.Object = obj
            self.Document = FakeGuiDocument()
            self.RootNode = coin.SoSeparator()
            self.Proxy = None
            self.display_modes = {}

        def addDisplayMode(self, node, name):
            self.display_modes[name] = node

    fake_view = FakeViewObject(dimension)
    provider = ViewProviderSingleItemDimension(fake_view)
    provider.attach(fake_view)

    if provider.geometry.getNumChildren() < 5:
        raise AssertionError(
            "single-item linear dimension scene graph is incomplete"
        )

    if provider.claimChildren():
        raise AssertionError("single-item dimension claims helper children")

    helper_names = []

    for property_name, suffix in (
        ("DisplayDimension", "_Display"),
        ("DisplayText", "_Text"),
        ("DisplayTextBox", "_TextBox"),
    ):
        helper = doc.addObject("Part::Feature", dimension.Name + suffix)
        helper.Shape = Part.makeLine(
            FreeCAD.Vector(0, 0, 0),
            FreeCAD.Vector(1, 0, 0)
        )
        dimension.addObject(helper)
        setattr(dimension, property_name, helper)
        helper_names.append(helper.Name)

    removed = MBDCommands.clear_dimension_display_helpers(doc, dimension)

    if removed != 3:
        raise AssertionError(
            "removed {} dimension helpers, expected 3".format(removed)
        )

    if dimension.Group:
        raise AssertionError("dimension helper group was not emptied")

    if any(doc.getObject(name) is not None for name in helper_names):
        raise AssertionError("dimension helper objects remain in document")

    basic = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_BasicDimension001"
    )
    MBDBasicDimension.MBDBasicDimension(basic)
    basic.DimensionType = "Distance"
    basic.NominalValue = 10.0
    basic.ReferenceObject1 = box_obj
    basic.ReferenceSubelement1 = "Face1"
    basic.ReferenceObject2 = box_obj
    basic.ReferenceSubelement2 = "Face2"
    update_pmi_display_layout(
        basic,
        FreeCAD.Vector(5, 28, 15),
        FreeCAD.Vector(0, 0, 1),
        FreeCAD.Vector(1, 0, 0),
        3.0
    )
    fake_basic_view = FakeViewObject(basic)
    basic_provider = ViewProviderSingleItemDimension(fake_basic_view)
    basic_provider.attach(fake_basic_view)

    if basic_provider.geometry.getNumChildren() < 5:
        raise AssertionError(
            "single-item basic dimension scene graph is incomplete"
        )

    if basic_provider.claimChildren():
        raise AssertionError(
            "single-item basic dimension claims helper children"
        )

    FreeCAD.closeDocument(doc.Name)
    print("single-item dimension layout passed")


def global_geometry_link_scope_smoke():
    output_path = "/tmp/mbd_global_geometry_links.FCStd"

    if os.path.exists(output_path):
        os.remove(output_path)

    doc = FreeCAD.newDocument("MBDGlobalGeometryLinkScopeSmoke")
    body = doc.addObject("PartDesign::Body", "Body")
    feature = body.newObject("PartDesign::Feature", "BodyFeature")
    feature.Shape = Part.makeBox(10, 20, 30)
    doc.recompute()

    datum = doc.addObject("App::FeaturePython", "MBD_DatumFeature_A")
    MBDDatumFeature(datum)
    datum.ReferencedObject = feature
    datum.ReferencedSubelement = "Face1"

    target = doc.addObject("App::FeaturePython", "MBD_DatumTarget_A1")
    MBDDatumTarget.MBDDatumTarget(target)
    target.ParentDatum = datum
    target.ConstructionObject = feature
    target.ReferencedObject = feature
    target.ReferencedSubelement = "Face1"

    dimension = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_Dimension_GlobalLinks"
    )
    MBDDimension.MBDDimension(dimension)
    dimension.ReferenceObject1 = feature
    dimension.ReferenceSubelement1 = "Face1"
    dimension.ReferenceObject2 = feature
    dimension.ReferenceSubelement2 = "Face2"

    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_GlobalLinks"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ControlledObject = feature
    fcf.ControlledSubelement = "Face1"
    fcf.ReferencedObject = feature
    fcf.ReferencedSubelement = "Face1"

    expected_global_links = {
        datum: ["ReferencedObject"],
        target: ["ConstructionObject", "ReferencedObject"],
        dimension: ["ReferenceObject1", "ReferenceObject2"],
        fcf: ["ControlledObject", "ReferencedObject"],
    }

    for obj, property_names in expected_global_links.items():
        for property_name in property_names:
            property_type = obj.getTypeIdOfProperty(property_name)

            if property_type != "App::PropertyLinkGlobal":
                raise AssertionError(
                    "{}.{} uses {}".format(
                        obj.Name,
                        property_name,
                        property_type
                    )
                )

            if getattr(obj, property_name) is not feature:
                raise AssertionError(
                    "{}.{} did not retain the body feature link".format(
                        obj.Name,
                        property_name
                    )
                )

    if target.getTypeIdOfProperty("ParentDatum") != "App::PropertyLink":
        raise AssertionError("PMI-to-PMI parent datum link should remain local")

    if fcf.getTypeIdOfProperty("DisplayFrame") != "App::PropertyLink":
        raise AssertionError("display helper link should remain local")

    legacy = doc.addObject("App::FeaturePython", "MBD_LegacyGeometryLink")
    legacy.addProperty("App::PropertyBool", "IsSemanticPMI", "MBD")
    legacy.IsSemanticPMI = True
    legacy.addProperty("App::PropertyLink", "ReferencedObject", "MBD")
    legacy.ReferencedObject = feature

    migrated = migrate_semantic_pmi_global_links(doc)

    if "MBD_LegacyGeometryLink.ReferencedObject" not in migrated:
        raise AssertionError("legacy geometry link was not reported as migrated")

    if (
        legacy.getTypeIdOfProperty("ReferencedObject")
        != "App::PropertyLinkGlobal"
    ):
        raise AssertionError("legacy geometry link type was not migrated")

    if legacy.ReferencedObject is not feature:
        raise AssertionError("legacy geometry link target was not preserved")

    datum_name = datum.Name
    feature_name = feature.Name
    doc.recompute()
    doc.saveAs(output_path)
    FreeCAD.closeDocument(doc.Name)

    reopened = FreeCAD.openDocument(output_path)
    reopened_datum = reopened.getObject(datum_name)
    reopened_feature = reopened.getObject(feature_name)

    if (
        reopened_datum.getTypeIdOfProperty("ReferencedObject")
        != "App::PropertyLinkGlobal"
    ):
        raise AssertionError("global geometry link type did not survive save/reopen")

    if reopened_datum.ReferencedObject is not reopened_feature:
        raise AssertionError("global geometry link target did not survive save/reopen")

    FreeCAD.closeDocument(reopened.Name)
    os.remove(output_path)
    print("global geometry link scope passed")


def common_datum_export_smoke(output_path):
    MBDExporter.QtGui.QMessageBox = AcceptMessageBox

    doc, box_obj = make_doc("MBDCommonDatumExportSmoke")
    datum_a = make_datum(doc, box_obj, "A", "Face1")
    datum_b = make_datum(doc, box_obj, "B", "Face3")
    datum_c = make_datum(doc, box_obj, "C", "Face5")
    datum_system = doc.addObject(
        "App::FeaturePython",
        "MBD_DatumSystem_A_B__C"
    )
    MBDDatumSystem(datum_system)
    datum_system.PrimaryDatums = [datum_a, datum_b]
    datum_system.SecondaryDatums = [datum_c]
    datum_system.TertiaryDatums = []
    add_position_fcf(doc, box_obj, datum_system, False, "Face1")
    doc.recompute()

    if os.path.exists(output_path):
        os.remove(output_path)

    result = MBDExporter.export_ap242(output_path)
    exists = os.path.exists(output_path)
    size = os.path.getsize(output_path) if exists else 0
    FreeCAD.closeDocument(doc.Name)

    if result is not True:
        raise AssertionError("common datum export returned {}".format(result))

    if not exists or size <= 0:
        raise AssertionError("common datum export did not create a STEP file")

    print("common datum export passed:", output_path, size)


def first_face_of_type(obj, type_name):
    for index, face in enumerate(obj.Shape.Faces, start=1):
        if type_name.lower() in face.Surface.__class__.__name__.lower():
            return "Face{}".format(index)

    raise AssertionError(
        "no {} face found on {}".format(type_name, obj.Name)
    )


def fcf_rule_validation_smoke():
    doc, box_obj = make_doc("MBDFCFRuleValidationSmoke")
    datum_a = make_datum(doc, box_obj, "A", "Face1")

    cyl = doc.addObject("Part::Feature", "RuleCylinder")
    cyl.Shape = Part.makeCylinder(
        5,
        30,
        FreeCAD.Vector(40, 0, 0),
        FreeCAD.Vector(0, 0, 1)
    )
    doc.recompute()
    cylinder_face = first_face_of_type(cyl, "Cylinder")

    datum_axis = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_DatumFeature_D"
    )
    MBDDatumFeature(datum_axis)
    datum_axis.DatumLabel = "D"
    datum_axis.DatumType = "Axis"
    datum_axis.ReferencedObject = cyl
    datum_axis.ReferencedSubelement = cylinder_face
    update_geometry_signature(datum_axis)

    datum_system_axis = doc.addObject(
        "App::FeaturePython",
        "MBD_DatumSystem_D"
    )
    MBDDatumSystem(datum_system_axis)
    datum_system_axis.PrimaryDatums = [datum_axis]

    def make_fcf(
        name,
        tolerance_type,
        controlled_obj,
        subelement,
        datum_ref=None,
        datum_system=None,
    ):
        fcf = doc.addObject("App::FeaturePython", name)
        MBDFeatureControlFrame(fcf)
        fcf.ToleranceType = tolerance_type
        fcf.ToleranceValue = 0.01
        fcf.ControlledObject = controlled_obj
        fcf.ControlledSubelement = subelement
        fcf.DatumReference = datum_ref
        fcf.DatumSystem = datum_system
        return fcf

    cases = [
        (
            "MBD_FCF_Circularity_Valid",
            "Circularity",
            cyl,
            cylinder_face,
            None,
            None,
            False,
            "circularity on cylinder should be valid",
        ),
        (
            "MBD_FCF_Circularity_Invalid",
            "Circularity",
            box_obj,
            "Face1",
            None,
            None,
            True,
            "circularity on plane should be rejected",
        ),
        (
            "MBD_FCF_Cylindricity_Valid",
            "Cylindricity",
            cyl,
            cylinder_face,
            None,
            None,
            False,
            "cylindricity on cylinder should be valid",
        ),
        (
            "MBD_FCF_Cylindricity_Invalid",
            "Cylindricity",
            box_obj,
            "Face1",
            None,
            None,
            True,
            "cylindricity on plane should be rejected",
        ),
        (
            "MBD_FCF_Straightness_Valid",
            "Straightness",
            cyl,
            cylinder_face,
            None,
            None,
            False,
            "axis straightness on cylinder should be valid",
        ),
        (
            "MBD_FCF_Straightness_Invalid",
            "Straightness",
            box_obj,
            "Face1",
            None,
            None,
            True,
            "straightness on plane should be rejected",
        ),
        (
            "MBD_FCF_Runout_Valid",
            "CircularRunout",
            cyl,
            cylinder_face,
            datum_axis,
            None,
            False,
            "runout with axis-capable datum should be valid",
        ),
        (
            "MBD_FCF_Runout_DatumSystem_Valid",
            "CircularRunout",
            cyl,
            cylinder_face,
            None,
            datum_system_axis,
            False,
            "runout with axis-capable datum system should be valid",
        ),
        (
            "MBD_FCF_Runout_Invalid",
            "CircularRunout",
            cyl,
            cylinder_face,
            datum_a,
            None,
            True,
            "runout with planar datum should be rejected",
        ),
        (
            "MBD_FCF_Angularity_Valid",
            "Angularity",
            box_obj,
            "Face1",
            datum_a,
            None,
            False,
            "angularity of plane to datum plane should be valid",
        ),
        (
            "MBD_FCF_LineProfile_Valid",
            "LineProfile",
            box_obj,
            "Edge1",
            None,
            None,
            False,
            "line profile on an edge should be valid",
        ),
        (
            "MBD_FCF_LineProfile_Invalid",
            "LineProfile",
            box_obj,
            "Face1",
            None,
            None,
            True,
            "line profile on a face should be rejected",
        ),
    ]

    for (
        name,
        tolerance_type,
        controlled_obj,
        subelement,
        datum_ref,
        datum_system,
        should_error,
        message
    ) in cases:
        fcf = make_fcf(
            name,
            tolerance_type,
            controlled_obj,
            subelement,
            datum_ref,
            datum_system
        )
        errors = MBDValidation.validate_fcf(fcf)
        has_error = len(errors) > 0

        if has_error != should_error:
            FreeCAD.closeDocument(doc.Name)
            raise AssertionError(
                "{}: expected error={}, got {} ({})".format(
                    message,
                    should_error,
                    has_error,
                    "; ".join(errors)
                )
            )

    FreeCAD.closeDocument(doc.Name)
    FreeCAD.Console.PrintMessage("FCF rule validation passed\n")


def basic_dimension_projection_smoke():
    doc, box_obj = make_doc("MBDBasicDimensionProjectionSmoke")
    datum = make_datum(doc, box_obj, "B", "Face1")

    target = doc.addObject("Part::Feature", "Target")
    target.Shape = Part.Vertex(5, 7, 12)
    doc.recompute()

    p1, p2 = MBDBasicDimension.display_points_from_references(
        datum,
        "",
        target,
        ""
    )
    measured = MBDBasicDimension.measured_value_from_references(
        "Distance",
        datum,
        "",
        target,
        ""
    )

    FreeCAD.closeDocument(doc.Name)

    if p1 is None or p2 is None:
        raise AssertionError("display endpoints were not resolved")

    if abs(p1.x) > 0.000001 or abs(p1.y - 7) > 0.000001 or abs(p1.z - 12) > 0.000001:
        raise AssertionError(
            "datum display endpoint was {}, {}, {}".format(p1.x, p1.y, p1.z)
        )

    if abs((p2 - p1).Length - measured) > 0.000001:
        raise AssertionError("display distance does not match measured distance")

    print("basic dimension projection passed")


def semantic_dimension_smoke():
    doc, box_obj = make_doc("MBDSemanticDimensionSmoke")

    point_a = doc.addObject("Part::Feature", "PointA")
    point_a.Shape = Part.Vertex(0, 0, 0)

    point_b = doc.addObject("Part::Feature", "PointB")
    point_b.Shape = Part.Vertex(25.4, 0, 0)
    doc.recompute()

    dim = doc.addObject("App::FeaturePython", "MBD_Dimension001")
    MBDDimension.MBDDimension(dim)
    dim.DimensionPurpose = "EqualBilateral"
    dim.DimensionKind = "Linear"
    dim.MeasurementType = "X"
    dim.NominalValue = 25.4
    dim.UpperTolerance = 0.127
    dim.LowerTolerance = 0.127
    dim.ReferenceObject1 = point_a
    dim.ReferenceObject2 = point_b
    MBDDimension.update_dimension_signature(dim)

    if dim.TypeId != "App::FeaturePython":
        raise AssertionError("semantic dimension is not a single feature item")

    report = MBDValidation.validate_document_structured(doc)
    issues = [
        issue for issue in report["issues"]
        if issue.obj is not None and issue.obj.Name == dim.Name
    ]
    measured_value = dim.MeasuredValue
    dimension_count = len(report["dimensions"])
    FreeCAD.closeDocument(doc.Name)

    if abs(measured_value - 25.4) > 0.000001:
        raise AssertionError("dimension measured value was not updated")

    if dimension_count != 1:
        raise AssertionError("semantic dimension was not reported")

    if issues:
        raise AssertionError(
            "semantic dimension validation issues: {}".format(
                "; ".join(issue.message for issue in issues)
            )
        )

    print("semantic dimension smoke passed")


def dimension_semantic_rules_smoke():
    doc = FreeCAD.newDocument("MBDDimensionSemanticRulesSmoke")
    cylinder = doc.addObject("Part::Feature", "RuleCylinder")
    cylinder.Shape = Part.makeCylinder(5, 20)
    point_a = doc.addObject("Part::Feature", "PointA")
    point_a.Shape = Part.Vertex(0, 0, 0)
    point_b = doc.addObject("Part::Feature", "PointB")
    point_b.Shape = Part.Vertex(10, 0, 0)
    doc.recompute()
    cylinder_face = first_face_of_type(cylinder, "Cylinder")

    def make_dimension(name, purpose, kind, first_obj, first_sub, second_obj=None, second_sub=""):
        dim = doc.addObject("App::DocumentObjectGroupPython", name)
        MBDDimension.MBDDimension(dim)
        dim.DimensionPurpose = purpose
        dim.DimensionKind = kind
        dim.MeasurementType = "Distance"
        dim.ReferenceObject1 = first_obj
        dim.ReferenceSubelement1 = first_sub
        dim.ReferenceObject2 = second_obj
        dim.ReferenceSubelement2 = second_sub
        measured = MBDDimension.measured_value_from_references(dim)

        if measured is not None:
            dim.NominalValue = measured

        return dim

    equal_bad = make_dimension(
        "EqualBilateralBad",
        "EqualBilateral",
        "Linear",
        point_a,
        "",
        point_b,
        ""
    )
    equal_bad.UpperTolerance = 0.001
    equal_bad.LowerTolerance = 0.0

    basic_bad = make_dimension(
        "BasicWithTolerance",
        "Basic",
        "Linear",
        point_a,
        "",
        point_b,
        ""
    )
    basic_bad.UpperTolerance = 0.001

    diameter_bad = make_dimension(
        "DiameterWithSecondReference",
        "Reference",
        "Diameter",
        cylinder,
        cylinder_face,
        point_a,
        ""
    )

    errors = {
        obj.Name: MBDValidation.validate_dimension(obj)
        for obj in (equal_bad, basic_bad, diameter_bad)
    }
    report = MBDValidation.validate_document(doc)
    equal_bad_name = equal_bad.Name
    basic_bad_name = basic_bad.Name
    diameter_bad_name = diameter_bad.Name
    FreeCAD.closeDocument(doc.Name)

    if "Dimensions found: 3" not in report:
        raise AssertionError("validation report did not list semantic dimensions")

    if "equal bilateral tolerance must have equal" not in report:
        raise AssertionError(
            "validation report omitted the equal-bilateral semantic error"
        )

    if not any("equal upper and lower" in error for error in errors[equal_bad_name]):
        raise AssertionError("unequal equal-bilateral tolerance was not rejected")

    if not any("must not carry" in error for error in errors[basic_bad_name]):
        raise AssertionError("toleranced basic dimension was not rejected")

    if not any(
        "exactly one cylindrical" in error
        for error in errors[diameter_bad_name]
    ):
        raise AssertionError("diameter second reference was not rejected")

    print("dimension semantic rules passed")


def dimension_reference_patterns_smoke():
    doc, box_obj = make_doc("MBDDimensionReferencePatternsSmoke")

    parallel_pair = None
    non_parallel_pair = None

    normals = []

    for index, face in enumerate(box_obj.Shape.Faces):
        u_min, u_max, v_min, v_max = face.ParameterRange
        normal = face.normalAt(
            (u_min + u_max) * 0.5,
            (v_min + v_max) * 0.5
        )
        normal.normalize()
        normals.append((index + 1, normal))

    for first_index, first_normal in normals:
        for second_index, second_normal in normals:
            if first_index >= second_index:
                continue

            cross = first_normal.cross(second_normal)

            if cross.Length <= 0.000001 and parallel_pair is None:
                parallel_pair = (first_index, second_index)

            if cross.Length > 0.5 and non_parallel_pair is None:
                non_parallel_pair = (first_index, second_index)

    if parallel_pair is None or non_parallel_pair is None:
        raise AssertionError("could not find expected box face pairs")

    result = MBDDimension.measurement_from_references(
        "Linear",
        "Distance",
        box_obj,
        "Face{}".format(parallel_pair[0]),
        box_obj,
        "Face{}".format(parallel_pair[1])
    )

    if result["value"] is None:
        raise AssertionError("parallel plane measurement failed")

    if result["pattern"] != "PlaneToPlane":
        raise AssertionError(
            "parallel plane pattern was {}".format(result["pattern"])
        )

    result = MBDDimension.measurement_from_references(
        "Linear",
        "Distance",
        box_obj,
        "Face{}".format(non_parallel_pair[0]),
        box_obj,
        "Face{}".format(non_parallel_pair[1])
    )

    if result["value"] is not None:
        raise AssertionError("non-parallel plane measurement should fail")

    point = doc.addObject("Part::Feature", "Point")
    point.Shape = Part.Vertex(25, 10, 15)
    doc.recompute()

    result = MBDDimension.measurement_from_references(
        "Linear",
        "Distance",
        box_obj,
        "Face{}".format(parallel_pair[0]),
        point,
        ""
    )
    FreeCAD.closeDocument(doc.Name)

    if result["value"] is None:
        raise AssertionError("plane-point measurement failed")

    if result["pattern"] != "PlaneToPoint":
        raise AssertionError(
            "plane-point pattern was {}".format(result["pattern"])
        )

    print("dimension reference patterns passed")


def basic_size_dimension_requires_profile_smoke():
    doc, box_obj = make_doc("MBDBasicSizeDimensionRequiresProfileSmoke")

    parallel_pair = None
    normals = []

    for index, face in enumerate(box_obj.Shape.Faces):
        u_min, u_max, v_min, v_max = face.ParameterRange
        normal = face.normalAt(
            (u_min + u_max) * 0.5,
            (v_min + v_max) * 0.5
        )
        normal.normalize()
        normals.append((index + 1, normal))

    for first_index, first_normal in normals:
        for second_index, second_normal in normals:
            if first_index >= second_index:
                continue

            if first_normal.cross(second_normal).Length <= 0.000001:
                parallel_pair = (first_index, second_index)
                break

        if parallel_pair is not None:
            break

    if parallel_pair is None:
        raise AssertionError("could not find parallel box faces")

    face1 = "Face{}".format(parallel_pair[0])
    face2 = "Face{}".format(parallel_pair[1])
    measured = MBDDimension.measurement_from_references(
        "Linear",
        "Distance",
        box_obj,
        face1,
        box_obj,
        face2
    )["value"]

    dim = doc.addObject("App::DocumentObjectGroupPython", "MBD_Dimension001")
    MBDDimension.MBDDimension(dim)
    dim.DimensionPurpose = "Basic"
    dim.DimensionKind = "Linear"
    dim.MeasurementType = "Distance"
    dim.NominalValue = measured
    dim.ReferenceObject1 = box_obj
    dim.ReferenceSubelement1 = face1
    dim.ReferenceObject2 = box_obj
    dim.ReferenceSubelement2 = face2
    MBDDimension.update_dimension_signature(dim)

    report = MBDValidation.validate_document_structured(doc)
    messages = [
        issue.message for issue in report["issues"]
        if issue.obj is not None and issue.obj.Name == dim.Name
    ]

    if not any("basic size dimension" in message for message in messages):
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError(
            "basic size dimension without profile was not rejected"
        )

    fcf = doc.addObject("App::DocumentObjectGroupPython", "MBD_FCF_Profile")
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Profile"
    fcf.ToleranceValue = 0.01
    fcf.ProfileAllOver = True
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = ""

    report = MBDValidation.validate_document_structured(doc)
    messages = [
        issue.message for issue in report["issues"]
        if issue.obj is not None and issue.obj.Name == dim.Name
    ]
    FreeCAD.closeDocument(doc.Name)

    if any("basic size dimension" in message for message in messages):
        raise AssertionError(
            "profile all-over did not satisfy basic size dimension control"
        )

    print("basic size dimension profile validation passed")


def cylinder_axis_dimension_smoke():
    doc = FreeCAD.newDocument("MBDCylinderAxisDimensionSmoke")

    cyl_a = doc.addObject("Part::Feature", "HoleLikeCylinderA")
    cyl_a.Shape = Part.makeCylinder(5, 30, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1))

    cyl_b = doc.addObject("Part::Feature", "HoleLikeCylinderB")
    cyl_b.Shape = Part.makeCylinder(5, 30, FreeCAD.Vector(20, 0, 0), FreeCAD.Vector(0, 0, 1))

    cyl_skew = doc.addObject("Part::Feature", "SkewCylinder")
    cyl_skew.Shape = Part.makeCylinder(5, 30, FreeCAD.Vector(0, 20, 0), FreeCAD.Vector(1, 0, 1))

    doc.recompute()

    def cylinder_face_name(obj):
        for index, face in enumerate(obj.Shape.Faces):
            try:
                if "cylinder" in face.Surface.__class__.__name__.lower():
                    return "Face{}".format(index + 1)
            except Exception:
                pass

        raise AssertionError("no cylindrical face found on {}".format(obj.Name))

    cyl_a_face = cylinder_face_name(cyl_a)
    cyl_b_face = cylinder_face_name(cyl_b)
    cyl_skew_face = cylinder_face_name(cyl_skew)

    diameter = MBDDimension.measurement_from_references(
        "Diameter",
        "Distance",
        cyl_a,
        cyl_a_face,
        None,
        ""
    )

    if abs(diameter["value"] - 10.0) > 0.000001:
        raise AssertionError("cylinder diameter was {}".format(diameter["value"]))

    parallel = MBDDimension.measurement_from_references(
        "Linear",
        "Distance",
        cyl_a,
        cyl_a_face,
        cyl_b,
        cyl_b_face
    )

    if parallel["pattern"] != "AxisToAxisParallel":
        raise AssertionError(
            "parallel axis pattern was {}".format(parallel["pattern"])
        )

    if abs(parallel["value"] - 20.0) > 0.000001:
        raise AssertionError("parallel axis distance was {}".format(parallel["value"]))

    skew = MBDDimension.measurement_from_references(
        "Linear",
        "Distance",
        cyl_a,
        cyl_a_face,
        cyl_skew,
        cyl_skew_face
    )

    FreeCAD.closeDocument(doc.Name)

    if skew["pattern"] != "AxisToAxisSkew":
        raise AssertionError("skew axis pattern was {}".format(skew["pattern"]))

    if skew["value"] is None:
        raise AssertionError("skew axis distance was not resolved")

    print("cylinder axis dimension patterns passed")


def position_fcf_hole_opening_direction_smoke():
    doc = FreeCAD.newDocument("MBDPositionFCFHoleOpeningSmoke")

    import MBDCommands

    body = doc.addObject("Part::Feature", "BlindHoleBody")
    box = Part.makeBox(40, 40, 30)
    cutter = Part.makeCylinder(
        5,
        20,
        FreeCAD.Vector(20, 20, 30),
        FreeCAD.Vector(0, 0, -1)
    )
    body.Shape = box.cut(cutter)
    doc.recompute()

    cylinder_face = None

    for index, face in enumerate(body.Shape.Faces):
        try:
            if "cylinder" in face.Surface.__class__.__name__.lower():
                cylinder_face = "Face{}".format(index + 1)
                break
        except Exception:
            pass

    if cylinder_face is None:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError("blind-hole cylindrical face was not found")

    cylinder = MBDDimension.cylindrical_face_reference(
        body,
        cylinder_face
    )

    if cylinder is None or cylinder["opening_direction"] is None:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError("blind-hole opening direction was not resolved")

    opening_point = cylinder["point"]
    opening_direction = cylinder["opening_direction"]

    if opening_direction.z <= 0.9:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError(
            "blind-hole opening direction was {}, expected +Z".format(
                opening_direction
            )
        )

    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_Position"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Position"
    fcf.ToleranceValue = 0.127
    fcf.DiameterZone = True
    fcf.ControlledObject = body
    fcf.ControlledSubelement = cylinder_face

    _frame, _text, leader = MBDCommands.create_fcf_display(doc, fcf)
    attachment = fcf_attachment_point(fcf)
    origin_offset = fcf.AnnotationOrigin - opening_point
    leader_segments = fcf_leader_segments(
        fcf,
        opening_point,
        fcf.AnnotationOrigin,
        fcf.AnnotationTextHeight
    )

    if origin_offset.dot(opening_direction) <= 0:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError(
            "position FCF origin was not placed beyond the hole opening"
        )

    if attachment is None or (attachment - opening_point).Length > 1e-6:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError(
            "single-item FCF leader did not attach at the hole opening"
        )

    first_leg = leader_segments[0][1] - leader_segments[0][0]

    if first_leg.Length <= 1e-9:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError("position FCF axis leader leg was null")

    first_leg.normalize()

    if abs(first_leg.dot(opening_direction)) < 0.999:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError(
            "position FCF first leader leg was not parallel to the hole axis"
        )

    diameter_measurement = MBDDimension.measurement_from_references(
        "Diameter",
        "Distance",
        body,
        cylinder_face,
        None,
        ""
    )
    diameter_direction = diameter_measurement.get("display_direction")

    if diameter_direction is None:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError("diameter display direction was not resolved")

    diameter_direction.normalize()

    if diameter_direction.dot(opening_direction) < 0.999:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError(
            "diameter display direction did not follow the hole opening axis"
        )

    diameter = MBDCommands.create_dimension_object(
        doc,
        body,
        cylinder_face,
        dimension_purpose="EqualBilateral",
        dimension_kind="Diameter",
        upper_tolerance=0.1,
        lower_tolerance=0.1,
        resolved_measurement=diameter_measurement
    )

    if diameter is None:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError("diameter dimension was not created")

    plane_normal = MBDCommands.diameter_annotation_plane_normal(
        diameter_measurement["point1"],
        diameter_measurement["point2"],
        opening_direction
    )

    if plane_normal is None:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError("diameter annotation plane was not resolved")

    diameter_layout = MBDCommands.dimension_display_layout(
        doc,
        diameter_measurement["point1"],
        diameter_measurement["point2"],
        MBDDimension.dimension_display_label(diameter),
        "Diameter",
        MBDCommands.preferred_display_offset_beyond_model(
            doc,
            diameter_measurement["point1"],
            diameter_measurement["point2"],
            opening_direction,
            3.0
        ),
        plane_normal,
        3.0
    )
    update_pmi_display_layout(
        diameter,
        diameter_layout["origin"],
        diameter_layout["normal"],
        diameter_layout["direction"],
        3.0
    )
    radial_direction = (
        diameter_measurement["point2"]
        - diameter_measurement["point1"]
    )
    radial_direction.normalize()
    diameter_plane_normal = FreeCAD.Vector(diameter.AnnotationNormal)
    diameter_plane_normal.normalize()

    if abs(diameter_plane_normal.dot(opening_direction)) > 1e-6:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError(
            "diameter text plane does not contain the hole-axis leaders"
        )

    if abs(diameter_plane_normal.dot(radial_direction)) > 1e-6:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError(
            "diameter text plane does not contain the dimension line"
        )

    MBDCommands.create_fcf_display(doc, fcf)
    fcf_plane_normal = FreeCAD.Vector(fcf.AnnotationNormal)
    fcf_plane_normal.normalize()

    if abs(abs(fcf_plane_normal.dot(diameter_plane_normal)) - 1.0) > 1e-6:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError(
            "position FCF does not share the diameter annotation plane"
        )

    if fcf_leader_segments(
        fcf,
        opening_point,
        fcf.AnnotationOrigin,
        fcf.AnnotationTextHeight
    ):
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError(
            "position FCF retained a redundant leader with a diameter dimension"
        )

    dim_x, dim_y, _dim_normal = annotation_basis(diameter)
    _fcf_x, fcf_y, _fcf_normal = annotation_basis(fcf)
    right_point = diameter_measurement["point1"]

    if (
        diameter_measurement["point2"].dot(dim_x)
        > diameter_measurement["point1"].dot(dim_x)
    ):
        right_point = diameter_measurement["point2"]

    extension_line_point = (
        diameter.AnnotationOrigin
        + dim_x
        * (right_point - diameter.AnnotationOrigin).dot(dim_x)
    )
    fcf_top_left = (
        fcf.AnnotationOrigin
        + fcf_y * (fcf.AnnotationTextHeight * 1.6)
    )

    if (fcf_top_left - extension_line_point).Length > 1e-6:
        FreeCAD.closeDocument(doc.Name)
        raise AssertionError(
            "position FCF did not attach directly to the diameter extension line"
        )

    if leader is not None:
        leader_points = [vertex.Point for vertex in leader.Shape.Vertexes]

        if not any(
            (point - opening_point).Length <= 1e-6
            for point in leader_points
        ):
            FreeCAD.closeDocument(doc.Name)
            raise AssertionError(
                "helper FCF leader did not attach at the hole opening"
            )

    FreeCAD.closeDocument(doc.Name)
    print("position FCF blind-hole opening direction passed")


def radius_dimension_display_smoke():
    doc = FreeCAD.newDocument("MBDRadiusDimensionDisplaySmoke")

    import MBDCommands

    cyl = doc.addObject("Part::Feature", "RadiusCylinder")
    cyl.Shape = Part.makeCylinder(
        5,
        30,
        FreeCAD.Vector(0, 0, 0),
        FreeCAD.Vector(0, 0, 1)
    )
    doc.recompute()

    cyl_face = None

    for index, face in enumerate(cyl.Shape.Faces):
        if "cylinder" in face.Surface.__class__.__name__.lower():
            cyl_face = "Face{}".format(index + 1)
            break

    if cyl_face is None:
        raise AssertionError("no cylindrical face found for radius display")

    dim = MBDCommands.create_dimension_object(
        doc,
        cyl,
        cyl_face,
        dimension_purpose="EqualBilateral",
        dimension_kind="Radius",
        upper_tolerance=0.1,
        lower_tolerance=0.1
    )

    if dim is None:
        raise AssertionError("radius dimension was not created")

    measurement = MBDDimension.measurement_from_references(
        "Radius",
        "Distance",
        cyl,
        cyl_face,
        None,
        ""
    )
    label = MBDDimension.dimension_display_label(dim)
    display = MBDCommands.make_radius_dimension_display(
        doc,
        measurement["point1"],
        measurement["point2"],
        label,
        measurement.get("text_normal"),
        dim.Name,
        3.0,
        False
    )

    if display is None:
        raise AssertionError("radius dimension display was not created")

    display_geometry, display_text, _display_box = display[:3]
    text_value = " ".join(display_text.Text) if display_text is not None else ""
    edge_count = len(display_geometry.Shape.Edges)
    FreeCAD.closeDocument(doc.Name)

    if not text_value.startswith("R "):
        raise AssertionError("radius dimension text did not start with R: {}".format(text_value))

    if edge_count < 3:
        raise AssertionError("radius display should include leader and arrowhead edges")

    print("radius dimension display passed")


def annotation_display_shape_smoke():
    doc, _box_obj = make_doc("MBDAnnotationDisplayShapeSmoke")

    import MBDCommands

    p1 = FreeCAD.Vector(0, 0, 0)
    p2 = FreeCAD.Vector(10, 0, 0)
    display = MBDCommands.make_basic_dimension_display(
        doc,
        p1,
        p2,
        "10.000 mm",
        preferred_offset=FreeCAD.Vector(0, 20, 0),
        text_normal=FreeCAD.Vector(0, 0, 1),
        owner_name="MBD_TestDimension",
        text_height=3.0,
        boxed_text=True
    )

    if display is None:
        raise AssertionError("dimension display was not created")

    display_geometry, display_text, display_box = display[:3]
    edge_count = len(display_geometry.Shape.Edges)
    FreeCAD.closeDocument(doc.Name)

    if edge_count < 7:
        raise AssertionError(
            "dimension display should include extension, dimension, and arrow lines; got {} edges".format(
                edge_count
            )
        )

    if display_text is None or display_box is None:
        raise AssertionError("dimension display text or box was not created")

    print("annotation display shape passed")


def preferred_display_offset_clears_model_smoke():
    doc, _box_obj = make_doc("MBDPreferredDisplayOffsetSmoke")

    import MBDCommands

    text_height = 3.0
    p1 = FreeCAD.Vector(2, 5, 12)
    p2 = FreeCAD.Vector(8, 5, 12)
    offset = MBDCommands.preferred_display_offset_beyond_model(
        doc,
        p1,
        p2,
        FreeCAD.Vector(0, 0, 1),
        text_height
    )
    bbox = MBDCommands.document_shape_bound_box(doc)
    display_extent = max((p1 + offset).z, (p2 + offset).z)
    FreeCAD.closeDocument(doc.Name)

    if display_extent <= bbox.ZMax:
        raise AssertionError(
            "preferred display offset did not clear model: {} <= {}".format(
                display_extent,
                bbox.ZMax
            )
        )

    if display_extent < bbox.ZMax + text_height * 2.0 - 1e-6:
        raise AssertionError(
            "preferred display offset did not include text clearance"
        )

    print("preferred display offset clears model passed")


def gdt_symbol_table_smoke():
    doc = FreeCAD.newDocument("MBDGDTSymbolTableSmoke")

    import MBDCommands

    group = MBDCommands.create_geometric_tolerance_symbol_table(doc)
    symbol_count = 0

    for obj in doc.Objects:
        if obj.Label.endswith("_Symbol"):
            symbol_count += 1

    expected_count = len(MBDCommands.GEOMETRIC_TOLERANCE_SYMBOLS)
    FreeCAD.closeDocument(doc.Name)

    if group is None:
        raise AssertionError("GD&T symbol table group was not created")

    if symbol_count != expected_count:
        raise AssertionError(
            "expected {} symbol objects, found {}".format(
                expected_count,
                symbol_count
            )
        )

    print("GD&T symbol table passed")


def grouped_display_helpers_smoke():
    doc, box_obj = make_doc("MBDGroupedDisplayHelpersSmoke")

    import MBDCommands

    datum = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_DatumFeature_A"
    )
    MBDDatumFeature(datum)
    datum.DatumLabel = "A"
    datum.ReferencedObject = box_obj
    datum.ReferencedSubelement = "Face1"
    update_geometry_signature(datum)

    MBDCommands.create_datum_display_text(doc, datum)

    if not hasattr(datum, "Group") or len(datum.Group) < 4:
        raise AssertionError("datum display helpers were not grouped")

    _datum_a, _datum_b, _datum_c, datum_system = make_datum_set(doc, box_obj)
    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_Position"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Position"
    fcf.ToleranceValue = 0.01
    fcf.DiameterZone = True
    fcf.DatumSystem = datum_system
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = "Face1"

    MBDCommands.create_fcf_display(doc, fcf)
    pmi_group = MBDCommands.organize_pmi_tree(doc)

    if not hasattr(fcf, "Group") or len(fcf.Group) < 4:
        raise AssertionError("FCF display helpers were not grouped")

    if pmi_group is None:
        raise AssertionError("top-level MBD PMI group was not created")

    if datum not in pmi_group.Group or fcf not in pmi_group.Group:
        raise AssertionError("semantic PMI objects were not grouped under MBD PMI")

    FreeCAD.closeDocument(doc.Name)
    print("grouped display helpers passed")


def fcf_tolerance_units_smoke():
    import MBDCommands

    inch_value = MBDCommands.parse_length_quantity_text("0.005 in")
    mm_value = MBDCommands.parse_length_quantity_text("0.127 mm")

    if abs(inch_value - mm_value) > 1e-6:
        raise AssertionError(
            "0.005 in parsed as {}, 0.127 mm parsed as {}".format(
                inch_value,
                mm_value
            )
        )

    print("FCF tolerance units passed")


def fcf_below_dimension_smoke():
    doc, box_obj = make_doc("MBDFCFBelowDimensionSmoke")

    import MBDCommands

    dim_obj = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_Dimension001"
    )
    MBDDimension.MBDDimension(dim_obj)
    dim_obj.DimensionKind = "Diameter"
    dim_obj.ReferenceObject1 = box_obj
    dim_obj.ReferenceSubelement1 = "Face1"
    dim_text = MBDCommands.make_basic_dimension_text(
        FreeCAD.Vector(10, 10, 10),
        "1.000 in",
        3.0,
        FreeCAD.Rotation(),
        "MBD_Dimension001_Text"
    )
    dim_obj.DisplayText = dim_text
    dim_obj.addObject(dim_text)
    dim_y = dim_text.Placement.Base.y
    update_pmi_display_layout(
        dim_obj,
        dim_text.Placement.Base,
        FreeCAD.Vector(0, 0, 1),
        FreeCAD.Vector(1, 0, 0),
        3.0
    )
    dim_obj.removeObject(dim_text)
    dim_obj.DisplayText = None
    doc.removeObject(dim_text.Name)

    _datum_a, _datum_b, _datum_c, datum_system = make_datum_set(doc, box_obj)
    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_Position"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Position"
    fcf.ToleranceValue = MBDCommands.parse_length_quantity_text("0.005 in")
    fcf.DiameterZone = True
    fcf.DatumSystem = datum_system
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = "Face1"

    frame_obj, _text_obj, _leader_obj = MBDCommands.create_fcf_display(doc, fcf)
    frame_y_max = frame_obj.Shape.BoundBox.YMax
    FreeCAD.closeDocument(doc.Name)

    if frame_y_max >= dim_y:
        raise AssertionError(
            "FCF was not placed below dimension text: {} >= {}".format(
                frame_y_max,
                dim_y
            )
        )

    print("FCF below dimension passed")


def flatness_fcf_display_smoke():
    doc, box_obj = make_doc("MBDFlatnessFCFDisplaySmoke")

    import MBDCommands

    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_Flatness"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Flatness"
    fcf.ToleranceValue = MBDCommands.parse_length_quantity_text("0.002 in")
    fcf.DiameterZone = False
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = "Face1"

    frame_obj, text_obj, leader_obj = MBDCommands.create_fcf_display(doc, fcf)
    group_size = len(fcf.Group) if hasattr(fcf, "Group") else 0
    FreeCAD.closeDocument(doc.Name)

    if frame_obj is None or text_obj is None or leader_obj is None:
        raise AssertionError("flatness FCF display was not fully created")

    if group_size < 4:
        raise AssertionError("flatness FCF display helpers were not grouped")

    print("flatness FCF display passed")


def parallelism_fcf_display_smoke():
    doc, box_obj = make_doc("MBDParallelismFCFDisplaySmoke")

    import MBDCommands

    datum_a, _datum_b, _datum_c, _datum_system = make_datum_set(doc, box_obj)
    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_Parallelism"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Parallelism"
    fcf.ToleranceValue = MBDCommands.parse_length_quantity_text("0.002 in")
    fcf.DiameterZone = False
    fcf.DatumReference = datum_a
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = "Face1"

    frame_obj, text_obj, leader_obj = MBDCommands.create_fcf_display(doc, fcf)
    cells = MBDCommands.fcf_cells(fcf)
    validation_errors = MBDValidation.validate_fcf(fcf)
    group_size = len(fcf.Group) if hasattr(fcf, "Group") else 0
    FreeCAD.closeDocument(doc.Name)

    if frame_obj is None or text_obj is None or leader_obj is None:
        raise AssertionError("parallelism FCF display was not fully created")

    if cells[-1] != "A" or len(cells) != 3:
        raise AssertionError("parallelism should use exactly one datum reference")

    if validation_errors:
        raise AssertionError(
            "parallelism FCF validation errors: {}".format(validation_errors)
        )

    if group_size < 5:
        raise AssertionError("parallelism FCF display helpers were not grouped")

    print("parallelism FCF display passed")


def perpendicularity_fcf_display_smoke():
    doc, box_obj = make_doc("MBDPerpendicularityFCFDisplaySmoke")

    import MBDCommands

    datum_a, _datum_b, _datum_c, _datum_system = make_datum_set(doc, box_obj)
    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_Perpendicularity"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Perpendicularity"
    fcf.ToleranceValue = MBDCommands.parse_length_quantity_text("0.002 in")
    fcf.DiameterZone = False
    fcf.DatumReference = datum_a
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = "Face1"

    frame_obj, text_obj, leader_obj = MBDCommands.create_fcf_display(doc, fcf)
    cells = MBDCommands.fcf_cells(fcf)
    validation_errors = MBDValidation.validate_fcf(fcf)
    group_size = len(fcf.Group) if hasattr(fcf, "Group") else 0
    FreeCAD.closeDocument(doc.Name)

    if frame_obj is None or text_obj is None or leader_obj is None:
        raise AssertionError("perpendicularity FCF display was not fully created")

    if cells[-1] != "A" or len(cells) != 3:
        raise AssertionError("perpendicularity should use exactly one datum reference")

    if validation_errors:
        raise AssertionError(
            "perpendicularity FCF validation errors: {}".format(validation_errors)
        )

    if group_size < 5:
        raise AssertionError("perpendicularity FCF display helpers were not grouped")

    print("perpendicularity FCF display passed")


def profile_fcf_display_smoke():
    doc, box_obj = make_doc("MBDProfileFCFDisplaySmoke")

    import MBDCommands

    preferred_point = FreeCAD.Vector(5, 10, 30)
    box_obj.Shape = box_obj.Shape.cut(
        Part.makeCylinder(
            3,
            15,
            preferred_point,
            FreeCAD.Vector(0, 0, -1)
        )
    )
    doc.recompute()

    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_Profile"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Profile"
    fcf.ToleranceValue = MBDCommands.parse_length_quantity_text("0.002 in")
    fcf.DiameterZone = False
    fcf.ProfileAllOver = True
    fcf.DatumSystem = None
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = ""

    frame_obj, text_obj, leader_obj = MBDCommands.create_fcf_display(doc, fcf)
    cells = MBDCommands.fcf_cells(fcf)
    validation_errors = MBDValidation.validate_fcf(fcf)
    group_size = len(fcf.Group) if hasattr(fcf, "Group") else 0
    attachment = fcf_attachment_point(fcf)
    attachment_distance = (
        Part.Vertex(attachment).distToShape(box_obj.Shape)[0]
        if attachment is not None else None
    )
    FreeCAD.closeDocument(doc.Name)

    if frame_obj is None or text_obj is None or leader_obj is None:
        raise AssertionError("profile FCF display was not fully created")

    if "ALL OVER" not in cells:
        raise AssertionError("profile all-over FCF should include ALL OVER cell")

    if len(cells) != 3:
        raise AssertionError("profile all-over without datum should use only symbol, value, and all-over cells")

    if validation_errors:
        raise AssertionError(
            "profile FCF validation errors: {}".format(validation_errors)
        )

    if group_size < 4:
        raise AssertionError("profile FCF display helpers were not grouped")

    if attachment is None or attachment_distance > 1e-7:
        raise AssertionError(
            "profile all-over leader does not touch the controlled body"
        )

    if (attachment - preferred_point).Length <= 1e-7:
        raise AssertionError(
            "profile all-over leader remained on the bounding-box envelope"
        )

    print("profile FCF display passed")


def line_profile_fcf_display_smoke():
    doc, box_obj = make_doc("MBDLineProfileFCFDisplaySmoke")

    import MBDCommands

    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_LineProfile"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "LineProfile"
    fcf.ToleranceValue = MBDCommands.parse_length_quantity_text("0.002 in")
    fcf.DiameterZone = False
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = "Edge1"

    frame_obj, text_obj, leader_obj = MBDCommands.create_fcf_display(doc, fcf)
    cells = MBDCommands.fcf_cells(fcf)
    validation_errors = MBDValidation.validate_fcf(fcf)
    grouped_labels = [
        getattr(obj, "Label", "")
        for obj in getattr(fcf, "Group", [])
    ]
    FreeCAD.closeDocument(doc.Name)

    if frame_obj is None or text_obj is None or leader_obj is None:
        raise AssertionError("line profile FCF display was not fully created")

    if cells[0] != "⌒":
        raise AssertionError("line profile should use the profile-of-line FCF cell")

    if not any("Profile of a LineSymbol" in label for label in grouped_labels):
        raise AssertionError("line profile drawn symbol was not grouped")

    if validation_errors:
        raise AssertionError(
            "line profile FCF validation errors: {}".format(validation_errors)
        )

    FreeCAD.Console.PrintMessage("line profile FCF display passed\n")


def flatness_fcf_exterior_leader_smoke():
    doc, box_obj = make_doc("MBDFlatnessFCFExteriorLeaderSmoke")

    import MBDCommands

    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_Flatness"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Flatness"
    fcf.ToleranceValue = MBDCommands.parse_length_quantity_text("0.002 in")
    fcf.DiameterZone = False
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = "Face1"
    point = MBDCommands.referenced_subelement_center(box_obj, "Face1")
    bbox = MBDCommands.document_shape_bound_box(doc)
    frame_obj, _text_obj, _leader_obj = MBDCommands.create_fcf_display(doc, fcf)
    frame_center = frame_obj.Shape.BoundBox.Center
    outside_x = (
        frame_center.x <= bbox.XMin
        or frame_center.x >= bbox.XMax
    )
    leader_crosses_box = (
        min(point.x, frame_center.x) < bbox.XMax - 1e-6
        and max(point.x, frame_center.x) > bbox.XMin + 1e-6
    )
    FreeCAD.closeDocument(doc.Name)

    if not outside_x:
        raise AssertionError("flatness FCF was not placed outside the box in X")

    if leader_crosses_box:
        raise AssertionError("flatness leader crosses through the box interior")

    print("flatness FCF exterior leader passed")


def exterior_direction_centroid_smoke():
    doc, box_obj = make_doc("MBDExteriorDirectionCentroidSmoke")

    import MBDCommands

    point = MBDCommands.referenced_subelement_center(box_obj, "Face1")
    doc_center, _doc_size = MBDCommands.document_shape_center_and_size(doc)
    inward = doc_center - point
    outward = point - doc_center
    resolved = MBDCommands.exterior_direction_from_point(doc, point, inward)
    FreeCAD.closeDocument(doc.Name)

    if resolved is None or resolved.dot(outward) <= 0:
        raise AssertionError("exterior direction did not resolve away from centroid")

    print("exterior direction centroid passed")


def oriented_face_normals_smoke():
    doc, box_obj = make_doc("MBDOrientedFaceNormalsSmoke")

    import MBDCommands

    doc_center, _doc_size = MBDCommands.document_shape_center_and_size(doc)

    for index, _face in enumerate(box_obj.Shape.Faces, start=1):
        subelement = "Face{}".format(index)
        face_center = MBDCommands.referenced_subelement_center(box_obj, subelement)
        normal = MBDCommands.outward_normal_from_reference(
            doc,
            box_obj,
            subelement
        )

        if normal is None:
            raise AssertionError("no normal resolved for {}".format(subelement))

        outward = face_center - doc_center

        if outward.Length <= 1e-9:
            continue

        if normal.dot(outward) <= 0:
            raise AssertionError(
                "{} normal points inward: normal {}, outward {}".format(
                    subelement,
                    normal,
                    outward
                )
            )

    FreeCAD.closeDocument(doc.Name)
    print("oriented face normals passed")


def surface_solid_probe_smoke():
    doc, box_obj = make_doc("MBDSurfaceSolidProbeSmoke")

    import MBDCommands

    doc_center, _doc_size = MBDCommands.document_shape_center_and_size(doc)

    for index, _face in enumerate(box_obj.Shape.Faces, start=1):
        subelement = "Face{}".format(index)
        point = MBDCommands.referenced_subelement_center(box_obj, subelement)
        outward = point - doc_center

        if outward.Length <= 1e-9:
            continue

        outward.normalize()
        inward = outward.negative()
        outward_hit = MBDCommands.distance_to_enter_owner_solid(
            box_obj,
            point,
            outward
        )
        inward_hit = MBDCommands.distance_to_enter_owner_solid(
            box_obj,
            point,
            inward
        )

        if outward_hit is not None:
            raise AssertionError(
                "{} outward direction hit solid at {}".format(
                    subelement,
                    outward_hit
                )
            )

        if inward_hit is None:
            raise AssertionError(
                "{} inward direction did not hit solid".format(subelement)
            )

    FreeCAD.closeDocument(doc.Name)
    print("surface solid probe passed")


def pmi_text_height_ignores_helpers_smoke():
    doc, box_obj = make_doc("MBDTextHeightIgnoresHelpersSmoke")

    import MBDCommands

    base_height = MBDCommands.pmi_text_height(doc)
    fcf = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_FCF_Flatness"
    )
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = "Flatness"
    fcf.ToleranceValue = MBDCommands.parse_length_quantity_text("0.002 in")
    fcf.DiameterZone = False
    fcf.ControlledObject = box_obj
    fcf.ControlledSubelement = "Face1"
    MBDCommands.create_fcf_display(doc, fcf)
    after_height = MBDCommands.pmi_text_height(doc)

    body = doc.addObject("PartDesign::Body", "Body")
    feature1 = body.newObject("PartDesign::Feature", "Feature1")
    feature1.Shape = Part.makeBox(5, 5, 5)
    feature2 = body.newObject("PartDesign::Feature", "Feature2")
    feature2.Shape = Part.makeBox(6, 6, 6)
    body.Tip = feature2
    doc.recompute()
    model_objects = MBDCommands.document_model_shape_objects(doc)

    if body not in model_objects:
        raise AssertionError("Part Design body was excluded from model bounds")

    if feature1 in model_objects or feature2 in model_objects:
        raise AssertionError(
            "intermediate Part Design features were included in model bounds"
        )

    FreeCAD.closeDocument(doc.Name)

    if abs(base_height - after_height) > 1e-9:
        raise AssertionError(
            "PMI text height changed after helpers: {} -> {}".format(
                base_height,
                after_height
            )
        )

    print("PMI text height ignores helpers passed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=[
            "datum-only",
            "fcf-no-diameter",
            "fcf-diameter",
            "all-fcfs",
            "stale-cancel",
            "basic-dimension-projection",
            "semantic-dimension",
            "dimension-semantic-rules",
            "dimension-export",
            "datum-target-export",
            "datum-target-sufficiency",
            "common-datum-system-validation",
            "common-datum-export",
            "display-layout-metadata",
            "single-item-fcf-layout",
            "single-item-datum-feature-layout",
            "single-item-dimension-layout",
            "global-geometry-link-scope",
            "fcf-rule-validation",
            "dimension-reference-patterns",
            "basic-size-dimension-requires-profile",
            "cylinder-axis-dimensions",
            "position-fcf-hole-opening-direction",
            "radius-dimension-display",
            "annotation-display-shape",
            "preferred-display-offset",
            "gdt-symbol-table",
            "grouped-display-helpers",
            "fcf-tolerance-units",
            "fcf-below-dimension",
            "flatness-fcf-display",
            "parallelism-fcf-display",
            "perpendicularity-fcf-display",
            "profile-fcf-display",
            "line-profile-fcf-display",
            "flatness-fcf-exterior-leader",
            "exterior-direction-centroid",
            "oriented-face-normals",
            "surface-solid-probe",
            "pmi-text-height-ignores-helpers",
        ],
        default="datum-only"
    )
    parser.add_argument(
        "--output",
        default="/tmp/mbd_headless_smoke.step"
    )
    parser.add_argument(
        "--controlled-subelement",
        default="Face1"
    )
    args = parser.parse_args()

    if args.mode == "basic-dimension-projection":
        basic_dimension_projection_smoke()
    elif args.mode == "semantic-dimension":
        semantic_dimension_smoke()
    elif args.mode == "dimension-semantic-rules":
        dimension_semantic_rules_smoke()
    elif args.mode == "dimension-export":
        dimension_export_smoke(args.output)
    elif args.mode == "datum-target-export":
        datum_target_export_smoke(args.output)
    elif args.mode == "datum-target-sufficiency":
        datum_target_sufficiency_smoke()
    elif args.mode == "common-datum-system-validation":
        common_datum_system_validation_smoke()
    elif args.mode == "common-datum-export":
        common_datum_export_smoke(args.output)
    elif args.mode == "display-layout-metadata":
        display_layout_metadata_smoke()
    elif args.mode == "single-item-fcf-layout":
        single_item_fcf_layout_smoke()
    elif args.mode == "single-item-datum-feature-layout":
        single_item_datum_feature_layout_smoke()
    elif args.mode == "single-item-dimension-layout":
        single_item_dimension_layout_smoke()
    elif args.mode == "global-geometry-link-scope":
        global_geometry_link_scope_smoke()
    elif args.mode == "fcf-rule-validation":
        fcf_rule_validation_smoke()
    elif args.mode == "dimension-reference-patterns":
        dimension_reference_patterns_smoke()
    elif args.mode == "basic-size-dimension-requires-profile":
        basic_size_dimension_requires_profile_smoke()
    elif args.mode == "cylinder-axis-dimensions":
        cylinder_axis_dimension_smoke()
    elif args.mode == "position-fcf-hole-opening-direction":
        position_fcf_hole_opening_direction_smoke()
    elif args.mode == "radius-dimension-display":
        radius_dimension_display_smoke()
    elif args.mode == "annotation-display-shape":
        annotation_display_shape_smoke()
    elif args.mode == "preferred-display-offset":
        preferred_display_offset_clears_model_smoke()
    elif args.mode == "gdt-symbol-table":
        gdt_symbol_table_smoke()
    elif args.mode == "grouped-display-helpers":
        grouped_display_helpers_smoke()
    elif args.mode == "fcf-tolerance-units":
        fcf_tolerance_units_smoke()
    elif args.mode == "fcf-below-dimension":
        fcf_below_dimension_smoke()
    elif args.mode == "flatness-fcf-display":
        flatness_fcf_display_smoke()
    elif args.mode == "parallelism-fcf-display":
        parallelism_fcf_display_smoke()
    elif args.mode == "perpendicularity-fcf-display":
        perpendicularity_fcf_display_smoke()
    elif args.mode == "profile-fcf-display":
        profile_fcf_display_smoke()
    elif args.mode == "line-profile-fcf-display":
        line_profile_fcf_display_smoke()
    elif args.mode == "flatness-fcf-exterior-leader":
        flatness_fcf_exterior_leader_smoke()
    elif args.mode == "exterior-direction-centroid":
        exterior_direction_centroid_smoke()
    elif args.mode == "oriented-face-normals":
        oriented_face_normals_smoke()
    elif args.mode == "surface-solid-probe":
        surface_solid_probe_smoke()
    elif args.mode == "pmi-text-height-ignores-helpers":
        pmi_text_height_ignores_helpers_smoke()
    elif args.mode == "stale-cancel":
        stale_cancel_smoke(args.output)
    else:
        export_smoke(args.mode, args.output, args.controlled_subelement)

    return 0


if __name__ == "__main__":
    sys.exit(main())
