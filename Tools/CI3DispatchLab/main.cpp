#include <algorithm>
#include <array>
#include <bit>
#include <charconv>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#ifndef __has_attribute
#define __has_attribute(x) 0
#endif

#ifndef __has_cpp_attribute
#define __has_cpp_attribute(x) 0
#endif

#if defined(__GNUC__) || defined(__clang__)
#define CI3_NOINLINE __attribute__((noinline))
#else
#define CI3_NOINLINE
#endif

#if defined(__clang__) && __has_attribute(preserve_none) && __has_cpp_attribute(clang::musttail)
#define CI3_HAS_MUSTTAIL 1
#define CI3_PRESERVE_NONE __attribute__((preserve_none))
#else
#define CI3_HAS_MUSTTAIL 0
#define CI3_PRESERVE_NONE
#endif

namespace
{

volatile std::uint64_t g_sink = 0;

struct Options
{
  std::uint64_t iterations = 10000;
  std::size_t repetitions = 5;
  std::size_t trace_length = 256;
  std::uint64_t seed = 0xC13C0FFEE1234567ULL;
  bool verify_only = false;
};

struct MachineState
{
  std::array<std::uint64_t, 4> regs{};
};

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

struct CompactOp8
{
  OpCode opcode{};
  std::uint8_t dst = 0;
  std::uint8_t src_a = 0;
  std::uint8_t src_b = 0;
  std::uint32_t immediate = 0;
};
static_assert(sizeof(CompactOp8) == 8);

struct CompactOp12
{
  CompactOp8 op{};
  std::uint32_t metadata = 0;
};
static_assert(sizeof(CompactOp12) == 12);

struct alignas(16) CompactOp16
{
  CompactOp8 op{};
  std::uint64_t metadata = 0;
};
static_assert(sizeof(CompactOp16) == 16);

struct alignas(16) IdOp16
{
  std::uint16_t id = 0;
  std::uint16_t reserved = 0;
  std::uint32_t immediate = 0;
  std::uint64_t metadata = 0;
};
static_assert(sizeof(IdOp16) == 16);

std::uint64_t NextRandom(std::uint64_t* state)
{
  std::uint64_t value = *state;
  value ^= value >> 12;
  value ^= value << 25;
  value ^= value >> 27;
  *state = value;
  return value * 0x2545F4914F6CDD1DULL;
}

MachineState MakeInitialState(std::uint64_t seed)
{
  MachineState state{};
  std::uint64_t random = seed ^ 0x9E3779B97F4A7C15ULL;
  for (std::uint64_t& reg : state.regs)
    reg = NextRandom(&random);
  return state;
}

std::vector<CompactOp8> MakeTrace(std::size_t length, std::uint64_t seed)
{
  if (length == 0)
    throw std::invalid_argument("trace length must be greater than zero");

  std::vector<CompactOp8> trace;
  trace.reserve(length);
  std::uint64_t random = seed;
  constexpr std::uint8_t op_count = static_cast<std::uint8_t>(OpCode::Count);

  for (std::size_t i = 0; i < length; ++i)
  {
    const std::uint64_t value = NextRandom(&random);
    CompactOp8 op{};
    op.opcode = static_cast<OpCode>(value % op_count);
    op.dst = static_cast<std::uint8_t>((value >> 8) & 3);
    op.src_a = static_cast<std::uint8_t>((value >> 10) & 3);
    op.src_b = static_cast<std::uint8_t>((value >> 12) & 3);
    op.immediate = static_cast<std::uint32_t>((value >> 16) | 1U);
    trace.emplace_back(op);
  }

  return trace;
}

std::uint64_t HashRegisters(std::uint64_t r0, std::uint64_t r1, std::uint64_t r2,
                            std::uint64_t r3)
{
  std::uint64_t hash = 0x243F6A8885A308D3ULL;
  const std::array<std::uint64_t, 4> values{r0, r1, r2, r3};
  for (std::uint64_t value : values)
  {
    hash ^= value + 0x9E3779B97F4A7C15ULL + (hash << 6) + (hash >> 2);
    hash = std::rotl(hash, 17);
  }
  return hash;
}

std::uint64_t Checksum(const MachineState& state)
{
  return HashRegisters(state.regs[0], state.regs[1], state.regs[2], state.regs[3]);
}

inline void ApplyOp(MachineState* state, const CompactOp8& op)
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

inline void ApplyPinnedOp(std::uint64_t* r0, std::uint64_t* r1, std::uint64_t* r2,
                          std::uint64_t* r3, const CompactOp8& op)
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

using InnerCallback = void (*)(MachineState*, std::uint32_t);
struct TwoLevelCallbackRecord;
using OuterCallback = void (*)(MachineState*, const TwoLevelCallbackRecord&);

struct TwoLevelCallbackRecord
{
  OuterCallback outer = nullptr;
  InnerCallback inner = nullptr;
  std::uint32_t immediate = 0;
  std::uint32_t reserved = 0;
};

struct OneLevelCallbackRecord
{
  InnerCallback callback = nullptr;
  std::uint32_t immediate = 0;
  std::uint32_t reserved = 0;
};

CI3_NOINLINE void CallbackAdd0(MachineState* state, std::uint32_t immediate)
{
  state->regs[0] += immediate;
}

CI3_NOINLINE void CallbackXor1With0(MachineState* state, std::uint32_t immediate)
{
  state->regs[1] ^= state->regs[0] + immediate;
}

CI3_NOINLINE void CallbackRotate2With1(MachineState* state, std::uint32_t immediate)
{
  state->regs[2] = std::rotl(state->regs[2] ^ state->regs[1], immediate & 63U);
}

CI3_NOINLINE void CallbackAdd3With2(MachineState* state, std::uint32_t immediate)
{
  state->regs[3] += state->regs[2] ^ immediate;
}

CI3_NOINLINE void CallbackMix0With3(MachineState* state, std::uint32_t immediate)
{
  state->regs[0] = std::rotl(state->regs[0] + state->regs[3], 17) ^ immediate;
}

CI3_NOINLINE void CallbackMultiply1Immediate(MachineState* state, std::uint32_t immediate)
{
  state->regs[1] *= static_cast<std::uint64_t>(immediate | 1U);
}

CI3_NOINLINE void CallbackSelect2(MachineState* state, std::uint32_t)
{
  state->regs[2] ^= state->regs[0] < state->regs[1] ? state->regs[3] : state->regs[0];
}

CI3_NOINLINE void CallbackSwapMix0And2(MachineState* state, std::uint32_t immediate)
{
  const std::uint64_t old_r0 = state->regs[0];
  state->regs[0] = state->regs[2] ^ immediate;
  state->regs[2] = old_r0 + state->regs[1];
}

CI3_NOINLINE void OuterInterpret(MachineState* state, const TwoLevelCallbackRecord& record)
{
  record.inner(state, record.immediate);
}

InnerCallback GetInnerCallback(OpCode opcode)
{
  switch (opcode)
  {
  case OpCode::Add0Immediate:
    return CallbackAdd0;
  case OpCode::Xor1With0:
    return CallbackXor1With0;
  case OpCode::Rotate2With1:
    return CallbackRotate2With1;
  case OpCode::Add3With2:
    return CallbackAdd3With2;
  case OpCode::Mix0With3:
    return CallbackMix0With3;
  case OpCode::Multiply1Immediate:
    return CallbackMultiply1Immediate;
  case OpCode::Select2:
    return CallbackSelect2;
  case OpCode::SwapMix0And2:
    return CallbackSwapMix0And2;
  case OpCode::Count:
    break;
  }
  throw std::logic_error("invalid opcode");
}

std::vector<TwoLevelCallbackRecord> MakeTwoLevelTrace(std::span<const CompactOp8> trace)
{
  std::vector<TwoLevelCallbackRecord> result;
  result.reserve(trace.size());
  for (const CompactOp8& op : trace)
    result.push_back({OuterInterpret, GetInnerCallback(op.opcode), op.immediate, 0});
  return result;
}

std::vector<OneLevelCallbackRecord> MakeOneLevelTrace(std::span<const CompactOp8> trace)
{
  std::vector<OneLevelCallbackRecord> result;
  result.reserve(trace.size());
  for (const CompactOp8& op : trace)
    result.push_back({GetInnerCallback(op.opcode), op.immediate, 0});
  return result;
}

std::vector<IdOp16> MakeIdTrace(std::span<const CompactOp8> trace)
{
  std::vector<IdOp16> result;
  result.reserve(trace.size());
  for (const CompactOp8& op : trace)
  {
    result.push_back({static_cast<std::uint16_t>(op.opcode), 0, op.immediate,
                      static_cast<std::uint64_t>(op.dst) |
                          (static_cast<std::uint64_t>(op.src_a) << 8) |
                          (static_cast<std::uint64_t>(op.src_b) << 16)});
  }
  return result;
}

std::vector<CompactOp12> MakeTrace12(std::span<const CompactOp8> trace)
{
  std::vector<CompactOp12> result;
  result.reserve(trace.size());
  for (const CompactOp8& op : trace)
    result.push_back({op, 0});
  return result;
}

std::vector<CompactOp16> MakeTrace16(std::span<const CompactOp8> trace)
{
  std::vector<CompactOp16> result;
  result.reserve(trace.size());
  for (const CompactOp8& op : trace)
    result.push_back({op, 0});
  return result;
}

CI3_NOINLINE std::uint64_t RunTwoLevelCallbacks(std::span<const TwoLevelCallbackRecord> trace,
                                                std::uint64_t iterations,
                                                MachineState state)
{
  for (std::uint64_t iteration = 0; iteration < iterations; ++iteration)
  {
    for (const TwoLevelCallbackRecord& record : trace)
      record.outer(&state, record);
  }
  return Checksum(state);
}

CI3_NOINLINE std::uint64_t RunDevirtualizedCallbacks(
    std::span<const TwoLevelCallbackRecord> trace, std::uint64_t iterations, MachineState state)
{
  for (std::uint64_t iteration = 0; iteration < iterations; ++iteration)
  {
    for (const TwoLevelCallbackRecord& record : trace)
    {
      if (record.outer == OuterInterpret)
        record.inner(&state, record.immediate);
      else
        record.outer(&state, record);
    }
  }
  return Checksum(state);
}

CI3_NOINLINE std::uint64_t RunOneLevelCallbacks(std::span<const OneLevelCallbackRecord> trace,
                                                std::uint64_t iterations,
                                                MachineState state)
{
  for (std::uint64_t iteration = 0; iteration < iterations; ++iteration)
  {
    for (const OneLevelCallbackRecord& record : trace)
      record.callback(&state, record.immediate);
  }
  return Checksum(state);
}

CI3_NOINLINE std::uint64_t RunIdSwitch(std::span<const IdOp16> trace,
                                       std::uint64_t iterations, MachineState state)
{
  for (std::uint64_t iteration = 0; iteration < iterations; ++iteration)
  {
    for (const IdOp16& op : trace)
    {
      const CompactOp8 compact{static_cast<OpCode>(op.id), 0, 0, 0, op.immediate};
      ApplyOp(&state, compact);
    }
  }
  return Checksum(state);
}

CI3_NOINLINE std::uint64_t RunCompactSwitch8(std::span<const CompactOp8> trace,
                                             std::uint64_t iterations,
                                             MachineState state)
{
  for (std::uint64_t iteration = 0; iteration < iterations; ++iteration)
  {
    for (const CompactOp8& op : trace)
      ApplyOp(&state, op);
  }
  return Checksum(state);
}

CI3_NOINLINE std::uint64_t RunCompactSwitch12(std::span<const CompactOp12> trace,
                                              std::uint64_t iterations,
                                              MachineState state)
{
  for (std::uint64_t iteration = 0; iteration < iterations; ++iteration)
  {
    for (const CompactOp12& op : trace)
      ApplyOp(&state, op.op);
  }
  return Checksum(state);
}

CI3_NOINLINE std::uint64_t RunCompactSwitch16(std::span<const CompactOp16> trace,
                                              std::uint64_t iterations,
                                              MachineState state)
{
  for (std::uint64_t iteration = 0; iteration < iterations; ++iteration)
  {
    for (const CompactOp16& op : trace)
      ApplyOp(&state, op.op);
  }
  return Checksum(state);
}

CI3_NOINLINE std::uint64_t RunPinnedSwitch8(std::span<const CompactOp8> trace,
                                            std::uint64_t iterations,
                                            MachineState state)
{
  std::uint64_t r0 = state.regs[0];
  std::uint64_t r1 = state.regs[1];
  std::uint64_t r2 = state.regs[2];
  std::uint64_t r3 = state.regs[3];

  for (std::uint64_t iteration = 0; iteration < iterations; ++iteration)
  {
    for (const CompactOp8& op : trace)
      ApplyPinnedOp(&r0, &r1, &r2, &r3, op);
  }

  return HashRegisters(r0, r1, r2, r3);
}

#if defined(__GNUC__) || defined(__clang__)
CI3_NOINLINE std::uint64_t RunComputedGoto8(std::span<const CompactOp8> trace,
                                            std::uint64_t iterations,
                                            MachineState state)
{
  const CompactOp8* const begin = trace.data();
  const CompactOp8* const end = begin + trace.size();
  const CompactOp8* ip = begin;
  std::uint64_t remaining = iterations;

  static const void* const dispatch_table[] = {
      &&op_add0, &&op_xor1, &&op_rotate2, &&op_add3,
      &&op_mix0, &&op_multiply1, &&op_select2, &&op_swap_mix,
  };

  goto dispatch;

dispatch:
  goto *dispatch_table[static_cast<std::uint8_t>(ip->opcode)];

#define CI3_NEXT_OP()                                                                            \
  do                                                                                             \
  {                                                                                              \
    ++ip;                                                                                        \
    if (ip == end)                                                                               \
    {                                                                                            \
      if (--remaining == 0)                                                                      \
        goto done;                                                                               \
      ip = begin;                                                                                \
    }                                                                                            \
    goto dispatch;                                                                               \
  } while (false)

op_add0:
  state.regs[0] += ip->immediate;
  CI3_NEXT_OP();

op_xor1:
  state.regs[1] ^= state.regs[0] + ip->immediate;
  CI3_NEXT_OP();

op_rotate2:
  state.regs[2] = std::rotl(state.regs[2] ^ state.regs[1], ip->immediate & 63U);
  CI3_NEXT_OP();

op_add3:
  state.regs[3] += state.regs[2] ^ ip->immediate;
  CI3_NEXT_OP();

op_mix0:
  state.regs[0] = std::rotl(state.regs[0] + state.regs[3], 17) ^ ip->immediate;
  CI3_NEXT_OP();

op_multiply1:
  state.regs[1] *= static_cast<std::uint64_t>(ip->immediate | 1U);
  CI3_NEXT_OP();

op_select2:
  state.regs[2] ^= state.regs[0] < state.regs[1] ? state.regs[3] : state.regs[0];
  CI3_NEXT_OP();

op_swap_mix:
  {
    const std::uint64_t old_r0 = state.regs[0];
    state.regs[0] = state.regs[2] ^ ip->immediate;
    state.regs[2] = old_r0 + state.regs[1];
  }
  CI3_NEXT_OP();

done:
#undef CI3_NEXT_OP
  return Checksum(state);
}
#endif

#if CI3_HAS_MUSTTAIL
struct TailOp;
using TailHandler = std::uint64_t(CI3_PRESERVE_NONE *)(
    const TailOp*, const TailOp*, std::uint64_t, std::uint64_t, std::uint64_t, std::uint64_t,
    std::uint64_t);

struct TailOp
{
  TailHandler handler = nullptr;
  std::uint32_t immediate = 0;
  std::uint32_t reserved = 0;
};

CI3_PRESERVE_NONE std::uint64_t TailAdd0(const TailOp* op, const TailOp* begin,
                                         std::uint64_t remaining, std::uint64_t r0,
                                         std::uint64_t r1, std::uint64_t r2,
                                         std::uint64_t r3);
CI3_PRESERVE_NONE std::uint64_t TailXor1(const TailOp* op, const TailOp* begin,
                                         std::uint64_t remaining, std::uint64_t r0,
                                         std::uint64_t r1, std::uint64_t r2,
                                         std::uint64_t r3);
CI3_PRESERVE_NONE std::uint64_t TailRotate2(const TailOp* op, const TailOp* begin,
                                            std::uint64_t remaining, std::uint64_t r0,
                                            std::uint64_t r1, std::uint64_t r2,
                                            std::uint64_t r3);
CI3_PRESERVE_NONE std::uint64_t TailAdd3(const TailOp* op, const TailOp* begin,
                                         std::uint64_t remaining, std::uint64_t r0,
                                         std::uint64_t r1, std::uint64_t r2,
                                         std::uint64_t r3);
CI3_PRESERVE_NONE std::uint64_t TailMix0(const TailOp* op, const TailOp* begin,
                                         std::uint64_t remaining, std::uint64_t r0,
                                         std::uint64_t r1, std::uint64_t r2,
                                         std::uint64_t r3);
CI3_PRESERVE_NONE std::uint64_t TailMultiply1(const TailOp* op, const TailOp* begin,
                                              std::uint64_t remaining, std::uint64_t r0,
                                              std::uint64_t r1, std::uint64_t r2,
                                              std::uint64_t r3);
CI3_PRESERVE_NONE std::uint64_t TailSelect2(const TailOp* op, const TailOp* begin,
                                            std::uint64_t remaining, std::uint64_t r0,
                                            std::uint64_t r1, std::uint64_t r2,
                                            std::uint64_t r3);
CI3_PRESERVE_NONE std::uint64_t TailSwapMix(const TailOp* op, const TailOp* begin,
                                            std::uint64_t remaining, std::uint64_t r0,
                                            std::uint64_t r1, std::uint64_t r2,
                                            std::uint64_t r3);
CI3_PRESERVE_NONE std::uint64_t TailEnd(const TailOp* op, const TailOp* begin,
                                        std::uint64_t remaining, std::uint64_t r0,
                                        std::uint64_t r1, std::uint64_t r2,
                                        std::uint64_t r3);

#define CI3_MUSTTAIL_NEXT(next_r0, next_r1, next_r2, next_r3)                              \
  do                                                                                        \
  {                                                                                         \
    const TailOp* const next = op + 1;                                                       \
    [[clang::musttail]] return next->handler(next, begin, remaining, next_r0, next_r1,       \
                                              next_r2, next_r3);                              \
  } while (false)

CI3_PRESERVE_NONE std::uint64_t TailAdd0(const TailOp* op, const TailOp* begin,
                                         std::uint64_t remaining, std::uint64_t r0,
                                         std::uint64_t r1, std::uint64_t r2,
                                         std::uint64_t r3)
{
  CI3_MUSTTAIL_NEXT(r0 + op->immediate, r1, r2, r3);
}

CI3_PRESERVE_NONE std::uint64_t TailXor1(const TailOp* op, const TailOp* begin,
                                         std::uint64_t remaining, std::uint64_t r0,
                                         std::uint64_t r1, std::uint64_t r2,
                                         std::uint64_t r3)
{
  CI3_MUSTTAIL_NEXT(r0, r1 ^ (r0 + op->immediate), r2, r3);
}

CI3_PRESERVE_NONE std::uint64_t TailRotate2(const TailOp* op, const TailOp* begin,
                                            std::uint64_t remaining, std::uint64_t r0,
                                            std::uint64_t r1, std::uint64_t r2,
                                            std::uint64_t r3)
{
  CI3_MUSTTAIL_NEXT(r0, r1, std::rotl(r2 ^ r1, op->immediate & 63U), r3);
}

CI3_PRESERVE_NONE std::uint64_t TailAdd3(const TailOp* op, const TailOp* begin,
                                         std::uint64_t remaining, std::uint64_t r0,
                                         std::uint64_t r1, std::uint64_t r2,
                                         std::uint64_t r3)
{
  CI3_MUSTTAIL_NEXT(r0, r1, r2, r3 + (r2 ^ op->immediate));
}

CI3_PRESERVE_NONE std::uint64_t TailMix0(const TailOp* op, const TailOp* begin,
                                         std::uint64_t remaining, std::uint64_t r0,
                                         std::uint64_t r1, std::uint64_t r2,
                                         std::uint64_t r3)
{
  CI3_MUSTTAIL_NEXT(std::rotl(r0 + r3, 17) ^ op->immediate, r1, r2, r3);
}

CI3_PRESERVE_NONE std::uint64_t TailMultiply1(const TailOp* op, const TailOp* begin,
                                              std::uint64_t remaining, std::uint64_t r0,
                                              std::uint64_t r1, std::uint64_t r2,
                                              std::uint64_t r3)
{
  CI3_MUSTTAIL_NEXT(r0, r1 * static_cast<std::uint64_t>(op->immediate | 1U), r2, r3);
}

CI3_PRESERVE_NONE std::uint64_t TailSelect2(const TailOp* op, const TailOp* begin,
                                            std::uint64_t remaining, std::uint64_t r0,
                                            std::uint64_t r1, std::uint64_t r2,
                                            std::uint64_t r3)
{
  (void)op;
  CI3_MUSTTAIL_NEXT(r0, r1, r2 ^ (r0 < r1 ? r3 : r0), r3);
}

CI3_PRESERVE_NONE std::uint64_t TailSwapMix(const TailOp* op, const TailOp* begin,
                                            std::uint64_t remaining, std::uint64_t r0,
                                            std::uint64_t r1, std::uint64_t r2,
                                            std::uint64_t r3)
{
  CI3_MUSTTAIL_NEXT(r2 ^ op->immediate, r1, r0 + r1, r3);
}

CI3_PRESERVE_NONE std::uint64_t TailEnd(const TailOp*, const TailOp* begin,
                                        std::uint64_t remaining, std::uint64_t r0,
                                        std::uint64_t r1, std::uint64_t r2,
                                        std::uint64_t r3)
{
  if (--remaining == 0)
    return HashRegisters(r0, r1, r2, r3);
  [[clang::musttail]] return begin->handler(begin, begin, remaining, r0, r1, r2, r3);
}

#undef CI3_MUSTTAIL_NEXT

TailHandler GetTailHandler(OpCode opcode)
{
  switch (opcode)
  {
  case OpCode::Add0Immediate:
    return TailAdd0;
  case OpCode::Xor1With0:
    return TailXor1;
  case OpCode::Rotate2With1:
    return TailRotate2;
  case OpCode::Add3With2:
    return TailAdd3;
  case OpCode::Mix0With3:
    return TailMix0;
  case OpCode::Multiply1Immediate:
    return TailMultiply1;
  case OpCode::Select2:
    return TailSelect2;
  case OpCode::SwapMix0And2:
    return TailSwapMix;
  case OpCode::Count:
    break;
  }
  throw std::logic_error("invalid opcode");
}

std::vector<TailOp> MakeTailTrace(std::span<const CompactOp8> trace)
{
  std::vector<TailOp> result;
  result.reserve(trace.size() + 1);
  for (const CompactOp8& op : trace)
    result.push_back({GetTailHandler(op.opcode), op.immediate, 0});
  result.push_back({TailEnd, 0, 0});
  return result;
}

CI3_NOINLINE std::uint64_t RunMusttail(std::span<const TailOp> trace,
                                       std::uint64_t iterations, MachineState state)
{
  const TailOp* const begin = trace.data();
  return begin->handler(begin, begin, iterations, state.regs[0], state.regs[1], state.regs[2],
                        state.regs[3]);
}
#endif

std::string CompilerName()
{
#if defined(__clang__)
  return std::string("clang-") + __clang_version__;
#elif defined(__GNUC__)
  return std::string("gcc-") + __VERSION__;
#elif defined(_MSC_VER)
  return std::string("msvc-") + std::to_string(_MSC_VER);
#else
  return "unknown";
#endif
}

std::string ArchitectureName()
{
#if defined(__aarch64__) || defined(_M_ARM64)
  return "aarch64";
#elif defined(__x86_64__) || defined(_M_X64)
  return "x86_64";
#elif defined(__i386__) || defined(_M_IX86)
  return "x86";
#else
  return "unknown";
#endif
}

std::string Hex(std::uint64_t value)
{
  std::ostringstream stream;
  stream << "0x" << std::hex << std::setw(16) << std::setfill('0') << value;
  return stream.str();
}

template <typename T>
T ParseInteger(std::string_view text, const char* option)
{
  T value{};
  int base = 10;
  if (text.size() > 2 && text[0] == '0' && (text[1] == 'x' || text[1] == 'X'))
  {
    text.remove_prefix(2);
    base = 16;
  }
  const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), value, base);
  if (error != std::errc{} || end != text.data() + text.size())
    throw std::invalid_argument(std::string("invalid value for ") + option);
  return value;
}

Options ParseOptions(int argc, char** argv)
{
  Options options{};
  for (int i = 1; i < argc; ++i)
  {
    const std::string_view arg = argv[i];
    auto require_value = [&](const char* option) -> std::string_view {
      if (++i >= argc)
        throw std::invalid_argument(std::string("missing value for ") + option);
      return argv[i];
    };

    if (arg == "--iterations")
      options.iterations = ParseInteger<std::uint64_t>(require_value("--iterations"), "--iterations");
    else if (arg == "--repetitions")
      options.repetitions = ParseInteger<std::size_t>(require_value("--repetitions"), "--repetitions");
    else if (arg == "--trace-length")
      options.trace_length = ParseInteger<std::size_t>(require_value("--trace-length"), "--trace-length");
    else if (arg == "--seed")
      options.seed = ParseInteger<std::uint64_t>(require_value("--seed"), "--seed");
    else if (arg == "--verify-only")
      options.verify_only = true;
    else if (arg == "--help")
    {
      std::cout << "CI3 Dispatch Lab\n"
                   "  --iterations N\n"
                   "  --repetitions N\n"
                   "  --trace-length N\n"
                   "  --seed N|0xHEX\n"
                   "  --verify-only\n";
      std::exit(0);
    }
    else
    {
      throw std::invalid_argument(std::string("unknown option: ") + std::string(arg));
    }
  }

  if (options.iterations == 0 || options.repetitions == 0 || options.trace_length == 0)
    throw std::invalid_argument("iterations, repetitions, and trace length must be non-zero");
  return options;
}

struct Engine
{
  std::string name;
  std::size_t record_bytes = 0;
  std::function<std::uint64_t()> run;
};

struct TimingResult
{
  double median_ns_per_op = 0;
  double min_ns_per_op = 0;
  double max_ns_per_op = 0;
  std::uint64_t checksum = 0;
};

TimingResult Measure(const Engine& engine, const Options& options, std::uint64_t total_ops)
{
  const std::uint64_t warm_checksum = engine.run();
  g_sink = warm_checksum;

  std::vector<double> samples;
  samples.reserve(options.repetitions);
  std::uint64_t checksum = 0;

  for (std::size_t repetition = 0; repetition < options.repetitions; ++repetition)
  {
    const auto start = std::chrono::steady_clock::now();
    checksum = engine.run();
    const auto stop = std::chrono::steady_clock::now();
    g_sink = checksum;

    const double elapsed_ns =
        std::chrono::duration<double, std::nano>(stop - start).count();
    samples.push_back(elapsed_ns / static_cast<double>(total_ops));
  }

  std::sort(samples.begin(), samples.end());
  double median = samples[samples.size() / 2];
  if (samples.size() % 2 == 0)
    median = (samples[samples.size() / 2 - 1] + samples[samples.size() / 2]) / 2.0;

  return {median, samples.front(), samples.back(), checksum};
}

void PrintEnvironment(const Options& options)
{
  std::cout << "{\"kind\":\"environment\",\"compiler\":\"" << CompilerName()
            << "\",\"architecture\":\"" << ArchitectureName() << "\",\"trace_length\":"
            << options.trace_length << ",\"iterations\":" << options.iterations
            << ",\"repetitions\":" << options.repetitions << ",\"seed\":\""
            << Hex(options.seed) << "\",\"computed_goto\":"
#if defined(__GNUC__) || defined(__clang__)
            << "true"
#else
            << "false"
#endif
            << ",\"preserve_none_musttail\":" << (CI3_HAS_MUSTTAIL ? "true" : "false")
            << "}\n";
}

void PrintResult(const Engine& engine, const TimingResult& result, const Options& options)
{
  std::cout << std::fixed << std::setprecision(4)
            << "{\"kind\":\"benchmark\",\"engine\":\"" << engine.name
            << "\",\"record_bytes\":" << engine.record_bytes << ",\"trace_length\":"
            << options.trace_length << ",\"iterations\":" << options.iterations
            << ",\"repetitions\":" << options.repetitions << ",\"median_ns_per_op\":"
            << result.median_ns_per_op << ",\"min_ns_per_op\":" << result.min_ns_per_op
            << ",\"max_ns_per_op\":" << result.max_ns_per_op << ",\"checksum\":\""
            << Hex(result.checksum) << "\"}\n";
}

}  // namespace

int main(int argc, char** argv)
{
  try
  {
    const Options options = ParseOptions(argc, argv);
    const std::vector<CompactOp8> trace = MakeTrace(options.trace_length, options.seed);
    const MachineState initial_state = MakeInitialState(options.seed);
    const std::vector<TwoLevelCallbackRecord> two_level = MakeTwoLevelTrace(trace);
    const std::vector<OneLevelCallbackRecord> one_level = MakeOneLevelTrace(trace);
    const std::vector<IdOp16> id_trace = MakeIdTrace(trace);
    const std::vector<CompactOp12> trace12 = MakeTrace12(trace);
    const std::vector<CompactOp16> trace16 = MakeTrace16(trace);
#if CI3_HAS_MUSTTAIL
    const std::vector<TailOp> tail_trace = MakeTailTrace(trace);
#endif

    std::vector<Engine> engines;
    engines.push_back({"callback-two-level", sizeof(TwoLevelCallbackRecord), [&] {
                         return RunTwoLevelCallbacks(two_level, options.iterations, initial_state);
                       }});
    engines.push_back({"callback-devirtualized", sizeof(TwoLevelCallbackRecord), [&] {
                         return RunDevirtualizedCallbacks(two_level, options.iterations,
                                                          initial_state);
                       }});
    engines.push_back({"callback-one-level", sizeof(OneLevelCallbackRecord), [&] {
                         return RunOneLevelCallbacks(one_level, options.iterations, initial_state);
                       }});
    engines.push_back({"id-switch-16", sizeof(IdOp16), [&] {
                         return RunIdSwitch(id_trace, options.iterations, initial_state);
                       }});
    engines.push_back({"compact-switch-8", sizeof(CompactOp8), [&] {
                         return RunCompactSwitch8(trace, options.iterations, initial_state);
                       }});
    engines.push_back({"compact-switch-12", sizeof(CompactOp12), [&] {
                         return RunCompactSwitch12(trace12, options.iterations, initial_state);
                       }});
    engines.push_back({"compact-switch-16", sizeof(CompactOp16), [&] {
                         return RunCompactSwitch16(trace16, options.iterations, initial_state);
                       }});
    engines.push_back({"pinned-switch-8", sizeof(CompactOp8), [&] {
                         return RunPinnedSwitch8(trace, options.iterations, initial_state);
                       }});
#if defined(__GNUC__) || defined(__clang__)
    engines.push_back({"computed-goto-8", sizeof(CompactOp8), [&] {
                         return RunComputedGoto8(trace, options.iterations, initial_state);
                       }});
#endif
#if CI3_HAS_MUSTTAIL
    engines.push_back({"preserve-none-musttail", sizeof(TailOp), [&] {
                         return RunMusttail(tail_trace, options.iterations, initial_state);
                       }});
#endif

    PrintEnvironment(options);

    const std::uint64_t reference_checksum = engines.front().run();
    for (const Engine& engine : engines)
    {
      const std::uint64_t checksum = engine.run();
      if (checksum != reference_checksum)
      {
        std::cerr << "verification failed for " << engine.name << ": expected "
                  << Hex(reference_checksum) << ", got " << Hex(checksum) << '\n';
        return 2;
      }
    }

    if (options.verify_only)
    {
      std::cout << "{\"kind\":\"verification\",\"engines\":" << engines.size()
                << ",\"checksum\":\"" << Hex(reference_checksum) << "\",\"status\":\"pass\"}\n";
      return 0;
    }

    if (options.trace_length > std::numeric_limits<std::uint64_t>::max() / options.iterations)
      throw std::overflow_error("total operation count overflow");
    const std::uint64_t total_ops =
        static_cast<std::uint64_t>(options.trace_length) * options.iterations;

    for (const Engine& engine : engines)
      PrintResult(engine, Measure(engine, options, total_ops), options);

    return 0;
  }
  catch (const std::exception& error)
  {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
