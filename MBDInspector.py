# MBDInspector.py

import FreeCAD
import FreeCADGui

from PySide import QtGui
from PySide import QtCore


class MBDInspectorWidget(QtGui.QWidget):

    def __init__(self):
        super(MBDInspectorWidget, self).__init__()

        self.setWindowTitle("MBD PMI Inspector")

        layout = QtGui.QVBoxLayout()

        self.table = QtGui.QTableWidget()
        self.table.setColumnCount(7)

        self.table.setHorizontalHeaderLabels([
            "Datum",
            "Reference",
            "Geometry",
            "Area",
            "Perimeter",
            "Edge Length",
            "Center"
        ])

        layout.addWidget(self.table)

        refresh_button = QtGui.QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)

        layout.addWidget(refresh_button)

        self.setLayout(layout)

        self.refresh()

    def refresh(self):

        doc = FreeCAD.ActiveDocument

        if doc is None:
            self.table.setRowCount(0)
            return

        datum_objects = []

        for obj in doc.Objects:

            if hasattr(obj, "IsSemanticPMI"):

                if hasattr(obj, "DatumLabel"):

                    datum_objects.append(obj)

        self.table.setRowCount(len(datum_objects))

        for row, obj in enumerate(datum_objects):

            reference = ""

            if obj.ReferencedObject:
                reference = "{}.{}".format(
                    obj.ReferencedObject.Name,
                    obj.ReferencedSubelement
                )

            center = ""

            if hasattr(obj, "CenterOfMass"):
                c = obj.CenterOfMass
                center = "({:.3f}, {:.3f}, {:.3f})".format(
                    c.x,
                    c.y,
                    c.z
                )

            area = getattr(obj, "Area", 0.0)
            perimeter = getattr(obj, "FacePerimeter", 0.0)
            edge_length = getattr(obj, "EdgeLength", 0.0)
            geom_type = getattr(obj, "GeometryType", "")

            values = [
                obj.DatumLabel,
                reference,
                geom_type,
                "{:.3f}".format(area),
                "{:.3f}".format(perimeter),
                "{:.3f}".format(edge_length),
                center
            ]

            for col, val in enumerate(values):

                item = QtGui.QTableWidgetItem(str(val))
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()


dock_widget = None


def show_inspector():

    global dock_widget

    mw = FreeCADGui.getMainWindow()

    if dock_widget is None:

        dock_widget = QtGui.QDockWidget("MBD PMI Inspector")
        dock_widget.setObjectName("MBDPMIInspector")

        inspector = MBDInspectorWidget()
        dock_widget.setWidget(inspector)

        mw.addDockWidget(
            QtCore.Qt.RightDockWidgetArea,
            dock_widget
        )

    dock_widget.show()