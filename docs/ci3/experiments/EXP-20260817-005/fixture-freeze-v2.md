# EXP-20260817-005 fixture and paired-run freeze v2

**Decision: PASS — fixture set and collection order are frozen before profile access.**

- Source-build prerequisite: `70abc18a2fb0d56135dcc35a41d988a50b53c7bc` / workflow `32110199577`
- Route prerequisite: `4b67e513f913c77e534aaf50d6b7ecae8780d7b2` / workflow `32124068535`
- Route artifact: `9320322911` / `sha256:c98bc4432ae5f7b18b35922a9c6d2f052b5c14128ff4f3df9ad0bb4d3ebf0692`
- Selected fixtures: 8; no qualified candidate was removed
- Workload classes: 4; two fixtures per class
- Profile output generated or examined for selection: no
- Frozen schedule SHA-256: `e21f81d5f343d23a9feef0852f1dbcc8e625bec3a978a44a03e0baba2e33db85`

## Frozen fixtures

| ID | Candidate | Class | Source-relative output | Binary SHA-256 | Route invariant |
|---|---|---|---|---|---|
| `F01` | `cputest_rlw` | `integer_control` | `build/cputest/cputest_rlw.elf` | `2d3904ade2eb089d7b3e250d547ebeff5623485f0d74fcb6128023bf3e63cafd` | `3 runs; exit=-15; stage=second_sigterm; signature=8d6897f3ac80ad95d8f1a5764e41d889351d44cf41e6935b6f1b5484a9a979ca` |
| `F02` | `cputest_cr` | `integer_control` | `build/cputest/cputest_cr.elf` | `a6ad00f9399816530cb95e6fb659030ba51a5748c3abc5f3163cb50abd14d95b` | `3 runs; exit=-15; stage=second_sigterm; signature=8d6897f3ac80ad95d8f1a5764e41d889351d44cf41e6935b6f1b5484a9a979ca` |
| `F03` | `cputest_load` | `memory_system` | `build/cputest/cputest_load.elf` | `0647e3e92f3504806ee73a25b4b35b35b64424b41617504577719e4ec9f65af2` | `3 runs; exit=-15; stage=second_sigterm; signature=8d6897f3ac80ad95d8f1a5764e41d889351d44cf41e6935b6f1b5484a9a979ca` |
| `F04` | `cputest_mtspr` | `memory_system` | `build/cputest/cputest_mtspr.elf` | `32d40f003954a063fc940bc3f15b989ac8a349801caff84fd1dfc01ba5271f19` | `3 runs; exit=-15; stage=second_sigterm; signature=8d6897f3ac80ad95d8f1a5764e41d889351d44cf41e6935b6f1b5484a9a979ca` |
| `F05` | `cputest_frsp` | `floating_paired` | `build/cputest/cputest_frsp.elf` | `d6a6f6c9852b39c6cb33cb44fc0115be776ead9ce9abcf3d835f5872985c936a` | `3 runs; exit=-15; stage=second_sigterm; signature=8d6897f3ac80ad95d8f1a5764e41d889351d44cf41e6935b6f1b5484a9a979ca` |
| `F06` | `cputest_pairedmove` | `floating_paired` | `build/cputest/cputest_pairedmove.elf` | `a13a6dc406f92aecabbf585036d1d05e8506481bd4e9e4ce67c3a71777bbc078` | `3 runs; exit=-15; stage=second_sigterm; signature=8d6897f3ac80ad95d8f1a5764e41d889351d44cf41e6935b6f1b5484a9a979ca` |
| `F07` | `gxtest_bitfield` | `gpu_pipeline` | `build/gxtest/gxtest_bitfield.elf` | `ea79ed906a47a9c2f7b181c4ba30aba70633d484ddd4582f0098e247c6507e24` | `3 runs; exit=-15; stage=second_sigterm; signature=8d6897f3ac80ad95d8f1a5764e41d889351d44cf41e6935b6f1b5484a9a979ca` |
| `F08` | `gxtest_tev` | `gpu_pipeline` | `build/gxtest/gxtest_tev.elf` | `ebcd0322c542bc606ffc69726992794b79e3929cb1d577fa13f9bddb7d5b4fee` | `3 runs; exit=-15; stage=second_sigterm; signature=8d6897f3ac80ad95d8f1a5764e41d889351d44cf41e6935b6f1b5484a9a979ca` |

## Frozen collection order

- Four warm-ups per fixture: `baseline, treatment, treatment, baseline`.
- Eight adjacent baseline/treatment pairs per fixture.
- Four baseline-first and four treatment-first pairs per fixture.
- Rotated round order puts every fixture in every ordinal position once.
- Baseline leaves `DOLPHIN_CI3_BLOCK_PROFILE_PATH` unset; treatment uses a unique fresh path.
- Measured profiles remain unopened until the complete collection passes completeness checks.

## Boundary

This is an anti-selection and anti-ordering control. It does not prove hardware-test completion,
textual Cached Interpreter selection, acceptable profiler overhead, hot-work coverage, lowering
value, Dolphin performance, game playability, or iPhone viability. Gate 2 remains open.

## Decision

Proceed only to a collection harness that consumes these files unchanged and fails closed on an
incomplete pair schedule, schema drift, route drift, or a missing baseline/treatment result.
