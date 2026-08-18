# EXP-20260817-005 collection-harness v2 — verdict

Date: 2026-08-18 America/Toronto

## Decision

**PASS — the fail-closed collection harness is validated.**

The valid read-only workflow `32167670558` passed on Ubuntu 24.04 and Apple ARM64 macOS 15 at
branch head `5e02ee8a0132b4677037975b76b32a3a38c8bef6` and GitHub PR merge ref
`262870ee30fc0967b59e0408dd3ac240a8b4784e`.

This gate validates collection infrastructure only. The real 160-run EXP-005 collection was not
executed, measured profile data was not produced, and no analysis or performance decision was made.

## Prerequisites verified

- source-build qualification PR #10 merged as
  `70abc18a2fb0d56135dcc35a41d988a50b53c7bc`;
- route-reconnaissance PR #17 merged as
  `4b67e513f913c77e534aaf50d6b7ecae8780d7b2`;
- fixture-and-schedule freeze PR #18 merged as
  `278e2b4a36835fbdfbcd65ba87017f8fa0ea3f17`;
- fixture manifest Git blob `119e00ec23fdf8421caaffcead98d091a9d81314`;
- run-order Git blob `8c4290d526d69a27e4fff7256b41c6ca79bc1487`;
- frozen run-order SHA-256
  `e21f81d5f343d23a9feef0852f1dbcc8e625bec3a978a44a03e0baba2e33db85`.

## Hosted validation

| Target | Job | Result | Python | Test-log SHA-256 |
|---|---:|---|---|---|
| Ubuntu 24.04 x86-64 | `95810963686` | pass | 3.12.3 | `0295286ce2605c1707124c62a557046956010757a64971ae888a3dfb69009a8b` |
| macOS 15.7.7 arm64 | `95810963684` | pass | 3.14.6 | `cd2d0fd3b7b77355fc78122bf59456d197959f07e772f62aaec9d7de0249177d` |

Both targets independently:

- matched the exact merged freeze pins;
- compiled the harness and tests;
- passed all 12 synthetic known-answer tests;
- validated a complete stable synthetic 160-run ledger;
- rejected duplicate treatment paths;
- rejected an incomplete ledger before opening a deliberately corrupt measured profile;
- rejected route drift;
- rejected prohibited profile fields and inconsistent aggregate histograms;
- rejected per-fixture treatment-profile instability after a successful unopened-profile preflight;
- validated the two-SIGTERM stop-controller stage;
- validated cross-platform route normalization.

The Linux lane also enforced the exact four-file implementation scope before bounded evidence files
were added.

## Artifacts

- Linux artifact `9336051884`, archive digest
  `sha256:bd288c938c890b82c6fe98711f4ae6f58e88614f9a616de7ee7746c5a7d2ebc0`;
- macOS artifact `9336067048`, archive digest
  `sha256:f2a5e19a096e982fe9e9ea85db2e40126f3cf2943aeb694ddc2e6d4b3720ab8a`.

Both artifacts record `PASS_HARNESS_VALIDATION_ONLY`, `analysis_performed: false`, and
`real_collection_executed: false`.

## Invalidated first matrix

Workflow `32167048386` is methodology evidence only. Ubuntu passed, while macOS exposed a lexical
versus canonical temporary-path spelling mismatch (`/var/...` versus `/private/var/...`) in route
normalization. The correction recognizes both spellings and replaces nested fixture and user paths
before repository parents. It did not change the frozen fixture set, route contract, schedule,
thresholds, or accepted route hashes. Both platforms then passed from a clean corrected head.

## Scope and data boundary

The implementation adds only:

- the collection harness;
- its synthetic test suite;
- a read-only validation workflow;
- the preregistered plan and bounded verdict/evidence records.

It changes no production Dolphin, Cached Interpreter, JIT, MMU, timing, exception, block-cache,
code-invalidation, renderer, DSP, or iOS path.

No fixture binaries, raw logs, user directories, real profile outputs, instruction words, guest
addresses, disassembly, firmware, keys, saves, commercial content, or proprietary material are
committed.

## What is proven

`PROVEN_RUNTIME (synthetic, cross-platform, scoped)`:

- the exact frozen experiment can be recognized and rejected on drift;
- incomplete or malformed collections fail before measured profile inspection;
- measured aggregate profiles are opened only after a complete unopened-profile preflight;
- exact schema, internal count consistency, prohibited-field exclusion, and per-fixture stability are
  enforced;
- a complete stable synthetic collection produces bounded output without analysis.

## What is not proven

- the real 160-run collection can complete on the hosted runner;
- fixture-specific architectural tests pass;
- profiling overhead is acceptable;
- coverage is execution-weighted or representative of games;
- the 17-operation subset is valuable;
- Dolphin is faster;
- a GameCube title is playable;
- an iPhone result exists;
- Gate 2 is complete.

## Next decision

Proceed only to a separate real-collection PR. It must rebuild the pinned legal fixtures and current
no-GUI Dolphin, execute the merged 160-run schedule unchanged, preserve only bounded aggregate
artifacts, and stop before any coverage or overhead analysis.
