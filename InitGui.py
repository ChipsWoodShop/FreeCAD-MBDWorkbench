# InitGui.py

import FreeCAD
import FreeCADGui

class MBDWorkbench(FreeCADGui.Workbench):
    MenuText = "MBD"
    ToolTip = "Model-Based Definition workbench for semantic PMI and AP242 export"
    Icon = ""

    def Initialize(self):
        import MBDCommands

        self.appendToolbar("MBD Tools", [
            "MBD_CreateDatumFeature",
            "MBD_ValidatePMI",
            "MBD_ShowPMIInspector",
            "MBD_CreateDatumSystem",
            "MBD_CreateFeatureControlFrame",
            "MBD_ExportAP242",
        ])

        self.appendMenu("MBD", [
            "MBD_CreateDatumFeature",
            "MBD_ValidatePMI",
            "MBD_ShowPMIInspector",
            "MBD_CreateDatumSystem",
            "MBD_CreateFeatureControlFrame",
            "MBD_ExportAP242",
        ])

    def Activated(self):
        FreeCAD.Console.PrintMessage("MBD Workbench activated\n")

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"

FreeCADGui.addWorkbench(MBDWorkbench())
