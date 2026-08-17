# CI3-PIR prior-art delta

## Mainline Dolphin Cached Interpreter

Already provides:

- analyzed guest blocks
- non-executable cached callback records
- block invalidation through Dolphin's common block cache
- software profiling support
- exact interpreter-function reuse
- speculative devirtualization of the dominant wrapper callback

Remaining structural issue under investigation:

- ordinary instructions still commonly reach an instruction-specific function pointer and repeatedly materialize architectural state.

## iCube

Already experiments with:

- callback IDs and mixed ID/pointer records
- direct switch dispatch
- computed-goto micro-operations
- common integer and branch fast paths
- guarded MEM1/MEM2 access
- paired-single NEON paths
- opcode profiling
- experimental callback-record block patching/linking

CI3 must not claim these mechanisms individually as novel.

Likely remaining delta:

- fully pointer-free portable IR
- compact variable-length operation storage rather than fixed maximum payloads
- same-IR dispatch comparisons
- block-selected host-register state pinning
- generation-safe reversible block IDs/links
- controlled matched benchmark evidence
- portable persistent IR/profile cache rather than native code

## Podish

Demonstrates that a no-JIT interpreter can combine:

- predecoded operations
- fixed-signature `preserve_none` handlers
- `musttail` dispatch
- micro-TLB state carried between handlers
- block linking
- lazy state
- profile-selected superoperations

Delta for CI3:

- high-fidelity full-system PowerPC console semantics
- Dolphin MMU, exceptions, timing, paired singles, and invalidation
- arm64e and real-game evidence

## PPSSPP

Demonstrates:

- interpreter-specific IR
- dense dispatch
- fused and specialized operations
- compiler-guided switch improvements
- attention to vector code generation and I-cache tradeoffs

Delta for CI3:

- PowerPC/Dolphin integration
- block-selected state pinning
- strict no-codegen GameCube product evidence

## Ryujinx PTC

Demonstrates persistent profiled translation caching with:

- guest-code hashes
- host feature and architecture validation
- native generated code
- relocations
- unwind information
- persisted compilation-tier state

CI3 distinction:

- persist portable non-executable interpreter IR and optimization decisions, not host-native code.

## Defensible research contribution

A compact, portable, state-pinned PowerPC interpreter for a high-fidelity full-system console emulator, with guarded memory specialization, generation-safe superblock execution, and persistent profile-guided optimization on Apple ARM64 without application-generated host CPU code.
