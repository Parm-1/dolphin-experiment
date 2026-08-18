#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from analyze_exp005 import analyze  # noqa: E402

PROHIBITED_KEY_FRAGMENTS = (
    "guest_address",
    "instruction_word",
    "instruction_bytes",
    "disassembly",
    "ordered_trace",
    "title_id",
    "user_identifier",
    "absolute_path",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_output(
    text: str,
    *,
    repository: pathlib.Path,
    user_directory: pathlib.Path,
    fixture: pathlib.Path,
) -> str:
    for old, new in (
        (str(repository.resolve()), "<REPO>"),
        (str(user_directory.resolve()), "<USERDIR>"),
        (str(fixture.resolve()), "<FIXTURE>"),
    ):
        text = text.replace(old, new)
    text = re.sub(
        r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\b",
        "<TIME>",
        text,
    )
    text = re.sub(r"\[[ ]*\d+(?:\.\d+)?s\]", "[<ELAPSED>]", text)
    text = re.sub(r"\b(?:pid|PID)[=: ]+\d+\b", "PID=<PID>", text)
    return text.replace("\r\n", "\n")


def _find_key(root: Any, names: tuple[str, ...]) -> Any:
    matches: list[Any] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in names:
                    matches.append(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(root)
    if not matches:
        raise KeyError(f"missing profile key aliases: {names}")
    serialized = {json.dumps(match, sort_keys=True) for match in matches}
    if len(serialized) != 1:
        raise ValueError(f"ambiguous profile key aliases: {names}")
    return matches[0]


def _integer(value: Any) -> int:
    if isinstance(value, bool):
        raise TypeError("boolean is not an aggregate integer")
    if isinstance(value, (int, str)):
        return int(value)
    raise TypeError(f"unsupported aggregate integer: {type(value).__name__}")


def _numeric_map(value: Any) -> dict[str, int]:
    if isinstance(value, list):
        return {str(index): _integer(item) for index, item in enumerate(value)}
    if isinstance(value, dict):
        return {str(key): _integer(item) for key, item in value.items()}
    raise TypeError(f"unsupported aggregate map: {type(value).__name__}")


def _validate_profile_schema(root: Any) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                lowered = str(key).lower()
                for fragment in PROHIBITED_KEY_FRAGMENTS:
                    if fragment in lowered:
                        raise ValueError(f"prohibited profile field: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(root)


def normalize_profile(root: dict[str, Any]) -> dict[str, Any]:
    _validate_profile_schema(root)
    counter_names = (
        "observed_blocks",
        "broken_blocks",
        "analyzed_operations",
        "eligible_operations",
        "skipped_operations",
        "supported_operations",
        "blocks_with_supported_operations",
        "fully_supported_eligible_blocks",
        "maximum_live_future_gprs",
    )
    counters = {name: _integer(_find_key(root, (name,))) for name in counter_names}
    return {
        "counters": counters,
        "eligible_block_lengths": _numeric_map(
            _find_key(root, ("eligible_block_lengths",))
        ),
        "supported_run_lengths": _numeric_map(
            _find_key(root, ("supported_run_lengths",))
        ),
        "semantic_feature_counts": _numeric_map(
            _find_key(root, ("semantic_feature_counts", "semantic_features"))
        ),
        "gpr_reuse_distance_counts": _numeric_map(
            _find_key(root, ("gpr_reuse_distance_counts", "gpr_reuse_distances"))
        ),
        "maximum_live_future_gprs_per_block": _numeric_map(
            _find_key(root, ("maximum_live_future_gprs_per_block",))
        ),
    }


def _collect_output(stdout: str, user_directory: pathlib.Path) -> str:
    text = stdout
    for log in sorted(user_directory.rglob("*.log")):
        try:
            text += "\n<LOGFILE>\n" + log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return text


def _run_one(
    *,
    phase: str,
    run_spec: dict[str, Any],
    fixture: dict[str, Any],
    dolphin: pathlib.Path,
    fixtures_root: pathlib.Path,
    repository: pathlib.Path,
    work_root: pathlib.Path,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    fixture_path = fixtures_root / fixture["source_relative_output"]
    if not fixture_path.is_file():
        raise FileNotFoundError(f"fixture missing: {fixture_path}")
    expected_binary_hash = fixture["produced_binary"]["sha256"]
    if _sha256_file(fixture_path) != expected_binary_hash:
        raise ValueError(f"fixture hash mismatch: {fixture['fixture_id']}")

    run_index = int(run_spec["run_index"])
    fixture_id = str(fixture["fixture_id"])
    condition = str(run_spec["condition"])
    run_root = work_root / f"{phase}-{run_index:04d}-{fixture_id}-{condition}"
    user_directory = run_root / "user"
    user_directory.mkdir(parents=True)
    profile_path = run_root / "profile.json"

    command = [
        "timeout",
        "--signal=TERM",
        "--kill-after=5s",
        "10s",
        str(dolphin),
        "-b",
        "-e",
        str(fixture_path),
        "-u",
        str(user_directory),
        "-v",
        "Null",
        "-C",
        "Dolphin.Core.CPUCore=2",
        "-C",
        "Dolphin.Core.DSPHLE=True",
    ]
    environment = os.environ.copy()
    if condition == "treatment":
        environment["DOLPHIN_CI3_BLOCK_PROFILE_PATH"] = str(profile_path)
    else:
        environment.pop("DOLPHIN_CI3_BLOCK_PROFILE_PATH", None)

    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter_ns()
    completed = subprocess.run(
        command,
        cwd=repository,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    wall_ns = time.perf_counter_ns() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)

    collected = _collect_output(completed.stdout, user_directory)
    normalized = normalize_output(
        collected,
        repository=repository,
        user_directory=user_directory,
        fixture=fixture_path,
    )
    normalized_bytes = normalized.encode()
    lower = normalized.lower()

    qualification = fixture["qualification"]
    expected_exit = int(qualification["expected_exit_status"])
    expected_timeout = bool(qualification["expected_timed_out"])
    expected_hash = str(qualification["expected_normalized_output_sha256"])
    matches_frozen = (
        completed.returncode == expected_exit
        and (completed.returncode == 124) == expected_timeout
        and _sha256_bytes(normalized_bytes) == expected_hash
        and "cached interpreter" in lower
        and not any(
            term in lower
            for term in ("panic alert", "segmentation fault", "assertion failed", "fatal error")
        )
    )

    profile_root: dict[str, Any] | None = None
    normalized_profile: dict[str, Any] | None = None
    profile_valid = False
    profile_sha256 = None
    if condition == "treatment":
        if profile_path.is_file():
            profile_bytes = profile_path.read_bytes()
            profile_sha256 = _sha256_bytes(profile_bytes)
            profile_root = json.loads(profile_bytes)
            normalized_profile = normalize_profile(profile_root)
            profile_valid = True
    elif profile_path.exists():
        raise ValueError("baseline unexpectedly created a profile")

    record = {
        "phase": phase,
        **run_spec,
        "fixture_id": fixture_id,
        "condition": condition,
        "wall_ns": wall_ns,
        "cpu_user_ns": round((after.ru_utime - before.ru_utime) * 1_000_000_000),
        "cpu_system_ns": round((after.ru_stime - before.ru_stime) * 1_000_000_000),
        "exit_status": completed.returncode,
        "timed_out": completed.returncode == 124,
        "normalized_sha256": _sha256_bytes(normalized_bytes),
        "normalized_bytes": len(normalized_bytes),
        "normalized_lines": normalized.count("\n") + (1 if normalized else 0),
        "cached_interpreter_seen": "cached interpreter" in lower,
        "panic_or_crash_seen": any(
            term in lower
            for term in ("panic alert", "segmentation fault", "assertion failed", "fatal error")
        ),
        "matches_frozen_route_invariant": matches_frozen,
        "profile_valid": profile_valid,
        "profile_sha256": profile_sha256,
    }

    shutil.rmtree(run_root, ignore_errors=True)
    return record, profile_root, normalized_profile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=pathlib.Path)
    parser.add_argument("--dolphin", required=True, type=pathlib.Path)
    parser.add_argument("--fixtures-root", required=True, type=pathlib.Path)
    parser.add_argument("--manifest", required=True, type=pathlib.Path)
    parser.add_argument("--schedule", required=True, type=pathlib.Path)
    parser.add_argument("--output-directory", required=True, type=pathlib.Path)
    parser.add_argument("--bootstrap-resamples", type=int, default=50_000)
    args = parser.parse_args()

    repository = args.repository.resolve()
    dolphin = args.dolphin.resolve()
    fixtures_root = args.fixtures_root.resolve()
    manifest = json.loads(args.manifest.read_text())
    schedule = json.loads(args.schedule.read_text())
    if manifest["manifest_state"] != "FROZEN_BEFORE_PROFILE_ACCESS":
        raise ValueError("fixture manifest is not frozen")

    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    profiles_directory = output / "profiles"
    profiles_directory.mkdir()

    fixtures = {item["fixture_id"]: item for item in manifest["fixtures"]}
    work_root = pathlib.Path(tempfile.mkdtemp(prefix="ci3-exp005-runs-"))
    warmup_records = []
    measured_records = []
    normalized_profiles: dict[str, dict[str, Any]] = {}
    representative_profile_hashes: dict[str, str] = {}
    profile_hash_sets: dict[str, set[str]] = {fixture_id: set() for fixture_id in fixtures}

    try:
        for run_spec in schedule["warmups"]:
            fixture = fixtures[str(run_spec["fixture_id"])]
            record, _, _ = _run_one(
                phase="warmup",
                run_spec=run_spec,
                fixture=fixture,
                dolphin=dolphin,
                fixtures_root=fixtures_root,
                repository=repository,
                work_root=work_root,
            )
            warmup_records.append(record)
            if not record["matches_frozen_route_invariant"] or (
                record["condition"] == "treatment" and not record["profile_valid"]
            ):
                raise RuntimeError(f"warmup invariant failed: {record}")

        for run_spec in schedule["measured"]:
            fixture_id = str(run_spec["fixture_id"])
            fixture = fixtures[fixture_id]
            record, profile_root, normalized_profile = _run_one(
                phase="measured",
                run_spec=run_spec,
                fixture=fixture,
                dolphin=dolphin,
                fixtures_root=fixtures_root,
                repository=repository,
                work_root=work_root,
            )
            measured_records.append(record)
            if record["condition"] == "treatment":
                if not record["profile_valid"] or profile_root is None or normalized_profile is None:
                    raise RuntimeError(f"missing treatment profile: {record}")
                profile_hash_sets[fixture_id].add(str(record["profile_sha256"]))
                if fixture_id not in normalized_profiles:
                    normalized_profiles[fixture_id] = normalized_profile
                    representative = profiles_directory / f"{fixture_id}.json"
                    representative.write_text(
                        json.dumps(profile_root, indent=2, sort_keys=True) + "\n"
                    )
                    representative_profile_hashes[fixture_id] = _sha256_file(representative)

        if set(normalized_profiles) != set(fixtures):
            raise RuntimeError("not every fixture produced a representative profile")

        aggregate_input = {
            "schema_version": 1,
            "experiment_id": "EXP-20260817-005",
            "fixtures": [
                {
                    "fixture_id": fixture["fixture_id"],
                    "workload_class": fixture["workload_class"],
                    "binary_sha256": fixture["produced_binary"]["sha256"],
                }
                for fixture in manifest["fixtures"]
            ],
            "runs": measured_records,
            "profiles": normalized_profiles,
            "profile_stability": {
                fixture_id: {
                    "unique_profile_hash_count": len(hashes),
                    "profile_hashes": sorted(hashes),
                    "byte_stable": len(hashes) == 1,
                    "representative_committed_sha256": representative_profile_hashes[fixture_id],
                }
                for fixture_id, hashes in sorted(profile_hash_sets.items())
            },
            "warmup_validation": {
                "run_count": len(warmup_records),
                "all_routes_match_frozen_invariant": all(
                    record["matches_frozen_route_invariant"] for record in warmup_records
                ),
                "all_treatment_profiles_valid": all(
                    record["condition"] != "treatment" or record["profile_valid"]
                    for record in warmup_records
                ),
            },
            "data_boundary": (
                "Only aggregate timings, normalized route hashes, and aggregate schema-v1 profiles are retained. "
                "Raw logs, user directories, built binaries, and absolute paths were deleted."
            ),
        }
        aggregate_path = output / "measurement-aggregate.json"
        aggregate_path.write_text(json.dumps(aggregate_input, indent=2, sort_keys=True) + "\n")

        analysis_result = analyze(
            aggregate_input, bootstrap_resamples=args.bootstrap_resamples
        )
        (output / "analysis.json").write_text(
            json.dumps(analysis_result, indent=2, sort_keys=True) + "\n"
        )
    finally:
        shutil.rmtree(work_root, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
