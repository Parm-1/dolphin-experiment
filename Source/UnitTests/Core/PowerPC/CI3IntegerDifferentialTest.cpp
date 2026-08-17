// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>
#include <vector>

#include "Common/CommonTypes.h"
#include "Core/PowerPC/Gekko.h"
#include "Core/PowerPC/Interpreter/Interpreter.h"
#include "Core/PowerPC/PPCTables.h"
#include "Core/PowerPC/PowerPC.h"
#include "Core/System.h"

#include <gtest/gtest.h>

namespace
{

enum class CI3Opcode : u8
{
  AddImmediate,
  OrImmediate,
  OrImmediateShifted,
  XorImmediate,
  XorImmediateShifted,
  RotateLeftWordImmediateAndMask,
  And,
  AndComplement,
  Or,
  OrComplement,
  Xor,
  Nor,
  CountLeadingZeros,
  ExtendSignByte,
  ExtendSignHalfword,
  ShiftLeftWord,
  ShiftRightWord,
  Count,
};

struct CI3Op
{
  CI3Opcode opcode{};
  u8 destination = 0;
  u8 source_a = 0;
  u8 source_b = 0;
  u32 immediate = 0;
};
static_assert(sizeof(CI3Op) == 8);

constexpr std::array<std::string_view, static_cast<std::size_t>(CI3Opcode::Count)>
    EXPECTED_NAMES = {
        "addi",    "ori",   "oris",   "xori",  "xoris",  "rlwinmx",
        "andx",    "andcx", "orx",    "orcx",  "xorx",   "norx",
        "cntlzwx", "extsbx", "extshx", "slwx", "srwx",
};

constexpr u32 PackRotateMask(u32 shift, u32 mask_begin, u32 mask_end)
{
  return (shift & 0x1f) | ((mask_begin & 0x1f) << 5) | ((mask_end & 0x1f) << 10);
}

constexpr u32 SignExtendImmediate(u32 immediate)
{
  return static_cast<u32>(static_cast<s32>(static_cast<s16>(immediate)));
}

std::uint64_t NextRandom(std::uint64_t* state)
{
  std::uint64_t value = *state;
  value ^= value >> 12;
  value ^= value << 25;
  value ^= value >> 27;
  *state = value;
  return value * 0x2545F4914F6CDD1DULL;
}

UGeckoInstruction Encode(const CI3Op& op)
{
  UGeckoInstruction inst{};

  switch (op.opcode)
  {
  case CI3Opcode::AddImmediate:
    inst.OPCD = 14;
    inst.RD = op.destination;
    inst.RA = op.source_a;
    inst.SIMM_16 = static_cast<s16>(op.immediate);
    break;
  case CI3Opcode::OrImmediate:
    inst.OPCD = 24;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.UIMM = op.immediate;
    break;
  case CI3Opcode::OrImmediateShifted:
    inst.OPCD = 25;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.UIMM = op.immediate;
    break;
  case CI3Opcode::XorImmediate:
    inst.OPCD = 26;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.UIMM = op.immediate;
    break;
  case CI3Opcode::XorImmediateShifted:
    inst.OPCD = 27;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.UIMM = op.immediate;
    break;
  case CI3Opcode::RotateLeftWordImmediateAndMask:
    inst.OPCD = 21;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.SH = op.immediate & 0x1f;
    inst.MB = (op.immediate >> 5) & 0x1f;
    inst.ME = (op.immediate >> 10) & 0x1f;
    inst.Rc = 0;
    break;
  case CI3Opcode::And:
    inst.OPCD = 31;
    inst.SUBOP10 = 28;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.RB = op.source_b;
    inst.Rc = 0;
    break;
  case CI3Opcode::AndComplement:
    inst.OPCD = 31;
    inst.SUBOP10 = 60;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.RB = op.source_b;
    inst.Rc = 0;
    break;
  case CI3Opcode::Or:
    inst.OPCD = 31;
    inst.SUBOP10 = 444;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.RB = op.source_b;
    inst.Rc = 0;
    break;
  case CI3Opcode::OrComplement:
    inst.OPCD = 31;
    inst.SUBOP10 = 412;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.RB = op.source_b;
    inst.Rc = 0;
    break;
  case CI3Opcode::Xor:
    inst.OPCD = 31;
    inst.SUBOP10 = 316;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.RB = op.source_b;
    inst.Rc = 0;
    break;
  case CI3Opcode::Nor:
    inst.OPCD = 31;
    inst.SUBOP10 = 124;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.RB = op.source_b;
    inst.Rc = 0;
    break;
  case CI3Opcode::CountLeadingZeros:
    inst.OPCD = 31;
    inst.SUBOP10 = 26;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.Rc = 0;
    break;
  case CI3Opcode::ExtendSignByte:
    inst.OPCD = 31;
    inst.SUBOP10 = 954;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.Rc = 0;
    break;
  case CI3Opcode::ExtendSignHalfword:
    inst.OPCD = 31;
    inst.SUBOP10 = 922;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.Rc = 0;
    break;
  case CI3Opcode::ShiftLeftWord:
    inst.OPCD = 31;
    inst.SUBOP10 = 24;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.RB = op.source_b;
    inst.Rc = 0;
    break;
  case CI3Opcode::ShiftRightWord:
    inst.OPCD = 31;
    inst.SUBOP10 = 536;
    inst.RA = op.destination;
    inst.RS = op.source_a;
    inst.RB = op.source_b;
    inst.Rc = 0;
    break;
  case CI3Opcode::Count:
    ADD_FAILURE() << "Attempted to encode the opcode sentinel";
    break;
  }

  return inst;
}

void ExecuteReference(Interpreter* interpreter, const CI3Op& op)
{
  const UGeckoInstruction inst = Encode(op);

  switch (op.opcode)
  {
  case CI3Opcode::AddImmediate:
    Interpreter::addi(*interpreter, inst);
    break;
  case CI3Opcode::OrImmediate:
    Interpreter::ori(*interpreter, inst);
    break;
  case CI3Opcode::OrImmediateShifted:
    Interpreter::oris(*interpreter, inst);
    break;
  case CI3Opcode::XorImmediate:
    Interpreter::xori(*interpreter, inst);
    break;
  case CI3Opcode::XorImmediateShifted:
    Interpreter::xoris(*interpreter, inst);
    break;
  case CI3Opcode::RotateLeftWordImmediateAndMask:
    Interpreter::rlwinmx(*interpreter, inst);
    break;
  case CI3Opcode::And:
    Interpreter::andx(*interpreter, inst);
    break;
  case CI3Opcode::AndComplement:
    Interpreter::andcx(*interpreter, inst);
    break;
  case CI3Opcode::Or:
    Interpreter::orx(*interpreter, inst);
    break;
  case CI3Opcode::OrComplement:
    Interpreter::orcx(*interpreter, inst);
    break;
  case CI3Opcode::Xor:
    Interpreter::xorx(*interpreter, inst);
    break;
  case CI3Opcode::Nor:
    Interpreter::norx(*interpreter, inst);
    break;
  case CI3Opcode::CountLeadingZeros:
    Interpreter::cntlzwx(*interpreter, inst);
    break;
  case CI3Opcode::ExtendSignByte:
    Interpreter::extsbx(*interpreter, inst);
    break;
  case CI3Opcode::ExtendSignHalfword:
    Interpreter::extshx(*interpreter, inst);
    break;
  case CI3Opcode::ShiftLeftWord:
    Interpreter::slwx(*interpreter, inst);
    break;
  case CI3Opcode::ShiftRightWord:
    Interpreter::srwx(*interpreter, inst);
    break;
  case CI3Opcode::Count:
    ADD_FAILURE() << "Attempted to execute the opcode sentinel";
    break;
  }
}

void ExecuteCompact(PowerPC::PowerPCState* state, const CI3Op& op)
{
  switch (op.opcode)
  {
  case CI3Opcode::AddImmediate:
  {
    const u32 immediate = SignExtendImmediate(op.immediate);
    state->gpr[op.destination] =
        op.source_a == 0 ? immediate : state->gpr[op.source_a] + immediate;
    break;
  }
  case CI3Opcode::OrImmediate:
    state->gpr[op.destination] = state->gpr[op.source_a] | (op.immediate & 0xffff);
    break;
  case CI3Opcode::OrImmediateShifted:
    state->gpr[op.destination] = state->gpr[op.source_a] | ((op.immediate & 0xffff) << 16);
    break;
  case CI3Opcode::XorImmediate:
    state->gpr[op.destination] = state->gpr[op.source_a] ^ (op.immediate & 0xffff);
    break;
  case CI3Opcode::XorImmediateShifted:
    state->gpr[op.destination] = state->gpr[op.source_a] ^ ((op.immediate & 0xffff) << 16);
    break;
  case CI3Opcode::RotateLeftWordImmediateAndMask:
  {
    const u32 shift = op.immediate & 0x1f;
    const u32 mask_begin = (op.immediate >> 5) & 0x1f;
    const u32 mask_end = (op.immediate >> 10) & 0x1f;
    state->gpr[op.destination] =
        std::rotl(state->gpr[op.source_a], shift) & MakeRotationMask(mask_begin, mask_end);
    break;
  }
  case CI3Opcode::And:
    state->gpr[op.destination] = state->gpr[op.source_a] & state->gpr[op.source_b];
    break;
  case CI3Opcode::AndComplement:
    state->gpr[op.destination] = state->gpr[op.source_a] & ~state->gpr[op.source_b];
    break;
  case CI3Opcode::Or:
    state->gpr[op.destination] = state->gpr[op.source_a] | state->gpr[op.source_b];
    break;
  case CI3Opcode::OrComplement:
    state->gpr[op.destination] = state->gpr[op.source_a] | ~state->gpr[op.source_b];
    break;
  case CI3Opcode::Xor:
    state->gpr[op.destination] = state->gpr[op.source_a] ^ state->gpr[op.source_b];
    break;
  case CI3Opcode::Nor:
    state->gpr[op.destination] = ~(state->gpr[op.source_a] | state->gpr[op.source_b]);
    break;
  case CI3Opcode::CountLeadingZeros:
    state->gpr[op.destination] = std::countl_zero(state->gpr[op.source_a]);
    break;
  case CI3Opcode::ExtendSignByte:
    state->gpr[op.destination] =
        static_cast<u32>(static_cast<s32>(static_cast<s8>(state->gpr[op.source_a])));
    break;
  case CI3Opcode::ExtendSignHalfword:
    state->gpr[op.destination] =
        static_cast<u32>(static_cast<s32>(static_cast<s16>(state->gpr[op.source_a])));
    break;
  case CI3Opcode::ShiftLeftWord:
  {
    const u32 amount = state->gpr[op.source_b];
    state->gpr[op.destination] =
        (amount & 0x20) != 0 ? 0 : state->gpr[op.source_a] << (amount & 0x1f);
    break;
  }
  case CI3Opcode::ShiftRightWord:
  {
    const u32 amount = state->gpr[op.source_b];
    state->gpr[op.destination] =
        (amount & 0x20) != 0 ? 0 : state->gpr[op.source_a] >> (amount & 0x1f);
    break;
  }
  case CI3Opcode::Count:
    ADD_FAILURE() << "Attempted to execute the opcode sentinel";
    break;
  }
}

void InitializeState(PowerPC::PowerPCState* state, std::uint64_t seed)
{
  std::uint64_t random = seed;

  state->pc = static_cast<u32>(NextRandom(&random));
  state->npc = static_cast<u32>(NextRandom(&random));
  for (u32& value : state->gpr)
    value = static_cast<u32>(NextRandom(&random));
  for (u64& value : state->cr.fields)
    value = NextRandom(&random);
  state->msr.Hex = static_cast<u32>(NextRandom(&random));
  state->fpscr.Hex = static_cast<u32>(NextRandom(&random));
  state->Exceptions = static_cast<u32>(NextRandom(&random));
  state->downcount = static_cast<int>(NextRandom(&random));
  state->xer_ca = NextRandom(&random) & 1;
  state->xer_so_ov = NextRandom(&random) & 3;
  state->xer_stringctrl = static_cast<u16>(NextRandom(&random));
  state->reserve_address = static_cast<u32>(NextRandom(&random));
  state->reserve = (NextRandom(&random) & 1) != 0;
  state->pagetable_update_pending = (NextRandom(&random) & 1) != 0;
  state->m_enable_dcache = (NextRandom(&random) & 1) != 0;

  for (PowerPC::PairedSingle& value : state->ps)
    value.SetBoth(NextRandom(&random), NextRandom(&random));
  for (u32& value : state->sr)
    value = static_cast<u32>(NextRandom(&random));
  for (u32& value : state->spr)
    value = static_cast<u32>(NextRandom(&random));

  state->pagetable_base = static_cast<u32>(NextRandom(&random));
  state->pagetable_mask = static_cast<u32>(NextRandom(&random));
}

void ExpectGPRsEqual(const PowerPC::PowerPCState& reference,
                     const PowerPC::PowerPCState& compact)
{
  for (std::size_t i = 0; i < std::size(reference.gpr); ++i)
    EXPECT_EQ(reference.gpr[i], compact.gpr[i]) << "GPR " << i;
}

void ExpectArchitecturalStateEqual(const PowerPC::PowerPCState& reference,
                                   const PowerPC::PowerPCState& compact)
{
  ExpectGPRsEqual(reference, compact);
  EXPECT_EQ(reference.pc, compact.pc);
  EXPECT_EQ(reference.npc, compact.npc);
  for (std::size_t i = 0; i < std::size(reference.cr.fields); ++i)
    EXPECT_EQ(reference.cr.fields[i], compact.cr.fields[i]) << "CR field " << i;
  EXPECT_EQ(reference.msr.Hex, compact.msr.Hex);
  EXPECT_EQ(reference.fpscr.Hex, compact.fpscr.Hex);
  EXPECT_EQ(reference.Exceptions, compact.Exceptions);
  EXPECT_EQ(reference.downcount, compact.downcount);
  EXPECT_EQ(reference.xer_ca, compact.xer_ca);
  EXPECT_EQ(reference.xer_so_ov, compact.xer_so_ov);
  EXPECT_EQ(reference.xer_stringctrl, compact.xer_stringctrl);
  EXPECT_EQ(reference.reserve_address, compact.reserve_address);
  EXPECT_EQ(reference.reserve, compact.reserve);
  EXPECT_EQ(reference.pagetable_update_pending, compact.pagetable_update_pending);
  EXPECT_EQ(reference.m_enable_dcache, compact.m_enable_dcache);

  for (std::size_t i = 0; i < std::size(reference.ps); ++i)
  {
    EXPECT_EQ(reference.ps[i].PS0AsU64(), compact.ps[i].PS0AsU64()) << "FPR " << i << " PS0";
    EXPECT_EQ(reference.ps[i].PS1AsU64(), compact.ps[i].PS1AsU64()) << "FPR " << i << " PS1";
  }
  for (std::size_t i = 0; i < reference.sr.size(); ++i)
    EXPECT_EQ(reference.sr[i], compact.sr[i]) << "SR " << i;
  for (std::size_t i = 0; i < std::size(reference.spr); ++i)
    EXPECT_EQ(reference.spr[i], compact.spr[i]) << "SPR " << i;

  EXPECT_EQ(reference.pagetable_base, compact.pagetable_base);
  EXPECT_EQ(reference.pagetable_mask, compact.pagetable_mask);
}

std::vector<CI3Op> MakeTrace(std::size_t length, std::uint64_t seed)
{
  std::vector<CI3Op> trace;
  trace.reserve(length);
  std::uint64_t random = seed;

  for (std::size_t i = 0; i < length; ++i)
  {
    const std::uint64_t value = NextRandom(&random);
    CI3Op op{};
    op.opcode = static_cast<CI3Opcode>(value % static_cast<u8>(CI3Opcode::Count));
    op.destination = (value >> 8) & 0x1f;
    op.source_a = (value >> 13) & 0x1f;
    op.source_b = (value >> 18) & 0x1f;
    op.immediate = static_cast<u32>(value >> 32);

    if (op.opcode == CI3Opcode::RotateLeftWordImmediateAndMask)
    {
      op.immediate = PackRotateMask(value >> 32, value >> 37, value >> 42);
    }

    trace.emplace_back(op);
  }

  return trace;
}

void ExecuteAndCompare(std::span<const CI3Op> trace, std::uint64_t state_seed)
{
  PowerPC::PowerPCState reference_state{};
  PowerPC::PowerPCState compact_state{};
  InitializeState(&reference_state, state_seed);
  InitializeState(&compact_state, state_seed);

  Core::System& system = Core::System::GetInstance();
  Interpreter interpreter(system, reference_state, system.GetMMU(),
                          system.GetPowerPC().GetBranchWatch(), system.GetPPCSymbolDB());
  interpreter.Init();

  for (std::size_t i = 0; i < trace.size(); ++i)
  {
    const CI3Op& op = trace[i];
    SCOPED_TRACE(::testing::Message() << "operation=" << i << " opcode="
                                      << EXPECTED_NAMES[static_cast<std::size_t>(op.opcode)]);
    ExecuteReference(&interpreter, op);
    ExecuteCompact(&compact_state, op);
    ExpectGPRsEqual(reference_state, compact_state);
    for (std::size_t field = 0; field < std::size(reference_state.cr.fields); ++field)
      EXPECT_EQ(reference_state.cr.fields[field], compact_state.cr.fields[field]);
    EXPECT_EQ(reference_state.GetXER().Hex, compact_state.GetXER().Hex);
    EXPECT_EQ(reference_state.Exceptions, compact_state.Exceptions);
  }

  ExpectArchitecturalStateEqual(reference_state, compact_state);
}

TEST(CI3PowerPCIntegerDifferential, EncodingsAndMetadataMatchScope)
{
  constexpr u64 disallowed_flags =
      FL_SET_CA | FL_READ_CA | FL_TIMER | FL_CHECKEXCEPTIONS | FL_USE_FPU | FL_LOADSTORE |
      FL_SET_OE | FL_PROGRAMEXCEPTION | FL_FLOAT_EXCEPTION | FL_FLOAT_DIV | FL_SET_MSR |
      FL_ENDBLOCK;

  for (std::size_t i = 0; i < static_cast<std::size_t>(CI3Opcode::Count); ++i)
  {
    CI3Op op{};
    op.opcode = static_cast<CI3Opcode>(i);
    op.destination = 3;
    op.source_a = 4;
    op.source_b = 5;
    op.immediate = op.opcode == CI3Opcode::RotateLeftWordImmediateAndMask ?
                       PackRotateMask(7, 28, 3) :
                       0x8001;

    const UGeckoInstruction inst = Encode(op);
    EXPECT_EQ(PPCTables::GetInstructionName(inst, 0), EXPECTED_NAMES[i]);

    const GekkoOPInfo* const info = PPCTables::GetOpInfo(inst, 0);
    EXPECT_EQ(info->type, OpType::Integer) << EXPECTED_NAMES[i];
    EXPECT_EQ(info->flags & disallowed_flags, 0U) << EXPECTED_NAMES[i];
    EXPECT_FALSE(inst.Rc) << EXPECTED_NAMES[i];
  }
}

TEST(CI3PowerPCIntegerDifferential, FixedEdgeCasesMatchReference)
{
  const std::array trace = {
      CI3Op{CI3Opcode::AddImmediate, 3, 0, 0, 0x8000},
      CI3Op{CI3Opcode::AddImmediate, 4, 4, 0, 0xffff},
      CI3Op{CI3Opcode::OrImmediate, 5, 3, 0, 0xffff},
      CI3Op{CI3Opcode::OrImmediateShifted, 5, 5, 0, 0xffff},
      CI3Op{CI3Opcode::XorImmediate, 6, 5, 0, 0x8001},
      CI3Op{CI3Opcode::XorImmediateShifted, 6, 6, 0, 0x8001},
      CI3Op{CI3Opcode::RotateLeftWordImmediateAndMask, 7, 6, 0,
            PackRotateMask(31, 28, 3)},
      CI3Op{CI3Opcode::ExtendSignByte, 8, 1, 0, 0},
      CI3Op{CI3Opcode::ExtendSignHalfword, 9, 1, 0, 0},
      CI3Op{CI3Opcode::CountLeadingZeros, 10, 2, 0, 0},
      CI3Op{CI3Opcode::ShiftLeftWord, 11, 1, 12, 0},
      CI3Op{CI3Opcode::ShiftRightWord, 13, 1, 14, 0},
      CI3Op{CI3Opcode::And, 15, 5, 6, 0},
      CI3Op{CI3Opcode::AndComplement, 16, 5, 6, 0},
      CI3Op{CI3Opcode::Or, 17, 15, 16, 0},
      CI3Op{CI3Opcode::OrComplement, 18, 15, 16, 0},
      CI3Op{CI3Opcode::Xor, 19, 17, 18, 0},
      CI3Op{CI3Opcode::Nor, 20, 17, 18, 0},
  };

  PowerPC::PowerPCState reference_state{};
  PowerPC::PowerPCState compact_state{};
  InitializeState(&reference_state, 0xED6ECA5E12345678ULL);
  InitializeState(&compact_state, 0xED6ECA5E12345678ULL);

  reference_state.gpr[1] = compact_state.gpr[1] = 0x80008080;
  reference_state.gpr[2] = compact_state.gpr[2] = 0;
  reference_state.gpr[12] = compact_state.gpr[12] = 32;
  reference_state.gpr[14] = compact_state.gpr[14] = 63;

  Core::System& system = Core::System::GetInstance();
  Interpreter interpreter(system, reference_state, system.GetMMU(),
                          system.GetPowerPC().GetBranchWatch(), system.GetPPCSymbolDB());
  interpreter.Init();

  for (const CI3Op& op : trace)
  {
    ExecuteReference(&interpreter, op);
    ExecuteCompact(&compact_state, op);
    ExpectGPRsEqual(reference_state, compact_state);
  }

  ExpectArchitecturalStateEqual(reference_state, compact_state);
}

TEST(CI3PowerPCIntegerDifferential, RandomizedTracesMatchReference)
{
  constexpr std::array seeds = {
      0x0000000000000001ULL, 0x0123456789abcdefULL, 0x1020304050607080ULL,
      0x243f6a8885a308d3ULL, 0x5a17e5eed1234567ULL, 0x7fffffffffffffffULL,
      0x8000000000000000ULL, 0x9e3779b97f4a7c15ULL, 0xc13c0ffee1234567ULL,
      0xdeadbeefcafebabeULL, 0xfedcba9876543210ULL, 0xffffffffffffffffULL,
  };

  for (const std::uint64_t seed : seeds)
  {
    SCOPED_TRACE(::testing::Message() << "seed=0x" << std::hex << seed);
    const std::vector<CI3Op> trace = MakeTrace(512, seed);
    ExecuteAndCompare(trace, seed ^ 0xa5a5a5a55a5a5a5aULL);
  }
}

}  // namespace
