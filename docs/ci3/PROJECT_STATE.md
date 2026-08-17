# CI3-PIR project state

Last updated: 2026-08-17 America/Toronto

## Current gate

**Gate 2 — minimum Dolphin integration**

Gate 0 is complete.

Gate 1 passed through `EXP-20260817-002`: compact ARM64 dispatch and coarse-boundary local state
survived a multi-seed, multi-trace matrix with assembly verification.

`EXP-20260817-003` completes a scoped semantic-feasibility subtask inside Gate 2. A test-local
eight-byte representation for 17 selected register-only PowerPC integer forms agreed with Dolphin's
reference Interpreter across three hosted targets.

Gate 2 is **not** passed. No CI3 runtime backend or Dolphin performance improvement has been
established, and the charter's microbenchmark and real-workload thresholds remain unmet.

## Repository state

- Implementation repository: `Parm-1/dolphin-experiment`
- Default branch: `master`
- Fork base at bootstrap: `fa61f77fedb1f804851414a231509c55b8d8ed6c`
- Control-plane merge: `ea396c4e08257b2ad9aa699c68a56e3f9fcb8380`
- Dispatch Lab v1 merge: `fa0c7391ba9770468567adf8c51371d61922a841`
- EXP-001 evidence merge: `21d7c0360e3c44d3ad6187af8ad913f661dc5fbf`
- Gate 1 implementation merge: `e3ee0bb1b20305c43cde6f1a357935fd915e90c9`
- Active implementation PR: #5, `ci3/powerpc-integer-differential`
- Tested PR head: `24d3b521e6139e02b536cd415b4afd9a16044cf9`

## Current capability

- Connected GitHub application: available with repository write/admin access.
- GitHub Actions: full Dolphin unit-test builds and the CI3 differential suite pass on Linux
  x86-64, Linux ARM64, and virtual Apple-M1 macOS ARM64 runners.
- PowerPC semantics: 17 selected register-only integer forms have scoped differential evidence.
- Runtime integration: no selectable CI3 CPU backend exists.
- Local commercial-game testing: unavailable in GitHub CI and must remain local/uncommitted.
- iPhone device testing: `BLOCKED_ENVIRONMENT` until a reproducible signing/device route exists.

## Latest evidence

Experiment `EXP-20260817-003`, successful workflow run `32070900486`, tested head
`24d3b521e6139e02b536cd415b4afd9a16044cf9`:

- all three hosted jobs built Dolphin's full unit-test executable;
- all three `CI3PowerPCIntegerDifferential` tests passed on every target;
- the compact operation record is eight bytes and covers 17 selected operation forms;
- one 18-operation fixed edge-case trace passed;
- 12 deterministic seeds × 512 operations produced 6,144 randomized differential operations;
- selected encodings and pre-registered metadata exclusions passed;
- no ROM, game executable, firmware, key, save, or proprietary-derived instruction trace was used.

Evidence state: `PROVEN_RUNTIME (differential, scoped)`.

## Active hypothesis

Real analyzed PowerPC blocks contain enough operations, local register reuse, and sufficiently
coarse semantic boundaries for the measured Dispatch Lab advantage to survive a minimal Dolphin
integration.

This is not yet established.

## Next workstream

Pre-register and implement aggregate-only block characterization before broad backend work.

Use Dolphin's existing analyzed `CodeBlock`/`CodeOp` data to record:

- block-length histograms;
- opcode frequencies;
- current-subset coverage and contiguous supported-run lengths;
- GPR read/write and short-range reuse distributions;
- boundary categories that require state materialization;
- generic fallback rates.

The output must be deterministic and machine-readable, and must not persist instruction words,
guest addresses, disassembly, or proprietary-derived traces.

After that characterization selects a defensible first lowering subset, build the smallest runtime
integration and compare it against mainline Cached Interpreter under the versioned benchmark
protocol.

Persistence, iOS UI work, large semantic fast paths, public performance claims, and broad game
testing remain deferred.

## Explicit blockers

- Gate 2 performance evidence does not exist.
- Device verification requires an external Apple build/signing/device path.
- No legal commercial-game fixture is available in GitHub CI.
- A stable legal workload route for aggregate block characterization still must be selected.
- Dolphin's AI contribution policy prevents presenting AI-authored console-behavior changes as
  ordinary upstream contributions; CI3 remains experimental in this fork.
