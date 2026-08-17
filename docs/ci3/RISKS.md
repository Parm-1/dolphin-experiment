# CI3-PIR risk register

| Risk | Likelihood | Impact | Current status | Mitigation / trigger |
|---|---:|---:|---|---|
| Duplicating iCube while claiming novelty | High | High | Active | Compare against pinned iCube; require delta and matched benchmarks. |
| AI-generated work conflicts with Dolphin upstream policy | High | High | Active | Keep experimental fork; disclose AI use; no ordinary upstream console-behavior PR. |
| Current runtime cannot clone or build the repo | Certain | Medium | Active | Use GitHub app for edits and GitHub Actions for builds/tests. |
| No Apple device/build path | High | High | BLOCKED_ENVIRONMENT | Use hosted macOS ARM64 for lab; device gate remains blocked. |
| Synthetic dispatch gains disappear in real Dolphin | Medium | High | Unknown | Use captured aggregate mixes, then Gate 2 real integration. |
| `preserve_none` ABI/compiler instability | Medium | Medium | Unknown | Keep same-IR computed-goto fallback; audit assembly on every compiler pin. |
| arm64e pointer authentication harms tail-threading | Medium | Medium | Unknown | Measure on Apple ARM64; do not assume. |
| Register flushing erases state-pinning gains | Medium | High | Unknown | Profile semantic boundaries; gate slot variants independently. |
| Handler specialization creates I-cache explosion | Medium | High | Unknown | Fixed text budget and code-size ablations. |
| Guarded memory paths violate MMU/store semantics | Medium | Critical | Unknown | Exact fallback, differential tests, separate store gate. |
| Stale direct block links | Medium | Critical | Unknown | Use block IDs and generation checks, never opaque callback patching. |
| Floating-point/paired-single mismatch | High | Critical | Unknown | Reference fallback, bitwise differential tests, delayed optimization. |
| Software vertex loader becomes dominant | Medium | High | Unknown | Measure subsystem time; open separate workstream only after evidence. |
| Persistent-cache parser becomes attack surface | Medium | High | Deferred | Bounds checks, hard limits, hashes, atomic writes, safe miss. |
| Phone thermal throttling invalidates short tests | High | High | Deferred | 15-minute sustained final protocol. |
| Overfitting to one title or synthetic trace | Medium | High | Active | Multiple seeds, mixes, homebrew, and titles; preserve null results. |
