"""Headless AP242 datum/datum-system import smoke test.

Run with FreeCADCmd, for example:

    FreeCADCmd tests/freecad_ap242_import_smoke.py -- /path/to/file.stp

The script avoids GUI dialogs but exercises the same importer layers used by
the `Import AP242 Datums` command: STEP geometry import, semantic PMI preview,
native datum/datum-system creation, and validation.
"""

import os
import sys
import traceback


WORKBENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if WORKBENCH_DIR not in sys.path:
    sys.path.insert(0, WORKBENCH_DIR)

import FreeCAD
import Part

from freecad.mbd_workbench import MBDCommands
from freecad.mbd_workbench import MBDImporter
from freecad.mbd_workbench import MBDValidation


def inspector_report_text(report):
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

    error_count = len([
        issue for issue in report["issues"]
        if issue.severity == "error"
    ])
    warning_count = len([
        issue for issue in report["issues"]
        if issue.severity == "warning"
    ])
    lines = [
        "Datums: {}   Targets: {}   Basics: {}   Dimensions: {}   Datum systems: {}   FCFs: {}   Errors: {}   Warnings: {}".format(
            len(report["datums"]),
            len(report["datum_targets"]),
            len(report["basic_dimensions"]),
            len(report["dimensions"]),
            len(report["datum_systems"]),
            len(report["fcfs"]),
            error_count,
            warning_count
        ),
        "",
        "\t".join([
            "Status",
            "Type",
            "Name",
            "PMI ID",
            "Attachment",
            "Geometry",
            "Message",
        ]),
    ]

    for obj in pmi_objects:
        issues = issues_by_object.get(obj.Name, [])
        status = "OK"

        if any(issue.severity == "error" for issue in issues):
            status = "Error"
        elif issues:
            status = "Warning"

        message = "; ".join([issue.message for issue in issues])
        geometry = (
            MBDValidation.fcf_geometry_text(obj)
            if MBDValidation.is_mbd_fcf(obj)
            else getattr(obj, "GeometryType", "")
        )
        lines.append("\t".join([
            status,
            MBDValidation.pmi_type(obj),
            obj.Name,
            getattr(obj, "PMIId", ""),
            MBDValidation.attachment_text(obj),
            geometry,
            message,
        ]))

    return "\n".join(lines)


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


def main():
    args = user_args()

    if not args:
        default_path = os.environ.get(
            "MBD_AP242_IMPORT_SMOKE_STEP",
            "/home/chip/Projects/FreeCAD MBD/NIST-PMI-STEP-Files/nist_ctc_01_asme1_ap242-e1.stp"
        )
        args = [default_path]

    filename = os.path.abspath(args[0])
    print("Selected STEP file: {}".format(filename))

    if not os.path.exists(filename):
        raise SystemExit("STEP file not found: {}".format(filename))

    doc = FreeCAD.newDocument("AP242ImportSmoke")

    try:
        import ImportGui
        ImportGui.insert(filename, doc.Name)
    except Exception:
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
                pass
            else:
                Import.insert(filename, doc.Name)
        except Exception:
            shape = Part.open(filename)
            if shape is None:
                raise RuntimeError("Part.open returned no shape for {}".format(filename))

            shape_obj = doc.addObject("Part::Feature", "ImportedShape")
            shape_obj.Shape = shape

    doc.recompute()

    shape_objects = MBDCommands.importable_shape_objects(doc, set())

    if not shape_objects:
        raise RuntimeError("No imported shape object was found after STEP import.")

    preview = MBDImporter.semantic_import_preview(filename)
    result = MBDImporter.create_native_datums_and_systems_from_preview(
        doc,
        shape_objects[0],
        preview
    )
    MBDCommands.organize_pmi_tree(doc)
    doc.recompute()

    validation_report = MBDValidation.validate_document_structured(doc)
    created = result["created"]
    datum_count = len(created["datums"])
    datum_target_count = len(created.get("datum_targets", []))
    datum_system_count = len(created["datum_systems"])
    dimension_count = len(created.get("dimensions", []))
    fcf_count = len(created.get("fcfs", []))
    error_issues = [
        issue
        for issue in validation_report.get("issues", [])
        if issue.severity == "error"
    ]
    error_count = len(error_issues)

    print("AP242 import smoke file: {}".format(filename))
    print("Imported shape object: {}".format(shape_objects[0].Name))
    print("Preview datums native-ready: {}/{}".format(
        sum(
            1
            for datum in preview["candidates"]["datums"]
            if datum.get("can_create_native", False)
        ),
        len(preview["candidates"]["datums"])
    ))
    print("Created datum features: {}".format(datum_count))
    print("Created datum targets: {}".format(datum_target_count))
    print("Created datum systems: {}".format(datum_system_count))
    print("Created dimensions: {}".format(dimension_count))
    print("Created FCFs: {}".format(fcf_count))
    print("")
    print("PMI Inspector report:")
    print(inspector_report_text(validation_report))

    if result.get("warnings"):
        print("Warnings:")

        for warning in result["warnings"]:
            print("- " + warning)

    if result.get("skipped"):
        print("Skipped:")

        for skipped in result["skipped"]:
            print("- " + skipped)

    if error_issues:
        print("Validation errors:")

        for error in error_issues:
            print("- " + error.message)

    if error_count:
        raise RuntimeError("Validation reported {} error(s).".format(error_count))

    print("AP242 import smoke passed.")
    FreeCAD.closeDocument(doc.Name)


try:
    main()
except Exception:
    traceback.print_exc()
    raise
