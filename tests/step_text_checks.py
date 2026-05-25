#!/usr/bin/env python3

import argparse
import re
import sys
from pathlib import Path


ENTITY_RE = re.compile(r"^#(\d+)\s*=\s*(.*?);", re.MULTILINE | re.DOTALL)
REF_RE = re.compile(r"#(\d+)")


def load_entities(text):
    return {
        entity_id: body.replace("\n", " ")
        for entity_id, body in ENTITY_RE.findall(text)
    }


def require(condition, message, failures):
    if not condition:
        failures.append(message)


def entity_refs(body):
    return REF_RE.findall(body)


def datum_labels(text):
    return set(re.findall(r"DATUM\('[^']*','[^']*',#[0-9]+,\.[FT]\.,'([^']+)'\)", text))


def tolerance_value(text):
    match = re.search(
        r"LENGTH_MEASURE_WITH_UNIT\(LENGTH_MEASURE\(([^)]+)\)",
        text
    )
    if not match:
        return None

    return float(match.group(1))


def check_step_file(path, expected_tolerance):
    text = path.read_text(errors="replace")
    entities = load_entities(text)
    failures = []

    require("AP242_MANAGED_MODEL_BASED_3D_ENGINEERING" in text,
            "STEP file is not AP242 managed model based engineering",
            failures)

    labels = datum_labels(text)
    for label in ["A", "B", "C"]:
        require(label in labels, "missing DATUM label {}".format(label), failures)

    datum_feature_ids = [
        entity_id
        for entity_id, body in entities.items()
        if body.startswith("DATUM_FEATURE")
    ]
    require(len(datum_feature_ids) >= 3,
            "expected at least three DATUM_FEATURE entities",
            failures)

    advanced_face_ids = {
        entity_id
        for entity_id, body in entities.items()
        if body.startswith("ADVANCED_FACE")
    }
    gisu_bodies = [
        body
        for body in entities.values()
        if body.startswith("GEOMETRIC_ITEM_SPECIFIC_USAGE")
    ]
    datum_gisus = [
        body
        for body in gisu_bodies
        if any("#" + datum_id in body for datum_id in datum_feature_ids)
    ]
    require(len(datum_gisus) >= 3,
            "expected datum GEOMETRIC_ITEM_SPECIFIC_USAGE entities",
            failures)

    for body in datum_gisus[:3]:
        refs = entity_refs(body)
        require(any(ref in advanced_face_ids for ref in refs),
                "datum GEOMETRIC_ITEM_SPECIFIC_USAGE does not target an ADVANCED_FACE",
                failures)

    require("POSITION_TOLERANCE" in text,
            "missing POSITION_TOLERANCE",
            failures)
    require("GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE" in text,
            "missing GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE",
            failures)

    if "TOLERANCE_ZONE" in text:
        require("TOLERANCE_ZONE_FORM" in text,
                "TOLERANCE_ZONE exists without TOLERANCE_ZONE_FORM",
                failures)

    value = tolerance_value(text)
    require(value is not None, "missing tolerance LENGTH_MEASURE value", failures)

    if value is not None:
        require(value > 0.0, "tolerance value is not positive", failures)

        if expected_tolerance is not None:
            require(abs(value - expected_tolerance) < 1e-12,
                    "tolerance value {} did not match expected {}".format(
                        value,
                        expected_tolerance
                    ),
                    failures)

    require("/*   NUL REF   */" not in text,
            "STEP file contains a null geometric tolerance reference",
            failures)

    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "step_file",
        type=Path
    )
    parser.add_argument(
        "--expected-tolerance",
        type=float,
        default=None
    )
    args = parser.parse_args()

    failures = check_step_file(args.step_file, args.expected_tolerance)

    if failures:
        for failure in failures:
            print("FAIL:", failure)
        return 1

    print("STEP text checks passed:", args.step_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
