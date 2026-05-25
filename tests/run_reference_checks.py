#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
CLEAN_REFERENCE = REPO_DIR / "tests" / "MBDTest01_BA.step"
DRIFT_REFERENCE = REPO_DIR / "tests" / "MBDTest01_AA.step"
STEP_CHECKS = REPO_DIR / "tests" / "step_text_checks.py"


def run_check(path):
    if not path.exists():
        print("missing reference:", path)
        return 1

    return subprocess.call([
        sys.executable,
        str(STEP_CHECKS),
        str(path),
        "--expected-tolerance",
        "0.01",
    ], cwd=str(REPO_DIR))


def main():
    failures = 0

    print("checking clean AP242 reference:", CLEAN_REFERENCE)
    failures += run_check(CLEAN_REFERENCE)

    print("checking topology-drift AP242 reference:", DRIFT_REFERENCE)
    failures += run_check(DRIFT_REFERENCE)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
