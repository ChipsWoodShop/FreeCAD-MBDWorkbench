# Contributing

Thanks for helping improve FreeCAD MBD Workbench.

## Before Opening an Issue

- Check the current `PROJECT_PLAN.md` for known limitations and active priorities.
- Try to reproduce the issue in the latest development branch.
- For AP242 issues, keep a small STEP file or FreeCAD document that demonstrates the problem.

## Bug Reports

Please include:

- FreeCAD version and operating system.
- MBD Workbench version or commit.
- Exact command or workflow used.
- Report-view output, if available.
- A small reproducible file when possible.

## Pull Requests

- Keep changes scoped to one behavior or workstream.
- Preserve existing user-created files and avoid broad refactors unless they are needed.
- Add or update tests for semantic import/export, validation, and display behavior when practical.
- Run the relevant local checks before submitting:

```bash
python3 tests/validate_package_metadata.py
python3 tests/test_mbd_importer.py
python3 tests/run_headless_smoke.py --mode datum-only
```

## Project Direction

The workbench prioritizes semantic PMI correctness and AP242 interoperability before final annotation cosmetics. Presentation polish matters, but should not destabilize semantic export/import behavior.
