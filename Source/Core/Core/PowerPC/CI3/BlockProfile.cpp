// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include "Core/PowerPC/CI3/BlockProfile.h"

#include <algorithm>
#include <array>
#include <string_view>

#include "Core/PowerPC/PPCTables.h"

namespace PowerPC::CI3
{
namespace
{

constexpr std::array<std::string_view, 17> SUPPORTED_OPERATION_NAMES = {
    "addi",    "ori",     "oris",    "xori",    "xoris",  "rlwinmx",
    "andx",    "andcx",   "orx",     "orcx",    "xorx",   "norx",
    "cntlzwx", "extsbx",  "extshx",  "slwx",    "srwx",
};

constexpr u64 DISALLOWED_SUPPORTED_FLAGS =
    FL_SET_CA | FL_READ_CA | FL_TIMER | FL_CHECKEXCEPTIONS | FL_USE_FPU | FL_LOADSTORE |
    FL_SET_FPRF | FL_READ_FPRF | FL_SET_OE | FL_PROGRAMEXCEPTION | FL_FLOAT_EXCEPTION |
    FL_FLOAT_DIV | FL_SET_CRx | FL_READ_CRx | FL_SET_MSR | FL_ENDBLOCK;

template <typename Enum>
constexpr std::size_t ToIndex(Enum value)
{
  return static_cast<std::size_t>(value);
}

std::string_view GetOperationName(const PPCAnalyst::CodeOp& operation)
{
  if (operation.opinfo == nullptr || operation.opinfo->opname == nullptr)
    return "<missing-opinfo>";

  return operation.opinfo->opname;
}

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

void IncrementSemanticFeature(BlockProfileData* data, SemanticFeature feature)
{
  ++data->semantic_feature_counts[ToIndex(feature)];
}

void ObserveSemanticFeatures(BlockProfileData* data, const PPCAnalyst::CodeOp& operation)
{
  const GekkoOPInfo* const info = operation.opinfo;
  const u64 flags = info == nullptr ? 0 : info->flags;
  const OpType type = info == nullptr ? OpType::Invalid : info->type;

  if ((flags & FL_LOADSTORE) != 0 || IsLoadStoreType(type))
    IncrementSemanticFeature(data, SemanticFeature::LoadStore);

  if ((flags & FL_USE_FPU) != 0 || IsFloatingPointType(type))
    IncrementSemanticFeature(data, SemanticFeature::FloatingPoint);

  if (operation.canEndBlock)
    IncrementSemanticFeature(data, SemanticFeature::BlockEnd);

  if (operation.canCauseException || (flags & FL_CHECKEXCEPTIONS) != 0)
    IncrementSemanticFeature(data, SemanticFeature::Exception);

  if ((flags & (FL_SET_CA | FL_READ_CA)) != 0 || operation.wantsCAInFlags ||
      operation.outputCA)
  {
    IncrementSemanticFeature(data, SemanticFeature::Carry);
  }

  if ((flags & FL_SET_OE) != 0 && operation.inst.OE != 0)
    IncrementSemanticFeature(data, SemanticFeature::Overflow);

  if ((flags & (FL_SET_CRx | FL_READ_CRx)) != 0 ||
      (((flags & (FL_RC_BIT | FL_RC_BIT_F)) != 0) && operation.inst.Rc != 0) ||
      static_cast<bool>(operation.crIn) || static_cast<bool>(operation.crOut))
  {
    IncrementSemanticFeature(data, SemanticFeature::ConditionRegister);
  }

  if ((flags & (FL_SET_FPRF | FL_READ_FPRF)) != 0 || operation.outputFPRF)
  {
    IncrementSemanticFeature(data, SemanticFeature::FPRF);
  }

  if (IsSystemStateType(type) || (flags & (FL_TIMER | FL_SET_MSR)) != 0)
    IncrementSemanticFeature(data, SemanticFeature::SystemState);

  if (type == OpType::Branch)
    IncrementSemanticFeature(data, SemanticFeature::Branch);
}

GPRReuseDistance GetReuseDistance(u32 distance)
{
  if (distance == 1)
    return GPRReuseDistance::Distance1;
  if (distance == 2)
    return GPRReuseDistance::Distance2;
  if (distance <= 4)
    return GPRReuseDistance::Distance3To4;
  if (distance <= 8)
    return GPRReuseDistance::Distance5To8;
  if (distance <= 16)
    return GPRReuseDistance::Distance9To16;
  return GPRReuseDistance::Distance17Plus;
}

template <typename Key>
void MergeMap(std::map<Key, u64>* destination, const std::map<Key, u64>& source)
{
  for (const auto& [key, count] : source)
    (*destination)[key] += count;
}

template <std::size_t Size>
void MergeArray(std::array<u64, Size>* destination, const std::array<u64, Size>& source)
{
  for (std::size_t i = 0; i < Size; ++i)
    (*destination)[i] += source[i];
}

}  // namespace

bool IsSupportedOperation(const PPCAnalyst::CodeOp& operation)
{
  if (operation.skip || operation.opinfo == nullptr || operation.opinfo->opname == nullptr ||
      operation.opinfo->type != OpType::Integer)
  {
    return false;
  }

  const std::string_view name = operation.opinfo->opname;
  if (std::ranges::find(SUPPORTED_OPERATION_NAMES, name) == SUPPORTED_OPERATION_NAMES.end())
    return false;

  const u64 flags = operation.opinfo->flags;
  if ((flags & DISALLOWED_SUPPORTED_FLAGS) != 0)
    return false;

  if ((flags & (FL_RC_BIT | FL_RC_BIT_F)) != 0 && operation.inst.Rc != 0)
    return false;

  if (operation.canEndBlock || operation.canCauseException ||
      static_cast<bool>(operation.crIn) || static_cast<bool>(operation.crOut) ||
      operation.outputFPRF || operation.wantsCAInFlags || operation.outputCA)
  {
    return false;
  }

  return true;
}

void BlockProfileAccumulator::ObserveBlock(bool broken,
                                           std::span<const PPCAnalyst::CodeOp> operations)
{
  ++m_data.observed_blocks;
  if (broken)
    ++m_data.broken_blocks;

  const u32 analyzed_length = static_cast<u32>(operations.size());
  m_data.analyzed_operations += analyzed_length;
  ++m_data.analyzed_block_lengths[analyzed_length];

  std::array<int, GPR_COUNT> last_write_index;
  last_write_index.fill(-1);

  u32 eligible_index = 0;
  u32 eligible_length = 0;
  u32 supported_operations = 0;
  u32 current_supported_run = 0;
  u32 maximum_live_future_gprs = 0;

  const auto finish_supported_run = [&] {
    if (current_supported_run != 0)
    {
      ++m_data.supported_run_lengths[current_supported_run];
      current_supported_run = 0;
    }
  };

  for (const PPCAnalyst::CodeOp& operation : operations)
  {
    ++m_data.opcode_counts[std::string{GetOperationName(operation)}];

    if (operation.skip)
    {
      ++m_data.skipped_operations;
      continue;
    }

    ++eligible_length;
    ++m_data.eligible_operations;

    const u32 read_count = operation.regsIn.Count();
    const u32 write_count = operation.regsOut.Count();
    ++m_data.gpr_reads_per_operation[read_count];
    ++m_data.gpr_writes_per_operation[write_count];

    const u32 live_future_gprs = operation.gprWillBeRead.Count();
    maximum_live_future_gprs = std::max(maximum_live_future_gprs, live_future_gprs);

    ObserveSemanticFeatures(&m_data, operation);

    for (const int reg : operation.regsIn)
    {
      const int producer_index = last_write_index[reg];
      if (producer_index < 0)
      {
        ++m_data.gpr_reuse_distance_counts[ToIndex(GPRReuseDistance::ExternalOrEarlierBlock)];
      }
      else
      {
        const u32 distance = eligible_index - static_cast<u32>(producer_index);
        ++m_data.gpr_reuse_distance_counts[ToIndex(GetReuseDistance(distance))];
      }
    }

    for (const int reg : operation.regsOut)
      last_write_index[reg] = static_cast<int>(eligible_index);

    if (IsSupportedOperation(operation))
    {
      ++supported_operations;
      ++m_data.supported_operations;
      ++current_supported_run;
    }
    else
    {
      finish_supported_run();
    }

    ++eligible_index;
  }

  finish_supported_run();

  ++m_data.eligible_block_lengths[eligible_length];
  m_data.maximum_live_future_gprs =
      std::max(m_data.maximum_live_future_gprs, maximum_live_future_gprs);
  ++m_data.maximum_live_future_gprs_per_block[maximum_live_future_gprs];

  if (supported_operations != 0)
    ++m_data.blocks_with_supported_operations;

  if (!broken && eligible_length != 0 && supported_operations == eligible_length)
    ++m_data.fully_supported_eligible_blocks;
}

void BlockProfileAccumulator::Merge(const BlockProfileAccumulator& other)
{
  const BlockProfileData& source = other.m_data;

  m_data.observed_blocks += source.observed_blocks;
  m_data.broken_blocks += source.broken_blocks;
  m_data.analyzed_operations += source.analyzed_operations;
  m_data.eligible_operations += source.eligible_operations;
  m_data.skipped_operations += source.skipped_operations;
  m_data.supported_operations += source.supported_operations;
  m_data.blocks_with_supported_operations += source.blocks_with_supported_operations;
  m_data.fully_supported_eligible_blocks += source.fully_supported_eligible_blocks;
  m_data.maximum_live_future_gprs =
      std::max(m_data.maximum_live_future_gprs, source.maximum_live_future_gprs);

  MergeMap(&m_data.analyzed_block_lengths, source.analyzed_block_lengths);
  MergeMap(&m_data.eligible_block_lengths, source.eligible_block_lengths);
  MergeMap(&m_data.supported_run_lengths, source.supported_run_lengths);
  MergeMap(&m_data.opcode_counts, source.opcode_counts);

  MergeArray(&m_data.gpr_reads_per_operation, source.gpr_reads_per_operation);
  MergeArray(&m_data.gpr_writes_per_operation, source.gpr_writes_per_operation);
  MergeArray(&m_data.maximum_live_future_gprs_per_block,
             source.maximum_live_future_gprs_per_block);
  MergeArray(&m_data.semantic_feature_counts, source.semantic_feature_counts);
  MergeArray(&m_data.gpr_reuse_distance_counts, source.gpr_reuse_distance_counts);
}

}  // namespace PowerPC::CI3
