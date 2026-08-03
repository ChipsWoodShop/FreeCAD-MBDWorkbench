"""FreeCAD MBD Workbench GUI registration shim."""

from freecad.mbd_workbench.InitGui import MBDWorkbench

try:
    import FreeCADGui

    if hasattr(FreeCADGui, "addWorkbench"):
        FreeCADGui.addWorkbench(MBDWorkbench())
except Exception:
    # Let FreeCAD surface import errors normally when a real GUI session loads
    # the workbench; this guard keeps non-GUI metadata/tooling imports harmless.
    raise
