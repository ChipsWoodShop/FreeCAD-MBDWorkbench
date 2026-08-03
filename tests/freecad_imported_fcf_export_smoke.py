"""Headless smoke test for re-exporting simple imported AP242 FCFs.

This covers imported flatness/profile tolerances that are safe to create as
native PMI but must bypass OCCT's direct geometric-tolerance writer because
that path produced null semantic references for imported topology.
"""

import os
import re
import sys
import tempfile
import traceback


WORKBENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if WORKBENCH_DIR not in sys.path:
    sys.path.insert(0, WORKBENCH_DIR)

import FreeCAD
import Part

from freecad.mbd_workbench import MBDExporter
from freecad.mbd_workbench.MBDDatum import MBDDatumFeature, update_geometry_signature
from freecad.mbd_workbench.MBDDatumSystem import MBDDatumSystem
from freecad.mbd_workbench.MBDFeatureControlFrame import MBDFeatureControlFrame
from freecad.mbd_workbench.MBDPMI import set_pmi_import_metadata


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


def add_datum(doc, shape_obj, label, subelement):
    datum = doc.addObject(
        "App::DocumentObjectGroupPython",
        "MBD_DatumFeature_" + label
    )
    MBDDatumFeature(datum)
    datum.DatumLabel = label
    datum.ReferencedObject = shape_obj
    datum.ReferencedSubelement = subelement
    update_geometry_signature(datum)
    return datum


def add_datum_system(doc, datums, name):
    datum_system = doc.addObject("App::FeaturePython", name)
    MBDDatumSystem(datum_system)
    datum_system.PrimaryDatums = datums
    datum_system.SecondaryDatums = []
    datum_system.TertiaryDatums = []
    return datum_system


def add_imported_fcf(
    doc,
    shape_obj,
    tolerance_type,
    subelement,
    datum_system=None,
    controlled_subelements=None
):
    fcf = doc.addObject("App::FeaturePython", "MBD_FCF_" + tolerance_type)
    MBDFeatureControlFrame(fcf)
    fcf.ToleranceType = tolerance_type
    fcf.ToleranceValue = 0.127
    fcf.DiameterZone = False
    fcf.ProfileAllOver = False
    fcf.DatumSystem = datum_system
    fcf.DatumReference = None
    fcf.ControlledObject = shape_obj
    fcf.ControlledSubelement = subelement
    if controlled_subelements is not None:
        fcf.ControlledSubelementList = controlled_subelements
    fcf.ReferencedObject = shape_obj
    fcf.ReferencedSubelement = subelement
    update_geometry_signature(fcf)
    set_pmi_import_metadata(
        fcf,
        "/tmp/imported_fcf_source.step",
        "#100",
        tolerance_type.upper() + "_TOLERANCE",
        "Native"
    )
    return fcf


def first_face_with_surface_name(shape_obj, token):
    token = token.lower()

    for index, face in enumerate(shape_obj.Shape.Faces, start=1):
        surface_name = face.Surface.__class__.__name__.lower()

        if token in surface_name:
            return "Face{}".format(index)

    raise RuntimeError(
        "Could not find a {} face on {}.".format(token, shape_obj.Name)
    )


def faces_with_surface_name(shape_obj, token):
    token = token.lower()
    faces = []

    for index, face in enumerate(shape_obj.Shape.Faces, start=1):
        surface_name = face.Surface.__class__.__name__.lower()

        if token in surface_name:
            faces.append("Face{}".format(index))

    if not faces:
        raise RuntimeError(
            "Could not find a {} face on {}.".format(token, shape_obj.Name)
        )

    return faces


def main():
    MBDExporter.QtGui.QMessageBox = AcceptMessageBox

    doc = FreeCAD.newDocument("ImportedFCFExportSmoke")
    shape_obj = doc.addObject("Part::Feature", "TestShape")
    box = Part.makeBox(10, 10, 10)
    cylinder = Part.makeCylinder(2.5, 10, FreeCAD.Vector(5, 5, 10))
    shape_obj.Shape = box.fuse(cylinder).removeSplitter()
    doc.recompute()
    cylindrical_face = first_face_with_surface_name(shape_obj, "cylinder")
    planar_faces = faces_with_surface_name(shape_obj, "plane")
    face_a = planar_faces[0]
    face_b = planar_faces[min(1, len(planar_faces) - 1)]
    face_c = planar_faces[min(2, len(planar_faces) - 1)]
    face_d = planar_faces[min(3, len(planar_faces) - 1)]
    face_e = planar_faces[min(4, len(planar_faces) - 1)]
    face_f = planar_faces[min(5, len(planar_faces) - 1)]

    datum_a = add_datum(doc, shape_obj, "A", face_a)
    datum_b = add_datum(doc, shape_obj, "B", face_b)
    datum_cylinder = add_datum(doc, shape_obj, "C", cylindrical_face)
    datum_system_a = add_datum_system(
        doc,
        [datum_a],
        "MBD_DatumSystem_A"
    )
    datum_system_a_b = add_datum_system(
        doc,
        [datum_a, datum_b],
        "MBD_DatumSystem_A_B"
    )
    datum_system_c = add_datum_system(
        doc,
        [datum_cylinder],
        "MBD_DatumSystem_C"
    )
    add_imported_fcf(doc, shape_obj, "Flatness", face_c)
    modifier_profile = add_imported_fcf(doc, shape_obj, "Profile", face_d)
    modifier_profile.TangentPlaneModifier = True
    modifier_profile.StatisticalToleranceModifier = True
    modifier_profile.CommonZoneModifier = True
    modifier_profile.MaximumToleranceValueEnabled = True
    modifier_profile.MaximumToleranceValue = 2.032
    modifier_profile.UnitBasisToleranceEnabled = True
    modifier_profile.UnitBasisType = "Circular"
    modifier_profile.UnitBasisPrimaryLength = 25.4
    modifier_profile.UnitBasisSecondaryLength = 25.4
    modifier_profile.UnequallyDisposedZone = True
    modifier_profile.UnequallyDisposedOffset = 0.0254
    modifier_profile.NonUniformToleranceZone = True
    add_imported_fcf(
        doc,
        shape_obj,
        "Profile",
        face_e,
        datum_system=datum_system_a,
        controlled_subelements=[face_e, face_f]
    )
    add_imported_fcf(
        doc,
        shape_obj,
        "LineProfile",
        face_f,
        datum_system=datum_system_a_b
    )
    add_imported_fcf(
        doc,
        shape_obj,
        "Parallelism",
        face_c,
        datum_system=datum_system_a
    )
    add_imported_fcf(
        doc,
        shape_obj,
        "Perpendicularity",
        face_d,
        datum_system=datum_system_a
    )
    add_imported_fcf(
        doc,
        shape_obj,
        "Angularity",
        face_e,
        datum_system=datum_system_a
    )
    modifier_position = add_imported_fcf(
        doc,
        shape_obj,
        "Position",
        face_f,
        datum_system=datum_system_a
    )
    modifier_position.MaterialConditionModifier = "MMC"
    modifier_position.ProjectedToleranceZone = True
    modifier_position.ProjectedToleranceHeight = 6.35
    add_imported_fcf(
        doc,
        shape_obj,
        "Circularity",
        cylindrical_face
    )
    add_imported_fcf(
        doc,
        shape_obj,
        "Cylindricity",
        cylindrical_face
    )
    add_imported_fcf(
        doc,
        shape_obj,
        "Straightness",
        cylindrical_face
    )
    circular_runout = add_imported_fcf(
        doc,
        shape_obj,
        "CircularRunout",
        cylindrical_face,
        datum_system=datum_system_c
    )
    circular_runout.RunoutOrientationAngle = 30.0
    total_runout = add_imported_fcf(
        doc,
        shape_obj,
        "TotalRunout",
        cylindrical_face,
        datum_system=datum_system_c
    )
    total_runout.RunoutOrientationAngle = 45.0
    doc.recompute()

    output_path = os.path.join(
        tempfile.gettempdir(),
        "mbd_imported_fcf_export_smoke.step"
    )

    if os.path.exists(output_path):
        os.remove(output_path)

    FreeCAD.setActiveDocument(doc.Name)
    ok = MBDExporter.export_ap242(output_path)

    if not ok:
        raise RuntimeError("MBDExporter.export_ap242 returned false.")

    with open(output_path, "r", encoding="utf-8", errors="replace") as handle:
        step_text = handle.read()

    if "/*   NUL REF   */" in step_text:
        raise RuntimeError("Exported STEP contains null semantic references.")

    for expected in (
        "FLATNESS_TOLERANCE",
        "SURFACE_PROFILE_TOLERANCE",
        "LINE_PROFILE_TOLERANCE",
        "PARALLELISM_TOLERANCE",
        "PERPENDICULARITY_TOLERANCE",
        "ANGULARITY_TOLERANCE",
        "ROUNDNESS_TOLERANCE",
        "CYLINDRICITY_TOLERANCE",
        "STRAIGHTNESS_TOLERANCE",
        "CIRCULAR_RUNOUT_TOLERANCE",
        "TOTAL_RUNOUT_TOLERANCE",
        "RUNOUT_ZONE_DEFINITION",
        "RUNOUT_ZONE_ORIENTATION",
        "POSITION_TOLERANCE",
        "TOLERANCE_ZONE_FORM",
        "TOLERANCE_ZONE",
        "GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE",
        "DATUM_SYSTEM",
        "COMMON_DATUM_LIST",
        "GEOMETRIC_TOLERANCE_WITH_MODIFIERS",
        "GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE",
        "GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT",
        "GEOMETRIC_TOLERANCE_WITH_DEFINED_AREA_UNIT",
        "UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE",
        "NON_UNIFORM_ZONE_DEFINITION",
        "PROJECTED_ZONE_DEFINITION",
    ):
        if expected not in step_text:
            raise RuntimeError("Expected {} in exported STEP.".format(expected))

    geometric_usage_aspects = re.findall(
        r"GEOMETRIC_ITEM_SPECIFIC_USAGE\('[^']*','[^']*',#(\d+),#\d+,#\d+\)",
        step_text
    )
    repeated_aspects = {
        aspect_id
        for aspect_id in geometric_usage_aspects
        if geometric_usage_aspects.count(aspect_id) > 1
    }

    if not repeated_aspects:
        raise RuntimeError(
            "Expected a multi-attachment imported FCF shape aspect."
        )

    print("Imported simple FCF export smoke passed.")
    FreeCAD.closeDocument(doc.Name)


try:
    main()
except Exception:
    traceback.print_exc()
    raise
