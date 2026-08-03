#!/usr/bin/env python3

"""Summarize AP242 semantic-import preview readiness for a STEP folder.

This is a headless helper for broad importer checks against external example
sets such as the NIST PMI STEP files.  It does not require FreeCAD, create
objects, or validate imported geometry in the GUI; it only exercises the
STEP semantic parser, native-ready classification, and tentative topology
binding logic.
"""

import argparse
import glob
import os
import sys
import time


WORKBENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKBENCH_DIR)

from freecad.mbd_workbench import MBDImporter


def step_files(path):
    if os.path.isfile(path):
        return [path]

    patterns = [
        os.path.join(path, "*.stp"),
        os.path.join(path, "*.step"),
        os.path.join(path, "*.STP"),
        os.path.join(path, "*.STEP"),
    ]
    files = []

    for pattern in patterns:
        files.extend(glob.glob(pattern))

    return sorted(set(files))


def readiness(preview, key):
    records = preview["candidates"][key]
    ready = sum(
        1
        for record in records
        if record.get("can_create_native", False)
    )
    return "{}/{}".format(ready, len(records))


def main():
    parser = argparse.ArgumentParser(
        description="Run AP242 semantic import-preview readiness over STEP files."
    )
    parser.add_argument(
        "path",
        help="STEP file or folder containing STEP files"
    )
    args = parser.parse_args()

    files = step_files(args.path)

    if not files:
        raise SystemExit("No STEP files found: {}".format(args.path))

    print(
        "file,datums,datum_systems,datum_targets,dimensions,fcfs,relationships,limitations,seconds"
    )

    for path in files:
        started = time.time()

        try:
            preview = MBDImporter.semantic_import_preview(path)
            values = [
                readiness(preview, "datums"),
                readiness(preview, "datum_systems"),
                readiness(preview, "datum_targets"),
                readiness(preview, "dimensions"),
                readiness(preview, "fcfs"),
                readiness(preview, "relationships"),
                str(len(preview["limitations"])),
                "{:.2f}".format(time.time() - started),
            ]
            print(os.path.basename(path) + "," + ",".join(values))
        except Exception as exc:
            print(
                "{},ERROR,{},{}".format(
                    os.path.basename(path),
                    repr(exc),
                    "{:.2f}".format(time.time() - started)
                )
            )


if __name__ == "__main__":
    main()
