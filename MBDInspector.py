# MBDInspector.py

import FreeCAD
import FreeCADGui

from PySide import QtGui
from PySide import QtCore

import MBDValidation


STATUS_COLORS = {
    "OK": QtGui.QColor(232, 245, 233),
    "Warning": QtGui.QColor(255, 248, 225),
    "Error": QtGui.QColor(255, 235, 238),
}


def set_item_status_style(item, status):
    color = STATUS_COLORS.get(status, QtGui.QColor(255, 255, 255))

    try:
        item.setBackground(QtGui.QBrush(color))
    except Exception:
        try:
            item.setBackgroundColor(color)
        except Exception:
            pass

    try:
        item.setForeground(QtGui.QBrush(QtGui.QColor(0, 0, 0)))
    except Exception:
        pass


class MBDInspectorWidget(QtGui.QWidget):

    def __init__(self):
        super(MBDInspectorWidget, self).__init__()

        self.setWindowTitle("MBD PMI Inspector")
        self.rows = []

        layout = QtGui.QVBoxLayout()

        self.summary_label = QtGui.QLabel("")
        layout.addWidget(self.summary_label)

        self.table = QtGui.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)

        self.table.setHorizontalHeaderLabels([
            "Status",
            "Type",
            "Name",
            "PMI ID",
            "Attachment",
            "Geometry",
            "Message"
        ])

        layout.addWidget(self.table)

        button_row = QtGui.QHBoxLayout()

        refresh_button = QtGui.QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)
        button_row.addWidget(refresh_button)

        select_button = QtGui.QPushButton("Select")
        select_button.clicked.connect(self.select_current)
        button_row.addWidget(select_button)

        suspect_button = QtGui.QPushButton("Select Suspect")
        suspect_button.clicked.connect(self.select_suspect)
        button_row.addWidget(suspect_button)

        copy_button = QtGui.QPushButton("Copy Report")
        copy_button.clicked.connect(self.copy_report)
        button_row.addWidget(copy_button)

        clear_button = QtGui.QPushButton("Clear")
        clear_button.clicked.connect(FreeCADGui.Selection.clearSelection)
        button_row.addWidget(clear_button)

        layout.addLayout(button_row)
        self.setLayout(layout)

        self.refresh()

    def refresh(self):
        doc = FreeCAD.ActiveDocument

        self.rows = []

        if doc is None:
            self.summary_label.setText("No active document")
            self.table.setRowCount(0)
            return

        report = MBDValidation.validate_document_structured(doc)
        issues_by_object = {}

        for issue in report["issues"]:
            if issue.obj is None:
                continue

            issues_by_object.setdefault(issue.obj.Name, []).append(issue)

        pmi_objects = []
        pmi_objects.extend(report["datums"])
        pmi_objects.extend(report["datum_targets"])
        pmi_objects.extend(report["basic_dimensions"])
        pmi_objects.extend(report["dimensions"])
        pmi_objects.extend(report["datum_systems"])
        pmi_objects.extend(report["fcfs"])

        self.table.setRowCount(len(pmi_objects))

        error_count = len([
            issue for issue in report["issues"]
            if issue.severity == "error"
        ])
        warning_count = len([
            issue for issue in report["issues"]
            if issue.severity == "warning"
        ])

        self.summary_label.setText(
            "Datums: {}   Targets: {}   Basics: {}   Dimensions: {}   Datum systems: {}   FCFs: {}   Errors: {}   Warnings: {}".format(
                len(report["datums"]),
                len(report["datum_targets"]),
                len(report["basic_dimensions"]),
                len(report["dimensions"]),
                len(report["datum_systems"]),
                len(report["fcfs"]),
                error_count,
                warning_count
            )
        )

        for row, obj in enumerate(pmi_objects):
            issues = issues_by_object.get(obj.Name, [])
            status = "OK"

            if any(issue.severity == "error" for issue in issues):
                status = "Error"
            elif issues:
                status = "Warning"

            message = "; ".join([issue.message for issue in issues])

            values = [
                status,
                MBDValidation.pmi_type(obj),
                obj.Name,
                getattr(obj, "PMIId", ""),
                MBDValidation.attachment_text(obj),
                MBDValidation.fcf_geometry_text(obj)
                    if MBDValidation.is_mbd_fcf(obj)
                    else getattr(obj, "GeometryType", ""),
                message,
            ]

            for col, value in enumerate(values):
                item = QtGui.QTableWidgetItem(str(value))
                set_item_status_style(item, status)
                self.table.setItem(row, col, item)

            self.rows.append({
                "object": obj,
                "status": status,
                "issues": issues,
            })

        self.table.resizeColumnsToContents()

    def report_text(self):
        lines = []
        lines.append(self.summary_label.text())
        lines.append("")

        headers = []

        for col in range(self.table.columnCount()):
            header = self.table.horizontalHeaderItem(col)
            headers.append(header.text() if header else "")

        lines.append("\t".join(headers))

        for row in range(self.table.rowCount()):
            values = []

            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                values.append(item.text() if item else "")

            lines.append("\t".join(values))

        return "\n".join(lines)

    def copy_report(self):
        self.refresh()

        clipboard = QtGui.QApplication.clipboard()
        clipboard.setText(self.report_text())

        FreeCAD.Console.PrintMessage(
            "Copied MBD PMI Inspector report to clipboard.\n"
        )

    def selected_row_indices(self):
        rows = set()

        for index in self.table.selectionModel().selectedRows():
            rows.add(index.row())

        return sorted(rows)

    def select_current(self):
        FreeCADGui.Selection.clearSelection()

        for row in self.selected_row_indices():
            self.select_row(row)

    def select_suspect(self):
        FreeCADGui.Selection.clearSelection()

        for row, data in enumerate(self.rows):
            if data["status"] != "OK":
                self.select_row(row)

    def select_row(self, row):
        if row < 0 or row >= len(self.rows):
            return

        obj = self.rows[row]["object"]
        FreeCADGui.Selection.addSelection(obj)

        target_obj = None
        subelement = ""

        if hasattr(obj, "ControlledObject") and obj.ControlledObject:
            target_obj = obj.ControlledObject
            subelement = obj.ControlledSubelement
        elif hasattr(obj, "ReferencedObject") and obj.ReferencedObject:
            target_obj = obj.ReferencedObject
            subelement = obj.ReferencedSubelement

        if target_obj is None:
            return

        try:
            FreeCADGui.Selection.addSelection(
                FreeCAD.ActiveDocument.Name,
                target_obj.Name,
                subelement
            )
        except Exception:
            FreeCADGui.Selection.addSelection(target_obj)


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
    else:
        inspector = dock_widget.widget()

        if inspector is not None and hasattr(inspector, "refresh"):
            inspector.refresh()

    dock_widget.show()
