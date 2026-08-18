#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

BOOTSTRAP_SEED = 0xC13C0005
BOOTSTRAP_RESAMPLES = 50_000


def _median(values: Iterable[float]) -> float:
    materialized = list(values)
    if not materialized:
        return 0.0
    return float(statistics.median(materialized))


def _percentile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    if probability <= 0:
        return ordered[0]
    if probability >= 1:
        return ordered[-1]
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def histogram_quantile(histogram: dict[str, int] | dict[int, int], probability: float) -> float:
    items = sorted((int(key), int(count)) for key, count in histogram.items() if int(count) > 0)
    total = sum(count for _, count in items)
    if total == 0:
        return 0.0
    rank = max(1, math.ceil(probability * total))
    cumulative = 0
    for value, count in items:
        cumulative += count
        if cumulative >= rank:
            return float(value)
    return float(items[-1][0])


def _group_measured_pairs(runs: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    issues: list[str] = []
    for run in runs:
        if run.get("phase") != "measured":
            continue
        fixture_id = str(run["fixture_id"])
        pair_id = str(run["pair_id"])
        condition = str(run["condition"])
        if condition in grouped[(fixture_id, pair_id)]:
            issues.append(f"duplicate {condition} run for {fixture_id}/{pair_id}")
        grouped[(fixture_id, pair_id)][condition] = run

    by_fixture: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (fixture_id, pair_id), conditions in sorted(grouped.items()):
        if set(conditions) != {"baseline", "treatment"}:
            issues.append(f"incomplete pair {fixture_id}/{pair_id}: {sorted(conditions)}")
            continue
        baseline = conditions["baseline"]
        treatment = conditions["treatment"]
        wall_overhead = treatment["wall_ns"] / baseline["wall_ns"] - 1.0
        baseline_cpu = baseline.get("cpu_user_ns", 0) + baseline.get("cpu_system_ns", 0)
        treatment_cpu = treatment.get("cpu_user_ns", 0) + treatment.get("cpu_system_ns", 0)
        cpu_overhead = treatment_cpu / baseline_cpu - 1.0 if baseline_cpu > 0 else None

        route_equivalent = (
            baseline.get("exit_status") == treatment.get("exit_status")
            and baseline.get("normalized_sha256") == treatment.get("normalized_sha256")
            and not baseline.get("panic_or_crash_seen", False)
            and not treatment.get("panic_or_crash_seen", False)
            and baseline.get("matches_frozen_route_invariant", False)
            and treatment.get("matches_frozen_route_invariant", False)
            and treatment.get("profile_valid", False)
        )
        if not route_equivalent:
            issues.append(f"route mismatch in {fixture_id}/{pair_id}")

        by_fixture[fixture_id].append(
            {
                "pair_id": pair_id,
                "wall_overhead_fraction": wall_overhead,
                "cpu_overhead_fraction": cpu_overhead,
                "route_equivalent": route_equivalent,
            }
        )
    return dict(by_fixture), issues


def stratified_bootstrap_interval(
    overheads_by_fixture: dict[str, list[float]],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float, float, float]:
    if not overheads_by_fixture or any(not values for values in overheads_by_fixture.values()):
        return 0.0, 0.0, 0.0

    rng = random.Random(seed)
    estimates: list[float] = []
    fixtures = sorted(overheads_by_fixture)
    for _ in range(resamples):
        fixture_medians = []
        for fixture_id in fixtures:
            values = overheads_by_fixture[fixture_id]
            sample = [values[rng.randrange(len(values))] for _ in range(len(values))]
            fixture_medians.append(_median(sample))
        estimates.append(_median(fixture_medians))

    point = _median(_median(overheads_by_fixture[fixture]) for fixture in fixtures)
    return point, _percentile(estimates, 0.025), _percentile(estimates, 0.975)


def summarize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    counters = profile["counters"]
    eligible_operations = int(counters["eligible_operations"])
    supported_operations = int(counters["supported_operations"])
    observed_blocks = int(counters["observed_blocks"])
    fully_supported = int(counters["fully_supported_eligible_blocks"])

    eligible_lengths = {str(key): int(value) for key, value in profile["eligible_block_lengths"].items()}
    empty_eligible_blocks = int(eligible_lengths.get("0", 0))
    nonempty_eligible_blocks = max(0, observed_blocks - empty_eligible_blocks)

    supported_runs = {str(key): int(value) for key, value in profile["supported_run_lengths"].items()}
    semantic_features = {
        str(key): int(value) for key, value in profile["semantic_feature_counts"].items()
    }
    feature_rates = {
        key: value / eligible_operations if eligible_operations else 0.0
        for key, value in semantic_features.items()
    }
    dominant_feature = max(feature_rates, key=feature_rates.get) if feature_rates else None
    dominant_rate = feature_rates.get(dominant_feature, 0.0) if dominant_feature else 0.0

    supported_fraction = supported_operations / eligible_operations if eligible_operations else 0.0
    fully_supported_fraction = fully_supported / nonempty_eligible_blocks if nonempty_eligible_blocks else 0.0
    run_median = histogram_quantile(supported_runs, 0.50)
    run_p75 = histogram_quantile(supported_runs, 0.75)
    run_p90 = histogram_quantile(supported_runs, 0.90)
    run_max = max((int(key) for key, value in supported_runs.items() if value), default=0)

    meets_proceed_band = (
        supported_fraction >= 0.30
        and run_median >= 2
        and (run_p75 >= 4 or fully_supported_fraction >= 0.10)
        and dominant_rate < 0.50
    )

    return {
        "eligible_operations": eligible_operations,
        "supported_operations": supported_operations,
        "supported_operation_fraction": supported_fraction,
        "observed_blocks": observed_blocks,
        "nonempty_eligible_blocks": nonempty_eligible_blocks,
        "fully_supported_eligible_blocks": fully_supported,
        "fully_supported_nonempty_block_fraction": fully_supported_fraction,
        "supported_run_length_median": run_median,
        "supported_run_length_p75": run_p75,
        "supported_run_length_p90": run_p90,
        "supported_run_length_max": run_max,
        "dominant_semantic_feature": dominant_feature,
        "dominant_semantic_feature_rate": dominant_rate,
        "semantic_feature_rates": feature_rates,
        "gpr_reuse_distance_counts": profile.get("gpr_reuse_distance_counts", {}),
        "maximum_live_future_gprs_per_block": profile.get(
            "maximum_live_future_gprs_per_block", {}
        ),
        "meets_proceed_band": meets_proceed_band,
    }


def analyze(input_data: dict[str, Any], *, bootstrap_resamples: int = BOOTSTRAP_RESAMPLES) -> dict[str, Any]:
    fixtures = {str(item["fixture_id"]): item for item in input_data["fixtures"]}
    pairs_by_fixture, pair_issues = _group_measured_pairs(input_data["runs"])

    wall_overheads = {
        fixture_id: [pair["wall_overhead_fraction"] for pair in pairs]
        for fixture_id, pairs in pairs_by_fixture.items()
    }
    cpu_overheads = {
        fixture_id: [
            pair["cpu_overhead_fraction"]
            for pair in pairs
            if pair["cpu_overhead_fraction"] is not None
        ]
        for fixture_id, pairs in pairs_by_fixture.items()
    }
    wall_point, wall_low, wall_high = stratified_bootstrap_interval(
        wall_overheads, resamples=bootstrap_resamples
    )

    fixture_timing = {}
    for fixture_id in sorted(fixtures):
        walls = wall_overheads.get(fixture_id, [])
        cpus = cpu_overheads.get(fixture_id, [])
        fixture_timing[fixture_id] = {
            "pair_count": len(walls),
            "median_wall_overhead_fraction": _median(walls),
            "minimum_wall_overhead_fraction": min(walls) if walls else 0.0,
            "maximum_wall_overhead_fraction": max(walls) if walls else 0.0,
            "median_cpu_overhead_fraction": _median(cpus) if cpus else None,
        }

    route_equivalent = not pair_issues and all(
        pair["route_equivalent"]
        for pairs in pairs_by_fixture.values()
        for pair in pairs
    )
    maximum_fixture_median = max(
        (item["median_wall_overhead_fraction"] for item in fixture_timing.values()),
        default=0.0,
    )

    if not route_equivalent:
        distortion_state = "FAIL_ROUTE_DIVERGENCE"
    elif wall_point > 0.03 or maximum_fixture_median > 0.10:
        distortion_state = "FAIL_OVERHEAD"
    elif wall_high > 0.05:
        distortion_state = "INCONCLUSIVE_NOISY_INTERVAL"
    else:
        distortion_state = "PASS"

    profile_summaries = {
        fixture_id: summarize_profile(input_data["profiles"][fixture_id])
        for fixture_id in sorted(fixtures)
    }

    class_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fixture_id, summary in profile_summaries.items():
        class_groups[str(fixtures[fixture_id]["workload_class"])].append(summary)

    class_summaries = {}
    for workload_class, summaries in sorted(class_groups.items()):
        class_summary = {
            "fixture_count": len(summaries),
            "median_supported_operation_fraction": _median(
                item["supported_operation_fraction"] for item in summaries
            ),
            "median_supported_run_length_median": _median(
                item["supported_run_length_median"] for item in summaries
            ),
            "median_supported_run_length_p75": _median(
                item["supported_run_length_p75"] for item in summaries
            ),
            "median_fully_supported_nonempty_block_fraction": _median(
                item["fully_supported_nonempty_block_fraction"] for item in summaries
            ),
            "median_dominant_semantic_feature_rate": _median(
                item["dominant_semantic_feature_rate"] for item in summaries
            ),
        }
        class_summary["meets_proceed_band"] = (
            class_summary["median_supported_operation_fraction"] >= 0.30
            and class_summary["median_supported_run_length_median"] >= 2
            and (
                class_summary["median_supported_run_length_p75"] >= 4
                or class_summary["median_fully_supported_nonempty_block_fraction"] >= 0.10
            )
            and class_summary["median_dominant_semantic_feature_rate"] < 0.50
        )
        class_summaries[workload_class] = class_summary

    passing_classes = sorted(
        workload_class
        for workload_class, summary in class_summaries.items()
        if summary["meets_proceed_band"]
    )
    fixture_supported_fractions = [
        item["supported_operation_fraction"] for item in profile_summaries.values()
    ]
    fixture_run_medians = [
        item["supported_run_length_median"] for item in profile_summaries.values()
    ]

    if distortion_state != "PASS":
        decision = "DO_NOT_PROCEED_MEASUREMENT_DISTORTION"
    elif len(passing_classes) >= 2:
        decision = "PROCEED_TO_MINIMUM_LOWERING_EXPERIMENT"
    elif (
        sum(value < 0.15 for value in fixture_supported_fractions)
        > len(fixture_supported_fractions) / 2
        or sum(value <= 1 for value in fixture_run_medians) > len(fixture_run_medians) / 2
    ):
        decision = "STOP_OR_REDIRECT_CURRENT_BACKEND"
    else:
        decision = "EXPAND_OR_REVISE_SUBSET_BEFORE_LOWERING"

    return {
        "schema_version": 1,
        "analysis": {
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_resamples": bootstrap_resamples,
            "pairing": "within fixture_id and pair_id",
            "overall_estimator": "median of fixture-specific paired-overhead medians",
            "class_estimator": "median of fixture metrics within workload class",
        },
        "distortion_gate": {
            "state": distortion_state,
            "route_equivalent": route_equivalent,
            "pair_issues": pair_issues,
            "overall_median_wall_overhead_fraction": wall_point,
            "paired_bootstrap_95_interval": [wall_low, wall_high],
            "maximum_fixture_median_wall_overhead_fraction": maximum_fixture_median,
            "fixtures": fixture_timing,
        },
        "coverage": {
            "fixtures": profile_summaries,
            "workload_classes": class_summaries,
            "passing_workload_classes": passing_classes,
        },
        "decision": decision,
        "interpretation_boundary": [
            "Compilation-weighted observations are not execution-weighted hot-path coverage.",
            "Duplicate block compilations may contribute more than once.",
            "A proceed verdict permits only the smallest controlled lowering experiment.",
            "No Dolphin speedup, game, device, thermal, or Gate 2 claim follows from this analysis.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bootstrap-resamples", type=int, default=BOOTSTRAP_RESAMPLES)
    args = parser.parse_args()

    result = analyze(json.loads(args.input.read_text()), bootstrap_resamples=args.bootstrap_resamples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
