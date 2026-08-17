#pragma once

#include "state_ops.h"

#include <cstdint>
#include <span>

namespace CI3StateLab
{

std::uint64_t RunStateNoBoundary(std::span<const Op> trace, std::uint64_t iterations,
                                 CI3StateModel state);
std::uint64_t RunStateEveryOp(std::span<const Op> trace, std::uint64_t iterations,
                              CI3StateModel state);
std::uint64_t RunStateEvery4(std::span<const Op> trace, std::uint64_t iterations,
                             CI3StateModel state);
std::uint64_t RunStateEvery16(std::span<const Op> trace, std::uint64_t iterations,
                              CI3StateModel state);
std::uint64_t RunStatePerTrace(std::span<const Op> trace, std::uint64_t iterations,
                               CI3StateModel state);

std::uint64_t RunPinnedNoBoundary(std::span<const Op> trace, std::uint64_t iterations,
                                  CI3StateModel state);
std::uint64_t RunPinnedEveryOp(std::span<const Op> trace, std::uint64_t iterations,
                               CI3StateModel state);
std::uint64_t RunPinnedEvery4(std::span<const Op> trace, std::uint64_t iterations,
                              CI3StateModel state);
std::uint64_t RunPinnedEvery16(std::span<const Op> trace, std::uint64_t iterations,
                               CI3StateModel state);
std::uint64_t RunPinnedPerTrace(std::span<const Op> trace, std::uint64_t iterations,
                                CI3StateModel state);

}  // namespace CI3StateLab
