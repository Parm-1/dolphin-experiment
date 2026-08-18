// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <limits>
#include <string>

#include "Core/PowerPC/CI3/BlockProfileJson.h"

#include <gtest/gtest.h>

namespace
{

using PowerPC::CI3::BlockProfileData;
using PowerPC::CI3::GPRReuseDistance;
using PowerPC::CI3::SemanticFeature;
using PowerPC::CI3::SerializeBlockProfile;

template <typename Enum>
constexpr std::size_t ToIndex(Enum value)
{
  return static_cast<std::size_t>(value);
}

TEST(CI3BlockProfileJson, SerializesDeterministicApprovedSchema)
{
  BlockProfileData data;
  data.observed_blocks = 2;
  data.broken_blocks = 1;
  data.analyzed_operations = 7;
  data.eligible_operations = 6;
  data.skipped_operations = 1;
  data.supported_operations = 4;
  data.blocks_with_supported_operations = 2;
  data.fully_supported_eligible_blocks = 1;
  data.maximum_live_future_gprs = 3;
  data.analyzed_block_lengths.emplace(2, 1);
  data.analyzed_block_lengths.emplace(5, 1);
  data.eligible_block_lengths.emplace(2, 1);
  data.eligible_block_lengths.emplace(4, 1);
  data.supported_run_lengths.emplace(1, 2);
  data.supported_run_lengths.emplace(2, 1);
  data.opcode_counts.emplace("addi", 2);
  data.opcode_counts.emplace("quoted\"\\\n", 1);
  data.gpr_reads_per_operation[0] = 2;
  data.gpr_reads_per_operation[1] = 4;
  data.gpr_writes_per_operation[0] = 1;
  data.gpr_writes_per_operation[1] = 5;
  data.maximum_live_future_gprs_per_block[2] = 1;
  data.maximum_live_future_gprs_per_block[3] = 1;
  data.semantic_feature_counts[ToIndex(SemanticFeature::LoadStore)] = 1;
  data.semantic_feature_counts[ToIndex(SemanticFeature::Branch)] = 2;
  data.gpr_reuse_distance_counts[ToIndex(GPRReuseDistance::Distance1)] = 3;
  data.gpr_reuse_distance_counts[ToIndex(GPRReuseDistance::ExternalOrEarlierBlock)] = 4;

  const std::string first = SerializeBlockProfile(data);
  const std::string second = SerializeBlockProfile(data);

  EXPECT_EQ(first, second);
  EXPECT_NE(first.find("\"schema\": \"ci3-powerpc-block-profile\""), std::string::npos);
  EXPECT_NE(first.find("\"observation_unit\": "
                       "\"successful_cached_interpreter_block_compilation\""),
            std::string::npos);
  EXPECT_NE(first.find("\"execution_weighted\": false"), std::string::npos);
  EXPECT_NE(first.find("\"unique_blocks\": false"), std::string::npos);
  EXPECT_NE(first.find("\"duplicate_compilations_possible\": true"), std::string::npos);
  EXPECT_NE(first.find("\"quoted\\\"\\\\\\n\": 1"), std::string::npos);
  EXPECT_NE(first.find("\"external_or_earlier_block\": 4"), std::string::npos);
  EXPECT_EQ(first.back(), '\n');
}

TEST(CI3BlockProfileJson, PreservesFullUnsignedIntegerPrecision)
{
  BlockProfileData data;
  data.observed_blocks = std::numeric_limits<u64>::max();

  const std::string json = SerializeBlockProfile(data);
  EXPECT_NE(json.find("18446744073709551615"), std::string::npos);
}

TEST(CI3BlockProfileJson, ContainsNoRawGuestDataFields)
{
  const std::string json = SerializeBlockProfile(BlockProfileData{});

  EXPECT_EQ(json.find("address"), std::string::npos);
  EXPECT_EQ(json.find("instruction_word"), std::string::npos);
  EXPECT_EQ(json.find("disassembly"), std::string::npos);
  EXPECT_EQ(json.find("title_id"), std::string::npos);
  EXPECT_EQ(json.find("filename"), std::string::npos);
  EXPECT_EQ(json.find("save"), std::string::npos);
}

}  // namespace
