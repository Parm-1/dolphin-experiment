# EXP-20260817-004 hypothesis

## Question

Can an opt-in, aggregate-only profiler attached to Dolphin's existing Cached Interpreter analysis path
produce a deterministic summary of encountered PowerPC block structure, opcode mix, register use,
semantic boundaries, and coverage by the current 17-operation CI3 subset without changing guest
semantics or retaining raw guest code?

## Purpose

`EXP-20260817-003` established scoped semantic agreement for a test-local eight-byte operation
format. It did not establish that real analyzed blocks contain enough supported operations, local
register reuse, or sufficiently coarse materialization boundaries for a runtime backend to retain
the Dispatch Lab advantage.

This experiment builds the smallest evidence route needed to answer that workload-shape question
before broader lowering or executor work.

## Observation unit

One observation is one successful Cached Interpreter block compilation after
`PPCAnalyzer::Analyze` and `CachedInterpreter::DoJit` have succeeded.

The initial profiler is deliberately **not**:

- a unique-block census;
- dynamically weighted by execution count;
- a persistent guest-code trace;
- a performance benchmark;
- a production telemetry feature.

Cache invalidation or recompilation may therefore cause the same guest block to contribute more
than once. This limitation must be recorded with every result.

## Activation and output

The profiler is disabled by default.

It is enabled only when the environment variable `DOLPHIN_CI3_BLOCK_PROFILE_PATH` contains a
non-empty output path. When enabled, the Cached Interpreter records aggregate counters in memory and
writes one deterministic JSON document during orderly shutdown.

An unset or empty environment variable must preserve the existing behavior and create no profiler
object or output file.

## Aggregate schema

The JSON output may contain only schema/version metadata and aggregate counts or histograms.

Required aggregates:

- observed successful block compilations;
- broken blocks;
- analyzed operations;
- eligible non-skipped operations;
- skipped operations;
- analyzed and eligible block-length histograms;
- opcode-name counts;
- GPR reads and writes per eligible operation;
- maximum within-block live-future GPR count;
- current 17-operation-subset coverage;
- contiguous supported-run lengths;
- blocks with any supported operation;
- fully supported eligible blocks;
- overlapping semantic-feature counts for load/store, FPU, block end, exception, carry, overflow,
  condition register, FPRF, system state, and branch operations;
- within-block GPR read reuse-distance buckets: `1`, `2`, `3-4`, `5-8`, `9-16`, `17+`, and
  `external_or_earlier_block`.

The output must not contain:

- guest instruction words;
- guest virtual or physical addresses;
- disassembly;
- ordered opcode or register sequences;
- title, game, firmware, save, or user identifiers;
- ROM, executable, key, or other proprietary data.

## Current-subset classifier

An operation is classified as supported only when:

- it is one of the 17 forms established in `EXP-20260817-003`;
- any record bit is clear;
- it is not skipped;
- it has no load/store, FPU, block-ending, exception, carry, overflow, timer, MSR, CR, or FPRF
  requirement outside the tested subset;
- its analyzed operation does not dynamically end the block or cause an exception.

This is a coverage classifier, not a lowering implementation.

## Validation fixtures

Unit tests will construct synthetic `PPCAnalyst::CodeOp` blocks with controlled metadata. They will
verify exact aggregate counts, supported-run lengths, semantic-feature categories, GPR read/write
histograms, reuse-distance buckets, skipped-operation handling, and deterministic serialization.

The fixtures contain no guest program or proprietary-derived trace.

## Pass condition

The experiment passes its instrumentation gate only if:

- exact synthetic aggregate tests pass;
- serialization of the same aggregate state is byte-for-byte deterministic;
- the serialized schema contains only approved aggregate fields;
- the profiler remains optional and disabled by default;
- the full Dolphin unit-test target builds on Linux x86-64, Linux ARM64, and Apple ARM64;
- all `CI3BlockProfile.*` tests pass on those targets;
- all existing `CI3PowerPCIntegerDifferential.*` tests continue to pass;
- no production execution or guest architectural state is changed by the disabled path.

## Falsifiers

- any raw instruction word, guest address, disassembly, ordered trace, or title identifier appears in
  output;
- the profiler is required for normal Cached Interpreter operation;
- enabling the profiler changes guest architectural results;
- aggregate results for identical synthetic input are nondeterministic;
- a required metric cannot be derived without retaining prohibited raw data;
- existing differential tests regress;
- any hosted target fails for a source or portability reason attributable to the profiler.

## Interpretation boundary

Passing proves only that CI3 has a privacy-bounded, reproducible instrumentation route over
successfully analyzed Cached Interpreter blocks.

It does not establish:

- the block distribution of any real workload;
- execution-weighted coverage;
- a performance improvement;
- correct CI3 lowering or fallback;
- a selectable CPU backend;
- a real-game, iPhone, thermal, or strict no-codegen result;
- Gate 2 completion.

A later data-collection run must use a legal, explicitly recorded workload and preserve only the
aggregate JSON. Dynamic weighting, if needed, is a separate experiment.

## AI disclosure

The experimental design and implementation are substantially AI-assisted and remain confined to
the user's research fork. They are not intended for upstream submission under Dolphin's current
generative-AI contribution policy.
