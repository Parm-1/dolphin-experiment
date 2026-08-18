# EXP-20260817-005 real collection v2

Date: 2026-08-18 America/Toronto

## Prerequisites

This work begins only after the preceding evidence chain has passed and merged:

- source-build qualification PR #10:
  `70abc18a2fb0d56135dcc35a41d988a50b53c7bc`;
- route-reconnaissance PR #17:
  `4b67e513f913c77e534aaf50d6b7ecae8780d7b2`;
- fixture-and-schedule freeze PR #18:
  `278e2b4a36835fbdfbcd65ba87017f8fa0ea3f17`;
- fail-closed collection-harness PR #19:
  `875e8be379eb58b05b851a705b43e3f3b8a9c070`.

The exact frozen run-order SHA-256 is:

`e21f81d5f343d23a9feef0852f1dbcc8e625bec3a978a44a03e0baba2e33db85`

## Question

Can the merged fail-closed harness execute and seal the exact 160-run legal-fixture schedule on
the hosted Ubuntu route without route drift, missing or reused treatment outputs, schema failure, or
per-fixture profile instability?

## Scope

This gate performs the real collection but stops before analysis.

It may:

- rebuild the eight pinned open-source `dolphin-emu/hwtests` fixtures;
- verify every fixture binary against the merged manifest;
- build current no-GUI Dolphin from the PR merge ref;
- execute the exact 32 warm-up and 128 measured runs;
- seal the complete ledger through the merged harness;
- retain bounded aggregate run metadata and one normalized profile per fixture;
- publish a bounded workflow artifact.

It must not:

- change the fixture set, order, timing, route, or stop controller;
- inspect measured treatment profiles before the 160-run preflight passes;
- invoke an overhead or coverage analyzer;
- select or expand CI3 operations;
- modify production emulator behavior;
- claim a Dolphin speedup, game result, iPhone result, or Gate 2 completion.

## Rebuild contract

The workflow must use:

- `dolphin-emu/hwtests@f28077b139eec18967f60db6ce1e15b182dfeac0`;
- toolchain
  `devkitpro/devkitppc@sha256:44cb1a920e1ec3ec7c06767493c3b85f8d643d6137cc4661f0201895ac6e4967`;
- only the eight frozen targets;
- the current PR merge ref for no-GUI Dolphin;
- the exact merged fixture manifest and run order.

Every rebuilt fixture must match its frozen SHA-256 before collection starts.

## Collection contract

The merged `collect_exp005.py` harness is authoritative.

It must:

1. validate the exact merged freeze by Git blob and SHA-256;
2. execute run indices `0..159` in order;
3. use a fresh process and user directory for every run;
4. keep baseline profiling disabled;
5. assign every treatment run its frozen unique profile token;
6. apply the frozen two-SIGTERM stop controller;
7. reject route, exit, timeout, termination-stage, crash-marker, fixture, or schema drift;
8. finish the unopened-profile preflight before opening any measured profile;
9. require eight normalized-identical measured profiles per fixture;
10. delete private collection state after a successful seal.

## Pass condition

The real-collection gate passes only when:

- the workflow builds the eight fixtures and no-GUI Dolphin;
- all fixture hashes match the merged freeze;
- the harness exits successfully;
- `collection-verdict.json` reports:
  - `gate_passed: true`;
  - `run_count: 160`;
  - `measured_pair_count: 64`;
  - `stable_fixture_profile_count: 8`;
  - `analysis_performed: false`;
  - `performance_claim_made: false`;
- `collection-aggregate.json` contains exactly 160 bounded run records and eight aggregate profiles;
- the private collection directory is deleted;
- only bounded result files are uploaded;
- a later evidence commit passes read-only Linux and macOS validation.

## Failure handling

A failure is a valid experimental result.

The workflow must preserve only bounded failure state and the hosted job log. It must not upload the
private ledger, raw treatment profiles, user directories, fixture binaries, raw emulator logs, or
absolute paths.

A failed collection blocks analysis. The project must decide whether the cause is:

- route instability;
- profile absence or schema drift;
- per-fixture profile instability;
- fixture or build drift;
- hosted-runner capacity;
- harness defect;
- another explicitly recorded condition.

## Data boundary

Durable evidence may contain only:

- source, toolchain, workflow, and commit pins;
- fixture IDs and hashes already present in the merged freeze;
- bounded run timing, termination, and normalized-route metadata;
- one normalized aggregate profile per fixture;
- profile-stability hashes;
- aggregate validation results;
- the bounded decision.

No fixture binary, raw log, user directory, raw treatment profile, guest address, instruction word,
disassembly, title identifier, save, key, firmware, commercial content, or proprietary-derived
material may be committed.

## Decision after a pass

A pass authorizes a separate analysis gate over the already sealed aggregate artifact. The analysis
method must be merged before the result is interpreted, and it must preserve the static-compilation
observation boundary: these profiles are not execution-weighted and may include duplicate
compilations.

## AI disclosure

The protocol, workflow, collection, validation, and evidence review are substantially AI-assisted
and remain confined to the user's experimental fork.
