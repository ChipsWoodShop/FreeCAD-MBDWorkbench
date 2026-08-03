#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
DEFAULT_FREECADCMD = Path("/tmp/squashfs-root/usr/bin/freecadcmd")
DEFAULT_APPIMAGE = Path("/home/chip/Applications/FreeCAD_1.1.1-Linux-x86_64-py311.AppImage")
FREECAD_CLI_HOME = Path("/tmp/mbd-freecad-cli")


def freecad_cli_env(mode=None, output=None, controlled_subelement=None):
    """Keep headless FreeCAD smoke runs out of the user's normal profile."""
    config_home = FREECAD_CLI_HOME / "config"
    cache_home = FREECAD_CLI_HOME / "cache"

    config_home.mkdir(parents=True, exist_ok=True)
    cache_home.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["APPIMAGE_EXTRACT_AND_RUN"] = "1"
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["XDG_CONFIG_HOME"] = str(config_home)
    env["XDG_CACHE_HOME"] = str(cache_home)

    if mode is not None:
        env["MBD_HEADLESS_SMOKE_MODE"] = mode

    if output is not None:
        env["MBD_HEADLESS_SMOKE_OUTPUT"] = output

    if controlled_subelement is not None:
        env["MBD_HEADLESS_SMOKE_CONTROLLED_SUBELEMENT"] = controlled_subelement

    return env


def freecad_console_command():
    freecadcmd = os.environ.get("FREECADCMD")

    if freecadcmd:
        return [freecadcmd]

    if DEFAULT_APPIMAGE.exists():
        return [str(DEFAULT_APPIMAGE), "--console"]

    if DEFAULT_FREECADCMD.exists():
        return [str(DEFAULT_FREECADCMD)]

    raise RuntimeError(
        "FreeCAD command not found at {} and AppImage not found at {}".format(
            DEFAULT_FREECADCMD,
            DEFAULT_APPIMAGE
        )
    )


def run_freecad_smoke(freecad_command, mode, output, controlled_subelement):
    wrapper = Path(tempfile.gettempdir()) / "mbd_run_headless_smoke.py"
    wrapper.write_text(
        textwrap.dedent(
            """\
            import importlib.util
            import sys

            repo_dir = {!r}
            script = {!r}
            sys.path.insert(0, repo_dir)

            spec = importlib.util.spec_from_file_location(
                "headless_freecad_smoke",
                script
            )
            headless_freecad_smoke = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(headless_freecad_smoke)
            sys.argv = [script]

            raise SystemExit(headless_freecad_smoke.main())
            """
        ).format(
            str(REPO_DIR),
            str(REPO_DIR / "tests" / "headless_freecad_smoke.py")
        ),
        encoding="utf-8"
    )

    return subprocess.call(
        freecad_command + [str(wrapper)],
        cwd=str(REPO_DIR),
        env=freecad_cli_env(
            mode=mode,
            output=output,
            controlled_subelement=controlled_subelement,
        )
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=[
            "datum-only",
            "fcf-no-diameter",
            "fcf-diameter",
            "fcf-material-modifier",
            "fcf-runout-orientation",
            "all-fcfs",
            "stale-cancel",
            "ap242-pmi-scan",
            "basic-dimension-projection",
            "semantic-dimension",
            "dimension-semantic-rules",
            "dimension-export",
            "datum-target-export",
            "line-datum-target-export",
            "area-datum-target-export",
            "datum-target-sufficiency",
            "mixed-datum-target-sufficiency",
            "common-datum-system-validation",
            "common-datum-export",
            "display-layout-metadata",
            "single-item-fcf-layout",
            "runout-orientation-display",
            "single-item-datum-feature-layout",
            "single-item-dimension-layout",
            "global-geometry-link-scope",
            "fcf-rule-validation",
            "dimension-reference-patterns",
            "basic-size-dimension-requires-profile",
            "cylinder-axis-dimensions",
            "position-fcf-hole-opening-direction",
            "radius-dimension-display",
            "annotation-display-shape",
            "preferred-display-offset",
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

    return run_freecad_smoke(
        freecad_console_command(),
        args.mode,
        args.output,
        args.controlled_subelement
    )


if __name__ == "__main__":
    sys.exit(main())
