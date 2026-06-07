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
            "MBD_CreateDatumTarget",
            "MBD_CreateDimension",
            "MBD_CreateDatumSystem",
            "MBD_CreateFeatureControlFrame",
            "MBD_CreateGDTSymbolTable",
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
            "MBD_CreateGDTSymbolTable",
            "MBD_ExportAP242",
        ])

    def Activated(self):
        FreeCAD.Console.PrintMessage("MBD Workbench activated\n")

        try:
            import MBDCommands
            from MBDPMI import migrate_semantic_pmi_global_links

            if FreeCAD.ActiveDocument is not None:
                migrated = migrate_semantic_pmi_global_links(
                    FreeCAD.ActiveDocument
                )

                if migrated:
                    FreeCAD.Console.PrintMessage(
                        "Updated {} MBD geometry links to global scope.\n".format(
                            len(migrated)
                        )
                    )

                MBDCommands.organize_pmi_tree(FreeCAD.ActiveDocument)
        except Exception as e:
            FreeCAD.Console.PrintWarning(
                "Could not organize MBD PMI tree: {}\n".format(e)
            )

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"

FreeCADGui.addWorkbench(MBDWorkbench())
