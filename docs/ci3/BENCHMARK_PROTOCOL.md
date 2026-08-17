# CI3-PIR benchmark protocol v0.1

This protocol is provisional until the dispatch laboratory and first runnable Dolphin baseline exist.

## General rules

- Compare identical source pins, build types, compiler versions, and relevant settings.
- Change one performance mechanism at a time.
- Preserve raw output and machine-readable summaries.
- Report median and spread, never only the best run.
- Separate CPU-backend performance from total emulator performance.
- Record negative and null results.

## Prohibited support for the primary claim

- VBI Skip.
- CPU underclocking.
- Game-specific timing or internal-frame-rate patches.
- Unverified Fast FP paths.
- Reduced-accuracy MMU or CPU-cache behavior.
- Different renderer or vertex-loader settings between compared CPU backends.

## Dispatch Lab

Each run must record:

- commit SHA
- runner OS and architecture
- compiler identity and version
- build type and flags
- operation-record size
- trace length and seed
- iterations and repetitions
- engine availability
- deterministic checksum
- median nanoseconds per guest-like operation
- minimum and maximum result
- executable size when practical

Required engines:

- CI2-like two-level callback
- one-level callback
- ID/switch
- compact switch
- compact computed goto where supported
- compact pinned-state executor
- `preserve_none`/`musttail` executor where supported

Every engine must produce the same final state for the same trace and initial state.

Synthetic traces must be generic register-machine operations. They must not encode copyrighted guest code or claim to reproduce a real game workload.

## Dolphin CPU-isolation mode

Purpose: isolate CPU-backend cost.

- Native generated vertex loader may be used where legally and technically available.
- This mode is explicitly not strict no-codegen.
- Renderer, DSP, accuracy settings, route, and fixture must remain fixed.

## Strict no-codegen mode

- CPU JIT unavailable.
- Generated native vertex loader unavailable.
- Software vertex loader selected.
- No application allocation of writable executable CPU pages.
- Startup log records the selected backend and boundary.

## Real workload recording

For every milestone scenario, record:

- date/timezone
- device or host model
- OS version
- compiler/toolchain
- repository and commit
- local patch commit
- build flags
- renderer
- vertex-loader mode
- DSP mode
- accuracy settings
- title/homebrew identity and hashes where appropriate
- deterministic route/input
- warm-up method
- run duration
- number of repetitions
- CPU-thread time
- total frame time
- emulation speed, FPS, and VPS where applicable
- p50/p95/p99 frame time
- generic fallback and memory-fast-path rates
- thermal decline during sustained device runs

Commercial game data remains local and uncommitted.

## Minimum repetition policy

- Development smoke tests: at least two repetitions.
- Gate evidence: at least five measured repetitions after warm-up.
- Final iPhone result: at least 15 minutes sustained, with power and thermal conditions recorded.
