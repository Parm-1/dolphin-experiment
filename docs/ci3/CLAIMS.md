# CI3-PIR claims register

| ID | Claim | State | Evidence | Promotion requirement |
|---|---|---|---|---|
| C-001 | The fork matched Dolphin master at bootstrap commit `fa61f77f`. | PROVEN_SOURCE | Pinned Git refs on 2026-08-17. | Re-pin after upstream sync. |
| C-002 | Mainline Cached Interpreter uses cached non-executable callback records and retains indirect dispatch in its common execution path. | PROVEN_SOURCE | Pinned Dolphin Cached Interpreter source and merged CI2/devirtualization history. | Recheck after upstream changes. |
| C-003 | iCube already implements ID dispatch, computed-goto micro-ops, direct hot handlers, guarded RAM paths, profiling, NEON paired-single paths, and experimental linking. | PROVEN_SOURCE | Pinned iCube branch at `8328103`. | Runtime reproduction under matched settings. |
| C-004 | iCube's public source does not by itself establish a controlled speedup attributable to each CPU optimization. | OBSERVED | No preserved matched benchmark suite was found during source review. | Locate or produce controlled benchmark evidence. |
| C-005 | Persistent CPU translation caching is established prior art. | PROVEN_SOURCE | Ryujinx PTC stores native code, relocations, unwind data, hashes, and profile state. | None; CI3 must distinguish portable IR persistence. |
| C-006 | A persistent IR cache alone does not remove steady-state interpreter dispatch. | INFERRED | Execution-cost model. | Runtime ablation after persistence exists. |
| C-007 | Compact direct dispatch has material synthetic ARM64 headroom over a CI2-like callback topology. | OBSERVED | EXP-20260817-001: 2.22x Linux ARM64 compact switch; 1.62x virtual-M1 compact switch. | Replicate across traces, harden methodology, then integrate minimally into Dolphin. |
| C-008 | Explicit block-selected state pinning materially reduces architectural-state traffic. | UNKNOWN | V1 ordinary switch state could be compiler-promoted; comparison is confounded. | Controlled materialization/flush experiment and assembly audit. |
| C-009 | `preserve_none`/`musttail` has material synthetic Apple ARM64 promise. | OBSERVED | EXP-20260817-001: 2.19x median on a virtual M1, with high variance. | Longer interleaved replication and Apple assembly audit. |
| C-010 | CI3 can achieve approximately 1.5x CPU-thread performance over mainline Cached Interpreter. | UNKNOWN | No Dolphin implementation or runtime evidence. | Gate 3 matched benchmark. |
| C-011 | CI3 can sustain full speed for at least one commercial GameCube title on the target iPhone in strict no-codegen mode. | UNKNOWN | No device build or result. | Gate 4 sustained device verification. |
| C-012 | The software vertex loader will become the next dominant bottleneck. | UNKNOWN | Plausible architecture risk only. | Per-frame subsystem timing after CPU acceleration. |
| C-013 | Computed goto is not uniformly superior to a compiler-generated switch. | OBSERVED | EXP-20260817-001: switch won on ARM64; computed goto won strongly under GCC x64. | Repeat across mixes and compiler versions. |
| C-014 | Dispatch performance is materially compiler- and architecture-sensitive. | OBSERVED | EXP-20260817-001 cross-runner ordering differed sharply. | Replication and generated-assembly comparison. |

Claims must be demoted when source pins change or controls invalidate the supporting evidence.
