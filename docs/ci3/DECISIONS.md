# CI3-PIR decisions

## D-001 — Use the Dolphin fork as implementation repository

Date: 2026-08-17

Decision: keep implementation and project-control records in `Parm-1/dolphin-experiment` under `docs/ci3/`.

Rationale:

- Preserves Dolphin history and upstream tracking.
- Keeps source pins and implementation changes reviewable together.
- Avoids an empty repository that would duplicate build and provenance work.

Reversible: yes. Control records can move to a separate repository later if they become noisy.

## D-002 — Dispatch Lab before Dolphin backend

Date: 2026-08-17

Decision: build a generic standalone dispatch/state laboratory before modifying PowerPC execution.

Rationale:

- Cheaply tests the central topology.
- Avoids duplicating iCube without evidence.
- Separates dispatch, representation density, and state pinning from MMU and console semantics.
- Complies with the need to keep early AI-assisted work away from emulated-console behavior.

Reversible: yes.

## D-003 — Persistence deferred

Date: 2026-08-17

Decision: do not implement a disk cache before Gate 2.

Rationale: persistence can improve warm-up while concealing a weak steady-state executor.

Reversible: yes.

## D-004 — No upstream AI-authored console-behavior PRs

Date: 2026-08-17

Decision: CI3 console-behavior work remains in the experimental fork unless Dolphin's policy is independently satisfied.

Rationale: `Contributing.md` explicitly restricts LLM use for emulated-console behavior and requires AI disclosure.

Reversible: only through a policy-compliant human-led process.

## D-005 — Pair Linux ARM64 Clang 18 with libc++ 18 in CI

Date: 2026-08-17

Decision: the Linux ARM64 differential-test job uses `clang++-18 -stdlib=libc++` with
`libc++-18-dev` and `libc++abi-18-dev`, and runs a small `std::expected` preflight before the full
Dolphin build.

Rationale:

- Run `32059823903` reached unrelated DiscIO code before failing because the runner's default
  Clang/libstdc++ pairing did not provide the required C++23 `std::expected` implementation.
- The explicit pairing makes the compiler and standard library reproducible.
- The preflight converts a late full-build failure into a fast, local diagnostic.

Reversible: yes. Remove the override after the default ARM64 runner toolchain provides the required
C++23 library surface and a controlled rerun passes.
