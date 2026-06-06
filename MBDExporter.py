# MBDExporter.py

import json
import re

import FreeCAD
import Part
from PySide import QtGui

import MBDDatumTarget
from MBDDatumSystem import datum_system_compartments

from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCC.Core.TCollection import TCollection_HAsciiString
from OCC.Core.TDataStd import (
    TDataStd_Integer,
    TDataStd_IntegerArray,
    TDataStd_Real,
    TDataStd_RealArray,
)
from OCC.Core.TDF import TDF_Label, TDF_LabelSequence
from OCC.Core.TDocStd import TDocStd_Document
from OCC.Core.TopoDS import topods
from OCC.Core.TopAbs import (
    TopAbs_COMPOUND,
    TopAbs_COMPSOLID,
    TopAbs_EDGE,
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
from OCC.Core.XCAFDoc import XCAFDoc_Datum, XCAFDoc_Dimension, XCAFDoc_DocumentTool


GEOMTOL_CHILD_TYPE = 1
GEOMTOL_CHILD_TYPE_OF_VALUE = 2
GEOMTOL_CHILD_VALUE = 3
GEOMTOL_CHILD_MATERIAL_REQUIREMENT = 4
GEOMTOL_CHILD_ZONE_MODIFIER = 5
GEOMTOL_CHILD_MODIFIERS = 7

DIMENSION_CHILD_TYPE = 1
DIMENSION_CHILD_VALUE = 2
DIMENSION_CHILD_DIR = 8

GEOMTOL_TYPE_BY_FCF_TYPE = {
    "Angularity": "XCAFDimTolObjects_GeomToleranceType_Angularity",
    "CircularRunout": "XCAFDimTolObjects_GeomToleranceType_CircularRunout",
    "Circularity": "XCAFDimTolObjects_GeomToleranceType_CircularityOrRoundness",
    "Cylindricity": "XCAFDimTolObjects_GeomToleranceType_Cylindricity",
    "Flatness": "XCAFDimTolObjects_GeomToleranceType_Flatness",
    "LineProfile": "XCAFDimTolObjects_GeomToleranceType_ProfileOfLine",
    "Parallelism": "XCAFDimTolObjects_GeomToleranceType_Parallelism",
    "Perpendicularity": "XCAFDimTolObjects_GeomToleranceType_Perpendicularity",
    "Position": "XCAFDimTolObjects_GeomToleranceType_Position",
    "Profile": "XCAFDimTolObjects_GeomToleranceType_ProfileOfSurface",
    "Straightness": "XCAFDimTolObjects_GeomToleranceType_Straightness",
    "TotalRunout": "XCAFDimTolObjects_GeomToleranceType_TotalRunout",
}

DIMENSION_TYPE_BY_KIND = {
    "Diameter": "XCAFDimTolObjects_DimensionType_Size_Diameter",
    "Radius": "XCAFDimTolObjects_DimensionType_Size_Radius",
}

DIMENSION_TYPE_BY_PATTERN = {
    "PlaneToPlane": "XCAFDimTolObjects_DimensionType_Size_Thickness",
}


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


def build_edge_label_map(shape_tool, simple_label):
    """
    Build a map:
        Edge1 -> XCAF TDF_Label
        Edge2 -> XCAF TDF_Label
        ...

    using the shape stored on the simple-shape label.
    """

    subshape_map = {}
    stored_shape = shape_tool.GetShape(simple_label)
    exp = TopExp_Explorer(stored_shape, TopAbs_EDGE)
    edge_index = 1

    while exp.More():
        edge = topods.Edge(exp.Current())
        added_label = TDF_Label()

        shape_tool.AddSubShape(
            simple_label,
            edge,
            added_label
        )

        subname = "Edge{}".format(edge_index)
        subshape_map[subname] = added_label

        edge_index += 1
        exp.Next()

    return subshape_map


def dimension_reference_label(ref_obj, ref_sub, face_label_map):
    if ref_obj is None:
        return None

    if hasattr(ref_obj, "DatumLabel"):
        ref_sub = getattr(ref_obj, "ReferencedSubelement", "")

    if not ref_sub:
        return None

    return face_label_map.get(ref_sub)


def dimension_reference_subname(ref_obj, ref_sub):
    if ref_obj is None:
        return None

    if hasattr(ref_obj, "DatumLabel"):
        ref_sub = getattr(ref_obj, "ReferencedSubelement", "")

    if not ref_sub:
        return None

    return str(ref_sub)


def dimension_type_value(dim_obj):
    dimension_kind = str(getattr(dim_obj, "DimensionKind", ""))
    reference_pattern = str(getattr(dim_obj, "ReferencePattern", ""))

    if dimension_kind == "Linear" and reference_pattern in DIMENSION_TYPE_BY_PATTERN:
        return int(getattr(XDTO, DIMENSION_TYPE_BY_PATTERN[reference_pattern]))

    if dimension_kind == "Linear":
        return None

    enum_name = DIMENSION_TYPE_BY_KIND.get(dimension_kind)

    if not enum_name:
        return None

    return int(getattr(XDTO, enum_name))


def dimension_is_plane_to_plane_size(dim_obj):
    return (
        str(getattr(dim_obj, "DimensionKind", "")) == "Linear"
        and str(getattr(dim_obj, "ReferencePattern", "")) == "PlaneToPlane"
    )


def dimension_is_linear_location(dim_obj):
    return (
        str(getattr(dim_obj, "DimensionKind", "")) == "Linear"
        and not dimension_is_plane_to_plane_size(dim_obj)
    )


def dimension_values(dim_obj):
    purpose = str(getattr(dim_obj, "DimensionPurpose", ""))

    if purpose == "Limits":
        return [
            float(getattr(dim_obj, "LowerLimit", 0.0)),
            float(getattr(dim_obj, "UpperLimit", 0.0)),
        ]

    nominal = float(getattr(dim_obj, "NominalValue", 0.0))

    if purpose in ("UnequalBilateral", "EqualBilateral"):
        return [
            nominal,
            abs(float(getattr(dim_obj, "LowerTolerance", 0.0))),
            abs(float(getattr(dim_obj, "UpperTolerance", 0.0))),
        ]

    return [nominal]


def dimension_nominal_value(dim_obj):
    return float(getattr(dim_obj, "NominalValue", 0.0))


def dimension_tolerance_values(dim_obj):
    purpose = str(getattr(dim_obj, "DimensionPurpose", ""))

    if purpose not in ("UnequalBilateral", "EqualBilateral"):
        return None

    return (
        abs(float(getattr(dim_obj, "LowerTolerance", 0.0))),
        abs(float(getattr(dim_obj, "UpperTolerance", 0.0))),
    )


def set_dimension_real_array(dim_label, child_id, values):
    real_array = TDataStd_RealArray.Set(
        dim_label.FindChild(child_id),
        1,
        len(values)
    )

    for index, value in enumerate(values, start=1):
        real_array.SetValue(index, float(value))


def configure_dimension(dim_label, dim_obj):
    dimension_type = dimension_type_value(dim_obj)

    if dimension_type is None:
        raise ValueError(
            "Unsupported dimension kind {}".format(dim_obj.DimensionKind)
        )

    XCAFDoc_Dimension.Set(dim_label)

    TDataStd_Integer.Set(
        dim_label.FindChild(DIMENSION_CHILD_TYPE),
        dimension_type
    )

    set_dimension_real_array(
        dim_label,
        DIMENSION_CHILD_VALUE,
        dimension_values(dim_obj)
    )

    if str(getattr(dim_obj, "MeasurementType", "")) in ("X", "Y", "Z"):
        direction = {
            "X": [1.0, 0.0, 0.0],
            "Y": [0.0, 1.0, 0.0],
            "Z": [0.0, 0.0, 1.0],
        }[str(dim_obj.MeasurementType)]
        set_dimension_real_array(
            dim_label,
            DIMENSION_CHILD_DIR,
            direction
        )


def iter_semantic_datums(doc):
    for obj in doc.Objects:
        if not hasattr(obj, "IsSemanticPMI"):
            continue

        if not obj.IsSemanticPMI:
            continue

        if hasattr(obj, "DatumLabel"):
            yield obj


def iter_semantic_datum_targets(doc):
    for obj in doc.Objects:
        if not hasattr(obj, "IsSemanticPMI") or not obj.IsSemanticPMI:
            continue

        if not hasattr(obj, "TargetId"):
            continue

        if not hasattr(obj, "ParentDatum"):
            continue

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


def iter_semantic_dimensions(doc):
    for obj in doc.Objects:
        if not hasattr(obj, "DimensionKind"):
            continue

        if not hasattr(obj, "DimensionPurpose"):
            continue

        if not hasattr(obj, "ReferenceObject1"):
            continue

        yield obj


def fcf_export_attachment_text(fcf_obj):
    controlled_object = getattr(fcf_obj, "ControlledObject", None)
    controlled_name = controlled_object.Name if controlled_object else "<none>"
    controlled_sub = getattr(fcf_obj, "ControlledSubelement", "")

    if (
        str(getattr(fcf_obj, "ToleranceType", "")) == "Profile"
        and getattr(fcf_obj, "ProfileAllOver", False)
        and not controlled_sub
    ):
        return "{} (all over)".format(controlled_name)

    if controlled_sub:
        return "{}.{}".format(controlled_name, controlled_sub)

    return controlled_name


def dimension_export_attachment_text(dim_obj):
    ref1 = getattr(dim_obj, "ReferenceObject1", None)
    ref2 = getattr(dim_obj, "ReferenceObject2", None)
    sub1 = getattr(dim_obj, "ReferenceSubelement1", "")
    sub2 = getattr(dim_obj, "ReferenceSubelement2", "")

    text1 = ref1.Name if ref1 else "<none>"
    text2 = ref2.Name if ref2 else "<none>"

    if sub1:
        text1 = "{}.{}".format(text1, sub1)

    if sub2:
        text2 = "{}.{}".format(text2, sub2)

    if ref2 or sub2:
        return "{} to {}".format(text1, text2)

    return text1


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


def create_xcaf_datum_reference(
    dimtol_tool,
    datum_obj,
    position,
    face_label_map
):
    if datum_obj is None or not hasattr(datum_obj, "DatumLabel"):
        return None

    subname = getattr(datum_obj, "ReferencedSubelement", "")

    if subname not in face_label_map:
        FreeCAD.Console.PrintWarning(
            "No face label found for datum reference {} on {}.\n".format(
                datum_obj.DatumLabel,
                subname
            )
        )
        return None

    datum_name = str(datum_obj.DatumLabel)
    datum_label = dimtol_tool.AddDatum()
    datum_attr = XCAFDoc_Datum.Set(datum_label)
    xcaf_datum = XCAFDimTolObjects_DatumObject()
    xcaf_datum.SetName(TCollection_HAsciiString(datum_name))
    xcaf_datum.SetSemanticName(
        TCollection_HAsciiString("Datum {}".format(datum_name))
    )
    xcaf_datum.SetPosition(int(position))
    datum_attr.SetObject(xcaf_datum)

    shape_labels = TDF_LabelSequence()
    shape_labels.Append(face_label_map[subname])
    dimtol_tool.SetDatum(shape_labels, datum_label)
    return datum_label


def parse_datum_target_number(target_id):
    digits = "".join(ch for ch in str(target_id) if ch.isdigit())

    if not digits:
        return 0

    return int(digits)


def vector_to_gp_pnt(vector):
    return gp_Pnt(
        float(vector.x),
        float(vector.y),
        float(vector.z)
    )


def vector_to_gp_dir(vector):
    return gp_Dir(
        float(vector.x),
        float(vector.y),
        float(vector.z)
    )


def perpendicular_reference_direction(normal):
    x_axis = FreeCAD.Vector(1, 0, 0)
    normal_copy = FreeCAD.Vector(normal)
    normal_copy.normalize()

    if abs(normal_copy.dot(x_axis)) > 0.9:
        x_axis = FreeCAD.Vector(0, 1, 0)

    reference = x_axis - normal_copy.multiply(normal_copy.dot(x_axis))

    if reference.Length <= 1e-9:
        reference = FreeCAD.Vector(0, 1, 0)

    reference.normalize()
    return reference


def datum_target_axis(target_obj):
    point = MBDDatumTarget.get_point_from_target(target_obj)

    if point is None:
        return None

    normal = FreeCAD.Vector(0, 0, 1)

    try:
        face = target_obj.ReferencedObject.Shape.getElement(
            target_obj.ReferencedSubelement
        )
        u_min, u_max, v_min, v_max = face.ParameterRange
        normal = face.normalAt(
            (u_min + u_max) * 0.5,
            (v_min + v_max) * 0.5
        )

        if normal.Length <= 1e-9:
            normal = FreeCAD.Vector(0, 0, 1)
    except Exception:
        pass

    normal.normalize()
    reference = perpendicular_reference_direction(normal)

    return gp_Ax2(
        vector_to_gp_pnt(point),
        vector_to_gp_dir(normal),
        vector_to_gp_dir(reference)
    )


def configure_datum_target(datum_label, target_obj):
    parent_datum = getattr(target_obj, "ParentDatum", None)

    if parent_datum is None:
        return False

    target_axis = datum_target_axis(target_obj)

    if target_axis is None:
        return False

    datum_name = str(parent_datum.DatumLabel)
    target_number = parse_datum_target_number(target_obj.TargetId)

    datum_attr = XCAFDoc_Datum.Set(datum_label)
    datum_obj = XCAFDimTolObjects_DatumObject()

    datum_obj.SetName(
        TCollection_HAsciiString(datum_name)
    )
    datum_obj.SetSemanticName(
        TCollection_HAsciiString("Datum target {}".format(target_obj.TargetId))
    )
    datum_obj.SetPosition(1)
    datum_obj.IsDatumTarget(True)
    datum_obj.SetDatumTargetType(
        XDTO.XCAFDimTolObjects_DatumTargetType_Point
    )
    datum_obj.SetDatumTargetAxis(target_axis)
    datum_obj.SetDatumTargetNumber(target_number)

    datum_attr.SetObject(datum_obj)
    return True


def export_datum_targets(doc, dimtol_tool, face_label_map):
    exported_count = 0

    for target_obj in iter_semantic_datum_targets(doc):
        subname = getattr(target_obj, "ReferencedSubelement", "")

        if subname not in face_label_map:
            FreeCAD.Console.PrintWarning(
                "No face label found for datum target {} on {}\n".format(
                    target_obj.TargetId,
                    subname
                )
            )
            continue

        datum_label = dimtol_tool.AddDatum()

        if not configure_datum_target(datum_label, target_obj):
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 export for datum target {} because its point or parent datum could not be resolved.\n".format(
                    target_obj.TargetId
                )
            )
            continue

        shape_labels = TDF_LabelSequence()
        shape_labels.Append(face_label_map[subname])
        dimtol_tool.SetDatum(shape_labels, datum_label)

        FreeCAD.Console.PrintMessage(
            "Creating semantic datum target {} on {}\n".format(
                target_obj.TargetId,
                subname
            )
        )
        exported_count += 1

    return exported_count


def geom_tolerance_type_value(tolerance_type):
    enum_name = GEOMTOL_TYPE_BY_FCF_TYPE.get(str(tolerance_type))

    if not enum_name:
        return None

    return int(getattr(XDTO, enum_name))


def set_geom_tolerance_modifiers(geomtol_label, modifiers):
    if not modifiers:
        return

    modifier_array = TDataStd_IntegerArray.Set(
        geomtol_label.FindChild(GEOMTOL_CHILD_MODIFIERS),
        1,
        len(modifiers)
    )

    for index, modifier in enumerate(modifiers, start=1):
        modifier_array.SetValue(index, int(modifier))


def configure_geometric_tolerance(geomtol_label, pmi_obj):
    # pythonocc does not expose XCAFDoc_GeomTolerance.SetObject()
    # reliably here, so populate the child labels used by OCCT.
    tolerance_type = geom_tolerance_type_value(pmi_obj.ToleranceType)

    if tolerance_type is None:
        raise ValueError(
            "Unsupported FCF type {}".format(pmi_obj.ToleranceType)
        )

    TDataStd_Integer.Set(
        geomtol_label.FindChild(GEOMTOL_CHILD_TYPE),
        tolerance_type
    )

    if getattr(pmi_obj, "DiameterZone", False):
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

    modifiers = []

    if (
        str(pmi_obj.ToleranceType) == "Profile"
        and getattr(pmi_obj, "ProfileAllOver", False)
    ):
        modifiers.append(XDTO.XCAFDimTolObjects_GeomToleranceModif_All_Over)

    set_geom_tolerance_modifiers(geomtol_label, modifiers)


def controlled_labels_for_fcf(pmi_obj, face_label_map, subshape_label_map=None):
    if subshape_label_map is None:
        subshape_label_map = face_label_map

    if (
        str(pmi_obj.ToleranceType) == "Profile"
        and getattr(pmi_obj, "ProfileAllOver", False)
        and not getattr(pmi_obj, "ControlledSubelement", "")
    ):
        return [
            face_label_map[name]
            for name in sorted(face_label_map)
        ]

    subname = pmi_obj.ControlledSubelement

    if subname in subshape_label_map:
        return [subshape_label_map[subname]]

    return []


def set_geom_tolerance_shapes(dimtol_tool, controlled_labels, geomtol_label):
    if len(controlled_labels) == 1:
        dimtol_tool.SetGeomTolerance(
            controlled_labels[0],
            geomtol_label
        )
        return

    label_sequence = TDF_LabelSequence()

    for label in controlled_labels:
        label_sequence.Append(label)

    dimtol_tool.SetGeomTolerance(
        label_sequence,
        geomtol_label
    )


def export_feature_control_frames(
    doc,
    dimtol_tool,
    face_label_map,
    subshape_label_map=None
):
    for pmi_obj in iter_feature_control_frames(doc):
        if geom_tolerance_type_value(pmi_obj.ToleranceType) is None:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 export for unsupported FCF type {} on {}.\n".format(
                    pmi_obj.ToleranceType,
                    fcf_export_attachment_text(pmi_obj)
                )
            )
            continue

        controlled_labels = controlled_labels_for_fcf(
            pmi_obj,
            face_label_map,
            subshape_label_map
        )

        if not controlled_labels:
            FreeCAD.Console.PrintWarning(
                "FCF controlled attachment {} not found in subshape map.\n".format(
                    fcf_export_attachment_text(pmi_obj)
                )
            )
            continue

        FreeCAD.Console.PrintMessage(
            "Creating semantic {} tolerance on {}\n".format(
                str(pmi_obj.ToleranceType).lower(),
                fcf_export_attachment_text(pmi_obj)
            )
        )

        geomtol_label = dimtol_tool.AddGeomTolerance()
        configure_geometric_tolerance(geomtol_label, pmi_obj)

        set_geom_tolerance_shapes(
            dimtol_tool,
            controlled_labels,
            geomtol_label
        )

        link_datums_to_geom_tolerance(
            dimtol_tool,
            pmi_obj,
            face_label_map,
            geomtol_label
        )


def export_dimensions(doc, dimtol_tool, face_label_map):
    pending_location_dimensions = []

    for dim_obj in iter_semantic_dimensions(doc):
        dimension_type = dimension_type_value(dim_obj)

        if dimension_type is None:
            if dimension_is_linear_location(dim_obj):
                first_subname = dimension_reference_subname(
                    getattr(dim_obj, "ReferenceObject1", None),
                    getattr(dim_obj, "ReferenceSubelement1", "")
                )
                second_subname = dimension_reference_subname(
                    getattr(dim_obj, "ReferenceObject2", None),
                    getattr(dim_obj, "ReferenceSubelement2", "")
                )

                if first_subname in face_label_map and second_subname in face_label_map:
                    pending_location_dimensions.append({
                        "name": getattr(dim_obj, "Name", ""),
                        "first_subname": first_subname,
                        "second_subname": second_subname,
                        "nominal": dimension_nominal_value(dim_obj),
                        "purpose": str(getattr(dim_obj, "DimensionPurpose", "")),
                        "measurement_type": str(getattr(dim_obj, "MeasurementType", "")),
                        "lower_tolerance": float(getattr(dim_obj, "LowerTolerance", 0.0)),
                        "upper_tolerance": float(getattr(dim_obj, "UpperTolerance", 0.0)),
                        "lower_limit": float(getattr(dim_obj, "LowerLimit", 0.0)),
                        "upper_limit": float(getattr(dim_obj, "UpperLimit", 0.0)),
                    })
                    FreeCAD.Console.PrintMessage(
                        "Creating semantic linear location dimension on {} using AP242 post-write entities\n".format(
                            dimension_export_attachment_text(dim_obj)
                        )
                    )
                    continue

            FreeCAD.Console.PrintWarning(
                "Skipping AP242 export for unsupported dimension kind {} on {}.\n".format(
                    getattr(dim_obj, "DimensionKind", ""),
                    dimension_export_attachment_text(dim_obj)
                )
            )
            continue

        first_label = dimension_reference_label(
            getattr(dim_obj, "ReferenceObject1", None),
            getattr(dim_obj, "ReferenceSubelement1", ""),
            face_label_map
        )

        if first_label is None:
            FreeCAD.Console.PrintWarning(
                "Dimension first reference {} not found in subshape map.\n".format(
                    dimension_export_attachment_text(dim_obj)
                )
            )
            continue

        second_label = None

        if str(getattr(dim_obj, "DimensionKind", "")) == "Linear":
            second_label = dimension_reference_label(
                getattr(dim_obj, "ReferenceObject2", None),
                getattr(dim_obj, "ReferenceSubelement2", ""),
                face_label_map
            )

            if second_label is None:
                FreeCAD.Console.PrintWarning(
                    "Dimension second reference {} not found in subshape map.\n".format(
                        dimension_export_attachment_text(dim_obj)
                    )
                )
                continue

        FreeCAD.Console.PrintMessage(
            "Creating semantic {} dimension on {}\n".format(
                str(dim_obj.DimensionKind).lower(),
                dimension_export_attachment_text(dim_obj)
            )
        )

        dim_label = dimtol_tool.AddDimension()
        configure_dimension(dim_label, dim_obj)

        if dimension_is_plane_to_plane_size(dim_obj):
            first_labels = TDF_LabelSequence()
            empty_labels = TDF_LabelSequence()
            first_labels.Append(first_label)
            first_labels.Append(second_label)
            dimtol_tool.SetDimension(
                first_labels,
                empty_labels,
                dim_label
            )
        elif second_label is not None:
            first_labels = TDF_LabelSequence()
            second_labels = TDF_LabelSequence()
            first_labels.Append(first_label)
            second_labels.Append(second_label)
            dimtol_tool.SetDimension(
                first_labels,
                second_labels,
                dim_label
            )
        else:
            dimtol_tool.SetDimension(
                first_label,
                dim_label
            )

    return pending_location_dimensions


def link_datums_to_geom_tolerance(
    dimtol_tool,
    pmi_obj,
    face_label_map,
    geomtol_label
):
    if hasattr(pmi_obj, "DatumReference") and pmi_obj.DatumReference:
        datum_label = create_xcaf_datum_reference(
            dimtol_tool,
            pmi_obj.DatumReference,
            1,
            face_label_map
        )

        if datum_label is not None:
            dimtol_tool.SetDatumToGeomTol(datum_label, geomtol_label)

        return

    if not hasattr(pmi_obj, "DatumSystem") or not pmi_obj.DatumSystem:
        return

    ds = pmi_obj.DatumSystem

    for position, (_role_name, datums) in enumerate(
        datum_system_compartments(ds),
        start=1
    ):
        for datum_obj in datums:
            datum_label = create_xcaf_datum_reference(
                dimtol_tool,
                datum_obj,
                position,
                face_label_map
            )

            if datum_label is not None:
                dimtol_tool.SetDatumToGeomTol(
                    datum_label,
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


def next_step_entity_id(text):
    ids = [
        int(entity_id)
        for entity_id in re.findall(r"#(\d+)\s*=", text)
    ]

    if not ids:
        return 1

    return max(ids) + 1


def find_step_product_definition_shape(text):
    datum_match = re.search(
        r"DATUM_FEATURE\('[^']*','[^']*',#(\d+),",
        text
    )

    if datum_match:
        return int(datum_match.group(1))

    shape_aspect_match = re.search(
        r"SHAPE_ASPECT\('[^']*','[^']*',#(\d+),",
        text
    )

    if shape_aspect_match:
        return int(shape_aspect_match.group(1))

    product_shapes = re.findall(
        r"#(\d+)\s*=\s*PRODUCT_DEFINITION_SHAPE\('','',#\d+\);",
        text
    )

    if product_shapes:
        return int(product_shapes[-1])

    return None


def find_step_shape_representation(text):
    match = re.search(
        r"#(\d+)\s*=\s*ADVANCED_BREP_SHAPE_REPRESENTATION\("
        r".*?\),#(\d+)\);",
        text,
        re.DOTALL
    )

    if not match:
        return None, None

    return int(match.group(1)), int(match.group(2))


def find_step_length_unit(text, context_id=None):
    if context_id is not None:
        context_match = re.search(
            r"#{}\s*=\s*\(.*?GLOBAL_UNIT_ASSIGNED_CONTEXT\s*\(\((.*?)\)\).*?"
            r"REPRESENTATION_CONTEXT".format(context_id),
            text,
            re.DOTALL
        )

        if context_match:
            for ref in context_match.group(1).replace("\n", " ").split(","):
                ref = ref.strip()

                if not ref.startswith("#"):
                    continue

                unit_id = int(ref[1:])

                if re.search(
                    r"#{}\s*=\s*\(\s*LENGTH_UNIT\(\)".format(unit_id),
                    text
                ):
                    return unit_id

    match = re.search(
        r"#(\d+)\s*=\s*\(\s*LENGTH_UNIT\(\)",
        text
    )

    if not match:
        return None

    return int(match.group(1))


def step_advanced_face_map(text):
    face_ids = re.findall(
        r"#(\d+)\s*=\s*ADVANCED_FACE\(",
        text
    )

    return {
        "Face{}".format(index): int(entity_id)
        for index, entity_id in enumerate(face_ids, start=1)
    }


def step_float(value):
    text = "{:.12g}".format(float(value))

    if "e" not in text.lower() and "." not in text:
        text += "."

    return text


def location_dimension_measure_items(location_dim, unit_id, first_id):
    purpose = location_dim["purpose"]
    entity_id = first_id
    item_ids = []
    lines = []

    if purpose == "Limits":
        values = [
            ("nominal value", location_dim["nominal"]),
            ("lower limit", location_dim["lower_limit"]),
            ("upper limit", location_dim["upper_limit"]),
        ]
    else:
        values = [
            ("nominal value", location_dim["nominal"]),
        ]

    for label, value in values:
        item_ids.append(entity_id)
        lines.append(
            "#{} = ( LENGTH_MEASURE_WITH_UNIT() MEASURE_REPRESENTATION_ITEM() "
            "MEASURE_WITH_UNIT(POSITIVE_LENGTH_MEASURE({}),#{}) "
            "REPRESENTATION_ITEM('{}') );".format(
                entity_id,
                step_float(value),
                unit_id,
                label
            )
        )
        entity_id += 1

    return item_ids, lines, entity_id


def append_step_dimensional_locations(filepath, location_dimensions):
    if not location_dimensions:
        return

    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    product_shape_id = find_step_product_definition_shape(text)
    shape_rep_id, context_id = find_step_shape_representation(text)
    unit_id = find_step_length_unit(text, context_id)
    face_map = step_advanced_face_map(text)
    next_id = next_step_entity_id(text)
    lines = []
    exported_count = 0

    if product_shape_id is None or shape_rep_id is None or context_id is None or unit_id is None:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 linear location dimensions because STEP context entities could not be identified.\n"
        )
        return

    for location_dim in location_dimensions:
        first_face_id = face_map.get(location_dim["first_subname"])
        second_face_id = face_map.get(location_dim["second_subname"])

        if first_face_id is None or second_face_id is None:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 linear location dimension {} because a face entity could not be mapped.\n".format(
                    location_dim["name"]
                )
            )
            continue

        first_aspect_id = next_id
        first_gisu_id = next_id + 1
        second_aspect_id = next_id + 2
        second_gisu_id = next_id + 3
        next_id += 4

        lines.extend([
            "#{} = SHAPE_ASPECT('','',#{},.T.);".format(
                first_aspect_id,
                product_shape_id
            ),
            "#{} = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#{},#{},#{});".format(
                first_gisu_id,
                first_aspect_id,
                shape_rep_id,
                first_face_id
            ),
            "#{} = SHAPE_ASPECT('','',#{},.T.);".format(
                second_aspect_id,
                product_shape_id
            ),
            "#{} = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#{},#{},#{});".format(
                second_gisu_id,
                second_aspect_id,
                shape_rep_id,
                second_face_id
            ),
        ])

        item_ids, item_lines, next_id = location_dimension_measure_items(
            location_dim,
            unit_id,
            next_id
        )
        lines.extend(item_lines)

        shape_dimension_id = next_id
        characteristic_rep_id = next_id + 1
        location_id = next_id + 2
        next_id += 3

        location_entity = "DIMENSIONAL_LOCATION"

        if location_dim.get("measurement_type") in ("X", "Y", "Z"):
            location_entity = "DIRECTED_DIMENSIONAL_LOCATION"

        lines.extend([
            "#{} = SHAPE_DIMENSION_REPRESENTATION('',({}),#{});".format(
                shape_dimension_id,
                ",".join("#{}".format(item_id) for item_id in item_ids),
                context_id
            ),
            "#{} = DIMENSIONAL_CHARACTERISTIC_REPRESENTATION(#{},#{});".format(
                characteristic_rep_id,
                location_id,
                shape_dimension_id
            ),
            "#{} = {}('linear distance',$,#{},#{});".format(
                location_id,
                location_entity,
                first_aspect_id,
                second_aspect_id
            ),
        ])

        tolerances = dimension_tolerance_values_from_export_data(location_dim)

        if tolerances:
            lower_tol, upper_tol = tolerances
            upper_measure_id = next_id
            lower_measure_id = next_id + 1
            tolerance_value_id = next_id + 2
            plus_minus_id = next_id + 3
            next_id += 4
            lines.extend([
                "#{} = MEASURE_WITH_UNIT({},#{});".format(
                    upper_measure_id,
                    step_float(upper_tol),
                    unit_id
                ),
                "#{} = MEASURE_WITH_UNIT({},#{});".format(
                    lower_measure_id,
                    step_float(-lower_tol),
                    unit_id
                ),
                "#{} = TOLERANCE_VALUE(#{},#{});".format(
                    tolerance_value_id,
                    lower_measure_id,
                    upper_measure_id
                ),
                "#{} = PLUS_MINUS_TOLERANCE(#{},#{});".format(
                    plus_minus_id,
                    tolerance_value_id,
                    location_id
                ),
            ])

        exported_count += 1

    if not lines:
        return

    insertion = "\n".join(lines) + "\n"
    insertion_index = text.rfind("ENDSEC;")

    if insertion_index < 0:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 linear location dimensions because ENDSEC was not found.\n"
        )
        return

    text = (
        text[:insertion_index]
        + insertion
        + text[insertion_index:]
    )

    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write(text)

    FreeCAD.Console.PrintMessage(
        "Added {} AP242 dimensional location entities after STEP write.\n".format(
            exported_count
        )
    )


def dimension_tolerance_values_from_export_data(location_dim):
    if location_dim["purpose"] not in ("UnequalBilateral", "EqualBilateral"):
        return None

    return (
        abs(location_dim["lower_tolerance"]),
        abs(location_dim["upper_tolerance"]),
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
    pending_location_dimensions = []

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
        edge_label_map = build_edge_label_map(
            shape_tool,
            simple_label
        )
        subshape_label_map = dict(face_label_map)
        subshape_label_map.update(edge_label_map)

        export_datums(
            doc,
            dimtol_tool,
            face_label_map
        )

        FreeCAD.Console.PrintMessage(
            "Mapped {} face labels and {} edge labels for {}\n".format(
                len(face_label_map),
                len(edge_label_map),
                obj.Name
            )
        )

        export_datum_targets(
            doc,
            dimtol_tool,
            face_label_map
        )

        export_feature_control_frames(
            doc,
            dimtol_tool,
            face_label_map,
            subshape_label_map
        )

        pending_location_dimensions.extend(
            export_dimensions(
                doc,
                dimtol_tool,
                face_label_map
            )
        )

        exported_count += 1

    transfer_and_write_step(
        xcaf_doc,
        dimtol_tool,
        filepath
    )

    if exported_count == 1:
        append_step_dimensional_locations(
            filepath,
            pending_location_dimensions
        )
    elif pending_location_dimensions:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 linear location dimensions because multiple export shapes were written.\n"
        )

    FreeCAD.Console.PrintMessage(
        "Exported {} shapes to {}\n".format(
            exported_count,
            filepath
        )
    )

    return True
