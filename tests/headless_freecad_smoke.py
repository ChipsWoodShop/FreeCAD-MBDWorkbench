#!/usr/bin/env python3

import argparse
import os
import sys


WORKBENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKBENCH_DIR)

import FreeCAD
import Part

import MBDExporter
import MBDBasicDimension
from MBDDatum import MBDDatumFeature, update_geometry_signature
from MBDDatumSystem import MBDDatumSystem
from MBDFeatureControlFrame import MBDFeatureControlFrame


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
    obj = doc.addObject("App::FeaturePython", "MBD_DatumFeature_" + label)
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
    datum_system.PrimaryDatum = datum_a
    datum_system.SecondaryDatum = datum_b
    datum_system.TertiaryDatum = datum_c

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


def export_smoke(mode, output_path, controlled_subelement):
    MBDExporter.QtGui.QMessageBox = AcceptMessageBox

    doc, box_obj = make_doc("MBDHeadlessSmoke")
    _, _, _, datum_system = make_datum_set(doc, box_obj)

    if mode == "fcf-no-diameter":
        add_position_fcf(doc, box_obj, datum_system, False, controlled_subelement)
    elif mode == "fcf-diameter":
        add_position_fcf(doc, box_obj, datum_system, True, controlled_subelement)

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=[
            "datum-only",
            "fcf-no-diameter",
            "fcf-diameter",
            "stale-cancel",
            "basic-dimension-projection",
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
    elif args.mode == "stale-cancel":
        stale_cancel_smoke(args.output)
    else:
        export_smoke(args.mode, args.output, args.controlled_subelement)

    return 0


if __name__ == "__main__":
    sys.exit(main())
