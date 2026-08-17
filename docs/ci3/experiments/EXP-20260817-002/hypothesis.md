# EXP-20260817-002 hypothesis

## Question

Do the synthetic ARM64 dispatch gains from EXP-20260817-001 survive multiple trace lengths and
seeds, and how does forced architectural-state materialization change the relative value of direct
state access versus explicit local state?

## Motivation

EXP-20260817-001 found large compact-dispatch and AppleClang musttail gains, but it used one seed,
one trace length, fixed engine order, and a state model that the compiler could scalar-promote. It
did not independently test state pinning.

## Pre-registered comparisons

### Dispatch matrix

- trace lengths: 64, 256, and 1024 operations
- three fixed seeds
- deterministic randomized case order
- seven measured repetitions per engine and case
- callback-two-level baseline
- Linux x64 GCC and Clang
- Linux ARM64 GCC and Clang
- macOS ARM64 AppleClang

### State-materialization matrix

The same trace matrix compares direct-state and explicit-local execution with:

- no semantic boundary
- boundary after every operation
- boundary after every four operations
- boundary after every sixteen operations
- boundary once per trace

The semantic boundary is a no-inline function in a separate translation unit. It forces escaped
state to be materialized and treated as possibly changed without performing guest work.

## Hypotheses

H2a: A compact switch or musttail engine remains at least 20% faster than the callback baseline on
all ARM64 cases.

H2b: No single dispatch topology wins across every compiler and architecture.

H3a: Boundary frequency is a first-order cost; every-operation materialization is substantially
slower than per-trace materialization.

H3b: Explicit local state provides a repeatable advantage over direct-state access at at least one
non-trivial boundary interval on ARM64.

## Falsifiers

- Compact dispatch falls below 1.2x the callback baseline on a substantial fraction of ARM64 cases.
- The v1 ordering reverses across seeds or trace lengths without an explainable predictor or
  footprint effect.
- State-boundary variants do not show a stable frequency-dependent cost.
- Explicit local state has no repeatable ARM64 advantage once materialization is controlled.
- Generated assembly shows that the intended boundary or local-state model was optimized away.

## Required artifacts

- raw JSONL for every case
- machine-readable and Markdown summaries
- compiler and runner environment
- deterministic checksums
- executable section sizes
- symbol-size listings
- disassembly for both executables

## Interpretation boundary

This remains a synthetic register-machine experiment. Passing it allows a minimum PowerPC-facing
prototype or a captured aggregate-trace experiment. It does not pass the Dolphin integration or
real-game performance gates by itself.
