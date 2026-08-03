# InitGui.py

import FreeCAD
import FreeCADGui

WorkbenchBase = getattr(FreeCADGui, "Workbench", object)


class MBDWorkbench(WorkbenchBase):
    MenuText = "MBD"
    ToolTip = "Model-Based Definition workbench for semantic PMI and AP242 export"
    Icon = ""

    def Initialize(self):
        from . import MBDCommands

        self.appendToolbar("MBD Tools", [
            "MBD_CreateDatumFeature",
            "MBD_ValidatePMI",
            "MBD_ShowPMIInspector",
            "MBD_CreateDatumTarget",
            "MBD_CreateDimension",
            "MBD_CreateDatumSystem",
            "MBD_CreateFeatureControlFrame",
            "MBD_InspectAP242PMI",
            "MBD_ImportAP242PMI",
            "MBD_ExportAP242",
        ])

        self.appendMenu("MBD", [
            "MBD_CreateDatumFeature",
            "MBD_ValidatePMI",
            "MBD_ShowPMIInspector",
            "MBD_CreateDatumTarget",
            "MBD_CreateDimension",
            "MBD_CreateDatumSystem",
            "MBD_CreateFeatureControlFrame",
            "MBD_InspectAP242PMI",
            "MBD_ImportAP242PMI",
            "MBD_ExportAP242",
        ])

    def Activated(self):
        FreeCAD.Console.PrintMessage("MBD Workbench activated\n")

        try:
            from . import MBDCommands

            if FreeCAD.ActiveDocument is not None:
                MBDCommands.organize_pmi_tree(FreeCAD.ActiveDocument)
        except Exception as e:
            FreeCAD.Console.PrintWarning(
                "Could not organize MBD PMI tree: {}\n".format(e)
            )

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"
