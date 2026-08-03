# FreeCAD MBD Workbench

FreeCAD MBD Workbench adds model-based definition tools for semantic PMI, GD&T annotations, validation, and AP242 STEP exchange.

This addon is early public-preview software. The current focus is semantic definition and AP242 interoperability; visual annotation polish and some advanced AP242 variants are still under active development.

## Requirements

- FreeCAD 1.1.0 or newer
- Python 3.11 or newer, through FreeCAD
- No external Python package dependencies

## Installation

For development or manual testing, clone this repository into a FreeCAD `Mod` directory:

```bash
git clone https://github.com/ChipsWoodShop/FreeCAD-MBDWorkbench.git MBDWorkbench
```

On Linux, one common target is:

```bash
~/.local/share/FreeCAD/Mod/MBDWorkbench
```

Restart FreeCAD and activate the `MBD` workbench.

## Current Capabilities

- Create datum features, datum targets, datum systems, dimensions, and feature control frames.
- Validate PMI attachments, datum-system sufficiency, dimension rules, and supported FCF geometry rules.
- Inspect PMI in the active FreeCAD document.
- Export supported semantic PMI to AP242 STEP.
- Inspect AP242 STEP files for semantic PMI coverage.
- Import supported AP242 semantic PMI into native MBD objects for conservative round-trip workflows.

Supported AP242 workflows include many common datum, datum target, dimension, and FCF cases. The project plan tracks exact coverage and remaining gaps.

## Known Limitations

- AP242 semantic import is conservative: unsupported or unsafe PMI is reported rather than silently converted.
- Presentation PMI export currently uses lightweight annotation placeholders, not exact graphical leader/frame/text reconstruction.
- Some derived-axis, path-defined, and advanced tolerance-zone cases remain future work.
- Annotation appearance and drag interaction are functional but not final ASME-style polish.
- Saved-document compatibility is not guaranteed before a stable `1.0.0` release.

## Testing

Pure Python importer tests:

```bash
python3 tests/test_mbd_importer.py
```

Headless FreeCAD smoke test:

```bash
python3 tests/run_headless_smoke.py --mode datum-only
```

The headless runner uses an isolated temporary FreeCAD profile under `/tmp/mbd-freecad-cli`.

## Privacy

The workbench does not intentionally perform network access or send model data to external services. AP242 inspection, import, validation, and export run locally.

## Reporting Issues

Please report bugs and feature requests through GitHub Issues:

https://github.com/ChipsWoodShop/FreeCAD-MBDWorkbench/issues

When reporting AP242 or geometry issues, include the FreeCAD version, operating system, exact command used, and a small reproducible STEP or FreeCAD file when possible.

See `CONTRIBUTING.md` for contribution guidelines and recommended local checks.

## License

FreeCAD MBD Workbench is licensed under the GNU Lesser General Public License v2.1 only. See `LICENSE`.
