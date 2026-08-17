# EXP-20260817-001 hypothesis

## Question

Does a compact direct-dispatch representation materially outperform a CI2-like two-level callback topology on hosted x64 and ARM64 runners while preserving deterministic state equivalence?

## Pre-registered threshold

The CI3 charter set the initial promise threshold at either:

- at least 20% faster than a CI2-like callback topology, or
- strong evidence that explicit state pinning offers a credible larger gain.

## Compared engines

- two-level callback
- devirtualized two-level callback
- one-level callback
- 16-byte ID/switch
- 8-, 12-, and 16-byte compact switch
- pinned local-state switch
- computed goto
- Clang `preserve_none`/`musttail`, where available

## Expected falsifiers

- less than 10% repeatable improvement from compact dispatch
- mismatched final state
- gains that occur on only one compiler and have no viable target-specific fallback
- excessive measurement instability that prevents ordering the alternatives

## Scope

The trace is a synthetic generic four-register workload. It is not PowerPC, does not encode game-derived instruction sequences, and cannot establish a Dolphin or real-game speedup.
