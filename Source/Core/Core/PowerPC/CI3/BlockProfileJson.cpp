// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include "Core/PowerPC/CI3/BlockProfileJson.h"

#include <array>
#include <charconv>
#include <map>
#include <string_view>

namespace PowerPC::CI3
{
namespace
{

template <typename Integer>
void AppendInteger(std::string* output, Integer value)
{
  std::array<char, 32> buffer{};
  const auto [end, error] = std::to_chars(buffer.data(), buffer.data() + buffer.size(), value);
  if (error == std::errc{})
    output->append(buffer.data(), end);
}

void AppendJsonString(std::string* output, std::string_view value)
{
  constexpr std::string_view hex = "0123456789abcdef";

  output->push_back('"');
  for (const unsigned char character : value)
  {
    switch (character)
    {
    case '"':
      output->append("\\\"");
      break;
    case '\\':
      output->append("\\\\");
      break;
    case '\b':
      output->append("\\b");
      break;
    case '\f':
      output->append("\\f");
      break;
    case '\n':
      output->append("\\n");
      break;
    case '\r':
      output->append("\\r");
      break;
    case '\t':
      output->append("\\t");
      break;
    default:
      if (character < 0x20)
      {
        output->append("\\u00");
        output->push_back(hex[character >> 4]);
        output->push_back(hex[character & 0x0f]);
      }
      else
      {
        output->push_back(static_cast<char>(character));
      }
      break;
    }
  }
  output->push_back('"');
}

void AppendPropertyName(std::string* output, std::string_view name, int indentation)
{
  output->append(static_cast<std::size_t>(indentation), ' ');
  AppendJsonString(output, name);
  output->append(": ");
}

template <std::size_t Size>
void AppendArray(std::string* output, const std::array<u64, Size>& values)
{
  output->push_back('[');
  for (std::size_t i = 0; i < Size; ++i)
  {
    if (i != 0)
      output->append(", ");
    AppendInteger(output, values[i]);
  }
  output->push_back(']');
}

void AppendNumericMap(std::string* output, const std::map<u32, u64>& values, int indentation)
{
  output->append("{\n");
  bool first = true;
  for (const auto& [key, count] : values)
  {
    if (!first)
      output->append(",\n");
    first = false;

    output->append(static_cast<std::size_t>(indentation + 2), ' ');
    output->push_back('"');
    AppendInteger(output, key);
    output->append("\": ");
    AppendInteger(output, count);
  }
  output->push_back('\n');
  output->append(static_cast<std::size_t>(indentation), ' ');
  output->push_back('}');
}

void AppendStringMap(std::string* output, const std::map<std::string, u64>& values, int indentation)
{
  output->append("{\n");
  bool first = true;
  for (const auto& [key, count] : values)
  {
    if (!first)
      output->append(",\n");
    first = false;

    output->append(static_cast<std::size_t>(indentation + 2), ' ');
    AppendJsonString(output, key);
    output->append(": ");
    AppendInteger(output, count);
  }
  output->push_back('\n');
  output->append(static_cast<std::size_t>(indentation), ' ');
  output->push_back('}');
}

void AppendNamedArray(std::string* output, std::string_view name, const auto& values, bool comma)
{
  AppendPropertyName(output, name, 4);
  AppendArray(output, values);
  output->append(comma ? ",\n" : "\n");
}

void AppendNamedCount(std::string* output, std::string_view name, u64 value)
{
  AppendPropertyName(output, name, 4);
  AppendInteger(output, value);
  output->append(",\n");
}

}  // namespace

std::string SerializeBlockProfile(const BlockProfileData& data)
{
  static constexpr std::array<std::string_view,
                              static_cast<std::size_t>(SemanticFeature::Count)>
      semantic_feature_names = {
          "load_store", "floating_point", "block_end", "exception", "carry",
          "overflow",   "condition_register", "fprf",  "system_state", "branch",
      };
  static constexpr std::array<std::string_view,
                              static_cast<std::size_t>(GPRReuseDistance::Count)>
      reuse_distance_names = {
          "1", "2", "3-4", "5-8", "9-16", "17+", "external_or_earlier_block",
      };

  std::string output;
  output.reserve(4096);
  output.append("{\n");
  AppendPropertyName(&output, "schema", 2);
  AppendJsonString(&output, "ci3-powerpc-block-profile");
  output.append(",\n");
  AppendPropertyName(&output, "schema_version", 2);
  AppendInteger(&output, 1);
  output.append(",\n");
  AppendPropertyName(&output, "observation_unit", 2);
  AppendJsonString(&output, "successful_cached_interpreter_block_compilation");
  output.append(",\n");
  AppendPropertyName(&output, "execution_weighted", 2);
  output.append("false,\n");
  AppendPropertyName(&output, "unique_blocks", 2);
  output.append("false,\n");
  AppendPropertyName(&output, "duplicate_compilations_possible", 2);
  output.append("true,\n");
  AppendPropertyName(&output, "aggregates", 2);
  output.append("{\n");

  AppendNamedCount(&output, "observed_blocks", data.observed_blocks);
  AppendNamedCount(&output, "broken_blocks", data.broken_blocks);
  AppendNamedCount(&output, "analyzed_operations", data.analyzed_operations);
  AppendNamedCount(&output, "eligible_operations", data.eligible_operations);
  AppendNamedCount(&output, "skipped_operations", data.skipped_operations);
  AppendNamedCount(&output, "supported_operations", data.supported_operations);
  AppendNamedCount(&output, "blocks_with_supported_operations",
                   data.blocks_with_supported_operations);
  AppendNamedCount(&output, "fully_supported_eligible_blocks",
                   data.fully_supported_eligible_blocks);
  AppendNamedCount(&output, "maximum_live_future_gprs", data.maximum_live_future_gprs);

  AppendPropertyName(&output, "analyzed_block_lengths", 4);
  AppendNumericMap(&output, data.analyzed_block_lengths, 4);
  output.append(",\n");
  AppendPropertyName(&output, "eligible_block_lengths", 4);
  AppendNumericMap(&output, data.eligible_block_lengths, 4);
  output.append(",\n");
  AppendPropertyName(&output, "supported_run_lengths", 4);
  AppendNumericMap(&output, data.supported_run_lengths, 4);
  output.append(",\n");
  AppendPropertyName(&output, "opcode_counts", 4);
  AppendStringMap(&output, data.opcode_counts, 4);
  output.append(",\n");

  AppendNamedArray(&output, "gpr_reads_per_operation", data.gpr_reads_per_operation, true);
  AppendNamedArray(&output, "gpr_writes_per_operation", data.gpr_writes_per_operation, true);
  AppendNamedArray(&output, "maximum_live_future_gprs_per_block",
                   data.maximum_live_future_gprs_per_block, true);

  AppendPropertyName(&output, "semantic_features", 4);
  output.append("{\n");
  for (std::size_t i = 0; i < semantic_feature_names.size(); ++i)
  {
    AppendPropertyName(&output, semantic_feature_names[i], 6);
    AppendInteger(&output, data.semantic_feature_counts[i]);
    output.append(i + 1 == semantic_feature_names.size() ? "\n" : ",\n");
  }
  output.append("    },\n");

  AppendPropertyName(&output, "gpr_reuse_distance", 4);
  output.append("{\n");
  for (std::size_t i = 0; i < reuse_distance_names.size(); ++i)
  {
    AppendPropertyName(&output, reuse_distance_names[i], 6);
    AppendInteger(&output, data.gpr_reuse_distance_counts[i]);
    output.append(i + 1 == reuse_distance_names.size() ? "\n" : ",\n");
  }
  output.append("    }\n");
  output.append("  }\n");
  output.append("}\n");
  return output;
}

}  // namespace PowerPC::CI3
