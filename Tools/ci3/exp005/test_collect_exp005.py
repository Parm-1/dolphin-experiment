#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import os
import sys
import tempfile
import unittest
from collections import defaultdict

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

import collect_exp005 as harness  # noqa: E402


CLASS_BY_INDEX = [
    "integer_control",
    "integer_control",
    "memory_system",
    "memory_system",
    "floating_paired",
    "floating_paired",
    "gpu_pipeline",
    "gpu_pipeline",
]


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def make_valid_profile(*, supported: int = 2):
    supported_runs = {"1": supported} if supported else {}
    profile = {
        "schema": "ci3-powerpc-block-profile",
        "schema_version": 1,
        "observation_unit": "successful_cached_interpreter_block_compilation",
        "execution_weighted": False,
        "unique_blocks": False,
        "duplicate_compilations_possible": True,
        "aggregates": {
            "observed_blocks": 2,
            "broken_blocks": 0,
            "analyzed_operations": 4,
            "eligible_operations": 4,
            "skipped_operations": 0,
            "supported_operations": supported,
            "blocks_with_supported_operations": 2 if supported else 0,
            "fully_supported_eligible_blocks": 0,
            "maximum_live_future_gprs": 2,
            "analyzed_block_lengths": {"2": 2},
            "eligible_block_lengths": {"2": 2},
            "supported_run_lengths": supported_runs,
            "opcode_counts": {"addi": 2, "lwz": 2},
            "gpr_reads_per_operation": [0, 4] + [0] * 31,
            "gpr_writes_per_operation": [0, 4] + [0] * 31,
            "maximum_live_future_gprs_per_block": [0, 0, 2] + [0] * 30,
            "semantic_features": {
                "load_store": 2,
                "floating_point": 0,
                "block_end": 0,
                "exception": 0,
                "carry": 0,
                "overflow": 0,
                "condition_register": 0,
                "fprf": 0,
                "system_state": 0,
                "branch": 0,
            },
            "gpr_reuse_distance": {
                "1": 0,
                "2": 0,
                "3-4": 0,
                "5-8": 0,
                "9-16": 0,
                "17+": 0,
                "external_or_earlier_block": 4,
            },
        },
    }
    return profile


def build_synthetic_freeze(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    fixtures = []
    for index in range(8):
        fixture_id = f"F{index + 1:02d}"
        fixtures.append({
            "fixture_id": fixture_id,
            "candidate_id": f"candidate_{index + 1}",
            "workload_class": CLASS_BY_INDEX[index],
            "selection_reason": "synthetic test",
            "source": {
                "repository": "example/legal-fixtures",
                "commit": "0" * 40,
                "license": "GPL-2.0-or-later",
                "build_target": f"candidate_{index + 1}",
                "relative_output": f"build/{fixture_id}.elf",
            },
            "build": {
                "binary_sha256": "0" * 64,
                "binary_size_bytes": 1,
                "binary_committed": False,
                "configure_command": "configure",
                "build_command_template": "build",
                "toolchain_repository_digest": "image@sha256:" + "0" * 64,
            },
            "route_qualification": {
                "workflow_run": 1,
                "tested_merge_ref": "0" * 40,
                "repetitions": 3,
                "timeout_seconds": 12,
                "video_backend": "Null",
                "cpu_core_configuration": "Dolphin.Core.CPUCore=5",
                "dsp_configuration": "Dolphin.Core.DSPHLE=True",
                "route_signature_sha256": "a" * 64,
                "normalized_output_sha256": "b" * 64,
                "normalized_bytes": 67,
                "normalized_lines": 2,
                "expected_exit_status": -15,
                "expected_termination_stage": "second_sigterm",
                "process_survived_to_timeout": True,
                "profile_created_while_disabled": False,
                "panic_or_crash_seen": False,
                "cached_interpreter_text_marker_seen": False,
                "architectural_result_marker_seen": False,
                "architectural_correctness_claimed": False,
            },
        })

    ids = [f["fixture_id"] for f in fixtures]
    run_index = 0
    warmups = []
    for round_index, condition in enumerate(harness.EXPECTED_WARMUP_ORDER, 1):
        rotated = ids[round_index - 1:] + ids[:round_index - 1]
        for ordinal, fixture_id in enumerate(rotated, 1):
            token = f"W{round_index:02d}-{fixture_id}-{condition}"
            warmups.append({
                "run_index": run_index,
                "phase": "warmup",
                "warmup_round": round_index,
                "fixture_id": fixture_id,
                "fixture_ordinal_in_round": ordinal,
                "condition": condition,
                "fresh_user_directory_token": f"runs/{run_index:03d}-{token}",
                "profile_output_token": f"profiles/warmup/{token}.json" if condition == "treatment" else None,
                "analyzed": False,
            })
            run_index += 1

    measured = []
    for round_index, first in enumerate(harness.EXPECTED_FIRST_CONDITION, 1):
        rotated = ids[round_index - 1:] + ids[:round_index - 1]
        second = "treatment" if first == "baseline" else "baseline"
        for ordinal, fixture_id in enumerate(rotated, 1):
            pair_id = f"R{round_index:02d}-{fixture_id}"
            for pair_position, condition in enumerate((first, second), 1):
                token = f"{pair_id}-P{pair_position}-{condition}"
                measured.append({
                    "run_index": run_index,
                    "phase": "measured",
                    "round": round_index,
                    "pair_id": pair_id,
                    "pair_position": pair_position,
                    "fixture_id": fixture_id,
                    "fixture_ordinal_in_round": ordinal,
                    "condition": condition,
                    "fresh_user_directory_token": f"runs/{run_index:03d}-{token}",
                    "profile_output_token": f"profiles/measured/{pair_id}.json" if condition == "treatment" else None,
                    "analyzed": True,
                })
                run_index += 1

    schedule = {
        "schema_version": 2,
        "experiment_id": harness.EXPERIMENT_ID,
        "stage": "profile_overhead_and_coverage_collection_order_v2",
        "frozen_by": "fixture-manifest-v2.json",
        "fixture_ids": ids,
        "route_contract": {
            "frontend": "dolphin-emu-nogui",
            "arguments": harness.EXPECTED_ROUTE_ARGUMENTS,
            "timeout_seconds": 12,
            "stop_controller": harness.EXPECTED_STOP_CONTROLLER,
            "fresh_process_per_run": True,
            "fresh_user_directory_per_run": True,
            "same_binary_and_settings_between_conditions": True,
        },
        "conditions": {
            "baseline": {
                "DOLPHIN_CI3_BLOCK_PROFILE_PATH": "unset",
                "profile_output_expected": False,
            },
            "treatment": {
                "DOLPHIN_CI3_BLOCK_PROFILE_PATH": "set to the run's unique profile_output_token",
                "profile_output_expected": True,
                "profile_output_must_be_fresh": True,
            },
        },
        "warmup_policy": {
            "round_condition_order": harness.EXPECTED_WARMUP_ORDER,
            "runs_per_fixture": 4,
            "total_runs": 32,
            "profile_outputs_analyzed": False,
            "treatment_profile_outputs_discarded_after_existence_and_schema_checks": True,
        },
        "measured_pair_policy": {
            "pairs_per_fixture": 8,
            "total_pairs": 64,
            "total_runs": 128,
            "first_condition_by_round": harness.EXPECTED_FIRST_CONDITION,
            "pairing_key": ["fixture_id", "pair_id"],
            "conditions_are_adjacent_within_pair": True,
            "baseline_first_pairs_per_fixture": 4,
            "treatment_first_pairs_per_fixture": 4,
        },
        "fixture_order_rule": "test",
        "profile_access_rule": "test",
        "warmups": warmups,
        "measured": measured,
        "total_scheduled_runs": 160,
    }
    schedule_path = root / "run-order-v2.json"
    schedule_path.write_bytes(json_bytes(schedule))
    manifest = {
        "schema_version": 2,
        "experiment_id": harness.EXPERIMENT_ID,
        "stage": "fixture_and_schedule_freeze_v2",
        "state": "FROZEN_BEFORE_PROFILE_ACCESS",
        "date": "2026-08-18",
        "prerequisites": {},
        "selection": {},
        "source": {},
        "fixtures": fixtures,
        "measurement": {
            "schedule_file": "run-order-v2.json",
            "schedule_sha256": hashlib.sha256(schedule_path.read_bytes()).hexdigest(),
            "warmup_runs_per_fixture": 4,
            "measured_pairs_per_fixture": 8,
            "total_warmup_runs": 32,
            "total_measured_pairs": 64,
            "total_measured_runs": 128,
            "total_scheduled_runs": 160,
        },
        "data_boundary": {
            "fixture_binaries_committed": False,
            "raw_logs_committed": False,
            "user_directories_committed": False,
            "profile_outputs_committed": False,
            "guest_instruction_words_committed": False,
            "guest_addresses_committed": False,
            "disassembly_committed": False,
            "proprietary_content_committed": False,
        },
        "interpretation_boundary": [],
        "next_authorized_step": "test",
    }
    manifest_path = root / "fixture-manifest-v2.json"
    manifest_path.write_bytes(json_bytes(manifest))
    return harness.load_frozen_experiment(manifest_path, schedule_path, require_pinned=False)


def stage_complete_collection(root: Path, frozen: harness.FrozenExperiment, *, unstable_fixture: str | None = None):
    private_root = root / "private"
    bounded_root = root / "bounded"
    private_root.mkdir()
    bounded_root.mkdir()
    records = []
    treatment_ordinal: dict[str, int] = defaultdict(int)
    for expected in frozen.ordered_runs:
        treatment = expected["condition"] == "treatment"
        measured_treatment = treatment and expected["phase"] == "measured"
        record = {
            "run_index": expected["run_index"],
            "phase": expected["phase"],
            "fixture_id": expected["fixture_id"],
            "condition": expected["condition"],
            "pair_id": expected.get("pair_id"),
            "pair_position": expected.get("pair_position"),
            "fresh_user_directory_token": expected["fresh_user_directory_token"],
            "profile_output_token": expected.get("profile_output_token"),
            "wall_ns": 1_000_000 + expected["run_index"],
            "exit_status": -15,
            "timed_out": True,
            "termination_stage": "second_sigterm",
            "normalized_sha256": "b" * 64,
            "route_signature_sha256": "a" * 64,
            "normalized_bytes": 67,
            "normalized_lines": 2,
            "panic_or_crash_seen": False,
            "profile_exists": measured_treatment,
            "profile_size_bytes": 1 if measured_treatment else 0,
        }
        if treatment and expected["phase"] == "warmup":
            record["warmup_profile_schema_validated_and_deleted"] = True
        if measured_treatment:
            fixture_id = expected["fixture_id"]
            ordinal = treatment_ordinal[fixture_id]
            treatment_ordinal[fixture_id] += 1
            profile = make_valid_profile()
            if unstable_fixture == fixture_id and ordinal == 7:
                profile = make_valid_profile(supported=1)
            path = harness._safe_join(private_root, expected["profile_output_token"], field="profile_output_token")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(json_bytes(profile))
            record["profile_size_bytes"] = path.stat().st_size
        records.append(record)
    ledger = {
        "schema_version": 1,
        "experiment_id": harness.EXPERIMENT_ID,
        "freeze_merge_commit": harness.EXPECTED_FREEZE_MERGE,
        "schedule_sha256": harness.EXPECTED_SCHEDULE_SHA256,
        "runs": records,
        "measured_profile_contents_opened": False,
    }
    ledger_path = private_root / "ledger.json"
    ledger_path.write_bytes(json_bytes(ledger))
    return private_root, bounded_root, ledger_path, records


class FrozenInputTests(unittest.TestCase):
    def test_synthetic_freeze_is_structurally_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            frozen = build_synthetic_freeze(Path(temporary))
            self.assertEqual(len(frozen.ordered_runs), 160)
            self.assertEqual(len(frozen.fixtures), 8)

    def test_duplicate_treatment_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            build_synthetic_freeze(root)
            schedule_path = root / "run-order-v2.json"
            schedule = json.loads(schedule_path.read_text())
            treatment = [run for run in schedule["measured"] if run["condition"] == "treatment"]
            treatment[1]["profile_output_token"] = treatment[0]["profile_output_token"]
            schedule_path.write_bytes(json_bytes(schedule))
            manifest_path = root / "fixture-manifest-v2.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["measurement"]["schedule_sha256"] = hashlib.sha256(schedule_path.read_bytes()).hexdigest()
            manifest_path.write_bytes(json_bytes(manifest))
            with self.assertRaisesRegex(harness.HarnessError, "reused treatment profile token"):
                harness.load_frozen_experiment(manifest_path, schedule_path, require_pinned=False)

    def test_current_repository_freeze_matches_pins(self):
        repository = Path(__file__).resolve().parents[3]
        manifest = repository / "docs/ci3/experiments/EXP-20260817-005/fixture-manifest-v2.json"
        schedule = repository / "docs/ci3/experiments/EXP-20260817-005/run-order-v2.json"
        if not manifest.exists():
            self.skipTest("test is not running from the Dolphin repository")
        frozen = harness.load_frozen_experiment(manifest, schedule)
        self.assertEqual(len(frozen.ordered_runs), 160)


class ProfileValidationTests(unittest.TestCase):
    def test_valid_profile_is_normalized(self):
        normalized = harness.validate_profile_document(make_valid_profile())
        self.assertEqual(normalized["aggregates"]["supported_operations"], 2)

    def test_prohibited_field_is_rejected(self):
        profile = make_valid_profile()
        profile["aggregates"]["guest_address_samples"] = []
        with self.assertRaisesRegex(harness.HarnessError, "prohibited profile field"):
            harness.validate_profile_document(profile)

    def test_histogram_inconsistency_is_rejected(self):
        profile = make_valid_profile()
        profile["aggregates"]["analyzed_block_lengths"] = {"2": 1}
        with self.assertRaisesRegex(harness.HarnessError, "analyzed block histogram"):
            harness.validate_profile_document(profile)


class CollectionSealTests(unittest.TestCase):
    def test_complete_stable_collection_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frozen = build_synthetic_freeze(root / "freeze")
            collection = root / "collection"
            collection.mkdir()
            private, bounded, ledger, _ = stage_complete_collection(collection, frozen)
            verdict = harness.seal_collection(
                frozen,
                private_root=private,
                ledger_path=ledger,
                bounded_root=bounded,
                delete_private=False,
            )
            self.assertTrue(verdict["gate_passed"])
            self.assertEqual(verdict["stable_fixture_profile_count"], 8)
            aggregate = json.loads((bounded / "collection-aggregate.json").read_text())
            self.assertEqual(len(aggregate["runs"]), 160)
            self.assertFalse(aggregate["data_boundary"]["measured_profiles_opened_before_preflight"])

    def test_missing_run_fails_before_corrupt_profile_is_opened(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frozen = build_synthetic_freeze(root / "freeze")
            collection = root / "collection"
            collection.mkdir()
            private, bounded, ledger, records = stage_complete_collection(collection, frozen)
            records.pop()
            ledger_data = json.loads(ledger.read_text())
            ledger_data["runs"] = records
            ledger.write_bytes(json_bytes(ledger_data))
            first_profile = next((private / "profiles/measured").glob("*.json"))
            first_profile.write_text("not valid JSON", encoding="utf-8")
            with self.assertRaisesRegex(harness.HarnessError, "collection is incomplete"):
                harness.seal_collection(
                    frozen,
                    private_root=private,
                    ledger_path=ledger,
                    bounded_root=bounded,
                    delete_private=False,
                )
            self.assertFalse((bounded / "collection-preflight.json").exists())

    def test_route_drift_fails_preflight(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frozen = build_synthetic_freeze(root / "freeze")
            collection = root / "collection"
            collection.mkdir()
            private, bounded, ledger, records = stage_complete_collection(collection, frozen)
            records[0]["route_signature_sha256"] = "c" * 64
            ledger_data = json.loads(ledger.read_text())
            ledger_data["runs"] = records
            ledger.write_bytes(json_bytes(ledger_data))
            with self.assertRaisesRegex(harness.HarnessError, "route signature drifted"):
                harness.seal_collection(
                    frozen,
                    private_root=private,
                    ledger_path=ledger,
                    bounded_root=bounded,
                    delete_private=False,
                )

    def test_unstable_treatment_profiles_fail_after_preflight(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frozen = build_synthetic_freeze(root / "freeze")
            collection = root / "collection"
            collection.mkdir()
            private, bounded, ledger, _ = stage_complete_collection(collection, frozen, unstable_fixture="F01")
            with self.assertRaisesRegex(harness.HarnessError, "F01 treatment profile is unstable"):
                harness.seal_collection(
                    frozen,
                    private_root=private,
                    ledger_path=ledger,
                    bounded_root=bounded,
                    delete_private=False,
                )
            preflight = json.loads((bounded / "collection-preflight.json").read_text())
            self.assertTrue(preflight["gate_passed"])
            self.assertFalse(preflight["measured_profiles_opened"])
            self.assertFalse((bounded / "collection-verdict.json").exists())


@unittest.skipUnless(os.name == "posix", "signal-controller test requires POSIX")
class ProcessControllerTests(unittest.TestCase):
    def test_second_sigterm_stage_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            child = Path(temporary) / "child.py"
            child.write_text(
                "import os, signal, time\n"
                "count = 0\n"
                "def handler(signum, frame):\n"
                "    global count\n"
                "    count += 1\n"
                "    if count >= 2:\n"
                "        os._exit(23)\n"
                "signal.signal(signal.SIGTERM, handler)\n"
                "print('ready', flush=True)\n"
                "while True: time.sleep(0.01)\n",
                encoding="utf-8",
            )
            result = harness.run_controlled_process(
                [sys.executable, str(child)],
                cwd=Path(temporary),
                environment=os.environ,
                policy=harness.StopPolicy(1.0, 0.2, 0.3),
            )
            self.assertTrue(result.timed_out)
            self.assertEqual(result.termination_stage, "second_sigterm")
            self.assertEqual(result.returncode, 23)
            self.assertIn("ready", result.output)


class NormalizationTests(unittest.TestCase):
    def test_route_normalization_removes_volatile_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            user = root / "user"
            fixture = root / "fixture.elf"
            text = f"2026-08-18 10:20:30 PID=123 0xabcdef01 {root} {user} {fixture}\n"
            normalized = harness.normalize_route_output(
                text,
                repository=root,
                user_directory=user,
                fixture=fixture,
            )
            self.assertNotIn("123", normalized)
            self.assertNotIn("abcdef01", normalized)
            self.assertIn("<REPO>", normalized)


if __name__ == "__main__":
    unittest.main()
