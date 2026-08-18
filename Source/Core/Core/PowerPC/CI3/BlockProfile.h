// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include <array>
#include <cstddef>
#include <map>
#include <span>
#include <string>

#include "Common/CommonTypes.h"
#include "Core/PowerPC/PPCAnalyst.h"

namespace PowerPC::CI3
{

enum class SemanticFeature : u8
{
  LoadStore,
  FloatingPoint,
  BlockEnd,
  Exception,
  Carry,
  Overflow,
  ConditionRegister,
  FPRF,
  SystemState,
  Branch,
  Count,
};

enum class GPRReuseDistance : u8
{
  Distance1,
  Distance2,
  Distance3To4,
  Distance5To8,
  Distance9To16,
  Distance17Plus,
  ExternalOrEarlierBlock,
  Count,
};

constexpr std::size_t GPR_COUNT = 32;
constexpr std::size_t GPR_CARDINALITY_BUCKETS = GPR_COUNT + 1;

struct BlockProfileData
{
  u64 observed_blocks = 0;
  u64 broken_blocks = 0;
  u64 analyzed_operations = 0;
  u64 eligible_operations = 0;
  u64 skipped_operations = 0;
  u64 supported_operations = 0;
  u64 blocks_with_supported_operations = 0;
  u64 fully_supported_eligible_blocks = 0;
  u32 maximum_live_future_gprs = 0;

  std::map<u32, u64> analyzed_block_lengths;
  std::map<u32, u64> eligible_block_lengths;
  std::map<u32, u64> supported_run_lengths;
  std::map<std::string, u64> opcode_counts;

  std::array<u64, GPR_CARDINALITY_BUCKETS> gpr_reads_per_operation{};
  std::array<u64, GPR_CARDINALITY_BUCKETS> gpr_writes_per_operation{};
  std::array<u64, GPR_CARDINALITY_BUCKETS> maximum_live_future_gprs_per_block{};
  std::array<u64, static_cast<std::size_t>(SemanticFeature::Count)> semantic_feature_counts{};
  std::array<u64, static_cast<std::size_t>(GPRReuseDistance::Count)>
      gpr_reuse_distance_counts{};

  bool operator==(const BlockProfileData&) const = default;
};

bool IsSupportedOperation(const PPCAnalyst::CodeOp& operation);

class BlockProfileAccumulator
{
public:
  void ObserveBlock(bool broken, std::span<const PPCAnalyst::CodeOp> operations);
  void Merge(const BlockProfileAccumulator& other);

  const BlockProfileData& GetData() const { return m_data; }

private:
  BlockProfileData m_data;
};

}  // namespace PowerPC::CI3
