# MBDFeatureControlFrame.py

import FreeCAD


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

    def execute(self, obj):
        pass


class ViewProviderMBDFeatureControlFrame:

    def __init__(self, vobj):
        vobj.Proxy = self