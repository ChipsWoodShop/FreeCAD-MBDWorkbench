# MBDFeatureControlFrame.py

import FreeCAD

from MBDPMI import ensure_pmi_identity


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
            "Position"
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
            "App::PropertyLink",
            "DatumSystem",
            "MBD_FCF",
            "Referenced datum system"
        )

        obj.addProperty(
            "App::PropertyLink",
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
        
        obj.addProperty(
            "App::PropertyLink",
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


class ViewProviderMBDFeatureControlFrame:

    def __init__(self, vobj):
        vobj.Proxy = self
