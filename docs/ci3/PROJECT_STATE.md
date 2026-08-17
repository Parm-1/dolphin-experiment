# CI3-PIR project state

Last updated: 2026-08-17 America/Toronto

## Current gate

**Gate 0 — source and benchmark bootstrap**

## Repository state

- Implementation repository: `Parm-1/dolphin-experiment`
- Default branch: `master`
- Fork base: `fa61f77fedb1f804851414a231509c55b8d8ed6c`
- Fork matches `dolphin-emu/dolphin` at the recorded base.
- Open project PRs at bootstrap: none.
- Open project issues at bootstrap: none.

## Current capability

- Connected GitHub application: available with repository write/admin access.
- Local execution environment: cannot resolve GitHub, so it cannot clone the repository or run repository builds directly.
- GitHub Actions: not yet configured in this fork.
- Apple Silicon target testing: not yet established.
- iPhone device testing: `BLOCKED_ENVIRONMENT` until a reproducible build and device route exists.
- Commercial game fixtures: unknown and must remain local/uncommitted.

## Active hypothesis

H1/H2 bootstrap: a standalone generic dispatch laboratory can determine whether compact records, direct dispatch, and state pinning justify a full Dolphin backend.

## Active workstream

Create and validate `Tools/CI3DispatchLab` with:

- CI2-like two-level callback dispatch.
- One-level callback dispatch.
- ID/switch dispatch.
- Compact switch dispatch.
- Compact computed-goto dispatch where supported.
- Pinned-state execution.
- Clang `preserve_none`/`musttail` execution where supported.
- Record-size reporting and deterministic equivalence checks.
- Linux x64, Linux ARM64, and macOS ARM64 CI.

## Next decision

After the dispatch lab produces controlled results:

- Continue to a minimum Dolphin backend if the compact/state-pinned topology is materially better.
- Redesign or stop the architecture if gains are small or synthetic-only.

## Explicit blockers

- Direct local cloning/building is unavailable in the current ChatGPT runtime because outbound DNS to GitHub is blocked.
- Device verification requires an external Apple build/signing/device path.
- No runtime performance claim is currently proven.
