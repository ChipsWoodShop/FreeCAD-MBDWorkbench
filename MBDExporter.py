# MBDExporter.py

import FreeCAD
import Part

from OCC.Core.TDocStd import TDocStd_Document
from OCC.Core.XCAFDoc import XCAFDoc_DocumentTool
from OCC.Core.STEPCAFControl import STEPCAFControl_Writer
from OCC.Core.Interface import Interface_Static
from OCC.Core.IFSelect import IFSelect_RetDone

def should_export_shape_object(obj):
    if not hasattr(obj, "Shape"):
        return False

    if hasattr(obj, "IsSemanticPMI") and obj.IsSemanticPMI:
        return False

    shape = obj.Shape

    if shape.isNull():
        return False

    if len(shape.Solids) == 0:
        return False

    # Prefer exporting PartDesign Body, not its internal features
    if obj.TypeId.startswith("PartDesign::") and obj.TypeId != "PartDesign::Body":
        return False

    return True

def export_ap242(filepath):

    doc = FreeCAD.ActiveDocument

    if doc is None:
        raise Exception("No active document.")

    # Configure AP242 schema
    Interface_Static.SetCVal(
        "write.step.schema",
        "AP242DIS"
    )

    # Create XCAF document
    xcaf_doc = TDocStd_Document("pythonocc-xcaf")

    shape_tool = XCAFDoc_DocumentTool.ShapeTool(
        xcaf_doc.Main()
    )

    exported_count = 0

    for obj in doc.Objects:

        if not should_export_shape_object(obj):
            continue

        shape = obj.Shape
        occ_shape = Part.__toPythonOCC__(shape)

        shape_tool.AddShape(occ_shape)
        exported_count += 1

    writer = STEPCAFControl_Writer()

    ok = writer.Transfer(xcaf_doc)

    if not ok:
        raise Exception("STEP transfer failed.")

    status = writer.Write(filepath)

    if status != IFSelect_RetDone:
        raise Exception("STEP write failed.")

    FreeCAD.Console.PrintMessage(
        "Exported {} shapes to {}\n".format(
            exported_count,
            filepath
        )
    )

    return True