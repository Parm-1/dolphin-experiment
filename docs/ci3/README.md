# CI3-PIR

CI3-PIR is an experimental research program for a portable, high-performance, JITless PowerPC execution backend for Dolphin.

The project asks whether a compact pointer-free interpreter representation, block-selected guest-state pinning, guarded memory specialization, and generation-safe block chaining can materially outperform Dolphin's current Cached Interpreter while preserving reference-interpreter behavior.

## Status

The project is at **Gate 0: source and benchmark bootstrap**. No CI3 CPU backend exists yet, and no performance result has been established.

The first implementation artifact is a standalone dispatch laboratory. It must test the proposed execution topology before any broad Dolphin integration, persistent cache, iOS frontend work, or PowerPC semantic rewrite.

## Boundaries

- GameCube first; Wii later.
- No runtime-generated host CPU instructions in the eventual strict configuration.
- Metal shader and pipeline compilation is outside this CPU-codegen boundary.
- No ROMs, firmware, keys, proprietary binaries, or derived game data may be committed.
- No VBI Skip, CPU underclocking, game timing patches, or unverified Fast FP paths may support the primary performance claim.
- The Dolphin reference Interpreter remains the semantic oracle.

## AI disclosure and upstream policy

This fork is being developed with substantial AI assistance. Dolphin's `Contributing.md` states that non-trivial AI-generated contributions must be disclosed and that LLMs must not be used to make upstream changes related to emulated-console behavior.

Accordingly:

- CI3 work remains experimental in this fork.
- AI-authored console-behavior changes must not be submitted upstream as ordinary Dolphin contributions.
- Any future upstreamable work must be independently understood, rewritten or validated as required by Dolphin's policy, and explicitly disclosed.
- Generic tooling, benchmark infrastructure, and documentation remain subject to normal review and attribution.

## Evidence vocabulary

- `PROVEN_SOURCE`: directly supported by pinned source or authoritative documentation.
- `PROVEN_RUNTIME`: reproduced under a recorded controlled experiment.
- `OBSERVED`: directly seen, but not yet controlled or generalized.
- `INFERRED`: reasoned from evidence, not directly proven.
- `UNKNOWN`: not established.
- `BLOCKED_ENVIRONMENT`: cannot currently be tested with available hardware, runner, toolchain, or fixture.
- `DISPROVEN`: a pre-registered hypothesis failed under recorded conditions.

See the other files in this directory for the charter, current project state, source pins, claims, risks, and benchmark protocol.
