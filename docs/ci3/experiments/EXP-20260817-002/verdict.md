# EXP-20260817-002 verdict

## Verdict

**GATE 1 PASS — PROCEED TO MINIMUM POWERPC-FACING VALIDATION**

The hardened matrix passed its pre-registered synthetic criteria:

- A compact or tail-threaded executor exceeded the callback baseline by at least 20% in every
  ARM64 case.
- Dispatch ordering differed materially by compiler and architecture.
- Forced state visibility had a clear frequency-dependent cost.
- Explicit local state produced repeatable ARM64 gains at block-like boundary intervals.
- Assembly confirmed that the musttail chain and state-materialization boundary were emitted as
  intended.
- All engines remained deterministically equivalent.

## Claims promoted

- Compact direct dispatch has material synthetic ARM64 headroom:
  `PROVEN_RUNTIME (synthetic)`.
- AppleClang `preserve_none`/`musttail` has material synthetic ARM64 headroom:
  `PROVEN_RUNTIME (synthetic)`.
- Dispatch strategy is compiler- and architecture-sensitive:
  `PROVEN_RUNTIME (synthetic)`.
- Explicit local state can improve ARM64 execution when flush boundaries are sufficiently coarse:
  `PROVEN_RUNTIME (synthetic, conditional)`.
- Per-instruction state materialization can erase or reverse that advantage:
  `PROVEN_RUNTIME (synthetic)`.

## Claims not promoted

- No claim about Dolphin's current Cached Interpreter throughput.
- No claim about PowerPC semantics or correctness.
- No claim about a game, iPhone, thermals, or strict no-codegen product viability.
- No claim that one dispatch executor should be used universally.
- No claim that persistence improves steady-state performance.

## Architectural consequence

Use one compact portable IR with multiple executors:

- a dense switch as the portable baseline;
- an AppleClang musttail executor as a measured target-specific candidate;
- a computed-goto executor only where target/compiler evidence supports it.

State should be carried across blocks or superblocks and materialized only at explicit semantic
boundaries. A design that flushes all guest state after every operation is rejected.

## Next experiment

The next work must be the smallest PowerPC-facing validation, not a complete backend.

It should determine:

1. the dynamic block/opcode/register-use distribution available from legal test workloads;
2. the fraction of operations that a 15–25-op compact IR subset could lower without changing
   semantics;
3. the real frequency of boundaries that force state materialization;
4. whether a minimal executor can preserve reference-interpreter results on generated or legal
   homebrew blocks.

Persistence remains deferred until Gate 2.
