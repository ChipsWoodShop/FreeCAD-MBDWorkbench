# MBDDatumSystem.py

import FreeCAD


class MBDDatumSystem:

    def __init__(self, obj):

        obj.Proxy = self

        obj.addProperty(
            "App::PropertyLink",
            "PrimaryDatum",
            "MBDDatumSystem",
            "Primary datum feature"
        )

        obj.addProperty(
            "App::PropertyLink",
            "SecondaryDatum",
            "MBDDatumSystem",
            "Secondary datum feature"
        )

        obj.addProperty(
            "App::PropertyLink",
            "TertiaryDatum",
            "MBDDatumSystem",
            "Tertiary datum feature"
        )

        obj.addProperty(
            "App::PropertyString",
            "Standard",
            "MBDDatumSystem",
            "GD&T standard"
        )

        obj.Standard = "ASME Y14.5"

        obj.addProperty(
            "App::PropertyBool",
            "IsSemanticPMI",
            "MBDDatumSystem",
            "Semantic PMI marker"
        )

        obj.IsSemanticPMI = True

    def execute(self, obj):
        pass


class ViewProviderMBDDatumSystem:

    def __init__(self, vobj):
        vobj.Proxy = self