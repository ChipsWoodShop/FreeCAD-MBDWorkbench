# MBDCommands.py

import FreeCAD
import FreeCADGui
from PySide import QtGui

from MBDDatum import MBDDatumFeature, ViewProviderMBDDatumFeature
import MBDValidation
from MBDDatum import (
    MBDDatumFeature,
    ViewProviderMBDDatumFeature,
    update_geometry_signature
)
import MBDInspector
from MBDDatumSystem import (
    MBDDatumSystem,
    ViewProviderMBDDatumSystem
)
from MBDFeatureControlFrame import (
    MBDFeatureControlFrame,
    ViewProviderMBDFeatureControlFrame
)
VALID_DATUM_LETTERS = [
    "A","B","C","D","E","F","G","H",
    "J","K","L","M","N",
    "P","R","S","T","U","V","W","Y"
]

def get_existing_datum_labels(doc):
    labels = set()

    for obj in doc.Objects:
        if hasattr(obj, "IsSemanticPMI") and hasattr(obj, "DatumLabel"):
            labels.add(obj.DatumLabel.strip().upper())

    return labels


def get_next_available_datum_label(doc):

    used = get_existing_datum_labels(doc)

    # Single-letter labels
    for letter in VALID_DATUM_LETTERS:
        if letter not in used:
            return letter

    # Double-letter labels
    for first in VALID_DATUM_LETTERS:
        for second in VALID_DATUM_LETTERS:

            label = first + second

            if label not in used:
                return label

    raise Exception("Ran out of datum labels.")

def get_datum_system_objects(doc):

    systems = []

    for obj in doc.Objects:

        if hasattr(obj, "PrimaryDatum"):
            systems.append(obj)

    return systems
class CreateDatumFeatureCommand:
    def GetResources(self):
        return {
            "MenuText": "Create Datum Feature",
            "ToolTip": "Create a semantic MBD datum feature from selected geometry",
            "Pixmap": ""
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        sel = FreeCADGui.Selection.getSelectionEx()

        if len(sel) != 1:
            QtGui.QMessageBox.warning(
                None,
                "MBD Datum Feature",
                "Select exactly one face, edge, or vertex."
            )
            return

        selection = sel[0]

        if not selection.SubElementNames:
            QtGui.QMessageBox.warning(
                None,
                "MBD Datum Feature",
                "Select a subelement such as a face, edge, or vertex."
            )
            return

        ref_obj = selection.Object
        ref_sub = selection.SubElementNames[0]

        used_labels = get_existing_datum_labels(doc)
        suggested_label = get_next_available_datum_label(doc)

        while True:
            label, ok = QtGui.QInputDialog.getText(
                None,
                "Datum Label",
                "Enter datum label:",
                text=suggested_label
            )

            if not ok:
                return

            label = str(label).strip().upper()

            if not label:
                QtGui.QMessageBox.warning(
                    None,
                    "MBD Datum Feature",
                    "Datum label cannot be blank."
                )
                continue

            if label in used_labels:
                QtGui.QMessageBox.warning(
                    None,
                    "MBD Datum Feature",
                    "Datum label {} is already used. Choose another label.".format(label)
                )
                continue

            break

        label = str(label).strip().upper()

        datum_obj = doc.addObject("App::FeaturePython", "MBD_DatumFeature_" + label)
        MBDDatumFeature(datum_obj)

        datum_obj.DatumLabel = label
        datum_obj.ReferencedObject = ref_obj
        datum_obj.ReferencedSubelement = ref_sub
        update_geometry_signature(datum_obj)
        
        if ref_sub.startswith("Face"):
            datum_obj.DatumType = "Plane"
        elif ref_sub.startswith("Edge"):
            datum_obj.DatumType = "Axis"
        elif ref_sub.startswith("Vertex"):
            datum_obj.DatumType = "Point"
        else:
            datum_obj.DatumType = "Feature"

        if FreeCAD.GuiUp:
            ViewProviderMBDDatumFeature(datum_obj.ViewObject)

        doc.recompute()

        FreeCAD.Console.PrintMessage(
            "Created MBD datum feature {} attached to {}.{}\n".format(
                label,
                ref_obj.Name,
                ref_sub
            )
        )


class ValidatePMICommand:
    def GetResources(self):
        return {
            "MenuText": "Validate PMI",
            "ToolTip": "Validate semantic MBD PMI objects",
            "Pixmap": ""
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        report = MBDValidation.validate_document(FreeCAD.ActiveDocument)

        QtGui.QMessageBox.information(
            None,
            "MBD Validation Report",
            report
        )

class ShowPMIInspectorCommand:

    def GetResources(self):
        return {
            "MenuText": "Show PMI Inspector",
            "ToolTip": "Show semantic PMI inspector",
            "Pixmap": ""
        }

    def IsActive(self):
        return True

    def Activated(self):
        MBDInspector.show_inspector()

class CreateDatumSystemCommand:

    def GetResources(self):
        return {
            "MenuText": "Create Datum System",
            "ToolTip": "Create a semantic datum system from selected datum features",
            "Pixmap": ""
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):

        doc = FreeCAD.ActiveDocument

        selection = FreeCADGui.Selection.getSelection()

        if len(selection) < 1 or len(selection) > 3:

            QtGui.QMessageBox.warning(
                None,
                "Datum System",
                "Select 1 to 3 datum features in precedence order."
            )

            return

        datum_objects = []

        for obj in selection:

            if not hasattr(obj, "IsSemanticPMI"):

                QtGui.QMessageBox.warning(
                    None,
                    "Datum System",
                    "{} is not semantic PMI.".format(obj.Name)
                )

                return

            if not hasattr(obj, "DatumLabel"):

                QtGui.QMessageBox.warning(
                    None,
                    "Datum System",
                    "{} is not a datum feature.".format(obj.Name)
                )

                return

            datum_objects.append(obj)

        labels = [obj.DatumLabel for obj in datum_objects]

        if len(labels) != len(set(labels)):

            QtGui.QMessageBox.warning(
                None,
                "Datum System",
                "Duplicate datums are not allowed in a datum system."
            )

            return

        name = "MBD_DatumSystem"

        if len(labels) > 0:
            name += "_" + "_".join(labels)

        ds_obj = doc.addObject(
            "App::FeaturePython",
            name
        )

        MBDDatumSystem(ds_obj)

        if len(datum_objects) >= 1:
            ds_obj.PrimaryDatum = datum_objects[0]

        if len(datum_objects) >= 2:
            ds_obj.SecondaryDatum = datum_objects[1]

        if len(datum_objects) >= 3:
            ds_obj.TertiaryDatum = datum_objects[2]

        if FreeCAD.GuiUp:
            ViewProviderMBDDatumSystem(ds_obj.ViewObject)

        doc.recompute()

        FreeCAD.Console.PrintMessage(
            "Created datum system: {}\n".format(
                " | ".join(labels)
            )
        )

class CreateFeatureControlFrameCommand:

    def GetResources(self):
        return {
            "MenuText": "Create Feature Control Frame",
            "ToolTip": "Create semantic feature control frame",
            "Pixmap": ""
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):

        doc = FreeCAD.ActiveDocument

        sel = FreeCADGui.Selection.getSelectionEx()

        if len(sel) != 1:

            QtGui.QMessageBox.warning(
                None,
                "Feature Control Frame",
                "Select exactly one controlled feature."
            )

            return

        selection = sel[0]

        if not selection.SubElementNames:

            QtGui.QMessageBox.warning(
                None,
                "Feature Control Frame",
                "Select a subelement such as a face or edge."
            )

            return

        controlled_obj = selection.Object
        controlled_sub = selection.SubElementNames[0]

        datum_systems = get_datum_system_objects(doc)

        if not datum_systems:

            QtGui.QMessageBox.warning(
                None,
                "Feature Control Frame",
                "No datum systems exist."
            )

            return

        tolerance, ok = QtGui.QInputDialog.getDouble(
            None,
            "Tolerance Value",
            "Enter tolerance value:",
            0.1,
            0.0001,
            9999,
            4
        )

        if not ok:
            return

        names = [obj.Name for obj in datum_systems]

        ds_name, ok = QtGui.QInputDialog.getItem(
            None,
            "Datum System",
            "Select datum system:",
            names,
            0,
            False
        )

        if not ok:
            return

        datum_system = doc.getObject(ds_name)

        fcf_obj = doc.addObject(
            "App::FeaturePython",
            "MBD_FCF_Position"
        )

        MBDFeatureControlFrame(fcf_obj)

        fcf_obj.ToleranceType = "Position"
        fcf_obj.ToleranceValue = tolerance

        fcf_obj.DatumSystem = datum_system

        fcf_obj.ControlledObject = controlled_obj
        fcf_obj.ControlledSubelement = controlled_sub

        if FreeCAD.GuiUp:
            ViewProviderMBDFeatureControlFrame(
                fcf_obj.ViewObject
            )

        doc.recompute()

        FreeCAD.Console.PrintMessage(
            "Created position tolerance on {}.{}\n".format(
                controlled_obj.Name,
                controlled_sub
            )
        )

FreeCADGui.addCommand("MBD_CreateDatumFeature", CreateDatumFeatureCommand())
FreeCADGui.addCommand("MBD_ValidatePMI", ValidatePMICommand())
FreeCADGui.addCommand(
    "MBD_ShowPMIInspector",
    ShowPMIInspectorCommand()
)
FreeCADGui.addCommand(
    "MBD_CreateDatumSystem",
    CreateDatumSystemCommand()
)
FreeCADGui.addCommand(
    "MBD_CreateFeatureControlFrame",
    CreateFeatureControlFrameCommand()
)