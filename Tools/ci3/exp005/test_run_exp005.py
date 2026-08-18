#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import pathlib
import tempfile
import unittest

from run_exp005 import normalize_output, normalize_profile


class OutputNormalizationTests(unittest.TestCase):
    def test_paths_timestamps_elapsed_and_pid_are_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            repository = root / "repo"
            user = root / "user"
            fixture = root / "fixtures" / "test.dol"
            text = (
                f"2026-08-17 12:34:56.123 {repository} {user} {fixture} "
                "[  1.25s] PID=1234\r\n"
            )
            normalized = normalize_output(
                text,
                repository=repository,
                user_directory=user,
                fixture=fixture,
            )
            self.assertEqual(
                normalized,
                "<TIME> <REPO> <USERDIR> <FIXTURE> [<ELAPSED>] PID=<PID>\n",
            )


class ProfileNormalizationTests(unittest.TestCase):
    def make_profile(self) -> dict:
        return {
            "schema": "ci3-powerpc-block-profile",
            "schema_version": 1,
            "observation_unit": "successful_cached_interpreter_block_compilation",
            "aggregates": {
                "observed_blocks": "10",
                "broken_blocks": "1",
                "analyzed_operations": "100",
                "eligible_operations": "90",
                "skipped_operations": "10",
                "supported_operations": "30",
                "blocks_with_supported_operations": "7",
                "fully_supported_eligible_blocks": "2",
                "maximum_live_future_gprs": "6",
                "eligible_block_lengths": {"0": "1", "9": "9"},
                "supported_run_lengths": {"1": "3", "4": "2"},
                "semantic_features": {"load_store": "20", "branch": "5"},
                "gpr_reuse_distances": {"distance_1": "11", "distance_2": "7"},
                "maximum_live_future_gprs_per_block": ["1", "2", "3"],
            },
        }

    def test_schema_is_converted_without_float_round_trip(self) -> None:
        normalized = normalize_profile(self.make_profile())
        self.assertEqual(normalized["counters"]["eligible_operations"], 90)
        self.assertEqual(normalized["eligible_block_lengths"], {"0": 1, "9": 9})
        self.assertEqual(normalized["semantic_feature_counts"]["load_store"], 20)
        self.assertEqual(
            normalized["maximum_live_future_gprs_per_block"],
            {"0": 1, "1": 2, "2": 3},
        )

    def test_prohibited_raw_guest_field_is_rejected(self) -> None:
        profile = self.make_profile()
        profile["guest_address"] = "0x80000000"
        with self.assertRaisesRegex(ValueError, "prohibited profile field"):
            normalize_profile(profile)


if __name__ == "__main__":
    unittest.main()
