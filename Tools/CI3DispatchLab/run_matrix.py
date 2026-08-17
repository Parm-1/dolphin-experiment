#!/usr/bin/env python3
"""Run a deterministic multi-trace CI3 benchmark matrix and summarize speedups."""

from __future__ import annotations

import argparse
import json
import random
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_SEEDS = (
    0xC13C0FFEE1234567,
    0x9E3779B97F4A7C15,
    0xD1B54A32D192ED03,
)
DEFAULT_TRACE_LENGTHS = (64, 256, 1024)


@dataclass(frozen=True)
class Case:
    seed: int
    trace_length: int
    iterations: int

    @property
    def case_id(self) -> str:
        return f"trace-{self.trace_length}-seed-{self.seed:016x}"


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--baseline-engine", required=True)
    parser.add_argument("--target-ops", type=parse_int, default=2_000_000)
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument(
        "--seed",
        dest="seeds",
        action="append",
        type=parse_int,
        help="Repeatable seed; may be supplied more than once.",
    )
    parser.add_argument(
        "--trace-length",
        dest="trace_lengths",
        action="append",
        type=parse_int,
        help="Trace length; may be supplied more than once.",
    )
    parser.add_argument(
        "--shuffle-seed",
        type=parse_int,
        default=0xC13D15A7C4,
        help="Deterministic case-order shuffle seed.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.binary.is_file():
        raise ValueError(f"benchmark binary does not exist: {args.binary}")
    if args.target_ops <= 0:
        raise ValueError,"--target-ops must be positive")
    if args.repetitions <= 0:
        raise ValueError("--repetitions must be positive")
    for trace_length in args.trace_lengths or DEFAULT_TRACE_LENGTHS:
        if trace_length <= 0:
            raise ValueError("trace lengths must be positive")


def make_cases(args: argparse.Namespace) -> list[Case]:
    seeds = tuple(args.seeds or DEFAULT_SEEDS)
    trace_lengths = tuple(args.trace_lengths or DEFAULT_TRACE_LENGTHS)
    cases = [
        Case(
            seed=seed,
            trace_length=trace_length,
            iterations=max(1, args.target_ops // trace_length),
        )
        for seed in seeds
        for trace_length in trace_lengths
    ]
    random.Random(args.shuffle_seed).shuffle(cases)
    return cases


def run_case(args: argparse.Namespace, case: Case) -> list[dict[str, Any]]:
    command = [
        str(args.binary),
        "--iterations",
        str(case.iterations),
        "--repetitions",
        str(args.repetitions),
        "--trace-length",
        str(case.trace_length),
        "--seed",
        hex(case.seed),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"case {case.case_id} failed with exit code {completed.returncode}\n"
            f"command: {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    records: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(completed.stdout.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"case {case.case_id} emitted invalid JSON on line {line_number}: {line}"
            ) from error
        record["case_id"] = case.case_id
        record["case_index"] = -1
        record["target_ops"] = args.target_ops
        records.append(record)

    benchmark_records = [record for record in records if record.get("kind") == "benchmark"]
    if not benchmark_records:
        raise RuntimeError(f"case {case.case_id} produced no benchmark records")
    if not any(record.get("engine") == args.baseline_engine for record in benchmark_records):
        raise RuntimeError(
            f"case {case.case_id} did not emit baseline engine {args.baseline_engine!r}"
        )
    return records


def add_speedups(records: list[dict[str, Any]], baseline_engine: str) -> None:
    by_case: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if record.get("kind") == "benchmark":
            by_case.setdefault(str(record["case_id"]), []).append(record)

    for case_id, case_records in by_case.items():
        baseline = next(
            (record for record in case_records if record.get("engine") == baseline_engine), None
        )
        if baseline is None:
            raise RuntimeError(f"missing baseline {baseline_engine!r} for case {case_id}")
        baseline_ns = float(baseline["median_ns_per_op"])
        if baseline_ns <= 0:
            raise RuntimeError(f"non-positive baseline time for case {case_id}")
        for record in case_records:
            engine_ns = float(record["median_ns_per_op"])
            if engine_ns <= 0:
                raise RuntimeError(
                    f"non-positive engine time for {record.get('engine')} in case {case_id}"
                )
            record["speedup_vs_baseline"] = baseline_ns / engine_ns


def make_summary(
    records: list[dict[str, Any]], baseline_engine: str, args: argparse.Namespace
) -> dict[str, Any]:
    speedups: dict[str, list[float]] = {}
    timings: dict[str, list[float]] = {}
    for record in records:
        if record.get("kind") != "benchmark":
            continue
        engine = str(record["engine"])
        speedups.setdefault(engine, []).append(float(record["speedup_vs_baseline"]))
        timings.setdefault(engine, []).append(float(record["median_ns_per_op"]))

    engines: list[dict[str, Any]] = []
    for engine in sorted(speedups):
        engine_speedups = speedups[engine]
        engine_timings = timings[engine]
        engines.append(
            {
                "engine": engine,
                "cases": len(engine_speedups),
                "median_speedup_vs_baseline": statistics.median(engine_speedups),
                "min_speedup_vs_baseline": min(engine_speedups),
                "max_speedup_vs_baseline": max(engine_speedups),
                "median_ns_per_op": statistics.median(engine_timings),
            }
        )

    engines.sort(key=lambda item: item["median_speedup_vs_baseline"], reverse=True)
    return {
        "schema_version": 1,
        "binary": str(args.binary),
        "baseline_engine": baseline_engine,
        "target_ops": args.target_ops,
        "repetitions": args.repetitions,
        "case_count": len({record["case_id"] for record in records}),
        "engines": engines,
    }


def write_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# CI3 benchmark matrix summary",
        "",
        f"Baseline: `{summary['baseline_engine']}`",
        "",
        "| Engine | Cases | Median speedup | Min–max speedup | Median ns/op |",
        "|---|---:|---:|---:|---:|",
    ]
    for engine in summary["engines"]:
        lines.append(
            f"| `{engine['engine']}` | {engine['cases']} | "
            f"{engine['median_speedup_vs_baseline']:.3f}x | "
            f"{engine['min_speedup_vs_baseline']:.3f}–"
            f"{engine['max_speedup_vs_baseline']:.3f}x | "
            f"{engine['median_ns_per_op']:.4f} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    try:
        validate_args(args)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        cases = make_cases(args)
        all_records: list[dict[str, Any]] = []

        for case_index, case in enumerate(cases):
            case_records = run_case(args, case)
            for record in case_records:
                record["case_index"] = case_index
            case_path = args.output_dir / f"{case.case_id}.jsonl"
            case_path.write_text(
                "".join(json.dumps(record, sort_keys=True) + "\n" for record in case_records),
                encoding="utf-8",
            )
            all_records.extend(case_records)

        add_speedups(all_records, args.baseline_engine)
        combined_path = args.output_dir / "combined.jsonl"
        combined_path.write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in all_records),
            encoding="utf-8",
        )

        summary = make_summary(all_records, args.baseline_engine, args)
        (args.output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_markdown(summary, args.output_dir / "summary.md")
        print(json.dumps(summary, sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
