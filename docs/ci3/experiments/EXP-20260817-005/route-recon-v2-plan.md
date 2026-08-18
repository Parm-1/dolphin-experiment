# EXP-20260817-005 route reconnaissance v2 protocol

Date: 2026-08-18 America/Toronto

## Prerequisite

PR #10 must be merged and workflow run `32110199577` must have completed successfully before this
experiment begins. The route workflow reads only the merged fixture-build qualification from
`master` and verifies every rebuilt candidate against its recorded SHA-256.

## Question

Can the current fork launch a preselected, source-classified set of open-source PowerPC hardware
fixtures through Dolphin's no-GUI Cached Interpreter route reproducibly enough to freeze a later
measurement set?

## Candidate set

The candidate set is fixed before any route output is observed and is drawn only from the 20
build-qualified outputs:

| Target | Workload class |
|---|---|
| `cputest_rlw` | `integer_control` |
| `cputest_cr` | `integer_control` |
| `cputest_load` | `memory_system` |
| `cputest_mtspr` | `memory_system` |
| `cputest_frsp` | `floating_paired` |
| `cputest_pairedmove` | `floating_paired` |
| `gxtest_bitfield` | `gpu_pipeline` |
| `gxtest_tev` | `gpu_pipeline` |

No candidate is selected using profiling, coverage, timing, or launch results.

## Route

Each candidate receives three fresh-process runs with:

- current PR head;
- no-GUI Dolphin;
- the explicit `headless` window platform;
- Null video backend;
- `Dolphin.Core.CPUCore=5`, matching `PowerPC::CPUCore::CachedInterpreter` in the pinned source;
- DSP HLE;
- profiling environment variable explicitly unset;
- natural exit or a fixed 12-second timeout.

The workflow records the exact command contract and whether a Cached Interpreter marker appeared in
available logs. Marker absence is reported rather than silently converted into proof that another
core ran.

## Route-contract corrections before the valid run

Two early workflow attempts were rejected as route-contract defects rather than interpreted as
emulator results:

1. run `32117017451` used the unsupported no-GUI `-b` option and failed before emulation;
2. run `32119465079` omitted `-p headless`, causing Linux to select `fbdev` and fail to open
   `/dev/fb0` before emulation.

A subsequent source audit also corrected the inherited CPU-core value from `2` to `5` before any run
could be accepted as Cached Interpreter evidence. Candidate selection, hashes, repetition count,
timeout, normalization, and pass thresholds were not changed.

## Stability rule

A candidate is a `ROUTE_CANDIDATE` only when all three runs:

- have the same exit status and timeout state;
- produce the same normalized route-signature hash;
- produce non-empty output;
- contain no panic, assertion, fatal-error, or segmentation-fault marker;
- exit naturally or under the fixed timeout/termination codes;
- produce no CI3 profile file while profiling is disabled.

Route signatures retain ordered route-relevant lines while normalizing paths, timestamps, process
and thread identifiers, elapsed values, and host pointer-like hexadecimal addresses. The full
normalized-output hash is also recorded but is not the stability criterion.

## Pass condition

The route-reconnaissance gate passes if at least four candidates qualify and the qualified set spans
at least three workload classes.

A pass authorizes only a separate docs-only fixture-freeze step. It does not establish instruction
coverage, profiling overhead, architectural correctness of each hardware test, a CPU speedup, a
playable game, an iPhone result, or Gate 2 completion.

## Failure and blocker handling

- Build, route, or publication failures preserve expiring diagnostic artifacts.
- A selected fixture hash mismatch is a hard failure.
- Inability to build the no-GUI route on the hosted runner is classified separately from route
  instability.
- No failing check may be bypassed to merge the evidence.

## Data boundary

Committed output may contain only source/toolchain pins, relative open-source fixture paths and
hashes, aggregate run statuses, normalized hashes, marker booleans, and the bounded verdict.

Raw logs, user directories, fixture binaries, absolute paths, instruction words, guest addresses,
disassembly, title identifiers, saves, firmware, keys, and proprietary content are not committed.

## AI disclosure

The protocol and workflow are substantially AI-assisted and remain confined to the user's research
fork. They are not intended as an upstream Dolphin console-behavior contribution under the current
generative-AI policy.
