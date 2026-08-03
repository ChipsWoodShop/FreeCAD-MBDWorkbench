# MBDExporter.py

import json
import math
import re

import FreeCAD
import Part
from PySide import QtGui

from . import MBDDatumTarget
from .MBDDatumSystem import datum_system_compartments

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

STEP_GEOMTOL_ENTITY_BY_FCF_TYPE = {
    "Angularity": "ANGULARITY_TOLERANCE",
    "CircularRunout": "CIRCULAR_RUNOUT_TOLERANCE",
    "Circularity": "ROUNDNESS_TOLERANCE",
    "Cylindricity": "CYLINDRICITY_TOLERANCE",
    "Flatness": "FLATNESS_TOLERANCE",
    "LineProfile": "LINE_PROFILE_TOLERANCE",
    "Parallelism": "PARALLELISM_TOLERANCE",
    "Perpendicularity": "PERPENDICULARITY_TOLERANCE",
    "Position": "POSITION_TOLERANCE",
    "Profile": "SURFACE_PROFILE_TOLERANCE",
    "Straightness": "STRAIGHTNESS_TOLERANCE",
    "TotalRunout": "TOTAL_RUNOUT_TOLERANCE",
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


def freecad_shape_type(shape):
    shape_type = getattr(shape, "ShapeType", None)

    if callable(shape_type):
        return shape_type()

    return shape_type


def exportable_shape_objects(doc):
    """Return shape objects that should be written as top-level STEP shapes.

    Imported STEP files can expose both a simple solid and a compound wrapper
    for the same geometry.  Exporting both duplicates geometry and semantic PMI
    references, which is why re-exporting an imported NIST file produced two
    shape objects and twice as many datum labels.  When simple solid-like
    objects are present, prefer them and skip compound wrappers.  A document
    that only contains a compound still exports that compound.
    """
    candidates = [
        obj
        for obj in doc.Objects
        if should_export_shape_object(obj)
    ]
    has_simple_solid = any(
        freecad_shape_type(obj.Shape) not in (TopAbs_COMPOUND, "Compound", "COMPOUND")
        for obj in candidates
    )

    if not has_simple_solid:
        return candidates

    return [
        obj
        for obj in candidates
        if freecad_shape_type(obj.Shape) not in (TopAbs_COMPOUND, "Compound", "COMPOUND")
    ]


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


def equivalent_face_subname(export_obj, ref_obj, ref_sub):
    if ref_obj is None:
        return None

    if hasattr(ref_obj, "DatumLabel"):
        ref_sub = getattr(ref_obj, "ReferencedSubelement", "")
        ref_obj = getattr(ref_obj, "ReferencedObject", None)

    if not ref_sub:
        return None

    if ref_obj is export_obj:
        return str(ref_sub)

    try:
        reference_face = ref_obj.Shape.getElement(ref_sub)
    except Exception:
        return None

    try:
        if hasattr(reference_face, "isSame"):
            for index, face in enumerate(export_obj.Shape.Faces, start=1):
                if reference_face.isSame(face):
                    return "Face{}".format(index)
    except Exception:
        pass

    try:
        reference_center = reference_face.CenterOfMass
        reference_area = float(reference_face.Area)
    except Exception:
        return None

    best_subname = None
    best_distance = None
    area_tolerance = max(abs(reference_area) * 1e-6, 1e-6)

    for index, face in enumerate(export_obj.Shape.Faces, start=1):
        try:
            area_delta = abs(float(face.Area) - reference_area)

            if area_delta > area_tolerance:
                continue

            distance = (face.CenterOfMass - reference_center).Length
        except Exception:
            continue

        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_subname = "Face{}".format(index)

    if best_distance is not None and best_distance <= 1e-5:
        return best_subname

    return None


def dimension_reference_label(export_obj, ref_obj, ref_sub, face_label_map):
    subname = equivalent_face_subname(export_obj, ref_obj, ref_sub)

    if not subname:
        return None

    return face_label_map.get(subname)


def dimension_reference_subname(export_obj, ref_obj, ref_sub):
    return equivalent_face_subname(export_obj, ref_obj, ref_sub)


def dimension_type_value(dim_obj):
    dimension_kind = str(getattr(dim_obj, "DimensionKind", ""))
    reference_pattern = str(getattr(dim_obj, "ReferencePattern", ""))
    ap242_entity = str(getattr(dim_obj, "AP242Entity", ""))

    if ap242_entity in ("DIMENSIONAL_LOCATION", "DIRECTED_DIMENSIONAL_LOCATION"):
        return None

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
    if str(getattr(dim_obj, "AP242Entity", "")) in (
        "DIMENSIONAL_LOCATION",
        "DIRECTED_DIMENSIONAL_LOCATION",
    ):
        return True

    return (
        str(getattr(dim_obj, "DimensionKind", "")) == "Linear"
        and not dimension_is_plane_to_plane_size(dim_obj)
    )


def dimension_is_angular(dim_obj):
    return str(getattr(dim_obj, "DimensionKind", "")) == "Angular"


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


def iter_presentation_placeholder_pmi(doc):
    for obj in iter_semantic_datums(doc):
        yield obj

    for obj in iter_semantic_datum_targets(doc):
        yield obj

    for obj in iter_semantic_dimensions(doc):
        yield obj

    for obj in iter_feature_control_frames(doc):
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


def presentation_placeholder_type(obj):
    if hasattr(obj, "DatumLabel"):
        return "Datum"

    if hasattr(obj, "TargetId") and hasattr(obj, "ParentDatum"):
        return "DatumTarget"

    if hasattr(obj, "DimensionKind") and hasattr(obj, "DimensionPurpose"):
        return "Dimension"

    if hasattr(obj, "ToleranceType") and hasattr(obj, "ControlledObject"):
        return "FCF"

    return "PMI"


def presentation_placeholder_name(obj):
    pmi_type = presentation_placeholder_type(obj)

    if pmi_type == "Datum":
        return "Datum Feature {}".format(getattr(obj, "DatumLabel", obj.Name))

    if pmi_type == "DatumTarget":
        return "Datum Target {}".format(getattr(obj, "TargetId", obj.Name))

    if pmi_type == "Dimension":
        return "{} Dimension {}".format(
            getattr(obj, "DimensionKind", ""),
            getattr(obj, "Name", "")
        ).strip()

    if pmi_type == "FCF":
        return "{} FCF {}".format(
            getattr(obj, "ToleranceType", ""),
            getattr(obj, "Name", "")
        ).strip()

    return getattr(obj, "Name", "PMI")


def pmi_presentation_placeholder_data(obj):
    pmi_type = presentation_placeholder_type(obj)

    try:
        text_height = float(getattr(obj, "AnnotationTextHeight", 0.0))
    except Exception:
        text_height = 0.0

    if text_height <= 0.0:
        text_height = 7.0

    data = {
        "name": presentation_placeholder_name(obj),
        "object_name": getattr(obj, "Name", ""),
        "type": pmi_type,
        "origin": getattr(obj, "AnnotationOrigin", FreeCAD.Vector(0, 0, 0)),
        "normal": getattr(obj, "AnnotationNormal", FreeCAD.Vector(0, 0, 1)),
        "direction": getattr(obj, "AnnotationDirection", FreeCAD.Vector(1, 0, 0)),
        "text_height": text_height,
        "layout_mode": str(getattr(obj, "DisplayLayoutMode", "")),
        "has_leader": pmi_type in ("Datum", "DatumTarget", "Dimension", "FCF"),
    }

    if pmi_type == "Datum":
        data["datum_label"] = str(getattr(obj, "DatumLabel", ""))
        data["subname"] = str(getattr(obj, "ReferencedSubelement", ""))
    elif pmi_type == "FCF":
        data["tolerance_type"] = str(getattr(obj, "ToleranceType", ""))
        data["subname"] = str(getattr(obj, "ControlledSubelement", ""))
    elif pmi_type == "Dimension":
        data["dimension_kind"] = str(getattr(obj, "DimensionKind", ""))
        data["subname"] = str(getattr(obj, "ReferenceSubelement1", ""))
    elif pmi_type == "DatumTarget":
        data["target_type"] = str(getattr(obj, "TargetType", ""))
        data["subname"] = str(getattr(obj, "ReferencedSubelement", ""))

    return data


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
        subnames = [
            str(item)
            for item in getattr(pmi_obj, "ReferencedSubelementList", [])
            if str(item)
        ]

        if not subnames and subname:
            subnames = [subname]

        if subname not in face_label_map:
            FreeCAD.Console.PrintWarning(
                "No face label found for {}\n".format(subname)
            )
            continue

        mapped_subnames = [
            item
            for item in subnames
            if item in face_label_map
        ]

        if not mapped_subnames:
            FreeCAD.Console.PrintWarning(
                "No mapped face labels found for datum {}.\n".format(
                    getattr(pmi_obj, "DatumLabel", "")
                )
            )
            continue

        for extra_subname in subnames:
            if extra_subname not in face_label_map:
                FreeCAD.Console.PrintWarning(
                    "No face label found for datum {} extra binding {}.\n".format(
                        getattr(pmi_obj, "DatumLabel", ""),
                        extra_subname
                    )
                )

        datum_name = str(pmi_obj.DatumLabel)

        FreeCAD.Console.PrintMessage(
            "Creating semantic datum {} on {}\n".format(
                datum_name,
                ", ".join(mapped_subnames)
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

        for mapped_subname in mapped_subnames:
            shape_labels.Append(face_label_map[mapped_subname])

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

        if str(face.Orientation).lower() == "reversed":
            normal = normal.negative()
    except Exception:
        pass

    normal.normalize()
    reference = None

    if str(target_obj.TargetType) in ("Line", "Circle", "Rectangle"):
        reference = FreeCAD.Vector(getattr(target_obj, "TargetDirection", FreeCAD.Vector()))

        if reference.Length > 1e-9:
            reference = reference - normal * reference.dot(normal)

            if reference.Length <= 1e-9:
                reference = None
            else:
                reference.normalize()
        else:
            reference = None

    if str(target_obj.TargetType) == "Line" and reference is None:
        line = MBDDatumTarget.line_geometry_from_target(target_obj)

        if line is None:
            return None

        reference = FreeCAD.Vector(line["direction"])
        reference = reference - normal * reference.dot(normal)

        if reference.Length <= 1e-9:
            return None

        reference.normalize()

    if reference is None:
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
    target_type = str(target_obj.TargetType)
    target_enum = getattr(
        XDTO,
        "XCAFDimTolObjects_DatumTargetType_" + target_type,
        None
    )

    if target_enum is None:
        return False

    if target_type == "Area":
        return False

    datum_obj.SetDatumTargetType(target_enum)
    datum_obj.SetDatumTargetAxis(target_axis)
    datum_obj.SetDatumTargetNumber(target_number)

    if target_type == "Line":
        line = MBDDatumTarget.line_geometry_from_target(target_obj)

        if line is None:
            return False

        datum_obj.SetDatumTargetLength(float(line["length"]))

    if target_type == "Circle":
        circle = MBDDatumTarget.circle_geometry_from_target(target_obj)

        if circle is None:
            return False

        datum_obj.SetDatumTargetLength(float(circle["diameter"]))

    if target_type == "Rectangle":
        rectangle = MBDDatumTarget.rectangle_geometry_from_target(target_obj)

        if rectangle is None:
            return False

        datum_obj.SetDatumTargetLength(float(rectangle["length"]))
        datum_obj.SetDatumTargetWidth(float(rectangle["width"]))

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

        if str(getattr(target_obj, "TargetType", "")) == "Area":
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 export for arbitrary area datum target {} because the current OCCT writer path does not emit generic Area targets.\n".format(
                    target_obj.TargetId
                )
            )
            continue

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


def append_optional_geom_tolerance_modifier(
    modifiers,
    pmi_obj,
    property_name,
    enum_name,
    display_name
):
    if not getattr(pmi_obj, property_name, False):
        return

    if hasattr(XDTO, enum_name):
        modifiers.append(getattr(XDTO, enum_name))
        return

    FreeCAD.Console.PrintWarning(
        "AP242 export for {} cannot include {} because this OCCT binding "
        "does not expose {}.\n".format(
            getattr(pmi_obj, "Name", "<FCF>"),
            display_name,
            enum_name
        )
    )


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

    material_modifier = str(
        getattr(pmi_obj, "MaterialConditionModifier", "None")
    )
    material_requirement = XDTO.XCAFDimTolObjects_GeomToleranceMatReqModif_None
    if material_modifier == "MMC":
        material_requirement = XDTO.XCAFDimTolObjects_GeomToleranceMatReqModif_M
    elif material_modifier == "LMC":
        material_requirement = XDTO.XCAFDimTolObjects_GeomToleranceMatReqModif_L

    TDataStd_Integer.Set(
        geomtol_label.FindChild(GEOMTOL_CHILD_MATERIAL_REQUIREMENT),
        int(material_requirement)
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

    append_optional_geom_tolerance_modifier(
        modifiers,
        pmi_obj,
        "TangentPlaneModifier",
        "XCAFDimTolObjects_GeomToleranceModif_Tangent_Plane",
        "tangent plane modifier"
    )
    append_optional_geom_tolerance_modifier(
        modifiers,
        pmi_obj,
        "StatisticalToleranceModifier",
        "XCAFDimTolObjects_GeomToleranceModif_Statistical_Tolerance",
        "statistical tolerance modifier"
    )
    append_optional_geom_tolerance_modifier(
        modifiers,
        pmi_obj,
        "CommonZoneModifier",
        "XCAFDimTolObjects_GeomToleranceModif_Common_Zone",
        "common zone modifier"
    )

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


def projected_zone_export_data(pmi_obj, controlled_labels):
    if not getattr(pmi_obj, "ProjectedToleranceZone", False):
        return None

    if str(getattr(pmi_obj, "ToleranceType", "")) != "Position":
        return None

    if not getattr(pmi_obj, "DiameterZone", False):
        return None

    subname = getattr(pmi_obj, "ControlledSubelement", "")

    if not subname or len(controlled_labels) != 1:
        return None

    try:
        height = float(getattr(pmi_obj, "ProjectedToleranceHeight", 0.0))
    except Exception:
        height = 0.0

    if height <= 0.0:
        return None

    return {
        "name": getattr(pmi_obj, "Name", ""),
        "subname": subname,
        "height": height,
    }


def advanced_geometric_tolerance_export_base(pmi_obj, controlled_labels):
    tolerance_entity = STEP_GEOMTOL_ENTITY_BY_FCF_TYPE.get(
        str(getattr(pmi_obj, "ToleranceType", ""))
    )

    if tolerance_entity is None:
        return None

    subname = getattr(pmi_obj, "ControlledSubelement", "")

    if (
        not subname
        and str(getattr(pmi_obj, "ToleranceType", "")) == "Profile"
        and getattr(pmi_obj, "ProfileAllOver", False)
    ):
        FreeCAD.Console.PrintWarning(
            "Skipping advanced AP242 FCF semantics for {} because all-over profile currently maps to multiple faces.\n".format(
                getattr(pmi_obj, "Name", "<FCF>")
            )
        )
        return None

    if not subname or len(controlled_labels) != 1:
        FreeCAD.Console.PrintWarning(
            "Skipping advanced AP242 FCF semantics for {} because it is not attached to one controlled subshape.\n".format(
                getattr(pmi_obj, "Name", "<FCF>")
            )
        )
        return None

    if not subname.startswith("Face"):
        FreeCAD.Console.PrintWarning(
            "Skipping advanced AP242 FCF semantics for {} because only face-backed tolerances are currently mapped.\n".format(
                getattr(pmi_obj, "Name", "<FCF>")
            )
        )
        return None

    return {
        "name": getattr(pmi_obj, "Name", ""),
        "subname": subname,
        "tolerance_entity": tolerance_entity,
    }


def maximum_tolerance_export_data(pmi_obj, controlled_labels):
    if not getattr(pmi_obj, "MaximumToleranceValueEnabled", False):
        return None

    base = advanced_geometric_tolerance_export_base(
        pmi_obj,
        controlled_labels
    )

    if base is None:
        return None

    try:
        maximum_value = float(getattr(pmi_obj, "MaximumToleranceValue", 0.0))
    except Exception:
        maximum_value = 0.0

    if maximum_value <= 0.0:
        return None

    base["maximum_value"] = maximum_value
    return base


def unit_basis_tolerance_export_data(pmi_obj, controlled_labels):
    if not getattr(pmi_obj, "UnitBasisToleranceEnabled", False):
        return None

    base = advanced_geometric_tolerance_export_base(
        pmi_obj,
        controlled_labels
    )

    if base is None:
        return None

    try:
        primary = float(getattr(pmi_obj, "UnitBasisPrimaryLength", 0.0))
    except Exception:
        primary = 0.0

    try:
        secondary = float(getattr(pmi_obj, "UnitBasisSecondaryLength", 0.0))
    except Exception:
        secondary = 0.0

    if primary <= 0.0:
        return None

    unit_type = str(getattr(pmi_obj, "UnitBasisType", "Length"))

    if unit_type == "Rectangular" and secondary <= 0.0:
        return None

    base.update({
        "unit_type": unit_type,
        "primary": primary,
        "secondary": secondary,
    })
    return base


def non_uniform_zone_export_data(pmi_obj, controlled_labels):
    if not getattr(pmi_obj, "NonUniformToleranceZone", False):
        return None

    base = advanced_geometric_tolerance_export_base(
        pmi_obj,
        controlled_labels
    )

    if base is None:
        return None

    return base


def affected_plane_export_data(pmi_obj, controlled_labels):
    affected_obj = getattr(pmi_obj, "AffectedPlaneObject", None)
    affected_sub = getattr(pmi_obj, "AffectedPlaneSubelement", "")

    if affected_obj is None or not affected_sub:
        return None

    base = advanced_geometric_tolerance_export_base(
        pmi_obj,
        controlled_labels
    )

    if base is None:
        return None

    if not str(affected_sub).startswith("Edge"):
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 affected-plane export for {} because the affected-plane reference is not an edge.\n".format(
                getattr(pmi_obj, "Name", "<FCF>")
            )
        )
        return None

    base["affected_subname"] = str(affected_sub)
    return base


def runout_orientation_export_data(pmi_obj, controlled_labels):
    tolerance_type = str(getattr(pmi_obj, "ToleranceType", ""))

    if tolerance_type not in ("CircularRunout", "TotalRunout"):
        return None

    base = advanced_geometric_tolerance_export_base(
        pmi_obj,
        controlled_labels
    )

    if base is None:
        return None

    try:
        angle = float(getattr(pmi_obj, "RunoutOrientationAngle", 0.0))
    except Exception:
        angle = 0.0

    base["angle_degrees"] = angle
    return base


def simple_imported_fcf_export_data(pmi_obj):
    if str(getattr(pmi_obj, "AP242ImportStatus", "")) != "Native":
        return None

    tolerance_type = str(getattr(pmi_obj, "ToleranceType", ""))

    if tolerance_type not in (
        "Angularity",
        "Circularity",
        "CircularRunout",
        "Cylindricity",
        "Flatness",
        "LineProfile",
        "Parallelism",
        "Perpendicularity",
        "Position",
        "Profile",
        "Straightness",
        "TotalRunout",
    ):
        return None

    subname = str(getattr(pmi_obj, "ControlledSubelement", ""))
    subnames = [
        str(item)
        for item in getattr(pmi_obj, "ControlledSubelementList", [])
        if str(item)
    ]

    if not subnames and subname:
        subnames = [subname]

    if not subnames or any(not item.startswith("Face") for item in subnames):
        return None

    try:
        tolerance_value = float(getattr(pmi_obj, "ToleranceValue", 0.0))
    except Exception:
        tolerance_value = 0.0

    if tolerance_value <= 0.0:
        return None

    datum_compartments = []
    datum_system = getattr(pmi_obj, "DatumSystem", None)

    if datum_system is not None:
        for _role_name, datums in datum_system_compartments(datum_system):
            labels = [
                str(getattr(datum_obj, "DatumLabel", ""))
                for datum_obj in datums
                if getattr(datum_obj, "DatumLabel", "")
            ]

            if labels:
                datum_compartments.append(labels)

    return {
        "name": getattr(pmi_obj, "Name", ""),
        "subname": subname,
        "subnames": subnames,
        "tolerance_type": tolerance_type,
        "tolerance_value": tolerance_value,
        "datum_compartments": datum_compartments,
        "material_condition": str(getattr(
            pmi_obj,
            "MaterialConditionModifier",
            "None"
        )),
        "tangent_plane": bool(getattr(pmi_obj, "TangentPlaneModifier", False)),
        "statistical_tolerance": bool(getattr(
            pmi_obj,
            "StatisticalToleranceModifier",
            False
        )),
        "common_zone": bool(getattr(pmi_obj, "CommonZoneModifier", False)),
        "projected_zone": bool(getattr(pmi_obj, "ProjectedToleranceZone", False)),
        "projected_height": float(getattr(
            pmi_obj,
            "ProjectedToleranceHeight",
            0.0
        )),
        "unequally_disposed": bool(getattr(
            pmi_obj,
            "UnequallyDisposedZone",
            False
        )),
        "unequal_offset": float(getattr(
            pmi_obj,
            "UnequallyDisposedOffset",
            0.0
        )),
        "maximum_enabled": bool(getattr(
            pmi_obj,
            "MaximumToleranceValueEnabled",
            False
        )),
        "maximum_value": float(getattr(
            pmi_obj,
            "MaximumToleranceValue",
            0.0
        )),
        "unit_basis_enabled": bool(getattr(
            pmi_obj,
            "UnitBasisToleranceEnabled",
            False
        )),
        "unit_basis_type": str(getattr(pmi_obj, "UnitBasisType", "Length")),
        "unit_basis_primary": float(getattr(
            pmi_obj,
            "UnitBasisPrimaryLength",
            0.0
        )),
        "unit_basis_secondary": float(getattr(
            pmi_obj,
            "UnitBasisSecondaryLength",
            0.0
        )),
        "non_uniform_zone": bool(getattr(
            pmi_obj,
            "NonUniformToleranceZone",
            False
        )),
        "runout_orientation_angle": float(getattr(
            pmi_obj,
            "RunoutOrientationAngle",
            0.0
        )),
    }


def profile_export_type_key(pmi_obj):
    tolerance_type = str(getattr(pmi_obj, "ToleranceType", ""))

    if tolerance_type in ("Profile", "LineProfile"):
        return tolerance_type

    normalized = tolerance_type.replace(" ", "").replace("_", "").lower()

    if normalized in ("profileofline", "lineprofile"):
        return "LineProfile"

    if normalized in ("profileofsurface", "surfaceprofile", "profile"):
        return "Profile"

    name = str(getattr(pmi_obj, "Name", ""))
    subname = str(getattr(pmi_obj, "ControlledSubelement", ""))

    if "LineProfile" in name or subname.startswith("Edge"):
        return "LineProfile"

    if "Profile" in name or subname.startswith("Face"):
        return "Profile"

    return tolerance_type


def unequally_disposed_profile_export_data(pmi_obj, controlled_labels):
    if not getattr(pmi_obj, "UnequallyDisposedZone", False):
        return None

    tolerance_type = profile_export_type_key(pmi_obj)

    if tolerance_type not in ("Profile", "LineProfile"):
        return None

    subname = getattr(pmi_obj, "ControlledSubelement", "")

    if not subname or len(controlled_labels) != 1:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 unequal-disposition export for {} because it is not attached to one controlled subshape.\n".format(
                getattr(pmi_obj, "Name", "<FCF>")
            )
        )
        return None

    if tolerance_type == "Profile" and not subname.startswith("Face"):
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 unequal-disposition export for {} because only face-backed profile tolerances are currently mapped.\n".format(
                getattr(pmi_obj, "Name", "<FCF>")
            )
        )
        return None

    if (
        tolerance_type == "LineProfile"
        and not (
            subname.startswith("Edge")
            or (
                subname.startswith("Face")
                and getattr(pmi_obj, "ProfileDirectionObject", None) is not None
                and str(getattr(
                    pmi_obj,
                    "ProfileDirectionSubelement",
                    ""
                )).startswith("Edge")
            )
        )
    ):
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 unequal-disposition export for {} because line profile must be edge-backed or face-backed with a stored direction line.\n".format(
                getattr(pmi_obj, "Name", "<FCF>")
            )
        )
        return None

    try:
        offset = float(getattr(pmi_obj, "UnequallyDisposedOffset", 0.0))
    except Exception:
        offset = 0.0

    if offset <= 0.0:
        return None

    return {
        "name": getattr(pmi_obj, "Name", ""),
        "subname": subname,
        "offset": offset,
        "tolerance_type": tolerance_type,
    }


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
    pending_projected_zones = []
    pending_unequal_profiles = []
    pending_maximum_tolerances = []
    pending_unit_basis_tolerances = []
    pending_non_uniform_zones = []
    pending_affected_planes = []
    pending_runout_orientations = []
    pending_simple_imported_fcfs = []
    pending_annotation_placeholders = []

    for pmi_obj in iter_feature_control_frames(doc):
        simple_imported_fcf = simple_imported_fcf_export_data(pmi_obj)

        if simple_imported_fcf is not None:
            pending_simple_imported_fcfs.append(simple_imported_fcf)
            FreeCAD.Console.PrintMessage(
                "Creating semantic {} tolerance on {} using AP242 post-write entities\n".format(
                    str(pmi_obj.ToleranceType).lower(),
                    fcf_export_attachment_text(pmi_obj)
                )
            )
            continue

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
        projected_zone = projected_zone_export_data(
            pmi_obj,
            controlled_labels
        )

        if projected_zone is not None:
            pending_projected_zones.append(projected_zone)

        unequal_profile = unequally_disposed_profile_export_data(
            pmi_obj,
            controlled_labels
        )

        if unequal_profile is not None:
            pending_unequal_profiles.append(unequal_profile)

        maximum_tolerance = maximum_tolerance_export_data(
            pmi_obj,
            controlled_labels
        )

        if maximum_tolerance is not None:
            pending_maximum_tolerances.append(maximum_tolerance)

        unit_basis_tolerance = unit_basis_tolerance_export_data(
            pmi_obj,
            controlled_labels
        )

        if unit_basis_tolerance is not None:
            pending_unit_basis_tolerances.append(unit_basis_tolerance)

        non_uniform_zone = non_uniform_zone_export_data(
            pmi_obj,
            controlled_labels
        )

        if non_uniform_zone is not None:
            pending_non_uniform_zones.append(non_uniform_zone)

        affected_plane = affected_plane_export_data(
            pmi_obj,
            controlled_labels
        )

        if affected_plane is not None:
            pending_affected_planes.append(affected_plane)

        runout_orientation = runout_orientation_export_data(
            pmi_obj,
            controlled_labels
        )

        if runout_orientation is not None:
            pending_runout_orientations.append(runout_orientation)

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

    return (
        pending_projected_zones,
        pending_unequal_profiles,
        pending_maximum_tolerances,
        pending_unit_basis_tolerances,
        pending_non_uniform_zones,
        pending_affected_planes,
        pending_runout_orientations,
        pending_simple_imported_fcfs,
    )


def export_dimensions(doc, dimtol_tool, face_label_map, export_obj):
    # Prefer native OCCT/XCAF dimension export when it produces valid shape
    # references. For radius, angular, and selected location cases, the direct
    # writer path produced null STEP references during testing, so collect those
    # dimensions here and append a narrow AP242 entity set after the main write.
    pending_location_dimensions = []
    pending_size_dimensions = []
    pending_angular_dimensions = []

    for dim_obj in iter_semantic_dimensions(doc):
        dimension_type = dimension_type_value(dim_obj)

        if (
            str(getattr(dim_obj, "AP242ImportStatus", "")) == "Native"
            and str(getattr(dim_obj, "DimensionKind", "")) == "Diameter"
        ):
            first_subname = dimension_reference_subname(
                export_obj,
                getattr(dim_obj, "ReferenceObject1", None),
                getattr(dim_obj, "ReferenceSubelement1", "")
            )

            if first_subname in face_label_map:
                pending_size_dimensions.append({
                    "name": getattr(dim_obj, "Name", ""),
                    "subname": first_subname,
                    "kind": "diameter",
                    "nominal": dimension_nominal_value(dim_obj),
                    "purpose": str(getattr(dim_obj, "DimensionPurpose", "")),
                    "lower_tolerance": float(getattr(dim_obj, "LowerTolerance", 0.0)),
                    "upper_tolerance": float(getattr(dim_obj, "UpperTolerance", 0.0)),
                    "lower_limit": float(getattr(dim_obj, "LowerLimit", 0.0)),
                    "upper_limit": float(getattr(dim_obj, "UpperLimit", 0.0)),
                })
                FreeCAD.Console.PrintMessage(
                    "Creating semantic diameter dimension on {} using AP242 post-write entities\n".format(
                        dimension_export_attachment_text(dim_obj)
                    )
                )
            else:
                FreeCAD.Console.PrintWarning(
                    "Skipping AP242 imported diameter dimension on {} because its face could not be mapped.\n".format(
                        dimension_export_attachment_text(dim_obj)
                    )
                )

            continue

        if str(getattr(dim_obj, "DimensionKind", "")) == "Radius":
            first_subname = dimension_reference_subname(
                export_obj,
                getattr(dim_obj, "ReferenceObject1", None),
                getattr(dim_obj, "ReferenceSubelement1", "")
            )

            if first_subname in face_label_map:
                pending_size_dimensions.append({
                    "name": getattr(dim_obj, "Name", ""),
                    "subname": first_subname,
                    "kind": "radius",
                    "nominal": dimension_nominal_value(dim_obj),
                    "purpose": str(getattr(dim_obj, "DimensionPurpose", "")),
                    "lower_tolerance": float(getattr(dim_obj, "LowerTolerance", 0.0)),
                    "upper_tolerance": float(getattr(dim_obj, "UpperTolerance", 0.0)),
                    "lower_limit": float(getattr(dim_obj, "LowerLimit", 0.0)),
                    "upper_limit": float(getattr(dim_obj, "UpperLimit", 0.0)),
                })
                FreeCAD.Console.PrintMessage(
                    "Creating semantic radius dimension on {} using AP242 post-write entities\n".format(
                        dimension_export_attachment_text(dim_obj)
                    )
                )
            else:
                FreeCAD.Console.PrintWarning(
                    "Skipping AP242 export for radius dimension on {} because its face could not be mapped.\n".format(
                        dimension_export_attachment_text(dim_obj)
                    )
                )

            continue

        if (
            str(getattr(dim_obj, "AP242Entity", "")) == "DIMENSIONAL_SIZE"
            and dimension_is_plane_to_plane_size(dim_obj)
        ):
            first_subname = dimension_reference_subname(
                export_obj,
                getattr(dim_obj, "ReferenceObject1", None),
                getattr(dim_obj, "ReferenceSubelement1", "")
            )
            second_subname = dimension_reference_subname(
                export_obj,
                getattr(dim_obj, "ReferenceObject2", None),
                getattr(dim_obj, "ReferenceSubelement2", "")
            )

            if first_subname in face_label_map and second_subname in face_label_map:
                pending_size_dimensions.append({
                    "name": getattr(dim_obj, "Name", ""),
                    "subname": first_subname,
                    "second_subname": second_subname,
                    "kind": "thickness",
                    "nominal": dimension_nominal_value(dim_obj),
                    "purpose": str(getattr(dim_obj, "DimensionPurpose", "")),
                    "lower_tolerance": float(getattr(dim_obj, "LowerTolerance", 0.0)),
                    "upper_tolerance": float(getattr(dim_obj, "UpperTolerance", 0.0)),
                    "lower_limit": float(getattr(dim_obj, "LowerLimit", 0.0)),
                    "upper_limit": float(getattr(dim_obj, "UpperLimit", 0.0)),
                })
                FreeCAD.Console.PrintMessage(
                    "Creating semantic linear size dimension on {} using AP242 post-write entities\n".format(
                        dimension_export_attachment_text(dim_obj)
                    )
                )
            else:
                FreeCAD.Console.PrintWarning(
                    "Skipping AP242 linear size dimension on {} because both faces could not be mapped.\n".format(
                        dimension_export_attachment_text(dim_obj)
                    )
                )

            continue

        if dimension_type is None:
            if dimension_is_angular(dim_obj):
                first_subname = dimension_reference_subname(
                    export_obj,
                    getattr(dim_obj, "ReferenceObject1", None),
                    getattr(dim_obj, "ReferenceSubelement1", "")
                )
                second_subname = dimension_reference_subname(
                    export_obj,
                    getattr(dim_obj, "ReferenceObject2", None),
                    getattr(dim_obj, "ReferenceSubelement2", "")
                )

                if first_subname in face_label_map and second_subname in face_label_map:
                    angular_entity = str(
                        getattr(dim_obj, "AP242Entity", "")
                    )

                    if angular_entity not in ("ANGULAR_SIZE", "ANGULAR_LOCATION"):
                        angular_entity = "ANGULAR_LOCATION"

                    pending_angular_dimensions.append({
                        "name": getattr(dim_obj, "Name", ""),
                        "first_subname": first_subname,
                        "second_subname": second_subname,
                        "entity": angular_entity,
                        "nominal": dimension_nominal_value(dim_obj),
                        "purpose": str(getattr(dim_obj, "DimensionPurpose", "")),
                        "lower_tolerance": float(getattr(dim_obj, "LowerTolerance", 0.0)),
                        "upper_tolerance": float(getattr(dim_obj, "UpperTolerance", 0.0)),
                        "lower_limit": float(getattr(dim_obj, "LowerLimit", 0.0)),
                        "upper_limit": float(getattr(dim_obj, "UpperLimit", 0.0)),
                    })
                    FreeCAD.Console.PrintMessage(
                        "Creating semantic angular dimension on {} using AP242 post-write entities\n".format(
                            dimension_export_attachment_text(dim_obj)
                        )
                    )
                    continue

                FreeCAD.Console.PrintWarning(
                    "Skipping AP242 export for angular dimension on {} because both references must map to exported faces.\n".format(
                        dimension_export_attachment_text(dim_obj)
                    )
                )
                continue

            if dimension_is_linear_location(dim_obj):
                first_subname = dimension_reference_subname(
                    export_obj,
                    getattr(dim_obj, "ReferenceObject1", None),
                    getattr(dim_obj, "ReferenceSubelement1", "")
                )
                second_subname = dimension_reference_subname(
                    export_obj,
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
            export_obj,
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
                export_obj,
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

    return pending_location_dimensions, pending_size_dimensions, pending_angular_dimensions


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


def step_escape(value):
    return str(value).replace("\\", "\\\\").replace("'", "''")


def step_number(value, default=0.0):
    try:
        number = float(value)
    except Exception:
        number = float(default)

    if abs(number) < 1e-12:
        number = 0.0

    return "{:.12g}".format(number)


def step_vector_text(vector):
    try:
        values = [float(vector.x), float(vector.y), float(vector.z)]
    except Exception:
        values = [0.0, 0.0, 0.0]

    return ",".join(step_number(value) for value in values)


def insert_step_lines_before_endsec(text, lines):
    if not lines:
        return text

    marker = "ENDSEC;"
    index = text.rfind(marker)

    if index < 0:
        return text + "\n" + "\n".join(lines) + "\n"

    return text[:index] + "\n".join(lines) + "\n" + text[index:]


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
        matches = re.findall(
            r"#(\d+)\s*=\s*SHAPE_REPRESENTATION\("
            r".*?\),#(\d+)\);",
            text,
            re.DOTALL
        )

        if not matches:
            return None, None

        representation_id, context_id = matches[-1]
        return int(representation_id), int(context_id)

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


def find_step_plane_angle_unit(text, context_id=None):
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
                    r"#{}\s*=\s*\([^;]*?PLANE_ANGLE_UNIT\(\)".format(unit_id),
                    text,
                    re.DOTALL
                ):
                    return unit_id

    match = re.search(
        r"#(\d+)\s*=\s*\([^;]*?PLANE_ANGLE_UNIT\(\)",
        text,
        re.DOTALL
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


def step_edge_curve_map(text):
    edge_ids = re.findall(
        r"#(\d+)\s*=\s*EDGE_CURVE\(",
        text
    )

    return {
        "Edge{}".format(index): int(entity_id)
        for index, entity_id in enumerate(edge_ids, start=1)
    }


def step_datum_ids_by_label(text):
    datum_ids = {}

    for entity_id, body in step_entities(text):
        if "DATUM(" not in body:
            continue

        match = re.search(
            r"DATUM\('[^']*','[^']*',#\d+,\.[TF]\.,'([^']+)'\)",
            body,
            re.DOTALL
        )

        if not match:
            continue

        datum_ids[match.group(1)] = entity_id

    return datum_ids


def step_semantic_entity_for_placeholder(text, placeholder):
    pmi_type = placeholder.get("type", "")

    if pmi_type == "Datum":
        return step_datum_ids_by_label(text).get(placeholder.get("datum_label", ""))

    if pmi_type == "FCF":
        subname = placeholder.get("subname", "")
        tolerance_entity = STEP_GEOMTOL_ENTITY_BY_FCF_TYPE.get(
            placeholder.get("tolerance_type", "")
        )

        if not subname or tolerance_entity is None:
            return None

        face_map = step_advanced_face_map(text)
        edge_map = step_edge_curve_map(text)
        item_id = face_map.get(subname) or edge_map.get(subname)

        if item_id is None:
            return None

        tolerance_ids = step_tolerances_for_face(text, item_id, tolerance_entity)

        if not tolerance_ids:
            return None

        return tolerance_ids[0]

    return None


def step_entities(text):
    return [
        (entity_id, body)
        for entity_id, body, _start, _end in step_entity_spans(text)
    ]


def step_entity_spans(text):
    return [
        (int(match.group(1)), match.group(2), match.start(2), match.end(2))
        for match in re.finditer(
            r"#(\d+)\s*=\s*(.*?);",
            text,
            re.DOTALL
        )
    ]


def step_shape_aspects_for_item(text, item_id):
    aspects = set()

    for _entity_id, body in step_entities(text):
        if "GEOMETRIC_ITEM_SPECIFIC_USAGE" not in body:
            continue

        match = re.search(
            r"GEOMETRIC_ITEM_SPECIFIC_USAGE\('[^']*','[^']*',#(\d+),#\d+,#{}\)".format(
                item_id
            ),
            body,
            re.DOTALL
        )

        if match:
            aspects.add(int(match.group(1)))

    return aspects


def step_shape_aspects_for_face(text, face_id):
    return step_shape_aspects_for_item(text, face_id)


def step_geometric_tolerance_aspect(text, tolerance_id):
    for entity_id, body in step_entities(text):
        if entity_id != tolerance_id:
            continue

        match = re.search(
            r"GEOMETRIC_TOLERANCE\('[^']*','[^']*',#\d+,#(\d+)\)",
            body,
            re.DOTALL
        )

        if match:
            return int(match.group(1))

        match = re.search(
            r"[A-Z_]+_TOLERANCE\('[^']*','[^']*',#\d+,#(\d+)\)",
            body,
            re.DOTALL
        )

        if match:
            return int(match.group(1))

    return None


def step_position_tolerance_zones_for_face(text, face_id):
    # OCCT writes the base position tolerance and its tolerance zone before our
    # post-write projected-zone pass. Match them through the controlled
    # GEOMETRIC_ITEM_SPECIFIC_USAGE shape aspect rather than relying on labels.
    controlled_aspects = step_shape_aspects_for_face(text, face_id)

    if not controlled_aspects:
        return []

    tolerance_ids = set()

    for entity_id, body in step_entities(text):
        if "POSITION_TOLERANCE" not in body:
            continue

        match = re.search(
            r"GEOMETRIC_TOLERANCE\('[^']*','[^']*',#\d+,#(\d+)\)",
            body,
            re.DOTALL
        )

        if match and int(match.group(1)) in controlled_aspects:
            tolerance_ids.add(entity_id)

    zone_ids = []

    for entity_id, body in step_entities(text):
        if "TOLERANCE_ZONE" not in body:
            continue

        for tolerance_id in tolerance_ids:
            if re.search(r"\(#{}\)".format(tolerance_id), body):
                zone_ids.append(entity_id)
                break

    return zone_ids


def step_tolerances_for_face(text, face_id, tolerance_entity):
    controlled_aspects = step_shape_aspects_for_face(text, face_id)

    if not controlled_aspects:
        return []

    tolerance_ids = []

    for entity_id, body in step_entities(text):
        if tolerance_entity not in body:
            continue

        match = re.search(
            r"GEOMETRIC_TOLERANCE\('[^']*','[^']*',#\d+,#(\d+)\)",
            body,
            re.DOTALL
        )

        if match and int(match.group(1)) in controlled_aspects:
            tolerance_ids.append(entity_id)
            continue

        simple_match = re.search(
            r"{}\('[^']*','[^']*',#\d+,#(\d+)\)".format(
                tolerance_entity
            ),
            body,
            re.DOTALL
        )

        if simple_match and int(simple_match.group(1)) in controlled_aspects:
            tolerance_ids.append(entity_id)

    return tolerance_ids


def step_profile_tolerances_for_face(text, face_id, tolerance_entity):
    return step_tolerances_for_face(text, face_id, tolerance_entity)


def geometric_tolerance_with_extra_subtypes(body, tolerance_entity, subtypes):
    if not subtypes:
        return None

    if all(subtype.split("(", 1)[0] in body for subtype in subtypes):
        return None

    stripped_body = body.lstrip()

    if stripped_body.startswith("("):
        close_index = body.rfind(")")

        if close_index < 0:
            return None

        insertion = "\n" + "\n".join(subtypes) + " "
        return body[:close_index].rstrip() + insertion + body[close_index:]

    match = re.match(
        r"({})\('([^']*)','([^']*)',#(\d+),#(\d+)\)".format(
            tolerance_entity
        ),
        stripped_body,
        re.DOTALL
    )

    if not match:
        return None

    _entity, name, description, magnitude_id, aspect_id = match.groups()

    # AP242 advanced tolerance options are subtypes of GEOMETRIC_TOLERANCE.
    # When OCCT emits a simple tolerance entity, convert it to the matching
    # complex entity and append the additional AP242 subtype records.
    return (
        "( GEOMETRIC_TOLERANCE('{}','{}',#{},#{}) \n"
        "{} \n"
        "{}() )"
    ).format(
        name,
        description,
        magnitude_id,
        aspect_id,
        "\n".join(subtypes),
        tolerance_entity
    )


def step_tolerance_zones_for_tolerance(text, tolerance_id):
    zone_ids = []

    for entity_id, body in step_entities(text):
        if "TOLERANCE_ZONE" not in body:
            continue

        if re.search(r"\(#{}\)".format(tolerance_id), body):
            zone_ids.append(entity_id)

    return zone_ids


def step_tolerances_with_entity(text, tolerance_entity):
    return [
        entity_id
        for entity_id, body in step_entities(text)
        if tolerance_entity in body
    ]


def profile_tolerance_with_unequal_disposition(body, displacement_id):
    if "UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE" in body:
        return None

    stripped_body = body.lstrip()

    if stripped_body.startswith("("):
        close_index = body.rfind(")")

        if close_index < 0:
            return None

        return (
            body[:close_index].rstrip()
            + "\nUNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE(#{}) ".format(
                displacement_id
            )
            + body[close_index:]
        )

    match = re.match(
        r"(SURFACE_PROFILE_TOLERANCE|LINE_PROFILE_TOLERANCE)\('([^']*)','([^']*)',#(\d+),#(\d+)\)",
        stripped_body,
        re.DOTALL
    )

    if not match:
        return None

    tolerance_entity, name, description, magnitude_id, aspect_id = match.groups()

    # OCCT sometimes writes profile tolerances as simple entities. AP242
    # represents unequal disposition as another subtype of geometric tolerance,
    # so convert the simple profile record to the equivalent complex entity.
    return (
        "( GEOMETRIC_TOLERANCE('{}','{}',#{},#{}) \n"
        "{}() \n"
        "UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE(#{}) )"
    ).format(
        name,
        description,
        magnitude_id,
        aspect_id,
        tolerance_entity,
        displacement_id
    )


def step_float(value):
    text = "{:.12g}".format(float(value))

    if "e" not in text.lower() and "." not in text:
        text += "."

    return text


def location_dimension_measure_items(location_dim, unit_id, first_id):
    return dimension_measure_items(location_dim, unit_id, first_id)


def dimension_measure_items(dimension_data, unit_id, first_id):
    purpose = dimension_data["purpose"]
    entity_id = first_id
    item_ids = []
    lines = []

    if purpose == "Limits":
        values = [
            ("nominal value", dimension_data["nominal"]),
            ("lower limit", dimension_data["lower_limit"]),
            ("upper limit", dimension_data["upper_limit"]),
        ]
    else:
        values = [
            ("nominal value", dimension_data["nominal"]),
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


def angular_dimension_measure_items(dimension_data, unit_id, first_id):
    purpose = dimension_data["purpose"]
    entity_id = first_id
    item_ids = []
    lines = []

    if purpose == "Limits":
        values = [
            ("nominal angle", dimension_data["nominal"]),
            ("lower limit", dimension_data["lower_limit"]),
            ("upper limit", dimension_data["upper_limit"]),
        ]
    else:
        values = [
            ("nominal angle", dimension_data["nominal"]),
        ]

    for label, value in values:
        item_ids.append(entity_id)
        lines.append(
            "#{} = ( MEASURE_REPRESENTATION_ITEM() MEASURE_WITH_UNIT("
            "PLANE_ANGLE_MEASURE({}),#{}) REPRESENTATION_ITEM('{}') );".format(
                entity_id,
                step_float(math.radians(float(value))),
                unit_id,
                label
            )
        )
        entity_id += 1

    return item_ids, lines, entity_id


def append_step_dimensional_sizes(filepath, size_dimensions):
    if not size_dimensions:
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
            "Skipping AP242 size dimensions because STEP context entities could not be identified.\n"
        )
        return

    for size_dim in size_dimensions:
        subnames = [size_dim["subname"]]

        if size_dim.get("second_subname"):
            subnames.append(size_dim["second_subname"])

        face_ids = [
            face_map.get(subname)
            for subname in subnames
        ]

        if any(face_id is None for face_id in face_ids):
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 size dimension {} because a face entity could not be mapped.\n".format(
                    size_dim["name"]
                )
            )
            continue

        aspect_id = next_id
        gisu_ids = list(range(next_id + 1, next_id + 1 + len(face_ids)))
        next_id += 1 + len(face_ids)

        lines.append(
            "#{} = SHAPE_ASPECT('','',#{},.T.);".format(
                aspect_id,
                product_shape_id
            )
        )

        for gisu_id, face_id in zip(gisu_ids, face_ids):
            lines.append(
                "#{} = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#{},#{},#{});".format(
                    gisu_id,
                    aspect_id,
                    shape_rep_id,
                    face_id
                )
            )

        item_ids, item_lines, next_id = dimension_measure_items(
            size_dim,
            unit_id,
            next_id
        )
        lines.extend(item_lines)

        shape_dimension_id = next_id
        characteristic_rep_id = next_id + 1
        size_id = next_id + 2
        next_id += 3

        lines.extend([
            "#{} = SHAPE_DIMENSION_REPRESENTATION('',({}),#{});".format(
                shape_dimension_id,
                ",".join("#{}".format(item_id) for item_id in item_ids),
                context_id
            ),
            "#{} = DIMENSIONAL_CHARACTERISTIC_REPRESENTATION(#{},#{});".format(
                characteristic_rep_id,
                size_id,
                shape_dimension_id
            ),
            "#{} = DIMENSIONAL_SIZE(#{},'{}');".format(
                size_id,
                aspect_id,
                size_dim["kind"]
            ),
        ])

        tolerances = dimension_tolerance_values_from_export_data(size_dim)

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
                    size_id
                ),
            ])

        exported_count += 1

    if not lines:
        return

    insertion = "\n".join(lines) + "\n"
    insertion_index = text.rfind("ENDSEC;")

    if insertion_index < 0:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 size dimensions because ENDSEC was not found.\n"
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
        "Added {} AP242 dimensional size entities after STEP write.\n".format(
            exported_count
        )
    )


def append_step_dimensional_locations(filepath, location_dimensions):
    if not location_dimensions:
        return

    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    product_shape_id = find_step_product_definition_shape(text)
    shape_rep_id, context_id = find_step_shape_representation(text)
    unit_id = find_step_length_unit(text, context_id)
    face_map = step_advanced_face_map(text)
    datum_ids_by_label = step_datum_ids_by_label(text)
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


def append_step_angular_dimensions(filepath, angular_dimensions):
    if not angular_dimensions:
        return

    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    product_shape_id = find_step_product_definition_shape(text)
    shape_rep_id, context_id = find_step_shape_representation(text)
    unit_id = find_step_plane_angle_unit(text, context_id)
    face_map = step_advanced_face_map(text)
    next_id = next_step_entity_id(text)
    lines = []
    exported_count = 0

    if product_shape_id is None or shape_rep_id is None or context_id is None or unit_id is None:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 angular dimensions because STEP context entities could not be identified.\n"
        )
        return

    for angular_dim in angular_dimensions:
        first_face_id = face_map.get(angular_dim["first_subname"])
        second_face_id = face_map.get(angular_dim["second_subname"])

        if first_face_id is None or second_face_id is None:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 angular dimension {} because a face entity could not be mapped.\n".format(
                    angular_dim["name"]
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

        item_ids, item_lines, next_id = angular_dimension_measure_items(
            angular_dim,
            unit_id,
            next_id
        )
        lines.extend(item_lines)

        shape_dimension_id = next_id
        characteristic_rep_id = next_id + 1
        angular_id = next_id + 2
        next_id += 3

        angular_entity = angular_dim.get("entity", "ANGULAR_LOCATION")

        if angular_entity == "ANGULAR_SIZE":
            characteristic_line = "#{} = ANGULAR_SIZE(#{},'angle');".format(
                angular_id,
                first_aspect_id
            )
        else:
            characteristic_line = "#{} = ANGULAR_LOCATION('angular distance',$,#{},#{});".format(
                angular_id,
                first_aspect_id,
                second_aspect_id
            )

        lines.extend([
            "#{} = SHAPE_DIMENSION_REPRESENTATION('',({}),#{});".format(
                shape_dimension_id,
                ",".join("#{}".format(item_id) for item_id in item_ids),
                context_id
            ),
            "#{} = DIMENSIONAL_CHARACTERISTIC_REPRESENTATION(#{},#{});".format(
                characteristic_rep_id,
                angular_id,
                shape_dimension_id
            ),
            characteristic_line,
        ])

        tolerances = dimension_tolerance_values_from_export_data(angular_dim)

        if tolerances:
            lower_tol, upper_tol = tolerances
            upper_measure_id = next_id
            lower_measure_id = next_id + 1
            tolerance_value_id = next_id + 2
            plus_minus_id = next_id + 3
            next_id += 4
            lines.extend([
                "#{} = MEASURE_WITH_UNIT(PLANE_ANGLE_MEASURE({}),#{});".format(
                    upper_measure_id,
                    step_float(math.radians(upper_tol)),
                    unit_id
                ),
                "#{} = MEASURE_WITH_UNIT(PLANE_ANGLE_MEASURE({}),#{});".format(
                    lower_measure_id,
                    step_float(math.radians(-lower_tol)),
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
                    angular_id
                ),
            ])

        exported_count += 1

    if not lines:
        return

    insertion = "\n".join(lines) + "\n"
    insertion_index = text.rfind("ENDSEC;")

    if insertion_index < 0:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 angular dimensions because ENDSEC was not found.\n"
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
        "Added {} AP242 angular dimension entities after STEP write.\n".format(
            exported_count
        )
    )


def append_step_simple_geometric_tolerances(filepath, tolerances):
    if not tolerances:
        return

    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    product_shape_id = find_step_product_definition_shape(text)
    shape_rep_id, context_id = find_step_shape_representation(text)
    unit_id = find_step_length_unit(text, context_id)
    angle_unit_id = find_step_plane_angle_unit(text, context_id)
    face_map = step_advanced_face_map(text)
    datum_ids_by_label = step_datum_ids_by_label(text)
    next_id = next_step_entity_id(text)
    lines = []
    exported_count = 0

    if product_shape_id is None or shape_rep_id is None or unit_id is None:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 imported FCF export because STEP context entities could not be identified.\n"
        )
        return

    for tolerance in tolerances:
        tolerance_entity = STEP_GEOMTOL_ENTITY_BY_FCF_TYPE.get(
            tolerance["tolerance_type"]
        )
        subnames = tolerance.get("subnames") or [tolerance.get("subname", "")]
        face_ids = [
            face_map.get(subname)
            for subname in subnames
            if str(subname).startswith("Face")
        ]

        if (
            tolerance_entity is None
            or not face_ids
            or any(face_id is None for face_id in face_ids)
        ):
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 imported FCF {} because its face or tolerance type could not be mapped.\n".format(
                    tolerance["name"]
                )
            )
            continue

        tolerance_lines = []
        aspect_id = next_id
        magnitude_id = next_id + 1 + len(face_ids)
        next_id += 2 + len(face_ids)

        tolerance_lines.extend([
            "#{} = SHAPE_ASPECT('','',#{},.T.);".format(
                aspect_id,
                product_shape_id
            ),
            "#{} = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE({}),#{});".format(
                magnitude_id,
                step_float(tolerance["tolerance_value"]),
                unit_id
            ),
        ])
        tolerance_lines[1:1] = [
            "#{} = GEOMETRIC_ITEM_SPECIFIC_USAGE('','',#{},#{},#{});".format(
                aspect_id + index,
                aspect_id,
                shape_rep_id,
                face_id
            )
            for index, face_id in enumerate(face_ids, start=1)
        ]

        datum_system_id = None
        datum_compartments = tolerance.get("datum_compartments", [])

        if datum_compartments:
            compartment_ids = []

            for compartment in datum_compartments:
                compartment_datum_ids = []

                for datum_label in compartment:
                    datum_id = datum_ids_by_label.get(datum_label)

                    if datum_id is None:
                        FreeCAD.Console.PrintWarning(
                            "Skipping AP242 datum reference {} for imported FCF {} because its exported DATUM entity could not be found.\n".format(
                                datum_label,
                                tolerance["name"]
                            )
                        )
                        compartment_datum_ids = []
                        break

                    compartment_datum_ids.append(datum_id)

                if not compartment_datum_ids:
                    compartment_ids = []
                    break

                if len(compartment_datum_ids) == 1:
                    datum_reference_value = "#{}".format(
                        compartment_datum_ids[0]
                    )
                else:
                    datum_reference_element_ids = []

                    for datum_id in compartment_datum_ids:
                        datum_reference_element_id = next_id
                        next_id += 1
                        datum_reference_element_ids.append(
                            datum_reference_element_id
                        )
                        tolerance_lines.append(
                            "#{} = DATUM_REFERENCE_ELEMENT('','',#{},.F.,#{},$);".format(
                                datum_reference_element_id,
                                product_shape_id,
                                datum_id
                            )
                        )

                    datum_reference_value = "COMMON_DATUM_LIST({})".format(
                        ",".join(
                            "#{}".format(datum_reference_element_id)
                            for datum_reference_element_id
                            in datum_reference_element_ids
                        )
                    )

                compartment_id = next_id
                next_id += 1
                compartment_ids.append(compartment_id)
                tolerance_lines.append(
                    "#{} = DATUM_REFERENCE_COMPARTMENT('',$,#{},.F.,{},$);".format(
                        compartment_id,
                        product_shape_id,
                        datum_reference_value
                    )
                )

            if not compartment_ids:
                continue

            datum_system_id = next_id
            next_id += 1
            tolerance_lines.append(
                "#{} = DATUM_SYSTEM('Imported datum system for {}',$,#{},.F.,({}));".format(
                    datum_system_id,
                    tolerance["name"],
                    product_shape_id,
                    ",".join("#{}".format(compartment_id)
                             for compartment_id in compartment_ids)
                )
            )

        modifier_subtypes = []
        material_modifiers = []

        material_condition = tolerance.get("material_condition", "None")

        if material_condition == "MMC":
            material_modifiers.append(".MAXIMUM_MATERIAL_REQUIREMENT.")
        elif material_condition == "LMC":
            material_modifiers.append(".LEAST_MATERIAL_REQUIREMENT.")

        if tolerance.get("tangent_plane"):
            material_modifiers.append(".TANGENT_PLANE.")

        if tolerance.get("statistical_tolerance"):
            material_modifiers.append(".STATISTICAL_TOLERANCE.")

        if tolerance.get("common_zone"):
            material_modifiers.append(".COMMON_ZONE.")

        if material_modifiers:
            modifier_subtypes.append(
                "GEOMETRIC_TOLERANCE_WITH_MODIFIERS(({}))".format(
                    ",".join(material_modifiers)
                )
            )

        if (
            tolerance.get("maximum_enabled")
            and tolerance.get("maximum_value", 0.0) > 0.0
        ):
            maximum_id = next_id
            next_id += 1
            tolerance_lines.append(
                "#{} = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE({}),#{});".format(
                    maximum_id,
                    step_float(tolerance["maximum_value"]),
                    unit_id
                )
            )
            modifier_subtypes.append(
                "GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE(#{})".format(
                    maximum_id
                )
            )

        if (
            tolerance.get("unit_basis_enabled")
            and tolerance.get("unit_basis_primary", 0.0) > 0.0
        ):
            primary_id = next_id
            next_id += 1
            tolerance_lines.append(
                "#{} = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE({}),#{});".format(
                    primary_id,
                    step_float(tolerance["unit_basis_primary"]),
                    unit_id
                )
            )
            modifier_subtypes.append(
                "GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT(#{})".format(
                    primary_id
                )
            )
            area_type_map = {
                "Circular": ".CIRCULAR.",
                "Rectangular": ".RECTANGULAR.",
                "Square": ".SQUARE.",
            }
            area_type = area_type_map.get(tolerance.get("unit_basis_type"))

            if area_type is not None:
                secondary = tolerance.get("unit_basis_secondary", 0.0)

                if tolerance.get("unit_basis_type") in ("Circular", "Square"):
                    secondary = tolerance["unit_basis_primary"]

                if secondary > 0.0:
                    secondary_id = next_id
                    next_id += 1
                    tolerance_lines.append(
                        "#{} = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE({}),#{});".format(
                            secondary_id,
                            step_float(secondary),
                            unit_id
                        )
                    )
                    modifier_subtypes.append(
                        "GEOMETRIC_TOLERANCE_WITH_DEFINED_AREA_UNIT({},#{})".format(
                            area_type,
                            secondary_id
                        )
                    )

        if (
            tolerance.get("unequally_disposed")
            and tolerance.get("unequal_offset", 0.0) > 0.0
            and tolerance["tolerance_type"] in ("Profile", "LineProfile")
        ):
            unequal_id = next_id
            next_id += 1
            tolerance_lines.append(
                "#{} = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE({}),#{});".format(
                    unequal_id,
                    step_float(tolerance["unequal_offset"]),
                    unit_id
                )
            )
            modifier_subtypes.append(
                "UNEQUALLY_DISPOSED_GEOMETRIC_TOLERANCE(#{})".format(
                    unequal_id
                )
            )

        tolerance_id = next_id
        next_id += 1

        if datum_system_id is None and not modifier_subtypes:
            tolerance_lines.append(
                "#{} = {}('','',#{},#{});".format(
                    tolerance_id,
                    tolerance_entity,
                    magnitude_id,
                    aspect_id
                )
            )
        else:
            subtype_lines = list(modifier_subtypes)

            if datum_system_id is not None:
                subtype_lines.insert(
                    0,
                    "GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE((#{}))".format(
                        datum_system_id
                    )
                )

            tolerance_lines.append(
                "#{} = ( GEOMETRIC_TOLERANCE('','',#{},#{}) \n"
                "{} \n"
                "{}() );".format(
                    tolerance_id,
                    magnitude_id,
                    aspect_id,
                    "\n".join(subtype_lines),
                    tolerance_entity
                )
            )
        zone_id = None

        if tolerance["tolerance_type"] == "Position":
            zone_form_id = next_id
            zone_id = next_id + 1
            next_id += 2
            tolerance_lines.extend([
                "#{} = TOLERANCE_ZONE_FORM('cylindrical or circular');".format(
                    zone_form_id
                ),
                "#{} = TOLERANCE_ZONE('','',#{},.F.,(#{}),#{});".format(
                    zone_id,
                    product_shape_id,
                    tolerance_id,
                    zone_form_id
                ),
            ])
        if tolerance["tolerance_type"] in ("CircularRunout", "TotalRunout"):
            zone_form_id = next_id
            zone_id = next_id + 1
            runout_definition_id = next_id + 2
            next_id += 3
            tolerance_lines.extend([
                "#{} = TOLERANCE_ZONE_FORM('cylindrical or circular');".format(
                    zone_form_id
                ),
                "#{} = TOLERANCE_ZONE('','',#{},.F.,(#{}),#{});".format(
                    zone_id,
                    product_shape_id,
                    tolerance_id,
                    zone_form_id
                ),
                "#{} = RUNOUT_ZONE_DEFINITION(#{},());".format(
                    runout_definition_id,
                    zone_id
                ),
            ])

            if angle_unit_id is not None:
                angle_id = next_id
                orientation_id = next_id + 1
                next_id += 2
                tolerance_lines.extend([
                    "#{} = RUNOUT_ZONE_ORIENTATION(#{});".format(
                        orientation_id,
                        angle_id
                    ),
                    "#{} = PLANE_ANGLE_MEASURE_WITH_UNIT(PLANE_ANGLE_MEASURE({}),#{});".format(
                        angle_id,
                        step_float(math.radians(tolerance.get(
                            "runout_orientation_angle",
                            0.0
                        ))),
                        angle_unit_id
                    ),
                ])
        if (
            tolerance.get("projected_zone")
            and tolerance.get("projected_height", 0.0) > 0.0
            and tolerance["tolerance_type"] == "Position"
            and zone_id is not None
        ):
            projected_height_id = next_id
            projected_zone_id = next_id + 1
            next_id += 2
            tolerance_lines.extend([
                "#{} = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE({}),#{});".format(
                    projected_height_id,
                    step_float(tolerance["projected_height"]),
                    unit_id
                ),
                "#{} = PROJECTED_ZONE_DEFINITION(#{},(),#{},#{});".format(
                    projected_zone_id,
                    zone_id,
                    aspect_id,
                    projected_height_id
                ),
            ])
        if tolerance.get("non_uniform_zone"):
            non_uniform_form_id = next_id
            non_uniform_zone_id = next_id + 1
            non_uniform_definition_id = next_id + 2
            next_id += 3
            tolerance_lines.extend([
                "#{} = TOLERANCE_ZONE_FORM('non uniform');".format(
                    non_uniform_form_id
                ),
                "#{} = TOLERANCE_ZONE('{}',$,#{},.F.,(#{}),#{});".format(
                    non_uniform_zone_id,
                    tolerance["name"],
                    product_shape_id,
                    tolerance_id,
                    non_uniform_form_id
                ),
                "#{} = NON_UNIFORM_ZONE_DEFINITION(#{});".format(
                    non_uniform_definition_id,
                    non_uniform_zone_id
                ),
            ])
        lines.extend(tolerance_lines)
        exported_count += 1

    if not lines:
        return

    insertion = "\n".join(lines) + "\n"
    insertion_index = text.rfind("ENDSEC;")

    if insertion_index < 0:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 imported FCF export because ENDSEC was not found.\n"
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
        "Added {} AP242 imported FCF tolerance entities after STEP write.\n".format(
            exported_count
        )
    )


def append_step_projected_zone_definitions(filepath, projected_zones):
    if not projected_zones:
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
            "Skipping AP242 projected zone definitions because STEP context entities could not be identified.\n"
        )
        return

    for projected_zone in projected_zones:
        face_id = face_map.get(projected_zone["subname"])

        if face_id is None:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 projected zone definition for {} because its face entity could not be mapped.\n".format(
                    projected_zone["name"]
                )
            )
            continue

        tolerance_zone_ids = step_position_tolerance_zones_for_face(
            text,
            face_id
        )

        if not tolerance_zone_ids:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 projected zone definition for {} because its base tolerance zone could not be found.\n".format(
                    projected_zone["name"]
                )
            )
            continue

        aspect_id = next_id
        gisu_id = next_id + 1
        height_id = next_id + 2
        projected_zone_id = next_id + 3
        next_id += 4

        lines.extend([
            "#{} = SHAPE_ASPECT('projected zone {}','',#{},.T.);".format(
                aspect_id,
                projected_zone["name"],
                product_shape_id
            ),
            "#{} = GEOMETRIC_ITEM_SPECIFIC_USAGE('projected zone {}','',#{},#{},#{});".format(
                gisu_id,
                projected_zone["name"],
                aspect_id,
                shape_rep_id,
                face_id
            ),
            "#{} = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE({}),#{});".format(
                height_id,
                step_float(projected_zone["height"]),
                unit_id
            ),
            "#{} = PROJECTED_ZONE_DEFINITION(#{},(),#{},#{});".format(
                projected_zone_id,
                tolerance_zone_ids[-1],
                aspect_id,
                height_id
            ),
        ])
        exported_count += 1

    if not lines:
        return

    insertion = "\n".join(lines) + "\n"
    insertion_index = text.rfind("ENDSEC;")

    if insertion_index < 0:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 projected zone definitions because ENDSEC was not found.\n"
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
        "Added {} AP242 projected zone definitions after STEP write.\n".format(
            exported_count
        )
    )


def append_step_unequally_disposed_profile_tolerances(filepath, unequal_profiles):
    if not unequal_profiles:
        return

    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    _shape_rep_id, context_id = find_step_shape_representation(text)
    unit_id = find_step_length_unit(text, context_id)
    face_map = step_advanced_face_map(text)
    next_id = next_step_entity_id(text)
    displacement_lines = []
    replacements = []
    exported_count = 0

    if unit_id is None:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 unequal-disposition profile tolerances because the STEP length unit could not be identified.\n"
        )
        return

    line_profile_ids = step_tolerances_with_entity(
        text,
        "LINE_PROFILE_TOLERANCE"
    )

    for unequal_profile in unequal_profiles:
        face_id = face_map.get(unequal_profile["subname"])

        if unequal_profile["tolerance_type"] == "LineProfile":
            if face_id is not None:
                tolerance_ids = step_profile_tolerances_for_face(
                    text,
                    face_id,
                    "LINE_PROFILE_TOLERANCE"
                )
            elif len(line_profile_ids) == 1:
                tolerance_ids = line_profile_ids
            else:
                FreeCAD.Console.PrintWarning(
                    "Skipping AP242 unequal-disposition line profile export for {} because multiple edge-backed line-profile mappings are present and STEP edge numbering is ambiguous.\n".format(
                        unequal_profile["name"]
                    )
                )
                continue
        else:
            if face_id is None:
                FreeCAD.Console.PrintWarning(
                    "Skipping AP242 unequal-disposition profile tolerance for {} because its face entity could not be mapped.\n".format(
                        unequal_profile["name"]
                    )
                )
                continue

            tolerance_ids = step_profile_tolerances_for_face(
                text,
                face_id,
                "SURFACE_PROFILE_TOLERANCE"
            )

        if not tolerance_ids:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 unequal-disposition profile tolerance for {} because its base profile tolerance could not be found.\n".format(
                    unequal_profile["name"]
                )
            )
            continue

        tolerance_id = tolerance_ids[-1]
        for entity_id, body, start, end in step_entity_spans(text):
            if entity_id != tolerance_id:
                continue

            displacement_id = next_id
            replacement_body = profile_tolerance_with_unequal_disposition(
                body,
                displacement_id
            )

            if replacement_body is not None:
                next_id += 1
                displacement_lines.append(
                    "#{} = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE({}),#{});".format(
                        displacement_id,
                        step_float(unequal_profile["offset"]),
                        unit_id
                    )
                )
                replacements.append((start, end, replacement_body))
                exported_count += 1
            break

    if not displacement_lines or not replacements:
        return

    for start, end, replacement_body in sorted(
        replacements,
        key=lambda item: item[0],
        reverse=True
    ):
        text = text[:start] + replacement_body + text[end:]

    insertion = "\n".join(displacement_lines) + "\n"
    insertion_index = text.rfind("ENDSEC;")

    if insertion_index < 0:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 unequal-disposition profile tolerances because ENDSEC was not found.\n"
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
        "Added {} AP242 unequally disposed profile tolerance entities after STEP write.\n".format(
            exported_count
        )
    )


def append_step_maximum_tolerances(filepath, maximum_tolerances):
    if not maximum_tolerances:
        return

    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    _shape_rep_id, context_id = find_step_shape_representation(text)
    unit_id = find_step_length_unit(text, context_id)
    face_map = step_advanced_face_map(text)
    next_id = next_step_entity_id(text)
    measure_lines = []
    replacements = []
    exported_count = 0

    if unit_id is None:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 maximum tolerance values because the STEP length unit could not be identified.\n"
        )
        return

    for maximum_tolerance in maximum_tolerances:
        face_id = face_map.get(maximum_tolerance["subname"])

        if face_id is None:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 maximum tolerance value for {} because its face entity could not be mapped.\n".format(
                    maximum_tolerance["name"]
                )
            )
            continue

        tolerance_ids = step_tolerances_for_face(
            text,
            face_id,
            maximum_tolerance["tolerance_entity"]
        )

        if not tolerance_ids:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 maximum tolerance value for {} because its base tolerance could not be found.\n".format(
                    maximum_tolerance["name"]
                )
            )
            continue

        tolerance_id = tolerance_ids[-1]

        for entity_id, body, start, end in step_entity_spans(text):
            if entity_id != tolerance_id:
                continue

            measure_id = next_id
            replacement_body = geometric_tolerance_with_extra_subtypes(
                body,
                maximum_tolerance["tolerance_entity"],
                [
                    "GEOMETRIC_TOLERANCE_WITH_MAXIMUM_TOLERANCE(#{})".format(
                        measure_id
                    )
                ]
            )

            if replacement_body is not None:
                next_id += 1
                measure_lines.append(
                    "#{} = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE({}),#{});".format(
                        measure_id,
                        step_float(maximum_tolerance["maximum_value"]),
                        unit_id
                    )
                )
                replacements.append((start, end, replacement_body))
                exported_count += 1
            break

    if not measure_lines or not replacements:
        return

    for start, end, replacement_body in sorted(
        replacements,
        key=lambda item: item[0],
        reverse=True
    ):
        text = text[:start] + replacement_body + text[end:]

    insertion = "\n".join(measure_lines) + "\n"
    insertion_index = text.rfind("ENDSEC;")

    if insertion_index < 0:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 maximum tolerance values because ENDSEC was not found.\n"
        )
        return

    text = text[:insertion_index] + insertion + text[insertion_index:]

    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write(text)

    FreeCAD.Console.PrintMessage(
        "Added {} AP242 maximum tolerance value entities after STEP write.\n".format(
            exported_count
        )
    )


def append_step_unit_basis_tolerances(filepath, unit_basis_tolerances):
    if not unit_basis_tolerances:
        return

    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    _shape_rep_id, context_id = find_step_shape_representation(text)
    unit_id = find_step_length_unit(text, context_id)
    face_map = step_advanced_face_map(text)
    next_id = next_step_entity_id(text)
    measure_lines = []
    replacements = []
    exported_count = 0

    if unit_id is None:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 unit-basis tolerances because the STEP length unit could not be identified.\n"
        )
        return

    area_type_map = {
        "Circular": ".CIRCULAR.",
        "Rectangular": ".RECTANGULAR.",
        "Square": ".SQUARE.",
    }

    for unit_basis in unit_basis_tolerances:
        face_id = face_map.get(unit_basis["subname"])

        if face_id is None:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 unit-basis tolerance for {} because its face entity could not be mapped.\n".format(
                    unit_basis["name"]
                )
            )
            continue

        tolerance_ids = step_tolerances_for_face(
            text,
            face_id,
            unit_basis["tolerance_entity"]
        )

        if not tolerance_ids:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 unit-basis tolerance for {} because its base tolerance could not be found.\n".format(
                    unit_basis["name"]
                )
            )
            continue

        tolerance_id = tolerance_ids[-1]

        for entity_id, body, start, end in step_entity_spans(text):
            if entity_id != tolerance_id:
                continue

            primary_id = next_id
            next_id += 1
            measure_lines.append(
                "#{} = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE({}),#{});".format(
                    primary_id,
                    step_float(unit_basis["primary"]),
                    unit_id
                )
            )

            subtypes = [
                "GEOMETRIC_TOLERANCE_WITH_DEFINED_UNIT(#{})".format(
                    primary_id
                )
            ]

            area_type = area_type_map.get(unit_basis["unit_type"])

            if area_type is not None:
                secondary_id = next_id
                next_id += 1
                secondary_value = unit_basis["secondary"]

                if unit_basis["unit_type"] in ("Circular", "Square"):
                    secondary_value = unit_basis["primary"]

                measure_lines.append(
                    "#{} = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE({}),#{});".format(
                        secondary_id,
                        step_float(secondary_value),
                        unit_id
                    )
                )
                subtypes.append(
                    "GEOMETRIC_TOLERANCE_WITH_DEFINED_AREA_UNIT({},#{})".format(
                        area_type,
                        secondary_id
                    )
                )

            replacement_body = geometric_tolerance_with_extra_subtypes(
                body,
                unit_basis["tolerance_entity"],
                subtypes
            )

            if replacement_body is not None:
                replacements.append((start, end, replacement_body))
                exported_count += 1
            else:
                measure_lines = measure_lines[:-(2 if area_type else 1)]
            break

    if not measure_lines or not replacements:
        return

    for start, end, replacement_body in sorted(
        replacements,
        key=lambda item: item[0],
        reverse=True
    ):
        text = text[:start] + replacement_body + text[end:]

    insertion = "\n".join(measure_lines) + "\n"
    insertion_index = text.rfind("ENDSEC;")

    if insertion_index < 0:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 unit-basis tolerances because ENDSEC was not found.\n"
        )
        return

    text = text[:insertion_index] + insertion + text[insertion_index:]

    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write(text)

    FreeCAD.Console.PrintMessage(
        "Added {} AP242 unit-basis tolerance entities after STEP write.\n".format(
            exported_count
        )
    )


def append_step_non_uniform_zone_definitions(filepath, non_uniform_zones):
    if not non_uniform_zones:
        return

    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    product_shape_id = find_step_product_definition_shape(text)
    face_map = step_advanced_face_map(text)
    next_id = next_step_entity_id(text)
    lines = []
    exported_count = 0

    if product_shape_id is None:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 non-uniform zone definitions because the STEP product definition shape could not be identified.\n"
        )
        return

    for non_uniform in non_uniform_zones:
        face_id = face_map.get(non_uniform["subname"])

        if face_id is None:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 non-uniform zone definition for {} because its face entity could not be mapped.\n".format(
                    non_uniform["name"]
                )
            )
            continue

        tolerance_ids = step_tolerances_for_face(
            text,
            face_id,
            non_uniform["tolerance_entity"]
        )

        if not tolerance_ids:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 non-uniform zone definition for {} because its base tolerance could not be found.\n".format(
                    non_uniform["name"]
                )
            )
            continue

        tolerance_id = tolerance_ids[-1]
        zone_ids = step_tolerance_zones_for_tolerance(text, tolerance_id)

        if zone_ids:
            zone_id = zone_ids[-1]
        else:
            form_id = next_id
            zone_id = next_id + 1
            next_id += 2
            lines.extend([
                "#{} = TOLERANCE_ZONE_FORM('non uniform');".format(
                    form_id
                ),
                "#{} = TOLERANCE_ZONE('{}',$,#{},.F.,(#{}),#{});".format(
                    zone_id,
                    non_uniform["name"],
                    product_shape_id,
                    tolerance_id,
                    form_id
                ),
            ])

        definition_id = next_id
        next_id += 1
        lines.append(
            "#{} = NON_UNIFORM_ZONE_DEFINITION(#{});".format(
                definition_id,
                zone_id
            )
        )
        exported_count += 1

    if not lines:
        return

    insertion = "\n".join(lines) + "\n"
    insertion_index = text.rfind("ENDSEC;")

    if insertion_index < 0:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 non-uniform zone definitions because ENDSEC was not found.\n"
        )
        return

    text = text[:insertion_index] + insertion + text[insertion_index:]

    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write(text)

    FreeCAD.Console.PrintMessage(
        "Added {} AP242 non-uniform zone definitions after STEP write.\n".format(
            exported_count
        )
    )


def step_runout_orientation_for_zone(text, zone_id):
    runout_seen = False

    for entity_id, body in step_entities(text):
        if "RUNOUT_ZONE_DEFINITION" in body and re.search(
            r"RUNOUT_ZONE_DEFINITION\(#{},".format(zone_id),
            body
        ):
            runout_seen = True
            continue

        if not runout_seen:
            continue

        match = re.search(
            r"RUNOUT_ZONE_ORIENTATION\(#(\d+)\)",
            body
        )

        if match:
            return entity_id, int(match.group(1))

        if "TOLERANCE_ZONE" in body or "GEOMETRIC_TOLERANCE" in body:
            return None, None

    return None, None


def append_step_runout_orientation_angles(filepath, runout_orientations):
    if not runout_orientations:
        return

    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    _shape_rep_id, context_id = find_step_shape_representation(text)
    unit_id = find_step_plane_angle_unit(text, context_id)
    face_map = step_advanced_face_map(text)
    replacements = []
    exported_count = 0

    if unit_id is None:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 runout orientation angles because the STEP plane-angle unit could not be identified.\n"
        )
        return

    for runout in runout_orientations:
        face_id = face_map.get(runout["subname"])

        if face_id is None:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 runout orientation for {} because its face entity could not be mapped.\n".format(
                    runout["name"]
                )
            )
            continue

        tolerance_ids = step_tolerances_for_face(
            text,
            face_id,
            runout["tolerance_entity"]
        )

        if not tolerance_ids:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 runout orientation for {} because its base runout tolerance could not be found.\n".format(
                    runout["name"]
                )
            )
            continue

        zone_ids = step_tolerance_zones_for_tolerance(
            text,
            tolerance_ids[-1]
        )

        if not zone_ids:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 runout orientation for {} because its runout tolerance zone could not be found.\n".format(
                    runout["name"]
                )
            )
            continue

        _orientation_id, angle_id = step_runout_orientation_for_zone(
            text,
            zone_ids[-1]
        )

        if angle_id is None:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 runout orientation for {} because its RUNOUT_ZONE_ORIENTATION angle could not be found.\n".format(
                    runout["name"]
                )
            )
            continue

        for entity_id, body, start, end in step_entity_spans(text):
            if entity_id != angle_id:
                continue

            replacement_body = (
                "PLANE_ANGLE_MEASURE_WITH_UNIT(PLANE_ANGLE_MEASURE({}),#{})"
            ).format(
                step_float(math.radians(runout["angle_degrees"])),
                unit_id
            )
            replacements.append((start, end, replacement_body))
            exported_count += 1
            break

    if not replacements:
        return

    for start, end, replacement_body in sorted(
        replacements,
        key=lambda item: item[0],
        reverse=True
    ):
        text = text[:start] + replacement_body + text[end:]

    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write(text)

    FreeCAD.Console.PrintMessage(
        "Updated {} AP242 runout orientation angle entities after STEP write.\n".format(
            exported_count
        )
    )


def append_step_affected_plane_associations(filepath, affected_planes):
    if not affected_planes:
        return

    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    product_shape_id = find_step_product_definition_shape(text)
    shape_rep_id, _context_id = find_step_shape_representation(text)
    face_map = step_advanced_face_map(text)
    edge_map = step_edge_curve_map(text)
    next_id = next_step_entity_id(text)
    lines = []
    exported_count = 0

    if product_shape_id is None or shape_rep_id is None:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 affected-plane associations because STEP context entities could not be identified.\n"
        )
        return

    for affected in affected_planes:
        face_id = face_map.get(affected["subname"])
        edge_id = edge_map.get(affected["affected_subname"])

        if face_id is None or edge_id is None:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 affected-plane association for {} because its face or line entity could not be mapped.\n".format(
                    affected["name"]
                )
            )
            continue

        tolerance_ids = step_tolerances_for_face(
            text,
            face_id,
            affected["tolerance_entity"]
        )

        if not tolerance_ids:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 affected-plane association for {} because its base tolerance could not be found.\n".format(
                    affected["name"]
                )
            )
            continue

        tolerance_aspect_id = step_geometric_tolerance_aspect(
            text,
            tolerance_ids[-1]
        )

        if tolerance_aspect_id is None:
            FreeCAD.Console.PrintWarning(
                "Skipping AP242 affected-plane association for {} because its tolerance shape aspect could not be found.\n".format(
                    affected["name"]
                )
            )
            continue

        line_aspect_ids = step_shape_aspects_for_item(text, edge_id)

        if line_aspect_ids:
            line_aspect_id = sorted(line_aspect_ids)[-1]
        else:
            line_aspect_id = next_id
            gisu_id = next_id + 1
            next_id += 2
            lines.extend([
                "#{} = SHAPE_ASPECT('affected plane line','representative plane element',#{},.T.);".format(
                    line_aspect_id,
                    product_shape_id
                ),
                "#{} = GEOMETRIC_ITEM_SPECIFIC_USAGE('affected plane line','',#{},#{},#{});".format(
                    gisu_id,
                    line_aspect_id,
                    shape_rep_id,
                    edge_id
                ),
            ])

        relationship_id = next_id
        next_id += 1
        lines.append(
            "#{} = SHAPE_ASPECT_RELATIONSHIP('affected plane association','affected plane association',#{},#{});".format(
                relationship_id,
                tolerance_aspect_id,
                line_aspect_id
            )
        )
        exported_count += 1

    if not lines:
        return

    insertion = "\n".join(lines) + "\n"
    insertion_index = text.rfind("ENDSEC;")

    if insertion_index < 0:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 affected-plane associations because ENDSEC was not found.\n"
        )
        return

    text = text[:insertion_index] + insertion + text[insertion_index:]

    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write(text)

    FreeCAD.Console.PrintMessage(
        "Added {} AP242 affected-plane associations after STEP write.\n".format(
            exported_count
        )
    )


def append_step_annotation_placeholders(filepath, placeholders):
    if not placeholders:
        return

    with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    _shape_rep_id, context_id = find_step_shape_representation(text)

    if context_id is None:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 annotation placeholders because the STEP representation context could not be identified.\n"
        )
        return

    next_id = next_step_entity_id(text)
    style_id = next_id
    next_id += 1
    lines = [
        "#{} = PRESENTATION_STYLE_ASSIGNMENT((NULL_STYLE(.NULL.)));".format(
            style_id
        )
    ]
    callout_ids = []
    semantic_links = []
    exported_count = 0

    for placeholder in placeholders:
        origin_id = next_id
        layout_set_id = next_id + 1
        placeholder_id = next_id + 2
        callout_id = next_id + 3
        next_id += 4

        name = step_escape(placeholder.get("name", "MBD PMI"))
        layout_description = step_escape(
            "MBD layout object={}; type={}; normal={}; direction={}".format(
                placeholder.get("object_name", ""),
                placeholder.get("type", "PMI"),
                step_vector_text(placeholder.get("normal")),
                step_vector_text(placeholder.get("direction")),
            )
        )
        text_height = step_number(placeholder.get("text_height", 7.0), 7.0)

        lines.extend([
            "#{} = CARTESIAN_POINT('MBD annotation origin',({}));".format(
                origin_id,
                step_vector_text(placeholder.get("origin")),
            ),
            "#{} = GEOMETRIC_SET('{}',(#{}));".format(
                layout_set_id,
                layout_description,
                origin_id,
            ),
            "#{} = ANNOTATION_PLACEHOLDER_OCCURRENCE('{}',(#{}),#{},.GPS_DATA.,{});".format(
                placeholder_id,
                name,
                style_id,
                layout_set_id,
                text_height,
            ),
            "#{} = DRAUGHTING_CALLOUT('{}',(#{}));".format(
                callout_id,
                name,
                placeholder_id,
            ),
        ])
        callout_ids.append(callout_id)

        semantic_id = step_semantic_entity_for_placeholder(text, placeholder)

        if semantic_id is not None:
            semantic_links.append((semantic_id, callout_id, placeholder_id))

        exported_count += 1

    if not callout_ids:
        return

    draughting_model_id = next_id
    next_id += 1
    lines.append(
        "#{} = DRAUGHTING_MODEL('MBD presentation placeholders',({}),#{});".format(
            draughting_model_id,
            ",".join("#{}".format(callout_id) for callout_id in callout_ids),
            context_id,
        )
    )

    for semantic_id, callout_id, placeholder_id in semantic_links:
        association_id = next_id
        next_id += 1
        lines.append(
            "#{} = DRAUGHTING_MODEL_ITEM_ASSOCIATION_WITH_PLACEHOLDER('PMI representation to presentation link','',#{},#{},#{},#{});".format(
                association_id,
                semantic_id,
                draughting_model_id,
                callout_id,
                placeholder_id,
            )
        )

    text = insert_step_lines_before_endsec(text, lines)

    if text is None:
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 annotation placeholders because ENDSEC was not found.\n"
        )
        return

    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write(text)

    FreeCAD.Console.PrintMessage(
        "Added {} AP242 annotation placeholder occurrences after STEP write ({} semantic links).\n".format(
            exported_count,
            len(semantic_links)
        )
    )


def dimension_tolerance_values_from_export_data(location_dim):
    if location_dim["purpose"] not in ("UnequalBilateral", "EqualBilateral"):
        return None

    return (
        abs(location_dim["lower_tolerance"]),
        abs(location_dim["upper_tolerance"]),
    )


def step_file_has_null_references(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except Exception:
        return False

    return "/*   NUL REF   */" in text


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

    if step_file_has_null_references(filepath):
        raise Exception(
            "STEP write produced null semantic references. "
            "One or more PMI attachments could not be mapped to the exported shape."
        )

    if status != IFSelect_RetDone:
        raise Exception("STEP write failed with status {}.".format(int(status)))


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
    pending_size_dimensions = []
    pending_angular_dimensions = []
    pending_projected_zones = []
    pending_unequal_profiles = []
    pending_maximum_tolerances = []
    pending_unit_basis_tolerances = []
    pending_non_uniform_zones = []
    pending_affected_planes = []
    pending_runout_orientations = []
    pending_simple_imported_fcfs = []

    for obj in exportable_shape_objects(doc):
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

        (
            projected_zones,
            unequal_profiles,
            maximum_tolerances,
            unit_basis_tolerances,
            non_uniform_zones,
            affected_planes,
            runout_orientations,
            simple_imported_fcfs,
        ) = export_feature_control_frames(
            doc,
            dimtol_tool,
            face_label_map,
            subshape_label_map
        )
        pending_projected_zones.extend(projected_zones)
        pending_unequal_profiles.extend(unequal_profiles)
        pending_maximum_tolerances.extend(maximum_tolerances)
        pending_unit_basis_tolerances.extend(unit_basis_tolerances)
        pending_non_uniform_zones.extend(non_uniform_zones)
        pending_affected_planes.extend(affected_planes)
        pending_runout_orientations.extend(runout_orientations)
        pending_simple_imported_fcfs.extend(simple_imported_fcfs)

        location_dimensions, size_dimensions, angular_dimensions = export_dimensions(
            doc,
            dimtol_tool,
            face_label_map,
            obj
        )
        pending_location_dimensions.extend(location_dimensions)
        pending_size_dimensions.extend(size_dimensions)
        pending_angular_dimensions.extend(angular_dimensions)

        exported_count += 1

    pending_annotation_placeholders = [
        pmi_presentation_placeholder_data(pmi_obj)
        for pmi_obj in iter_presentation_placeholder_pmi(doc)
    ]

    transfer_and_write_step(
        xcaf_doc,
        dimtol_tool,
        filepath
    )

    if exported_count == 1:
        # The post-write entity pass references face IDs from the single STEP
        # product shape. It is intentionally disabled for multi-shape exports
        # until we have unambiguous per-shape reference mapping.
        append_step_dimensional_sizes(
            filepath,
            pending_size_dimensions
        )
        append_step_dimensional_locations(
            filepath,
            pending_location_dimensions
        )
        append_step_angular_dimensions(
            filepath,
            pending_angular_dimensions
        )
        append_step_simple_geometric_tolerances(
            filepath,
            pending_simple_imported_fcfs
        )
        append_step_projected_zone_definitions(
            filepath,
            pending_projected_zones
        )
        append_step_unequally_disposed_profile_tolerances(
            filepath,
            pending_unequal_profiles
        )
        append_step_maximum_tolerances(
            filepath,
            pending_maximum_tolerances
        )
        append_step_unit_basis_tolerances(
            filepath,
            pending_unit_basis_tolerances
        )
        append_step_non_uniform_zone_definitions(
            filepath,
            pending_non_uniform_zones
        )
        append_step_runout_orientation_angles(
            filepath,
            pending_runout_orientations
        )
        append_step_affected_plane_associations(
            filepath,
            pending_affected_planes
        )
        append_step_annotation_placeholders(
            filepath,
            pending_annotation_placeholders
        )
    elif (
        pending_location_dimensions
        or pending_size_dimensions
        or pending_angular_dimensions
        or pending_projected_zones
        or pending_unequal_profiles
        or pending_maximum_tolerances
        or pending_unit_basis_tolerances
        or pending_non_uniform_zones
        or pending_affected_planes
        or pending_runout_orientations
        or pending_simple_imported_fcfs
        or pending_annotation_placeholders
    ):
        FreeCAD.Console.PrintWarning(
            "Skipping AP242 post-write PMI entities because multiple export shapes were written.\n"
        )

    FreeCAD.Console.PrintMessage(
        "Exported {} shapes to {}\n".format(
            exported_count,
            filepath
        )
    )

    return True
