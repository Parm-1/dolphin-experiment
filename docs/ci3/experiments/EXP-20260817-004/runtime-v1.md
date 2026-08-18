# EXP-20260817-004 runtime integration v1

This slice connects aggregate-only profiling to Cached Interpreter through the non-empty
`DOLPHIN_CI3_BLOCK_PROFILE_PATH` environment variable.

The disabled path allocates no session and performs no file I/O. When enabled, successfully
finalized compilations contribute their existing analyzed `PPCAnalyst::CodeOp` span. Canonical
schema-v1 JSON is written only during explicit orderly shutdown. No guest instruction word,
address, disassembly, ordered trace, title identifier, or proprietary content is retained.

The output remains compilation-weighted, not execution-weighted and not a unique-block census.
Tests cover disabled activation, construction/destruction side effects, canonical explicit flush,
stale-file overwrite, invalid-target failure, and all earlier CI3 regressions.

Passing establishes only a privacy-bounded opt-in instrumentation route. It does not establish a
legal workload profile, profiling overhead, a CI3 executor, a Dolphin speedup, a game or iPhone
result, or Gate 2 completion.

The design and implementation are substantially AI-assisted and remain confined to this
experimental fork.
