#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
DEFAULT_FREECADCMD = Path("/tmp/squashfs-root/usr/bin/freecadcmd")
DEFAULT_APPIMAGE = Path("/home/chip/Applications/FreeCAD_1.1.1-Linux-x86_64-py311.AppImage")


def ensure_freecadcmd():
    if DEFAULT_FREECADCMD.exists():
        return DEFAULT_FREECADCMD

    if not DEFAULT_APPIMAGE.exists():
        raise RuntimeError(
            "FreeCAD command not found at {} and AppImage not found at {}".format(
                DEFAULT_FREECADCMD,
                DEFAULT_APPIMAGE
            )
        )

    subprocess.check_call(
        [str(DEFAULT_APPIMAGE), "--appimage-extract"],
        cwd="/tmp"
    )

    if not DEFAULT_FREECADCMD.exists():
        raise RuntimeError("AppImage extraction did not create {}".format(DEFAULT_FREECADCMD))

    return DEFAULT_FREECADCMD


def run_freecad_smoke(freecadcmd, mode, output, controlled_subelement):
    script = REPO_DIR / "tests" / "headless_freecad_smoke.py"
    command = (
        "import runpy, sys; "
        "sys.argv = [{!r}, '--mode', {!r}, '--output', {!r}, "
        "'--controlled-subelement', {!r}]; "
        "runpy.run_path({!r}, run_name='__main__')"
    ).format(
        str(script),
        mode,
        output,
        controlled_subelement,
        str(script)
    )

    return subprocess.call([
        str(freecadcmd),
        "-c",
        command,
    ], cwd=str(REPO_DIR))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=[
            "datum-only",
            "fcf-no-diameter",
            "fcf-diameter",
            "all-fcfs",
            "stale-cancel",
            "basic-dimension-projection",
            "semantic-dimension",
            "dimension-semantic-rules",
            "dimension-export",
            "datum-target-export",
            "datum-target-sufficiency",
            "common-datum-system-validation",
            "common-datum-export",
            "display-layout-metadata",
            "fcf-rule-validation",
            "dimension-reference-patterns",
            "basic-size-dimension-requires-profile",
            "cylinder-axis-dimensions",
            "radius-dimension-display",
            "annotation-display-shape",
            "preferred-display-offset",
            "gdt-symbol-table",
            "grouped-display-helpers",
            "fcf-tolerance-units",
            "fcf-below-dimension",
            "flatness-fcf-display",
            "parallelism-fcf-display",
            "perpendicularity-fcf-display",
            "profile-fcf-display",
            "line-profile-fcf-display",
            "flatness-fcf-exterior-leader",
            "exterior-direction-centroid",
            "oriented-face-normals",
            "surface-solid-probe",
            "pmi-text-height-ignores-helpers",
        ],
        default="datum-only"
    )
    parser.add_argument(
        "--output",
        default="/tmp/mbd_headless_smoke.step"
    )
    parser.add_argument(
        "--controlled-subelement",
        default="Face1"
    )
    args = parser.parse_args()

    freecadcmd = Path(os.environ.get("FREECADCMD", ensure_freecadcmd()))
    return run_freecad_smoke(
        freecadcmd,
        args.mode,
        args.output,
        args.controlled_subelement
    )


if __name__ == "__main__":
    sys.exit(main())
