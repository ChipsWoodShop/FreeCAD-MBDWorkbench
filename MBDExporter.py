# MBDExporter.py

import json

import FreeCAD
import Part
from PySide import QtGui

from OCC.Core.TCollection import TCollection_HAsciiString
from OCC.Core.TDataStd import TDataStd_Integer, TDataStd_Real
from OCC.Core.TDF import TDF_Label, TDF_LabelSequence
from OCC.Core.TDocStd import TDocStd_Document
from OCC.Core.TopoDS import topods
from OCC.Core.TopAbs import (
    TopAbs_COMPOUND,
    TopAbs_COMPSOLID,
    TopAbs_FACE,
    TopAbs_SHELL,
    TopAbs_SOLID,
)
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.Interface import Interface_Static
from OCC.Core.STEPCAFControl import STEPCAFControl_Writer
from OCC.Core.StepData import StepData_ConfParameters
from OCC.Core.XCAFDimTolObjects import XCAFDimTolObjects_DatumObject
import OCC.Core.XCAFDimTolObjects as XDTO
from OCC.Core.XCAFDoc import XCAFDoc_Datum, XCAFDoc_DocumentTool


GEOMTOL_CHILD_TYPE = 1
GEOMTOL_CHILD_TYPE_OF_VALUE = 2
GEOMTOL_CHILD_VALUE = 3
GEOMTOL_CHILD_MATERIAL_REQUIREMENT = 4
GEOMTOL_CHILD_ZONE_MODIFIER = 5


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

    # Prefer exporting PartDesign Body, not its internal features.
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


def configure_step_ap242():
    Interface_Static.SetCVal(
        "write.step.schema",
        "AP242DIS"
    )
    Interface_Static.SetIVal("write.step.schema", 5)


def create_xcaf_document():
    xcaf_doc = TDocStd_Document("pythonocc-xcaf")
    shape_tool = XCAFDoc_DocumentTool.ShapeTool(
        xcaf_doc.Main()
    )
    dimtol_tool = XCAFDoc_DocumentTool.DimTolTool(
        xcaf_doc.Main()
    )

    return xcaf_doc, shape_tool, dimtol_tool


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


def export_body_shape(shape_tool, obj):
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
        "OCCT shape type: {}\n".format(shape_type_name(occ_shape))
    )

    return root_label, simple_label


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

        shape_tool.AddSubShape(
            simple_label,
            face,
            added_label
        )

        subname = "Face{}".format(face_index)
        subshape_map[subname] = added_label

        face_index += 1
        exp.Next()

    return subshape_map


def iter_semantic_datums(doc):
    for obj in doc.Objects:
        if not hasattr(obj, "IsSemanticPMI"):
            continue

        if not obj.IsSemanticPMI:
            continue

        if obj.TypeId != "App::FeaturePython":
            continue

        if hasattr(obj, "DatumLabel"):
            yield obj


def iter_feature_control_frames(doc):
    for obj in doc.Objects:
        if not hasattr(obj, "ToleranceType"):
            continue

        if not hasattr(obj, "ControlledObject"):
            continue

        if not hasattr(obj, "ControlledSubelement"):
            continue

        yield obj


def export_datums(doc, dimtol_tool, face_label_map):
    datum_label_map = {}

    for pmi_obj in iter_semantic_datums(doc):
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
        datum_label_map[datum_name] = datum_label

        shape_labels = TDF_LabelSequence()
        shape_labels.Append(face_label)

        dimtol_tool.SetDatum(
            shape_labels,
            datum_label
        )

    return datum_label_map


def configure_position_tolerance(geomtol_label, pmi_obj):
    # pythonocc does not expose XCAFDoc_GeomTolerance.SetObject()
    # reliably here, so populate the child labels used by OCCT.
    TDataStd_Integer.Set(
        geomtol_label.FindChild(GEOMTOL_CHILD_TYPE),
        int(XDTO.XCAFDimTolObjects_GeomToleranceType_Position)
    )

    if pmi_obj.DiameterZone:
        TDataStd_Integer.Set(
            geomtol_label.FindChild(GEOMTOL_CHILD_TYPE_OF_VALUE),
            int(XDTO.XCAFDimTolObjects_GeomToleranceTypeValue_Diameter)
        )

    TDataStd_Real.Set(
        geomtol_label.FindChild(GEOMTOL_CHILD_VALUE),
        float(pmi_obj.ToleranceValue)
    )

    TDataStd_Integer.Set(
        geomtol_label.FindChild(GEOMTOL_CHILD_MATERIAL_REQUIREMENT),
        int(XDTO.XCAFDimTolObjects_GeomToleranceMatReqModif_None)
    )

    TDataStd_Integer.Set(
        geomtol_label.FindChild(GEOMTOL_CHILD_ZONE_MODIFIER),
        int(XDTO.XCAFDimTolObjects_GeomToleranceZoneModif_None)
    )


def export_feature_control_frames(doc, dimtol_tool, face_label_map, datum_label_map):
    for pmi_obj in iter_feature_control_frames(doc):
        subname = pmi_obj.ControlledSubelement

        if subname not in face_label_map:
            FreeCAD.Console.PrintWarning(
                "FCF controlled subshape {} not found in subshape map.\n".format(
                    subname
                )
            )
            continue

        controlled_label = face_label_map[subname]

        FreeCAD.Console.PrintMessage(
            "Creating semantic geom tolerance on {}\n".format(
                subname
            )
        )

        geomtol_label = dimtol_tool.AddGeomTolerance()
        configure_position_tolerance(geomtol_label, pmi_obj)

        dimtol_tool.SetGeomTolerance(
            controlled_label,
            geomtol_label
        )

        link_datum_system_to_geom_tolerance(
            dimtol_tool,
            pmi_obj,
            datum_label_map,
            geomtol_label
        )


def link_datum_system_to_geom_tolerance(
    dimtol_tool,
    pmi_obj,
    datum_label_map,
    geomtol_label
):
    if not hasattr(pmi_obj, "DatumSystem") or not pmi_obj.DatumSystem:
        return

    ds = pmi_obj.DatumSystem

    for datum_ref_name in [
        "PrimaryDatum",
        "SecondaryDatum",
        "TertiaryDatum"
    ]:
        if not hasattr(ds, datum_ref_name):
            continue

        datum_obj = getattr(ds, datum_ref_name)

        if not datum_obj:
            continue

        datum_label_text = datum_obj.DatumLabel

        if datum_label_text not in datum_label_map:
            FreeCAD.Console.PrintWarning(
                "Datum {} not found in datum_label_map.\n".format(
                    datum_label_text
                )
            )
            continue

        dimtol_tool.SetDatumToGeomTol(
            datum_label_map[datum_label_text],
            geomtol_label
        )


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


def confirm_export_despite_warnings(validation_issues):
    if not validation_issues:
        return True

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

    return msg.exec_() == QtGui.QMessageBox.Yes


def print_validation_warnings(validation_issues):
    if not validation_issues:
        return

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


def transfer_and_write_step(xcaf_doc, dimtol_tool, filepath):
    writer = STEPCAFControl_Writer()
    writer.SetDimTolMode(True)
    writer.SetNameMode(True)
    writer.SetPropsMode(True)

    params = StepData_ConfParameters()
    params.WriteSchema = (
        StepData_ConfParameters.WriteMode_StepSchema_AP242DIS
    )

    ok = writer.Transfer(
        xcaf_doc,
        params
    )

    datum_labels = TDF_LabelSequence()
    dimtol_tool.GetDatumLabels(datum_labels)

    FreeCAD.Console.PrintMessage(
        "XCAF datum labels found: {}\n".format(datum_labels.Length())
    )

    if not ok:
        raise Exception("STEP transfer failed.")

    status = writer.Write(filepath)

    if status != IFSelect_RetDone:
        raise Exception("STEP write failed.")


def export_ap242(filepath):
    doc = FreeCAD.ActiveDocument

    if doc is None:
        raise Exception("No active document.")

    validation_issues = validate_pmi_geometry_signatures(doc)

    if not confirm_export_despite_warnings(validation_issues):
        FreeCAD.Console.PrintWarning(
            "AP242 export cancelled by user.\n"
        )
        return

    print_validation_warnings(validation_issues)
    configure_step_ap242()

    xcaf_doc, shape_tool, dimtol_tool = create_xcaf_document()
    exported_count = 0

    for obj in doc.Objects:
        if not should_export_shape_object(obj):
            continue

        _root_label, simple_label = export_body_shape(
            shape_tool,
            obj
        )

        face_label_map = build_face_label_map(
            shape_tool,
            simple_label
        )

        datum_label_map = export_datums(
            doc,
            dimtol_tool,
            face_label_map
        )

        FreeCAD.Console.PrintMessage(
            "Mapped {} face labels for {}\n".format(
                len(face_label_map),
                obj.Name
            )
        )

        export_feature_control_frames(
            doc,
            dimtol_tool,
            face_label_map,
            datum_label_map
        )

        exported_count += 1

    transfer_and_write_step(
        xcaf_doc,
        dimtol_tool,
        filepath
    )

    FreeCAD.Console.PrintMessage(
        "Exported {} shapes to {}\n".format(
            exported_count,
            filepath
        )
    )

    return True
