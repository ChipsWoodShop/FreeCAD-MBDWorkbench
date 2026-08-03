"""Profile the slow NIST STC10 AP242 import/export smoke phases.

This is intentionally separate from the pass/fail smoke test.  It writes a
timestamped progress log to /tmp so a hung FreeCAD/AppImage run still leaves
evidence about the last completed phase.
"""

import os
import sys
import tempfile
import time
import traceback


WORKBENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if WORKBENCH_DIR not in sys.path:
    sys.path.insert(0, WORKBENCH_DIR)

import FreeCAD

from freecad.mbd_workbench import MBDCommands
from freecad.mbd_workbench import MBDExporter
from freecad.mbd_workbench import MBDImporter
from freecad.mbd_workbench import MBDValidation


def import_step_geometry(doc, filename):
    try:
        import ImportGui
        ImportGui.insert(filename, doc.Name)
        return
    except Exception:
        pass

    try:
        import Import
        before_docs = set(FreeCAD.listDocuments().keys())
        before_object_names = {obj.Name for obj in doc.Objects}
        imported_doc = Import.open(filename)
        imported_objects = []

        if isinstance(imported_doc, list):
            imported_objects = imported_doc
            imported_doc = None

        if imported_doc is None:
            active_doc = FreeCAD.ActiveDocument

            if active_doc is not None and active_doc.Name not in before_docs:
                imported_doc = active_doc

        imported_into_active_doc = (
            imported_doc is None
            and any(obj.Name not in before_object_names for obj in doc.Objects)
        )

        if imported_objects:
            FreeCAD.setActiveDocument(doc.Name)

            for imported_obj in imported_objects:
                if isinstance(imported_obj, tuple):
                    imported_obj = next(
                        (
                            item
                            for item in imported_obj
                            if hasattr(item, "Shape")
                        ),
                        None
                    )

                    if imported_obj is None:
                        continue

                if not hasattr(imported_obj, "Shape"):
                    continue

                copied = doc.addObject("Part::Feature", imported_obj.Name)
                copied.Shape = imported_obj.Shape
        elif imported_doc is not None and imported_doc is not doc:
            FreeCAD.setActiveDocument(doc.Name)

            for imported_obj in list(imported_doc.Objects):
                if not hasattr(imported_obj, "Shape"):
                    continue

                copied = doc.addObject("Part::Feature", imported_obj.Name)
                copied.Shape = imported_obj.Shape

            FreeCAD.closeDocument(imported_doc.Name)
        elif imported_into_active_doc:
            return
        else:
            Import.insert(filename, doc.Name)

        return
    except Exception:
        pass

    import Part
    shape = Part.open(filename)

    if shape is None:
        raise RuntimeError("Part.open returned no shape for {}".format(filename))

    shape_obj = doc.addObject("Part::Feature", "ImportedShape")
    shape_obj.Shape = shape


DEFAULT_STEP = (
    "/home/chip/Projects/FreeCAD MBD/NIST-PMI-STEP-Files/"
    "nist_stc_10_asme1_ap242-e2.stp"
)
LOG_PATH = os.path.join(tempfile.gettempdir(), "mbd_stc10_phase_profile.log")


def log(message):
    line = "{:.3f} {}\n".format(time.perf_counter(), message)

    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()

    FreeCAD.Console.PrintMessage(line)


def main():
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)

    filename = os.path.abspath(
        sys.argv[sys.argv.index("--") + 1]
        if "--" in sys.argv and sys.argv.index("--") + 1 < len(sys.argv)
        else DEFAULT_STEP
    )
    started = time.perf_counter()
    log("start {}".format(filename))
    doc = FreeCAD.newDocument("STC10PhaseProfile")

    try:
        before_names = {obj.Name for obj in doc.Objects}
        log("before geometry import")
        import_step_geometry(doc, filename)
        log("after geometry import {:.3f}s".format(time.perf_counter() - started))

        doc.recompute()
        log("after import recompute {:.3f}s".format(time.perf_counter() - started))

        shape_objects = MBDCommands.importable_shape_objects(doc, before_names)
        log("after shape lookup count={} {:.3f}s".format(
            len(shape_objects),
            time.perf_counter() - started
        ))

        if not shape_objects:
            raise RuntimeError("No imported shape object was found.")

        preview = MBDImporter.semantic_import_preview(filename)
        log("after semantic preview {:.3f}s".format(time.perf_counter() - started))

        result = MBDImporter.create_native_datums_and_systems_from_preview(
            doc,
            shape_objects[0],
            preview
        )
        log("after native PMI creation {:.3f}s".format(time.perf_counter() - started))

        MBDCommands.organize_pmi_tree(doc)
        log("after tree organization {:.3f}s".format(time.perf_counter() - started))

        doc.recompute()
        log("after native recompute {:.3f}s".format(time.perf_counter() - started))

        validation_report = MBDValidation.validate_document_structured(doc)
        errors = [
            issue
            for issue in validation_report.get("issues", [])
            if issue.severity == "error"
        ]
        log("after validation errors={} {:.3f}s".format(
            len(errors),
            time.perf_counter() - started
        ))

        output_path = os.path.join(
            tempfile.gettempdir(),
            "mbd_stc10_phase_profile.step"
        )

        if os.path.exists(output_path):
            os.remove(output_path)

        FreeCAD.setActiveDocument(doc.Name)
        ok = MBDExporter.export_ap242(output_path)
        log("after export ok={} exists={} {:.3f}s".format(
            ok,
            os.path.exists(output_path),
            time.perf_counter() - started
        ))

        created = result["created"]
        log(
            "created datums={} targets={} systems={} dimensions={} fcfs={}".format(
                len(created.get("datums", [])),
                len(created.get("datum_targets", [])),
                len(created.get("datum_systems", [])),
                len(created.get("dimensions", [])),
                len(created.get("fcfs", [])),
            )
        )
        log("done total {:.3f}s".format(time.perf_counter() - started))
    finally:
        FreeCAD.closeDocument(doc.Name)


try:
    main()
except Exception:
    log("exception")
    traceback.print_exc()
    raise
