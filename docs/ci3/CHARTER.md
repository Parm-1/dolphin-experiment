# CI3-PIR charter

## Mission

Determine whether a new JITless PowerPC execution backend for Dolphin can provide a significant, correctness-preserving performance improvement on Apple ARM64 and eventually sustain full-speed execution for at least part of the GameCube library on a stock iPhone without application-generated host CPU code.

## Primary thesis

A compact pointer-free PowerPC IR, combined with block-selected guest-register pinning, guarded RAM access, and generation-safe block chaining, can achieve at least a 1.5x CPU-thread performance improvement over current mainline Dolphin Cached Interpreter under identical accuracy and rendering settings.

This is a falsifiable hypothesis, not a promised result.

## Independent claims

1. **Execution:** compact IR and state pinning materially improve steady-state CPU execution.
2. **Correctness:** optimized paths match Dolphin's reference Interpreter at every supported semantic boundary.
3. **Product:** strict no-runtime-codegen mode reaches sustained full speed in at least one commercial GameCube title on the target iPhone.
4. **Persistence:** a portable per-title IR/profile cache improves startup and warm-up without semantic or steady-state regressions.

Failure of one claim must not be hidden by success in another. Faster cache loading is not evidence of faster steady-state interpretation.

## Gates

### Gate 0 — source and benchmark bootstrap

Required:

- Source pins and prior-art delta are recorded.
- Legal and AI boundaries are explicit.
- Benchmark protocol is versioned.
- A standalone dispatch laboratory is designed.

### Gate 1 — dispatch laboratory

Proceed to Dolphin integration only if compact execution shows material promise in representative synthetic and captured aggregate mixes.

Desired evidence:

- At least 20% over a CI2-like callback topology, or
- Strong evidence that state pinning provides a credible path beyond that.

### Gate 2 — minimum Dolphin integration

Required:

- At least 20% improvement in representative CPU microbenchmarks over mainline Cached Interpreter.
- At least 10–15% improvement in one real CPU-limited title or legal homebrew proxy.
- No unexplained differential-correctness failures.

Persistence must not begin before this gate.

### Gate 3 — structural performance

Required:

- Approximately 1.5x CPU-thread performance over mainline Cached Interpreter.
- Better performance than the pinned iCube comparison under matched settings.
- Controlled ablations for retained optimizations.

### Gate 4 — strict no-codegen product

Required:

- Device-verified iPhone result.
- CPU JIT and generated native vertex loader disabled.
- At least one commercial GameCube title at sustained 100% emulation speed.
- No prohibited timing or accuracy shortcut.

### Gate 5 — persistence

Required:

- Measurable cold-start or warm-up improvement.
- Safe validation and invalidation.
- No material steady-state regression.

## Initial architecture hypotheses

- H1: compact pointer-free records reduce dispatch and data-footprint cost.
- H2: computed goto or a dense switch is a strong portable baseline.
- H3: `preserve_none`/`musttail` may improve Apple ARM64 execution by carrying state in host registers.
- H4: block-selected register slots reduce repeated `PowerPCState` traffic.
- H5: guarded MEM1/MEM2, stack-relative, BAT-stable, or software-TLB operations reduce generic MMU cost.
- H6: generation-checked data links reduce block-dispatch overhead safely.
- H7: a bounded profile-selected static superoperation library improves dispatch efficiency without excessive I-cache growth.
- H8: portable persistent IR and profiles improve warm-up, not inherently steady-state execution.
- H9: the software vertex loader may become the dominant strict-no-codegen bottleneck after CPU acceleration.

## Initial non-goals

- Switch or Wii U emulation.
- A new frontend or App Store submission.
- Persistent caching before the execution engine is proven.
- Hundreds of handwritten semantic fast paths.
- DSP redesign.
- Game-specific speed patches.
- Public performance claims without preserved raw evidence.
- Upstream submission of AI-generated console-behavior code.
