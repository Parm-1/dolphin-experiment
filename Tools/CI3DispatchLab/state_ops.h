#pragma once

#include "state_model.h"

#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <stdexcept>
#include <vector>

namespace CI3StateLab
{

enum class OpCode : std::uint8_t
{
  Add0Immediate = 0,
  Xor1With0,
  Rotate2With1,
  Add3With2,
  Mix0With3,
  Multiply1Immediate,
  Select2,
  SwapMix0And2,
  Count,
};

struct Op
{
  OpCode opcode{};
  std::uint8_t reserved[3]{};
  std::uint32_t immediate = 0;
};
static_assert(sizeof(Op) == 8);

inline std::uint64_t NextRandom(std::uint64_t* state)
{
  std::uint64_t value = *state;
  value ^= value >> 12;
  value ^= value << 25;
  value ^= value >> 27;
  *state = value;
  return value * 0x2545F4914F6CDD1DULL;
}

inline CI3StateModel MakeInitialState(std::uint64_t seed)
{
  CI3StateModel state{};
  std::uint64_t random = seed ^ 0x9E3779B97F4A7C15ULL;
  for (std::uint64_t& reg : state.regs)
    reg = NextRandom(&random);
  return state;
}

inline std::vector<Op> MakeTrace(std::size_t length, std::uint64_t seed)
{
  if (length == 0)
    throw std::invalid_argument("trace length must be greater than zero");

  std::vector<Op> trace;
  trace.reserve(length);
  std::uint64_t random = seed;
  constexpr auto op_count = static_cast<std::uint8_t>(OpCode::Count);

  for (std::size_t i = 0; i < length; ++i)
  {
    const std::uint64_t value = NextRandom(&random);
    trace.push_back({static_cast<OpCode>(value % op_count), {},
                     static_cast<std::uint32_t>((value >> 16) | 1U)});
  }
  return trace;
}

inline std::uint64_t HashRegisters(std::uint64_t r0, std::uint64_t r1, std::uint64_t r2,
                                   std::uint64_t r3)
{
  std::uint64_t hash = 0x243F6A8885A308D3ULL;
  for (const std::uint64_t value : std::array<std::uint64_t, 4>{r0, r1, r2, r3})
  {
    hash ^= value + 0x9E3779B97F4A7C15ULL + (hash << 6) + (hash >> 2);
    hash = std::rotl(hash, 17);
  }
  return hash;
}

inline std::uint64_t Checksum(const CI3StateModel& state)
{
  return HashRegisters(state.regs[0], state.regs[1], state.regs[2], state.regs[3]);
}

inline void ApplyState(CI3StateModel* state, const Op& op)
{
  switch (op.opcode)
  {
  case OpCode::Add0Immediate:
    state->regs[0] += op.immediate;
    break;
  case OpCode::Xor1With0:
    state->regs[1] ^= state->regs[0] + op.immediate;
    break;
  case OpCode::Rotate2With1:
    state->regs[2] = std::rotl(state->regs[2] ^ state->regs[1], op.immediate & 63U);
    break;
  case OpCode::Add3With2:
    state->regs[3] += state->regs[2] ^ op.immediate;
    break;
  case OpCode::Mix0With3:
    state->regs[0] = std::rotl(state->regs[0] + state->regs[3], 17) ^ op.immediate;
    break;
  case OpCode::Multiply1Immediate:
    state->regs[1] *= static_cast<std::uint64_t>(op.immediate | 1U);
    break;
  case OpCode::Select2:
    state->regs[2] ^= state->regs[0] < state->regs[1] ? state->regs[3] : state->regs[0];
    break;
  case OpCode::SwapMix0And2:
  {
    const std::uint64_t old_r0 = state->regs[0];
    state->regs[0] = state->regs[2] ^ op.immediate;
    state->regs[2] = old_r0 + state->regs[1];
    break;
  }
  case OpCode::Count:
    std::abort();
  }
}

inline void ApplyPinned(std::uint64_t* r0, std::uint64_t* r1, std::uint64_t* r2,
                        std::uint64_t* r3, const Op& op)
{
  switch (op.opcode)
  {
  case OpCode::Add0Immediate:
    *r0 += op.immediate;
    break;
  case OpCode::Xor1With0:
    *r1 ^= *r0 + op.immediate;
    break;
  case OpCode::Rotate2With1:
    *r2 = std::rotl(*r2 ^ *r1, op.immediate & 63U);
    break;
  case OpCode::Add3With2:
    *r3 += *r2 ^ op.immediate;
    break;
  case OpCode::Mix0With3:
    *r0 = std::rotl(*r0 + *r3, 17) ^ op.immediate;
    break;
  case OpCode::Multiply1Immediate:
    *r1 *= static_cast<std::uint64_t>(op.immediate | 1U);
    break;
  case OpCode::Select2:
    *r2 ^= *r0 < *r1 ? *r3 : *r0;
    break;
  case OpCode::SwapMix0And2:
  {
    const std::uint64_t old_r0 = *r0;
    *r0 = *r2 ^ op.immediate;
    *r2 = old_r0 + *r1;
    break;
  }
  case OpCode::Count:
    std::abort();
  }
}

}  // namespace CI3StateLab
