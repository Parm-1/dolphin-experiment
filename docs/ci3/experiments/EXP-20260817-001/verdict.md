# EXP-20260817-001 verdict

## Verdict

**PROMISING; REPLICATE AND HARDEN**

The initial falsifier did not trigger. Compact direct dispatch exceeded the 20% promise threshold on both ARM64 runners:

- Linux ARM64 compact switch: approximately 2.22x the callback baseline.
- virtual M1 compact switch: approximately 1.62x.
- virtual M1 `preserve_none`/`musttail`: approximately 2.19x.

All compared engines produced the same deterministic final checksum.

## Claims promoted

- Compact direct dispatch has material synthetic ARM64 promise: `OBSERVED`.
- `preserve_none`/`musttail` has material synthetic Apple ARM64 promise: `OBSERVED`, with high variance.
- Dispatch strategy is compiler- and architecture-sensitive: `OBSERVED`.

## Claims not promoted

- Explicit block-selected state pinning remains `UNKNOWN`; the compiler could already promote the ordinary switch state.
- Gate 1 is not passed.
- No Dolphin, PowerPC, real-game, iPhone, or persistent-cache performance claim is supported.

## Required follow-up

1. Run multiple seeds and trace lengths with longer timings.
2. Interleave or randomize engine measurement order.
3. Add controlled state-materialization and flush-frequency variants.
4. Capture generated assembly and binary text size.
5. Make ID/switch semantics directly comparable without temporary-record artifacts.
6. Add operation mixes that vary branch entropy and state dependencies.
7. Re-run on Linux ARM64 and virtual M1 before choosing a Dolphin executor.
