# EXP-20260817-002 analysis

## Result

The hardened Dispatch Lab passed all five hosted build/test jobs. Every engine produced the same
deterministic final state in every case. The matrix covered three fixed seeds, trace lengths of 64,
256, and 1024 operations, approximately two million operations per case, and seven measured
repetitions.

This experiment remains synthetic. It establishes runtime properties of the proposed execution
topologies, not Dolphin, PowerPC, game, or iPhone performance.

## H2a — compact ARM64 dispatch

**Supported.**

For each ARM64 compiler target, at least one pre-registered compact or tail-threaded executor
exceeded the callback baseline by more than 20% in every one of the nine cases.

| Target | Representative engine | Median speedup | Minimum case | Maximum case | Median ns/op |
|---|---|---:|---:|---:|---:|
| Linux ARM64, GCC 13.3 | `compact-switch-12` | 2.241x | 2.196x | 2.461x | 0.8653 |
| Linux ARM64, Clang 18.1 | `compact-switch-16` | 1.412x | 1.349x | 1.488x | 1.2616 |
| virtual M1, AppleClang 17 | `preserve-none-musttail` | 2.159x | 1.670x | 2.352x | 1.2545 |

The compact switch result is therefore not a one-seed anomaly. The absolute magnitude remains
compiler-dependent.

## H2b — no universal dispatch topology

**Supported.**

- GCC ARM64 strongly favored a compact compiler-generated switch.
- Clang ARM64 also favored a compact switch, but by a smaller margin.
- AppleClang ARM64 favored `preserve_none`/`musttail`.
- GCC x64 favored computed goto, with a 2.617x median speedup.
- Clang x64 generated a different ordering again.

CI3 should keep a common portable IR and permit target/compiler-specific executors. It should not
hard-code computed goto, switch, or musttail as universally superior.

## H3a — semantic-boundary frequency

**Supported, with a non-monotonic-codegen caveat.**

The no-inline boundary was emitted in a separate translation unit. Assembly shows the caller
materializing four values, calling `CI3SemanticBoundary`, and reloading them. The boundary function
itself contains no guest work.

Median cost of an every-operation boundary relative to one boundary per trace:

| Target | Direct state | Explicit local state |
|---|---:|---:|
| Linux ARM64, GCC | 1.773x | 2.232x |
| Linux ARM64, Clang | 1.204x | 1.818x |
| virtual M1, AppleClang | 1.326x | 1.569x |

Boundary frequency is therefore a first-order cost. The exact ordering was not strictly monotonic:
some GCC variants made an every-four boundary more expensive than every-operation. Compiler
register allocation, loop layout, and spill placement must be inspected rather than inferred from
the source-level interval alone.

## H3b — explicit local state

**Conditionally supported.**

The table reports direct-state time divided by explicit-local time at the same boundary. Values
above 1.0 mean explicit locals were faster.

| Target | No boundary | Per trace | Every 16 | Every 4 | Every op |
|---|---:|---:|---:|---:|---:|
| Linux ARM64, GCC | 1.007x (6/9) | 1.004x (7/9) | **1.144x (9/9)** | 0.931x (0/9) | 0.801x (0/9) |
| Linux ARM64, Clang | **1.351x (9/9)** | **1.435x (9/9)** | **1.277x (9/9)** | **1.155x (9/9)** | 0.895x (0/9) |
| virtual M1, AppleClang | **1.151x (9/9)** | **1.249x (8/9)** | **1.182x (7/9)** | **1.221x (9/9)** | 1.066x (8/9) |

The result supports block- or superblock-scoped state carrying. It does not support mandatory
per-instruction flush/reload. On Linux ARM64, explicit locals became slower when forced through a
boundary after every operation.

This is synthetic evidence for the mechanism, not evidence that Dolphin's actual register liveness,
exceptions, HLE calls, debugger boundaries, or MMU paths will permit the same retention interval.

## Assembly audit

AppleClang emitted the intended tail-threaded form. `TailAdd0` compiled to:

```asm
ldr   x0, [x20, #0x10]!
ldur  w8, [x20, #-0x8]
add   x23, x8, x23
br    x0
```

There is no ordinary call/return between operations.

The state-boundary model was also preserved. GCC ARM64 emitted paired stores of local values,
`bl CI3SemanticBoundary`, and paired reloads. `CI3SemanticBoundary` itself compiled to `ret`.
The measured boundary cost therefore includes materialization and call/return overhead rather than
guest semantics.

## Text footprint

Linux ARM64 executable text sizes:

| Compiler | Dispatch lab | State lab |
|---|---:|---:|
| GCC 13.3 | 36,220 bytes | 34,612 bytes |
| Clang 18.1 | 34,439 bytes | 35,108 bytes |

These sizes do not yet model a large PowerPC opcode or superoperation library.

## Limitations

- Generic four-register arithmetic/control workload.
- No PowerPC decoding or Dolphin block distribution.
- No MMU, exceptions, timing, floating point, paired singles, HLE, debugger, or invalidation.
- Hosted virtual machines rather than controlled bare-metal hardware.
- Fixed engine order within a case; only case order was shuffled.
- No hardware performance counters.
- The boundary model is deliberately conservative but not an actual Dolphin semantic boundary.
- State engines differ enough for compiler code shape to remain an important confound.
- No real-game, iPhone, or strict-no-codegen result.

## Interpretation

The synthetic falsifier did not trigger. Compact direct dispatch is robust enough on ARM64 to
justify a minimum PowerPC-facing experiment. Explicit local state is valuable only when semantic
boundaries are sufficiently coarse, which directly constrains the CI3 architecture: keep values
local across blocks or superblocks and flush only at proven boundaries.

The experiment does not justify persistence, a full backend, or performance claims about Dolphin.
