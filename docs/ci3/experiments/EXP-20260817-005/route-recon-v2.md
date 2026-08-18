# EXP-20260817-005 route reconnaissance v2

**Verdict: PASS**

- Tested Dolphin commit: `01faa904e1caff3195b2d8185416c9d8f43479b1`
- GitHub Actions run: `32124068535`
- Qualified candidates: 8 / 8
- Qualified workload classes: `['floating_paired', 'gpu_pipeline', 'integer_control', 'memory_system']`
- Profiling environment variable: unset
- Profile output expected: no

| Candidate | Class | Verdict | Stable signature | Exit statuses | Cached marker in all runs |
|---|---|---|---:|---|---:|
| `cputest_rlw` | `integer_control` | `ROUTE_CANDIDATE` | true | `[-15]` | false |
| `cputest_cr` | `integer_control` | `ROUTE_CANDIDATE` | true | `[-15]` | false |
| `cputest_load` | `memory_system` | `ROUTE_CANDIDATE` | true | `[-15]` | false |
| `cputest_mtspr` | `memory_system` | `ROUTE_CANDIDATE` | true | `[-15]` | false |
| `cputest_frsp` | `floating_paired` | `ROUTE_CANDIDATE` | true | `[-15]` | false |
| `cputest_pairedmove` | `floating_paired` | `ROUTE_CANDIDATE` | true | `[-15]` | false |
| `gxtest_bitfield` | `gpu_pipeline` | `ROUTE_CANDIDATE` | true | `[-15]` | false |
| `gxtest_tev` | `gpu_pipeline` | `ROUTE_CANDIDATE` | true | `[-15]` | false |

## Interpretation boundary

- A pass authorizes only a separate fixture-freeze step.
- It is not instruction coverage, profiling overhead, architectural correctness, lowering,
  performance, game, iPhone, thermal, or Gate 2 evidence.
- Raw logs, user directories, and rebuilt binaries are not part of the durable result.
