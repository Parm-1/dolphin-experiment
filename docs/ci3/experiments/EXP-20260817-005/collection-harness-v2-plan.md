# EXP-20260817-005 fail-closed collection harness v2

Date: 2026-08-18 America/Toronto

## Prerequisites

This work begins only after both prior gates are merged:

- source-build qualification PR #10, merge `70abc18a2fb0d56135dcc35a41d988a50b53c7bc`;
- route-reconnaissance PR #17, merge `4b67e513f913c77e534aaf50d6b7ecae8780d7b2`;
- fixture-and-schedule freeze PR #18, merge `278e2b4a36835fbdfbcd65ba87017f8fa0ea3f17`.

The harness pins the exact merged fixture manifest by Git blob
`119e00ec23fdf8421caaffcead98d091a9d81314`, the exact run order by Git blob
`8c4290d526d69a27e4fff7256b41c6ca79bc1487`, and the run-order SHA-256
`e21f81d5f343d23a9feef0852f1dbcc8e625bec3a978a44a03e0baba2e33db85`.

## Question

Can the frozen 160-run baseline/treatment schedule be executed and sealed through a collection
harness that fails closed on incomplete pairs, route drift, fixture drift, schema drift, missing or
reused profile outputs, and unstable treatment profiles, while preventing measured profile contents
from being inspected before collection completeness passes?

## Scope

This gate implements and validates collection infrastructure only.

It does not:

- run the real 160-run workload;
- analyze profiler overhead or coverage;
- choose or expand the CI3 operation subset;
- modify Dolphin's CPU execution path;
- claim a speedup, game result, iPhone result, or Gate 2 completion.

## Required phases

### Phase A — exact freeze validation

Before any execution, the harness must verify:

- the exact merged fixture and schedule Git objects;
- the schedule SHA-256 recorded by the manifest;
- eight fixtures in the frozen order and two fixtures per workload class;
- 32 warm-ups and 128 measured runs with contiguous indices `0..159`;
- all 64 adjacent measured pairs;
- four baseline-first and four treatment-first pairs per fixture;
- complete fixture-position rotation;
- unique fresh-user-directory and treatment-profile tokens;
- the exact no-GUI route arguments and stop-controller contract.

### Phase B — private collection

Every scheduled run must use:

- the frozen fixture binary and verified SHA-256;
- a fresh process and user directory;
- the frozen route arguments;
- the profiler environment variable unset for baseline and set to a unique path for treatment;
- the frozen timeout and two-SIGTERM stop controller;
- no raw-log retention after normalization.

Warm-up treatment profiles may be opened only for schema validation, then must be deleted. Measured
profiles must remain unopened during collection.

### Phase C — unopened-profile preflight

After all 160 runs, and before parsing any measured profile, the harness must reject:

- a missing, duplicate, reordered, or modified ledger entry;
- a missing baseline/treatment pair;
- route-signature, normalized-output, exit-status, timeout, termination-stage, or crash-marker drift;
- a baseline profile output;
- a missing, empty, reused, or stale measured treatment profile;
- any path token that escapes the private collection root.

Only a passing preflight may authorize measured-profile inspection.

### Phase D — profile schema and stability

After preflight, the harness must validate the exact schema-v1 aggregate profile contract, including:

- duplicate-key rejection;
- no prohibited raw-guest or identifying fields;
- non-negative full-`u64` counts;
- exact aggregate, semantic-feature, and GPR-reuse keys;
- histogram/count consistency;
- exactly eight measured treatment profiles per fixture;
- one normalized profile value per fixture across those eight runs.

Any schema or stability failure must produce a bounded fail-closed record and no analysis result.

### Phase E — bounded output

A passing seal may retain only:

- aggregate run timing and normalized route metadata;
- one normalized aggregate profile per fixture;
- per-fixture profile-stability hashes;
- preflight and collection verdicts.

It must delete the private ledger, raw treatment profiles, user directories, and other run-private
state after a successful seal. Failure diagnostics remain private and must not be committed.

## Validation matrix

The gate requires read-only validation on Ubuntu 24.04 and macOS 15.

Synthetic known-answer tests must cover:

- exact current freeze validation;
- a complete stable 160-run ledger;
- schedule token reuse rejection;
- missing-run rejection before a deliberately corrupt measured profile is opened;
- route-drift rejection;
- prohibited profile-field rejection;
- histogram inconsistency rejection;
- treatment-profile instability after a successful unopened-profile preflight;
- the two-SIGTERM process-controller stage;
- route normalization of paths, time, IDs, and pointer-like values.

## Pass condition

The harness gate passes only if:

- both hosted operating systems pass all tests;
- the exact merged freeze validates on both systems;
- the positive complete/stable collection fixture seals successfully;
- every negative control fails for the preregistered reason;
- the PR contains no production emulator changes;
- the final diff is limited to the harness, tests, workflow, and bounded experiment records.

## Decision after a pass

Proceed to a separate real collection PR that rebuilds the pinned legal fixtures and current no-GUI
Dolphin, executes the frozen 160-run schedule exactly, preserves only bounded aggregate artifacts,
and stops before analysis.

## AI disclosure

The design and implementation are substantially AI-assisted and remain confined to the user's
experimental fork. They are not intended as an upstream Dolphin console-behavior contribution.
