# CI3-PIR claims register

| ID | Claim | State | Evidence | Promotion requirement |
|---|---|---|---|---|
| C-001 | The fork matches current Dolphin master at bootstrap commit `fa61f77f`. | PROVEN_SOURCE | Pinned Git refs on 2026-08-17. | Re-pin after upstream sync. |
| C-002 | Mainline Cached Interpreter uses cached non-executable callback records and retains indirect dispatch in its common execution path. | PROVEN_SOURCE | Pinned Dolphin Cached Interpreter source and merged CI2/devirtualization history. | Recheck after upstream changes. |
| C-003 | iCube already implements ID dispatch, computed-goto micro-ops, direct hot handlers, guarded RAM paths, profiling, NEON paired-single paths, and experimental linking. | PROVEN_SOURCE | Pinned iCube branch at `8328103`. | Runtime reproduction under matched settings. |
| C-004 | iCube's public source does not by itself establish a controlled speedup attributable to each CPU optimization. | OBSERVED | No preserved matched benchmark suite was found during source review. | Locate or produce controlled benchmark evidence. |
| C-005 | Persistent CPU translation caching is established prior art. | PROVEN_SOURCE | Ryujinx PTC stores native code, relocations, unwind data, hashes, and profile state. | None; CI3 must distinguish portable IR persistence. |
| C-006 | A persistent IR cache alone does not remove steady-state interpreter dispatch. | INFERRED | Execution-cost model. | Runtime ablation after persistence exists. |
| C-007 | Compact pointer-free records can beat a CI2-like callback topology by at least 20%. | UNKNOWN | Dispatch Lab not yet implemented. | Gate 1 controlled benchmark. |
| C-008 | State pinning can materially reduce architectural-state traffic. | UNKNOWN | Supported by VM prior art, not Dolphin runtime evidence. | Dispatch Lab and Dolphin ablation. |
| C-009 | `preserve_none`/`musttail` beats computed goto on Apple arm64e. | UNKNOWN | Compiler mechanism exists; target result unmeasured. | Same-IR macOS ARM64 benchmark and assembly audit. |
| C-010 | CI3 can achieve approximately 1.5x CPU-thread performance over mainline Cached Interpreter. | UNKNOWN | No implementation or runtime evidence. | Gate 3 matched benchmark. |
| C-011 | CI3 can sustain full speed for at least one commercial GameCube title on the target iPhone in strict no-codegen mode. | UNKNOWN | No device build or result. | Gate 4 sustained device verification. |
| C-012 | The software vertex loader will become the next dominant bottleneck. | UNKNOWN | Plausible architecture risk only. | Per-frame subsystem timing after CPU acceleration. |

Claims must be demoted when source pins change or controls invalidate the supporting evidence.
