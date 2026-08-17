# CI3-PIR source lock

Pinned on 2026-08-17 America/Toronto.

These repositories are comparative and research inputs. A pin does not authorize copying code. Reuse requires file-level license and attribution review.

| Role | Repository | Ref | Commit | Expected license/use |
|---|---|---|---|---|
| Implementation and semantic oracle | `Parm-1/dolphin-experiment` | `master` | `fa61f77fedb1f804851414a231509c55b8d8ed6c` | Dolphin GPL-2.0-or-later; experimental fork. |
| Upstream reference | `dolphin-emu/dolphin` | `master` | `fa61f77fedb1f804851414a231509c55b8d8ed6c` | GPL-2.0-or-later. |
| Optimized JITless comparison | `Provenance-Emu/iCube` | `feature/icube-testflight` | `832810306a1463f63d529834e5239bfe8124b21b` | Dolphin-derived; verify file-level GPL headers before reuse. Reference first. |
| Tail-threaded interpreter prior art | `meokit/podish` | `main` | `3149a4ba2d4c05a16ecf0a8aec9989c1ff7fb1bf` | Repository states GPLv3/commercial dual licensing. Reference only unless reviewed. |
| Compact IR interpreter prior art | `hrydgard/ppsspp` | `master` | `ae76fec2d5025037041279e14964fe77a6db0ef0` | GPL-2.0-or-later. Reference first. |
| Persistent translation cache prior art | `jamesoram/Ryujinx` | `master` | `7d158acc3b5826a08941d6e8d50d3a3897021bcd` | Verify repository/file license before reuse. Reference only. |

## Required source areas

### Dolphin

- `Source/Core/Core/PowerPC/CachedInterpreter/`
- `Source/Core/Core/PowerPC/Interpreter/`
- `Source/Core/Core/PowerPC/PPCAnalyst.*`
- `Source/Core/Core/PowerPC/JitCommon/`
- `Source/Core/Core/PowerPC/JitArm64/`
- `Source/Core/Core/PowerPC/MMU.*`
- `Source/Core/VideoCommon/VertexLoader*`
- relevant unit tests

### iCube

- `CachedInterpreter.cpp/.h`
- `CachedInterpreterEmitter.*`
- `CachedInterpreterBlockCache.*`
- Fast FP, VBI Skip, CPU clock, renderer, and vertex-loader configuration

### Podish

- `libfibercpu/src/dispatch.h`
- `libfibercpu/src/decoder.h`
- `libfibercpu/src/superopcodes.*`
- `docs/superopcode-design.md`

### PPSSPP

- `Core/MIPS/IR/IRInterpreter.cpp`
- IR operation/lowering files
- issue 19143 and merged follow-ups

### Ryujinx

- `ARMeilleure/Translation/PTC/Ptc.cs`
- `ARMeilleure/Translation/PTC/PtcProfiler.cs`

## Re-pinning rule

Update this file only in a dedicated source-sync change. Record why the new pin is needed and rerun any source-dependent claim audit.
