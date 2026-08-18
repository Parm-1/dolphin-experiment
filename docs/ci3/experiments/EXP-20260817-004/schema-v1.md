# CI3 aggregate block-profile schema v1

This document defines the deterministic JSON representation produced from `BlockProfileData`.
It is a serialization contract for aggregate research evidence, not a runtime-integration or
performance claim.

## Identity and observation semantics

The top-level metadata is fixed:

- `schema`: `ci3-powerpc-block-profile`
- `schema_version`: `1`
- `observation_unit`: `successful_cached_interpreter_block_compilation`
- `execution_weighted`: `false`
- `unique_blocks`: `false`
- `duplicate_compilations_possible`: `true`

These fields make the primary limitation explicit: repeated compilation after invalidation or cache
clearing may contribute the same guest block more than once. The schema must not be interpreted as a
unique-block census or an execution-frequency profile.

## Aggregate payload

`aggregates` contains only counters and histograms already represented by `BlockProfileData`:

- block and operation totals;
- analyzed and eligible block-length histograms;
- current-subset supported-run lengths;
- opcode-name counts;
- GPR read/write cardinality arrays;
- maximum future-live GPR pressure;
- overlapping semantic-feature counts;
- within-block GPR reuse-distance counts.

Numeric-map keys are serialized as decimal JSON object keys. Fixed arrays and named feature objects
have a stable order. All counters are emitted as decimal integers without conversion through
floating point, preserving the full unsigned 64-bit range in the serialized text.

## Determinism

For the same `BlockProfileData`, serialization must be byte-for-byte identical across repeated
calls. Determinism follows from:

- fixed top-level and aggregate field order;
- ordered `std::map` traversal;
- fixed array and enum-name order;
- locale-independent `std::to_chars` integer formatting;
- a final newline.

## Privacy and provenance boundary

Schema v1 has no fields for:

- guest instruction words;
- virtual or physical guest addresses;
- disassembly or ordered opcode/register traces;
- title, game, firmware, save, user, or filename identifiers;
- ROMs, executables, keys, or proprietary-derived data.

Opcode keys are Dolphin table names, not guest bytes. A later runtime collector must write only this
aggregate document and must not add ad hoc metadata that could identify or reconstruct a workload.

## Evolution

Any field addition, removal, rename, type change, or observation-semantics change requires a new
`schema_version`. Execution weighting and unique-block accounting are separate experiments and must
not silently alter schema v1 semantics.
