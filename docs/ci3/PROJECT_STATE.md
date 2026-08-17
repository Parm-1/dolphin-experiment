# CI3-PIR project state

Last updated: 2026-08-17 America/Toronto

## Current gate

**Gate 1 — Dispatch Lab validation in progress**

Gate 0 is complete: source pins, prior-art delta, legal/AI boundaries, project claims, risks, and benchmark protocol are recorded.

Gate 1 is not yet passed.

## Repository state

- Implementation repository: `Parm-1/dolphin-experiment`
- Default branch: `master`
- Fork base at bootstrap: `fa61f77fedb1f804851414a231509c55b8d8ed6c`
- Control-plane merge: `ea396c4e08257b2ad9aa699c68a56e3f9fcb8380`
- Active implementation PR: #2, `ci3/dispatch-lab-v1`

## Current capability

- Connected GitHub application: available with repository write/admin access.
- Local execution: standalone lab builds with GCC and Clang; full repository cloning is blocked by outbound DNS in the current runtime.
- GitHub Actions: Linux x64, Linux ARM64, and macOS ARM64 execution available.
- Apple hosted target: virtual Apple M1 runner verified.
- iPhone device testing: `BLOCKED_ENVIRONMENT` until a reproducible signing/device route exists.
- Commercial game fixtures: unknown and must remain local/uncommitted.

## Latest evidence

Experiment `EXP-20260817-001`, workflow run `32019158620`:

- all four jobs built and passed deterministic equivalence
- Linux ARM64 compact switch: approximately 2.22x the callback baseline
- virtual M1 compact switch: approximately 1.62x
- virtual M1 `preserve_none`/`musttail`: approximately 2.19x
- macOS measurements showed high variance
- computed goto was slower than switch on both ARM64 runners
- compiler behavior diverged sharply on x64

Evidence state: `OBSERVED`, synthetic only.

## Active hypothesis

H1/H2 hardening: compact direct dispatch and AppleClang musttail have enough synthetic ARM64 headroom to justify replication across multiple traces and explicit state-materialization models.

## Next workstream

Dispatch Lab v2:

- multiple seeds and trace lengths
- longer measurements and interleaved engine order
- controlled state materialization/flush-frequency variants
- generated assembly and executable text-size capture
- direct ID/switch semantics
- high- and low-branch-entropy operation mixes
- machine-readable speedup analysis

## Explicit blockers

- Device verification requires an external Apple build/signing/device path.
- No Dolphin, PowerPC, game, iPhone, or persistent-cache performance claim is proven.
- State-pinning performance remains unknown because v1 allowed compiler scalar promotion in the ordinary switch path.
