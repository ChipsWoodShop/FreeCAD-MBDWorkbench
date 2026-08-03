#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest


WORKBENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKBENCH_DIR)

from freecad.mbd_workbench import MBDImporter


class MBDImporterTests(unittest.TestCase):

    def write_step(self, text):
        handle = tempfile.NamedTemporaryFile(
            "w",
            suffix=".step",
            delete=False
        )
        with handle:
            handle.write(text)

        self.addCleanup(lambda: os.path.exists(handle.name) and os.remove(handle.name))
        return handle.name

    def test_semantic_import_preview_recognizes_native_candidates(self):
        path = self.write_step("""ISO-10303-21;
DATA;
#1 = DATUM('','',#26,.F.,'A');
#2 = DATUM('','',#26,.F.,'B');
#3 = DATUM_REFERENCE_COMPARTMENT('','',#26,.F.,#1,$);
#4 = DATUM_REFERENCE_COMPARTMENT('','',#26,.F.,#2,$);
#5 = DATUM_SYSTEM('','',#26,.F.,(#3,#4));
#6 = (GEOMETRIC_TOLERANCE('','',#8,#9)
GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE((#5))
GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT(#10)
POSITION_TOLERANCE());
#7 = DIMENSIONAL_SIZE(#11,'diameter');
#8 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.1),#12);
#9 = SHAPE_ASPECT('','',#13,.T.);
#10 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(10.0),#12);
ENDSEC;
END-ISO-10303-21;
""")
        preview = MBDImporter.semantic_import_preview(path)

        self.assertEqual(
            ["A", "B"],
            [
                datum["label"]
                for datum in preview["candidates"]["datums"]
            ]
        )
        self.assertEqual(
            "A | B",
            preview["candidates"]["datum_systems"][0]["label"]
        )
        self.assertEqual(
            "Position",
            preview["candidates"]["fcfs"][0]["tolerance_type"]
        )
        self.assertIn(
            "GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT",
            preview["candidates"]["fcfs"][0]["modifiers"]
        )
        self.assertEqual(
            "Diameter",
            preview["candidates"]["dimensions"][0]["dimension_kind"]
        )

    def test_semantic_import_preview_reads_fcf_modifier_values(self):
        path = self.write_step("""ISO-10303-21;
DATA;
#1 = DATUM('','',#26,.F.,'A');
#2 = DATUM_REFERENCE_COMPARTMENT('','',#26,.F.,#1,$);
#3 = DATUM_SYSTEM('','',#26,.F.,(#2));
#4 = ADVANCED_FACE('',(),#20,.T.);
#5 = SHAPE_ASPECT('','',#26,.T.);
#6 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#5,#30,#4);
#7 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.127),#40);
#8 = (GEOMETRIC_TOLERANCE('','',#7,#5)
GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE((#3))
GEOMETRIC_TOLERANCE_WITH_MODIFIERS((.MAXIMUM_MATERIAL_REQUIREMENT.,.TANGENT_PLANE.,.STATISTICAL_TOLERANCE.,.COMMON_ZONE.))
GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE(#9)
GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT(#10)
GEOMETRIC_TOLERANCE_WITH_DEFINED_AREA_UNIT(.CIRCULAR.,#11)
UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE(#12)
SURFACE_PROFILE_TOLERANCE());
#9 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(2.032),#40);
#10 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(25.4),#40);
#11 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(25.4),#40);
#12 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.0254),#40);
#13 = TOLERANCE_ZONE_FORM('non uniform');
#14 = TOLERANCE_ZONE('', '', #26, .F., (#8), #13);
#15 = NON_UNIFORM_ZONE_DEFINITION(#14);
#16 = TOLERANCE_ZONE_FORM('cylindrical or circular');
#17 = TOLERANCE_ZONE('', '', #26, .F., (#8), #16);
#18 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(6.35),#40);
#19 = PROJECTED_ZONE_DEFINITION(#17,(),#5,#18);
ENDSEC;
END-ISO-10303-21;
""")
        preview = MBDImporter.semantic_import_preview(path)
        values = preview["candidates"]["fcfs"][0]["modifier_values"]

        self.assertEqual("MMC", values["material_condition"])
        self.assertTrue(values["tangent_plane"])
        self.assertTrue(values["statistical_tolerance"])
        self.assertTrue(values["common_zone"])
        self.assertAlmostEqual(2.032, values["maximum_tolerance"])
        self.assertEqual("Circular", values["unit_basis"]["type"])
        self.assertAlmostEqual(25.4, values["unit_basis"]["primary"])
        self.assertAlmostEqual(25.4, values["unit_basis"]["secondary"])
        self.assertAlmostEqual(0.0254, values["unequally_disposed"])
        self.assertAlmostEqual(6.35, values["projected_zone_height"])
        self.assertTrue(values["non_uniform_zone"])
        self.assertEqual([], values["unsupported"])

    def test_semantic_import_preview_reads_affected_plane_association(self):
        path = self.write_step("""ISO-10303-21;
DATA;
#1 = DATUM('','',#26,.F.,'A');
#2 = DATUM_REFERENCE_COMPARTMENT('','',#26,.F.,#1,$);
#3 = DATUM_SYSTEM('','',#26,.F.,(#2));
#4 = ADVANCED_FACE('',(),#20,.T.);
#5 = SHAPE_ASPECT('controlled face','',#26,.T.);
#6 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#5,#30,#4);
#7 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.127),#40);
#8 = (GEOMETRIC_TOLERANCE('','',#7,#5)
GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE((#3))
LINE_PROFILE_TOLERANCE());
#9 = EDGE_CURVE('',#10,#11,#12,.T.);
#13 = SHAPE_ASPECT('affected plane line','representative plane element',#26,.T.);
#14 = GEOMETRIC_ITEM_SPECIFIC_USAGE('affected plane line','',#13,#30,#9);
#15 = SHAPE_ASPECT_RELATIONSHIP('affected plane association','affected plane association',#5,#13);
ENDSEC;
END-ISO-10303-21;
""")
        preview = MBDImporter.semantic_import_preview(path)
        affected_usages = preview["candidates"]["fcfs"][0]["affected_plane_usages"]

        self.assertEqual(1, len(affected_usages))
        self.assertEqual("Edge1", affected_usages[0]["subelement"])

    def test_semantic_import_preview_reads_runout_orientation_angle(self):
        path = self.write_step("""ISO-10303-21;
DATA;
#1 = DATUM('','',#26,.F.,'A');
#2 = DATUM_REFERENCE_COMPARTMENT('','',#26,.F.,#1,$);
#3 = DATUM_SYSTEM('','',#26,.F.,(#2));
#4 = ADVANCED_FACE('',(),#20,.T.);
#5 = SHAPE_ASPECT('controlled face','',#26,.T.);
#6 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#5,#30,#4);
#7 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.127),#40);
#8 = (GEOMETRIC_TOLERANCE('','',#7,#5)
GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE((#3))
CIRCULAR_RUNOUT_TOLERANCE());
#9 = TOLERANCE_ZONE_FORM('cylindrical or circular');
#10 = TOLERANCE_ZONE('', '', #26, .F., (#8), #9);
#11 = (RUNOUT_ZONE_DEFINITION(#10,())
RUNOUT_ZONE_ORIENTATION(#12));
#12 = PLANE_ANGLE_MEASURE_WITH_UNIT(PLANE_ANGLE_MEASURE(0.7853981633974483),#41);
ENDSEC;
END-ISO-10303-21;
""")
        preview = MBDImporter.semantic_import_preview(path)
        values = preview["candidates"]["fcfs"][0]["modifier_values"]

        self.assertAlmostEqual(45.0, values["runout_orientation_angle"])

    def test_semantic_import_preview_reports_deferred_entities(self):
        path = self.write_step("""ISO-10303-21;
DATA;
#1 = DIMENSIONAL_SIZE_WITH_PATH(#2,'path size',#3);
#2 = SHAPE_ASPECT('','',#4,.T.);
#3 = SHAPE_ASPECT('','',#4,.T.);
#5 = ANNOTATION_PLACEHOLDER_OCCURRENCE('','',#6,#7);
ENDSEC;
END-ISO-10303-21;
""")
        preview = MBDImporter.semantic_import_preview(path)
        report = MBDImporter.format_semantic_import_preview(preview)

        self.assertFalse(
            preview["candidates"]["dimensions"][0]["can_create_native"]
        )
        self.assertIn("DIMENSIONAL_SIZE_WITH_PATH", report)
        self.assertIn("ANNOTATION_PLACEHOLDER_OCCURRENCE", report)

    def test_semantic_import_preview_resolves_composite_dimension_geometry(self):
        path = self.write_step("""ISO-10303-21;
DATA;
#10 = ADVANCED_FACE('',(),#20,.T.);
#11 = ADVANCED_FACE('',(),#21,.T.);
#30 = SHAPE_ASPECT('','',#90,.T.);
#31 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#30,#100,#10);
#32 = SHAPE_ASPECT('','',#90,.T.);
#33 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#32,#100,#11);
#40 = COMPOSITE_SHAPE_ASPECT('','',#90,.T.);
#41 = SHAPE_ASPECT_RELATIONSHIP('',$,#40,#30);
#42 = SHAPE_ASPECT_RELATIONSHIP('',$,#40,#32);
#50 = DIMENSIONAL_SIZE(#40,'thickness');
ENDSEC;
END-ISO-10303-21;
""")
        preview = MBDImporter.semantic_import_preview(path)
        dimension = preview["candidates"]["dimensions"][0]

        self.assertEqual("Linear", dimension["dimension_kind"])
        self.assertEqual(
            ["Face1", "Face2"],
            [
                usage["subelement"]
                for usage in dimension["geometry_usages"]
            ]
        )

    def test_semantic_import_preview_reads_dimension_values(self):
        path = self.write_step("""ISO-10303-21;
DATA;
#10 = ADVANCED_FACE('',(),#20,.T.);
#30 = SHAPE_ASPECT('','',#90,.T.);
#31 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#30,#100,#10);
#40 = DIMENSIONAL_SIZE(#30,'diameter');
#50 = DIMENSIONAL_CHARACTERISTIC_REPRESENTATION(#40,#60);
#60 = SHAPE_DIMENSION_REPRESENTATION('',(#70),#90);
#70 = (LENGTH_MEASURE_WITH_UNIT() MEASURE_WITH_UNIT(POSITIVE_LENGTH_MEASURE(5.),#91) REPRESENTATION_ITEM('nominal value'));
#80 = PLUS_MINUS_TOLERANCE(#81,#40);
#81 = TOLERANCE_VALUE(#82,#83);
#82 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(-0.1),#91);
#83 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.2),#91);
ENDSEC;
END-ISO-10303-21;
""")
        preview = MBDImporter.semantic_import_preview(path)
        values = preview["candidates"]["dimensions"][0]["values"]

        self.assertEqual(5.0, values["nominal_value"])
        self.assertEqual(-0.1, values["lower_tolerance"])
        self.assertEqual(0.2, values["upper_tolerance"])

    def test_semantic_import_preview_scales_dimension_values_by_measure_unit(self):
        path = self.write_step("""ISO-10303-21;
DATA;
#10 = ADVANCED_FACE('',(),#20,.T.);
#30 = SHAPE_ASPECT('','',#90,.T.);
#31 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#30,#100,#10);
#40 = DIMENSIONAL_SIZE(#30,'diameter');
#50 = DIMENSIONAL_CHARACTERISTIC_REPRESENTATION(#40,#60);
#60 = SHAPE_DIMENSION_REPRESENTATION('',(#70),#90);
#70 = (LENGTH_MEASURE_WITH_UNIT() MEASURE_REPRESENTATION_ITEM() MEASURE_WITH_UNIT(LENGTH_MEASURE(5.),#91) REPRESENTATION_ITEM('nominal value'));
#80 = PLUS_MINUS_TOLERANCE(#81,#40);
#81 = TOLERANCE_VALUE(#82,#83);
#82 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(-0.1),#91);
#83 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.2),#91);
#91 = (CONVERSION_BASED_UNIT('inch',#94) LENGTH_UNIT() NAMED_UNIT(#95));
#92 = (LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.));
#94 = MEASURE_WITH_UNIT(LENGTH_MEASURE(25.4),#92);
ENDSEC;
END-ISO-10303-21;
""")
        preview = MBDImporter.semantic_import_preview(path)
        values = preview["candidates"]["dimensions"][0]["values"]

        self.assertAlmostEqual(127.0, values["nominal_value"])
        self.assertAlmostEqual(-2.54, values["lower_tolerance"])
        self.assertAlmostEqual(5.08, values["upper_tolerance"])

    def test_semantic_import_preview_resolves_composite_datum_geometry(self):
        path = self.write_step("""ISO-10303-21;
DATA;
#10 = ADVANCED_FACE('A_FACE',(),#20,.T.);
#11 = ADVANCED_FACE('B_FACE_1',(),#21,.T.);
#12 = ADVANCED_FACE('B_FACE_2',(),#22,.T.);
#13 = ADVANCED_FACE('C_FACE_1',(),#23,.T.);
#14 = ADVANCED_FACE('C_FACE_2',(),#24,.T.);
#34 = DATUM_FEATURE('Simple Datum.1',$,#90,.T.);
#35 = DATUM_FEATURE('Simple Datum.2',$,#90,.T.);
#36 = DATUM_FEATURE('Simple Datum.3',$,#90,.T.);
#37 = DATUM('',$,#90,.F.,'A');
#38 = DATUM('',$,#90,.F.,'B');
#39 = DATUM('',$,#90,.F.,'C');
#40 = SHAPE_ASPECT_RELATIONSHIP('',$,#34,#37);
#41 = SHAPE_ASPECT_RELATIONSHIP('',$,#35,#38);
#42 = SHAPE_ASPECT_RELATIONSHIP('',$,#36,#39);
#50 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','DATUM',#34,#100,#10);
#228 = COMPOSITE_SHAPE_ASPECT('','DATUM',#90,.F.);
#229 = COMPOSITE_SHAPE_ASPECT('','DATUM',#90,.F.);
#312 = SHAPE_ASPECT('','DATUM',#90,.F.);
#313 = SHAPE_ASPECT('','DATUM',#90,.F.);
#314 = SHAPE_ASPECT('','DATUM',#90,.F.);
#315 = SHAPE_ASPECT('','DATUM',#90,.F.);
#60 = SHAPE_ASPECT_RELATIONSHIP('',$,#228,#312);
#61 = SHAPE_ASPECT_RELATIONSHIP('',$,#228,#313);
#62 = SHAPE_ASPECT_RELATIONSHIP('',$,#229,#314);
#63 = SHAPE_ASPECT_RELATIONSHIP('',$,#229,#315);
#70 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','DATUM',#312,#100,#11);
#71 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','DATUM',#313,#100,#12);
#72 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','DATUM',#314,#100,#13);
#73 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','DATUM',#315,#100,#14);
ENDSEC;
END-ISO-10303-21;
""")
        preview = MBDImporter.semantic_import_preview(path)
        datums = {
            datum["label"]: datum
            for datum in preview["candidates"]["datums"]
        }

        self.assertTrue(datums["A"]["can_create_native"])
        self.assertTrue(datums["B"]["can_create_native"])
        self.assertTrue(datums["C"]["can_create_native"])
        self.assertEqual(
            ["Face1"],
            [
                usage["subelement"]
                for usage in datums["A"]["geometry_usages"]
            ]
        )
        self.assertEqual(
            ["Face2", "Face3"],
            [
                usage["subelement"]
                for usage in datums["B"]["geometry_usages"]
            ]
        )
        self.assertEqual(
            ["Face4", "Face5"],
            [
                usage["subelement"]
                for usage in datums["C"]["geometry_usages"]
            ]
        )

    def test_semantic_import_preview_resolves_common_datum_list_elements(self):
        path = self.write_step("""ISO-10303-21;
DATA;
#10 = ADVANCED_FACE('A_FACE',(),#20,.T.);
#11 = ADVANCED_FACE('B_FACE',(),#21,.T.);
#30 = DATUM_FEATURE('','',#90,.T.);
#31 = GEOMETRIC_ITEM_SPECIFIC_USAGE('A','',#30,#100,#10);
#32 = DATUM('','',#90,.F.,'A');
#33 = SHAPE_ASPECT_RELATIONSHIP('',$,#30,#32);
#40 = DATUM_FEATURE('','',#90,.T.);
#41 = GEOMETRIC_ITEM_SPECIFIC_USAGE('B','',#40,#100,#11);
#42 = DATUM('','',#90,.F.,'B');
#43 = SHAPE_ASPECT_RELATIONSHIP('',$,#40,#42);
#50 = DATUM_REFERENCE_ELEMENT($,$,$,.F.,#32,$);
#51 = DATUM_REFERENCE_ELEMENT($,$,$,.F.,#42,$);
#52 = DATUM_REFERENCE_COMPARTMENT('','',#90,.F.,COMMON_DATUM_LIST((#50,#51)));
#53 = DATUM_SYSTEM('','',#90,.F.,(#52));
ENDSEC;
END-ISO-10303-21;
""")
        preview = MBDImporter.semantic_import_preview(path)

        self.assertEqual(
            "A-B",
            preview["candidates"]["datum_systems"][0]["label"]
        )
        self.assertEqual(
            [["A", "B"]],
            preview["candidates"]["datum_systems"][0]["compartments"]
        )

    def test_semantic_import_preview_resolves_placed_datum_target_parameters(self):
        path = self.write_step("""ISO-10303-21;
DATA;
#10 = DATUM('','',#90,.F.,'C');
#11 = PLACED_DATUM_TARGET_FEATURE('','rectangle',#90,.T.,'1');
#12 = SHAPE_ASPECT_RELATIONSHIP('','datum target',#11,#10);
#20 = PROPERTY_DEFINITION('','',#11);
#21 = SHAPE_DEFINITION_REPRESENTATION(#20,#22);
#22 = SHAPE_REPRESENTATION_WITH_PARAMETERS('',(#30,#31,#40),#90);
#30 = (LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.25),#91)
REPRESENTATION_ITEM('target width'));
#31 = (LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(2.0),#91)
REPRESENTATION_ITEM('target length'));
#40 = AXIS2_PLACEMENT_3D('orientation',#41,#42,#43);
#41 = CARTESIAN_POINT('',(10.375,0.,1.175));
#42 = DIRECTION('',(1.,0.,0.));
#43 = DIRECTION('',(0.,1.,0.));
ENDSEC;
END-ISO-10303-21;
""")
        preview = MBDImporter.semantic_import_preview(path)
        datum = preview["candidates"]["datums"][0]
        target = preview["candidates"]["datum_targets"][0]

        self.assertTrue(datum["can_create_native"])
        self.assertEqual(["#11"], datum["target_refs"])
        self.assertEqual("C", target["parent_datum_label"])
        self.assertEqual("Rectangle", target["target_kind"])
        self.assertEqual("1", target["target_number"])
        self.assertTrue(target["can_create_native"])
        self.assertEqual(2.0, target["parameters"]["length"])
        self.assertEqual(1.25, target["parameters"]["width"])
        self.assertEqual(
            [10.375, 0.0, 1.175],
            target["parameters"]["placement"]["location"]
        )

    def test_native_datum_creation_helper_creates_datums_and_systems(self):
        try:
            import FreeCAD
            import Part
        except Exception:
            self.skipTest("FreeCAD is not available in this Python")

        path = self.write_step("""ISO-10303-21;
DATA;
#10 = ADVANCED_FACE('',(),#20,.T.);
#11 = ADVANCED_FACE('',(),#21,.T.);
#30 = DATUM_FEATURE('','',#90,.T.);
#31 = GEOMETRIC_ITEM_SPECIFIC_USAGE('A','',#30,#100,#10);
#32 = DATUM('','',#90,.F.,'A');
#33 = SHAPE_ASPECT_RELATIONSHIP('',$,#30,#32);
#40 = DATUM_FEATURE('','',#90,.T.);
#41 = GEOMETRIC_ITEM_SPECIFIC_USAGE('B','',#40,#100,#11);
#42 = DATUM('','',#90,.F.,'B');
#43 = SHAPE_ASPECT_RELATIONSHIP('',$,#40,#42);
#50 = DATUM_REFERENCE_COMPARTMENT('','',#90,.F.,#32,$);
#51 = DATUM_REFERENCE_COMPARTMENT('','',#90,.F.,#42,$);
#52 = DATUM_SYSTEM('','',#90,.F.,(#50,#51));
ENDSEC;
END-ISO-10303-21;
""")
        doc = FreeCAD.newDocument("MBDImporterUnit")
        shape_obj = doc.addObject("Part::Feature", "ImportedShape")
        shape_obj.Shape = Part.makeBox(10, 20, 30)

        try:
            preview = MBDImporter.semantic_import_preview(path)
            result = MBDImporter.create_native_datums_and_systems_from_preview(
                doc,
                shape_obj,
                preview
            )

            self.assertEqual(2, len(result["created"]["datums"]))
            self.assertEqual(1, len(result["created"]["datum_systems"]))
            self.assertFalse(result["skipped"])
            self.assertEqual(
                ["A", "B"],
                [
                    datum.DatumLabel
                    for datum in result["created"]["datums"]
                ]
            )
            self.assertEqual(
                "Face1",
                result["created"]["datums"][0].ReferencedSubelement
            )
            self.assertEqual(
                "#32",
                result["created"]["datums"][0].AP242SourceId
            )
            self.assertEqual(
                "DATUM_SYSTEM",
                result["created"]["datum_systems"][0].AP242SourceType
            )
        finally:
            FreeCAD.closeDocument(doc.Name)

    def test_native_creation_imports_target_backed_datum(self):
        try:
            import FreeCAD
            import Part
        except Exception:
            self.skipTest("FreeCAD is not available in this Python")

        path = self.write_step("""ISO-10303-21;
DATA;
#10 = DATUM('','',#90,.F.,'C');
#11 = PLACED_DATUM_TARGET_FEATURE('','rectangle',#90,.T.,'1');
#12 = SHAPE_ASPECT_RELATIONSHIP('','datum target',#11,#10);
#20 = PROPERTY_DEFINITION('','',#11);
#21 = SHAPE_DEFINITION_REPRESENTATION(#20,#22);
#22 = SHAPE_REPRESENTATION_WITH_PARAMETERS('',(#30,#31,#40),#90);
#30 = (LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.25),#91)
REPRESENTATION_ITEM('target width'));
#31 = (LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(2.0),#91)
REPRESENTATION_ITEM('target length'));
#40 = AXIS2_PLACEMENT_3D('orientation',#41,#42,#43);
#41 = CARTESIAN_POINT('',(10.,5.,5.));
#42 = DIRECTION('',(1.,0.,0.));
#43 = DIRECTION('',(0.,1.,0.));
#50 = DATUM_REFERENCE_COMPARTMENT('','',#90,.F.,#10,$);
#51 = DATUM_SYSTEM('','',#90,.F.,(#50));
ENDSEC;
END-ISO-10303-21;
""")
        doc = FreeCAD.newDocument("MBDImporterTargetUnit")
        shape_obj = doc.addObject("Part::Feature", "ImportedShape")
        shape_obj.Shape = Part.makeBox(10, 20, 30)

        try:
            preview = MBDImporter.semantic_import_preview(path)
            result = MBDImporter.create_native_datums_and_systems_from_preview(
                doc,
                shape_obj,
                preview
            )

            self.assertEqual(1, len(result["created"]["datums"]))
            self.assertEqual(1, len(result["created"]["datum_targets"]))
            self.assertEqual(1, len(result["created"]["datum_systems"]))
            self.assertFalse(result["skipped"])
            target = result["created"]["datum_targets"][0]
            self.assertEqual("C1", target.TargetId)
            self.assertEqual("Rectangle", str(target.TargetType))
            self.assertAlmostEqual(2.0, float(target.TargetLength))
            self.assertAlmostEqual(1.25, float(target.TargetWidth))
            self.assertEqual("#11", target.AP242SourceId)
            self.assertEqual("DATUM_TARGET", target.AP242SourceType)
        finally:
            FreeCAD.closeDocument(doc.Name)

    def test_native_creation_imports_point_line_and_circle_targets(self):
        try:
            import FreeCAD
            import Part
        except Exception:
            self.skipTest("FreeCAD is not available in this Python")

        path = self.write_step("""ISO-10303-21;
DATA;
#10 = DATUM('','',#90,.F.,'A');
#11 = PLACED_DATUM_TARGET_FEATURE('','point',#90,.T.,'1');
#12 = SHAPE_ASPECT_RELATIONSHIP('','datum target',#11,#10);
#20 = PROPERTY_DEFINITION('','',#11);
#21 = SHAPE_DEFINITION_REPRESENTATION(#20,#22);
#22 = SHAPE_REPRESENTATION_WITH_PARAMETERS('',(#40),#90);
#30 = DATUM('','',#90,.F.,'B');
#31 = PLACED_DATUM_TARGET_FEATURE('','line',#90,.T.,'1');
#32 = SHAPE_ASPECT_RELATIONSHIP('','datum target',#31,#30);
#33 = PROPERTY_DEFINITION('','',#31);
#34 = SHAPE_DEFINITION_REPRESENTATION(#33,#35);
#35 = SHAPE_REPRESENTATION_WITH_PARAMETERS('',(#36,#41),#90);
#36 = (LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(4.0),#91)
REPRESENTATION_ITEM('target length'));
#50 = DATUM('','',#90,.F.,'C');
#51 = PLACED_DATUM_TARGET_FEATURE('','circle',#90,.T.,'1');
#52 = SHAPE_ASPECT_RELATIONSHIP('','datum target',#51,#50);
#53 = PROPERTY_DEFINITION('','',#51);
#54 = SHAPE_DEFINITION_REPRESENTATION(#53,#55);
#55 = SHAPE_REPRESENTATION_WITH_PARAMETERS('',(#56,#42),#90);
#56 = (LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(2.5),#91)
REPRESENTATION_ITEM('target diameter'));
#40 = AXIS2_PLACEMENT_3D('orientation',#60,#63,#64);
#41 = AXIS2_PLACEMENT_3D('orientation',#61,#63,#64);
#42 = AXIS2_PLACEMENT_3D('orientation',#62,#63,#64);
#60 = CARTESIAN_POINT('',(1.,1.,0.));
#61 = CARTESIAN_POINT('',(4.,1.,0.));
#62 = CARTESIAN_POINT('',(7.,1.,0.));
#63 = DIRECTION('',(0.,0.,1.));
#64 = DIRECTION('',(1.,0.,0.));
ENDSEC;
END-ISO-10303-21;
""")
        doc = FreeCAD.newDocument("MBDImporterTargetKindsUnit")
        shape_obj = doc.addObject("Part::Feature", "ImportedShape")
        shape_obj.Shape = Part.makeBox(10, 10, 2)

        try:
            preview = MBDImporter.semantic_import_preview(path)
            result = MBDImporter.create_native_datums_and_systems_from_preview(
                doc,
                shape_obj,
                preview
            )

            targets = {
                str(target.TargetType): target
                for target in result["created"]["datum_targets"]
            }
            self.assertEqual(3, len(targets))
            self.assertIn("Point", targets)
            self.assertIn("Line", targets)
            self.assertIn("Circle", targets)
            self.assertAlmostEqual(4.0, float(targets["Line"].TargetLength))
            self.assertAlmostEqual(2.5, float(targets["Circle"].TargetDiameter))
            self.assertEqual("#51", targets["Circle"].AP242SourceId)
        finally:
            FreeCAD.closeDocument(doc.Name)

    def test_native_creation_imports_measurable_dimension(self):
        try:
            import FreeCAD
            import Part
        except Exception:
            self.skipTest("FreeCAD is not available in this Python")

        path = self.write_step("""ISO-10303-21;
DATA;
#10 = ADVANCED_FACE('',(),#20,.T.);
#11 = ADVANCED_FACE('',(),#21,.T.);
#30 = SHAPE_ASPECT('','',#90,.T.);
#31 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#30,#100,#10);
#32 = SHAPE_ASPECT('','',#90,.T.);
#33 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#32,#100,#11);
#40 = DIMENSIONAL_LOCATION(#30,#32,'distance');
ENDSEC;
END-ISO-10303-21;
""")
        doc = FreeCAD.newDocument("MBDImporterDimensionUnit")
        shape_obj = doc.addObject("Part::Feature", "ImportedShape")
        shape_obj.Shape = Part.makeBox(10, 20, 30)

        try:
            preview = MBDImporter.semantic_import_preview(path)
            result = MBDImporter.create_native_datums_and_systems_from_preview(
                doc,
                shape_obj,
                preview
            )

            self.assertEqual(1, len(result["created"]["dimensions"]))
            self.assertFalse(result["skipped"])
            dimension = result["created"]["dimensions"][0]
            self.assertEqual("Reference", str(dimension.DimensionPurpose))
            self.assertEqual("Linear", str(dimension.DimensionKind))
            self.assertEqual("DIMENSIONAL_LOCATION", dimension.AP242Entity)
            self.assertEqual("#40", dimension.AP242SourceId)
            self.assertEqual("DIMENSIONAL_LOCATION", dimension.AP242SourceType)
            self.assertTrue(dimension.GeometrySignatureValid)
        finally:
            FreeCAD.closeDocument(doc.Name)

    def test_native_creation_imports_simple_fcf(self):
        try:
            import FreeCAD
            import Part
        except Exception:
            self.skipTest("FreeCAD is not available in this Python")

        path = self.write_step("""ISO-10303-21;
DATA;
#10 = ADVANCED_FACE('',(),#20,.T.);
#30 = SHAPE_ASPECT('','',#90,.T.);
#31 = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#30,#100,#10);
#40 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.25),#91);
#50 = (GEOMETRIC_TOLERANCE('','',#40,#30) FLATNESS_TOLERANCE());
ENDSEC;
END-ISO-10303-21;
""")
        doc = FreeCAD.newDocument("MBDImporterFCFUnit")
        shape_obj = doc.addObject("Part::Feature", "ImportedShape")
        shape_obj.Shape = Part.makeBox(10, 20, 30)

        try:
            preview = MBDImporter.semantic_import_preview(path)
            result = MBDImporter.create_native_datums_and_systems_from_preview(
                doc,
                shape_obj,
                preview
            )

            self.assertEqual(1, len(result["created"]["fcfs"]))
            self.assertFalse(result["skipped"])
            fcf = result["created"]["fcfs"][0]
            self.assertEqual("Flatness", str(fcf.ToleranceType))
            self.assertAlmostEqual(0.25, float(fcf.ToleranceValue))
            self.assertEqual("Face1", fcf.ControlledSubelement)
            self.assertEqual("#50", fcf.AP242SourceId)
            self.assertEqual("Flatness", fcf.AP242SourceType)
            self.assertTrue(fcf.GeometrySignatureValid)
        finally:
            FreeCAD.closeDocument(doc.Name)


if __name__ == "__main__":
    unittest.main()
