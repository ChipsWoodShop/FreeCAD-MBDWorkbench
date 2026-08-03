"""Headless check for the packaged MBD workbench layout."""

import os
import sys


WORKBENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if WORKBENCH_DIR not in sys.path:
    sys.path.insert(0, WORKBENCH_DIR)

import FreeCAD
import FreeCADGui

from freecad.mbd_workbench import MBDCommands
from freecad.mbd_workbench.InitGui import MBDWorkbench


def main():
    icon_path = MBDCommands.command_icon("create_datum_feature.svg")

    if not os.path.exists(icon_path):
        raise RuntimeError("Expected command icon at {}".format(icon_path))

    workbench = MBDWorkbench()

    if workbench.GetClassName() != "Gui::PythonWorkbench":
        raise RuntimeError("Unexpected workbench class name.")

    if FreeCAD.ActiveDocument is None:
        FreeCAD.newDocument("MBDPackageLayoutSmoke")

    print("MBD package layout smoke passed.")
    print("Icon path: {}".format(icon_path))
    print("Workbench class: {}".format(workbench.__class__.__name__))
    print("FreeCADGui.addCommand available: {}".format(
        hasattr(FreeCADGui, "addCommand")
    ))


main()
