# CI3 Dispatch Lab

The CI3 Dispatch Lab is a standalone synthetic benchmark for testing interpreter execution topology before CI3 modifies Dolphin's PowerPC backend.

It intentionally implements a small generic four-register machine, not GameCube or Wii semantics. No guest code, ROM-derived trace, or proprietary data is included.

## Questions tested

- What is the cost of a CI2-like two-level callback path?
- How much does speculative devirtualization recover?
- How do 8-, 12-, and 16-byte records affect dense switch execution?
- Does computed goto beat a compiler-generated switch?
- Does carrying four machine registers as locals reduce state traffic?
- Does Clang `preserve_none` plus `musttail` beat computed goto on supported targets?

All engines execute the same deterministic trace and must produce the same checksum before timing results are accepted.

## Build

```sh
cmake -S Tools/CI3DispatchLab -B build/ci3-dispatch-lab -DCMAKE_BUILD_TYPE=Release
cmake --build build/ci3-dispatch-lab --parallel
ctest --test-dir build/ci3-dispatch-lab --output-on-failure
```

## Run

```sh
./build/ci3-dispatch-lab/ci3_dispatch_lab \
  --iterations 10000 \
  --repetitions 5 \
  --trace-length 256 \
  --seed 0xC13C0FFEE1234567
```

Output is JSON Lines. Each benchmark record includes the engine, record size, trace parameters, median/min/max nanoseconds per operation, and deterministic checksum.

Use `--verify-only` for a fast equivalence test.

## Engines

- `callback-two-level`: outer callback followed by an instruction callback.
- `callback-devirtualized`: common outer callback is detected and bypassed.
- `callback-one-level`: one operation callback per record.
- `id-switch-16`: 16-bit operation ID in a 16-byte record.
- `compact-switch-8`: dense switch over an 8-byte record.
- `compact-switch-12`: dense switch over a 12-byte record.
- `compact-switch-16`: dense switch over a 16-byte record.
- `pinned-switch-8`: 8-byte records with four machine registers held as local values.
- `computed-goto-8`: GNU/Clang labels-as-values dispatch over 8-byte records.
- `preserve-none-musttail`: fixed-signature Clang tail-threaded handlers where supported.

## Limitations

This lab measures a synthetic arithmetic/control mix. It does not model Dolphin's MMU, exceptions, timing, floating point, paired singles, HLE transitions, debugger boundaries, or real block distributions. A positive result permits Dolphin integration work; it does not prove a real-game speedup.

## AI disclosure

This experimental benchmark was substantially drafted with AI assistance. It is isolated from emulated-console behavior and is not presented as an upstream Dolphin contribution.
