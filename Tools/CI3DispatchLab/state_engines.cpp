#include "state_engines.h"

#include <cstddef>

#if defined(__GNUC__) || defined(__clang__)
#define CI3_NOINLINE __attribute__((noinline))
#else
#define CI3_NOINLINE
#endif

namespace CI3StateLab
{
namespace
{

template <std::size_t Interval>
CI3_NOINLINE std::uint64_t RunState(std::span<const Op> trace, std::uint64_t iterations,
                                    CI3StateModel state)
{
  std::size_t since_boundary = 0;
  for (std::uint64_t iteration = 0; iteration < iterations; ++iteration)
  {
    for (const Op& op : trace)
    {
      ApplyState(&state, op);
      if constexpr (Interval != 0)
      {
        if (++since_boundary == Interval)
        {
          CI3SemanticBoundary(&state);
          since_boundary = 0;
        }
      }
    }
    if constexpr (Interval == 0)
      CI3SemanticBoundary(&state);
  }
  if constexpr (Interval != 0)
  {
    if (since_boundary != 0)
      CI3SemanticBoundary(&state);
  }
  return Checksum(state);
}

template <std::size_t Interval>
CI3_NOINLINE std::uint64_t RunPinned(std::span<const Op> trace, std::uint64_t iterations,
                                     CI3StateModel state)
{
  std::uint64_t r0 = state.regs[0];
  std::uint64_t r1 = state.regs[1];
  std::uint64_t r2 = state.regs[2];
  std::uint64_t r3 = state.regs[3];
  std::size_t since_boundary = 0;

  const auto flush = [&] {
    state.regs[0] = r0;
    state.regs[1] = r1;
    state.regs[2] = r2;
    state.regs[3] = r3;
    CI3SemanticBoundary(&state);
    r0 = state.regs[0];
    r1 = state.regs[1];
    r2 = state.regs[2];
    r3 = state.regs[3];
  };

  for (std::uint64_t iteration = 0; iteration < iterations; ++iteration)
  {
    for (const Op& op : trace)
    {
      ApplyPinned(&r0, &r1, &r2, &r3, op);
      if constexpr (Interval != 0)
      {
        if (++since_boundary == Interval)
        {
          flush();
          since_boundary = 0;
        }
      }
    }
    if constexpr (Interval == 0)
      flush();
  }
  if constexpr (Interval != 0)
  {
    if (since_boundary != 0)
      flush();
  }
  return HashRegisters(r0, r1, r2, r3);
}

}  // namespace

CI3_NOINLINE std::uint64_t RunStateNoBoundary(std::span<const Op> trace,
                                              std::uint64_t iterations,
                                              CI3StateModel state)
{
  for (std::uint64_t iteration = 0; iteration < iterations; ++iteration)
  {
    for (const Op& op : trace)
      ApplyState(&state, op);
  }
  return Checksum(state);
}

std::uint64_t RunStateEveryOp(std::span<const Op> trace, std::uint64_t iterations,
                              CI3StateModel state)
{
  return RunState<1>(trace, iterations, state);
}

std::uint64_t RunStateEvery4(std::span<const Op> trace, std::uint64_t iterations,
                             CI3StateModel state)
{
  return RunState<4>(trace, iterations, state);
}

std::uint64_t RunStateEvery16(std::span<const Op> trace, std::uint64_t iterations,
                              CI3StateModel state)
{
  return RunState<16>(trace, iterations, state);
}

std::uint64_t RunStatePerTrace(std::span<const Op> trace, std::uint64_t iterations,
                               CI3StateModel state)
{
  return RunState<0>(trace, iterations, state);
}

CI3_NOINLINE std::uint64_t RunPinnedNoBoundary(std::span<const Op> trace,
                                               std::uint64_t iterations,
                                               CI3StateModel state)
{
  std::uint64_t r0 = state.regs[0];
  std::uint64_t r1 = state.regs[1];
  std::uint64_t r2 = state.regs[2];
  std::uint64_t r3 = state.regs[3];
  for (std::uint64_t iteration = 0; iteration < iterations; ++iteration)
  {
    for (const Op& op : trace)
      ApplyPinned(&r0, &r1, &r2, &r3, op);
  }
  return HashRegisters(r0, r1, r2, r3);
}

std::uint64_t RunPinnedEveryOp(std::span<const Op> trace, std::uint64_t iterations,
                               CI3StateModel state)
{
  return RunPinned<1>(trace, iterations, state);
}

std::uint64_t RunPinnedEvery4(std::span<const Op> trace, std::uint64_t iterations,
                              CI3StateModel state)
{
  return RunPinned<4>(trace, iterations, state);
}

std::uint64_t RunPinnedEvery16(std::span<const Op> trace, std::uint64_t iterations,
                               CI3StateModel state)
{
  return RunPinned<16>(trace, iterations, state);
}

std::uint64_t RunPinnedPerTrace(std::span<const Op> trace, std::uint64_t iterations,
                                CI3StateModel state)
{
  return RunPinned<0>(trace, iterations, state);
}

}  // namespace CI3StateLab
