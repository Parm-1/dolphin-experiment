#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import json
import pathlib
import re
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[3]
EXP006 = ROOT / "docs/ci3/experiments/EXP-20260817-006"
ACTION = json.loads((EXP006 / "stage0-action.json").read_text())
SLUG = ACTION["action_slug"]


def write(path: str, content: str) -> None:
    destination = ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(textwrap.dedent(content), encoding="utf-8")


def add_lines_after(path: str, needle: str, lines: list[str]) -> None:
    file_path = ROOT / path
    content = file_path.read_text(encoding="utf-8")
    if all(line in content for line in lines):
        return
    if needle not in content:
        raise RuntimeError(f"missing insertion point in {path}: {needle!r}")
    insertion = needle + "".join(line for line in lines if line not in content)
    file_path.write_text(content.replace(needle, insertion, 1), encoding="utf-8")


def generate_minimum_lowering() -> list[str]:
    write(
        "Source/Core/Core/PowerPC/CI3/SemanticOp.h",
        r'''// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include <array>
#include <cstddef>
#include <string_view>

#include "Common/CommonTypes.h"

namespace PowerPC::CI3
{

enum class SemanticOpcode : u8
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

struct SemanticOp
{
  SemanticOpcode opcode{};
  u8 destination = 0;
  u8 source_a = 0;
  u8 source_b = 0;
  u32 immediate = 0;

  bool operator==(const SemanticOp&) const = default;
};
static_assert(sizeof(SemanticOp) == 8);

constexpr std::array<std::string_view, static_cast<std::size_t>(SemanticOpcode::Count)>
    SEMANTIC_OPERATION_NAMES = {
        "addi",    "ori",    "oris",   "xori",    "xoris", "rlwinmx",
        "andx",    "andcx",  "orx",    "orcx",    "xorx",  "norx",
        "cntlzwx", "extsbx", "extshx", "slwx",    "srwx",
};

constexpr u32 PackRotateMask(u32 shift, u32 mask_begin, u32 mask_end)
{
  return (shift & 0x1f) | ((mask_begin & 0x1f) << 5) | ((mask_end & 0x1f) << 10);
}

constexpr std::string_view GetSemanticOperationName(SemanticOpcode opcode)
{
  return SEMANTIC_OPERATION_NAMES[static_cast<std::size_t>(opcode)];
}

}  // namespace PowerPC::CI3
''',
    )

    write(
        "Source/Core/Core/PowerPC/CI3/Lowering.h",
        r'''// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include <cstddef>
#include <expected>
#include <optional>
#include <span>
#include <vector>

#include "Common/CommonTypes.h"
#include "Core/PowerPC/CI3/SemanticOp.h"
#include "Core/PowerPC/PPCAnalyst.h"

namespace PowerPC::CI3
{

enum class LoweringRejectReason : u8
{
  BrokenBlock,
  Skipped,
  MissingOpInfo,
  UnsupportedName,
  WrongOperationType,
  RecordBit,
  CarryOrOverflow,
  ConditionRegister,
  FPRF,
  Memory,
  FloatingPoint,
  BranchOrBlockEnd,
  Exception,
  TimerOrSystemState,
  ClassifierRejected,
};

using LoweringResult = std::expected<SemanticOp, LoweringRejectReason>;

LoweringResult LowerOperation(const PPCAnalyst::CodeOp& operation);
const char* GetLoweringRejectReasonName(LoweringRejectReason reason);

enum class PartitionEntryKind : u8
{
  LoweredRun,
  Fallback,
  Skipped,
};

struct PartitionEntry
{
  PartitionEntryKind kind{};
  std::size_t operation_index = 0;
  std::size_t operation_count = 0;
  std::vector<SemanticOp> operations;
  std::optional<LoweringRejectReason> rejection;

  bool operator==(const PartitionEntry&) const = default;
};

struct BlockPartition
{
  bool broken = false;
  std::vector<PartitionEntry> entries;

  std::size_t LoweredOperationCount() const;
};

BlockPartition PartitionBlock(bool broken, std::span<const PPCAnalyst::CodeOp> operations);

}  // namespace PowerPC::CI3
''',
    )

    write(
        "Source/Core/Core/PowerPC/CI3/Lowering.cpp",
        r'''// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include "Core/PowerPC/CI3/Lowering.h"

#include <algorithm>
#include <string_view>
#include <utility>

#include "Core/PowerPC/CI3/BlockProfile.h"
#include "Core/PowerPC/PPCTables.h"

namespace PowerPC::CI3
{
namespace
{

bool IsLoadStoreType(OpType type)
{
  switch (type)
  {
  case OpType::Load:
  case OpType::Store:
  case OpType::LoadFP:
  case OpType::StoreFP:
  case OpType::LoadPS:
  case OpType::StorePS:
    return true;
  default:
    return false;
  }
}

bool IsFloatingPointType(OpType type)
{
  switch (type)
  {
  case OpType::SystemFP:
  case OpType::LoadFP:
  case OpType::StoreFP:
  case OpType::DoubleFP:
  case OpType::SingleFP:
  case OpType::LoadPS:
  case OpType::StorePS:
  case OpType::PS:
    return true;
  default:
    return false;
  }
}

bool IsSystemStateType(OpType type)
{
  switch (type)
  {
  case OpType::SPR:
  case OpType::System:
  case OpType::SystemFP:
  case OpType::DataCache:
  case OpType::InstructionCache:
    return true;
  default:
    return false;
  }
}

bool IsEstablishedName(std::string_view name)
{
  return std::ranges::find(SEMANTIC_OPERATION_NAMES, name) != SEMANTIC_OPERATION_NAMES.end();
}

LoweringRejectReason DiagnoseRejection(const PPCAnalyst::CodeOp& operation)
{
  if (operation.skip)
    return LoweringRejectReason::Skipped;
  if (operation.opinfo == nullptr || operation.opinfo->opname == nullptr)
    return LoweringRejectReason::MissingOpInfo;

  const GekkoOPInfo& info = *operation.opinfo;
  const u64 flags = info.flags;

  if ((flags & FL_LOADSTORE) != 0 || IsLoadStoreType(info.type))
    return LoweringRejectReason::Memory;
  if ((flags & FL_USE_FPU) != 0 || IsFloatingPointType(info.type))
    return LoweringRejectReason::FloatingPoint;
  if (info.type == OpType::Branch || (flags & FL_ENDBLOCK) != 0 || operation.canEndBlock)
    return LoweringRejectReason::BranchOrBlockEnd;
  if ((flags & (FL_CHECKEXCEPTIONS | FL_PROGRAMEXCEPTION | FL_FLOAT_EXCEPTION | FL_FLOAT_DIV)) !=
          0 ||
      operation.canCauseException)
  {
    return LoweringRejectReason::Exception;
  }
  if ((flags & (FL_SET_CA | FL_READ_CA | FL_SET_OE)) != 0 || operation.wantsCAInFlags ||
      operation.outputCA)
  {
    return LoweringRejectReason::CarryOrOverflow;
  }
  if ((flags & (FL_RC_BIT | FL_RC_BIT_F)) != 0 && operation.inst.Rc != 0)
    return LoweringRejectReason::RecordBit;
  if ((flags & (FL_SET_CRx | FL_READ_CRx)) != 0 || static_cast<bool>(operation.crIn) ||
      static_cast<bool>(operation.crOut))
  {
    return LoweringRejectReason::ConditionRegister;
  }
  if ((flags & (FL_SET_FPRF | FL_READ_FPRF)) != 0 || operation.outputFPRF)
    return LoweringRejectReason::FPRF;
  if ((flags & (FL_TIMER | FL_SET_MSR)) != 0 || IsSystemStateType(info.type))
    return LoweringRejectReason::TimerOrSystemState;
  if (!IsEstablishedName(info.opname))
    return LoweringRejectReason::UnsupportedName;
  if (info.type != OpType::Integer)
    return LoweringRejectReason::WrongOperationType;
  return LoweringRejectReason::ClassifierRejected;
}

SemanticOp EncodeEstablishedOperation(const PPCAnalyst::CodeOp& operation)
{
  const UGeckoInstruction inst = operation.inst;
  const std::string_view name = operation.opinfo->opname;

  if (name == "addi")
  {
    return {SemanticOpcode::AddImmediate, static_cast<u8>(inst.RD), static_cast<u8>(inst.RA), 0,
            static_cast<u32>(static_cast<u16>(inst.SIMM_16))};
  }
  if (name == "ori")
  {
    return {SemanticOpcode::OrImmediate, static_cast<u8>(inst.RA), static_cast<u8>(inst.RS), 0,
            static_cast<u32>(inst.UIMM)};
  }
  if (name == "oris")
  {
    return {SemanticOpcode::OrImmediateShifted, static_cast<u8>(inst.RA),
            static_cast<u8>(inst.RS), 0, static_cast<u32>(inst.UIMM)};
  }
  if (name == "xori")
  {
    return {SemanticOpcode::XorImmediate, static_cast<u8>(inst.RA), static_cast<u8>(inst.RS), 0,
            static_cast<u32>(inst.UIMM)};
  }
  if (name == "xoris")
  {
    return {SemanticOpcode::XorImmediateShifted, static_cast<u8>(inst.RA),
            static_cast<u8>(inst.RS), 0, static_cast<u32>(inst.UIMM)};
  }
  if (name == "rlwinmx")
  {
    return {SemanticOpcode::RotateLeftWordImmediateAndMask, static_cast<u8>(inst.RA),
            static_cast<u8>(inst.RS), 0, PackRotateMask(inst.SH, inst.MB, inst.ME)};
  }

  SemanticOpcode opcode{};
  if (name == "andx")
    opcode = SemanticOpcode::And;
  else if (name == "andcx")
    opcode = SemanticOpcode::AndComplement;
  else if (name == "orx")
    opcode = SemanticOpcode::Or;
  else if (name == "orcx")
    opcode = SemanticOpcode::OrComplement;
  else if (name == "xorx")
    opcode = SemanticOpcode::Xor;
  else if (name == "norx")
    opcode = SemanticOpcode::Nor;
  else if (name == "cntlzwx")
    opcode = SemanticOpcode::CountLeadingZeros;
  else if (name == "extsbx")
    opcode = SemanticOpcode::ExtendSignByte;
  else if (name == "extshx")
    opcode = SemanticOpcode::ExtendSignHalfword;
  else if (name == "slwx")
    opcode = SemanticOpcode::ShiftLeftWord;
  else
    opcode = SemanticOpcode::ShiftRightWord;

  const bool has_source_b = opcode == SemanticOpcode::And ||
                            opcode == SemanticOpcode::AndComplement || opcode == SemanticOpcode::Or ||
                            opcode == SemanticOpcode::OrComplement || opcode == SemanticOpcode::Xor ||
                            opcode == SemanticOpcode::Nor || opcode == SemanticOpcode::ShiftLeftWord ||
                            opcode == SemanticOpcode::ShiftRightWord;
  return {opcode, static_cast<u8>(inst.RA), static_cast<u8>(inst.RS),
          has_source_b ? static_cast<u8>(inst.RB) : u8{0}, 0};
}

}  // namespace

LoweringResult LowerOperation(const PPCAnalyst::CodeOp& operation)
{
  if (!IsSupportedOperation(operation))
    return std::unexpected(DiagnoseRejection(operation));
  return EncodeEstablishedOperation(operation);
}

const char* GetLoweringRejectReasonName(LoweringRejectReason reason)
{
  switch (reason)
  {
  case LoweringRejectReason::BrokenBlock:
    return "broken_block";
  case LoweringRejectReason::Skipped:
    return "skipped";
  case LoweringRejectReason::MissingOpInfo:
    return "missing_opinfo";
  case LoweringRejectReason::UnsupportedName:
    return "unsupported_name";
  case LoweringRejectReason::WrongOperationType:
    return "wrong_operation_type";
  case LoweringRejectReason::RecordBit:
    return "record_bit";
  case LoweringRejectReason::CarryOrOverflow:
    return "carry_or_overflow";
  case LoweringRejectReason::ConditionRegister:
    return "condition_register";
  case LoweringRejectReason::FPRF:
    return "fprf";
  case LoweringRejectReason::Memory:
    return "memory";
  case LoweringRejectReason::FloatingPoint:
    return "floating_point";
  case LoweringRejectReason::BranchOrBlockEnd:
    return "branch_or_block_end";
  case LoweringRejectReason::Exception:
    return "exception";
  case LoweringRejectReason::TimerOrSystemState:
    return "timer_or_system_state";
  case LoweringRejectReason::ClassifierRejected:
    return "classifier_rejected";
  }
  return "unknown";
}

std::size_t BlockPartition::LoweredOperationCount() const
{
  std::size_t count = 0;
  for (const PartitionEntry& entry : entries)
  {
    if (entry.kind == PartitionEntryKind::LoweredRun)
      count += entry.operation_count;
  }
  return count;
}

BlockPartition PartitionBlock(bool broken, std::span<const PPCAnalyst::CodeOp> operations)
{
  BlockPartition partition{.broken = broken};
  std::vector<SemanticOp> current_run;
  std::size_t current_run_start = 0;

  const auto flush_run = [&] {
    if (current_run.empty())
      return;
    const std::size_t count = current_run.size();
    partition.entries.push_back({PartitionEntryKind::LoweredRun, current_run_start, count,
                                 std::move(current_run), std::nullopt});
    current_run.clear();
  };

  for (std::size_t index = 0; index < operations.size(); ++index)
  {
    const PPCAnalyst::CodeOp& operation = operations[index];
    if (operation.skip)
    {
      flush_run();
      partition.entries.push_back({PartitionEntryKind::Skipped, index, 1, {},
                                   LoweringRejectReason::Skipped});
      continue;
    }

    if (broken)
    {
      flush_run();
      partition.entries.push_back({PartitionEntryKind::Fallback, index, 1, {},
                                   LoweringRejectReason::BrokenBlock});
      continue;
    }

    LoweringResult lowered = LowerOperation(operation);
    if (lowered)
    {
      if (current_run.empty())
        current_run_start = index;
      current_run.push_back(*lowered);
      continue;
    }

    flush_run();
    partition.entries.push_back(
        {PartitionEntryKind::Fallback, index, 1, {}, lowered.error()});
  }

  flush_run();
  return partition;
}

}  // namespace PowerPC::CI3
''',
    )

    write(
        "Source/UnitTests/Core/PowerPC/CI3LoweringTest.cpp",
        r'''// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <array>
#include <bit>
#include <cstddef>
#include <span>
#include <string_view>

#include "Common/CommonTypes.h"
#include "Core/PowerPC/CI3/Lowering.h"
#include "Core/PowerPC/Interpreter/Interpreter.h"
#include "Core/PowerPC/PPCTables.h"
#include "Core/PowerPC/PowerPC.h"
#include "Core/System.h"

#include <gtest/gtest.h>

namespace
{
using PowerPC::CI3::BlockPartition;
using PowerPC::CI3::GetLoweringRejectReasonName;
using PowerPC::CI3::LoweringRejectReason;
using PowerPC::CI3::LowerOperation;
using PowerPC::CI3::PackRotateMask;
using PowerPC::CI3::PartitionBlock;
using PowerPC::CI3::PartitionEntryKind;
using PowerPC::CI3::SemanticOp;
using PowerPC::CI3::SemanticOpcode;

UGeckoInstruction MakeInstruction(SemanticOpcode opcode)
{
  UGeckoInstruction inst{};
  switch (opcode)
  {
  case SemanticOpcode::AddImmediate:
    inst.OPCD = 14;
    inst.RD = 3;
    inst.RA = 4;
    inst.SIMM_16 = static_cast<s16>(0x8001);
    break;
  case SemanticOpcode::OrImmediate:
  case SemanticOpcode::OrImmediateShifted:
  case SemanticOpcode::XorImmediate:
  case SemanticOpcode::XorImmediateShifted:
    inst.OPCD = opcode == SemanticOpcode::OrImmediate ? 24 :
                opcode == SemanticOpcode::OrImmediateShifted ? 25 :
                opcode == SemanticOpcode::XorImmediate ? 26 : 27;
    inst.RA = 3;
    inst.RS = 4;
    inst.UIMM = 0x8001;
    break;
  case SemanticOpcode::RotateLeftWordImmediateAndMask:
    inst.OPCD = 21;
    inst.RA = 3;
    inst.RS = 4;
    inst.SH = 7;
    inst.MB = 28;
    inst.ME = 3;
    inst.Rc = 0;
    break;
  default:
    inst.OPCD = 31;
    inst.RA = 3;
    inst.RS = 4;
    inst.RB = 5;
    inst.Rc = 0;
    switch (opcode)
    {
    case SemanticOpcode::And:
      inst.SUBOP10 = 28;
      break;
    case SemanticOpcode::AndComplement:
      inst.SUBOP10 = 60;
      break;
    case SemanticOpcode::Or:
      inst.SUBOP10 = 444;
      break;
    case SemanticOpcode::OrComplement:
      inst.SUBOP10 = 412;
      break;
    case SemanticOpcode::Xor:
      inst.SUBOP10 = 316;
      break;
    case SemanticOpcode::Nor:
      inst.SUBOP10 = 124;
      break;
    case SemanticOpcode::CountLeadingZeros:
      inst.SUBOP10 = 26;
      break;
    case SemanticOpcode::ExtendSignByte:
      inst.SUBOP10 = 954;
      break;
    case SemanticOpcode::ExtendSignHalfword:
      inst.SUBOP10 = 922;
      break;
    case SemanticOpcode::ShiftLeftWord:
      inst.SUBOP10 = 24;
      break;
    case SemanticOpcode::ShiftRightWord:
      inst.SUBOP10 = 536;
      break;
    default:
      break;
    }
    break;
  case SemanticOpcode::Count:
    ADD_FAILURE() << "semantic opcode sentinel";
    break;
  }
  return inst;
}

PPCAnalyst::CodeOp MakeCodeOp(SemanticOpcode opcode)
{
  PPCAnalyst::CodeOp operation{};
  operation.inst = MakeInstruction(opcode);
  operation.opinfo = PPCTables::GetOpInfo(operation.inst, 0);
  return operation;
}

SemanticOp ExpectedRecord(SemanticOpcode opcode)
{
  switch (opcode)
  {
  case SemanticOpcode::AddImmediate:
    return {opcode, 3, 4, 0, 0x8001};
  case SemanticOpcode::OrImmediate:
  case SemanticOpcode::OrImmediateShifted:
  case SemanticOpcode::XorImmediate:
  case SemanticOpcode::XorImmediateShifted:
    return {opcode, 3, 4, 0, 0x8001};
  case SemanticOpcode::RotateLeftWordImmediateAndMask:
    return {opcode, 3, 4, 0, PackRotateMask(7, 28, 3)};
  case SemanticOpcode::CountLeadingZeros:
  case SemanticOpcode::ExtendSignByte:
  case SemanticOpcode::ExtendSignHalfword:
    return {opcode, 3, 4, 0, 0};
  default:
    return {opcode, 3, 4, 5, 0};
  }
}

void ConfigureSynthetic(PPCAnalyst::CodeOp* operation, GekkoOPInfo* info, const char* name,
                        OpType type, u64 flags)
{
  *info = GekkoOPInfo{name, type, 1, flags, nullptr};
  *operation = PPCAnalyst::CodeOp{};
  operation->opinfo = info;
}

void ExecuteReference(Interpreter* interpreter, const PPCAnalyst::CodeOp& operation)
{
  Interpreter::GetInterpreterOp(operation.inst)(*interpreter, operation.inst);
}

u32 SignExtendImmediate(u32 immediate)
{
  return static_cast<u32>(static_cast<s32>(static_cast<s16>(immediate)));
}

void ExecuteCompact(PowerPC::PowerPCState* state, const SemanticOp& operation)
{
  switch (operation.opcode)
  {
  case SemanticOpcode::AddImmediate:
  {
    const u32 immediate = SignExtendImmediate(operation.immediate);
    state->gpr[operation.destination] =
        operation.source_a == 0 ? immediate : state->gpr[operation.source_a] + immediate;
    break;
  }
  case SemanticOpcode::OrImmediate:
    state->gpr[operation.destination] = state->gpr[operation.source_a] |
                                        (operation.immediate & 0xffff);
    break;
  case SemanticOpcode::OrImmediateShifted:
    state->gpr[operation.destination] = state->gpr[operation.source_a] |
                                        ((operation.immediate & 0xffff) << 16);
    break;
  case SemanticOpcode::XorImmediate:
    state->gpr[operation.destination] = state->gpr[operation.source_a] ^
                                        (operation.immediate & 0xffff);
    break;
  case SemanticOpcode::XorImmediateShifted:
    state->gpr[operation.destination] = state->gpr[operation.source_a] ^
                                        ((operation.immediate & 0xffff) << 16);
    break;
  case SemanticOpcode::RotateLeftWordImmediateAndMask:
  {
    const u32 shift = operation.immediate & 0x1f;
    const u32 mask_begin = (operation.immediate >> 5) & 0x1f;
    const u32 mask_end = (operation.immediate >> 10) & 0x1f;
    state->gpr[operation.destination] =
        std::rotl(state->gpr[operation.source_a], shift) &
        MakeRotationMask(mask_begin, mask_end);
    break;
  }
  case SemanticOpcode::And:
    state->gpr[operation.destination] =
        state->gpr[operation.source_a] & state->gpr[operation.source_b];
    break;
  case SemanticOpcode::AndComplement:
    state->gpr[operation.destination] =
        state->gpr[operation.source_a] & ~state->gpr[operation.source_b];
    break;
  case SemanticOpcode::Or:
    state->gpr[operation.destination] =
        state->gpr[operation.source_a] | state->gpr[operation.source_b];
    break;
  case SemanticOpcode::OrComplement:
    state->gpr[operation.destination] =
        state->gpr[operation.source_a] | ~state->gpr[operation.source_b];
    break;
  case SemanticOpcode::Xor:
    state->gpr[operation.destination] =
        state->gpr[operation.source_a] ^ state->gpr[operation.source_b];
    break;
  case SemanticOpcode::Nor:
    state->gpr[operation.destination] =
        ~(state->gpr[operation.source_a] | state->gpr[operation.source_b]);
    break;
  case SemanticOpcode::CountLeadingZeros:
    state->gpr[operation.destination] = std::countl_zero(state->gpr[operation.source_a]);
    break;
  case SemanticOpcode::ExtendSignByte:
    state->gpr[operation.destination] = static_cast<u32>(
        static_cast<s32>(static_cast<s8>(state->gpr[operation.source_a])));
    break;
  case SemanticOpcode::ExtendSignHalfword:
    state->gpr[operation.destination] = static_cast<u32>(
        static_cast<s32>(static_cast<s16>(state->gpr[operation.source_a])));
    break;
  case SemanticOpcode::ShiftLeftWord:
  {
    const u32 amount = state->gpr[operation.source_b];
    state->gpr[operation.destination] =
        (amount & 0x20) != 0 ? 0 : state->gpr[operation.source_a] << (amount & 0x1f);
    break;
  }
  case SemanticOpcode::ShiftRightWord:
  {
    const u32 amount = state->gpr[operation.source_b];
    state->gpr[operation.destination] =
        (amount & 0x20) != 0 ? 0 : state->gpr[operation.source_a] >> (amount & 0x1f);
    break;
  }
  case SemanticOpcode::Count:
    ADD_FAILURE() << "semantic opcode sentinel";
    break;
  }
}

TEST(CI3Lowering, LowersEveryEstablishedForm)
{
  for (std::size_t index = 0; index < static_cast<std::size_t>(SemanticOpcode::Count); ++index)
  {
    const auto opcode = static_cast<SemanticOpcode>(index);
    SCOPED_TRACE(PowerPC::CI3::GetSemanticOperationName(opcode));
    const PPCAnalyst::CodeOp operation = MakeCodeOp(opcode);
    const auto result = LowerOperation(operation);
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(*result, ExpectedRecord(opcode));
    EXPECT_EQ(sizeof(*result), 8U);
  }
}

TEST(CI3Lowering, PreservesImmediateAndRotateFields)
{
  PPCAnalyst::CodeOp addi = MakeCodeOp(SemanticOpcode::AddImmediate);
  addi.inst.RA = 0;
  addi.inst.RD = 31;
  addi.inst.SIMM_16 = static_cast<s16>(0x8000);
  auto lowered_addi = LowerOperation(addi);
  ASSERT_TRUE(lowered_addi);
  EXPECT_EQ(lowered_addi->destination, 31);
  EXPECT_EQ(lowered_addi->source_a, 0);
  EXPECT_EQ(lowered_addi->immediate, 0x8000U);

  PPCAnalyst::CodeOp rotate = MakeCodeOp(SemanticOpcode::RotateLeftWordImmediateAndMask);
  rotate.inst.RA = 7;
  rotate.inst.RS = 7;
  rotate.inst.SH = 31;
  rotate.inst.MB = 29;
  rotate.inst.ME = 2;
  auto lowered_rotate = LowerOperation(rotate);
  ASSERT_TRUE(lowered_rotate);
  EXPECT_EQ(lowered_rotate->destination, 7);
  EXPECT_EQ(lowered_rotate->source_a, 7);
  EXPECT_EQ(lowered_rotate->immediate, PackRotateMask(31, 29, 2));
}

TEST(CI3Lowering, ReportsSpecificRejectionReasons)
{
  GekkoOPInfo info{};
  PPCAnalyst::CodeOp operation{};

  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::MissingOpInfo);

  ConfigureSynthetic(&operation, &info, "addi", OpType::Integer, 0);
  operation.skip = true;
  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::Skipped);

  ConfigureSynthetic(&operation, &info, "mulli", OpType::Integer, 0);
  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::UnsupportedName);

  ConfigureSynthetic(&operation, &info, "addi", OpType::Invalid, 0);
  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::WrongOperationType);

  ConfigureSynthetic(&operation, &info, "andx", OpType::Integer, FL_RC_BIT);
  operation.inst.Rc = 1;
  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::RecordBit);

  ConfigureSynthetic(&operation, &info, "addi", OpType::Integer, FL_SET_CA);
  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::CarryOrOverflow);

  ConfigureSynthetic(&operation, &info, "addi", OpType::Integer, FL_SET_CR0);
  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::ConditionRegister);

  ConfigureSynthetic(&operation, &info, "addi", OpType::Integer, FL_SET_FPRF);
  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::FPRF);

  ConfigureSynthetic(&operation, &info, "addi", OpType::Integer, FL_LOADSTORE);
  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::Memory);

  ConfigureSynthetic(&operation, &info, "addi", OpType::Integer, FL_USE_FPU);
  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::FloatingPoint);

  ConfigureSynthetic(&operation, &info, "addi", OpType::Branch, 0);
  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::BranchOrBlockEnd);

  ConfigureSynthetic(&operation, &info, "addi", OpType::Integer, FL_PROGRAMEXCEPTION);
  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::Exception);

  ConfigureSynthetic(&operation, &info, "addi", OpType::Integer, FL_TIMER);
  EXPECT_EQ(LowerOperation(operation).error(), LoweringRejectReason::TimerOrSystemState);

  for (LoweringRejectReason reason : {
           LoweringRejectReason::BrokenBlock, LoweringRejectReason::Skipped,
           LoweringRejectReason::MissingOpInfo, LoweringRejectReason::UnsupportedName,
           LoweringRejectReason::WrongOperationType, LoweringRejectReason::RecordBit,
           LoweringRejectReason::CarryOrOverflow, LoweringRejectReason::ConditionRegister,
           LoweringRejectReason::FPRF, LoweringRejectReason::Memory,
           LoweringRejectReason::FloatingPoint, LoweringRejectReason::BranchOrBlockEnd,
           LoweringRejectReason::Exception, LoweringRejectReason::TimerOrSystemState,
           LoweringRejectReason::ClassifierRejected,
       })
  {
    EXPECT_STRNE(GetLoweringRejectReasonName(reason), "unknown");
  }
}

TEST(CI3Lowering, PartitionsMaximalRunsAndExactFallbacks)
{
  GekkoOPInfo unsupported_info{};
  PPCAnalyst::CodeOp unsupported{};
  ConfigureSynthetic(&unsupported, &unsupported_info, "mulli", OpType::Integer, 0);

  std::array operations = {
      MakeCodeOp(SemanticOpcode::AddImmediate), MakeCodeOp(SemanticOpcode::OrImmediate),
      unsupported, MakeCodeOp(SemanticOpcode::XorImmediate),
      MakeCodeOp(SemanticOpcode::And), MakeCodeOp(SemanticOpcode::Nor),
  };
  operations[4].skip = true;

  const BlockPartition partition = PartitionBlock(false, operations);
  ASSERT_EQ(partition.entries.size(), 5U);
  EXPECT_EQ(partition.entries[0].kind, PartitionEntryKind::LoweredRun);
  EXPECT_EQ(partition.entries[0].operation_index, 0U);
  EXPECT_EQ(partition.entries[0].operation_count, 2U);
  EXPECT_EQ(partition.entries[1].kind, PartitionEntryKind::Fallback);
  EXPECT_EQ(partition.entries[1].operation_index, 2U);
  EXPECT_EQ(partition.entries[1].rejection, LoweringRejectReason::UnsupportedName);
  EXPECT_EQ(partition.entries[2].kind, PartitionEntryKind::LoweredRun);
  EXPECT_EQ(partition.entries[2].operation_index, 3U);
  EXPECT_EQ(partition.entries[2].operation_count, 1U);
  EXPECT_EQ(partition.entries[3].kind, PartitionEntryKind::Skipped);
  EXPECT_EQ(partition.entries[3].operation_index, 4U);
  EXPECT_EQ(partition.entries[4].kind, PartitionEntryKind::LoweredRun);
  EXPECT_EQ(partition.entries[4].operation_index, 5U);
  EXPECT_EQ(partition.LoweredOperationCount(), 4U);
}

TEST(CI3Lowering, BrokenBlocksForceFallbackWithoutAbsorbingSkippedOps)
{
  std::array operations = {MakeCodeOp(SemanticOpcode::AddImmediate),
                           MakeCodeOp(SemanticOpcode::OrImmediate),
                           MakeCodeOp(SemanticOpcode::XorImmediate)};
  operations[1].skip = true;

  const BlockPartition partition = PartitionBlock(true, operations);
  ASSERT_EQ(partition.entries.size(), 3U);
  EXPECT_EQ(partition.entries[0].kind, PartitionEntryKind::Fallback);
  EXPECT_EQ(partition.entries[0].rejection, LoweringRejectReason::BrokenBlock);
  EXPECT_EQ(partition.entries[1].kind, PartitionEntryKind::Skipped);
  EXPECT_EQ(partition.entries[2].kind, PartitionEntryKind::Fallback);
  EXPECT_EQ(partition.LoweredOperationCount(), 0U);
}

TEST(CI3Lowering, LoweredRecordsRoundTripThroughEstablishedSemantics)
{
  std::array<PPCAnalyst::CodeOp, static_cast<std::size_t>(SemanticOpcode::Count)> operations{};
  for (std::size_t index = 0; index < operations.size(); ++index)
  {
    operations[index] = MakeCodeOp(static_cast<SemanticOpcode>(index));
    operations[index].inst.RA = static_cast<u32>((index + 3) & 0x1f);
    operations[index].inst.RD = operations[index].inst.RA;
    operations[index].inst.RS = static_cast<u32>((index + 4) & 0x1f);
    operations[index].inst.RB = static_cast<u32>((index + 5) & 0x1f);
    operations[index].opinfo = PPCTables::GetOpInfo(operations[index].inst, 0);
  }

  PowerPC::PowerPCState reference{};
  PowerPC::PowerPCState compact{};
  for (std::size_t index = 0; index < std::size(reference.gpr); ++index)
    reference.gpr[index] = compact.gpr[index] = static_cast<u32>(0x9e3779b9U * (index + 1));
  reference.cr.fields = compact.cr.fields;
  reference.xer_ca = compact.xer_ca = 1;
  reference.xer_so_ov = compact.xer_so_ov = 3;

  Core::System& system = Core::System::GetInstance();
  Interpreter interpreter(system, reference, system.GetMMU(), system.GetPowerPC().GetBranchWatch(),
                          system.GetPPCSymbolDB());
  interpreter.Init();

  for (const PPCAnalyst::CodeOp& operation : operations)
  {
    const auto lowered = LowerOperation(operation);
    ASSERT_TRUE(lowered.has_value());
    ExecuteReference(&interpreter, operation);
    ExecuteCompact(&compact, *lowered);
    for (std::size_t reg = 0; reg < std::size(reference.gpr); ++reg)
      EXPECT_EQ(reference.gpr[reg], compact.gpr[reg]) << "GPR " << reg;
    EXPECT_EQ(reference.GetXER().Hex, compact.GetXER().Hex);
    for (std::size_t field = 0; field < std::size(reference.cr.fields); ++field)
      EXPECT_EQ(reference.cr.fields[field], compact.cr.fields[field]);
  }
}

}  // namespace
''',
    )

    cmake = ROOT / "Source/UnitTests/Core/CMakeLists.txt"
    content = cmake.read_text(encoding="utf-8")
    marker = "target_sources(PowerPCTest PRIVATE\n"
    additions = [
        "  ../../Core/Core/PowerPC/CI3/Lowering.cpp\n",
        "  PowerPC/CI3LoweringTest.cpp\n",
    ]
    if any(line not in content for line in additions):
        if marker not in content:
            raise RuntimeError("PowerPCTest target_sources block missing")
        content = content.replace(marker, marker + "".join(line for line in additions if line not in content), 1)
        cmake.write_text(content, encoding="utf-8")

    workflow = ROOT / ".github/workflows/ci3-powerpc-differential.yml"
    workflow_text = workflow.read_text(encoding="utf-8")
    anchor = '      - "Source/UnitTests/Core/PowerPC/CI3IntegerDifferentialTest.cpp"\n'
    new_paths = (
        '      - "Source/Core/Core/PowerPC/CI3/Lowering.cpp"\n'
        '      - "Source/Core/Core/PowerPC/CI3/Lowering.h"\n'
        '      - "Source/Core/Core/PowerPC/CI3/SemanticOp.h"\n'
        '      - "Source/UnitTests/Core/PowerPC/CI3LoweringTest.cpp"\n'
    )
    if 'CI3LoweringTest.cpp' not in workflow_text:
        if workflow_text.count(anchor) < 2:
            raise RuntimeError("CI3 workflow path anchors changed")
        workflow_text = workflow_text.replace(anchor, new_paths + anchor)
    filter_match = re.search(r"--gtest_filter='([^']+)'", workflow_text)
    if not filter_match:
        raise RuntimeError("CI3 gtest filter missing")
    filters = filter_match.group(1).split(":")
    if "CI3Lowering.*" not in filters:
        filters.append("CI3Lowering.*")
        workflow_text = workflow_text[: filter_match.start(1)] + ":".join(filters) + workflow_text[filter_match.end(1) :]
    workflow.write_text(workflow_text, encoding="utf-8")

    write(
        "docs/ci3/experiments/EXP-20260817-006/stage1-lowering-v1.md",
        '''# EXP-20260817-006 Stage 1 — pure lowering and partitioning

**Scope: test-compiled only; no production execution hook.**

This slice introduces a shared eight-byte semantic record, pure lowering from one already analyzed
`PPCAnalyst::CodeOp`, typed rejection reasons, and maximal supported-run partitioning.

Acceptance is authoritative only when the merged `IsSupportedOperation` classifier accepts the
operation. Diagnostic rejection reasons do not create a second acceptance policy.

## Preserved boundaries

- `Lowering.cpp` is compiled into `PowerPCTest`, not the production `core` target.
- `CachedInterpreter`, CPU selection, block cache, dispatch, state materialization, memory, timing,
  exception handling, and settings are unchanged.
- Broken blocks force fallback; skipped operations remain explicit non-executed partition entries.
- Unsupported operations remain exact one-operation fallback entries.
- No benchmark or speed claim is made.

## Validation gate

All 17 established mappings, immediate/rotate packing, rejection categories, mixed partitioning,
broken/skipped behavior, semantic round-trip, and all previous CI3 suites must pass on Linux
x86-64, Linux ARM64, and Apple ARM64 before merge.
''',
    )

    return [
        ".github/workflows/ci3-powerpc-differential.yml",
        "Source/Core/Core/PowerPC/CI3/SemanticOp.h",
        "Source/Core/Core/PowerPC/CI3/Lowering.h",
        "Source/Core/Core/PowerPC/CI3/Lowering.cpp",
        "Source/UnitTests/Core/CMakeLists.txt",
        "Source/UnitTests/Core/PowerPC/CI3LoweringTest.cpp",
        "docs/ci3/experiments/EXP-20260817-006/stage1-lowering-v1.md",
    ]


def generate_subset_screen_packet() -> list[str]:
    ranking = json.loads((EXP006 / "candidate-ranking-v1.json").read_text())
    candidates = ranking.get("candidates", [])
    packet = {
        "schema_version": 1,
        "experiment_id": "EXP-20260817-006",
        "stage": "semantic_screen_source_packet",
        "candidate_count": len(candidates),
        "candidates": [
            {
                "operation_name": item["operation_name"],
                "workload_class_breadth": item["workload_class_breadth"],
                "fixture_breadth": item["fixture_breadth"],
                "total_compilation_count": item["total_compilation_count"],
                "screen_state": "PENDING_PINNED_METADATA_AND_INTERPRETER_REVIEW",
            }
            for item in candidates[:30]
        ],
        "implementation_started": False,
    }
    write(
        "docs/ci3/experiments/EXP-20260817-006/semantic-screen-source-packet-v1.json",
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
    )
    write(
        "docs/ci3/experiments/EXP-20260817-006/stage1-semantic-screen-v1.md",
        '''# EXP-20260817-006 Stage 1 — pinned semantic screening packet

This stage freezes the measured candidate order and opens no implementation path. The next review
must locate each candidate in pinned `PPCTables` metadata and its Interpreter semantic function,
then reject memory, FPU, branch, exception, timer/system-state, carry/overflow, and difficult CR/XER
forms before selecting at most eight operations.

No candidate is selected by rank alone. No profile is rerun, no classifier is changed, and no new
semantic code is introduced in this slice.
''',
    )
    return [
        "docs/ci3/experiments/EXP-20260817-006/semantic-screen-source-packet-v1.json",
        "docs/ci3/experiments/EXP-20260817-006/stage1-semantic-screen-v1.md",
    ]


def generate_redirect_packet() -> list[str]:
    inputs = json.loads((EXP006 / "architecture-cost-inputs-v1.json").read_text())
    packet = {
        "schema_version": 1,
        "experiment_id": "EXP-20260817-006",
        "stage": "redirect_prototype_contract",
        "candidate_architectures": inputs["candidate_architectures"],
        "required_engines": [
            "ci2_like_callback_baseline",
            "dense_generic_decoded_switch",
            "profile_selected_static_superoperations",
            "state_carrying_callback_or_tail_dispatch",
        ],
        "required_outputs": [
            "deterministic_checksum",
            "nanoseconds_per_operation",
            "record_bytes_per_operation",
            "generated_or_static_code_size",
            "state_materialization_boundaries",
        ],
        "production_integration": False,
    }
    write(
        "docs/ci3/experiments/EXP-20260817-006/redirect-prototype-contract-v1.json",
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
    )
    write(
        "docs/ci3/experiments/EXP-20260817-006/stage1-redirect-prototype-v1.md",
        '''# EXP-20260817-006 Stage 1 — architecture redirect prototype contract

The rejected 17-form runtime path remains blocked. This slice freezes the standalone prototype
engines, equivalence checksum, record/code-size outputs, and state-boundary metric before code is
written. The trace mix must be generated only from the committed aggregate histograms and must not
contain guest code or proprietary-derived sequences.

No production Dolphin source path, persistence, memory specialization, or device work is authorized.
''',
    )
    return [
        "docs/ci3/experiments/EXP-20260817-006/redirect-prototype-contract-v1.json",
        "docs/ci3/experiments/EXP-20260817-006/stage1-redirect-prototype-v1.md",
    ]


def generate_distortion_packet() -> list[str]:
    plan = json.loads((EXP006 / "distortion-ablation-plan-v1.json").read_text())
    packet = {
        "schema_version": 1,
        "experiment_id": "EXP-20260817-006",
        "stage": "ablation_implementation_contract",
        "ablations": plan["ablations"],
        "schema_change_allowed": False,
        "privacy_change_allowed": False,
        "frozen_fixture_schedule_required": True,
        "result_version": 2,
        "implementation_started": False,
    }
    write(
        "docs/ci3/experiments/EXP-20260817-006/ablation-implementation-contract-v1.json",
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
    )
    write(
        "docs/ci3/experiments/EXP-20260817-006/stage1-distortion-ablation-v1.md",
        '''# EXP-20260817-006 Stage 1 — profiler ablation implementation contract

This slice freezes the A0–A5 instrumentation modes and the requirement that all enabled modes retain
architectural route equality. No schema field may be dropped merely to improve timing. Any changed
observation contract requires a new schema/protocol version rather than `results-v2`.

The next code PR may add experimental/test-only mode selection and known-answer equality tests, but
must not rerun the frozen schedule until those tests merge.
''',
    )
    return [
        "docs/ci3/experiments/EXP-20260817-006/ablation-implementation-contract-v1.json",
        "docs/ci3/experiments/EXP-20260817-006/stage1-distortion-ablation-v1.md",
    ]


if SLUG == "minimum_lowering_v1":
    GENERATED = generate_minimum_lowering()
elif SLUG == "subset_expansion_v1":
    GENERATED = generate_subset_screen_packet()
elif SLUG == "architecture_redirect_v1":
    GENERATED = generate_redirect_packet()
elif SLUG == "distortion_remediation_v1":
    GENERATED = generate_distortion_packet()
else:
    raise SystemExit(f"unsupported Stage 1 action: {SLUG}")

write(
    "docs/ci3/experiments/EXP-20260817-006/stage1-manifest.json",
    json.dumps(
        {
            "schema_version": 1,
            "experiment_id": "EXP-20260817-006",
            "action_slug": SLUG,
            "generated_paths": GENERATED,
            "production_runtime_hook_added": False,
            "performance_measurement_started": False,
        },
        indent=2,
        sort_keys=True,
    )
    + "\n",
)

(ROOT / "Tools/ci3/exp006/generate_stage1.py").unlink()
(ROOT / ".github/workflows/ci3-exp006-stage1.yml").unlink()
print(SLUG)
