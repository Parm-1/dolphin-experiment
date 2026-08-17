# EXP-20260817-003 verdict

## Verdict

**SCOPED PASS — THE FIRST POWERPC SEMANTIC SUBSET AGREES WITH THE REFERENCE
INTERPRETER; GATE 2 REMAINS OPEN**

At tested head `24d3b521e6139e02b536cd415b4afd9a16044cf9`, workflow run
`32070900486` passed on all three hosted targets:

- Linux x86-64 with GCC 13.3.0
- Linux ARM64 with Clang 18.1.3 and libc++ 18
- virtual Apple M1 with AppleClang 17.0.0

All targets built Dolphin's full unit-test executable and passed the three
`CI3PowerPCIntegerDifferential` tests.

## Evidence

The test-local executor uses an eight-byte pointer-free operation record for 17 selected
register-only integer forms.

The preserved workload contains:

- one encoding/name/metadata check for every selected operation form;
- an 18-operation fixed edge-case trace;
- 12 deterministic seeds with 512 operations each;
- 6,144 randomized differential operations in total.

For each operation, the compact executor and the public Dolphin `Interpreter` semantic function
begin from matched state. General-purpose registers are compared after every operation.
Randomized traces also compare CR, XER, and pending exceptions after every operation, and the
broader architectural state is compared at trace completion.

No ROM, game executable, firmware, key, save, proprietary instruction trace, or runtime-generated
host code is used.

## Failures that improved the experiment

The successful run followed two useful failures:

1. Run `32059256892` showed that the test incorrectly treated the low instruction bit as an `Rc`
   field for immediate-form encodings. Fixed and randomized semantics already matched, but the
   metadata test correctly failed. The assertion was narrowed to forms that actually contain a
   record bit.
2. Run `32059823903` passed on Linux x86-64 and macOS ARM64, but Linux ARM64 failed while compiling
   unrelated DiscIO code because the default Clang/libstdc++ pairing did not provide
   `std::expected`. The ARM64 job now pins Clang 18 with libc++ 18 and runs a fast C++23
   standard-library preflight before configuring Dolphin.

These were test-definition and CI-toolchain problems, not evidence of a compact/reference semantic
mismatch.

## Claims promoted

- A test-local eight-byte CI3 operation format can reproduce current Dolphin Interpreter results
  for the selected 17 register-only integer forms under the tested states:
  `PROVEN_RUNTIME (differential, scoped)`.
- The selected encodings resolve to the intended Dolphin operation names and satisfy the
  pre-registered metadata exclusions on the tested source pin:
  `PROVEN_RUNTIME (differential, scoped)`.
- The minimum semantic-feasibility subtask needed before runtime integration is complete for this
  subset.

## Claims not promoted

- No selectable CI3 CPU backend exists.
- No block lowering, dispatch, exception-boundary placement, memory behavior, floating-point
  behavior, or persistent-cache behavior has been validated.
- No performance improvement has been measured.
- Gate 2 has not passed: the charter still requires representative CPU-microbenchmark and
  real-workload speedups with no unexplained differential failures.
- No game, iPhone, thermal, or strict no-codegen result is established.

## Next experiment

Proceed to aggregate-only workload characterization before implementing a broad backend.

The next instrumentation should consume Dolphin's already analyzed `CodeBlock`/`CodeOp` data and
record only aggregate statistics:

- block-length distribution;
- opcode frequencies;
- fraction and run lengths covered by the current 17-operation subset;
- GPR read/write and short-range reuse distributions;
- semantic-boundary categories that force state materialization;
- generic fallback rates.

It must not persist guest instruction words, addresses, disassembly, or proprietary-derived traces.
The result should select the smallest serious lowering/integration experiment and provide the
denominators needed for the first controlled performance test.
