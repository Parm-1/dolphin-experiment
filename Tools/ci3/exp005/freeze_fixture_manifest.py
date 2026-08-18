#!/usr/bin/env python3
"""Deterministically generate or verify the EXP-005 fixture/run-order freeze."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

EXP = "EXP-20260817-005"
DATE = "2026-08-18"
BUILD_MERGE = "70abc18a2fb0d56135dcc35a41d988a50b53c7bc"
BUILD_RUN = 32110199577
BUILD_BLOB = "a02e8596612e34093e4d64af3a3a68681d85320a"
ROUTE_MERGE = "4b67e513f913c77e534aaf50d6b7ecae8780d7b2"
ROUTE_RUN = 32124068535
ROUTE_ARTIFACT = 9320322911
ROUTE_ARTIFACT_SHA = "c98bc4432ae5f7b18b35922a9c6d2f052b5c14128ff4f3df9ad0bb4d3ebf0692"
ROUTE_RESULT_BLOB = "c26e885b6a05da9da3bedc816d25f9e731d5e52b"
ROUTE_MANIFEST_BLOB = "6be307b8d4ed0a52bd56241d674573691592a20c"
ROUTE_RESULT_SHA = "f0cb4bbb718bd442f78e6526d561fb88fbc409ee2fa99546b4391032cc178c94"
ROUTE_TESTED = "01faa904e1caff3195b2d8185416c9d8f43479b1"
EXPECTED = [
    ("cputest_rlw", "integer_control"),
    ("cputest_cr", "integer_control"),
    ("cputest_load", "memory_system"),
    ("cputest_mtspr", "memory_system"),
    ("cputest_frsp", "floating_paired"),
    ("cputest_pairedmove", "floating_paired"),
    ("gxtest_bitfield", "gpu_pipeline"),
    ("gxtest_tev", "gpu_pipeline"),
]
WARM = ["baseline", "treatment", "treatment", "baseline"]
FIRST = ["baseline", "treatment", "treatment", "baseline", "treatment", "baseline", "baseline", "treatment"]
FILES = {
    "fixture-manifest-v2.json": None,
    "run-order-v2.json": None,
    "fixture-freeze-v2.md": None,
    "fixture-freeze-v2-evidence.json": None,
}


def jbytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def digest(value: bytes):
    return hashlib.sha256(value).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def other(condition):
    return "treatment" if condition == "baseline" else "baseline"


def derive(root: Path):
    exp = root / "docs/ci3/experiments" / EXP
    build = load(exp / "build-qualification-v1.json")
    route = load(exp / "route-recon-v2.json")
    rmanifest = load(exp / "route-recon-v2-manifest.json")

    bi = build["interpretation"]
    assert build["experiment_id"] == EXP
    assert bi["selected_fixture_set_build_qualified"] is True
    assert bi["profile_data_generated"] is False and bi["profile_data_examined"] is False
    assert build["build"]["successful_workflow_run"] == BUILD_RUN
    assert route["experiment_id"] == EXP and route["gate_passed"] is True
    assert route["stage"] == "non_profiled_route_reconnaissance_v2"
    assert route["github_actions_run_id"] == ROUTE_RUN and route["dolphin_commit"] == ROUTE_TESTED
    assert route["prerequisite_merge_commit"] == BUILD_MERGE
    assert route["profiler_environment_variable"] == "unset"
    assert route["profile_output_expected"] is False
    assert rmanifest["gate_passed"] is True and rmanifest["github_actions_run_id"] == ROUTE_RUN
    assert rmanifest["tested_head_sha"] == ROUTE_TESTED
    assert rmanifest["route_result_sha256"] == ROUTE_RESULT_SHA
    assert rmanifest["raw_logs_committed"] is False and rmanifest["fixture_binaries_committed"] is False

    candidates = route["candidates"]
    assert [(c["candidate_id"], c["workload_class"]) for c in candidates] == EXPECTED
    assert route["qualified_candidate_count"] == len(EXPECTED)
    assert Counter(c["workload_class"] for c in candidates) == Counter({
        "integer_control": 2, "memory_system": 2, "floating_paired": 2, "gpu_pipeline": 2
    })
    outputs = {item["target"]: item for item in build["executable_outputs"]}
    fixtures = []
    for n, c in enumerate(candidates, 1):
        b = outputs[c["candidate_id"]]
        assert (c["source_relative_output"], c["sha256"], c["size_bytes"]) == (
            b["path"], b["sha256"], b["size_bytes"]
        )
        assert c["route_recon_verdict"] == "ROUTE_CANDIDATE"
        assert c["route_signature_stable"] is True and c["acceptable_launch_stop_route"] is True
        runs = c["runs"]
        assert len(runs) == 3
        singular = lambda key: {run[key] for run in runs}
        for key in ("route_signature_sha256", "normalized_sha256", "normalized_bytes", "normalized_lines", "exit_status", "termination_stage"):
            assert len(singular(key)) == 1
        assert all(run["timed_out"] and run["process_survived_to_timeout"] for run in runs)
        assert not any(run["panic_or_crash_seen"] or run["profile_file_created_while_disabled"] for run in runs)
        fixtures.append({
            "fixture_id": f"F{n:02d}",
            "candidate_id": c["candidate_id"],
            "workload_class": c["workload_class"],
            "selection_reason": "All eight preregistered route candidates qualified; none was removed or ranked using profile, timing, coverage, or performance data.",
            "source": {
                "repository": build["repository"], "commit": build["source_commit"],
                "license": build["source_license"], "build_target": c["candidate_id"],
                "relative_output": c["source_relative_output"],
            },
            "build": {
                "configure_command": build["build"]["configure_command"],
                "build_command_template": build["build"]["build_command"],
                "toolchain_repository_digest": build["toolchain"]["repository_digest"],
                "binary_sha256": c["sha256"], "binary_size_bytes": c["size_bytes"],
                "binary_committed": False,
            },
            "route_qualification": {
                "workflow_run": ROUTE_RUN, "tested_merge_ref": ROUTE_TESTED,
                "repetitions": 3, "timeout_seconds": route["timeout_seconds"],
                "video_backend": route["video_backend"],
                "cpu_core_configuration": route["cpu_core_configuration"],
                "dsp_configuration": route["dsp_configuration"],
                "route_signature_sha256": next(iter(singular("route_signature_sha256"))),
                "normalized_output_sha256": next(iter(singular("normalized_sha256"))),
                "normalized_bytes": next(iter(singular("normalized_bytes"))),
                "normalized_lines": next(iter(singular("normalized_lines"))),
                "expected_exit_status": next(iter(singular("exit_status"))),
                "expected_termination_stage": next(iter(singular("termination_stage"))),
                "process_survived_to_timeout": True, "profile_created_while_disabled": False,
                "panic_or_crash_seen": False,
                "cached_interpreter_text_marker_seen": all(r["cached_interpreter_marker_seen"] for r in runs),
                "architectural_result_marker_seen": False,
                "architectural_correctness_claimed": False,
            },
        })

    ids = [f["fixture_id"] for f in fixtures]
    run_index = 0
    warmups = []
    for rnd, condition in enumerate(WARM, 1):
        rotated = ids[rnd - 1:] + ids[:rnd - 1]
        for ordinal, fid in enumerate(rotated, 1):
            token = f"W{rnd:02d}-{fid}-{condition}"
            warmups.append({
                "run_index": run_index, "phase": "warmup", "warmup_round": rnd,
                "fixture_id": fid, "fixture_ordinal_in_round": ordinal, "condition": condition,
                "fresh_user_directory_token": f"runs/{run_index:03d}-{token}",
                "profile_output_token": f"profiles/warmup/{token}.json" if condition == "treatment" else None,
                "analyzed": False,
            })
            run_index += 1
    measured = []
    for rnd, first in enumerate(FIRST, 1):
        rotated = ids[rnd - 1:] + ids[:rnd - 1]
        for ordinal, fid in enumerate(rotated, 1):
            pair = f"R{rnd:02d}-{fid}"
            for pos, condition in enumerate((first, other(first)), 1):
                token = f"{pair}-P{pos}-{condition}"
                measured.append({
                    "run_index": run_index, "phase": "measured", "round": rnd,
                    "pair_id": pair, "pair_position": pos, "fixture_id": fid,
                    "fixture_ordinal_in_round": ordinal, "condition": condition,
                    "fresh_user_directory_token": f"runs/{run_index:03d}-{token}",
                    "profile_output_token": f"profiles/measured/{pair}.json" if condition == "treatment" else None,
                    "analyzed": True,
                })
                run_index += 1
    schedule = {
        "schema_version": 2, "experiment_id": EXP,
        "stage": "profile_overhead_and_coverage_collection_order_v2",
        "frozen_by": "fixture-manifest-v2.json", "fixture_ids": ids,
        "route_contract": {
            "frontend": "dolphin-emu-nogui",
            "arguments": ["-e", "<fixture>", "-u", "<fresh-user-directory>", "-v", "Null", "-p", "headless", "-C", "Dolphin.Core.CPUCore=5", "-C", "Dolphin.Core.DSPHLE=True"],
            "timeout_seconds": 12,
            "stop_controller": ["wait 12 seconds", "send SIGTERM and wait 3 seconds", "send SIGTERM again and wait 2 seconds", "send SIGKILL only if still alive"],
            "fresh_process_per_run": True, "fresh_user_directory_per_run": True,
            "same_binary_and_settings_between_conditions": True,
        },
        "conditions": {
            "baseline": {"DOLPHIN_CI3_BLOCK_PROFILE_PATH": "unset", "profile_output_expected": False},
            "treatment": {"DOLPHIN_CI3_BLOCK_PROFILE_PATH": "set to the run's unique profile_output_token", "profile_output_expected": True, "profile_output_must_be_fresh": True},
        },
        "warmup_policy": {
            "round_condition_order": WARM, "runs_per_fixture": 4, "total_runs": len(warmups),
            "profile_outputs_analyzed": False,
            "treatment_profile_outputs_discarded_after_existence_and_schema_checks": True,
        },
        "measured_pair_policy": {
            "pairs_per_fixture": 8, "total_pairs": 64, "total_runs": len(measured),
            "first_condition_by_round": FIRST, "pairing_key": ["fixture_id", "pair_id"],
            "conditions_are_adjacent_within_pair": True,
            "baseline_first_pairs_per_fixture": 4, "treatment_first_pairs_per_fixture": 4,
        },
        "fixture_order_rule": "Rotate the fixed fixture list left by round_number - 1; every fixture occupies every measured ordinal position exactly once.",
        "profile_access_rule": "No schema-v1 profile may influence fixture selection or this schedule. Measured profiles may be opened only after this freeze is merged and the complete collection passes completeness checks.",
        "warmups": warmups, "measured": measured, "total_scheduled_runs": 160,
    }

    # Fail closed on schedule incompleteness or imbalance.
    assert [r["run_index"] for r in warmups + measured] == list(range(160))
    wb = defaultdict(list)
    for r in warmups: wb[r["fixture_id"]].append(r["condition"])
    assert all(wb[fid] == WARM for fid in ids)
    pairs, positions, firsts = defaultdict(list), defaultdict(set), defaultdict(list)
    for r in measured:
        pairs[r["pair_id"]].append(r)
        positions[r["fixture_id"]].add(r["fixture_ordinal_in_round"])
        if r["pair_position"] == 1: firsts[r["fixture_id"]].append(r["condition"])
    assert len(pairs) == 64
    for runs in pairs.values():
        runs.sort(key=lambda r: r["pair_position"])
        assert len(runs) == 2 and {r["condition"] for r in runs} == {"baseline", "treatment"}
        assert runs[1]["run_index"] == runs[0]["run_index"] + 1
    assert all(positions[fid] == set(range(1, 9)) and firsts[fid] == FIRST for fid in ids)
    treatment_tokens = [r["profile_output_token"] for r in warmups + measured if r["condition"] == "treatment"]
    assert len(treatment_tokens) == len(set(treatment_tokens))

    schedule_b = jbytes(schedule)
    manifest = {
        "schema_version": 2, "experiment_id": EXP, "stage": "fixture_and_schedule_freeze_v2",
        "state": "FROZEN_BEFORE_PROFILE_ACCESS", "date": DATE,
        "prerequisites": {
            "source_build": {"merge_commit": BUILD_MERGE, "workflow_run": BUILD_RUN, "evidence_blob_sha": BUILD_BLOB},
            "route_reconnaissance": {"merge_commit": ROUTE_MERGE, "workflow_run": ROUTE_RUN, "artifact_id": ROUTE_ARTIFACT, "artifact_sha256": ROUTE_ARTIFACT_SHA, "result_blob_sha": ROUTE_RESULT_BLOB, "manifest_blob_sha": ROUTE_MANIFEST_BLOB, "result_sha256": ROUTE_RESULT_SHA, "tested_merge_ref": ROUTE_TESTED},
        },
        "selection": {
            "rule": "Include every candidate in the preregistered v2 route order only if all eight qualify; any removal, replacement, or reorder requires a new freeze version.",
            "candidate_count": 8, "workload_class_count": 4,
            "fixtures_per_class": dict(sorted(Counter(f["workload_class"] for f in fixtures).items())),
            "profile_data_generated_before_freeze": False, "profile_data_examined_before_freeze": False,
            "coverage_data_used_for_selection": False, "timing_data_used_for_selection": False,
        },
        "source": {"repository": build["repository"], "commit": build["source_commit"], "license": build["source_license"], "toolchain_repository_digest": build["toolchain"]["repository_digest"], "full_upstream_suite_build_qualified": False, "full_upstream_suite_blocker": build["known_full_suite_blocker"]},
        "fixtures": fixtures,
        "measurement": {"schedule_file": "run-order-v2.json", "schedule_sha256": digest(schedule_b), "warmup_runs_per_fixture": 4, "measured_pairs_per_fixture": 8, "total_warmup_runs": 32, "total_measured_pairs": 64, "total_measured_runs": 128, "total_scheduled_runs": 160},
        "data_boundary": {"fixture_binaries_committed": False, "raw_logs_committed": False, "user_directories_committed": False, "profile_outputs_committed": False, "guest_instruction_words_committed": False, "guest_addresses_committed": False, "disassembly_committed": False, "proprietary_content_committed": False},
        "interpretation_boundary": ["Routes are reproducible launch/stop evidence, not architectural test completion.", "The logs did not textually confirm Cached Interpreter or fixture-specific pass markers.", "No profiler overhead, coverage, lowering value, Dolphin speedup, game result, iPhone result, or Gate 2 completion is established."],
        "next_authorized_step": "Implement a fail-closed collection harness that executes this schedule exactly and rejects missing pairs, unstable treatment profiles, or route drift before analysis.",
    }
    manifest_b = jbytes(manifest)
    lines = [
        "# EXP-20260817-005 fixture and paired-run freeze v2", "",
        "**Decision: PASS — fixture set and collection order are frozen before profile access.**", "",
        f"- Source-build prerequisite: `{BUILD_MERGE}` / workflow `{BUILD_RUN}`",
        f"- Route prerequisite: `{ROUTE_MERGE}` / workflow `{ROUTE_RUN}`",
        f"- Route artifact: `{ROUTE_ARTIFACT}` / `sha256:{ROUTE_ARTIFACT_SHA}`",
        "- Selected fixtures: 8; no qualified candidate was removed",
        "- Workload classes: 4; two fixtures per class",
        "- Profile output generated or examined for selection: no",
        f"- Frozen schedule SHA-256: `{digest(schedule_b)}`", "", "## Frozen fixtures", "",
        "| ID | Candidate | Class | Source-relative output | Binary SHA-256 | Route invariant |",
        "|---|---|---|---|---|---|",
    ]
    for f in fixtures:
        q = f["route_qualification"]
        inv = f"3 runs; exit={q['expected_exit_status']}; stage={q['expected_termination_stage']}; signature={q['route_signature_sha256']}"
        lines.append(f"| `{f['fixture_id']}` | `{f['candidate_id']}` | `{f['workload_class']}` | `{f['source']['relative_output']}` | `{f['build']['binary_sha256']}` | `{inv}` |")
    lines += [
        "", "## Frozen collection order", "",
        "- Four warm-ups per fixture: `baseline, treatment, treatment, baseline`.",
        "- Eight adjacent baseline/treatment pairs per fixture.",
        "- Four baseline-first and four treatment-first pairs per fixture.",
        "- Rotated round order puts every fixture in every ordinal position once.",
        "- Baseline leaves `DOLPHIN_CI3_BLOCK_PROFILE_PATH` unset; treatment uses a unique fresh path.",
        "- Measured profiles remain unopened until the complete collection passes completeness checks.",
        "", "## Boundary", "",
        "This is an anti-selection and anti-ordering control. It does not prove hardware-test completion,",
        "textual Cached Interpreter selection, acceptable profiler overhead, hot-work coverage, lowering",
        "value, Dolphin performance, game playability, or iPhone viability. Gate 2 remains open.",
        "", "## Decision", "",
        "Proceed only to a collection harness that consumes these files unchanged and fails closed on an",
        "incomplete pair schedule, schema drift, route drift, or a missing baseline/treatment result.", "",
    ]
    summary_b = "\n".join(lines).encode()
    evidence = {
        "schema_version": 1, "experiment_id": EXP, "stage": "fixture_and_schedule_freeze_v2",
        "gate_passed": True, "fixture_count": 8, "workload_class_count": 4,
        "warmup_run_count": 32, "measured_pair_count": 64, "measured_run_count": 128,
        "total_scheduled_run_count": 160,
        "inputs": {"build-qualification-v1.json": {"git_blob_sha": BUILD_BLOB}, "route-recon-v2.json": {"git_blob_sha": ROUTE_RESULT_BLOB, "sha256": ROUTE_RESULT_SHA}, "route-recon-v2-manifest.json": {"git_blob_sha": ROUTE_MANIFEST_BLOB}},
        "outputs": {"fixture-manifest-v2.json": {"sha256": digest(manifest_b)}, "run-order-v2.json": {"sha256": digest(schedule_b)}, "fixture-freeze-v2.md": {"sha256": digest(summary_b)}},
        "validation": {"all_route_candidates_included": True, "exactly_two_fixtures_per_class": True, "source_build_fields_match": True, "route_invariants_singular": True, "profile_disabled_during_prerequisite_route": True, "pair_schedule_complete": True, "condition_order_balanced": True, "fixture_positions_balanced": True, "treatment_profile_tokens_unique": True, "raw_or_proprietary_data_committed": False},
        "decision": "PASS_FREEZE_AND_PROCEED_TO_FAIL_CLOSED_COLLECTION_HARNESS",
    }
    return {
        "fixture-manifest-v2.json": manifest_b,
        "run-order-v2.json": schedule_b,
        "fixture-freeze-v2.md": summary_b,
        "fixture-freeze-v2-evidence.json": jbytes(evidence),
    }


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    root = args.root.resolve()
    exp = root / "docs/ci3/experiments" / EXP
    outputs = derive(root)
    if args.write:
        for name, data in outputs.items(): (exp / name).write_bytes(data)
        print("wrote deterministic fixture freeze")
        return 0
    errors = []
    for name, expected in outputs.items():
        path = exp / name
        actual = path.read_bytes() if path.exists() else b""
        if actual != expected: errors.append(f"{name}: expected {digest(expected)}, got {digest(actual)}")
    if errors: raise SystemExit("freeze mismatch:\n- " + "\n- ".join(errors))
    print("fixture freeze matches deterministic derivation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
