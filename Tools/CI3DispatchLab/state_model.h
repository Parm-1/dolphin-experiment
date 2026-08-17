#pragma once

#include <cstdint>

struct CI3StateModel
{
  std::uint64_t regs[4]{};
};

extern "C" void CI3SemanticBoundary(CI3StateModel* state) noexcept;
