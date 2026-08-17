# EXP-20260817-003 hypothesis

## Question

Can a compact, pointer-free eight-byte operation format execute a first register-only PowerPC integer subset with exactly the same architectural results as Dolphin's reference Interpreter?

## Scope

This experiment is deliberately narrower than a CI3 backend. It covers only operations whose selected forms:

- touch general-purpose registers only
- do not request the record bit
- do not read or write carry or overflow
- do not access memory
- do not use the FPU or paired singles
- do not end a block
- do not raise an architecturally modelled exception

Initial operation set:

- `addi`
- `ori`, `oris`
- `xori`, `xoris`
- `rlwinm` with `Rc=0`
- `and`, `andc`
- `or`, `orc`
- `xor`, `nor`
- `cntlzw` with `Rc=0`
- `extsb`, `extsh` with `Rc=0`
- `slw`, `srw` with `Rc=0`

The direct executor is test-local. It is not wired into Dolphin's production CPU-core selection or Cached Interpreter.

## Oracle

Each compact operation is encoded as a `UGeckoInstruction` and executed through the corresponding public Dolphin `Interpreter` semantic function against an independently initialized `PowerPCState`.

The compact executor runs the same sequence from the same initial state. Tests compare GPRs after every operation and the remaining relevant architectural state at the end of each trace.

## Cases

- explicit aliasing and edge cases
- signed immediate boundaries
- `addi` with `rA=0`
- wrapped rotate masks
- shift counts below and above 32
- deterministic randomized traces across multiple seeds
- encoding/name and `PPCTables` safety-property checks

No ROM, game executable, firmware, key, save, or proprietary-derived instruction trace is used.

## Pass condition

- All selected encodings resolve to the expected Dolphin instruction names.
- Every selected form has the pre-registered safe metadata properties.
- All fixed edge cases match.
- All randomized traces match after every operation.
- The test builds and passes on x86-64, Linux ARM64, and Apple ARM64 hosted runners.

## Falsifiers

- any architectural mismatch
- any selected encoding resolving to a different operation
- a selected form carrying a memory, FPU, block-ending, exception, carry, or overflow requirement
- setup dependence on a running game, MMU mapping, or runtime code generation

## Interpretation boundary

Passing proves only that this first compact semantic subset agrees with the current Dolphin Interpreter under the tested states. It does not prove:

- a performance increase
- correct block lowering
- correct exception-boundary placement
- a complete PowerPC backend
- a real-game or iPhone result
- a persistent-cache benefit

## AI disclosure

The experimental test design and implementation are AI-assisted and remain confined to the user's research fork. They are not intended for upstream submission under Dolphin's current generative-AI contribution policy.
