# CI3 Dispatch Lab

The CI3 Dispatch Lab is a standalone synthetic benchmark for testing interpreter execution
architecture before CI3 modifies Dolphin's PowerPC backend.

It intentionally implements a small generic four-register machine, not GameCube or Wii semantics.
No guest code, ROM-derived trace, or proprietary data is included.

## Questions tested

The original dispatch executable asks:

- What is the cost of a CI2-like two-level callback path?
- How much does speculative devirtualization recover?
- How do 8-, 12-, and 16-byte records affect dense switch execution?
- Does computed goto beat a compiler-generated switch?
- Does Clang `preserve_none` plus `musttail` beat computed goto on supported targets?

The state-materialization executable asks:

- What happens when architectural state must become visible at semantic boundaries?
- How does boundary frequency change the cost?
- Does explicitly carrying four values locally survive those boundaries better than direct state
  access?

All engines execute the same deterministic trace and must produce the same checksum before timing
results are accepted.

## Build

```sh
cmake -S Tools/CI3DispatchLab -B build/ci3-dispatch-lab -DCMAKE_BUILD_TYPE=Release
cmake --build build/ci3-dispatch-lab --parallel
ctest --test-dir build/ci3-dispatch-lab --output-on-failure
```

## Run a single dispatch trace

```sh
./build/ci3-dispatch-lab/ci3_dispatch_lab \
  --iterations 10000 \
  --repetitions 7 \
  --trace-length 256 \
  --seed 0xC13C0FFEE1234567
```

## Run a single state-materialization trace

```sh
./build/ci3-dispatch-lab/ci3_state_lab \
  --iterations 10000 \
  --repetitions 7 \
  --trace-length 256 \
  --seed 0x51A7E5EED1234567
```

## Run a matrix

`run_matrix.py` randomizes a deterministic matrix of three seeds and three trace lengths, stores
per-case JSONL, and calculates speedups against a named baseline.

```sh
python3 Tools/CI3DispatchLab/run_matrix.py \
  --binary build/ci3-dispatch-lab/ci3_dispatch_lab \
  --output-dir results/dispatch \
  --baseline-engine callback-two-level
```

Use `state-promotable` as the baseline for `ci3_state_lab`.

## Dispatch engines

- `callback-two-level`: outer callback followed by an instruction callback.
- `callback-devirtualized`: common outer callback is detected and bypassed.
- `callback-one-level`: one operation callback per record.
- `id-switch-16`: 16-bit operation ID in a 16-byte record.
- `compact-switch-8`: dense switch over an 8-byte record.
- `compact-switch-12`: dense switch over a 12-byte record.
- `compact-switch-16`: dense switch over a 16-byte record.
- `pinned-switch-8`: four machine values expressed as locals. In v1 this was confounded by
  compiler scalar promotion and is not independent evidence of explicit pinning.
- `computed-goto-8`: GNU/Clang labels-as-values dispatch over 8-byte records.
- `preserve-none-musttail`: fixed-signature Clang tail-threaded handlers where supported.

## State-materialization engines

The state lab links a no-inline semantic-boundary function from a separate translation unit. The
call forces escaped state to be materialized and treated as possibly modified without adding guest
semantics.

It compares direct-state and explicit-local variants with:

- no boundary
- a boundary after every operation
- a boundary after every four operations
- a boundary after every sixteen operations
- a boundary once per trace

The benchmark includes call and materialization cost. It models a semantic boundary, not a complete
Dolphin exception, HLE, timing, or debugger path.

## Output

Both executables emit JSON Lines. Each benchmark record contains the engine, trace parameters,
median/min/max nanoseconds per operation, and deterministic checksum.

`run_matrix.py` additionally emits:

- one raw JSONL file per case
- `combined.jsonl`
- `summary.json`
- `summary.md`

Use `--verify-only` for a fast equivalence test.

## Limitations

The lab uses synthetic arithmetic/control mixes. It does not model Dolphin's MMU, exceptions,
timing, floating point, paired singles, HLE transitions, debugger boundaries, or real block
distributions. Hosted virtual hardware is noisy. A positive result permits a more realistic
experiment; it does not prove a Dolphin or real-game speedup.

## AI disclosure

This experimental benchmark was substantially drafted with AI assistance. It is isolated from
emulated-console behavior and is not presented as an upstream Dolphin contribution.
