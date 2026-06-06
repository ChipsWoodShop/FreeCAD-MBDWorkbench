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


def check_step_file(
    path,
    expected_tolerance,
    require_all_fcfs=False,
    require_dimensions=False,
    min_dimensional_size=1,
    require_location_dimensions=False,
    require_directed_location_dimensions=False,
    require_datum_targets=False,
    require_common_datum=False,
    require_geometric_tolerances=True
):
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

    if require_geometric_tolerances:
        require("POSITION_TOLERANCE" in text,
                "missing POSITION_TOLERANCE",
                failures)
        require("GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE" in text,
                "missing GEOMETRIC_TOLERANCE_WITH_DATUM_REFERENCE",
                failures)

    if require_all_fcfs:
        for entity_name in [
            "ANGULARITY_TOLERANCE",
            "CIRCULAR_RUNOUT_TOLERANCE",
            "CYLINDRICITY_TOLERANCE",
            "FLATNESS_TOLERANCE",
            "LINE_PROFILE_TOLERANCE",
            "PARALLELISM_TOLERANCE",
            "PERPENDICULARITY_TOLERANCE",
            "ROUNDNESS_TOLERANCE",
            "STRAIGHTNESS_TOLERANCE",
            "SURFACE_PROFILE_TOLERANCE",
            "TOTAL_RUNOUT_TOLERANCE",
        ]:
            require(entity_name in text,
                    "missing {}".format(entity_name),
                    failures)

    if require_dimensions:
        for entity_name in [
            "DIMENSIONAL_SIZE",
            "SHAPE_DIMENSION_REPRESENTATION",
            "DIMENSIONAL_CHARACTERISTIC_REPRESENTATION",
            "PLUS_MINUS_TOLERANCE",
        ]:
            require(entity_name in text,
                    "missing {}".format(entity_name),
                    failures)

        dimensional_size_count = len([
            body
            for body in entities.values()
            if body.startswith("DIMENSIONAL_SIZE")
        ])
        require(dimensional_size_count >= min_dimensional_size,
                "expected at least {} DIMENSIONAL_SIZE entities, found {}".format(
                    min_dimensional_size,
                    dimensional_size_count
                ),
                failures)

    if require_location_dimensions:
        require("DIMENSIONAL_LOCATION" in text,
                "missing DIMENSIONAL_LOCATION",
                failures)

    if require_directed_location_dimensions:
        require("DIRECTED_DIMENSIONAL_LOCATION" in text,
                "missing DIRECTED_DIMENSIONAL_LOCATION",
                failures)

    if require_datum_targets:
        for entity_name in [
            "PLACED_DATUM_TARGET_FEATURE",
            "FEATURE_FOR_DATUM_TARGET_RELATIONSHIP",
            "SHAPE_REPRESENTATION_WITH_PARAMETERS",
        ]:
            require(entity_name in text,
                    "missing {}".format(entity_name),
                    failures)

    if require_common_datum:
        for entity_name in [
            "COMMON_DATUM_LIST",
            "DATUM_REFERENCE_ELEMENT",
            "DATUM_REFERENCE_COMPARTMENT",
            "DATUM_SYSTEM",
        ]:
            require(entity_name in text,
                    "missing {}".format(entity_name),
                    failures)

    if "TOLERANCE_ZONE" in text:
        require("TOLERANCE_ZONE_FORM" in text,
                "TOLERANCE_ZONE exists without TOLERANCE_ZONE_FORM",
                failures)

    value = tolerance_value(text)

    if require_geometric_tolerances:
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
    parser.add_argument(
        "--require-all-fcfs",
        action="store_true"
    )
    parser.add_argument(
        "--require-dimensions",
        action="store_true"
    )
    parser.add_argument(
        "--min-dimensional-size",
        type=int,
        default=1
    )
    parser.add_argument(
        "--require-location-dimensions",
        action="store_true"
    )
    parser.add_argument(
        "--require-directed-location-dimensions",
        action="store_true"
    )
    parser.add_argument(
        "--require-datum-targets",
        action="store_true"
    )
    parser.add_argument(
        "--require-common-datum",
        action="store_true"
    )
    parser.add_argument(
        "--no-geometric-tolerances",
        action="store_true"
    )
    args = parser.parse_args()

    failures = check_step_file(
        args.step_file,
        args.expected_tolerance,
        args.require_all_fcfs,
        args.require_dimensions,
        args.min_dimensional_size,
        args.require_location_dimensions,
        args.require_directed_location_dimensions,
        args.require_datum_targets,
        args.require_common_datum,
        not args.no_geometric_tolerances
    )

    if failures:
        for failure in failures:
            print("FAIL:", failure)
        return 1

    print("STEP text checks passed:", args.step_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
