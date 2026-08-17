# EXP-20260817-001 analysis

All four hosted jobs built successfully, passed deterministic equivalence, and produced the same checksum: `0xb261ca7ae51ec0a8`.

Speedups below are relative to `callback-two-level` on the same runner. Lower nanoseconds per operation is better.

## Linux ARM64, GCC 13.3

| Engine | Median ns/op | Speedup | Min–max ns/op |
|---|---:|---:|---:|
| `compact-switch-12` | 0.9017 | 2.22x | 0.8971–0.9087 |
| `id-switch-16` | 0.9041 | 2.22x | 0.9032–0.9156 |
| `compact-switch-8` | 0.9071 | 2.21x | 0.9040–0.9187 |
| `pinned-switch-8` | 0.9105 | 2.20x | 0.9054–0.9155 |
| `compact-switch-16` | 0.9533 | 2.10x | 0.9513–0.9595 |
| `computed-goto-8` | 1.4377 | 1.39x | 1.4361–1.4380 |
| `callback-two-level` | 2.0048 | 1.00x | 2.0033–2.0085 |

The compact switch family clearly beat callbacks in this synthetic trace. Computed goto was materially slower than the compiler-generated switch.

## macOS ARM64, AppleClang 17, virtual M1

| Engine | Median ns/op | Speedup | Min–max ns/op |
|---|---:|---:|---:|
| `preserve-none-musttail` | 1.3284 | 2.19x | 1.2738–2.5394 |
| `compact-switch-12` | 1.7956 | 1.62x | 1.7195–2.4284 |
| `compact-switch-8` | 1.8222 | 1.60x | 1.6488–2.1811 |
| `callback-devirtualized` | 2.5553 | 1.14x | 2.5318–3.3859 |
| `computed-goto-8` | 2.6046 | 1.12x | 2.3033–4.8361 |
| `callback-two-level` | 2.9126 | 1.00x | 2.8751–3.4533 |

The musttail result is the strongest Apple-target signal, but the hosted virtual M1 showed large run-to-run ranges. It is an observation requiring longer interleaved replication, not a stable performance claim.

## Compiler sensitivity on x64

- Clang 18 strongly favored compact switch and pinned local state; the best observed result was 4.03x over callbacks.
- GCC 13 generated poor switch results for the same trace; computed goto was 2.50x faster than callbacks and substantially faster than its switch variants.

This demonstrates that no single dispatch strategy should be assumed portable. CI3 should preserve more than one executor over the same IR and choose by measured target/compiler behavior.

## Important confound: state-pinning test is not independent

`RunCompactSwitch8` receives a local `MachineState` by value. An optimizing compiler can promote its four array elements into host registers across the loop. Consequently, `pinned-switch-8` does not isolate explicit CI3 state pinning from automatic scalar replacement.

The result does not promote the state-pinning hypothesis. A follow-up must model state materialization and controlled flush boundaries explicitly, then inspect generated assembly.

## Additional limitations

- one seed
- one trace length
- fixed engine execution order
- shared hosted runners
- a short smoke benchmark
- generic arithmetic/control operations only
- no MMU, exceptions, timing, floating point, paired singles, fallback calls, or real block distribution
- the callback records are CI2-like, not a byte-for-byte model of Dolphin's current records

## Interpretation

The result establishes `OBSERVED` evidence that direct compact dispatch has enough synthetic ARM64 headroom to justify a hardened Dispatch Lab. It does not pass Gate 1 and does not justify Dolphin integration yet.
