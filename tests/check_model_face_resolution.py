#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path


WORKBENCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH_DIR))

import FreeCAD

from freecad.mbd_workbench import MBDExporter
from freecad.mbd_workbench.MBDDatum import update_geometry_signature


class AcceptMessageBox:
    Warning = 1
    Yes = 1
    Cancel = 2

    def setIcon(self, *args):
        pass

    def setWindowTitle(self, *args):
        pass

    def setText(self, *args):
        pass

    def setInformativeText(self, *args):
        pass

    def setStandardButtons(self, *args):
        pass

    def exec_(self):
        return self.Yes


def find_body(doc):
    body = doc.getObject("Body")

    if body is None:
        raise RuntimeError("Body object not found")

    return body


def find_fcf(doc):
    for obj in doc.Objects:
        if hasattr(obj, "ToleranceType") and hasattr(obj, "ControlledSubelement"):
            return obj

    raise RuntimeError("MBD FCF object not found")


def has_null_ref(path):
    if not path.exists():
        return False

    return "NUL REF" in path.read_text(errors="replace")


def check_faces(model_path, output_dir):
    MBDExporter.QtGui.QMessageBox = AcceptMessageBox
    doc = FreeCAD.openDocument(str(model_path))
    body = find_body(doc)
    fcf = find_fcf(doc)

    output_dir.mkdir(parents=True, exist_ok=True)

    face_count = len(body.Shape.Faces)
    results = []

    original_diameter_zone = fcf.DiameterZone
    fcf.DiameterZone = False

    for index in range(1, face_count + 1):
        subelement = "Face{}".format(index)
        output_path = output_dir / "face_resolution_{}.step".format(subelement)

        if output_path.exists():
            os.remove(str(output_path))

        fcf.ControlledObject = body
        fcf.ControlledSubelement = subelement
        fcf.ReferencedObject = body
        fcf.ReferencedSubelement = subelement
        update_geometry_signature(fcf)
        doc.recompute()

        status = "ok"

        try:
            MBDExporter.export_ap242(str(output_path))
        except Exception as exc:
            status = "error: {}".format(exc)

        if has_null_ref(output_path):
            status = "null-ref"

        exists = output_path.exists()
        size = output_path.stat().st_size if exists else 0
        results.append((subelement, status, size))

    fcf.DiameterZone = original_diameter_zone
    FreeCAD.closeDocument(doc.Name)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/mbd_face_resolution")
    )
    args = parser.parse_args()

    results = check_faces(args.model, args.output_dir)

    for subelement, status, size in results:
        print("{} {} size={}".format(subelement, status, size))

    return 0


if __name__ == "__main__":
    sys.exit(main())
