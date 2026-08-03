# MBDFeatureControlFrame.py

import FreeCAD

from .MBDPMI import ensure_global_link_property, ensure_pmi_identity
from .MBDViewProvider import ViewProviderSingleItemFCF


def add_property_if_missing(obj, prop_type, name, group, description):
    if hasattr(obj, name):
        return

    obj.addProperty(
        prop_type,
        name,
        group,
        description
    )


class MBDFeatureControlFrame:

    def __init__(self, obj):

        obj.Proxy = self

        obj.addProperty(
            "App::PropertyEnumeration",
            "ToleranceType",
            "MBD_FCF",
            "Type of geometric tolerance"
        )

        obj.ToleranceType = [
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

        obj.addProperty(
            "App::PropertyFloat",
            "ToleranceValue",
            "MBD_FCF",
            "Tolerance value"
        )

        obj.ToleranceValue = 0.1

        obj.addProperty(
            "App::PropertyBool",
            "DiameterZone",
            "MBD_FCF",
            "Tolerance zone is diametrical"
        )

        obj.DiameterZone = True

        obj.addProperty(
            "App::PropertyBool",
            "ProfileAllOver",
            "MBD_FCF",
            "Profile tolerance applies all over the part"
        )

        obj.ProfileAllOver = False

        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "MaterialConditionModifier",
            "MBD_FCF",
            "Tolerance material condition modifier"
        )
        obj.MaterialConditionModifier = ["None", "MMC", "LMC"]

        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "ProjectedToleranceZone",
            "MBD_FCF",
            "Tolerance zone is projected"
        )
        obj.ProjectedToleranceZone = False

        add_property_if_missing(
            obj,
            "App::PropertyLength",
            "ProjectedToleranceHeight",
            "MBD_FCF",
            "Projected tolerance zone height"
        )

        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "UnequallyDisposedZone",
            "MBD_FCF",
            "Profile tolerance zone is unequally disposed"
        )
        obj.UnequallyDisposedZone = False

        add_property_if_missing(
            obj,
            "App::PropertyLength",
            "UnequallyDisposedOffset",
            "MBD_FCF",
            "Unequally disposed profile offset"
        )

        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "TangentPlaneModifier",
            "MBD_FCF",
            "Include tangent plane modifier"
        )
        obj.TangentPlaneModifier = False

        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "StatisticalToleranceModifier",
            "MBD_FCF",
            "Include statistical tolerance modifier"
        )
        obj.StatisticalToleranceModifier = False

        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "CommonZoneModifier",
            "MBD_FCF",
            "Include common zone modifier"
        )
        obj.CommonZoneModifier = False

        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "MaximumToleranceValueEnabled",
            "MBD_FCF",
            "Include maximum tolerance value"
        )
        obj.MaximumToleranceValueEnabled = False

        add_property_if_missing(
            obj,
            "App::PropertyLength",
            "MaximumToleranceValue",
            "MBD_FCF",
            "Maximum tolerance value"
        )

        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "UnitBasisToleranceEnabled",
            "MBD_FCF",
            "Include unit-basis tolerance"
        )
        obj.UnitBasisToleranceEnabled = False

        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "UnitBasisType",
            "MBD_FCF",
            "Unit-basis tolerance area type"
        )
        obj.UnitBasisType = ["Length", "Circular", "Square", "Rectangular"]

        add_property_if_missing(
            obj,
            "App::PropertyLength",
            "UnitBasisPrimaryLength",
            "MBD_FCF",
            "Unit-basis primary length"
        )

        add_property_if_missing(
            obj,
            "App::PropertyLength",
            "UnitBasisSecondaryLength",
            "MBD_FCF",
            "Unit-basis secondary length"
        )

        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "NonUniformToleranceZone",
            "MBD_FCF",
            "Include non-uniform tolerance zone"
        )
        obj.NonUniformToleranceZone = False

        obj.addProperty(
            "App::PropertyLink",
            "DatumSystem",
            "MBD_FCF",
            "Referenced datum system"
        )

        obj.addProperty(
            "App::PropertyLink",
            "DatumReference",
            "MBD_FCF",
            "Single referenced datum feature"
        )

        ensure_global_link_property(
            obj,
            "ControlledObject",
            "MBD_FCF",
            "Controlled geometry object"
        )

        obj.addProperty(
            "App::PropertyString",
            "ControlledSubelement",
            "MBD_FCF",
            "Controlled subelement"
        )

        add_property_if_missing(
            obj,
            "App::PropertyStringList",
            "ControlledSubelementList",
            "MBD_FCF",
            "All controlled subelements for imported multi-geometry tolerances"
        )

        ensure_global_link_property(
            obj,
            "ProfileDirectionObject",
            "MBD_FCF",
            "Optional section/direction line for profile of a line"
        )

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "ProfileDirectionSubelement",
            "MBD_FCF",
            "Optional section/direction subelement for profile of a line"
        )

        ensure_global_link_property(
            obj,
            "AffectedPlaneObject",
            "MBD_FCF",
            "Datum line or line element defining the affected plane"
        )

        add_property_if_missing(
            obj,
            "App::PropertyString",
            "AffectedPlaneSubelement",
            "MBD_FCF",
            "Subelement defining the affected plane line"
        )

        add_property_if_missing(
            obj,
            "App::PropertyAngle",
            "RunoutOrientationAngle",
            "MBD_FCF",
            "Runout zone orientation angle"
        )
        
        ensure_global_link_property(
            obj,
            "ReferencedObject",
            "MBD",
            "Object used for generic PMI geometry validation"
        )

        obj.addProperty(
            "App::PropertyString",
            "ReferencedSubelement",
            "MBD",
            "Subelement used for generic PMI geometry validation"
        )

        obj.addProperty(
            "App::PropertyVector",
            "CenterOfMass",
            "GeometrySignature",
            "Center of mass of referenced geometry"
        )

        obj.addProperty(
            "App::PropertyFloat",
            "Area",
            "GeometrySignature",
            "Area of referenced face"
        )

        obj.addProperty(
            "App::PropertyFloat",
            "FacePerimeter",
            "GeometrySignature",
            "Perimeter of referenced face"
        )

        obj.addProperty(
            "App::PropertyFloat",
            "EdgeLength",
            "GeometrySignature",
            "Length of referenced edge"
        )

        obj.addProperty(
            "App::PropertyString",
            "GeometryType",
            "GeometrySignature",
            "Underlying geometry type"
        )
        obj.addProperty(
            "App::PropertyBool",
            "IsSemanticPMI",
            "MBD_FCF",
            "Semantic PMI marker"
        )

        obj.IsSemanticPMI = True

        obj.addProperty(
            "App::PropertyString",
            "Standard",
            "MBD_FCF",
            "GD&T standard"
        )

        obj.Standard = "ASME Y14.5"
        obj.addProperty(
            "App::PropertyString",
            "GeometrySignature",
            "MBD",
            "Stored geometric signature of referenced feature"
        )

        obj.addProperty(
            "App::PropertyBool",
            "GeometrySignatureValid",
            "MBD",
            "Whether current referenced geometry matches stored signature"
        )
        obj.GeometrySignatureValid = True
        ensure_pmi_identity(obj, "fcf-created")
    def execute(self, obj):
        pass


class ViewProviderMBDFeatureControlFrame(ViewProviderSingleItemFCF):
    pass
