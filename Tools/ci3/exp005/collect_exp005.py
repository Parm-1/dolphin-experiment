#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed EXP-005 collection harness.

The harness separates collection completeness from profile inspection:

1. validate the exact merged fixture and schedule freeze;
2. execute every scheduled run in a fresh process and private directory;
3. seal the run ledger without parsing measured treatment profiles;
4. only after the complete schedule passes, validate and compare measured profiles;
5. emit bounded aggregate evidence and delete private run data.

No analysis or performance decision is performed here.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import subprocess
import tempfile
import time
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping, Sequence

EXPERIMENT_ID = "EXP-20260817-005"
EXPECTED_FREEZE_MERGE = "278e2b4a36835fbdfbcd65ba87017f8fa0ea3f17"
EXPECTED_MANIFEST_GIT_BLOB = "119e00ec23fdf8421caaffcead98d091a9d81314"
EXPECTED_SCHEDULE_GIT_BLOB = "8c4290d526d69a27e4fff7256b41c6ca79bc1487"
EXPECTED_SCHEDULE_SHA256 = "e21f81d5f343d23a9feef0852f1dbcc8e625bec3a978a44a03e0baba2e33db85"
EXPECTED_ROUTE_ARGUMENTS = [
    "-e",
    "<fixture>",
    "-u",
    "<fresh-user-directory>",
    "-v",
    "Null",
    "-p",
    "headless",
    "-C",
    "Dolphin.Core.CPUCore=5",
    "-C",
    "Dolphin.Core.DSPHLE=True",
]
EXPECTED_STOP_CONTROLLER = [
    "wait 12 seconds",
    "send SIGTERM and wait 3 seconds",
    "send SIGTERM again and wait 2 seconds",
    "send SIGKILL only if still alive",
]
EXPECTED_WARMUP_ORDER = ["baseline", "treatment", "treatment", "baseline"]
EXPECTED_FIRST_CONDITION = [
    "baseline",
    "treatment",
    "treatment",
    "baseline",
    "treatment",
    "baseline",
    "baseline",
    "treatment",
]
MAX_U64 = (1 << 64) - 1

ROOT_PROFILE_KEYS = {
    "schema",
    "schema_version",
    "observation_unit",
    "execution_weighted",
    "unique_blocks",
    "duplicate_compilations_possible",
    "aggregates",
}
AGGREGATE_COUNT_KEYS = {
    "observed_blocks",
    "broken_blocks",
    "analyzed_operations",
    "eligible_operations",
    "skipped_operations",
    "supported_operations",
    "blocks_with_supported_operations",
    "fully_supported_eligible_blocks",
    "maximum_live_future_gprs",
}
AGGREGATE_MAP_KEYS = {
    "analyzed_block_lengths",
    "eligible_block_lengths",
    "supported_run_lengths",
    "opcode_counts",
}
AGGREGATE_ARRAY_KEYS = {
    "gpr_reads_per_operation",
    "gpr_writes_per_operation",
    "maximum_live_future_gprs_per_block",
}
AGGREGATE_OBJECT_KEYS = {"semantic_features", "gpr_reuse_distance"}
SEMANTIC_FEATURE_KEYS = {
    "load_store",
    "floating_point",
    "block_end",
    "exception",
    "carry",
    "overflow",
    "condition_register",
    "fprf",
    "system_state",
    "branch",
}
REUSE_DISTANCE_KEYS = {
    "1",
    "2",
    "3-4",
    "5-8",
    "9-16",
    "17+",
    "external_or_earlier_block",
}
PROHIBITED_PROFILE_KEY_FRAGMENTS = (
    "guest_address",
    "instruction_word",
    "instruction_bytes",
    "disassembly",
    "ordered_trace",
    "title_id",
    "user_identifier",
    "absolute_path",
    "guest_pc",
    "physical_address",
)
VOLATILE_PATTERNS = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\b"), "<TIME>"),
    (re.compile(r"\[[ ]*\d+(?:\.\d+)?s\]"), "[<ELAPSED>]"),
    (re.compile(r"\b(?:pid|PID|tid|TID)[=: ]+\d+\b"), "ID=<ID>"),
    (re.compile(r"0x[0-9a-fA-F]{6,}"), "<HEX>"),
]
ROUTE_KEYWORDS = (
    "dolphin",
    "cached interpreter",
    "cpu core",
    "boot",
    "video backend",
    "null",
    "dsp",
    "ios",
    "shutdown",
    "panic",
    "fatal",
    "assert",
    "error",
    "warning",
    "hwtest",
    "gekko",
    "powerpc",
)
CRASH_TERMS = (
    "panic alert",
    "segmentation fault",
    "assertion failed",
    "fatal error",
    "terminate called",
    "stack trace:",
)


class HarnessError(RuntimeError):
    """Expected fail-closed validation error."""


@dataclasses.dataclass(frozen=True)
class FrozenExperiment:
    manifest: dict[str, Any]
    schedule: dict[str, Any]
    fixtures: dict[str, dict[str, Any]]
    ordered_runs: tuple[dict[str, Any], ...]


@dataclasses.dataclass(frozen=True)
class StopPolicy:
    timeout_seconds: float
    first_term_wait_seconds: float
    second_term_wait_seconds: float


@dataclasses.dataclass(frozen=True)
class ProcessResult:
    returncode: int
    output: str
    timed_out: bool
    termination_stage: str
    wall_ns: int


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()  # noqa: S324 - Git object identity.


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(path)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HarnessError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_strict(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise HarnessError(f"cannot load JSON {path}: {error}") from error


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HarnessError(message)


def _safe_relative_token(token: str, *, field: str) -> PurePosixPath:
    path = PurePosixPath(token)
    _require(bool(token), f"{field} is empty")
    _require(not path.is_absolute(), f"{field} must be relative: {token}")
    _require(".." not in path.parts and "." not in path.parts, f"unsafe {field}: {token}")
    _require("\\" not in token, f"{field} must use POSIX separators: {token}")
    return path


def _safe_join(root: Path, token: str, *, field: str) -> Path:
    relative = _safe_relative_token(token, field=field)
    result = root.joinpath(*relative.parts)
    resolved_root = root.resolve()
    resolved_parent = result.parent.resolve()
    _require(
        resolved_parent == resolved_root or resolved_root in resolved_parent.parents,
        f"{field} escapes collection root: {token}",
    )
    return result


def _validate_schedule_structure(manifest: Mapping[str, Any], schedule: Mapping[str, Any]) -> None:
    _require(manifest.get("schema_version") == 2, "fixture manifest schema_version must be 2")
    _require(manifest.get("experiment_id") == EXPERIMENT_ID, "wrong fixture experiment_id")
    _require(manifest.get("state") == "FROZEN_BEFORE_PROFILE_ACCESS", "fixture manifest is not frozen")
    _require(schedule.get("schema_version") == 2, "run-order schema_version must be 2")
    _require(schedule.get("experiment_id") == EXPERIMENT_ID, "wrong schedule experiment_id")
    _require(
        schedule.get("stage") == "profile_overhead_and_coverage_collection_order_v2",
        "wrong schedule stage",
    )
    data_boundary = manifest.get("data_boundary")
    _require(isinstance(data_boundary, dict), "missing data boundary")
    _require(data_boundary and all(value is False for value in data_boundary.values()), "data boundary changed")

    route = schedule.get("route_contract")
    _require(isinstance(route, dict), "missing route contract")
    _require(route.get("frontend") == "dolphin-emu-nogui", "wrong route frontend")
    _require(route.get("arguments") == EXPECTED_ROUTE_ARGUMENTS, "route arguments drifted")
    _require(route.get("timeout_seconds") == 12, "route timeout drifted")
    _require(route.get("stop_controller") == EXPECTED_STOP_CONTROLLER, "stop controller drifted")
    _require(route.get("fresh_process_per_run") is True, "fresh-process guarantee missing")
    _require(route.get("fresh_user_directory_per_run") is True, "fresh-user-dir guarantee missing")
    _require(route.get("same_binary_and_settings_between_conditions") is True, "condition parity guarantee missing")

    conditions = schedule.get("conditions")
    _require(isinstance(conditions, dict) and set(conditions) == {"baseline", "treatment"}, "condition set drifted")
    _require(conditions["baseline"].get("DOLPHIN_CI3_BLOCK_PROFILE_PATH") == "unset", "baseline profiler state drifted")
    _require(conditions["baseline"].get("profile_output_expected") is False, "baseline output expectation drifted")
    _require(
        conditions["treatment"].get("DOLPHIN_CI3_BLOCK_PROFILE_PATH")
        == "set to the run's unique profile_output_token",
        "treatment profiler state drifted",
    )
    _require(conditions["treatment"].get("profile_output_expected") is True, "treatment output expectation drifted")
    _require(conditions["treatment"].get("profile_output_must_be_fresh") is True, "treatment freshness guarantee missing")

    fixtures = manifest.get("fixtures")
    fixture_ids = schedule.get("fixture_ids")
    _require(isinstance(fixtures, list) and len(fixtures) == 8, "expected exactly eight frozen fixtures")
    _require(isinstance(fixture_ids, list) and len(fixture_ids) == 8, "expected eight scheduled fixture IDs")
    observed_ids = [fixture.get("fixture_id") for fixture in fixtures]
    _require(observed_ids == fixture_ids, "fixture order differs between manifest and schedule")
    _require(len(set(observed_ids)) == len(observed_ids), "duplicate fixture ID")
    _require(
        Counter(fixture.get("workload_class") for fixture in fixtures)
        == Counter({"integer_control": 2, "memory_system": 2, "floating_paired": 2, "gpu_pipeline": 2}),
        "fixture class balance drifted",
    )

    warmups = schedule.get("warmups")
    measured = schedule.get("measured")
    _require(isinstance(warmups, list) and len(warmups) == 32, "expected 32 warm-up runs")
    _require(isinstance(measured, list) and len(measured) == 128, "expected 128 measured runs")
    ordered = warmups + measured
    _require(schedule.get("total_scheduled_runs") == 160, "total scheduled run count drifted")
    _require([run.get("run_index") for run in ordered] == list(range(160)), "run indices are incomplete or reordered")

    user_tokens: set[str] = set()
    profile_tokens: set[str] = set()
    for run in ordered:
        _require(run.get("fixture_id") in observed_ids, f"unknown fixture in run {run.get('run_index')}")
        _require(run.get("condition") in {"baseline", "treatment"}, "unknown condition")
        user_token = run.get("fresh_user_directory_token")
        _require(isinstance(user_token, str), "missing user-directory token")
        _safe_relative_token(user_token, field="fresh_user_directory_token")
        _require(user_token not in user_tokens, f"reused user-directory token: {user_token}")
        user_tokens.add(user_token)
        profile_token = run.get("profile_output_token")
        if run["condition"] == "baseline":
            _require(profile_token is None, "baseline has a profile-output token")
        else:
            _require(isinstance(profile_token, str), "treatment lacks a profile-output token")
            _safe_relative_token(profile_token, field="profile_output_token")
            _require(profile_token not in profile_tokens, f"reused treatment profile token: {profile_token}")
            profile_tokens.add(profile_token)
        expected_phase = "warmup" if run in warmups else "measured"
        _require(run.get("phase") == expected_phase, f"phase mismatch at run {run.get('run_index')}")
        _require(run.get("analyzed") is (expected_phase == "measured"), "analyzed flag drifted")

    warm_by_fixture: dict[str, list[str]] = defaultdict(list)
    for run in warmups:
        warm_by_fixture[str(run["fixture_id"])].append(str(run["condition"]))
    _require(all(warm_by_fixture[fid] == EXPECTED_WARMUP_ORDER for fid in observed_ids), "warm-up order drifted")

    pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    positions: dict[str, set[int]] = defaultdict(set)
    firsts: dict[str, list[str]] = defaultdict(list)
    for run in measured:
        pair_id = run.get("pair_id")
        _require(isinstance(pair_id, str), "measured run lacks pair_id")
        pairs[pair_id].append(run)
        position = run.get("fixture_ordinal_in_round")
        _require(isinstance(position, int), "missing fixture ordinal")
        positions[str(run["fixture_id"])].add(position)
        if run.get("pair_position") == 1:
            firsts[str(run["fixture_id"])].append(str(run["condition"]))
    _require(len(pairs) == 64, "expected 64 measured pairs")
    for pair_id, runs in pairs.items():
        runs.sort(key=lambda item: int(item["pair_position"]))
        _require(len(runs) == 2, f"pair {pair_id} is incomplete")
        _require([run["pair_position"] for run in runs] == [1, 2], f"pair {pair_id} positions drifted")
        _require({run["condition"] for run in runs} == {"baseline", "treatment"}, f"pair {pair_id} condition set drifted")
        _require(runs[1]["run_index"] == runs[0]["run_index"] + 1, f"pair {pair_id} is not adjacent")
        _require(runs[0]["fixture_id"] == runs[1]["fixture_id"], f"pair {pair_id} crosses fixtures")
    for fixture_id in observed_ids:
        _require(positions[fixture_id] == set(range(1, 9)), f"fixture position balance drifted for {fixture_id}")
        _require(firsts[fixture_id] == EXPECTED_FIRST_CONDITION, f"first-condition order drifted for {fixture_id}")


def load_frozen_experiment(manifest_path: Path, schedule_path: Path, *, require_pinned: bool = True) -> FrozenExperiment:
    manifest_bytes = manifest_path.read_bytes()
    schedule_bytes = schedule_path.read_bytes()
    manifest = load_json_strict(manifest_path)
    schedule = load_json_strict(schedule_path)
    _require(isinstance(manifest, dict) and isinstance(schedule, dict), "frozen files must contain JSON objects")
    _validate_schedule_structure(manifest, schedule)
    schedule_sha = _sha256_bytes(schedule_bytes)
    _require(manifest["measurement"]["schedule_sha256"] == schedule_sha, "manifest schedule hash mismatch")
    if require_pinned:
        _require(_git_blob_sha(manifest_bytes) == EXPECTED_MANIFEST_GIT_BLOB, "fixture manifest differs from merged freeze")
        _require(_git_blob_sha(schedule_bytes) == EXPECTED_SCHEDULE_GIT_BLOB, "run order differs from merged freeze")
        _require(schedule_sha == EXPECTED_SCHEDULE_SHA256, "run-order SHA-256 differs from merged freeze")
    fixtures = {str(item["fixture_id"]): item for item in manifest["fixtures"]}
    return FrozenExperiment(
        manifest=manifest,
        schedule=schedule,
        fixtures=fixtures,
        ordered_runs=tuple(schedule["warmups"] + schedule["measured"]),
    )


def normalize_route_output(text: str, *, repository: Path, user_directory: Path, fixture: Path) -> str:
    path_replacements: list[tuple[str, str]] = []
    for path, replacement in (
        (repository, "<REPO>"),
        (user_directory, "<USERDIR>"),
        (fixture, "<FIXTURE>"),
    ):
        path_replacements.extend(
            (spelling, replacement)
            for spelling in {str(path), str(path.resolve())}
            if spelling
        )
    # Replace nested paths before their parents, and handle macOS aliases such as
    # /var versus /private/var without weakening the normalized route contract.
    for old, replacement in sorted(
        path_replacements, key=lambda item: len(item[0]), reverse=True
    ):
        text = text.replace(old, replacement)
    text = text.replace("\r\n", "\n").replace("\x00", "")
    for pattern, replacement in VOLATILE_PATTERNS:
        text = pattern.sub(replacement, text)
    return re.sub(r"[ \t]+", " ", text)


def route_signature(normalized: str) -> str:
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    selected = [line for line in lines if any(keyword in line.lower() for keyword in ROUTE_KEYWORDS)]
    if not selected:
        selected = lines[:64]
    return "\n".join(selected[:256]) + ("\n" if selected else "")


def _collect_user_logs(stdout: str, user_directory: Path) -> str:
    text = stdout
    for log in sorted(user_directory.rglob("*.log")):
        try:
            text += "\n<LOGFILE>\n" + log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return text


def run_controlled_process(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    policy: StopPolicy,
) -> ProcessResult:
    started = time.perf_counter_ns()
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=dict(environment),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    timed_out = False
    stage = "natural_exit"
    try:
        output, _ = process.communicate(timeout=policy.timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        stage = "first_sigterm"
        process.send_signal(signal.SIGTERM)
        try:
            output, _ = process.communicate(timeout=policy.first_term_wait_seconds)
        except subprocess.TimeoutExpired:
            stage = "second_sigterm"
            process.send_signal(signal.SIGTERM)
            try:
                output, _ = process.communicate(timeout=policy.second_term_wait_seconds)
            except subprocess.TimeoutExpired:
                stage = "sigkill_after_two_sigterm"
                process.kill()
                output, _ = process.communicate()
    return ProcessResult(
        returncode=int(process.returncode),
        output=output,
        timed_out=timed_out,
        termination_stage=stage,
        wall_ns=time.perf_counter_ns() - started,
    )


def _validate_nonnegative_u64(value: Any, *, field: str) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool), f"{field} must be an integer")
    _require(0 <= value <= MAX_U64, f"{field} is outside u64 range")
    return value


def _walk_profile_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            _require(
                not any(fragment in lowered for fragment in PROHIBITED_PROFILE_KEY_FRAGMENTS),
                f"prohibited profile field: {key}",
            )
            _walk_profile_keys(child)
    elif isinstance(value, list):
        for child in value:
            _walk_profile_keys(child)


def validate_profile_document(value: Any) -> dict[str, Any]:
    _require(isinstance(value, dict), "profile root must be an object")
    _walk_profile_keys(value)
    _require(set(value) == ROOT_PROFILE_KEYS, "profile root schema drifted")
    _require(value["schema"] == "ci3-powerpc-block-profile", "wrong profile schema")
    _require(value["schema_version"] == 1, "wrong profile schema_version")
    _require(value["observation_unit"] == "successful_cached_interpreter_block_compilation", "wrong observation unit")
    _require(value["execution_weighted"] is False, "profile unexpectedly execution-weighted")
    _require(value["unique_blocks"] is False, "profile unexpectedly claims unique blocks")
    _require(value["duplicate_compilations_possible"] is True, "duplicate-compilation boundary drifted")
    aggregates = value["aggregates"]
    _require(isinstance(aggregates, dict), "aggregates must be an object")
    expected_aggregate_keys = AGGREGATE_COUNT_KEYS | AGGREGATE_MAP_KEYS | AGGREGATE_ARRAY_KEYS | AGGREGATE_OBJECT_KEYS
    _require(set(aggregates) == expected_aggregate_keys, "aggregate schema drifted")

    normalized: dict[str, Any] = {}
    for key in sorted(AGGREGATE_COUNT_KEYS):
        normalized[key] = _validate_nonnegative_u64(aggregates[key], field=key)
    for key in sorted(AGGREGATE_MAP_KEYS):
        mapping = aggregates[key]
        _require(isinstance(mapping, dict), f"{key} must be an object")
        normalized[key] = {
            str(map_key): _validate_nonnegative_u64(count, field=f"{key}.{map_key}")
            for map_key, count in sorted(mapping.items(), key=lambda item: str(item[0]))
        }
    for key in sorted(AGGREGATE_ARRAY_KEYS):
        sequence = aggregates[key]
        _require(isinstance(sequence, list), f"{key} must be an array")
        _require(len(sequence) == 33, f"{key} must contain 33 GPR-cardinality buckets")
        normalized[key] = [
            _validate_nonnegative_u64(count, field=f"{key}[{index}]")
            for index, count in enumerate(sequence)
        ]
    semantic = aggregates["semantic_features"]
    _require(isinstance(semantic, dict) and set(semantic) == SEMANTIC_FEATURE_KEYS, "semantic feature schema drifted")
    normalized["semantic_features"] = {
        key: _validate_nonnegative_u64(semantic[key], field=f"semantic_features.{key}")
        for key in sorted(semantic)
    }
    reuse = aggregates["gpr_reuse_distance"]
    _require(isinstance(reuse, dict) and set(reuse) == REUSE_DISTANCE_KEYS, "reuse-distance schema drifted")
    normalized["gpr_reuse_distance"] = {
        key: _validate_nonnegative_u64(reuse[key], field=f"gpr_reuse_distance.{key}")
        for key in sorted(reuse)
    }

    observed = normalized["observed_blocks"]
    analyzed = normalized["analyzed_operations"]
    eligible = normalized["eligible_operations"]
    supported = normalized["supported_operations"]
    _require(normalized["broken_blocks"] <= observed, "broken_blocks exceeds observed_blocks")
    _require(normalized["blocks_with_supported_operations"] <= observed, "supported block count exceeds observed blocks")
    _require(normalized["fully_supported_eligible_blocks"] <= observed, "fully supported block count exceeds observed blocks")
    _require(supported <= eligible <= analyzed, "operation count ordering is impossible")
    _require(normalized["skipped_operations"] + eligible == analyzed, "skipped + eligible must equal analyzed")
    def numeric_histogram_total(mapping: Mapping[str, int], *, field: str) -> tuple[int, int]:
        weighted = 0
        count = 0
        for raw_key, bucket_count in mapping.items():
            _require(raw_key.isdigit(), f"{field} contains a non-numeric bucket: {raw_key}")
            bucket = int(raw_key)
            weighted += bucket * bucket_count
            count += bucket_count
        return count, weighted

    analyzed_block_count, analyzed_weighted = numeric_histogram_total(
        normalized["analyzed_block_lengths"], field="analyzed_block_lengths"
    )
    eligible_block_count, eligible_weighted = numeric_histogram_total(
        normalized["eligible_block_lengths"], field="eligible_block_lengths"
    )
    _, supported_weighted = numeric_histogram_total(
        normalized["supported_run_lengths"], field="supported_run_lengths"
    )
    _require(analyzed_block_count == observed, "analyzed block histogram does not sum to observed blocks")
    _require(eligible_block_count == observed, "eligible block histogram does not sum to observed blocks")
    _require(analyzed_weighted == analyzed, "analyzed block histogram weight does not equal analyzed operations")
    _require(eligible_weighted == eligible, "eligible block histogram weight does not equal eligible operations")
    _require(supported_weighted == supported, "supported-run histogram weight does not equal supported operations")
    _require(sum(normalized["opcode_counts"].values()) == analyzed, "opcode histogram does not sum to analyzed operations")
    _require(sum(normalized["gpr_reads_per_operation"]) == eligible, "GPR-read histogram does not sum to eligible operations")
    _require(sum(normalized["gpr_writes_per_operation"]) == eligible, "GPR-write histogram does not sum to eligible operations")
    _require(sum(normalized["maximum_live_future_gprs_per_block"]) == observed, "live-future histogram does not sum to observed blocks")
    _require(normalized["maximum_live_future_gprs"] <= 32, "maximum live-future GPR count exceeds 32")
    nonzero_live = [index for index, count in enumerate(normalized["maximum_live_future_gprs_per_block"]) if count]
    expected_max_live = max(nonzero_live, default=0)
    _require(normalized["maximum_live_future_gprs"] == expected_max_live, "maximum live-future GPR scalar disagrees with histogram")
    total_gpr_reads = sum(index * count for index, count in enumerate(normalized["gpr_reads_per_operation"]))
    _require(sum(normalized["gpr_reuse_distance"].values()) == total_gpr_reads, "reuse-distance counts do not equal total GPR reads")
    _require(all(count <= eligible for count in normalized["semantic_features"].values()), "semantic feature count exceeds eligible operations")
    return {
        "schema": value["schema"],
        "schema_version": value["schema_version"],
        "observation_unit": value["observation_unit"],
        "execution_weighted": value["execution_weighted"],
        "unique_blocks": value["unique_blocks"],
        "duplicate_compilations_possible": value["duplicate_compilations_possible"],
        "aggregates": normalized,
    }


def load_and_validate_profile(path: Path) -> dict[str, Any]:
    return validate_profile_document(load_json_strict(path))


def _route_record_matches(run: Mapping[str, Any], fixture: Mapping[str, Any]) -> None:
    qualification = fixture["route_qualification"]
    _require(run.get("exit_status") == qualification["expected_exit_status"], "exit status drifted")
    _require(run.get("termination_stage") == qualification["expected_termination_stage"], "termination stage drifted")
    _require(run.get("timed_out") is qualification["process_survived_to_timeout"], "timeout state drifted")
    _require(run.get("normalized_sha256") == qualification["normalized_output_sha256"], "normalized route output drifted")
    _require(run.get("route_signature_sha256") == qualification["route_signature_sha256"], "route signature drifted")
    _require(run.get("panic_or_crash_seen") is False, "crash marker seen")


def validate_collection_preflight(
    frozen: FrozenExperiment,
    records: Sequence[Mapping[str, Any]],
    *,
    private_root: Path,
) -> dict[str, Any]:
    _require(len(records) == len(frozen.ordered_runs), "collection is incomplete")
    _require([record.get("run_index") for record in records] == list(range(len(records))), "ledger indices are incomplete or reordered")
    expected_by_index = {int(run["run_index"]): run for run in frozen.ordered_runs}
    treatment_paths: set[Path] = set()
    pair_conditions: dict[str, set[str]] = defaultdict(set)
    pair_counts: Counter[str] = Counter()
    for record in records:
        run_index = int(record["run_index"])
        expected = expected_by_index[run_index]
        for field in (
            "phase",
            "fixture_id",
            "condition",
            "fresh_user_directory_token",
            "profile_output_token",
        ):
            _require(record.get(field) == expected.get(field), f"ledger field {field} drifted at run {run_index}")
        if expected["phase"] == "measured":
            _require(record.get("pair_id") == expected.get("pair_id"), f"pair_id drifted at run {run_index}")
            _require(record.get("pair_position") == expected.get("pair_position"), f"pair_position drifted at run {run_index}")
            pair_id = str(expected["pair_id"])
            pair_counts[pair_id] += 1
            pair_conditions[pair_id].add(str(expected["condition"]))
        fixture = frozen.fixtures[str(expected["fixture_id"])]
        _route_record_matches(record, fixture)
        profile_token = expected.get("profile_output_token")
        if expected["condition"] == "baseline":
            _require(record.get("profile_exists") is False, f"baseline profile exists at run {run_index}")
        elif expected["phase"] == "warmup":
            _require(record.get("profile_exists") is False, f"warm-up profile was not deleted at run {run_index}")
            _require(
                record.get("warmup_profile_schema_validated_and_deleted") is True,
                f"warm-up treatment profile was not schema-validated at run {run_index}",
            )
        else:
            _require(record.get("profile_exists") is True, f"treatment profile missing at run {run_index}")
            _require(isinstance(profile_token, str), "treatment token missing")
            profile_path = _safe_join(private_root, profile_token, field="profile_output_token")
            _require(profile_path.is_file(), f"treatment profile file missing at run {run_index}")
            _require(profile_path.stat().st_size > 0, f"treatment profile is empty at run {run_index}")
            _require(profile_path not in treatment_paths, f"treatment profile path reused: {profile_token}")
            treatment_paths.add(profile_path)
    _require(len(pair_counts) == 64 and all(count == 2 for count in pair_counts.values()), "measured pair set is incomplete")
    _require(all(conditions == {"baseline", "treatment"} for conditions in pair_conditions.values()), "measured pair condition set is incomplete")
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "stage": "collection_preflight",
        "gate_passed": True,
        "run_count": len(records),
        "warmup_run_count": sum(record["phase"] == "warmup" for record in records),
        "measured_run_count": sum(record["phase"] == "measured" for record in records),
        "measured_pair_count": len(pair_counts),
        "treatment_profile_count": len(treatment_paths),
        "measured_profiles_opened": False,
        "decision": "PASS_OPEN_MEASURED_PROFILES_FOR_SCHEMA_AND_STABILITY_VALIDATION",
    }


def validate_measured_profiles(
    frozen: FrozenExperiment,
    records: Sequence[Mapping[str, Any]],
    *,
    private_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    profiles_by_fixture: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for record in records:
        if record["phase"] != "measured" or record["condition"] != "treatment":
            continue
        token = str(record["profile_output_token"])
        path = _safe_join(private_root, token, field="profile_output_token")
        document = load_and_validate_profile(path)
        canonical = _json_bytes(document)
        profiles_by_fixture[str(record["fixture_id"])].append((_sha256_bytes(canonical), document))

    _require(set(profiles_by_fixture) == set(frozen.fixtures), "not every fixture produced measured profiles")
    representative: dict[str, dict[str, Any]] = {}
    stability: dict[str, Any] = {}
    for fixture_id in frozen.schedule["fixture_ids"]:
        entries = profiles_by_fixture[fixture_id]
        _require(len(entries) == 8, f"fixture {fixture_id} does not have eight measured treatment profiles")
        hashes = [entry[0] for entry in entries]
        unique_hashes = sorted(set(hashes))
        _require(len(unique_hashes) == 1, f"fixture {fixture_id} treatment profile is unstable")
        representative[fixture_id] = entries[0][1]
        stability[fixture_id] = {
            "measured_profile_count": len(entries),
            "unique_normalized_profile_count": 1,
            "normalized_profile_sha256": unique_hashes[0],
            "stable": True,
        }
    return representative, stability


def seal_collection(
    frozen: FrozenExperiment,
    *,
    private_root: Path,
    ledger_path: Path,
    bounded_root: Path,
    delete_private: bool = True,
) -> dict[str, Any]:
    ledger = load_json_strict(ledger_path)
    _require(isinstance(ledger, dict), "ledger must be an object")
    _require(ledger.get("schema_version") == 1, "ledger schema drifted")
    _require(ledger.get("experiment_id") == EXPERIMENT_ID, "ledger experiment_id drifted")
    records = ledger.get("runs")
    _require(isinstance(records, list), "ledger runs must be an array")

    preflight = validate_collection_preflight(frozen, records, private_root=private_root)
    _atomic_write(bounded_root / "collection-preflight.json", _json_bytes(preflight))

    try:
        profiles, stability = validate_measured_profiles(frozen, records, private_root=private_root)
    except Exception as error:
        _atomic_write(
            bounded_root / "profile-validation-failure.json",
            _json_bytes({
                "schema_version": 1,
                "experiment_id": EXPERIMENT_ID,
                "stage": "measured_profile_validation_failure",
                "measured_profiles_opened": True,
                "error_type": type(error).__name__,
                "decision": "FAIL_CLOSED_DO_NOT_ANALYZE",
            }),
        )
        raise
    bounded_records = []
    for record in records:
        bounded_records.append({
            key: record[key]
            for key in (
                "run_index",
                "phase",
                "fixture_id",
                "condition",
                "pair_id",
                "pair_position",
                "wall_ns",
                "exit_status",
                "timed_out",
                "termination_stage",
                "normalized_sha256",
                "route_signature_sha256",
                "normalized_bytes",
                "normalized_lines",
                "panic_or_crash_seen",
                "profile_exists",
                "profile_size_bytes",
            )
            if key in record
        })
    bounded_collection = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "stage": "complete_collection_after_profile_validation",
        "freeze_merge_commit": EXPECTED_FREEZE_MERGE,
        "schedule_sha256": EXPECTED_SCHEDULE_SHA256,
        "runs": bounded_records,
        "profiles": profiles,
        "profile_stability": stability,
        "data_boundary": {
            "raw_logs_retained": False,
            "user_directories_retained": False,
            "fixture_binaries_retained": False,
            "absolute_paths_retained": False,
            "measured_profiles_opened_before_preflight": False,
        },
    }
    collection_bytes = _json_bytes(bounded_collection)
    _atomic_write(bounded_root / "collection-aggregate.json", collection_bytes)
    verdict = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "stage": "fail_closed_collection_harness",
        "gate_passed": True,
        "run_count": len(records),
        "measured_pair_count": 64,
        "stable_fixture_profile_count": len(stability),
        "collection_aggregate_sha256": _sha256_bytes(collection_bytes),
        "analysis_performed": False,
        "performance_claim_made": False,
        "decision": "PASS_COLLECTION_INTEGRITY_AND_PROCEED_TO_SEPARATE_ANALYSIS_GATE",
    }
    _atomic_write(bounded_root / "collection-verdict.json", _json_bytes(verdict))
    if delete_private:
        shutil.rmtree(private_root)
    return verdict


def _fixture_path(fixtures_root: Path, fixture: Mapping[str, Any]) -> Path:
    relative = _safe_relative_token(str(fixture["source"]["relative_output"]), field="source.relative_output")
    return fixtures_root.joinpath(*relative.parts)


def _build_command(dolphin: Path, schedule: Mapping[str, Any], *, fixture: Path, user_directory: Path) -> list[str]:
    command = [str(dolphin)]
    for argument in schedule["route_contract"]["arguments"]:
        if argument == "<fixture>":
            command.append(str(fixture))
        elif argument == "<fresh-user-directory>":
            command.append(str(user_directory))
        else:
            command.append(str(argument))
    return command


def collect(
    frozen: FrozenExperiment,
    *,
    repository: Path,
    dolphin: Path,
    fixtures_root: Path,
    output_root: Path,
    policy: StopPolicy | None = None,
) -> dict[str, Any]:
    repository = repository.resolve()
    dolphin = dolphin.resolve()
    fixtures_root = fixtures_root.resolve()
    output_root = output_root.resolve()
    _require(dolphin.is_file(), f"Dolphin binary does not exist: {dolphin}")
    _require(not output_root.exists() or output_root.is_dir(), "output root exists and is not a directory")
    _require(not output_root.exists() or not any(output_root.iterdir()), "output root must be new or empty")
    output_root.mkdir(parents=True, exist_ok=True)
    private_root = output_root / "private"
    bounded_root = output_root / "bounded"
    private_root.mkdir()
    bounded_root.mkdir()
    policy = policy or StopPolicy(timeout_seconds=12, first_term_wait_seconds=3, second_term_wait_seconds=2)

    for fixture in frozen.fixtures.values():
        path = _fixture_path(fixtures_root, fixture)
        _require(path.is_file(), f"fixture missing: {fixture['fixture_id']}")
        _require(_sha256_file(path) == fixture["build"]["binary_sha256"], f"fixture hash mismatch: {fixture['fixture_id']}")

    ledger_path = private_root / "ledger.json"
    records: list[dict[str, Any]] = []
    environment_base = os.environ.copy()
    environment_base.pop("DOLPHIN_CI3_BLOCK_PROFILE_PATH", None)
    try:
        for expected in frozen.ordered_runs:
            fixture = frozen.fixtures[str(expected["fixture_id"])]
            fixture_path = _fixture_path(fixtures_root, fixture)
            user_directory = _safe_join(private_root, str(expected["fresh_user_directory_token"]), field="fresh_user_directory_token")
            _require(not user_directory.exists(), f"user directory already exists: {expected['run_index']}")
            user_directory.mkdir(parents=True)
            profile_token = expected.get("profile_output_token")
            profile_path: Path | None = None
            environment = environment_base.copy()
            if expected["condition"] == "treatment":
                profile_path = _safe_join(private_root, str(profile_token), field="profile_output_token")
                _require(not profile_path.exists(), f"treatment profile path is not fresh: {profile_token}")
                profile_path.parent.mkdir(parents=True, exist_ok=True)
                environment["DOLPHIN_CI3_BLOCK_PROFILE_PATH"] = str(profile_path)
            command = _build_command(dolphin, frozen.schedule, fixture=fixture_path, user_directory=user_directory)
            result = run_controlled_process(command, cwd=repository, environment=environment, policy=policy)
            collected_output = _collect_user_logs(result.output, user_directory)
            normalized = normalize_route_output(
                collected_output,
                repository=repository,
                user_directory=user_directory,
                fixture=fixture_path,
            )
            signature = route_signature(normalized)
            lower = normalized.lower()
            profile_exists = profile_path.is_file() if profile_path is not None else False
            profile_size = profile_path.stat().st_size if profile_exists and profile_path is not None else 0
            record = {
                "run_index": expected["run_index"],
                "phase": expected["phase"],
                "fixture_id": expected["fixture_id"],
                "condition": expected["condition"],
                "pair_id": expected.get("pair_id"),
                "pair_position": expected.get("pair_position"),
                "fresh_user_directory_token": expected["fresh_user_directory_token"],
                "profile_output_token": profile_token,
                "wall_ns": result.wall_ns,
                "exit_status": result.returncode,
                "timed_out": result.timed_out,
                "termination_stage": result.termination_stage,
                "normalized_sha256": _sha256_bytes(normalized.encode("utf-8")),
                "route_signature_sha256": _sha256_bytes(signature.encode("utf-8")),
                "normalized_bytes": len(normalized.encode("utf-8")),
                "normalized_lines": normalized.count("\n") + (1 if normalized else 0),
                "panic_or_crash_seen": any(term in lower for term in CRASH_TERMS),
                "cached_interpreter_text_marker_seen": "cached interpreter" in lower,
                "profile_exists": profile_exists,
                "profile_size_bytes": profile_size,
            }
            _route_record_matches(record, fixture)
            if expected["condition"] == "baseline":
                _require(not profile_exists, f"baseline created a profile at run {expected['run_index']}")
            elif expected["phase"] == "warmup":
                _require(profile_path is not None and profile_exists, f"warm-up treatment profile missing at run {expected['run_index']}")
                load_and_validate_profile(profile_path)
                profile_path.unlink()
                record["profile_exists"] = False
                record["profile_size_bytes"] = 0
                record["warmup_profile_schema_validated_and_deleted"] = True
            else:
                _require(profile_exists, f"measured treatment profile missing at run {expected['run_index']}")
            shutil.rmtree(user_directory, ignore_errors=True)
            records.append(record)
            _atomic_write(
                ledger_path,
                _json_bytes({
                    "schema_version": 1,
                    "experiment_id": EXPERIMENT_ID,
                    "freeze_merge_commit": EXPECTED_FREEZE_MERGE,
                    "schedule_sha256": EXPECTED_SCHEDULE_SHA256,
                    "runs": records,
                    "measured_profile_contents_opened": False,
                }),
            )
        return seal_collection(
            frozen,
            private_root=private_root,
            ledger_path=ledger_path,
            bounded_root=bounded_root,
            delete_private=True,
        )
    except Exception:
        _atomic_write(
            bounded_root / "collection-failure.json",
            _json_bytes({
                "schema_version": 1,
                "experiment_id": EXPERIMENT_ID,
                "stage": "collection_failure",
                "completed_run_count": len(records),
                "measured_profile_contents_opened": (
                    (bounded_root / "profile-validation-failure.json").exists()
                    or (bounded_root / "collection-verdict.json").exists()
                ),
                "decision": "FAIL_CLOSED_DO_NOT_ANALYZE",
            }),
        )
        raise


def _default_frozen_paths(repository: Path) -> tuple[Path, Path]:
    exp = repository / "docs/ci3/experiments" / EXPERIMENT_ID
    return exp / "fixture-manifest-v2.json", exp / "run-order-v2.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check-frozen", help="validate the exact merged freeze")
    check.add_argument("--repository", type=Path, default=Path.cwd())

    collect_parser = subparsers.add_parser("collect", help="execute and seal the exact frozen collection")
    collect_parser.add_argument("--repository", type=Path, required=True)
    collect_parser.add_argument("--dolphin", type=Path, required=True)
    collect_parser.add_argument("--fixtures-root", type=Path, required=True)
    collect_parser.add_argument("--output-root", type=Path, required=True)

    seal_parser = subparsers.add_parser("seal", help="seal a previously staged complete private collection")
    seal_parser.add_argument("--repository", type=Path, required=True)
    seal_parser.add_argument("--private-root", type=Path, required=True)
    seal_parser.add_argument("--ledger", type=Path, required=True)
    seal_parser.add_argument("--bounded-root", type=Path, required=True)
    seal_parser.add_argument("--keep-private", action="store_true")

    args = parser.parse_args()
    repository = args.repository.resolve()
    manifest_path, schedule_path = _default_frozen_paths(repository)
    frozen = load_frozen_experiment(manifest_path, schedule_path)
    if args.command == "check-frozen":
        print("EXP-005 fixture and run-order freeze matches merged pins")
        return 0
    if args.command == "collect":
        result = collect(
            frozen,
            repository=repository,
            dolphin=args.dolphin,
            fixtures_root=args.fixtures_root,
            output_root=args.output_root,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "seal":
        result = seal_collection(
            frozen,
            private_root=args.private_root.resolve(),
            ledger_path=args.ledger.resolve(),
            bounded_root=args.bounded_root.resolve(),
            delete_private=not args.keep_private,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
