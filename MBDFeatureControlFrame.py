# MBDFeatureControlFrame.py

import FreeCAD

from MBDPMI import ensure_global_link_property, ensure_pmi_identity
from MBDViewProvider import ViewProviderSingleItemFCF


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
        obj.addProperty(
            "App::PropertyLink",
            "DisplayFrame",
            "MBD_FCF",
            "Optional visible feature control frame helper"
        )

        obj.addProperty(
            "App::PropertyLink",
            "DisplayText",
            "MBD_FCF",
            "Optional visible feature control frame text helper"
        )

        obj.addProperty(
            "App::PropertyLink",
            "DisplayLeader",
            "MBD_FCF",
            "Optional visible feature control frame leader helper"
        )
        ensure_pmi_identity(obj, "fcf-created")
    def execute(self, obj):
        pass


class ViewProviderMBDFeatureControlFrame(ViewProviderSingleItemFCF):
    pass
