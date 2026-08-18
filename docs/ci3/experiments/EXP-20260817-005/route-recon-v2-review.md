# EXP-20260817-005 route reconnaissance v2 — review and decision

Date: 2026-08-18 America/Toronto

## Decision

**PASS — proceed only to deterministic fixture freeze.**

The preregistered route gate required at least four qualifying candidates across at least three
workload classes. Valid workflow run `32124068535` qualified all eight candidates across all four
preselected classes.

This is the stopping decision for the current work cycle. It authorizes a separate fixture-manifest
and paired-run-order freeze. It does not authorize interpreting profiling coverage, adding a CI3
execution backend, changing the opcode subset, claiming performance, or beginning iPhone work.

## Tested state

- Repository: `Parm-1/dolphin-experiment`
- Pull request: `#17`
- PR head: `ab4251f14c5cfeb25d78a7a1609c79bc8ed9b2ad`
- GitHub pull-request merge ref checked out by Actions: `01faa904e1caff3195b2d8185416c9d8f43479b1`
- Base prerequisite: PR `#10`, merge `70abc18a2fb0d56135dcc35a41d988a50b53c7bc`
- Prerequisite workflow: `32110199577`, success
- Valid route workflow: `32124068535`, success
- Route job: `95670635180`, success
- Artifact: `9320322911`
- Artifact digest: `sha256:c98bc4432ae5f7b18b35922a9c6d2f052b5c14128ff4f3df9ad0bb4d3ebf0692`
- Fixture source: `dolphin-emu/hwtests@f28077b139eec18967f60db6ce1e15b182dfeac0`
- Requested CPU core: `PowerPC::CPUCore::CachedInterpreter` (`Dolphin.Core.CPUCore=5`)
- Video/window route: Null backend with explicit `headless` platform
- Profiling: disabled; no CI3 profile file was created

## Result

All eight candidates produced three repeatable fresh-process routes:

- `cputest_rlw`, `cputest_cr` — `integer_control`
- `cputest_load`, `cputest_mtspr` — `memory_system`
- `cputest_frsp`, `cputest_pairedmove` — `floating_paired`
- `gxtest_bitfield`, `gxtest_tev` — `gpu_pipeline`

Every run:

- survived to the fixed 12-second stop boundary;
- followed the same controlled second-SIGTERM termination path;
- returned the same status within its candidate;
- produced a stable normalized route-signature hash;
- contained no panic, assertion, fatal-error, segmentation-fault, or other registered crash marker;
- created no profiler output while profiling was disabled.

The exact route result and generated summary hashes are preserved by
`route-recon-v2-manifest.json`.

## Invalidated attempts

These runs are retained as methodology history but are not used as gate evidence:

1. `32117017451`: obsolete no-GUI `-b` option; failed before emulation.
2. `32119465079`: omitted explicit headless platform; fbdev initialization failed before emulation.
3. `32121448667`: fixtures ran, but GNU `timeout` returned a SIGKILL status that the harness failed
   to identify as the preregistered fixed timeout.

Candidates, hashes, repetitions, timeout, normalization, and the 4-candidate/3-class threshold were
not changed in response to those attempts. The final correction replaced ambiguous shell-timeout
status inference with explicit process timeout and signal-stage accounting.

## Important limitation

The available no-GUI output contained only Dolphin's signal-shutdown message. A textual
`Cached Interpreter` marker and fixture-specific architectural result marker were not present.
Therefore this is deliberately classified as **route/liveness evidence**, not proof that each
hardware test reached or passed its intended assertion path, and not execution-weighted workload
evidence.

The next fixture-freeze step may use these candidates only as repeatable launch/stop routes. The
later profiling experiment must independently require valid aggregate profiler output and route
equivalence before any coverage decision is made.

## Data boundary

Only aggregate statuses, normalized hashes, relative open-source fixture paths, source/toolchain
pins, and bounded interpretation are committed. Raw logs, rebuilt binaries, user directories,
absolute paths, guest instruction data, firmware, keys, saves, and proprietary content are excluded.

## Evidence classification

- Route gate under the preregistered criteria: `PROVEN_RUNTIME (route, scoped)`
- Fixture-specific architectural correctness: `UNKNOWN`
- Cached-Interpreter block execution for these runs: `UNKNOWN` until valid profiler output is
  collected under the frozen measurement route
- Performance improvement: `UNKNOWN`
- Gate 2 completion: **No**
