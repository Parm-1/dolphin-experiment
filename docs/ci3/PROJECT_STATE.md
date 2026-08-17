# CI3-PIR project state

Last updated: 2026-08-17 America/Toronto

## Current gate

**Gate 2 — minimum PowerPC-facing validation**

Gate 0 is complete.

Gate 1 passed through `EXP-20260817-002`: compact ARM64 dispatch and coarse-boundary local state
survived a multi-seed, multi-trace matrix with assembly verification.

Gate 2 is not yet passed. No Dolphin, PowerPC, game, or device speedup has been established.

## Repository state

- Implementation repository: `Parm-1/dolphin-experiment`
- Default branch: `master`
- Fork base at bootstrap: `fa61f77fedb1f804851414a231509c55b8d8ed6c`
- Control-plane merge: `ea396c4e08257b2ad9aa699c68a56e3f9fcb8380`
- Dispatch Lab v1 merge: `fa0c7391ba9770468567adf8c51371d61922a841`
- EXP-001 evidence merge: `21d7c0360e3c44d3ad6187af8ad913f661dc5fbf`
- Active implementation PR: #4, `ci3/dispatch-lab-v2`

## Current capability

- Connected GitHub application: available with repository write/admin access.
- Local execution: standalone lab builds with GCC and Clang; full repository cloning is blocked by
  outbound DNS in the current runtime.
- GitHub Actions: Linux x64, Linux ARM64, and virtual-M1 macOS ARM64 execution verified.
- iPhone device testing: `BLOCKED_ENVIRONMENT` until a reproducible signing/device route exists.
- Commercial game fixtures: unknown and must remain local/uncommitted.

## Latest evidence

Experiment `EXP-20260817-002`, successful workflow run `32022583823`:

- five hosted jobs built, tested, and uploaded diagnostics;
- three seeds × three trace lengths per target;
- Linux ARM64 GCC compact switch: 2.241x median, 2.196x minimum case;
- Linux ARM64 Clang compact switch: 1.412x median, 1.349x minimum case;
- virtual-M1 musttail: 2.159x median, 1.670x minimum case;
- explicit locals improved moderate-boundary ARM64 cases, but could regress with every-operation
  materialization;
- assembly confirmed both the musttail chain and forced state spill/reload boundary.

Evidence state: `PROVEN_RUNTIME (synthetic)`.

## Active hypothesis

A small compact PowerPC-facing representation can preserve reference semantics while covering enough
hot, low-boundary operations to retain part of the Dispatch Lab advantage.

## Next workstream

Pre-register and build the minimum PowerPC-facing experiment.

It should begin with source and workload characterization rather than a full backend:

- inspect existing Dolphin PowerPC test infrastructure and legal homebrew fixtures;
- define an instrumentation-only block/opcode/register/boundary profile format;
- establish a CI-buildable route that changes no guest semantics;
- select the first 15–25 operations from evidence;
- build differential tests against the reference Interpreter;
- measure only after coverage and correctness are established.

Persistence, iOS UI work, large semantic fast paths, and public performance claims remain deferred.

## Explicit blockers

- Device verification requires an external Apple build/signing/device path.
- No legal commercial-game fixture is available in GitHub CI.
- No Dolphin or PowerPC runtime result exists yet.
- Dolphin's AI contribution policy prevents presenting AI-authored console-behavior changes as
  ordinary upstream contributions; CI3 remains experimental in this fork.
