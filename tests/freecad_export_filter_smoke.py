"""Headless smoke test for AP242 export object filtering.

Run with FreeCADCmd.  The test creates a document containing both a simple
solid and a compound wrapper.  The exporter should prefer the simple solid and
skip the compound wrapper to avoid duplicate geometry/PMI on re-exported STEP
imports.
"""

import os
import sys
import traceback


WORKBENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if WORKBENCH_DIR not in sys.path:
    sys.path.insert(0, WORKBENCH_DIR)

import FreeCAD
import Part

from freecad.mbd_workbench import MBDExporter


def main():
    doc = FreeCAD.newDocument("MBDExportFilterSmoke")
    box = Part.makeBox(10, 10, 10)

    solid_obj = doc.addObject("Part::Feature", "SimpleSolid")
    solid_obj.Shape = box

    compound_obj = doc.addObject("Part::Feature", "CompoundWrapper")
    compound_obj.Shape = Part.makeCompound([box])

    doc.recompute()

    export_names = [
        obj.Name
        for obj in MBDExporter.exportable_shape_objects(doc)
    ]

    print("Exportable shape objects: {}".format(", ".join(export_names)))

    if export_names != ["SimpleSolid"]:
        raise RuntimeError(
            "Expected only SimpleSolid to export, got {}".format(export_names)
        )

    FreeCAD.closeDocument(doc.Name)
    print("AP242 export object filter smoke passed.")


try:
    main()
except Exception:
    traceback.print_exc()
    raise
