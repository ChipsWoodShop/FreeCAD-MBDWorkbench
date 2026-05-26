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
import MBDDimension
import MBDValidation
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


def semantic_dimension_smoke():
    doc, box_obj = make_doc("MBDSemanticDimensionSmoke")

    point_a = doc.addObject("Part::Feature", "PointA")
    point_a.Shape = Part.Vertex(0, 0, 0)

    point_b = doc.addObject("Part::Feature", "PointB")
    point_b.Shape = Part.Vertex(25.4, 0, 0)
    doc.recompute()

    dim = doc.addObject("App::DocumentObjectGroupPython", "MBD_Dimension001")
    MBDDimension.MBDDimension(dim)
    dim.DimensionPurpose = "PlusMinus"
    dim.DimensionKind = "Linear"
    dim.MeasurementType = "X"
    dim.NominalValue = 25.4
    dim.UpperTolerance = 0.127
    dim.LowerTolerance = 0.127
    dim.ReferenceObject1 = point_a
    dim.ReferenceObject2 = point_b
    MBDDimension.update_dimension_signature(dim)

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
            "semantic-dimension",
            "dimension-reference-patterns",
            "cylinder-axis-dimensions",
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
    elif args.mode == "dimension-reference-patterns":
        dimension_reference_patterns_smoke()
    elif args.mode == "cylinder-axis-dimensions":
        cylinder_axis_dimension_smoke()
    elif args.mode == "stale-cancel":
        stale_cancel_smoke(args.output)
    else:
        export_smoke(args.mode, args.output, args.controlled_subelement)

    return 0


if __name__ == "__main__":
    sys.exit(main())
