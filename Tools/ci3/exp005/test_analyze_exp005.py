#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import unittest

from analyze_exp005 import (
    analyze,
    histogram_quantile,
    stratified_bootstrap_interval,
)


def make_profile(*, supported_fraction: float = 0.40, dominant_boundary: int = 20) -> dict:
    eligible = 1_000
    supported = round(eligible * supported_fraction)
    return {
        "counters": {
            "observed_blocks": 100,
            "broken_blocks": 0,
            "analyzed_operations": eligible,
            "eligible_operations": eligible,
            "skipped_operations": 0,
            "supported_operations": supported,
            "blocks_with_supported_operations": 80,
            "fully_supported_eligible_blocks": 20,
            "maximum_live_future_gprs": 8,
        },
        "eligible_block_lengths": {"0": 0, "8": 100},
        "supported_run_lengths": {"1": 10, "2": 30, "4": 50, "8": 10},
        "semantic_feature_counts": {
            "load_store": dominant_boundary,
            "floating_point": 10,
            "block_end": 10,
        },
        "gpr_reuse_distance_counts": {"distance_1": 100, "distance_2": 100},
        "maximum_live_future_gprs_per_block": {"4": 50, "8": 50},
    }


def make_input(*, overhead: float = 0.02, profile: dict | None = None) -> dict:
    fixtures = [
        {"fixture_id": "F01", "workload_class": "integer_control"},
        {"fixture_id": "F02", "workload_class": "memory_translation"},
        {"fixture_id": "F03", "workload_class": "floating_paired"},
    ]
    runs = []
    for fixture in fixtures:
        for pair in range(8):
            base = 1_000_000_000 + pair * 10_000
            pair_id = f"R{pair + 1:02d}-{fixture['fixture_id']}"
            common = {
                "phase": "measured",
                "fixture_id": fixture["fixture_id"],
                "pair_id": pair_id,
                "exit_status": 124,
                "normalized_sha256": "same-route",
                "panic_or_crash_seen": False,
                "matches_frozen_route_invariant": True,
                "profile_valid": True,
                "cpu_user_ns": 800_000_000,
                "cpu_system_ns": 100_000_000,
            }
            runs.append({**common, "condition": "baseline", "wall_ns": base})
            runs.append(
                {
                    **common,
                    "condition": "treatment",
                    "wall_ns": round(base * (1.0 + overhead)),
                    "cpu_user_ns": round(800_000_000 * (1.0 + overhead)),
                }
            )
    profile = profile or make_profile()
    return {
        "fixtures": fixtures,
        "runs": runs,
        "profiles": {fixture["fixture_id"]: profile for fixture in fixtures},
    }


class HistogramTests(unittest.TestCase):
    def test_histogram_quantiles_use_nearest_rank(self) -> None:
        histogram = {"1": 1, "2": 2, "4": 5, "8": 2}
        self.assertEqual(histogram_quantile(histogram, 0.50), 4)
        self.assertEqual(histogram_quantile(histogram, 0.75), 4)
        self.assertEqual(histogram_quantile(histogram, 0.90), 8)

    def test_empty_histogram_is_zero(self) -> None:
        self.assertEqual(histogram_quantile({}, 0.50), 0)


class BootstrapTests(unittest.TestCase):
    def test_stratified_bootstrap_is_deterministic(self) -> None:
        values = {"F01": [0.01, 0.02, 0.03], "F02": [0.02, 0.03, 0.04]}
        first = stratified_bootstrap_interval(values, resamples=2_000, seed=123)
        second = stratified_bootstrap_interval(values, resamples=2_000, seed=123)
        self.assertEqual(first, second)
        self.assertAlmostEqual(first[0], 0.025)


class DecisionTests(unittest.TestCase):
    def test_known_answer_passes_distortion_and_coverage(self) -> None:
        result = analyze(make_input(), bootstrap_resamples=2_000)
        self.assertEqual(result["distortion_gate"]["state"], "PASS")
        self.assertEqual(
            result["decision"], "PROCEED_TO_MINIMUM_LOWERING_EXPERIMENT"
        )
        self.assertGreaterEqual(
            len(result["coverage"]["passing_workload_classes"]), 2
        )

    def test_high_overhead_blocks_lowering_interpretation(self) -> None:
        result = analyze(make_input(overhead=0.12), bootstrap_resamples=1_000)
        self.assertEqual(result["distortion_gate"]["state"], "FAIL_OVERHEAD")
        self.assertEqual(
            result["decision"], "DO_NOT_PROCEED_MEASUREMENT_DISTORTION"
        )

    def test_weak_coverage_stops_current_backend(self) -> None:
        weak_profile = make_profile(supported_fraction=0.10)
        weak_profile["supported_run_lengths"] = {"1": 100}
        result = analyze(
            make_input(profile=weak_profile), bootstrap_resamples=1_000
        )
        self.assertEqual(result["distortion_gate"]["state"], "PASS")
        self.assertEqual(result["decision"], "STOP_OR_REDIRECT_CURRENT_BACKEND")

    def test_route_divergence_fails_distortion_gate(self) -> None:
        data = make_input()
        data["runs"][1]["normalized_sha256"] = "different-route"
        result = analyze(data, bootstrap_resamples=1_000)
        self.assertEqual(
            result["distortion_gate"]["state"], "FAIL_ROUTE_DIVERGENCE"
        )


if __name__ == "__main__":
    unittest.main()
