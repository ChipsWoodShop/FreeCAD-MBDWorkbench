"""Headless AP242 import-then-export smoke test.

Run with FreeCADCmd, for example:

    FreeCADCmd tests/freecad_ap242_import_export_smoke.py -- /path/to/file.stp

This covers checks that do not need a human GUI pass: STEP import, semantic PMI
preview, native datum/datum-target/datum-system creation, AP242 re-export, and
basic STEP text sanity checks for null semantic references.
"""

import os
import re
import sys
import tempfile
import time
import traceback


WORKBENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if WORKBENCH_DIR not in sys.path:
    sys.path.insert(0, WORKBENCH_DIR)

import FreeCAD
import Part

from freecad.mbd_workbench import MBDCommands
from freecad.mbd_workbench import MBDExporter
from freecad.mbd_workbench import MBDImporter
from freecad.mbd_workbench import MBDValidation


def log_phase(message):
    print(message, flush=True)


def user_args():
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
    elif "--pass" in sys.argv:
        args = sys.argv[sys.argv.index("--pass") + 1:]
    else:
        args = sys.argv[1:]

    return [
        arg
        for arg in args
        if not arg.lower().endswith(".py")
    ]


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

    shape = Part.open(filename)

    if shape is None:
        raise RuntimeError("Part.open returned no shape for {}".format(filename))

    shape_obj = doc.addObject("Part::Feature", "ImportedShape")
    shape_obj.Shape = shape


def main():
    args = user_args()

    if not args:
        default_path = os.environ.get(
            "MBD_AP242_IMPORT_EXPORT_SMOKE_STEP",
            "/home/chip/Projects/FreeCAD MBD/NIST-PMI-STEP-Files/nist_ctc_05_asme1_ap242-e1.stp"
        )
        args = [default_path]

    filename = os.path.abspath(args[0])
    log_phase("Selected STEP file: {}".format(filename))

    if not os.path.exists(filename):
        raise SystemExit("STEP file not found: {}".format(filename))

    log_phase("Creating FreeCAD document.")
    doc = FreeCAD.newDocument("AP242ImportExportSmoke")

    try:
        started = time.perf_counter()
        before_names = {obj.Name for obj in doc.Objects}
        log_phase("Starting STEP geometry import.")
        import_step_geometry(doc, filename)
        geometry_import_done = time.perf_counter()
        log_phase(
            "Finished STEP geometry import in {:.3f}s.".format(
                geometry_import_done - started
            )
        )
        log_phase("Starting import recompute.")
        doc.recompute()
        import_recompute_done = time.perf_counter()
        log_phase(
            "Finished import recompute in {:.3f}s.".format(
                import_recompute_done - geometry_import_done
            )
        )

        log_phase("Finding imported shape objects.")
        shape_objects = MBDCommands.importable_shape_objects(doc, before_names)
        shape_lookup_done = time.perf_counter()

        if not shape_objects:
            raise RuntimeError("No imported shape object was found after STEP import.")

        log_phase("Starting semantic PMI preview.")
        preview = MBDImporter.semantic_import_preview(filename)
        preview_done = time.perf_counter()
        log_phase(
            "Finished semantic PMI preview in {:.3f}s.".format(
                preview_done - shape_lookup_done
            )
        )
        log_phase("Starting native PMI creation.")
        result = MBDImporter.create_native_datums_and_systems_from_preview(
            doc,
            shape_objects[0],
            preview
        )
        native_done = time.perf_counter()
        log_phase(
            "Finished native PMI creation in {:.3f}s.".format(
                native_done - preview_done
            )
        )
        log_phase("Organizing PMI tree.")
        MBDCommands.organize_pmi_tree(doc)
        tree_done = time.perf_counter()
        log_phase("Starting native recompute.")
        doc.recompute()
        native_recompute_done = time.perf_counter()
        log_phase(
            "Finished native recompute in {:.3f}s.".format(
                native_recompute_done - tree_done
            )
        )

        log_phase("Starting validation.")
        validation_report = MBDValidation.validate_document_structured(doc)
        validation_done = time.perf_counter()
        log_phase(
            "Finished validation in {:.3f}s.".format(
                validation_done - native_recompute_done
            )
        )
        error_issues = [
            issue
            for issue in validation_report.get("issues", [])
            if issue.severity == "error"
        ]

        if error_issues:
            for error in error_issues:
                print("Validation error: {}".format(error.message))

            raise RuntimeError(
                "Validation reported {} error(s).".format(len(error_issues))
            )

        export_objects = MBDExporter.exportable_shape_objects(doc)
        export_names = [obj.Name for obj in export_objects]
        output_path = os.path.join(
            tempfile.gettempdir(),
            "mbd_import_export_smoke.step"
        )

        if os.path.exists(output_path):
            os.remove(output_path)

        FreeCAD.setActiveDocument(doc.Name)
        log_phase("Starting AP242 export.")
        ok = MBDExporter.export_ap242(output_path)
        export_done = time.perf_counter()
        log_phase(
            "Finished AP242 export in {:.3f}s.".format(
                export_done - validation_done
            )
        )

        if not ok:
            raise RuntimeError("MBDExporter.export_ap242 returned false.")

        if not os.path.exists(output_path):
            raise RuntimeError("Export did not create {}".format(output_path))

        with open(output_path, "r", encoding="utf-8", errors="replace") as handle:
            step_text = handle.read()
        read_export_done = time.perf_counter()

        if "/*   NUL REF   */" in step_text:
            raise RuntimeError("Re-exported STEP contains null semantic references.")

        created = result["created"]
        created_pmi_count = sum(
            len(created.get(key, []))
            for key in (
                "datums",
                "datum_targets",
                "datum_systems",
                "dimensions",
                "fcfs",
            )
        )
        placeholder_count = len(re.findall(
            r"=\s*ANNOTATION_PLACEHOLDER_OCCURRENCE\(",
            step_text
        ))

        if created_pmi_count and placeholder_count == 0:
            raise RuntimeError(
                "Expected AP242 annotation placeholders in re-exported STEP."
            )

        created_datums_by_source_id = {
            str(getattr(datum, "AP242SourceId", "")): datum
            for datum in created.get("datums", [])
        }

        for datum_candidate in preview["candidates"].get("datums", []):
            geometry_usages = [
                usage
                for usage in datum_candidate.get("geometry_usages", [])
                if usage.get("subelement")
            ]

            if len(geometry_usages) <= 1:
                continue

            datum_obj = created_datums_by_source_id.get(
                datum_candidate.get("step_id", "")
            )

            if datum_obj is None:
                continue

            preserved = [
                str(item)
                for item in getattr(datum_obj, "ReferencedSubelementList", [])
                if str(item)
            ]

            if len(preserved) != len(geometry_usages):
                raise RuntimeError(
                    "Expected imported datum {} to preserve {} bindings, got {}.".format(
                        datum_obj.Name,
                        len(geometry_usages),
                        len(preserved)
                    )
                )

            attachment = MBDValidation.attachment_text(datum_obj)

            for preserved_sub in preserved:
                if preserved_sub not in attachment:
                    raise RuntimeError(
                        "Expected imported datum {} attachment text to include {}, got {!r}.".format(
                            datum_obj.Name,
                            preserved_sub,
                            attachment
                        )
                    )

        fcf_entity_by_type = {
            "Angularity": "ANGULARITY_TOLERANCE",
            "Circularity": "ROUNDNESS_TOLERANCE",
            "CircularRunout": "CIRCULAR_RUNOUT_TOLERANCE",
            "Cylindricity": "CYLINDRICITY_TOLERANCE",
            "Flatness": "FLATNESS_TOLERANCE",
            "LineProfile": "LINE_PROFILE_TOLERANCE",
            "Parallelism": "PARALLELISM_TOLERANCE",
            "Perpendicularity": "PERPENDICULARITY_TOLERANCE",
            "Position": "POSITION_TOLERANCE",
            "Profile": "SURFACE_PROFILE_TOLERANCE",
            "Straightness": "STRAIGHTNESS_TOLERANCE",
            "TotalRunout": "TOTAL_RUNOUT_TOLERANCE",
        }

        for fcf in created.get("fcfs", []):
            expected = fcf_entity_by_type.get(str(fcf.ToleranceType))

            if expected is not None and expected not in step_text:
                raise RuntimeError(
                    "Expected {} in re-exported STEP for {}.".format(
                        expected,
                        fcf.Name
                    )
                )

        if any(
            str(getattr(fcf, "ToleranceType", "")) in (
                "CircularRunout",
                "TotalRunout"
            )
            for fcf in created.get("fcfs", [])
        ):
            for expected in ("RUNOUT_ZONE_DEFINITION", "RUNOUT_ZONE_ORIENTATION"):
                if expected not in step_text:
                    raise RuntimeError(
                        "Expected {} in re-exported STEP for imported runout.".format(
                            expected
                        )
                    )

        print("AP242 import/export smoke file: {}".format(filename))
        print("Imported shape object: {}".format(shape_objects[0].Name))
        print("Exportable shape objects: {}".format(", ".join(export_names)))
        print("Created datum features: {}".format(len(created["datums"])))
        print("Created datum targets: {}".format(
            len(created.get("datum_targets", []))
        ))
        print("Created datum systems: {}".format(len(created["datum_systems"])))
        print("Created dimensions: {}".format(len(created.get("dimensions", []))))
        print("Created FCFs: {}".format(len(created.get("fcfs", []))))
        print("Exported annotation placeholders: {}".format(placeholder_count))
        print("Exported STEP: {}".format(output_path))
        print(
            "Timing: geometry import {:.3f}s, import recompute {:.3f}s, "
            "shape lookup {:.3f}s, semantic preview {:.3f}s, native PMI "
            "creation {:.3f}s, tree organization {:.3f}s, native recompute "
            "{:.3f}s, validation {:.3f}s, AP242 export {:.3f}s, export read "
            "{:.3f}s, total {:.3f}s".format(
                geometry_import_done - started,
                import_recompute_done - geometry_import_done,
                shape_lookup_done - import_recompute_done,
                preview_done - shape_lookup_done,
                native_done - preview_done,
                tree_done - native_done,
                native_recompute_done - tree_done,
                validation_done - native_recompute_done,
                export_done - validation_done,
                read_export_done - export_done,
                read_export_done - started
            )
        )
        print("AP242 import/export smoke passed.")
    finally:
        FreeCAD.closeDocument(doc.Name)


try:
    main()
except Exception:
    traceback.print_exc()
    raise
