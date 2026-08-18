# EXP-20260817-005 analysis plan v1

**State: frozen before measured execution**

This plan operationalizes the thresholds preregistered in `hypothesis.md`. The analyzer and runner
covered by this plan must be merged before the measurement trigger is created.

## Inputs

The measurement runner consumes only:

- the merged frozen `fixture-manifest.json`;
- the merged `run-order-v1.json`;
- exact locally rebuilt fixture binaries matching their frozen SHA-256 hashes;
- a no-GUI Dolphin build from the exact commit used by route reconnaissance;
- per-run wall and child-process CPU times;
- normalized route hashes and aggregate schema-v1 treatment profiles.

Raw stdout/stderr, Dolphin user directories, built fixture binaries, and absolute paths are deleted
and are not analysis inputs.

## Route equivalence

Every measured pair must contain exactly one baseline and one treatment run for the same fixture and
`pair_id`. A pair is route-equivalent only when:

- exit status matches between conditions;
- normalized output SHA-256 matches between conditions;
- both runs match the frozen fixture route invariant;
- neither run contains a panic/crash marker;
- the treatment profile exists and passes aggregate-schema validation.

Any failed pair makes the distortion gate `FAIL_ROUTE_DIVERGENCE`. Coverage may still be summarized
for diagnosis, but it cannot authorize lowering.

## Timing estimator

For each pair:

`overhead = treatment_wall_ns / baseline_wall_ns - 1`

For each fixture, compute the median of its eight paired overheads. The overall point estimate is the
median of the fixture-specific medians, preventing a short or prolific fixture from dominating.

The confidence interval is a stratified paired bootstrap:

- deterministic PRNG seed: `0xC13C0005`;
- resamples: 50,000;
- resample paired overheads with replacement separately within every fixture;
- compute the median within each resampled fixture;
- compute the median across fixture medians;
- report the interpolated 2.5th and 97.5th percentiles.

Child-process CPU overhead is calculated identically when nonzero CPU time is available, but wall
time controls the preregistered distortion gate.

## Distortion gate

- `PASS`: route equivalence holds, overall median wall overhead is at most 3%, bootstrap upper bound
  is at most 5%, and no fixture median exceeds 10%.
- `INCONCLUSIVE_NOISY_INTERVAL`: point and fixture medians pass, but the bootstrap upper bound
  exceeds 5%.
- `FAIL_OVERHEAD`: overall median exceeds 3% or a fixture median exceeds 10%.
- `FAIL_ROUTE_DIVERGENCE`: any measured pair fails route equivalence.

An inconclusive or failed distortion gate blocks a lowering decision.

## Coverage extraction

The runner converts schema-v1 JSON into integer aggregate maps without a floating-point round trip.
It rejects prohibited raw-guest-data fields. For every fixture, derive:

- supported eligible-operation fraction;
- fully supported nonempty eligible-block fraction;
- supported-run median, p75, p90, and maximum from the histogram;
- semantic-feature rates divided by eligible operations;
- dominant semantic-feature rate;
- GPR reuse-distance and future-live-pressure aggregates.

An individual fixture meets the proceed band when:

- supported operation fraction is at least 30%;
- supported-run median is at least 2;
- supported-run p75 is at least 4, or fully supported nonempty blocks are at least 10%;
- the dominant semantic-feature rate is below 50%.

## Workload-class estimator

For each workload class, take the median of each fixture metric within that class. A class meets the
proceed band by applying the same thresholds to those class medians. At least two workload classes
must pass.

## Final decision

1. `DO_NOT_PROCEED_MEASUREMENT_DISTORTION` if the distortion gate is not `PASS`.
2. `PROCEED_TO_MINIMUM_LOWERING_EXPERIMENT` if the distortion gate passes and at least two workload
   classes meet the proceed band.
3. `STOP_OR_REDIRECT_CURRENT_BACKEND` if most fixtures have less than 15% supported operations or
   supported-run medians no greater than 1.
4. `EXPAND_OR_REVISE_SUBSET_BEFORE_LOWERING` otherwise.

The decision permits or blocks only the smallest controlled lowering experiment. It is not a
performance result.

## Reproducibility

The committed analyzer has synthetic known-answer tests for histogram quantiles, deterministic
bootstrap behavior, passing coverage, high overhead, weak coverage, and route divergence. The
runner has tests for normalization, aggregate integer extraction, and prohibited-field rejection.

Changing the seed, resample count, pairing, estimators, thresholds, route normalization, or profile
extraction after measured execution begins requires a new analysis-plan version and invalidates
unblinded EXP-005 results.
