# MBDExporter.py

import FreeCAD
import Part
import json
from PySide import QtGui

from OCC.Core.TDocStd import TDocStd_Document
from OCC.Core.XCAFDoc import XCAFDoc_DocumentTool
from OCC.Core.STEPCAFControl import STEPCAFControl_Writer
from OCC.Core.Interface import Interface_Static
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.TopAbs import (
    TopAbs_COMPOUND,
    TopAbs_COMPSOLID,
    TopAbs_SOLID,
    TopAbs_SHELL,
    TopAbs_FACE,
)
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import topods
from OCC.Core.TDF import TDF_Label
from OCC.Core.XCAFDoc import XCAFDoc_DocumentTool
from OCC.Core.TCollection import TCollection_HAsciiString
from OCC.Core.TDF import TDF_LabelSequence
from OCC.Core.TDF import TDF_LabelSequence, TDF_Tool
from OCC.Core.XCAFDoc import XCAFDoc_Datum
from OCC.Core.StepData import StepData_ConfParameters
from OCC.Core.XCAFDoc import XCAFDoc_Datum
from OCC.Core.XCAFDimTolObjects import XCAFDimTolObjects_DatumObject

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


def shape_type_name(shape):
    names = {
        TopAbs_COMPOUND: "COMPOUND",
        TopAbs_COMPSOLID: "COMPSOLID",
        TopAbs_SOLID: "SOLID",
        TopAbs_SHELL: "SHELL",
        TopAbs_FACE: "FACE",
    }
    return names.get(shape.ShapeType(), str(shape.ShapeType()))


def get_simple_shape_label(shape_tool, root_label):
    """
    AddShape() may return a reference label if the shape has location.
    AddSubShape() requires a top-level simple-shape label.
    """

    if shape_tool.IsSimpleShape(root_label):
        return root_label

    if shape_tool.IsReference(root_label):
        simple_label = TDF_Label()

        ok = shape_tool.GetReferredShape(
            root_label,
            simple_label
        )

        if ok and not simple_label.IsNull():
            return simple_label

    return root_label


def build_face_label_map(shape_tool, simple_label):
    """
    Build a map:
        Face1 -> XCAF TDF_Label
        Face2 -> XCAF TDF_Label
        ...

    using the shape stored on the simple-shape label.
    """

    subshape_map = {}

    stored_shape = shape_tool.GetShape(simple_label)

    exp = TopExp_Explorer(stored_shape, TopAbs_FACE)

    face_index = 1

    while exp.More():

        face = topods.Face(exp.Current())

        added_label = TDF_Label()

        added = shape_tool.AddSubShape(
            simple_label,
            face,
            added_label
        )

        subname = "Face{}".format(face_index)

        subshape_map[subname] = added_label

        FreeCAD.Console.PrintMessage(
            "Mapped {} -> added: {}, null: {}\n".format(
                subname,
                added,
                added_label.IsNull()
            )
        )

        face_index += 1
        exp.Next()

    return subshape_map

def validate_pmi_geometry_signatures(doc):
    issues = []

    for obj in doc.Objects:
        if not hasattr(obj, "IsSemanticPMI") or not obj.IsSemanticPMI:
            continue

        if not hasattr(obj, "ReferencedObject"):
            continue

        if not hasattr(obj, "ReferencedSubelement"):
            continue

        if not hasattr(obj, "GeometrySignature"):
            continue

        if not obj.GeometrySignature:
            continue

        try:
            old_sig = json.loads(obj.GeometrySignature)
        except Exception as e:
            issues.append(
                "{}: stored geometry signature could not be parsed: {}".format(
                    obj.Label,
                    e
                )
            )
            obj.GeometrySignatureValid = False
            continue

        ref_obj = obj.ReferencedObject
        sub = obj.ReferencedSubelement

        try:
            target = ref_obj.Shape.getElement(sub)
        except Exception as e:
            issues.append(
                "{}: referenced subelement {} could not be resolved: {}".format(
                    obj.Label,
                    sub,
                    e
                )
            )
            obj.GeometrySignatureValid = False
            continue

        warnings = []

        try:
            new_com = [
                round(target.CenterOfMass.x, 6),
                round(target.CenterOfMass.y, 6),
                round(target.CenterOfMass.z, 6),
            ]

            old_com = old_sig.get("CenterOfMass")
            if old_com:
                dx = new_com[0] - old_com[0]
                dy = new_com[1] - old_com[1]
                dz = new_com[2] - old_com[2]
                dist = (dx * dx + dy * dy + dz * dz) ** 0.5

                if dist > 0.5:
                    warnings.append(
                        "center of mass moved {:.3f} mm".format(dist)
                    )
        except Exception:
            pass

        try:
            old_area = old_sig.get("Area")
            new_area = target.Area

            if old_area:
                pct = abs(new_area - old_area) / old_area * 100.0

                if pct > 5.0:
                    warnings.append(
                        "area changed by {:.1f}%".format(pct)
                    )
        except Exception:
            pass

        try:
            old_type = old_sig.get("GeometryType")
            new_type = "Unknown"

            try:
                new_type = target.Surface.__class__.__name__
            except Exception:
                try:
                    new_type = target.Curve.__class__.__name__
                except Exception:
                    pass

            if old_type and old_type != new_type:
                warnings.append(
                    "geometry type changed from {} to {}".format(
                        old_type,
                        new_type
                    )
                )
        except Exception:
            pass

        if warnings:
            obj.GeometrySignatureValid = False
            for warning in warnings:
                issues.append(
                    "{} on {}: {}".format(
                        obj.Label,
                        sub,
                        warning
                    )
                )
        else:
            obj.GeometrySignatureValid = True

    return issues

def export_ap242(filepath):

    doc = FreeCAD.ActiveDocument
    validation_issues = validate_pmi_geometry_signatures(doc)
    msg = QtGui.QMessageBox()
    msg.setIcon(QtGui.QMessageBox.Warning)

    msg.setWindowTitle("MBD Attachment Validation")

    msg.setText(
        "Potential stale PMI attachments were detected."
    )

    msg.setInformativeText(
        "\n".join(validation_issues[:10]) +
        "\n\nContinue AP242 export anyway?"
    )

    msg.setStandardButtons(
        QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel
    )

    result = msg.exec_()

    if result != QtGui.QMessageBox.Yes:
        FreeCAD.Console.PrintWarning(
            "AP242 export cancelled by user.\n"
        )
        return
    if validation_issues:
        FreeCAD.Console.PrintWarning(
            "\nMBD geometry attachment validation warnings:\n"
        )

        for issue in validation_issues:
            FreeCAD.Console.PrintWarning(
                "  - {}\n".format(issue)
            )

        FreeCAD.Console.PrintWarning(
            "PMI export will continue, but affected datum/FCF attachments should be reviewed.\n\n"
        )
    if doc is None:
        raise Exception("No active document.")

    Interface_Static.SetCVal(
        "write.step.schema",
        "AP242DIS"
    )

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

        root_label = shape_tool.AddShape(
            occ_shape,
            False,
            False
        )

        simple_label = get_simple_shape_label(
            shape_tool,
            root_label
        )

        FreeCAD.Console.PrintMessage(
            "Export object: {}\n".format(obj.Name)
        )
        FreeCAD.Console.PrintMessage(
            "Root label null: {}\n".format(root_label.IsNull())
        )
        FreeCAD.Console.PrintMessage(
            "Root is reference: {}\n".format(shape_tool.IsReference(root_label))
        )
        FreeCAD.Console.PrintMessage(
            "Simple label null: {}\n".format(simple_label.IsNull())
        )
        FreeCAD.Console.PrintMessage(
            "Simple is simple shape: {}\n".format(
                shape_tool.IsSimpleShape(simple_label)
            )
        )
        FreeCAD.Console.PrintMessage(
            "OCCT shape type: {}\n".format(shape_type_name(occ_shape))
        )

        face_label_map = build_face_label_map(
            shape_tool,
            simple_label
        )
        dimtol_tool = XCAFDoc_DocumentTool.DimTolTool(
            xcaf_doc.Main()
        )
        for subname in ["Face1", "Face4", "Face5"]:
                lab = face_label_map[subname]
                sh = shape_tool.GetShape(lab)
                FreeCAD.Console.PrintMessage(
                    "{} label null: {}, shape null: {}, shape type: {}\n".format(
                        subname,
                        lab.IsNull(),
                        sh.IsNull(),
                        shape_type_name(sh)
                    )
                )
    
        for pmi_obj in doc.Objects:

            if not hasattr(pmi_obj, "IsSemanticPMI"):
                continue

            if not pmi_obj.IsSemanticPMI:
                continue

            if pmi_obj.TypeId != "App::FeaturePython":
                continue

            if not hasattr(pmi_obj, "DatumLabel"):
                continue

            subname = pmi_obj.ReferencedSubelement

            if subname not in face_label_map:

                FreeCAD.Console.PrintWarning(
                    "No face label found for {}\n".format(subname)
                )

                continue

            face_label = face_label_map[subname]

            datum_name = str(pmi_obj.DatumLabel)

            FreeCAD.Console.PrintMessage(
                "Creating semantic datum {} on {}\n".format(
                    datum_name,
                    subname
                )
            )

            datum_label = dimtol_tool.AddDatum()

            datum_attr = XCAFDoc_Datum.Set(datum_label)

            datum_obj = XCAFDimTolObjects_DatumObject()

            datum_obj.SetName(
                TCollection_HAsciiString(datum_name)
            )

            datum_obj.SetSemanticName(
                TCollection_HAsciiString("Datum {}".format(datum_name))
            )

            datum_obj.SetPosition(1)

            datum_attr.SetObject(datum_obj)

            
            shape_labels = TDF_LabelSequence()

            shape_labels.Append(face_label)
            FreeCAD.Console.PrintMessage(
                "Attaching datum {} to {} label null: {}\n".format(
                    datum_name,
                    subname,
                    face_label.IsNull()
                )
            )
            dimtol_tool.SetDatum(
                shape_labels,
                datum_label
            )
        FreeCAD.Console.PrintMessage(
            "Mapped {} face labels for {}\n".format(
                len(face_label_map),
                obj.Name
            )
        )

        exported_count += 1
    Interface_Static.SetCVal("write.step.schema", "AP242DIS")
    Interface_Static.SetIVal("write.step.schema", 5)

    FreeCAD.Console.PrintMessage(
        "write.step.schema CVal before writer: {}\n".format(
            Interface_Static.CVal("write.step.schema")
        )
    )

    FreeCAD.Console.PrintMessage(
        "write.step.schema IVal before writer: {}\n".format(
            Interface_Static.IVal("write.step.schema")
        )
    )

    writer = STEPCAFControl_Writer()

    FreeCAD.Console.PrintMessage(
        "write.step.schema CVal after writer: {}\n".format(
            Interface_Static.CVal("write.step.schema")
        )
    )

    FreeCAD.Console.PrintMessage(
        "write.step.schema IVal after writer: {}\n".format(
            Interface_Static.IVal("write.step.schema")
        )
    )

    writer.SetDimTolMode(True)
    writer.SetNameMode(True)
    writer.SetPropsMode(True)

    params = StepData_ConfParameters()

    params.WriteSchema = (
        StepData_ConfParameters.WriteMode_StepSchema_AP242DIS
    )

    FreeCAD.Console.PrintMessage(
        "params.WriteSchema: {}\n".format(params.WriteSchema)
    )

    ok = writer.Transfer(
        xcaf_doc,
        params
    )

    FreeCAD.Console.PrintMessage(
        "Transfer with explicit params returned: {}\n".format(ok)
    )
    FreeCAD.Console.PrintMessage(
        "params.WriteSchema numeric: {}\n".format(
            int(params.WriteSchema)
        )
    )
    FreeCAD.Console.PrintMessage(
        "AP242 enum numeric: {}\n".format(
            int(
                StepData_ConfParameters.WriteMode_StepSchema_AP242DIS
            )
        )
    )
    datum_labels = TDF_LabelSequence()
    dimtol_tool.GetDatumLabels(datum_labels)

    FreeCAD.Console.PrintMessage(
        "XCAF datum labels found: {}\n".format(datum_labels.Length())
    )

    for i in range(datum_labels.Length()):
        lab = datum_labels.Value(i + 1)
        FreeCAD.Console.PrintMessage(
            "XCAF datum {} label null: {}\n".format(
                i + 1,
                lab.IsNull()
            )
        )
    for subname, face_label in face_label_map.items():
        datum_seq = TDF_LabelSequence()
        found = dimtol_tool.GetRefDatumLabel(face_label, datum_seq)

        FreeCAD.Console.PrintMessage(
            "{} datum refs found: {}, count: {}\n".format(
                subname,
                found,
                datum_seq.Length()
            )
        )
    
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