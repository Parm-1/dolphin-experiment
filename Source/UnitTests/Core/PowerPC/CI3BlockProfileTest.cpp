// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <array>
#include <cstddef>
#include <string_view>

#include "Common/BitSet.h"
#include "Common/CommonTypes.h"
#include "Core/PowerPC/CI3/BlockProfile.h"
#include "Core/PowerPC/PPCAnalyst.h"
#include "Core/PowerPC/PPCTables.h"

#include <gtest/gtest.h>

namespace
{

using PowerPC::CI3::BlockProfileAccumulator;
using PowerPC::CI3::GPRReuseDistance;
using PowerPC::CI3::IsSupportedOperation;
using PowerPC::CI3::SemanticFeature;

template <typename Enum>
constexpr std::size_t ToIndex(Enum value)
{
  return static_cast<std::size_t>(value);
}

void ConfigureOperation(PPCAnalyst::CodeOp* operation, GekkoOPInfo* info, const char* name,
                        OpType type, u64 flags, BitSet32 regs_in = {}, BitSet32 regs_out = {})
{
  *info = GekkoOPInfo{name, type, 1, flags, nullptr};
  *operation = PPCAnalyst::CodeOp{};
  operation->opinfo = info;
  operation->regsIn = regs_in;
  operation->regsOut = regs_out;
}

TEST(CI3BlockProfile, SupportedClassifierMatchesEstablishedSubset)
{
  constexpr std::array<std::string_view, 17> names = {
      "addi",    "ori",     "oris",    "xori",    "xoris",  "rlwinmx",
      "andx",    "andcx",   "orx",     "orcx",    "xorx",   "norx",
      "cntlzwx", "extsbx",  "extshx",  "slwx",    "srwx",
  };

  for (const std::string_view name : names)
  {
    SCOPED_TRACE(name);

    const bool has_record_bit =
        name != "addi" && name != "ori" && name != "oris" && name != "xori" && name != "xoris";
    const u64 flags = has_record_bit ? static_cast<u64>(FL_RC_BIT) : 0;

    GekkoOPInfo info{};
    PPCAnalyst::CodeOp operation{};
    ConfigureOperation(&operation, &info, name.data(), OpType::Integer, flags);

    EXPECT_TRUE(IsSupportedOperation(operation));

    operation.inst.Rc = 1;
    EXPECT_EQ(IsSupportedOperation(operation), !has_record_bit);
  }
}

TEST(CI3BlockProfile, SupportedClassifierRejectsSemanticBoundaries)
{
  GekkoOPInfo info{};
  PPCAnalyst::CodeOp operation{};

  ConfigureOperation(&operation, &info, "mulli", OpType::Integer, 0);
  EXPECT_FALSE(IsSupportedOperation(operation));

  ConfigureOperation(&operation, &info, "addi", OpType::Load, 0);
  EXPECT_FALSE(IsSupportedOperation(operation));

  ConfigureOperation(&operation, &info, "addi", OpType::Integer, FL_LOADSTORE);
  EXPECT_FALSE(IsSupportedOperation(operation));

  ConfigureOperation(&operation, &info, "andx", OpType::Integer, FL_RC_BIT);
  operation.inst.Rc = 1;
  EXPECT_FALSE(IsSupportedOperation(operation));

  ConfigureOperation(&operation, &info, "addi", OpType::Integer, 0);
  operation.skip = true;
  EXPECT_FALSE(IsSupportedOperation(operation));

  ConfigureOperation(&operation, &info, "addi", OpType::Integer, 0);
  operation.canCauseException = true;
  EXPECT_FALSE(IsSupportedOperation(operation));

  ConfigureOperation(&operation, &info, "addi", OpType::Integer, 0);
  operation.crOut[0] = true;
  EXPECT_FALSE(IsSupportedOperation(operation));

  ConfigureOperation(&operation, &info, "addi", OpType::Integer, 0);
  operation.outputCA = true;
  EXPECT_FALSE(IsSupportedOperation(operation));

  ConfigureOperation(&operation, &info, "addi", OpType::Integer, 0);
  operation.wantsCA = true;
  operation.wantsFPRF = true;
  EXPECT_TRUE(IsSupportedOperation(operation));
}

TEST(CI3BlockProfile, LivenessAnnotationsDoNotMasqueradeAsSemantics)
{
  GekkoOPInfo info{};
  PPCAnalyst::CodeOp operation{};
  ConfigureOperation(&operation, &info, "addi", OpType::Integer, FL_OUT_D | FL_IN_A0);
  operation.wantsCA = true;
  operation.wantsFPRF = true;
  operation.wantsCR[0] = true;

  BlockProfileAccumulator accumulator;
  accumulator.ObserveBlock(false, std::span<const PPCAnalyst::CodeOp>{&operation, 1});
  const auto& data = accumulator.GetData();

  EXPECT_EQ(data.supported_operations, 1U);
  EXPECT_EQ(data.semantic_feature_counts[ToIndex(SemanticFeature::Carry)], 0U);
  EXPECT_EQ(data.semantic_feature_counts[ToIndex(SemanticFeature::FPRF)], 0U);
  EXPECT_EQ(data.semantic_feature_counts[ToIndex(SemanticFeature::ConditionRegister)], 0U);
}

TEST(CI3BlockProfile, AccumulatesKnownAnswerBlock)
{
  std::array<GekkoOPInfo, 6> info{};
  std::array<PPCAnalyst::CodeOp, 6> operations{};

  ConfigureOperation(&operations[0], &info[0], "addi", OpType::Integer, FL_OUT_D | FL_IN_A0,
                     {}, BitSet32{3});
  operations[0].gprWillBeRead = BitSet32{3, 4};

  ConfigureOperation(&operations[1], &info[1], "ori", OpType::Integer, FL_OUT_A | FL_IN_S,
                     BitSet32{3}, BitSet32{4});
  operations[1].gprWillBeRead = BitSet32{4, 5, 6};

  ConfigureOperation(&operations[2], &info[2], "xori", OpType::Integer, FL_OUT_A | FL_IN_S,
                     BitSet32{4}, BitSet32{7});
  operations[2].skip = true;
  operations[2].gprWillBeRead = BitSet32{31};

  ConfigureOperation(&operations[3], &info[3], "lwz", OpType::Load,
                     FL_OUT_D | FL_IN_A0 | FL_LOADSTORE, BitSet32{4}, BitSet32{5});
  operations[3].canCauseException = true;
  operations[3].gprWillBeRead = BitSet32{5, 6};

  ConfigureOperation(&operations[4], &info[4], "xorx", OpType::Integer,
                     FL_OUT_A | FL_IN_SB | FL_RC_BIT, BitSet32{4, 5}, BitSet32{6});
  operations[4].gprWillBeRead = BitSet32{6};

  ConfigureOperation(&operations[5], &info[5], "bx", OpType::Branch, FL_ENDBLOCK);
  operations[5].canEndBlock = true;

  BlockProfileAccumulator accumulator;
  accumulator.ObserveBlock(true, operations);
  const auto& data = accumulator.GetData();

  EXPECT_EQ(data.observed_blocks, 1U);
  EXPECT_EQ(data.broken_blocks, 1U);
  EXPECT_EQ(data.analyzed_operations, 6U);
  EXPECT_EQ(data.eligible_operations, 5U);
  EXPECT_EQ(data.skipped_operations, 1U);
  EXPECT_EQ(data.supported_operations, 3U);
  EXPECT_EQ(data.blocks_with_supported_operations, 1U);
  EXPECT_EQ(data.fully_supported_eligible_blocks, 0U);

  EXPECT_EQ(data.analyzed_block_lengths.at(6), 1U);
  EXPECT_EQ(data.eligible_block_lengths.at(5), 1U);
  EXPECT_EQ(data.supported_run_lengths.at(1), 1U);
  EXPECT_EQ(data.supported_run_lengths.at(2), 1U);

  EXPECT_EQ(data.opcode_counts.size(), 6U);
  EXPECT_EQ(data.opcode_counts.at("addi"), 1U);
  EXPECT_EQ(data.opcode_counts.at("xori"), 1U);
  EXPECT_EQ(data.opcode_counts.at("bx"), 1U);

  EXPECT_EQ(data.gpr_reads_per_operation[0], 2U);
  EXPECT_EQ(data.gpr_reads_per_operation[1], 2U);
  EXPECT_EQ(data.gpr_reads_per_operation[2], 1U);
  EXPECT_EQ(data.gpr_writes_per_operation[0], 1U);
  EXPECT_EQ(data.gpr_writes_per_operation[1], 4U);

  EXPECT_EQ(data.maximum_live_future_gprs, 3U);
  EXPECT_EQ(data.maximum_live_future_gprs_per_block[3], 1U);

  EXPECT_EQ(data.semantic_feature_counts[ToIndex(SemanticFeature::LoadStore)], 1U);
  EXPECT_EQ(data.semantic_feature_counts[ToIndex(SemanticFeature::Exception)], 1U);
  EXPECT_EQ(data.semantic_feature_counts[ToIndex(SemanticFeature::BlockEnd)], 1U);
  EXPECT_EQ(data.semantic_feature_counts[ToIndex(SemanticFeature::Branch)], 1U);
  EXPECT_EQ(data.semantic_feature_counts[ToIndex(SemanticFeature::ConditionRegister)], 0U);

  EXPECT_EQ(data.gpr_reuse_distance_counts[ToIndex(GPRReuseDistance::Distance1)], 3U);
  EXPECT_EQ(data.gpr_reuse_distance_counts[ToIndex(GPRReuseDistance::Distance2)], 1U);
  EXPECT_EQ(
      data.gpr_reuse_distance_counts[ToIndex(GPRReuseDistance::ExternalOrEarlierBlock)], 0U);
}

TEST(CI3BlockProfile, TracksReuseDistanceBuckets)
{
  constexpr std::size_t operation_count = 20;
  std::array<GekkoOPInfo, operation_count> info{};
  std::array<PPCAnalyst::CodeOp, operation_count> operations{};

  for (std::size_t i = 0; i < operation_count; ++i)
    ConfigureOperation(&operations[i], &info[i], "mulli", OpType::Integer, 0);

  operations[0].regsOut = BitSet32{1, 2, 3, 4, 5, 6};
  operations[1].regsIn = BitSet32{1};
  operations[2].regsIn = BitSet32{2};
  operations[3].regsIn = BitSet32{3};
  operations[5].regsIn = BitSet32{4};
  operations[9].regsIn = BitSet32{5};
  operations[17].regsIn = BitSet32{6};
  operations[19].regsIn = BitSet32{7};

  BlockProfileAccumulator accumulator;
  accumulator.ObserveBlock(false, operations);
  const auto& counts = accumulator.GetData().gpr_reuse_distance_counts;

  EXPECT_EQ(counts[ToIndex(GPRReuseDistance::Distance1)], 1U);
  EXPECT_EQ(counts[ToIndex(GPRReuseDistance::Distance2)], 1U);
  EXPECT_EQ(counts[ToIndex(GPRReuseDistance::Distance3To4)], 1U);
  EXPECT_EQ(counts[ToIndex(GPRReuseDistance::Distance5To8)], 1U);
  EXPECT_EQ(counts[ToIndex(GPRReuseDistance::Distance9To16)], 1U);
  EXPECT_EQ(counts[ToIndex(GPRReuseDistance::Distance17Plus)], 1U);
  EXPECT_EQ(counts[ToIndex(GPRReuseDistance::ExternalOrEarlierBlock)], 1U);
}

TEST(CI3BlockProfile, WholeXERAccessesCountAsCarryBoundaries)
{
  std::array<GekkoOPInfo, 2> info{};
  std::array<PPCAnalyst::CodeOp, 2> operations{};

  ConfigureOperation(&operations[0], &info[0], "mfspr", OpType::SPR, 0);
  operations[0].inst.OPCD = 31;
  operations[0].inst.SUBOP10 = 339;
  operations[0].inst.SPRU = 0;
  operations[0].inst.SPRL = SPR_XER;

  ConfigureOperation(&operations[1], &info[1], "mtspr", OpType::SPR, 0);
  operations[1].inst.OPCD = 31;
  operations[1].inst.SUBOP10 = 467;
  operations[1].inst.SPRU = 0;
  operations[1].inst.SPRL = SPR_XER;

  BlockProfileAccumulator accumulator;
  accumulator.ObserveBlock(false, operations);
  const auto& counts = accumulator.GetData().semantic_feature_counts;

  EXPECT_EQ(counts[ToIndex(SemanticFeature::Carry)], 2U);
  EXPECT_EQ(counts[ToIndex(SemanticFeature::SystemState)], 2U);
}

TEST(CI3BlockProfile, CountsOverlappingSemanticFeatures)
{
  std::array<GekkoOPInfo, 2> info{};
  std::array<PPCAnalyst::CodeOp, 2> operations{};

  ConfigureOperation(&operations[0], &info[0], "synthetic-system-fp", OpType::SystemFP,
                     FL_LOADSTORE | FL_USE_FPU | FL_SET_CA | FL_SET_OE | FL_SET_CR0 |
                         FL_SET_FPRF | FL_TIMER | FL_SET_MSR);
  operations[0].inst.OE = 1;
  operations[0].canEndBlock = true;
  operations[0].canCauseException = true;
  operations[0].outputFPRF = true;
  operations[0].crIn[0] = true;

  ConfigureOperation(&operations[1], &info[1], "synthetic-branch", OpType::Branch, 0);

  BlockProfileAccumulator accumulator;
  accumulator.ObserveBlock(false, operations);
  const auto& counts = accumulator.GetData().semantic_feature_counts;

  EXPECT_EQ(counts[ToIndex(SemanticFeature::LoadStore)], 1U);
  EXPECT_EQ(counts[ToIndex(SemanticFeature::FloatingPoint)], 1U);
  EXPECT_EQ(counts[ToIndex(SemanticFeature::BlockEnd)], 1U);
  EXPECT_EQ(counts[ToIndex(SemanticFeature::Exception)], 1U);
  EXPECT_EQ(counts[ToIndex(SemanticFeature::Carry)], 1U);
  EXPECT_EQ(counts[ToIndex(SemanticFeature::Overflow)], 1U);
  EXPECT_EQ(counts[ToIndex(SemanticFeature::ConditionRegister)], 1U);
  EXPECT_EQ(counts[ToIndex(SemanticFeature::FPRF)], 1U);
  EXPECT_EQ(counts[ToIndex(SemanticFeature::SystemState)], 1U);
  EXPECT_EQ(counts[ToIndex(SemanticFeature::Branch)], 1U);
}

TEST(CI3BlockProfile, MergeIsOrderIndependent)
{
  std::array<GekkoOPInfo, 2> info{};
  std::array<PPCAnalyst::CodeOp, 2> supported_operations{};
  ConfigureOperation(&supported_operations[0], &info[0], "addi", OpType::Integer,
                     FL_OUT_D | FL_IN_A0, {}, BitSet32{3});
  ConfigureOperation(&supported_operations[1], &info[1], "ori", OpType::Integer,
                     FL_OUT_A | FL_IN_S, BitSet32{3}, BitSet32{4});

  GekkoOPInfo unsupported_info{};
  PPCAnalyst::CodeOp unsupported_operation{};
  ConfigureOperation(&unsupported_operation, &unsupported_info, "lwz", OpType::Load,
                     FL_LOADSTORE, BitSet32{4}, BitSet32{5});
  unsupported_operation.canCauseException = true;

  BlockProfileAccumulator left;
  left.ObserveBlock(false, supported_operations);
  BlockProfileAccumulator right;
  right.ObserveBlock(true, std::span<const PPCAnalyst::CodeOp>{&unsupported_operation, 1});

  BlockProfileAccumulator left_then_right = left;
  left_then_right.Merge(right);

  BlockProfileAccumulator right_then_left = right;
  right_then_left.Merge(left);

  EXPECT_EQ(left_then_right.GetData(), right_then_left.GetData());
  EXPECT_EQ(left_then_right.GetData().observed_blocks, 2U);
  EXPECT_EQ(left_then_right.GetData().fully_supported_eligible_blocks, 1U);
}

TEST(CI3BlockProfile, BrokenBlocksAreNotFullySupported)
{
  GekkoOPInfo info{};
  PPCAnalyst::CodeOp operation{};
  ConfigureOperation(&operation, &info, "addi", OpType::Integer, FL_OUT_D | FL_IN_A0);

  BlockProfileAccumulator accumulator;
  accumulator.ObserveBlock(true, std::span<const PPCAnalyst::CodeOp>{&operation, 1});

  const auto& data = accumulator.GetData();
  EXPECT_EQ(data.broken_blocks, 1U);
  EXPECT_EQ(data.supported_operations, 1U);
  EXPECT_EQ(data.blocks_with_supported_operations, 1U);
  EXPECT_EQ(data.fully_supported_eligible_blocks, 0U);
}

TEST(CI3BlockProfile, EmptyAndSkippedBlocksAreNotFullySupported)
{
  BlockProfileAccumulator accumulator;
  accumulator.ObserveBlock(false, std::span<const PPCAnalyst::CodeOp>{});

  GekkoOPInfo info{};
  PPCAnalyst::CodeOp skipped{};
  ConfigureOperation(&skipped, &info, "addi", OpType::Integer, FL_OUT_D | FL_IN_A0);
  skipped.skip = true;
  accumulator.ObserveBlock(false, std::span<const PPCAnalyst::CodeOp>{&skipped, 1});

  const auto& data = accumulator.GetData();
  EXPECT_EQ(data.observed_blocks, 2U);
  EXPECT_EQ(data.eligible_operations, 0U);
  EXPECT_EQ(data.skipped_operations, 1U);
  EXPECT_EQ(data.fully_supported_eligible_blocks, 0U);
  EXPECT_EQ(data.eligible_block_lengths.at(0), 2U);
  EXPECT_EQ(data.maximum_live_future_gprs_per_block[0], 2U);
}

}  // namespace
