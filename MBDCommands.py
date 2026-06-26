# MBDCommands.py

import math
import os
import time

import FreeCAD
import FreeCADGui
import Part
from PySide import QtGui

from MBDBasicDimension import (
    MBDBasicDimension,
    ViewProviderMBDBasicDimension,
    point_from_reference,
    reference_point_for_display,
    measured_value_from_references,
    display_points_from_references,
    surface_from_datum_reference,
    measured_dimension_value,
    update_basic_dimension_signature
)
from MBDDimension import (
    MBDDimension,
    ViewProviderMBDDimension,
    DIMENSION_PURPOSES,
    DIMENSION_PURPOSE_CHOICES,
    cylindrical_face_reference,
    dimension_display_label,
    measurement_from_references,
    nearest_point_on_shape,
    update_dimension_signature
)
from MBDDatum import MBDDatumFeature, ViewProviderMBDDatumFeature
import MBDValidation
from MBDDatum import (
    MBDDatumFeature,
    ViewProviderMBDDatumFeature,
    update_geometry_signature
)
import MBDInspector
from MBDPMI import append_pmi_history, update_pmi_display_layout
from MBDDatumTarget import (
    MBDDatumTarget,
    ViewProviderMBDDatumTarget,
    straight_edge_geometry,
    target_surface_distance,
    update_datum_target_signature
)
from MBDDatumSystem import (
    DATUM_COMPARTMENT_PROPERTIES,
    MBDDatumSystem,
    ViewProviderMBDDatumSystem,
    datum_compartment_label,
    datum_system_compartments,
    datum_system_label,
    datum_system_object_label,
    synchronize_datum_system_label,
    is_datum_system_object
)
from MBDFeatureControlFrame import (
    MBDFeatureControlFrame,
    ViewProviderMBDFeatureControlFrame
)
import MBDExporter
VALID_DATUM_LETTERS = [
    "A","B","C","D","E","F","G","H",
    "J","K","L","M","N",
    "P","R","S","T","U","V","W","Y"
]

MAX_DISPLAY_OFFSET = 1000.0
TEXT_HEIGHT_FACTOR = 0.12
TEXT_STAGGER_FACTOR = 1.35
PMI_TEXT_HEIGHT_FACTOR = 0.06
EXTENSION_GAP_FACTOR = 0.7
EXTENSION_OVERSHOOT_FACTOR = 0.8
ARROW_LENGTH_FACTOR = 1.3
ARROW_WIDTH_FACTOR = 0.45
TEXT_WIDTH_FACTOR = 0.62
TEXT_GAP_FACTOR = 0.35

GEOMETRIC_TOLERANCE_SYMBOLS = [
    ("Straightness", "⏤"),
    ("Flatness", "⏥"),
    ("Circularity", "○"),
    ("Cylindricity", "⌭"),
    ("Profile of a Line", "⌒"),
    ("Profile of a Surface", "⌓"),
    ("Angularity", "∠"),
    ("Perpendicularity", "⟂"),
    ("Parallelism", "∥"),
    ("Position", "⌖"),
    ("Concentricity", "◎"),
    ("Symmetry", "⌯"),
    ("Circular Runout", "↗"),
    ("Total Runout", "⌰"),
    ("Diameter", "⌀"),
]


def command_icon(filename):
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "mbd_command_icons",
        filename
    )


def finite_number(value):
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def finite_vector(vector):
    return (
        finite_number(vector.x)
        and finite_number(vector.y)
        and finite_number(vector.z)
    )


def sane_bound_box(bbox):
    values = [
        bbox.XMin, bbox.XMax,
        bbox.YMin, bbox.YMax,
        bbox.ZMin, bbox.ZMax,
        bbox.XLength, bbox.YLength, bbox.ZLength,
    ]

    if not all(finite_number(value) for value in values):
        return False

    if max(bbox.XLength, bbox.YLength, bbox.ZLength) > MAX_DISPLAY_OFFSET:
        return False

    return True


def is_semantic_pmi_object(obj):
    return getattr(obj, "IsSemanticPMI", False)


def get_mbd_pmi_group(doc):
    if doc is None:
        return None

    group = doc.getObject("MBD_PMI")

    if group is None:
        group = doc.addObject("App::DocumentObjectGroup", "MBD_PMI")
        group.Label = "MBD PMI"

    return group


def add_to_mbd_pmi_group(doc, obj):
    group = get_mbd_pmi_group(doc)

    if group is None or obj is None or obj == group:
        return None

    try:
        if obj not in group.Group:
            group.addObject(obj)
    except Exception:
        pass

    return group


def organize_pmi_tree(doc):
    group = get_mbd_pmi_group(doc)

    if group is None:
        return None

    for obj in doc.Objects:
        if obj == group:
            continue

        if not is_semantic_pmi_object(obj):
            continue

        if is_datum_system_object(obj):
            synchronize_datum_system_label(obj)

        add_to_mbd_pmi_group(doc, obj)

        if (
            FreeCAD.GuiUp
            and hasattr(obj, "DatumLabel")
            and not hasattr(obj, "TargetId")
        ):
            activate_datum_view_provider(doc, obj)

        if FreeCAD.GuiUp and hasattr(obj, "ToleranceType"):
            proxy = getattr(getattr(obj, "ViewObject", None), "Proxy", None)

            if not hasattr(proxy, "rebuild"):
                ViewProviderMBDFeatureControlFrame(obj.ViewObject)
                proxy = getattr(obj.ViewObject, "Proxy", None)

            clear_fcf_display_helpers(doc, obj)

            if hasattr(proxy, "rebuild"):
                proxy.rebuild()

        if FreeCAD.GuiUp and hasattr(obj, "TargetId"):
            proxy = getattr(getattr(obj, "ViewObject", None), "Proxy", None)

            if not hasattr(proxy, "rebuild"):
                ViewProviderMBDDatumTarget(obj.ViewObject)
                proxy = getattr(obj.ViewObject, "Proxy", None)

            clear_datum_target_display_helpers(doc, obj)

            if hasattr(proxy, "rebuild"):
                proxy.rebuild()

        if FreeCAD.GuiUp and (
            hasattr(obj, "DimensionKind")
            or hasattr(obj, "DimensionType")
        ):
            activate_dimension_view_provider(doc, obj)

    return group


def get_existing_datum_labels(doc):
    labels = set()

    for obj in doc.Objects:
        if hasattr(obj, "IsSemanticPMI") and hasattr(obj, "DatumLabel"):
            labels.add(obj.DatumLabel.strip().upper())

    return labels


def get_next_available_datum_label(doc):

    used = get_existing_datum_labels(doc)

    # Single-letter labels
    for letter in VALID_DATUM_LETTERS:
        if letter not in used:
            return letter

    # Double-letter labels
    for first in VALID_DATUM_LETTERS:
        for second in VALID_DATUM_LETTERS:

            label = first + second

            if label not in used:
                return label

    raise Exception("Ran out of datum labels.")

def get_datum_system_objects(doc):

    systems = []

    for obj in doc.Objects:

        if is_datum_system_object(obj):
            systems.append(obj)

    return systems


def get_datum_feature_objects(doc):
    datums = []

    for obj in doc.Objects:
        if hasattr(obj, "DatumLabel") and getattr(obj, "IsSemanticPMI", False):
            datums.append(obj)

    return datums


def get_datum_target_objects(doc, datum_obj=None):

    targets = []

    for obj in doc.Objects:
        if not hasattr(obj, "TargetId"):
            continue

        if datum_obj is not None and obj.ParentDatum != datum_obj:
            continue

        targets.append(obj)

    return targets


def get_next_datum_target_id(doc, datum_obj):
    prefix = datum_obj.DatumLabel.strip().upper()
    used = set()

    for target in get_datum_target_objects(doc, datum_obj):
        used.add(target.TargetId.strip().upper())

    index = 1

    while True:
        target_id = "{}{}".format(prefix, index)

        if target_id not in used:
            return target_id

        index += 1


def selection_subelement(selection):
    if selection.SubElementNames:
        return selection.SubElementNames[0]

    return ""


def object_has_solid_shape(obj):
    try:
        shape = obj.Shape
        return len(shape.Solids) > 0 or shape.ShapeType == "Solid"
    except Exception:
        return False


def body_level_fcf_candidate(obj):
    if obj is None:
        return False

    if is_pmi_display_helper(obj):
        return False

    if not object_has_solid_shape(obj):
        return False

    type_id = getattr(obj, "TypeId", "")

    if type_id == "PartDesign::Body":
        return True

    return hasattr(obj, "Shape")


def single_body_level_fcf_candidate(doc):
    candidates = [
        obj for obj in doc.Objects
        if body_level_fcf_candidate(obj)
    ]

    bodies = [
        obj for obj in candidates
        if getattr(obj, "TypeId", "") == "PartDesign::Body"
    ]

    if len(bodies) == 1:
        return bodies[0]

    if len(candidates) == 1:
        return candidates[0]

    return None


def expanded_selection_references(selection):
    references = []

    for item in selection:
        subelements = list(getattr(item, "SubElementNames", []))

        if not subelements:
            references.append((item, ""))
            continue

        for subelement in subelements:
            references.append((item, subelement))

    return references


def semantic_reference_for_subelement(doc, selection, subelement):
    obj = selection.Object

    if hasattr(obj, "DatumLabel"):
        return obj, ""

    if not subelement:
        return obj, subelement

    for candidate in doc.Objects:
        if not hasattr(candidate, "DatumLabel"):
            continue

        try:
            if (
                candidate.ReferencedObject == obj
                and candidate.ReferencedSubelement == subelement
            ):
                return candidate, ""
        except Exception:
            pass

    return obj, subelement


def semantic_datum_for_selection(doc, selection):
    obj = selection.Object
    subelement = selection_subelement(selection)

    if hasattr(obj, "DatumLabel"):
        return obj, ""

    if not subelement:
        return obj, subelement

    for candidate in doc.Objects:
        if not hasattr(candidate, "DatumLabel"):
            continue

        try:
            if (
                candidate.ReferencedObject == obj
                and candidate.ReferencedSubelement == subelement
            ):
                return candidate, ""
        except Exception:
            pass

    return obj, subelement


def document_shape_center_and_size(doc):
    bbox = document_shape_bound_box(doc)

    if bbox is None:
        return None, 10.0

    center = FreeCAD.Vector(
        (bbox.XMin + bbox.XMax) * 0.5,
        (bbox.YMin + bbox.YMax) * 0.5,
        (bbox.ZMin + bbox.ZMax) * 0.5
    )
    size = max(bbox.XLength, bbox.YLength, bbox.ZLength, 10.0)
    size = min(size, MAX_DISPLAY_OFFSET)

    return center, size


def is_pmi_display_helper(obj):
    name = getattr(obj, "Name", "")
    label = getattr(obj, "Label", "")
    name_label = "{} {}".format(name, label)

    if getattr(obj, "IsSemanticPMI", False):
        return True

    helper_patterns = [
        "MBD_BasicDimension_Display",
        "MBD_GDTSymbolTable",
        "_Display",
        "_TextBox",
        "_Text",
        "_Frame",
        "_Leader",
        "_Marker",
        "_Symbol",
        "_Separator",
        "DiameterSymbol",
        "PositionSymbol",
        "FlatnessSymbol",
    ]

    for pattern in helper_patterns:
        if pattern in name_label:
            return True

    try:
        for parent in obj.InList:
            try:
                if not hasattr(parent, "Group") or obj not in parent.Group:
                    continue
            except Exception:
                continue

            if getattr(parent, "IsSemanticPMI", False):
                return True

            parent_name_label = "{} {}".format(
                getattr(parent, "Name", ""),
                getattr(parent, "Label", "")
            )

            if "MBD_GDTSymbolTable" in parent_name_label:
                return True
    except Exception:
        pass

    return False


def clear_fcf_display_helpers(doc, fcf_obj):
    helpers = []

    for property_name in ("DisplayFrame", "DisplayText", "DisplayLeader"):
        try:
            helper = getattr(fcf_obj, property_name, None)

            if helper is not None and helper not in helpers:
                helpers.append(helper)

            setattr(fcf_obj, property_name, None)
        except Exception:
            pass

    try:
        for child in list(fcf_obj.Group):
            if getattr(child, "IsSemanticPMI", False):
                continue

            if child not in helpers:
                helpers.append(child)
    except Exception:
        pass

    for helper in helpers:
        try:
            if hasattr(fcf_obj, "removeObject"):
                fcf_obj.removeObject(helper)
        except Exception:
            pass

        try:
            if doc.getObject(helper.Name) is not None:
                doc.removeObject(helper.Name)
        except Exception:
            pass

    return len(helpers)


def clear_datum_target_display_helpers(doc, target_obj):
    helper = getattr(target_obj, "DisplayText", None)

    try:
        target_obj.DisplayText = None
    except Exception:
        pass

    helpers = []

    if helper is not None:
        helpers.append(helper)

    try:
        for child in list(target_obj.Group):
            if getattr(child, "IsSemanticPMI", False):
                continue

            if child not in helpers:
                helpers.append(child)
    except Exception:
        pass

    for child in helpers:
        try:
            target_obj.removeObject(child)
        except Exception:
            pass

        try:
            if doc.getObject(child.Name) is not None:
                doc.removeObject(child.Name)
        except Exception:
            pass

    return len(helpers)


def adopt_datum_layout_from_helpers(doc, datum_obj):
    text_obj = getattr(datum_obj, "DisplayText", None)

    if text_obj is None:
        return False

    try:
        placement = text_obj.Placement
        rotation = placement.Rotation
        text_height = pmi_text_height(doc)
        view_obj = getattr(text_obj, "ViewObject", None)

        if view_obj is not None and hasattr(view_obj, "FontSize"):
            text_height = float(view_obj.FontSize)

        return update_pmi_display_layout(
            datum_obj,
            placement.Base,
            rotation.multVec(FreeCAD.Vector(0, 0, 1)),
            rotation.multVec(FreeCAD.Vector(1, 0, 0)),
            text_height
        )
    except Exception:
        return False


def clear_datum_display_helpers(doc, datum_obj):
    helpers = []

    for property_name in (
        "DisplayText",
        "DisplayFrame",
        "DisplayMarker",
        "DisplayLeader",
    ):
        try:
            helper = getattr(datum_obj, property_name, None)

            if helper is not None and helper not in helpers:
                helpers.append(helper)

            setattr(datum_obj, property_name, None)
        except Exception:
            pass

    try:
        for child in list(datum_obj.Group):
            if getattr(child, "IsSemanticPMI", False):
                continue

            if child not in helpers:
                helpers.append(child)
    except Exception:
        pass

    for helper in helpers:
        try:
            datum_obj.removeObject(helper)
        except Exception:
            pass

        try:
            if doc.getObject(helper.Name) is not None:
                doc.removeObject(helper.Name)
        except Exception:
            pass

    return len(helpers)


def set_default_datum_display_layout(doc, datum_obj):
    normal = datum_outward_normal(doc, datum_obj)
    point = referenced_subelement_center(
        datum_obj.ReferencedObject,
        datum_obj.ReferencedSubelement
    )

    if point is None:
        return False

    height = pmi_text_height(doc)
    leader_direction = FreeCAD.Vector(0, 0, 1)

    if normal is not None and finite_vector(normal) and normal.Length > 0:
        leader_direction = FreeCAD.Vector(normal)

    leader_direction.normalize()
    rotation = datum_symbol_rotation(leader_direction)
    box_origin = point + leader_direction * (
        height * 1.2
        + height * 0.25
        + height * 1.6
        + height * 0.25
    )
    plane_normal = (
        rotation.multVec(FreeCAD.Vector(0, 0, 1))
        if rotation else normal
    )
    reading_direction = (
        rotation.multVec(FreeCAD.Vector(1, 0, 0))
        if rotation else leader_direction
    )
    return update_pmi_display_layout(
        datum_obj,
        box_origin,
        plane_normal,
        reading_direction,
        height
    )


def activate_datum_view_provider(doc, datum_obj):
    adopted = adopt_datum_layout_from_helpers(doc, datum_obj)

    if not adopted and (
        not hasattr(datum_obj, "AnnotationTextHeight")
        or float(datum_obj.AnnotationTextHeight) <= 0
    ):
        set_default_datum_display_layout(doc, datum_obj)

    proxy = getattr(
        getattr(datum_obj, "ViewObject", None),
        "Proxy",
        None
    )

    if not hasattr(proxy, "rebuild"):
        ViewProviderMBDDatumFeature(datum_obj.ViewObject)
        proxy = getattr(datum_obj.ViewObject, "Proxy", None)

    clear_datum_display_helpers(doc, datum_obj)

    if hasattr(proxy, "rebuild"):
        proxy.rebuild()

    return proxy


def adopt_dimension_layout_from_helpers(doc, dimension_obj):
    text_obj = getattr(dimension_obj, "DisplayText", None)

    if text_obj is None:
        return False

    try:
        placement = text_obj.Placement
        rotation = placement.Rotation
        text_height = pmi_text_height(doc)
        view_obj = getattr(text_obj, "ViewObject", None)

        if view_obj is not None and hasattr(view_obj, "FontSize"):
            text_height = float(view_obj.FontSize)

        return update_pmi_display_layout(
            dimension_obj,
            placement.Base,
            rotation.multVec(FreeCAD.Vector(0, 0, 1)),
            rotation.multVec(FreeCAD.Vector(1, 0, 0)),
            text_height
        )
    except Exception:
        return False


def clear_dimension_display_helpers(doc, dimension_obj):
    helpers = []

    for property_name in (
        "DisplayDimension",
        "DisplayText",
        "DisplayTextBox",
    ):
        try:
            helper = getattr(dimension_obj, property_name, None)

            if helper is not None:
                if helper not in helpers:
                    helpers.append(helper)

                setattr(dimension_obj, property_name, None)
        except Exception:
            pass

    try:
        for child in list(dimension_obj.Group):
            if getattr(child, "IsSemanticPMI", False):
                continue

            if child not in helpers:
                helpers.append(child)
    except Exception:
        pass

    for helper in helpers:
        try:
            dimension_obj.removeObject(helper)
        except Exception:
            pass

        try:
            if doc.getObject(helper.Name) is not None:
                doc.removeObject(helper.Name)
        except Exception:
            pass

    return len(helpers)


def activate_dimension_view_provider(
    doc,
    dimension_obj,
    resolved_display_data=None
):
    timing_started = time.perf_counter()
    adopt_dimension_layout_from_helpers(doc, dimension_obj)
    timing_adopted = time.perf_counter()
    proxy = getattr(
        getattr(dimension_obj, "ViewObject", None),
        "Proxy",
        None
    )
    timing_proxy_read = time.perf_counter()
    created_provider = False

    if not hasattr(proxy, "rebuild"):
        if hasattr(dimension_obj, "DimensionKind"):
            ViewProviderMBDDimension(
                dimension_obj.ViewObject,
                resolved_display_data
            )
        else:
            ViewProviderMBDBasicDimension(
                dimension_obj.ViewObject,
                resolved_display_data
            )

        proxy = getattr(dimension_obj.ViewObject, "Proxy", None)
        created_provider = True

    timing_provider_created = time.perf_counter()

    if (
        not created_provider
        and resolved_display_data is not None
        and proxy is not None
    ):
        proxy._resolved_display_data = resolved_display_data

    clear_dimension_display_helpers(doc, dimension_obj)
    timing_helpers_cleared = time.perf_counter()

    if proxy is not None:
        proxy._suspend_rebuild = False

    # Assigning a new view provider invokes attach(), which performs the
    # initial rebuild using resolved_display_data. Rebuilding again here
    # duplicated all scene-graph work and could force another geometry query.
    if not created_provider and hasattr(proxy, "rebuild"):
        proxy.rebuild()

    timing_rebuilt = time.perf_counter()

    if timing_rebuilt - timing_started > 1.0:
        FreeCAD.Console.PrintMessage(
            "Dimension provider phases for {}: adopt {:.3f}s, lookup {:.3f}s, "
            "construct {:.3f}s, cleanup {:.3f}s, rebuild {:.3f}s\n".format(
                dimension_obj.Name,
                timing_adopted - timing_started,
                timing_proxy_read - timing_adopted,
                timing_provider_created - timing_proxy_read,
                timing_helpers_cleared - timing_provider_created,
                timing_rebuilt - timing_helpers_cleared
            )
        )

    return proxy


def document_model_shape_objects(doc):
    objects = []

    for obj in doc.Objects:
        if is_pmi_display_helper(obj):
            continue

        type_id = str(getattr(obj, "TypeId", ""))

        if type_id == "PartDesign::Body":
            objects.append(obj)
            continue

        try:
            parent = obj.getParentGeoFeatureGroup()
        except Exception:
            parent = None

        if (
            parent is not None
            and str(getattr(parent, "TypeId", "")) == "PartDesign::Body"
        ):
            # The Body shape already represents its complete feature history.
            # Reading every intermediate feature shape can trigger expensive
            # Part Design recomputes during annotation layout.
            continue

        objects.append(obj)

    return objects


def document_shape_bound_box(doc):
    bbox = None

    for obj in document_model_shape_objects(doc):
        try:
            if not hasattr(obj, "Shape") or obj.Shape.isNull():
                continue

            obj_box = obj.Shape.BoundBox

            if not sane_bound_box(obj_box):
                continue

            if bbox is None:
                bbox = obj_box
            else:
                bbox.add(obj_box)
        except Exception:
            pass

    return bbox


def bound_box_corners(bbox):
    return [
        FreeCAD.Vector(x, y, z)
        for x in [bbox.XMin, bbox.XMax]
        for y in [bbox.YMin, bbox.YMax]
        for z in [bbox.ZMin, bbox.ZMax]
    ]


def max_projection(points, direction):
    return max(point.dot(direction) for point in points)


def pmi_text_height(doc):
    _, doc_size = document_shape_center_and_size(doc)
    return max(doc_size * PMI_TEXT_HEIGHT_FACTOR, 3.0)


def display_offset_for_dimension(doc, p1, p2):
    return display_offset_for_dimension_with_preference(doc, p1, p2, None)


def preferred_display_offset_beyond_model(doc, p1, p2, display_direction, text_height):
    if display_direction is None or not finite_vector(display_direction):
        return None

    leader = FreeCAD.Vector(display_direction)

    if leader.Length <= 1e-9:
        return None

    leader.normalize()
    current_extent = model_extent_along(doc, leader)
    offset, _new_extent = offset_beyond_current_extent(
        doc,
        p1,
        p2,
        leader,
        current_extent,
        text_height
    )
    return offset


def exterior_direction_from_point(doc, point, direction):
    if point is None or direction is None or not finite_vector(direction):
        return None

    candidate = FreeCAD.Vector(direction)

    if candidate.Length <= 1e-9:
        return None

    candidate.normalize()
    opposite = candidate.negative()

    doc_center, _doc_size = document_shape_center_and_size(doc)

    if doc_center is not None and finite_vector(doc_center):
        outward = point - doc_center

        if outward.Length > 1e-9:
            if candidate.dot(outward) < 0:
                return opposite

            return candidate

    bbox = document_shape_bound_box(doc)

    if bbox is None:
        return candidate

    corners = bound_box_corners(bbox)
    candidate_gap = max_projection(corners, candidate) - point.dot(candidate)
    opposite_gap = max_projection(corners, opposite) - point.dot(opposite)

    if opposite_gap < candidate_gap:
        return opposite

    return candidate


def display_offset_for_dimension_with_preference(doc, p1, p2, preferred_offset):
    midpoint = p1 + ((p2 - p1) * 0.5)
    measured_direction = p2 - p1
    using_preferred_offset = False

    if preferred_offset is not None and finite_vector(preferred_offset):
        offset = FreeCAD.Vector(preferred_offset)
        using_preferred_offset = True
        offset_length = max(offset.Length, 15.0)
    else:
        doc_center, doc_size = document_shape_center_and_size(doc)
        offset_length = min(
            max(doc_size * 0.75, 15.0),
            MAX_DISPLAY_OFFSET * 0.1
        )
        offset = FreeCAD.Vector(0, 0, offset_length)

        if doc_center is not None and finite_vector(doc_center):
            offset = midpoint - doc_center

    if not finite_vector(offset) or offset.Length > MAX_DISPLAY_OFFSET:
        offset = FreeCAD.Vector(0, 0, offset_length)

    if measured_direction.Length > 0 and offset.Length > 0:
        measured_unit = FreeCAD.Vector(measured_direction)
        measured_unit.normalize()
        offset = offset - measured_unit * offset.dot(measured_unit)

    if not finite_vector(offset) or offset.Length > MAX_DISPLAY_OFFSET:
        offset = FreeCAD.Vector(0, 0, offset_length)

    if offset.Length == 0 and measured_direction.Length > 0:
        offset = measured_direction.cross(FreeCAD.Vector(0, 0, 1))

        if offset.Length == 0:
            offset = measured_direction.cross(FreeCAD.Vector(0, 1, 0))

    if offset.Length == 0:
        offset = FreeCAD.Vector(0, 0, offset_length)
    elif using_preferred_offset:
        if offset.Length > MAX_DISPLAY_OFFSET:
            offset.normalize()
            offset.multiply(MAX_DISPLAY_OFFSET)
    else:
        offset.normalize()
        offset.multiply(offset_length)

    return offset


def diameter_annotation_plane_normal(p1, p2, display_direction):
    if (
        p1 is None
        or p2 is None
        or display_direction is None
        or not finite_vector(display_direction)
    ):
        return None

    measured_direction = p2 - p1

    if measured_direction.Length <= 1e-9:
        return None

    normal = measured_direction.cross(FreeCAD.Vector(display_direction))

    if normal.Length <= 1e-9:
        return None

    normal.normalize()
    return normal


def dimension_display_layout(
    doc,
    p1,
    p2,
    label,
    dimension_kind,
    preferred_offset=None,
    text_normal=None,
    text_height=None
):
    measured_direction = p2 - p1

    if measured_direction.Length <= 1e-9:
        return None

    if text_height is None:
        text_height = pmi_text_height(doc)

    if str(dimension_kind) == "Radius":
        radius_direction = FreeCAD.Vector(measured_direction)
        radius_direction.normalize()
        normal = None

        if text_normal is not None and finite_vector(text_normal):
            normal = FreeCAD.Vector(text_normal)
            normal = (
                normal
                - radius_direction * normal.dot(radius_direction)
            )

            if normal.Length <= 1e-9:
                normal = None

        if normal is None:
            normal = radius_direction.cross(FreeCAD.Vector(0, 0, 1))

            if normal.Length <= 1e-9:
                normal = radius_direction.cross(FreeCAD.Vector(0, 1, 0))

        if normal.Length <= 1e-9:
            return None

        normal.normalize()
        _center, doc_size = document_shape_center_and_size(doc)
        leader_length = min(
            max(doc_size * 0.25, text_height * 6.0),
            MAX_DISPLAY_OFFSET * 0.25
        )
        text_gap = text_height * TEXT_GAP_FACTOR
        arrow_length = text_height * ARROW_LENGTH_FACTOR
        leader_end = p2 + radius_direction * leader_length
        text_point = (
            leader_end
            + radius_direction * (arrow_length + text_gap)
        )
        rotation = text_rotation_for_display_line(
            p2,
            leader_end,
            normal
        )
    else:
        offset = display_offset_for_dimension_with_preference(
            doc,
            p1,
            p2,
            preferred_offset
        )
        p1_display = p1 + offset
        p2_display = p2 + offset
        dim_direction = p2_display - p1_display

        if dim_direction.Length <= 1e-9:
            return None

        dim_direction.normalize()
        arrow_length = text_height * ARROW_LENGTH_FACTOR
        prefix_width = (
            text_height * 1.15
            if str(dimension_kind) == "Diameter"
            else 0.0
        )
        prefix_gap = (
            text_height * 0.25
            if str(dimension_kind) == "Diameter"
            else 0.0
        )
        text_width = (
            max(
                len(label) * text_height * TEXT_WIDTH_FACTOR,
                text_height * 2.0
            )
            + prefix_width
            + prefix_gap
        )
        text_clearance = text_height * TEXT_GAP_FACTOR
        available_width = max(
            (p2_display - p1_display).Length - arrow_length * 2.0,
            0.0
        )
        text_fits_inside = (
            text_width + text_clearance * 2.0 < available_width
        )
        rotation = text_rotation_for_display_line(
            p1_display,
            p2_display,
            text_normal
        )
        text_axis = FreeCAD.Vector(dim_direction)

        if rotation is not None:
            text_axis = rotation.multVec(FreeCAD.Vector(1, 0, 0))

        if text_axis.Length <= 1e-9:
            text_axis = FreeCAD.Vector(dim_direction)

        text_axis.normalize()
        midpoint = p1 + (p2 - p1) * 0.5

        if text_fits_inside:
            text_point = (
                midpoint
                + offset
                - text_axis * (text_width * 0.5)
            )
        else:
            right_display = p2_display

            if p1_display.dot(text_axis) > p2_display.dot(text_axis):
                right_display = p1_display

            text_point = (
                right_display
                + text_axis * (
                    arrow_length + text_clearance * 2.0
                )
            )

    if rotation is not None:
        normal = rotation.multVec(FreeCAD.Vector(0, 0, 1))
        direction = rotation.multVec(FreeCAD.Vector(1, 0, 0))
    else:
        direction = FreeCAD.Vector(measured_direction)
        direction.normalize()
        normal = (
            FreeCAD.Vector(text_normal)
            if text_normal is not None and finite_vector(text_normal)
            else direction.cross(FreeCAD.Vector(0, 0, 1))
        )

        if normal.Length <= 1e-9:
            normal = direction.cross(FreeCAD.Vector(0, 1, 0))

        if normal.Length <= 1e-9:
            normal = FreeCAD.Vector(0, 0, 1)

        normal.normalize()

    return {
        "origin": text_point,
        "normal": normal,
        "direction": direction,
    }


def make_basic_dimension_display(
    doc,
    p1,
    p2,
    label,
    preferred_offset=None,
    text_normal=None,
    owner_name="MBD_BasicDimension",
    text_height=None,
    boxed_text=True,
    prefix_symbol_name=None
):
    try:
        midpoint = p1 + ((p2 - p1) * 0.5)
        offset = display_offset_for_dimension_with_preference(
            doc,
            p1,
            p2,
            preferred_offset
        )
        measured_direction = p2 - p1

        if measured_direction.Length == 0:
            return None

        if text_height is None:
            text_height = pmi_text_height(doc)

        p1_display = p1 + offset
        p2_display = p2 + offset
        dim_direction = p2_display - p1_display

        if dim_direction.Length == 0:
            return None

        dim_direction.normalize()
        extension_direction = FreeCAD.Vector(offset)

        if extension_direction.Length == 0:
            return None

        extension_direction.normalize()
        extension_gap = text_height * EXTENSION_GAP_FACTOR
        extension_overshoot = text_height * EXTENSION_OVERSHOOT_FACTOR
        arrow_length = text_height * ARROW_LENGTH_FACTOR
        arrow_width = text_height * ARROW_WIDTH_FACTOR
        prefix_width = text_height * 1.15 if prefix_symbol_name else 0.0
        prefix_gap = text_height * 0.25 if prefix_symbol_name else 0.0
        text_width = (
            max(len(label) * text_height * TEXT_WIDTH_FACTOR, text_height * 2.0)
            + prefix_width
            + prefix_gap
        )
        text_clearance = text_height * TEXT_GAP_FACTOR
        available_width = max(
            (p2_display - p1_display).Length - (arrow_length * 2.0),
            0.0
        )
        text_fits_inside = text_width + (text_clearance * 2.0) < available_width
        text_rotation = text_rotation_for_display_line(
            p1_display,
            p2_display,
            text_normal
        )
        text_axis = FreeCAD.Vector(dim_direction)

        if text_rotation is not None:
            try:
                text_axis = text_rotation.multVec(FreeCAD.Vector(1, 0, 0))
            except Exception:
                text_axis = FreeCAD.Vector(dim_direction)

        if text_axis.Length == 0:
            text_axis = FreeCAD.Vector(dim_direction)

        text_axis.normalize()

        part_p1 = p1 + extension_direction * extension_gap
        part_p2 = p2 + extension_direction * extension_gap
        ext1_end = p1_display + extension_direction * extension_overshoot
        ext2_end = p2_display + extension_direction * extension_overshoot
        dimension_start = p1_display
        dimension_end = p2_display
        text_point = midpoint + offset

        if not text_fits_inside:
            right_display = p2_display
            left_display = p1_display

            if p1_display.dot(text_axis) > p2_display.dot(text_axis):
                right_display = p1_display
                left_display = p2_display

            if (right_display - p2_display).Length < 1e-6:
                dimension_end = right_display + text_axis * (arrow_length + text_clearance)
            else:
                dimension_start = right_display + text_axis * (arrow_length + text_clearance)

            text_point = right_display + text_axis * (arrow_length + (text_clearance * 2.0))
        else:
            text_point = (midpoint + offset) - text_axis * (text_width * 0.5)

        if not finite_vector(p1_display) or not finite_vector(p2_display):
            FreeCAD.Console.PrintWarning(
                "Skipped basic dimension display because display coordinates were invalid.\n"
            )
            return None

        arrow1 = make_arrowhead_shapes(
            p1_display,
            dim_direction,
            extension_direction,
            arrow_length,
            arrow_width,
            inward=True
        )
        arrow2 = make_arrowhead_shapes(
            p2_display,
            dim_direction.negative(),
            extension_direction,
            arrow_length,
            arrow_width,
            inward=True
        )
        shapes = [
            Part.makePolygon([part_p1, ext1_end]),
            Part.makePolygon([part_p2, ext2_end]),
            Part.makePolygon([dimension_start, dimension_end]),
        ]
        shapes.extend(arrow1)
        shapes.extend(arrow2)

        dim = doc.addObject("Part::Feature", owner_name + "_Display")
        dim.Shape = Part.makeCompound(shapes)
        dim.Label = dim.Name

        view_obj = getattr(dim, "ViewObject", None)

        if view_obj is not None:
            for prop, value in [
                ("LineColor", (1.0, 1.0, 1.0)),
                ("PointColor", (1.0, 1.0, 1.0)),
                ("LineWidth", 1.0),
                ("PointSize", 2.0),
            ]:
                if hasattr(view_obj, prop):
                    try:
                        setattr(view_obj, prop, value)
                    except Exception:
                        pass

        text_origin = text_point
        symbol_obj = None

        if prefix_symbol_name:
            symbol_obj = make_gdt_symbol_geometry(
                doc,
                prefix_symbol_name,
                text_point,
                text_height * 0.9,
                text_rotation,
                owner_name + "_" + prefix_symbol_name + "Symbol"
            )
            text_origin = text_point + text_axis * (prefix_width + prefix_gap)

        text_obj = make_basic_dimension_text(
            text_origin,
            label,
            text_height,
            text_rotation,
            owner_name + "_Text"
        )
        text_box = None

        if boxed_text:
            text_box = make_basic_dimension_text_box(
                doc,
                text_point,
                label,
                text_height,
                text_rotation,
                owner_name + "_TextBox"
            )
        doc.recompute()
        FreeCAD.Console.PrintMessage(
            "Created basic dimension display {}: "
            "display line ({:.6f}, {:.6f}, {:.6f}) to "
            "({:.6f}, {:.6f}, {:.6f})\n".format(
                dim.Name,
                p1_display.x, p1_display.y, p1_display.z,
                p2_display.x, p2_display.y, p2_display.z
            )
        )
        return dim, text_obj, text_box, symbol_obj
    except Exception as e:
        FreeCAD.Console.PrintWarning(
            "Could not create basic dimension display: {}\n".format(e)
        )
        return None


def make_radius_dimension_display(
    doc,
    center_point,
    surface_point,
    label,
    text_normal=None,
    owner_name="MBD_Dimension",
    text_height=None,
    boxed_text=False
):
    try:
        if center_point is None or surface_point is None:
            return None

        radius_direction = surface_point - center_point

        if radius_direction.Length <= 1e-9:
            return None

        radius_direction.normalize()

        if text_height is None:
            text_height = pmi_text_height(doc)

        normal = None

        if text_normal is not None and finite_vector(text_normal):
            normal = FreeCAD.Vector(text_normal)
            normal = normal - radius_direction * normal.dot(radius_direction)

            if normal.Length <= 1e-9:
                normal = None

        if normal is None:
            normal = radius_direction.cross(FreeCAD.Vector(0, 0, 1))

            if normal.Length <= 1e-9:
                normal = radius_direction.cross(FreeCAD.Vector(0, 1, 0))

        if normal.Length <= 1e-9:
            return None

        normal.normalize()
        side_direction = normal.cross(radius_direction)

        if side_direction.Length <= 1e-9:
            return None

        side_direction.normalize()
        _center, doc_size = document_shape_center_and_size(doc)
        leader_length = min(
            max(doc_size * 0.25, text_height * 6.0),
            MAX_DISPLAY_OFFSET * 0.25
        )
        text_gap = text_height * TEXT_GAP_FACTOR
        arrow_length = text_height * ARROW_LENGTH_FACTOR
        arrow_width = text_height * ARROW_WIDTH_FACTOR
        leader_end = surface_point + radius_direction * leader_length
        text_point = leader_end + radius_direction * (arrow_length + text_gap)
        rotation = text_rotation_for_display_line(
            surface_point,
            leader_end,
            normal
        )
        shapes = [Part.makePolygon([surface_point, leader_end])]
        shapes.extend(
            make_arrowhead_shapes(
                surface_point,
                radius_direction,
                side_direction,
                arrow_length,
                arrow_width,
                inward=True
            )
        )

        dim = doc.addObject("Part::Feature", owner_name + "_Display")
        dim.Shape = Part.makeCompound(shapes)
        dim.Label = dim.Name

        view_obj = getattr(dim, "ViewObject", None)

        if view_obj is not None:
            for prop, value in [
                ("LineColor", (1.0, 1.0, 1.0)),
                ("LineWidth", 1.0),
            ]:
                if hasattr(view_obj, prop):
                    try:
                        setattr(view_obj, prop, value)
                    except Exception:
                        pass

        text_obj = make_basic_dimension_text(
            text_point,
            label,
            text_height,
            rotation,
            owner_name + "_Text"
        )
        text_box = None

        if boxed_text:
            text_box = make_basic_dimension_text_box(
                doc,
                text_point,
                label,
                text_height,
                rotation,
                owner_name + "_TextBox"
            )

        doc.recompute()
        return dim, text_obj, text_box, None
    except Exception as e:
        FreeCAD.Console.PrintWarning(
            "Could not create radius dimension display: {}\n".format(e)
        )
        return None


def outward_normal_from_shape(doc, shape):
    if shape is None:
        return None

    normal = oriented_normal_from_shape(shape)

    if normal is None:
        return None

    normal.normalize()
    doc_center, _ = document_shape_center_and_size(doc)

    try:
        shape_point = shape.CenterOfMass
    except Exception:
        shape_point = FreeCAD.Vector(0, 0, 0)

    if doc_center is not None and finite_vector(doc_center):
        if (shape_point - doc_center).dot(normal) < 0:
            normal = normal.negative()

    return normal


def oriented_normal_from_shape(shape):
    try:
        u_min, u_max, v_min, v_max = shape.ParameterRange
        normal = shape.normalAt(
            (u_min + u_max) * 0.5,
            (v_min + v_max) * 0.5
        )
    except Exception:
        try:
            normal = FreeCAD.Vector(shape.Surface.Axis)
        except Exception:
            return None

    if normal.Length <= 1e-9:
        return None

    normal.normalize()

    try:
        if str(shape.Orientation).lower() == "reversed":
            normal = normal.negative()
    except Exception:
        pass

    return normal


def point_inside_shape(shape, point):
    try:
        return shape.isInside(point, 1e-5, True)
    except Exception:
        try:
            return shape.distToShape(Part.Vertex(point))[0] <= 1e-5
        except Exception:
            return False


def direction_enters_solid(owner_obj, point, direction):
    return distance_to_enter_owner_solid(owner_obj, point, direction) is not None


def distance_to_enter_owner_solid(owner_obj, point, direction):
    if owner_obj is None or point is None or direction is None:
        return None

    if not finite_vector(direction) or direction.Length <= 1e-9:
        return None

    try:
        solid_shape = owner_obj.Shape
        bbox = solid_shape.BoundBox
    except Exception:
        return None

    probe = FreeCAD.Vector(direction)
    probe.normalize()
    step = max(
        min(max(bbox.XLength, bbox.YLength, bbox.ZLength) * 0.01, 1.0),
        0.025
    )
    max_distance = max(bbox.XLength, bbox.YLength, bbox.ZLength) * 2.0 + step
    distance = step

    while distance <= max_distance:
        sample = point + probe * distance

        if point_inside_shape(solid_shape, sample):
            return distance

        distance += step

    return None


def outward_normal_from_reference(doc, owner_obj, subelement):
    shape = reference_shape(owner_obj, subelement)
    normal = oriented_normal_from_shape(shape)

    if normal is None:
        return None

    try:
        point = shape.CenterOfMass
    except Exception:
        point = referenced_subelement_center(owner_obj, subelement)

    forward_hit = distance_to_enter_owner_solid(owner_obj, point, normal)
    reverse_hit = distance_to_enter_owner_solid(owner_obj, point, normal.negative())

    if forward_hit is not None and reverse_hit is None:
        normal = normal.negative()
    elif reverse_hit is not None and forward_hit is None:
        pass
    elif forward_hit is not None and reverse_hit is not None:
        if forward_hit < reverse_hit:
            normal = normal.negative()
    else:
        exterior = exterior_direction_from_point(doc, point, normal)

        if exterior is not None:
            normal = exterior

    return normal


def normal_probe_report(doc, owner_obj, subelement):
    shape = reference_shape(owner_obj, subelement)
    normal = oriented_normal_from_shape(shape)

    if shape is None or normal is None:
        return "normal probe unavailable"

    try:
        point = shape.CenterOfMass
    except Exception:
        point = referenced_subelement_center(owner_obj, subelement)

    forward_hit = distance_to_enter_owner_solid(owner_obj, point, normal)
    reverse_hit = distance_to_enter_owner_solid(owner_obj, point, normal.negative())
    chosen = outward_normal_from_reference(doc, owner_obj, subelement)

    try:
        orientation = str(shape.Orientation)
    except Exception:
        orientation = "<unknown>"

    def fmt_vector(vector):
        if vector is None:
            return "<none>"

        return "({:.6f}, {:.6f}, {:.6f})".format(
            vector.x,
            vector.y,
            vector.z
        )

    return (
        "orientation={} point={} oriented_normal={} "
        "forward_hit={} reverse_hit={} chosen={}"
    ).format(
        orientation,
        fmt_vector(point),
        fmt_vector(normal),
        forward_hit,
        reverse_hit,
        fmt_vector(chosen)
    )


def reference_shape(obj, subelement=""):
    if obj is None:
        return None

    if subelement:
        try:
            return obj.Shape.getElement(subelement)
        except Exception:
            return None

    try:
        return obj.Shape
    except Exception:
        return None


def display_context_for_dimension(doc, ref_obj_1, ref_sub_1, ref_obj_2, ref_sub_2, p1, p2):
    normal = outward_normal_from_reference(
        doc,
        ref_obj_1,
        ref_sub_1
    )

    if normal is None:
        normal = outward_normal_from_reference(
            doc,
            ref_obj_2,
            ref_sub_2
        )

    text_normal = normal
    preferred_offset = None

    if normal is not None:
        leader = leader_direction_for_points(doc, p1, p2, normal)

        if leader is not None:
            measured_direction = p2 - p1

            if measured_direction.Length > 0:
                annotation_normal = measured_direction.cross(leader)

                if annotation_normal.Length > 0:
                    annotation_normal.normalize()
                    text_normal = annotation_normal

            current_extent = model_extent_along(doc, leader)
            preferred_offset, _new_extent = offset_beyond_current_extent(
                doc,
                p1,
                p2,
                leader,
                current_extent,
                pmi_text_height(doc)
            )

    return preferred_offset, text_normal


def make_arrowhead_shapes(tip, direction, side_direction, length, width, inward=True):
    if direction is None or side_direction is None:
        return []

    if direction.Length == 0 or side_direction.Length == 0:
        return []

    arrow_direction = FreeCAD.Vector(direction)
    side = FreeCAD.Vector(side_direction)
    arrow_direction.normalize()
    side.normalize()

    if not inward:
        arrow_direction = arrow_direction.negative()

    base = tip + arrow_direction * length
    side_offset = side * (width * 0.5)

    return [
        Part.makePolygon([tip, base + side_offset]),
        Part.makePolygon([tip, base - side_offset]),
    ]


def choose_dimension_text_side(doc, p1_display, p2_display, dim_direction):
    doc_center, _doc_size = document_shape_center_and_size(doc)

    if doc_center is None or not finite_vector(doc_center):
        return 1

    midpoint = p1_display + ((p2_display - p1_display) * 0.5)
    center_delta = midpoint - doc_center

    if center_delta.Length == 0:
        return 1

    if center_delta.dot(dim_direction) >= 0:
        return 1

    return -1


def make_basic_dimension_text_box(doc, point, text, height, rotation=None, object_name="MBD_BasicDimension_TextBox"):
    try:
        width = max(len(text) * height * TEXT_WIDTH_FACTOR, height * 2.0)
        padding = height * 0.35
        return make_annotation_box(
            doc,
            point,
            width,
            height,
            padding,
            rotation,
            object_name
        )
    except Exception as e:
        FreeCAD.Console.PrintWarning(
            "Could not create basic dimension text box: {}\n".format(e)
        )
        return None


def make_annotation_box(doc, point, width, height, padding, rotation=None, object_name="MBD_Annotation_Box"):
    try:
        local_points = [
            FreeCAD.Vector(-padding, -padding, 0),
            FreeCAD.Vector(width + padding, -padding, 0),
            FreeCAD.Vector(width + padding, height + padding, 0),
            FreeCAD.Vector(-padding, height + padding, 0),
            FreeCAD.Vector(-padding, -padding, 0),
        ]

        placement = FreeCAD.Placement(point, rotation or FreeCAD.Rotation())
        points = [placement.multVec(local_point) for local_point in local_points]
        box_obj = doc.addObject("Part::Feature", object_name)
        box_obj.Shape = Part.makePolygon(points)
        box_obj.Label = box_obj.Name

        view_obj = getattr(box_obj, "ViewObject", None)

        if view_obj is not None:
            for prop, value in [
                ("LineColor", (1.0, 1.0, 1.0)),
                ("LineWidth", 1.0),
            ]:
                if hasattr(view_obj, prop):
                    try:
                        setattr(view_obj, prop, value)
                    except Exception:
                        pass

        return box_obj
    except Exception as e:
        FreeCAD.Console.PrintWarning(
            "Could not create annotation box: {}\n".format(e)
        )
        return None


def make_line_feature(doc, p1, p2, object_name="MBD_Line"):
    try:
        if p1 is None or p2 is None:
            return None

        if (p2 - p1).Length <= 1e-9:
            return None

        line_obj = doc.addObject("Part::Feature", object_name)
        line_obj.Shape = Part.makePolygon([p1, p2])
        line_obj.Label = line_obj.Name

        view_obj = getattr(line_obj, "ViewObject", None)

        if view_obj is not None:
            for prop, value in [
                ("LineColor", (1.0, 1.0, 1.0)),
                ("LineWidth", 1.0),
            ]:
                if hasattr(view_obj, prop):
                    try:
                        setattr(view_obj, prop, value)
                    except Exception:
                        pass

        return line_obj
    except Exception as e:
        FreeCAD.Console.PrintWarning(
            "Could not create display line: {}\n".format(e)
        )
        return None


def add_display_children(parent_obj, *children):
    if parent_obj is None or not hasattr(parent_obj, "addObject"):
        return

    for child in children:
        if child is None:
            continue

        try:
            parent_obj.addObject(child)
        except Exception:
            pass


def make_basic_dimension_text(point, text, height, rotation=None, object_name="MBD_BasicDimension_Text"):
    try:
        import Draft

        placement = point

        if rotation is not None:
            placement = FreeCAD.Placement(point, rotation)

        text_obj = Draft.make_text(
            text,
            placement=placement,
            screen=False,
            height=height
        )

        if text_obj is None:
            return None

        text_obj.Label = object_name

        view_obj = getattr(text_obj, "ViewObject", None)

        if view_obj is not None:
            for prop, value in [
                ("TextColor", (1.0, 0.0, 0.0)),
                ("LineColor", (1.0, 0.0, 0.0)),
                ("FontSize", height),
            ]:
                if hasattr(view_obj, prop):
                    try:
                        setattr(view_obj, prop, value)
                    except Exception:
                        pass

        FreeCAD.Console.PrintMessage(
            "Created basic dimension text {} at "
            "({:.6f}, {:.6f}, {:.6f}) value {}\n".format(
                text_obj.Name,
                point.x, point.y, point.z,
                text
            )
        )
        return text_obj
    except Exception as e:
        FreeCAD.Console.PrintWarning(
            "Could not create basic dimension text: {}\n".format(e)
        )
        return None


def referenced_subelement_center(obj, subelement):
    if obj is None or not subelement:
        return None

    try:
        target = obj.Shape.getElement(subelement)

        if hasattr(target, "CenterOfMass"):
            return target.CenterOfMass

        if hasattr(target, "Point"):
            return target.Point
    except Exception:
        pass

    return None


def make_pmi_label_text(doc, point, text, owner_name, normal=None, height=None):
    if point is None:
        return None

    _, doc_size = document_shape_center_and_size(doc)

    if height is None:
        height = pmi_text_height(doc)

    offset = FreeCAD.Vector(0, 0, height * 1.5)

    if normal is not None and finite_vector(normal):
        offset = FreeCAD.Vector(normal)

        if offset.Length > 0:
            offset.normalize()
            offset.multiply(height * 1.5)

    label_point = point + offset
    rotation = None

    if normal is not None:
        rotation = text_rotation_for_display_line(
            label_point,
            label_point + FreeCAD.Vector(1, 0, 0),
            normal
        )

    return make_basic_dimension_text(
        label_point,
        text,
        height,
        rotation,
        owner_name + "_Text"
    )


def symbol_polyline(local_points, placement):
    return Part.makePolygon([placement.multVec(point) for point in local_points])


def symbol_arc_points(cx, cy, rx, ry, start_degrees, end_degrees, segments=24):
    if segments < 2:
        segments = 2

    return [
        FreeCAD.Vector(
            cx + rx * math.cos(math.radians(start_degrees + (end_degrees - start_degrees) * index / segments)),
            cy + ry * math.sin(math.radians(start_degrees + (end_degrees - start_degrees) * index / segments)),
            0
        )
        for index in range(segments + 1)
    ]


def symbol_circle_points(cx, cy, radius, segments=48):
    points = symbol_arc_points(cx, cy, radius, radius, 0, 360, segments)
    points.append(points[0])
    return points


def symbol_ellipse_points(cx, cy, rx, ry, segments=48):
    points = symbol_arc_points(cx, cy, rx, ry, 0, 360, segments)
    points.append(points[0])
    return points


def make_gdt_symbol_geometry(doc, symbol_name, point, size, rotation=None, object_name="MBD_GDT_Symbol"):
    try:
        placement = FreeCAD.Placement(point, rotation or FreeCAD.Rotation())
        shapes = []

        def add_line(x1, y1, x2, y2):
            shapes.append(symbol_polyline([
                FreeCAD.Vector(x1 * size, y1 * size, 0),
                FreeCAD.Vector(x2 * size, y2 * size, 0),
            ], placement))

        def add_poly(points):
            shapes.append(symbol_polyline([
                FreeCAD.Vector(x * size, y * size, 0)
                for x, y in points
            ], placement))

        def add_arc(cx, cy, rx, ry, start_degrees, end_degrees):
            shapes.append(symbol_polyline([
                FreeCAD.Vector(point.x * size, point.y * size, 0)
                for point in symbol_arc_points(cx, cy, rx, ry, start_degrees, end_degrees)
            ], placement))

        def add_circle(cx, cy, radius):
            shapes.append(symbol_polyline([
                FreeCAD.Vector(point.x * size, point.y * size, 0)
                for point in symbol_circle_points(cx, cy, radius)
            ], placement))

        def add_ellipse(cx, cy, rx, ry):
            shapes.append(symbol_polyline([
                FreeCAD.Vector(point.x * size, point.y * size, 0)
                for point in symbol_ellipse_points(cx, cy, rx, ry)
            ], placement))

        def add_arrow(x1, y1, x2, y2):
            add_line(x1, y1, x2, y2)
            direction = FreeCAD.Vector(x2 - x1, y2 - y1, 0)

            if direction.Length <= 1e-9:
                return

            direction.normalize()
            side = FreeCAD.Vector(-direction.y, direction.x, 0)
            tip = FreeCAD.Vector(x2, y2, 0)
            base = tip - direction * 0.16
            left = base + side * 0.06
            right = base - side * 0.06
            add_line(tip.x, tip.y, left.x, left.y)
            add_line(tip.x, tip.y, right.x, right.y)

        if symbol_name == "Straightness":
            add_line(0.15, 0.50, 0.85, 0.50)
        elif symbol_name == "Flatness":
            add_poly([(0.18, 0.38), (0.82, 0.38), (0.70, 0.62), (0.06, 0.62), (0.18, 0.38)])
        elif symbol_name == "Circularity":
            add_circle(0.50, 0.50, 0.28)
        elif symbol_name == "Cylindricity":
            add_circle(0.50, 0.50, 0.18)
            add_line(0.18, 0.18, 0.46, 0.82)
            add_line(0.54, 0.18, 0.82, 0.82)
        elif symbol_name == "Profile of a Line":
            add_arc(0.50, 0.28, 0.35, 0.35, 25, 155)
        elif symbol_name == "Profile of a Surface":
            add_arc(0.50, 0.35, 0.35, 0.30, 20, 160)
            add_line(0.18, 0.35, 0.82, 0.35)
        elif symbol_name == "Angularity":
            add_line(0.18, 0.25, 0.82, 0.25)
            add_line(0.28, 0.25, 0.70, 0.75)
        elif symbol_name == "Perpendicularity":
            add_line(0.18, 0.25, 0.82, 0.25)
            add_line(0.50, 0.25, 0.50, 0.78)
        elif symbol_name == "Parallelism":
            add_line(0.28, 0.22, 0.50, 0.78)
            add_line(0.50, 0.22, 0.72, 0.78)
        elif symbol_name == "Position":
            add_circle(0.50, 0.50, 0.26)
            add_line(0.18, 0.50, 0.82, 0.50)
            add_line(0.50, 0.18, 0.50, 0.82)
        elif symbol_name == "Concentricity":
            add_circle(0.50, 0.50, 0.29)
            add_circle(0.50, 0.50, 0.14)
        elif symbol_name == "Symmetry":
            add_line(0.22, 0.35, 0.78, 0.35)
            add_line(0.12, 0.50, 0.88, 0.50)
            add_line(0.22, 0.65, 0.78, 0.65)
        elif symbol_name == "Circular Runout":
            add_arrow(0.22, 0.28, 0.78, 0.72)
        elif symbol_name == "Total Runout":
            add_line(0.22, 0.28, 0.42, 0.28)
            add_arrow(0.22, 0.28, 0.58, 0.72)
            add_arrow(0.42, 0.28, 0.78, 0.72)
        elif symbol_name == "Diameter":
            add_circle(0.50, 0.50, 0.26)
            add_line(0.28, 0.22, 0.72, 0.78)
        else:
            add_circle(0.50, 0.50, 0.25)

        symbol_obj = doc.addObject("Part::Feature", object_name)
        symbol_obj.Shape = Part.makeCompound(shapes)
        symbol_obj.Label = object_name

        view_obj = getattr(symbol_obj, "ViewObject", None)

        if view_obj is not None:
            for prop, value in [
                ("LineColor", (1.0, 1.0, 1.0)),
                ("LineWidth", 1.0),
            ]:
                if hasattr(view_obj, prop):
                    try:
                        setattr(view_obj, prop, value)
                    except Exception:
                        pass

        return symbol_obj
    except Exception as e:
        FreeCAD.Console.PrintWarning(
            "Could not create GD&T symbol geometry {}: {}\n".format(
                symbol_name,
                e
            )
        )
        return None


def create_geometric_tolerance_symbol_table(doc=None):
    if doc is None:
        doc = FreeCAD.ActiveDocument

    if doc is None:
        doc = FreeCAD.newDocument("MBD_GDTSymbolTable")

    center, doc_size = document_shape_center_and_size(doc)

    if center is None:
        center = FreeCAD.Vector(0, 0, 0)

    height = pmi_text_height(doc)
    row_height = height * 2.0
    symbol_col_width = height * 5.0
    label_col_width = height * 14.0
    table_width = symbol_col_width + label_col_width
    table_height = row_height * (len(GEOMETRIC_TOLERANCE_SYMBOLS) + 1)
    origin = center + FreeCAD.Vector(doc_size * 0.75, doc_size * 0.75, doc_size * 0.75)

    group = doc.addObject("App::DocumentObjectGroup", "MBD_GDTSymbolTable")
    group.Label = "MBD GD&T Symbol Table"

    def add_to_group(obj):
        if obj is not None:
            try:
                group.addObject(obj)
            except Exception:
                pass

    title = make_basic_dimension_text(
        origin,
        "GD&T Symbol Rendering Test",
        height,
        None,
        group.Name + "_Title"
    )
    add_to_group(title)

    header_y = -row_height
    symbol_header = make_basic_dimension_text(
        origin + FreeCAD.Vector(height * 0.3, header_y, 0),
        "Symbol",
        height,
        None,
        group.Name + "_SymbolHeader"
    )
    label_header = make_basic_dimension_text(
        origin + FreeCAD.Vector(symbol_col_width + height * 0.3, header_y, 0),
        "Name",
        height,
        None,
        group.Name + "_NameHeader"
    )
    add_to_group(symbol_header)
    add_to_group(label_header)

    header_frame = make_annotation_box(
        doc,
        origin + FreeCAD.Vector(0, header_y, 0),
        table_width,
        height,
        height * 0.35,
        None,
        group.Name + "_HeaderFrame"
    )
    add_to_group(header_frame)

    for index, (name, _symbol) in enumerate(GEOMETRIC_TOLERANCE_SYMBOLS):
        y = -row_height * (index + 2)
        symbol_obj = make_gdt_symbol_geometry(
            doc,
            name,
            origin + FreeCAD.Vector(height * 0.8, y - height * 0.05, 0),
            height * 1.15,
            None,
            "{}_{:02d}_Symbol".format(group.Name, index + 1)
        )
        label_text = make_basic_dimension_text(
            origin + FreeCAD.Vector(symbol_col_width + height * 0.3, y, 0),
            name,
            height,
            None,
            "{}_{:02d}_Label".format(group.Name, index + 1)
        )
        row_frame = make_annotation_box(
            doc,
            origin + FreeCAD.Vector(0, y, 0),
            table_width,
            height,
            height * 0.35,
            None,
            "{}_{:02d}_Frame".format(group.Name, index + 1)
        )
        separator = make_line_feature(
            doc,
            origin + FreeCAD.Vector(symbol_col_width, y - height * 0.35, 0),
            origin + FreeCAD.Vector(symbol_col_width, y + height * 1.35, 0),
            "{}_{:02d}_Separator".format(group.Name, index + 1)
        )
        add_to_group(symbol_obj)
        add_to_group(label_text)
        add_to_group(row_frame)
        add_to_group(separator)

    doc.recompute()
    FreeCAD.Console.PrintMessage(
        "Created GD&T symbol rendering table with {} symbols.\n".format(
            len(GEOMETRIC_TOLERANCE_SYMBOLS)
        )
    )
    return group


def make_datum_triangle(doc, tip, normal, height, rotation=None, object_name="MBD_Datum_Triangle"):
    try:
        if normal is None or not finite_vector(normal):
            return None

        marker_height = height * 1.2
        marker_width = height * 0.9
        local_points = [
            FreeCAD.Vector(0, -marker_width * 0.5, 0),
            FreeCAD.Vector(0, marker_width * 0.5, 0),
            FreeCAD.Vector(marker_height, 0, 0),
            FreeCAD.Vector(0, -marker_width * 0.5, 0),
        ]
        placement = FreeCAD.Placement(tip, rotation or FreeCAD.Rotation())
        points = [placement.multVec(local_point) for local_point in local_points]
        marker = doc.addObject("Part::Feature", object_name)
        marker.Shape = Part.makePolygon(points)
        marker.Label = marker.Name

        view_obj = getattr(marker, "ViewObject", None)

        if view_obj is not None:
            for prop, value in [
                ("LineColor", (1.0, 1.0, 1.0)),
                ("LineWidth", 1.0),
            ]:
                if hasattr(view_obj, prop):
                    try:
                        setattr(view_obj, prop, value)
                    except Exception:
                        pass

        return marker
    except Exception as e:
        FreeCAD.Console.PrintWarning(
            "Could not create datum triangle marker: {}\n".format(e)
        )
        return None


def datum_symbol_rotation(leader_direction):
    if leader_direction is None or not finite_vector(leader_direction):
        return None

    x_axis = FreeCAD.Vector(leader_direction)

    if x_axis.Length <= 1e-9:
        return None

    x_axis.normalize()
    z_axis = x_axis.cross(FreeCAD.Vector(0, 0, 1))

    if z_axis.Length <= 1e-9:
        z_axis = x_axis.cross(FreeCAD.Vector(0, 1, 0))

    if z_axis.Length <= 1e-9:
        return None

    z_axis.normalize()
    y_axis = z_axis.cross(x_axis)

    if y_axis.Length <= 1e-9:
        return None

    y_axis.normalize()

    return FreeCAD.Rotation(x_axis, y_axis, z_axis, "XYZ")


def create_datum_display_text(doc, datum_obj):
    normal = datum_outward_normal(doc, datum_obj)
    point = referenced_subelement_center(
        datum_obj.ReferencedObject,
        datum_obj.ReferencedSubelement
    )

    if point is None:
        return None

    height = pmi_text_height(doc)
    leader_direction = FreeCAD.Vector(0, 0, 1)

    if normal is not None and finite_vector(normal) and normal.Length > 0:
        leader_direction = FreeCAD.Vector(normal)

    leader_direction.normalize()
    rotation = datum_symbol_rotation(leader_direction)
    triangle_length = height * 1.2
    gap = height * 0.25
    leader_length = height * 1.6
    box_width = max(len(datum_obj.DatumLabel) * height * TEXT_WIDTH_FACTOR, height)
    box_height = height
    box_origin = point + leader_direction * (triangle_length + gap + leader_length + gap)

    text_obj = make_basic_dimension_text(
        box_origin,
        datum_obj.DatumLabel,
        height,
        rotation,
        datum_obj.Name + "_Text"
    )
    frame_obj = make_annotation_box(
        doc,
        box_origin,
        box_width,
        box_height,
        height * 0.25,
        rotation,
        datum_obj.Name + "_Frame"
    )
    marker_obj = make_datum_triangle(
        doc,
        point,
        normal,
        height,
        rotation,
        datum_obj.Name + "_Marker"
    )
    leader_obj = make_line_feature(
        doc,
        point + leader_direction * triangle_length,
        point + leader_direction * (triangle_length + leader_length),
        datum_obj.Name + "_Leader"
    )

    if text_obj is not None:
        datum_obj.DisplayText = text_obj

    if hasattr(datum_obj, "DisplayFrame") and frame_obj is not None:
        datum_obj.DisplayFrame = frame_obj

    if hasattr(datum_obj, "DisplayMarker") and marker_obj is not None:
        datum_obj.DisplayMarker = marker_obj

    if hasattr(datum_obj, "DisplayLeader") and leader_obj is not None:
        datum_obj.DisplayLeader = leader_obj

    add_display_children(datum_obj, marker_obj, leader_obj, frame_obj, text_obj)
    plane_normal = rotation.multVec(FreeCAD.Vector(0, 0, 1)) if rotation else normal
    reading_direction = (
        rotation.multVec(FreeCAD.Vector(1, 0, 0))
        if rotation else leader_direction
    )
    update_pmi_display_layout(
        datum_obj,
        box_origin,
        plane_normal,
        reading_direction,
        height
    )

    return text_obj


def create_datum_target_display_text(doc, target_obj):
    normal = None

    if target_obj.ParentDatum is not None:
        normal = datum_outward_normal(doc, target_obj.ParentDatum)

    point = FreeCAD.Vector(target_obj.TargetPoint)
    height = pmi_text_height(doc)
    offset = FreeCAD.Vector(0, 0, height * 1.5)

    if normal is not None and finite_vector(normal) and normal.Length > 0:
        offset = FreeCAD.Vector(normal)
        offset.normalize()
        offset.multiply(height * 1.5)

    label_point = point + offset
    rotation = None

    if normal is not None:
        rotation = text_rotation_for_display_line(
            label_point,
            label_point + FreeCAD.Vector(1, 0, 0),
            normal
        )

    plane_normal = (
        rotation.multVec(FreeCAD.Vector(0, 0, 1))
        if rotation else normal
    )
    reading_direction = (
        rotation.multVec(FreeCAD.Vector(1, 0, 0))
        if rotation else FreeCAD.Vector(1, 0, 0)
    )
    update_pmi_display_layout(
        target_obj,
        label_point,
        plane_normal,
        reading_direction,
        height
    )
    proxy = getattr(getattr(target_obj, "ViewObject", None), "Proxy", None)

    if hasattr(proxy, "rebuild"):
        clear_datum_target_display_helpers(doc, target_obj)
        proxy.rebuild()
        return target_obj

    text_obj = make_pmi_label_text(
        doc,
        point,
        target_obj.TargetId,
        target_obj.Name,
        normal,
        height
    )

    if text_obj is not None:
        target_obj.DisplayText = text_obj

    add_display_children(target_obj, text_obj)

    if text_obj is not None:
        rotation = text_obj.Placement.Rotation
        text_height = getattr(
            text_obj.ViewObject,
            "FontSize",
            pmi_text_height(doc)
        )

        if hasattr(text_height, "Value"):
            text_height = text_height.Value

    return text_obj


def fcf_display_label(fcf_obj):
    zone = ""

    if getattr(fcf_obj, "DiameterZone", False):
        zone = "DIA "

    tolerance = FreeCAD.Units.Quantity(
        fcf_obj.ToleranceValue,
        FreeCAD.Units.Length
    ).UserString
    pieces = [
        str(fcf_obj.ToleranceType).upper(),
        zone + tolerance,
    ]
    datum_label = ""

    if hasattr(fcf_obj, "DatumReference") and fcf_obj.DatumReference is not None:
        datum = fcf_obj.DatumReference

        if hasattr(datum, "DatumLabel"):
            datum_label = datum.DatumLabel
    else:
        datum_label = datum_system_label(getattr(fcf_obj, "DatumSystem", None))

    if datum_label:
        pieces.append(datum_label)

    return " | ".join(pieces)


def fcf_tolerance_symbol(tolerance_type):
    if str(tolerance_type) == "Angularity":
        return "∠"

    if str(tolerance_type) == "Circularity":
        return "○"

    if str(tolerance_type) == "CircularRunout":
        return "↗"

    if str(tolerance_type) == "Cylindricity":
        return "⌭"

    if str(tolerance_type) == "Position":
        return "⌖"

    if str(tolerance_type) == "LineProfile":
        return "⌒"

    if str(tolerance_type) == "Flatness":
        return "⏥"

    if str(tolerance_type) == "Parallelism":
        return "∥"

    if str(tolerance_type) == "Perpendicularity":
        return "⟂"

    if str(tolerance_type) == "Profile":
        return "⌓"

    if str(tolerance_type) == "Straightness":
        return "⏤"

    if str(tolerance_type) == "TotalRunout":
        return "⌰"

    return str(tolerance_type).upper()


def fcf_cells(fcf_obj):
    tolerance = FreeCAD.Units.Quantity(
        fcf_obj.ToleranceValue,
        FreeCAD.Units.Length
    ).UserString

    if getattr(fcf_obj, "DiameterZone", False):
        tolerance = "⌀ " + tolerance

    cells = [
        fcf_tolerance_symbol(fcf_obj.ToleranceType),
        tolerance,
    ]

    if (
        str(fcf_obj.ToleranceType) == "Profile"
        and getattr(fcf_obj, "ProfileAllOver", False)
    ):
        cells.append("ALL OVER")

    if hasattr(fcf_obj, "DatumReference") and fcf_obj.DatumReference is not None:
        datum = fcf_obj.DatumReference

        if hasattr(datum, "DatumLabel"):
            cells.append(datum.DatumLabel)
    elif fcf_obj.DatumSystem is not None:
        for _role_name, datums in datum_system_compartments(
            fcf_obj.DatumSystem
        ):
            label = datum_compartment_label(datums)

            if label:
                cells.append(label)

    return cells


def parse_length_quantity_text(text):
    return FreeCAD.Units.Quantity(str(text)).Value


def gdt_symbol_name_for_fcf_cell(cell):
    return {
        "⌖": "Position",
        "⏥": "Flatness",
        "∥": "Parallelism",
        "⟂": "Perpendicularity",
        "⌒": "Profile of a Line",
        "⌓": "Profile of a Surface",
        "∠": "Angularity",
        "○": "Circularity",
        "⌭": "Cylindricity",
        "⏤": "Straightness",
        "↗": "Circular Runout",
        "⌰": "Total Runout",
    }.get(cell)


def fcf_cell_layout(cells, height):
    padding = height * 0.3
    cell_widths = [
        max(len(cell) * height * TEXT_WIDTH_FACTOR, height * 1.6)
        for cell in cells
    ]
    frame_height = height + padding * 2.0
    cell_spans = [width + padding * 2.0 for width in cell_widths]
    total_width = sum(cell_spans)
    return padding, cell_widths, cell_spans, frame_height, total_width


def make_fcf_frame(doc, origin, cells, height, rotation=None, object_name="MBD_FCF_Frame"):
    try:
        _padding, _cell_widths, cell_spans, frame_height, total_width = fcf_cell_layout(
            cells,
            height
        )
        local_lines = []
        x = 0.0
        local_lines.append((FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(total_width, 0, 0)))
        local_lines.append((FreeCAD.Vector(total_width, 0, 0), FreeCAD.Vector(total_width, frame_height, 0)))
        local_lines.append((FreeCAD.Vector(total_width, frame_height, 0), FreeCAD.Vector(0, frame_height, 0)))
        local_lines.append((FreeCAD.Vector(0, frame_height, 0), FreeCAD.Vector(0, 0, 0)))

        for span in cell_spans[:-1]:
            x += span
            local_lines.append((FreeCAD.Vector(x, 0, 0), FreeCAD.Vector(x, frame_height, 0)))

        placement = FreeCAD.Placement(origin, rotation or FreeCAD.Rotation())
        shapes = [
            Part.makePolygon([
                placement.multVec(start),
                placement.multVec(end),
            ])
            for start, end in local_lines
        ]
        frame_obj = doc.addObject("Part::Feature", object_name)
        frame_obj.Shape = Part.makeCompound(shapes)
        frame_obj.Label = frame_obj.Name

        view_obj = getattr(frame_obj, "ViewObject", None)

        if view_obj is not None:
            for prop, value in [
                ("LineColor", (1.0, 1.0, 1.0)),
                ("LineWidth", 1.0),
            ]:
                if hasattr(view_obj, prop):
                    try:
                        setattr(view_obj, prop, value)
                    except Exception:
                        pass

        return frame_obj
    except Exception as e:
        FreeCAD.Console.PrintWarning(
            "Could not create FCF frame: {}\n".format(e)
        )
        return None


def make_fcf_cell_texts(doc, origin, cells, height, rotation=None, object_name="MBD_FCF_Text"):
    padding, _cell_widths, cell_spans, _frame_height, _total_width = fcf_cell_layout(
        cells,
        height
    )
    placement = FreeCAD.Placement(origin, rotation or FreeCAD.Rotation())
    text_objects = []
    x = 0.0

    for index, cell in enumerate(cells):
        symbol_name = gdt_symbol_name_for_fcf_cell(cell)

        if symbol_name is not None:
            symbol_size = height * 0.95
            symbol_x = x + (cell_spans[index] - symbol_size) * 0.5
            symbol_point = placement.multVec(FreeCAD.Vector(symbol_x, padding * 0.6, 0))
            symbol_obj = make_gdt_symbol_geometry(
                doc,
                symbol_name,
                symbol_point,
                symbol_size,
                rotation,
                "{}{:02d}_{}Symbol".format(
                    object_name,
                    index + 1,
                    symbol_name
                )
            )

            if symbol_obj is not None:
                text_objects.append(symbol_obj)
        elif cell.startswith("⌀ "):
            text = cell[2:].strip()
            symbol_size = height * 0.75
            gap = height * 0.25
            text_width = len(text) * height * TEXT_WIDTH_FACTOR
            combined_width = symbol_size + gap + text_width
            start_x = x + max((cell_spans[index] - combined_width) * 0.5, padding * 0.5)
            symbol_point = placement.multVec(FreeCAD.Vector(start_x, padding * 0.7, 0))
            text_point = placement.multVec(FreeCAD.Vector(start_x + symbol_size + gap, padding, 0))
            symbol_obj = make_gdt_symbol_geometry(
                doc,
                "Diameter",
                symbol_point,
                symbol_size,
                rotation,
                "{}{:02d}_DiameterSymbol".format(object_name, index + 1)
            )
            text_obj = make_basic_dimension_text(
                text_point,
                text,
                height,
                rotation,
                "{}{:02d}".format(object_name, index + 1)
            )

            if symbol_obj is not None:
                text_objects.append(symbol_obj)

            if text_obj is not None:
                text_objects.append(text_obj)
        else:
            text_width = len(cell) * height * TEXT_WIDTH_FACTOR
            text_x = x + max((cell_spans[index] - text_width) * 0.5, padding * 0.5)
            text_point = placement.multVec(FreeCAD.Vector(text_x, padding, 0))
            text_obj = make_basic_dimension_text(
                text_point,
                cell,
                height,
                rotation,
                "{}{:02d}".format(object_name, index + 1)
            )

            if text_obj is not None:
                text_objects.append(text_obj)

        x += cell_spans[index]

    return text_objects


def dimension_references_feature(dim_obj, controlled_obj, controlled_sub):
    if dim_obj is None or controlled_obj is None:
        return False

    for obj_prop, sub_prop in [
        ("ReferenceObject1", "ReferenceSubelement1"),
        ("ReferenceObject2", "ReferenceSubelement2"),
    ]:
        try:
            if (
                getattr(dim_obj, obj_prop, None) == controlled_obj
                and getattr(dim_obj, sub_prop, "") == controlled_sub
            ):
                return True
        except Exception:
            pass

    return False


def find_control_dimension_for_fcf(doc, fcf_obj):
    for obj in reversed(doc.Objects):
        if not hasattr(obj, "DimensionKind"):
            continue

        if dimension_references_feature(
            obj,
            fcf_obj.ControlledObject,
            fcf_obj.ControlledSubelement
        ):
            return obj

    return None


def fcf_origin_below_dimension(doc, fcf_obj, text_height, fallback_origin, fallback_rotation):
    dim_obj = find_control_dimension_for_fcf(doc, fcf_obj)

    if dim_obj is None:
        return fallback_origin, fallback_rotation

    try:
        dim_text = getattr(dim_obj, "DisplayText", None)

        if dim_text is not None:
            placement = dim_text.Placement
            rotation = placement.Rotation
            dim_origin = placement.Base
        else:
            dim_origin = FreeCAD.Vector(dim_obj.AnnotationOrigin)
            normal = FreeCAD.Vector(dim_obj.AnnotationNormal)
            direction = FreeCAD.Vector(dim_obj.AnnotationDirection)

            if normal.Length <= 1e-9 or direction.Length <= 1e-9:
                return fallback_origin, fallback_rotation

            normal.normalize()
            direction = direction - normal * direction.dot(normal)

            if direction.Length <= 1e-9:
                return fallback_origin, fallback_rotation

            direction.normalize()
            up = normal.cross(direction)

            if up.Length <= 1e-9:
                return fallback_origin, fallback_rotation

            up.normalize()
            rotation = FreeCAD.Rotation(direction, up, normal, "XYZ")

        if str(getattr(dim_obj, "DimensionKind", "")) == "Diameter":
            measurement = measurement_from_references(
                dim_obj.DimensionKind,
                dim_obj.MeasurementType,
                dim_obj.ReferenceObject1,
                dim_obj.ReferenceSubelement1,
                dim_obj.ReferenceObject2,
                dim_obj.ReferenceSubelement2
            )
            point1 = measurement.get("point1")
            point2 = measurement.get("point2")

            if point1 is not None and point2 is not None:
                x_axis = rotation.multVec(FreeCAD.Vector(1, 0, 0))
                y_axis = rotation.multVec(FreeCAD.Vector(0, 1, 0))
                right_point = point1

                if point2.dot(x_axis) > point1.dot(x_axis):
                    right_point = point2

                extension_line = (
                    dim_origin
                    + x_axis * (right_point - dim_origin).dot(x_axis)
                )
                frame_height = text_height * 1.6
                origin = extension_line - y_axis * frame_height
                return origin, rotation

        origin = dim_origin + rotation.multVec(
            FreeCAD.Vector(0, -text_height * 2.1, 0)
        )
        return origin, rotation
    except Exception:
        return fallback_origin, fallback_rotation


def create_fcf_display(doc, fcf_obj):
    point = referenced_subelement_center(
        fcf_obj.ControlledObject,
        fcf_obj.ControlledSubelement
    )
    normal = None
    position_cylinder = None

    if str(getattr(fcf_obj, "ToleranceType", "")) == "Position":
        position_cylinder = cylindrical_face_reference(
            fcf_obj.ControlledObject,
            fcf_obj.ControlledSubelement
        )

        if position_cylinder is not None:
            point = position_cylinder["point"]
            normal = position_cylinder.get("opening_direction")

    if (
        point is None
        and str(getattr(fcf_obj, "ToleranceType", "")) == "Profile"
        and getattr(fcf_obj, "ProfileAllOver", False)
    ):
        try:
            bbox = fcf_obj.ControlledObject.Shape.BoundBox
            preferred_point = FreeCAD.Vector(
                (bbox.XMin + bbox.XMax) * 0.5,
                (bbox.YMin + bbox.YMax) * 0.5,
                bbox.ZMax
            )
            point = nearest_point_on_shape(
                fcf_obj.ControlledObject,
                preferred_point
            )
            normal = FreeCAD.Vector(0, 0, 1)
        except Exception:
            point = None

    if point is None:
        return None

    if normal is None:
        normal = outward_normal_from_reference(
            doc,
            fcf_obj.ControlledObject,
            fcf_obj.ControlledSubelement
        )
    text_height = pmi_text_height(doc)
    display_direction = FreeCAD.Vector(0, 0, 1)

    if normal is not None:
        display_direction = FreeCAD.Vector(normal)

    offset = preferred_display_offset_beyond_model(
        doc,
        point,
        point,
        display_direction,
        text_height
    )

    if offset is None:
        _, doc_size = document_shape_center_and_size(doc)
        offset_length = min(max(doc_size * 0.9, 20.0), MAX_DISPLAY_OFFSET * 0.12)
        offset = FreeCAD.Vector(display_direction)

        if offset.Length <= 1e-9:
            offset = FreeCAD.Vector(0, 0, 1)

        offset.normalize()
        offset.multiply(offset_length)

    normal = display_direction

    frame_origin = point + offset
    cells = fcf_cells(fcf_obj)
    rotation = None

    if normal is not None:
        rotation = text_rotation_for_display_line(
            frame_origin,
            frame_origin + FreeCAD.Vector(1, 0, 0),
            normal
        )

    if str(fcf_obj.ToleranceType) == "Position":
        frame_origin, rotation = fcf_origin_below_dimension(
            doc,
            fcf_obj,
            text_height,
            frame_origin,
            rotation
        )

    plane_normal = (
        rotation.multVec(FreeCAD.Vector(0, 0, 1))
        if rotation else normal
    )
    reading_direction = (
        rotation.multVec(FreeCAD.Vector(1, 0, 0))
        if rotation else FreeCAD.Vector(1, 0, 0)
    )
    update_pmi_display_layout(
        fcf_obj,
        frame_origin,
        plane_normal,
        reading_direction,
        text_height
    )
    proxy = getattr(getattr(fcf_obj, "ViewObject", None), "Proxy", None)

    if hasattr(proxy, "rebuild"):
        proxy._suspend_rebuild = False
        clear_fcf_display_helpers(doc, fcf_obj)
        proxy.rebuild()
        return fcf_obj, None, None

    text_objects = make_fcf_cell_texts(
        doc,
        frame_origin,
        cells,
        text_height,
        rotation,
        fcf_obj.Name + "_Text"
    )
    frame_obj = make_fcf_frame(
        doc,
        frame_origin,
        cells,
        text_height,
        rotation,
        fcf_obj.Name + "_Frame"
    )
    leader_obj = make_line_feature(doc, point, frame_origin, fcf_obj.Name + "_Leader")
    text_obj = text_objects[0] if text_objects else None

    fcf_obj.DisplayText = text_obj
    fcf_obj.DisplayFrame = frame_obj
    fcf_obj.DisplayLeader = leader_obj
    add_display_children(fcf_obj, frame_obj, leader_obj, *text_objects)

    return frame_obj, text_obj, leader_obj


def datum_outward_normal(doc, datum_obj):
    surface = surface_from_datum_reference(datum_obj)

    if surface is None:
        return None

    normal = outward_normal_from_reference(
        doc,
        datum_obj.ReferencedObject,
        datum_obj.ReferencedSubelement
    )

    return normal


def text_rotation_for_display_line(p1_display, p2_display, outward_normal):
    if outward_normal is None or not finite_vector(outward_normal):
        return None

    normal = FreeCAD.Vector(outward_normal)

    if normal.Length <= 1e-9:
        return None

    normal.normalize()
    x_axis = p2_display - p1_display

    if x_axis.Length <= 1e-9:
        return None

    x_axis = x_axis - normal * x_axis.dot(normal)

    if x_axis.Length <= 1e-9:
        x_axis = normal.cross(FreeCAD.Vector(0, 0, 1))

        if x_axis.Length <= 1e-9:
            x_axis = normal.cross(FreeCAD.Vector(0, 1, 0))

    if x_axis.Length <= 1e-9:
        return None

    x_axis.normalize()

    dominant_axis = max(
        [
            (abs(x_axis.x), x_axis.x),
            (abs(x_axis.y), x_axis.y),
            (abs(x_axis.z), x_axis.z),
        ],
        key=lambda item: item[0]
    )

    if dominant_axis[1] < 0:
        x_axis = x_axis.negative()

    y_axis = normal.cross(x_axis)

    if y_axis.Length <= 1e-9:
        return None

    y_axis.normalize()

    return FreeCAD.Rotation(x_axis, y_axis, normal, "XYZ")


def datum_display_offset(doc, datum_obj, stack_index=0):
    surface = surface_from_datum_reference(datum_obj)
    doc_center, doc_size = document_shape_center_and_size(doc)
    offset_length = min(max(doc_size * 0.75, 15.0), MAX_DISPLAY_OFFSET * 0.1)
    stack_spacing = max(doc_size * 0.12, 3.0)

    if surface is None:
        return None

    try:
        u_min, u_max, v_min, v_max = surface.ParameterRange
        normal = surface.normalAt(
            (u_min + u_max) * 0.5,
            (v_min + v_max) * 0.5
        )
    except Exception:
        return None

    if normal.Length == 0:
        return None

    normal.normalize()

    try:
        surface_point = surface.CenterOfMass
    except Exception:
        surface_point = FreeCAD.Vector(0, 0, 0)

    if doc_center is not None and finite_vector(doc_center):
        if (surface_point - doc_center).dot(normal) < 0:
            normal = normal.negative()

    stack_direction = normal.cross(FreeCAD.Vector(0, 0, 1))

    if stack_direction.Length == 0:
        stack_direction = normal.cross(FreeCAD.Vector(0, 1, 0))

    if stack_direction.Length > 0:
        stack_direction.normalize()
        stack_direction.multiply(stack_spacing * stack_index)
    else:
        stack_direction = FreeCAD.Vector(0, 0, 0)

    return normal * offset_length + stack_direction


def datum_plane_display_offset(doc, datum_obj, p1, p2, stack_index=0):
    normal = datum_outward_normal(doc, datum_obj)
    doc_center, doc_size = document_shape_center_and_size(doc)
    offset_length = min(max(doc_size * 0.75, 15.0), MAX_DISPLAY_OFFSET * 0.1)
    text_height = max(offset_length * TEXT_HEIGHT_FACTOR, 3.0)
    stack_spacing = text_height * TEXT_STAGGER_FACTOR

    if normal is None:
        return None

    midpoint = p1 + ((p2 - p1) * 0.5)
    measured_direction = p2 - p1
    offset = FreeCAD.Vector(0, 0, 0)

    if measured_direction.Length > 0:
        measured_direction = measured_direction - normal * measured_direction.dot(normal)

    if measured_direction.Length > 0:
        offset = measured_direction.cross(normal)

    if offset.Length == 0:
        if doc_center is not None and finite_vector(doc_center):
            offset = midpoint - doc_center
            offset = offset - normal * offset.dot(normal)

    if offset.Length == 0:
        offset = normal.cross(FreeCAD.Vector(0, 0, 1))

    if offset.Length == 0:
        offset = normal.cross(FreeCAD.Vector(0, 1, 0))

    if offset.Length == 0:
        return None

    offset.normalize()

    if doc_center is not None and finite_vector(doc_center):
        center_vector = midpoint - doc_center
        center_vector = center_vector - normal * center_vector.dot(normal)

        if center_vector.Length > 0 and center_vector.dot(offset) < 0:
            offset = offset.negative()

    offset.multiply(offset_length + (stack_spacing * stack_index))

    return offset


def leader_direction_for_dimension(doc, datum_obj, p1, p2):
    normal = datum_outward_normal(doc, datum_obj)
    doc_center, _ = document_shape_center_and_size(doc)

    if normal is None:
        return None

    return leader_direction_for_points(doc, p1, p2, normal)


def leader_direction_for_points(doc, p1, p2, normal):
    doc_center, _ = document_shape_center_and_size(doc)

    if normal is None:
        return None

    measured_direction = p2 - p1

    if measured_direction.Length > 0:
        measured_direction = measured_direction - normal * measured_direction.dot(normal)

    leader = FreeCAD.Vector(0, 0, 0)

    if measured_direction.Length > 0:
        leader = measured_direction.cross(normal)

    midpoint = p1 + ((p2 - p1) * 0.5)

    if leader.Length == 0 and doc_center is not None and finite_vector(doc_center):
        leader = midpoint - doc_center
        leader = leader - normal * leader.dot(normal)

    if leader.Length == 0:
        leader = normal.cross(FreeCAD.Vector(0, 0, 1))

    if leader.Length == 0:
        leader = normal.cross(FreeCAD.Vector(0, 1, 0))

    if leader.Length == 0:
        return None

    leader.normalize()

    if doc_center is not None and finite_vector(doc_center):
        center_vector = midpoint - doc_center
        center_vector = center_vector - normal * center_vector.dot(normal)

        if center_vector.Length > 0 and center_vector.dot(leader) < 0:
            leader = leader.negative()

    return leader


def leader_direction_key(leader):
    if leader is None or not finite_vector(leader):
        return "Unknown"

    return (
        round(leader.x, 3),
        round(leader.y, 3),
        round(leader.z, 3),
    )


def model_extent_along(doc, leader):
    bbox = document_shape_bound_box(doc)

    if bbox is None:
        return 0.0

    return max_projection(bound_box_corners(bbox), leader)


def offset_beyond_current_extent(doc, p1, p2, leader, current_extent, text_height):
    current_dimension_extent = max_projection([p1, p2], leader)
    desired_extent = current_extent + (text_height * 2.0)
    offset_distance = desired_extent - current_dimension_extent

    if offset_distance < text_height * 2.0:
        offset_distance = text_height * 2.0
        desired_extent = current_dimension_extent + offset_distance

    return leader * offset_distance, desired_extent


def dimension_direction_key(doc, datum_obj, p1, p2):
    normal = datum_outward_normal(doc, datum_obj)
    direction = p2 - p1

    if direction.Length == 0:
        return "Unknown"

    if normal is not None and finite_vector(normal) and normal.Length > 0:
        normal = FreeCAD.Vector(normal)
        normal.normalize()
        direction = direction - normal * direction.dot(normal)

    if direction.Length == 0:
        direction = p2 - p1

    components = [
        ("X", abs(direction.x)),
        ("Y", abs(direction.y)),
        ("Z", abs(direction.z)),
    ]
    components.sort(key=lambda item: item[1], reverse=True)

    return components[0][0]


def staggered_offset_from_base(base_offset, stack_index, text_height=None):
    if base_offset is None or not finite_vector(base_offset):
        return None

    offset = FreeCAD.Vector(base_offset)

    if offset.Length == 0:
        return None

    if text_height is None:
        text_height = max(offset.Length * TEXT_HEIGHT_FACTOR, 3.0)

    stagger = text_height * TEXT_STAGGER_FACTOR * stack_index
    direction = FreeCAD.Vector(offset)
    direction.normalize()

    return offset + direction * stagger


def existing_basic_dimension_key(obj):
    refs = [
        (
            obj.ReferenceObject1.Name if obj.ReferenceObject1 else "",
            obj.ReferenceSubelement1,
        ),
        (
            obj.ReferenceObject2.Name if obj.ReferenceObject2 else "",
            obj.ReferenceSubelement2,
        ),
    ]
    refs.sort()
    return tuple(refs)


def basic_dimension_key(ref_obj_1, ref_sub_1, ref_obj_2, ref_sub_2):
    refs = [
        (ref_obj_1.Name if ref_obj_1 else "", ref_sub_1),
        (ref_obj_2.Name if ref_obj_2 else "", ref_sub_2),
    ]
    refs.sort()
    return tuple(refs)


def object_name_exists(doc, name):
    try:
        return doc.getObject(name) is not None
    except Exception:
        return False


def next_basic_dimension_name(doc):
    index = 1

    while True:
        name = "MBD_BasicDimension{:03d}".format(index)

        if not object_name_exists(doc, name):
            return name

        index += 1


def next_dimension_name(doc):
    index = 1

    while True:
        name = "MBD_Dimension{:03d}".format(index)

        if not object_name_exists(doc, name):
            return name

        index += 1


def create_dimension_object(
    doc,
    ref_obj_1,
    ref_sub_1,
    ref_obj_2=None,
    ref_sub_2="",
    nominal=None,
    dimension_purpose="EqualBilateral",
    dimension_kind="Linear",
    measurement_type="Distance",
    upper_tolerance=0.0,
    lower_tolerance=0.0,
    upper_limit=0.0,
    lower_limit=0.0,
    preferred_offset=None,
    text_normal=None,
    text_height=None,
    resolved_measurement=None
):
    timing_started = time.perf_counter()
    measurement = resolved_measurement

    if measurement is None:
        measurement = measurement_from_references(
            dimension_kind,
            measurement_type,
            ref_obj_1,
            ref_sub_1,
            ref_obj_2,
            ref_sub_2
        )
    measured = measurement.get("value")

    if measured is None:
        return None

    if nominal is None:
        nominal = measured

    dimension_name = next_dimension_name(doc)
    dim_obj = doc.addObject(
        "App::FeaturePython",
        dimension_name
    )

    if FreeCAD.GuiUp:
        ViewProviderMBDDimension(
            dim_obj.ViewObject,
            {
                "kind": str(dimension_kind),
                "label": "",
                "point1": measurement.get("point1"),
                "point2": measurement.get("point2"),
                "boxed": str(dimension_purpose) == "Basic",
            },
            suspend_rebuild=True
        )

    MBDDimension(dim_obj)
    dim_obj.Label = dim_obj.Name
    dim_obj.DimensionPurpose = str(dimension_purpose)
    dim_obj.DimensionKind = str(dimension_kind)
    dim_obj.MeasurementType = str(measurement_type)
    dim_obj.NominalValue = nominal
    dim_obj.MeasuredValue = measured
    dim_obj.UpperTolerance = upper_tolerance
    dim_obj.LowerTolerance = lower_tolerance
    dim_obj.UpperLimit = upper_limit
    dim_obj.LowerLimit = lower_limit
    dim_obj.ReferenceObject1 = ref_obj_1
    dim_obj.ReferenceSubelement1 = ref_sub_1
    dim_obj.ReferenceObject2 = ref_obj_2
    dim_obj.ReferenceSubelement2 = ref_sub_2
    dim_obj.ReferencePattern = measurement.get("pattern", "")
    dim_obj.ValidationMessage = measurement.get("message", "")
    timing_object_ready = time.perf_counter()

    if (
        str(dimension_kind) in ("Diameter", "Radius")
        or str(dim_obj.ReferencePattern) == "PlaneToPlane"
    ):
        dim_obj.AP242Entity = "DIMENSIONAL_SIZE"
    elif str(dimension_purpose) == "Basic":
        dim_obj.AP242Entity = "DIMENSIONAL_LOCATION"
    elif str(measurement_type) == "Distance":
        dim_obj.AP242Entity = "DIMENSIONAL_LOCATION"
    else:
        dim_obj.AP242Entity = "DIMENSIONAL_LOCATION"

    update_dimension_signature(dim_obj, measurement)
    append_pmi_history(dim_obj, "dimension-attached")
    add_to_mbd_pmi_group(doc, dim_obj)
    timing_metadata_ready = time.perf_counter()

    if FreeCAD.GuiUp:
        p1 = measurement.get("point1")
        p2 = measurement.get("point2")

        if p1 is not None and p2 is not None:
            measurement_text_normal = measurement.get("text_normal")
            display_direction = measurement.get("display_direction")

            if (
                text_normal is None
                and str(dimension_kind) == "Diameter"
            ):
                text_normal = diameter_annotation_plane_normal(
                    p1,
                    p2,
                    display_direction
                )

            if text_normal is None and measurement_text_normal is not None:
                text_normal = measurement_text_normal

            if text_height is None:
                text_height = pmi_text_height(doc)

            if preferred_offset is None:
                if (
                    display_direction is not None
                    and finite_vector(display_direction)
                ):
                    preferred_offset = preferred_display_offset_beyond_model(
                        doc,
                        p1,
                        p2,
                        display_direction,
                        text_height
                    )

                    if text_normal is None:
                        text_normal = FreeCAD.Vector(display_direction)
                elif text_normal is None:
                    preferred_offset, text_normal = display_context_for_dimension(
                        doc,
                        ref_obj_1,
                        ref_sub_1,
                        ref_obj_2,
                        ref_sub_2,
                        p1,
                        p2
                    )

            layout = dimension_display_layout(
                doc,
                p1,
                p2,
                dimension_display_label(dim_obj),
                str(dimension_kind),
                preferred_offset,
                text_normal,
                text_height
            )

            if layout is not None:
                update_pmi_display_layout(
                    dim_obj,
                    layout["origin"],
                    layout["normal"],
                    layout["direction"],
                    text_height
                )

        timing_layout_ready = time.perf_counter()
        activate_dimension_view_provider(
            doc,
            dim_obj,
            {
                "kind": str(dimension_kind),
                "label": dimension_display_label(dim_obj),
                "point1": measurement.get("point1"),
                "point2": measurement.get("point2"),
                "boxed": str(dimension_purpose) == "Basic",
            }
        )
        timing_provider_ready = time.perf_counter()

        if timing_provider_ready - timing_started > 1.0:
            FreeCAD.Console.PrintMessage(
                "Dimension creation phases for {}: object {:.3f}s, "
                "metadata {:.3f}s, layout {:.3f}s, provider {:.3f}s\n".format(
                    dim_obj.Name,
                    timing_object_ready - timing_started,
                    timing_metadata_ready - timing_object_ready,
                    timing_layout_ready - timing_metadata_ready,
                    timing_provider_ready - timing_layout_ready
                )
            )

    return dim_obj


def create_basic_dimension_object(
    doc,
    ref_obj_1,
    ref_sub_1,
    ref_obj_2,
    ref_sub_2,
    nominal=None,
    preferred_offset=None,
    text_normal=None,
    text_height=None,
    dimension_type="Distance"
):
    measured = measured_value_from_references(
        dimension_type,
        ref_obj_1,
        ref_sub_1,
        ref_obj_2,
        ref_sub_2
    )

    if measured is None:
        return None

    if nominal is None:
        nominal = measured

    dimension_name = next_basic_dimension_name(doc)
    dim_obj = doc.addObject(
        "App::FeaturePython",
        dimension_name
    )

    MBDBasicDimension(dim_obj)
    dim_obj.Label = dim_obj.Name
    dim_obj.DimensionType = str(dimension_type)
    dim_obj.NominalValue = nominal
    dim_obj.ReferenceObject1 = ref_obj_1
    dim_obj.ReferenceSubelement1 = ref_sub_1
    dim_obj.ReferenceObject2 = ref_obj_2
    dim_obj.ReferenceSubelement2 = ref_sub_2
    update_basic_dimension_signature(dim_obj)
    append_pmi_history(dim_obj, "basic-dimension-attached")
    add_to_mbd_pmi_group(doc, dim_obj)

    display_label = "{}".format(
        FreeCAD.Units.Quantity(
            nominal,
            FreeCAD.Units.Length
        ).UserString
    )

    if FreeCAD.GuiUp:
        if not hasattr(dim_obj, "addObject"):
            ViewProviderMBDBasicDimension(dim_obj.ViewObject)

        p1, p2 = display_points_from_references(
            ref_obj_1,
            ref_sub_1,
            ref_obj_2,
            ref_sub_2
        )

        if p1 is not None and p2 is not None:
            FreeCAD.Console.PrintMessage(
                "Basic dimension display endpoints: "
                "({:.6f}, {:.6f}, {:.6f}) to "
                "({:.6f}, {:.6f}, {:.6f})\n".format(
                    p1.x, p1.y, p1.z,
                    p2.x, p2.y, p2.z
                )
            )
            display_objects = make_basic_dimension_display(
                doc,
                p1,
                p2,
                display_label,
                preferred_offset,
                text_normal,
                dim_obj.Name,
                text_height
            )

            if display_objects is not None:
                display_geometry, display_text, display_text_box = display_objects[:3]
                extra_display_objects = display_objects[3:]
                dim_obj.DisplayDimension = display_geometry
                dim_obj.DisplayText = display_text
                dim_obj.DisplayTextBox = display_text_box

                try:
                    if display_geometry is not None:
                        dim_obj.addObject(display_geometry)
                        display_geometry.Label = display_geometry.Name

                    if display_text is not None:
                        dim_obj.addObject(display_text)
                        display_text.Label = dim_obj.Name + "_Text"

                    if display_text_box is not None:
                        dim_obj.addObject(display_text_box)
                        display_text_box.Label = display_text_box.Name

                    add_display_children(dim_obj, *extra_display_objects)
                except Exception:
                    pass

                dim_obj.Label = dim_obj.Name

        activate_dimension_view_provider(doc, dim_obj)

    return dim_obj


def create_basic_dimension_from_measurement(
    doc,
    ref_obj_1,
    ref_sub_1,
    ref_obj_2,
    ref_sub_2,
    measurement,
    nominal=None,
    preferred_offset=None,
    text_normal=None,
    text_height=None,
    dimension_type="Distance"
):
    measured = measurement.get("value")

    if measured is None:
        return None

    if nominal is None:
        nominal = measured

    dimension_name = next_basic_dimension_name(doc)
    dim_obj = doc.addObject(
        "App::DocumentObjectGroupPython",
        dimension_name
    )

    MBDBasicDimension(dim_obj)
    dim_obj.Label = dim_obj.Name
    dim_obj.DimensionType = str(dimension_type)
    dim_obj.NominalValue = nominal
    dim_obj.MeasuredValue = measured
    dim_obj.ReferenceObject1 = ref_obj_1
    dim_obj.ReferenceSubelement1 = ref_sub_1
    dim_obj.ReferenceObject2 = ref_obj_2
    dim_obj.ReferenceSubelement2 = ref_sub_2
    update_basic_dimension_signature(dim_obj)
    append_pmi_history(dim_obj, "basic-dimension-attached")
    add_to_mbd_pmi_group(doc, dim_obj)

    display_label = "{}".format(
        FreeCAD.Units.Quantity(
            nominal,
            FreeCAD.Units.Length
        ).UserString
    )

    if FreeCAD.GuiUp:
        if not hasattr(dim_obj, "addObject"):
            ViewProviderMBDBasicDimension(dim_obj.ViewObject)

        p1 = measurement.get("point1")
        p2 = measurement.get("point2")

        if p1 is not None and p2 is not None:
            FreeCAD.Console.PrintMessage(
                "Basic dimension display endpoints: "
                "({:.6f}, {:.6f}, {:.6f}) to "
                "({:.6f}, {:.6f}, {:.6f})\n".format(
                    p1.x, p1.y, p1.z,
                    p2.x, p2.y, p2.z
                )
            )
            display_objects = make_basic_dimension_display(
                doc,
                p1,
                p2,
                display_label,
                preferred_offset,
                text_normal,
                dim_obj.Name,
                text_height
            )

            if display_objects is not None:
                display_geometry, display_text, display_text_box = display_objects[:3]
                extra_display_objects = display_objects[3:]
                dim_obj.DisplayDimension = display_geometry
                dim_obj.DisplayText = display_text
                dim_obj.DisplayTextBox = display_text_box

                try:
                    if display_geometry is not None:
                        dim_obj.addObject(display_geometry)
                        display_geometry.Label = display_geometry.Name

                    if display_text is not None:
                        dim_obj.addObject(display_text)
                        display_text.Label = dim_obj.Name + "_Text"

                    if display_text_box is not None:
                        dim_obj.addObject(display_text_box)
                        display_text_box.Label = display_text_box.Name

                    add_display_children(dim_obj, *extra_display_objects)
                except Exception:
                    pass

                dim_obj.Label = dim_obj.Name

        activate_dimension_view_provider(doc, dim_obj)

    return dim_obj


def target_parent_datum_for_references(ref_obj_1, ref_obj_2):
    if hasattr(ref_obj_1, "ParentDatum") and ref_obj_1.ParentDatum is not None:
        return ref_obj_1.ParentDatum

    if hasattr(ref_obj_2, "ParentDatum") and ref_obj_2.ParentDatum is not None:
        return ref_obj_2.ParentDatum

    return None


class CreateDatumFeatureCommand:
    def GetResources(self):
        return {
            "MenuText": "Create Datum Feature",
            "ToolTip": "Create a semantic MBD datum feature from selected geometry",
            "Pixmap": command_icon("create_datum_feature.svg")
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        sel = FreeCADGui.Selection.getSelectionEx()

        if len(sel) != 1:
            QtGui.QMessageBox.warning(
                None,
                "MBD Datum Feature",
                "Select exactly one face, edge, or vertex."
            )
            return

        selection = sel[0]

        if not selection.SubElementNames:
            QtGui.QMessageBox.warning(
                None,
                "MBD Datum Feature",
                "Select a subelement such as a face, edge, or vertex."
            )
            return

        ref_obj = selection.Object
        ref_sub = selection.SubElementNames[0]

        used_labels = get_existing_datum_labels(doc)
        suggested_label = get_next_available_datum_label(doc)

        while True:
            label, ok = QtGui.QInputDialog.getText(
                None,
                "Datum Label",
                "Enter datum label:",
                text=suggested_label
            )

            if not ok:
                return

            label = str(label).strip().upper()

            if not label:
                QtGui.QMessageBox.warning(
                    None,
                    "MBD Datum Feature",
                    "Datum label cannot be blank."
                )
                continue

            if label in used_labels:
                QtGui.QMessageBox.warning(
                    None,
                    "MBD Datum Feature",
                    "Datum label {} is already used. Choose another label.".format(label)
                )
                continue

            break

        label = str(label).strip().upper()

        datum_obj = doc.addObject(
            "App::DocumentObjectGroupPython",
            "MBD_DatumFeature_" + label
        )
        MBDDatumFeature(datum_obj)

        datum_obj.DatumLabel = label
        datum_obj.ReferencedObject = ref_obj
        datum_obj.ReferencedSubelement = ref_sub
        update_geometry_signature(datum_obj)
        append_pmi_history(datum_obj, "datum-attached")
        add_to_mbd_pmi_group(doc, datum_obj)
        
        if ref_sub.startswith("Face"):
            datum_obj.DatumType = "Plane"
        elif ref_sub.startswith("Edge"):
            datum_obj.DatumType = "Axis"
        elif ref_sub.startswith("Vertex"):
            datum_obj.DatumType = "Point"
        else:
            datum_obj.DatumType = "Feature"

        if FreeCAD.GuiUp:
            set_default_datum_display_layout(doc, datum_obj)
            activate_datum_view_provider(doc, datum_obj)

        doc.recompute()

        FreeCAD.Console.PrintMessage(
            "Created MBD datum feature {} attached to {}.{}\n".format(
                label,
                ref_obj.Name,
                ref_sub
            )
        )


class ValidatePMICommand:
    def GetResources(self):
        return {
            "MenuText": "Validate PMI",
            "ToolTip": "Validate semantic MBD PMI objects",
            "Pixmap": command_icon("validate_pmi.svg")
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        report = MBDValidation.validate_document(FreeCAD.ActiveDocument)

        QtGui.QMessageBox.information(
            None,
            "MBD Validation Report",
            report
        )

class ShowPMIInspectorCommand:

    def GetResources(self):
        return {
            "MenuText": "Show PMI Inspector",
            "ToolTip": "Show semantic PMI inspector",
            "Pixmap": command_icon("show_pmi_inspector.svg")
        }

    def IsActive(self):
        return True

    def Activated(self):
        MBDInspector.show_inspector()


class CreateDatumTargetCommand:

    def GetResources(self):
        return {
            "MenuText": "Create Datum Target",
            "ToolTip": "Create a semantic point or line datum target",
            "Pixmap": command_icon("create_datum_target.svg")
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        selection = FreeCADGui.Selection.getSelectionEx()

        if len(selection) != 2:
            QtGui.QMessageBox.warning(
                None,
                "Datum Target",
                "Select one MBD datum feature and one construction point or straight edge."
            )
            return

        parent_datum = None
        construction_selection = None

        for item in selection:
            if hasattr(item.Object, "DatumLabel"):
                parent_datum = item.Object
            else:
                construction_selection = item

        if parent_datum is None or construction_selection is None:
            QtGui.QMessageBox.warning(
                None,
                "Datum Target",
                "Selection must include one MBD datum feature and one construction point or straight edge."
            )
            return

        if parent_datum.ReferencedObject is None or not parent_datum.ReferencedSubelement:
            QtGui.QMessageBox.warning(
                None,
                "Datum Target",
                "The parent datum must be attached to an inspected face."
            )
            return

        suggested_id = get_next_datum_target_id(doc, parent_datum)

        target_id, ok = QtGui.QInputDialog.getText(
            None,
            "Datum Target",
            "Enter datum target ID:",
            text=suggested_id
        )

        if not ok:
            return

        target_id = str(target_id).strip().upper()

        if not target_id:
            QtGui.QMessageBox.warning(
                None,
                "Datum Target",
                "Datum target ID cannot be blank."
            )
            return

        target_obj = doc.addObject(
            "App::DocumentObjectGroupPython",
            "MBD_DatumTarget_" + target_id
        )

        MBDDatumTarget(target_obj)

        target_obj.TargetId = target_id
        target_obj.ParentDatum = parent_datum
        target_obj.ConstructionObject = construction_selection.Object

        if construction_selection.SubElementNames:
            target_obj.ConstructionSubelement = construction_selection.SubElementNames[0]

        selected_shape = None

        try:
            if target_obj.ConstructionSubelement:
                selected_shape = construction_selection.Object.Shape.getElement(
                    target_obj.ConstructionSubelement
                )
            else:
                selected_shape = construction_selection.Object.Shape
        except Exception:
            pass

        line_geometry = None

        if getattr(selected_shape, "ShapeType", "") == "Edge":
            line_geometry = straight_edge_geometry(selected_shape)
        elif selected_shape is not None:
            try:
                if len(selected_shape.Edges) == 1:
                    line_geometry = straight_edge_geometry(
                        selected_shape.Edges[0]
                    )
            except Exception:
                pass

        if getattr(selected_shape, "ShapeType", "") == "Edge" and line_geometry is None:
            doc.removeObject(target_obj.Name)
            QtGui.QMessageBox.warning(
                None,
                "Datum Target",
                "A line datum target requires a straight construction edge."
            )
            return

        target_obj.TargetType = "Line" if line_geometry else "Point"
        target_obj.ReferencedObject = parent_datum.ReferencedObject
        target_obj.ReferencedSubelement = parent_datum.ReferencedSubelement

        update_datum_target_signature(target_obj)

        if not target_obj.GeometrySignatureValid:
            doc.removeObject(target_obj.Name)
            QtGui.QMessageBox.warning(
                None,
                "Datum Target",
                "The selected construction reference does not resolve to a supported point or straight line."
            )
            return

        if str(target_obj.TargetType) == "Line":
            distance = target_surface_distance(target_obj)

            if (
                distance is None
                or distance > float(target_obj.SurfaceTolerance)
            ):
                doc.removeObject(target_obj.Name)
                QtGui.QMessageBox.warning(
                    None,
                    "Datum Target",
                    "A line datum target must lie on the parent datum face. "
                    "The selected line is {:.6f} mm from {}.{}.".format(
                        distance if distance is not None else 0.0,
                        parent_datum.ReferencedObject.Name,
                        parent_datum.ReferencedSubelement
                    )
                )
                return

        append_pmi_history(target_obj, "datum-target-attached")
        add_to_mbd_pmi_group(doc, target_obj)

        if FreeCAD.GuiUp:
            ViewProviderMBDDatumTarget(target_obj.ViewObject)
            create_datum_target_display_text(doc, target_obj)

        doc.recompute()

        FreeCAD.Console.PrintMessage(
            "Created {} datum target {} for datum {} using {}\n".format(
                str(target_obj.TargetType).lower(),
                target_id,
                parent_datum.DatumLabel,
                construction_selection.Object.Name
            )
        )


class CreateDimensionCommand:

    def GetResources(self):
        return {
            "MenuText": "Create Dimension",
            "ToolTip": "Create a semantic AP242-ready dimension between two references",
            "Pixmap": command_icon("create_dimension.svg")
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        selection = FreeCADGui.Selection.getSelectionEx()
        references = expanded_selection_references(selection)

        if len(references) not in (1, 2):
            QtGui.QMessageBox.warning(
                None,
                "Dimension",
                "Select one cylindrical face for diameter/radius, or two compatible references for a linear dimension."
            )
            return

        ref1, subelement1 = references[0]
        ref_obj_1, sub1 = semantic_reference_for_subelement(
            doc,
            ref1,
            subelement1
        )
        ref_obj_2 = None
        sub2 = ""

        if len(references) == 2:
            ref2, subelement2 = references[1]
            ref_obj_2, sub2 = semantic_reference_for_subelement(
                doc,
                ref2,
                subelement2
            )

        purpose, ok = QtGui.QInputDialog.getItem(
            None,
            "Dimension",
            "Dimension purpose:",
            DIMENSION_PURPOSE_CHOICES,
            2,
            False
        )

        if not ok:
            return

        dimension_kind = "Linear"

        if len(references) == 1:
            dimension_kind, ok = QtGui.QInputDialog.getItem(
                None,
                "Dimension",
                "Dimension kind:",
                ["Diameter", "Radius"],
                0,
                False
            )

            if not ok:
                return

        measurement_type = "Distance"

        measurement_started = time.perf_counter()
        measurement = measurement_from_references(
            dimension_kind,
            measurement_type,
            ref_obj_1,
            sub1,
            ref_obj_2,
            sub2
        )
        measurement_elapsed = time.perf_counter() - measurement_started
        measured = measurement.get("value")

        if measured is None:
            QtGui.QMessageBox.warning(
                None,
                "Dimension",
                measurement.get(
                    "message",
                    "References must resolve to compatible dimension geometry."
                )
            )
            return

        measured_text = FreeCAD.Units.Quantity(
            measured,
            FreeCAD.Units.Length
        ).UserString
        nominal = measured

        upper_tolerance = 0.0
        lower_tolerance = 0.0
        upper_limit = nominal
        lower_limit = nominal

        if purpose == "EqualBilateral":
            tolerance_text, ok = QtGui.QInputDialog.getText(
                None,
                "Dimension",
                "Bilateral tolerance:",
                text=FreeCAD.Units.Quantity(0.0, FreeCAD.Units.Length).UserString
            )

            if not ok:
                return

            try:
                upper_tolerance = abs(
                    FreeCAD.Units.Quantity(str(tolerance_text)).Value
                )
                lower_tolerance = upper_tolerance
            except Exception:
                QtGui.QMessageBox.warning(
                    None,
                    "Dimension",
                    "Enter a tolerance value such as 0.005 in or 0.1 mm."
                )
                return

        if purpose == "UnequalBilateral":
            upper_text, ok = QtGui.QInputDialog.getText(
                None,
                "Dimension",
                "Upper tolerance:",
                text=FreeCAD.Units.Quantity(0.0, FreeCAD.Units.Length).UserString
            )

            if not ok:
                return

            lower_text, ok = QtGui.QInputDialog.getText(
                None,
                "Dimension",
                "Lower tolerance:",
                text=FreeCAD.Units.Quantity(0.0, FreeCAD.Units.Length).UserString
            )

            if not ok:
                return

            try:
                upper_tolerance = abs(
                    FreeCAD.Units.Quantity(str(upper_text)).Value
                )
                lower_tolerance = abs(
                    FreeCAD.Units.Quantity(str(lower_text)).Value
                )
            except Exception:
                QtGui.QMessageBox.warning(
                    None,
                    "Dimension",
                    "Enter tolerance values such as 0.005 in or 0.1 mm."
                )
                return

        if purpose == "Limits":
            lower_text, ok = QtGui.QInputDialog.getText(
                None,
                "Dimension",
                "Lower limit:",
                text=measured_text
            )

            if not ok:
                return

            upper_text, ok = QtGui.QInputDialog.getText(
                None,
                "Dimension",
                "Upper limit:",
                text=measured_text
            )

            if not ok:
                return

            try:
                lower_limit = FreeCAD.Units.Quantity(str(lower_text)).Value
                upper_limit = FreeCAD.Units.Quantity(str(upper_text)).Value
            except Exception:
                QtGui.QMessageBox.warning(
                    None,
                    "Dimension",
                    "Enter limit values such as 1.245 in or 31.6 mm."
                )
                return

        creation_started = time.perf_counter()
        dim_obj = create_dimension_object(
            doc,
            ref_obj_1,
            sub1,
            ref_obj_2,
            sub2,
            nominal=nominal,
            dimension_purpose=str(purpose),
            dimension_kind=str(dimension_kind),
            measurement_type=str(measurement_type),
            upper_tolerance=upper_tolerance,
            lower_tolerance=lower_tolerance,
            upper_limit=upper_limit,
            lower_limit=lower_limit,
            resolved_measurement=measurement
        )
        creation_elapsed = time.perf_counter() - creation_started

        if dim_obj is None:
            QtGui.QMessageBox.warning(
                None,
                "Dimension",
                "Could not create the dimension."
            )
            return

        FreeCAD.Console.PrintMessage(
            "Created dimension {} between {} and {} "
            "(geometry {:.3f}s, creation {:.3f}s)\n".format(
                dim_obj.Name,
                ref_obj_1.Name,
                ref_obj_2.Name if ref_obj_2 else "<none>",
                measurement_elapsed,
                creation_elapsed
            )
        )


def choose_datum_system_compartments(datum_objects, initial_datums=None):
    dialog = QtGui.QDialog()
    dialog.setWindowTitle("Create Datum System")
    layout = QtGui.QVBoxLayout(dialog)
    layout.addWidget(QtGui.QLabel(
        "Select one or more datum features in each compartment. "
        "Multiple selections in one compartment form a common datum."
    ))

    initial_datums = list(initial_datums or [])
    list_widgets = []

    for compartment_index, (_prop_name, role_name) in enumerate(
        DATUM_COMPARTMENT_PROPERTIES
    ):
        group_box = QtGui.QGroupBox(role_name)
        group_layout = QtGui.QVBoxLayout(group_box)
        list_widget = QtGui.QListWidget()
        list_widget.setSelectionMode(
            QtGui.QAbstractItemView.ExtendedSelection
        )

        for datum in datum_objects:
            list_widget.addItem(
                "{} ({})".format(datum.Label, datum.DatumLabel)
            )

        if compartment_index < len(initial_datums):
            initial_datum = initial_datums[compartment_index]

            for row, datum in enumerate(datum_objects):
                if datum == initial_datum:
                    list_widget.item(row).setSelected(True)
                    break

        group_layout.addWidget(list_widget)
        layout.addWidget(group_box)
        list_widgets.append(list_widget)

    buttons = QtGui.QDialogButtonBox(
        QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec_() != QtGui.QDialog.Accepted:
        return None

    compartments = []

    for list_widget in list_widgets:
        selected_rows = sorted(
            list_widget.row(item)
            for item in list_widget.selectedItems()
        )
        compartments.append([
            datum_objects[row]
            for row in selected_rows
        ])

    return compartments


class CreateDatumSystemCommand:

    def GetResources(self):
        return {
            "MenuText": "Create Datum System",
            "ToolTip": "Create a semantic datum system from selected datum features",
            "Pixmap": command_icon("create_datum_system.svg")
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):

        doc = FreeCAD.ActiveDocument
        datum_objects = sorted(
            get_datum_feature_objects(doc),
            key=lambda datum: str(datum.DatumLabel)
        )

        if not datum_objects:
            QtGui.QMessageBox.warning(
                None,
                "Datum System",
                "Create at least one datum feature before creating a datum system."
            )
            return

        initial_datums = [
            obj for obj in FreeCADGui.Selection.getSelection()
            if obj in datum_objects
        ][:3]
        compartments = choose_datum_system_compartments(
            datum_objects,
            initial_datums
        )

        if compartments is None:
            return

        primary, secondary, tertiary = compartments

        if not primary:
            QtGui.QMessageBox.warning(
                None,
                "Datum System",
                "The primary datum-reference compartment cannot be empty."
            )
            return

        if tertiary and not secondary:
            QtGui.QMessageBox.warning(
                None,
                "Datum System",
                "Define a secondary compartment before defining a tertiary compartment."
            )
            return

        all_datums = primary + secondary + tertiary

        if len(all_datums) != len(set(datum.Name for datum in all_datums)):
            QtGui.QMessageBox.warning(
                None,
                "Datum System",
                "A datum feature cannot appear in more than one compartment."
            )
            return

        compartment_labels = [
            datum_compartment_label(datums)
            for datums in compartments
            if datums
        ]
        requested_name = "MBD_DatumSystem_" + "_".join(compartment_labels)

        ds_obj = doc.addObject(
            "App::FeaturePython",
            requested_name
        )

        MBDDatumSystem(ds_obj)
        add_to_mbd_pmi_group(doc, ds_obj)
        ds_obj.PrimaryDatums = primary
        ds_obj.SecondaryDatums = secondary
        ds_obj.TertiaryDatums = tertiary
        ds_obj.Label = datum_system_object_label(ds_obj)

        if FreeCAD.GuiUp:
            ViewProviderMBDDatumSystem(ds_obj.ViewObject)

        doc.recompute()

        FreeCAD.Console.PrintMessage(
            "Created datum system: {}\n".format(
                datum_system_label(ds_obj)
            )
        )

class CreateFeatureControlFrameCommand:

    def GetResources(self):
        return {
            "MenuText": "Create Feature Control Frame",
            "ToolTip": "Create semantic feature control frame",
            "Pixmap": command_icon("create_feature_control_frame.svg")
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):

        doc = FreeCAD.ActiveDocument

        sel = FreeCADGui.Selection.getSelectionEx()

        tolerance_types = [
            "Position",
            "Flatness",
            "Parallelism",
            "Perpendicularity",
            "Angularity",
            "Straightness",
            "Circularity",
            "Cylindricity",
            "CircularRunout",
            "TotalRunout",
            "LineProfile",
            "Profile"
        ]

        tolerance_type, ok = QtGui.QInputDialog.getItem(
            None,
            "Feature Control Frame",
            "Select tolerance type:",
            tolerance_types,
            0,
            False
        )

        if not ok:
            return

        tolerance_type = str(tolerance_type)
        profile_all_over = False

        if tolerance_type == "Profile":
            reply = QtGui.QMessageBox.question(
                None,
                "Profile Scope",
                "Apply this profile tolerance all over?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.No
            )
            profile_all_over = reply == QtGui.QMessageBox.Yes

        controlled_obj = None
        controlled_sub = ""

        if profile_all_over:
            if len(sel) == 0:
                controlled_obj = single_body_level_fcf_candidate(doc)

                if controlled_obj is None:
                    QtGui.QMessageBox.warning(
                        None,
                        "Feature Control Frame",
                        "Select one body, or leave nothing selected only when the document has exactly one body."
                    )
                    return
            elif len(sel) == 1:
                controlled_obj = sel[0].Object

                if not body_level_fcf_candidate(controlled_obj):
                    QtGui.QMessageBox.warning(
                        None,
                        "Feature Control Frame",
                        "All-over profile must be attached to a body or solid."
                    )
                    return
            else:
                QtGui.QMessageBox.warning(
                    None,
                    "Feature Control Frame",
                    "Select one body for all-over profile, or leave nothing selected when there is only one body."
                )
                return
        else:
            if len(sel) != 1:

                QtGui.QMessageBox.warning(
                    None,
                    "Feature Control Frame",
                    "Select exactly one controlled feature."
                )

                return

            selection = sel[0]

            if not selection.SubElementNames:

                QtGui.QMessageBox.warning(
                    None,
                    "Feature Control Frame",
                    "Select a subelement such as a face or edge."
                )

                return

            controlled_obj = selection.Object
            controlled_sub = selection.SubElementNames[0]

        if (
            tolerance_type in (
                "Flatness",
                "Parallelism",
                "Perpendicularity",
                "Angularity",
                "Circularity",
                "Cylindricity",
                "CircularRunout",
                "TotalRunout",
                "Profile"
            )
            and not profile_all_over
            and not controlled_sub.startswith("Face")
        ):
            QtGui.QMessageBox.warning(
                None,
                "Feature Control Frame",
                "{} must be attached to a face or surface.".format(
                    tolerance_type
                )
            )
            return

        if (
            tolerance_type == "LineProfile"
            and not controlled_sub.startswith("Edge")
        ):
            QtGui.QMessageBox.warning(
                None,
                "Feature Control Frame",
                "Line profile must be attached to an edge or curve."
            )
            return

        tolerance_text, ok = QtGui.QInputDialog.getText(
            None,
            "Tolerance Value",
            "Enter tolerance value with units:",
            text="0.005 in"
        )

        if not ok:
            return

        try:
            tolerance = parse_length_quantity_text(tolerance_text)
        except Exception:
            QtGui.QMessageBox.warning(
                None,
                "Tolerance Value",
                "Enter a tolerance with units, such as 0.005 in or 0.1 mm."
            )
            return

        datum_system = None
        datum_reference = None

        if tolerance_type == "Position":
            datum_systems = get_datum_system_objects(doc)

            if not datum_systems:
                QtGui.QMessageBox.warning(
                    None,
                    "Feature Control Frame",
                    "No datum systems exist."
                )
                return

            names = [obj.Label for obj in datum_systems]

            ds_name, ok = QtGui.QInputDialog.getItem(
                None,
                "Datum System",
                "Select datum system:",
                names,
                0,
                False
            )

            if not ok:
                return

            datum_system = datum_systems[names.index(str(ds_name))]

        if tolerance_type in ("Profile", "LineProfile"):
            datum_systems = get_datum_system_objects(doc)
            names = ["<none>"] + [obj.Label for obj in datum_systems]

            ds_name, ok = QtGui.QInputDialog.getItem(
                None,
                "Datum System",
                "Select datum system:",
                names,
                0,
                False
            )

            if not ok:
                return

            if str(ds_name) != "<none>":
                datum_system = datum_systems[
                    names.index(str(ds_name)) - 1
                ]

        if tolerance_type in (
            "Parallelism",
            "Perpendicularity",
            "Angularity"
        ):
            datum_features = get_datum_feature_objects(doc)
            datum_systems = get_datum_system_objects(doc)
            choices = []

            for obj in datum_features:
                choices.append((
                    "{} ({})".format(obj.Name, obj.DatumLabel),
                    obj,
                    None
                ))

            for obj in datum_systems:
                choices.append((
                    obj.Label,
                    None,
                    obj
                ))

            if not choices:
                QtGui.QMessageBox.warning(
                    None,
                    "Feature Control Frame",
                    "No datum features or datum systems exist."
                )
                return

            names = [choice[0] for choice in choices]

            datum_name, ok = QtGui.QInputDialog.getItem(
                None,
                "Datum Reference",
                "Select datum feature or datum system:",
                names,
                0,
                False
            )

            if not ok:
                return

            _label, datum_reference, datum_system = choices[
                names.index(str(datum_name))
            ]

        if tolerance_type in ("CircularRunout", "TotalRunout"):
            datum_features = get_datum_feature_objects(doc)
            datum_systems = get_datum_system_objects(doc)

            choices = []

            for obj in datum_features:
                choices.append((
                    "{} ({})".format(obj.Name, obj.DatumLabel),
                    obj,
                    None
                ))

            for obj in datum_systems:
                choices.append((
                    obj.Label,
                    None,
                    obj
                ))

            if not choices:
                QtGui.QMessageBox.warning(
                    None,
                    "Feature Control Frame",
                    "No datum features or datum systems exist."
                )
                return

            names = [choice[0] for choice in choices]

            datum_name, ok = QtGui.QInputDialog.getItem(
                None,
                "Datum Reference",
                "Select datum feature or datum system:",
                names,
                0,
                False
            )

            if not ok:
                return

            _label, datum_reference, datum_system = choices[
                names.index(str(datum_name))
            ]

        fcf_obj = doc.addObject(
            "App::FeaturePython",
            "MBD_FCF_" + tolerance_type
        )

        if FreeCAD.GuiUp:
            ViewProviderMBDFeatureControlFrame(
                fcf_obj.ViewObject,
                suspend_rebuild=True
            )

        MBDFeatureControlFrame(fcf_obj)

        fcf_obj.ToleranceType = tolerance_type
        fcf_obj.ToleranceValue = tolerance
        fcf_obj.DiameterZone = tolerance_type == "Position"
        fcf_obj.ProfileAllOver = profile_all_over
        fcf_obj.DatumSystem = datum_system
        fcf_obj.DatumReference = datum_reference

        fcf_obj.ControlledObject = controlled_obj
        fcf_obj.ControlledSubelement = controlled_sub
        fcf_obj.ReferencedObject = controlled_obj
        fcf_obj.ReferencedSubelement = controlled_sub
        update_geometry_signature(fcf_obj)
        append_pmi_history(fcf_obj, "fcf-attached")
        add_to_mbd_pmi_group(doc, fcf_obj)

        if FreeCAD.GuiUp:
            create_fcf_display(doc, fcf_obj)

        doc.recompute()

        FreeCAD.Console.PrintMessage(
            "Created {} tolerance on {}{}\n".format(
                tolerance_type.lower(),
                controlled_obj.Name,
                ".{}".format(controlled_sub) if controlled_sub else ""
            )
        )


class CreateGDTSymbolTableCommand:

    def GetResources(self):
        return {
            "MenuText": "Create GD&T Symbol Table",
            "ToolTip": "Create a visible test table for GD&T symbol rendering",
            "Pixmap": command_icon("create_gdt_symbol_table.svg")
        }

    def IsActive(self):
        return True

    def Activated(self):
        group = create_geometric_tolerance_symbol_table(FreeCAD.ActiveDocument)

        if FreeCAD.GuiUp and group is not None:
            QtGui.QMessageBox.information(
                None,
                "GD&T Symbol Table",
                "Created GD&T symbol rendering table."
            )


class ExportAP242Command:

    def GetResources(self):
        return {
            "MenuText": "Export AP242",
            "ToolTip": "Export AP242 STEP with semantic infrastructure",
            "Pixmap": command_icon("export_ap242.svg")
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):

        filename, _ = QtGui.QFileDialog.getSaveFileName(
            None,
            "Export AP242",
            "",
            "STEP Files (*.step *.stp)"
        )

        if not filename:
            return

        try:

            MBDExporter.export_ap242(filename)

            QtGui.QMessageBox.information(
                None,
                "AP242 Export",
                "Export complete."
            )

        except Exception as e:

            QtGui.QMessageBox.critical(
                None,
                "AP242 Export Failed",
                str(e)
            )

if hasattr(FreeCADGui, "addCommand"):
    FreeCADGui.addCommand("MBD_CreateDatumFeature", CreateDatumFeatureCommand())
    FreeCADGui.addCommand("MBD_ValidatePMI", ValidatePMICommand())
    FreeCADGui.addCommand(
        "MBD_ShowPMIInspector",
        ShowPMIInspectorCommand()
    )
    FreeCADGui.addCommand(
        "MBD_CreateDatumTarget",
        CreateDatumTargetCommand()
    )
    FreeCADGui.addCommand(
        "MBD_CreateDimension",
        CreateDimensionCommand()
    )
    FreeCADGui.addCommand(
        "MBD_CreateDatumSystem",
        CreateDatumSystemCommand()
    )
    FreeCADGui.addCommand(
        "MBD_CreateFeatureControlFrame",
        CreateFeatureControlFrameCommand()
    )
    FreeCADGui.addCommand(
        "MBD_CreateGDTSymbolTable",
        CreateGDTSymbolTableCommand()
    )
    FreeCADGui.addCommand(
        "MBD_ExportAP242",
        ExportAP242Command()
    )
