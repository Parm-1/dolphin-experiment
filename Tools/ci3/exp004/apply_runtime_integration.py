#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def write(path: str, content: str) -> None:
    destination = ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    destination = ROOT / path
    text = destination.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"missing insertion point in {path}: {old!r}")
    destination.write_text(text.replace(old, new, 1), encoding="utf-8")


write(
    "Source/Core/Core/PowerPC/CI3/BlockProfileRuntime.h",
    '''// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include <memory>
#include <span>
#include <string>

#include "Core/PowerPC/CI3/BlockProfile.h"

namespace PowerPC::CI3
{

class BlockProfileRuntime
{
public:
  explicit BlockProfileRuntime(std::string output_path);

  void ObserveBlock(bool broken, std::span<const PPCAnalyst::CodeOp> operations);
  bool Flush() const;

  const BlockProfileData& GetData() const { return m_accumulator.GetData(); }

private:
  std::string m_output_path;
  BlockProfileAccumulator m_accumulator;
};

std::unique_ptr<BlockProfileRuntime> CreateBlockProfileRuntime(const char* output_path);

}  // namespace PowerPC::CI3
''',
)

write(
    "Source/Core/Core/PowerPC/CI3/BlockProfileRuntime.cpp",
    '''// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include "Core/PowerPC/CI3/BlockProfileRuntime.h"

#include <utility>

#include "Common/FileUtil.h"
#include "Core/PowerPC/CI3/BlockProfileJson.h"

namespace PowerPC::CI3
{

BlockProfileRuntime::BlockProfileRuntime(std::string output_path)
    : m_output_path(std::move(output_path))
{
}

void BlockProfileRuntime::ObserveBlock(bool broken,
                                       std::span<const PPCAnalyst::CodeOp> operations)
{
  m_accumulator.ObserveBlock(broken, operations);
}

bool BlockProfileRuntime::Flush() const
{
  return File::WriteStringToFile(m_output_path, SerializeBlockProfile(m_accumulator.GetData()));
}

std::unique_ptr<BlockProfileRuntime> CreateBlockProfileRuntime(const char* output_path)
{
  if (output_path == nullptr || output_path[0] == '\0')
    return nullptr;

  return std::make_unique<BlockProfileRuntime>(output_path);
}

}  // namespace PowerPC::CI3
''',
)

replace_once(
    "Source/Core/Core/PowerPC/CachedInterpreter/CachedInterpreter.h",
    "#include <cstddef>\n",
    "#include <cstddef>\n#include <memory>\n",
)
replace_once(
    "Source/Core/Core/PowerPC/CachedInterpreter/CachedInterpreter.h",
    "namespace CoreTiming\n{",
    "namespace PowerPC::CI3\n{\nclass BlockProfileRuntime;\n}\n\nnamespace CoreTiming\n{",
)
replace_once(
    "Source/Core/Core/PowerPC/CachedInterpreter/CachedInterpreter.h",
    "  CachedInterpreterBlockCache m_block_cache;\n",
    "  CachedInterpreterBlockCache m_block_cache;\n"
    "  std::unique_ptr<PowerPC::CI3::BlockProfileRuntime> m_ci3_block_profile;\n",
)

replace_once(
    "Source/Core/Core/PowerPC/CachedInterpreter/CachedInterpreter.cpp",
    "#include <span>\n",
    "#include <cstdlib>\n#include <span>\n",
)
replace_once(
    "Source/Core/Core/PowerPC/CachedInterpreter/CachedInterpreter.cpp",
    '#include "Core/PowerPC/Gekko.h"\n',
    '#include "Core/PowerPC/CI3/BlockProfileRuntime.h"\n#include "Core/PowerPC/Gekko.h"\n',
)
replace_once(
    "Source/Core/Core/PowerPC/CachedInterpreter/CachedInterpreter.cpp",
    "  m_block_cache.Init();\n\n  code_block.m_stats",
    "  m_block_cache.Init();\n\n"
    "  m_ci3_block_profile = PowerPC::CI3::CreateBlockProfileRuntime(\n"
    '      std::getenv("DOLPHIN_CI3_BLOCK_PROFILE_PATH"));\n\n'
    "  code_block.m_stats",
)
replace_once(
    "Source/Core/Core/PowerPC/CachedInterpreter/CachedInterpreter.cpp",
    "void CachedInterpreter::Shutdown()\n{\n  m_block_cache.Shutdown();\n}",
    "void CachedInterpreter::Shutdown()\n{\n"
    "  if (m_ci3_block_profile && !m_ci3_block_profile->Flush())\n"
    '    ERROR_LOG_FMT(DYNA_REC, "Failed to write CI3 aggregate block profile");\n'
    "  m_ci3_block_profile.reset();\n\n"
    "  m_block_cache.Shutdown();\n}",
)
replace_once(
    "Source/Core/Core/PowerPC/CachedInterpreter/CachedInterpreter.cpp",
    "      m_block_cache.FinalizeBlock(*b, jo.enableBlocklink, code_block, m_code_buffer);\n\n"
    "#ifdef JIT_LOG_GENERATED_CODE",
    "      m_block_cache.FinalizeBlock(*b, jo.enableBlocklink, code_block, m_code_buffer);\n\n"
    "      if (m_ci3_block_profile)\n"
    "      {\n"
    "        m_ci3_block_profile->ObserveBlock(\n"
    "            code_block.m_broken,\n"
    "            std::span<const PPCAnalyst::CodeOp>{m_code_buffer.data(),\n"
    "                                                code_block.m_num_instructions});\n"
    "      }\n\n"
    "#ifdef JIT_LOG_GENERATED_CODE",
)

replace_once(
    "Source/Core/Core/CMakeLists.txt",
    "  PowerPC/BreakPoints.cpp\n  PowerPC/BreakPoints.h\n",
    "  PowerPC/BreakPoints.cpp\n"
    "  PowerPC/BreakPoints.h\n"
    "  PowerPC/CI3/BlockProfile.cpp\n"
    "  PowerPC/CI3/BlockProfile.h\n"
    "  PowerPC/CI3/BlockProfileJson.cpp\n"
    "  PowerPC/CI3/BlockProfileJson.h\n"
    "  PowerPC/CI3/BlockProfileRuntime.cpp\n"
    "  PowerPC/CI3/BlockProfileRuntime.h\n",
)

write(
    "Source/UnitTests/Core/PowerPC/CI3BlockProfileRuntimeTest.cpp",
    '''// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <atomic>
#include <filesystem>
#include <memory>
#include <string>

#include "Common/BitSet.h"
#include "Common/FileUtil.h"
#include "Core/PowerPC/CI3/BlockProfileJson.h"
#include "Core/PowerPC/CI3/BlockProfileRuntime.h"
#include "Core/PowerPC/PPCAnalyst.h"
#include "Core/PowerPC/PPCTables.h"

#include <gtest/gtest.h>

namespace
{
using PowerPC::CI3::BlockProfileRuntime;
using PowerPC::CI3::CreateBlockProfileRuntime;
using PowerPC::CI3::SerializeBlockProfile;

class TemporaryPath
{
public:
  explicit TemporaryPath(bool directory = false)
  {
    static std::atomic<u64> counter{0};
    m_path = std::filesystem::temp_directory_path() /
             ("dolphin-ci3-block-profile-" +
              std::to_string(counter.fetch_add(1, std::memory_order_relaxed)));
    std::error_code error;
    std::filesystem::remove_all(m_path, error);
    if (directory)
      std::filesystem::create_directories(m_path);
  }

  ~TemporaryPath()
  {
    std::error_code error;
    std::filesystem::remove_all(m_path, error);
  }

  const std::filesystem::path& Get() const { return m_path; }
  std::string String() const { return m_path.string(); }

private:
  std::filesystem::path m_path;
};

PPCAnalyst::CodeOp MakeSupportedOperation(GekkoOPInfo* info)
{
  *info = GekkoOPInfo{"addi", OpType::Integer, 1, FL_OUT_D | FL_IN_A0, nullptr};
  PPCAnalyst::CodeOp operation{};
  operation.opinfo = info;
  operation.regsOut = BitSet32{3};
  return operation;
}

TEST(CI3BlockProfileRuntime, NullAndEmptyPathsAreDisabled)
{
  EXPECT_EQ(CreateBlockProfileRuntime(nullptr), nullptr);
  EXPECT_EQ(CreateBlockProfileRuntime(""), nullptr);
}

TEST(CI3BlockProfileRuntime, ConstructionAndDestructionPerformNoFileIO)
{
  TemporaryPath path;
  {
    std::unique_ptr<BlockProfileRuntime> runtime = CreateBlockProfileRuntime(path.String().c_str());
    ASSERT_NE(runtime, nullptr);
    EXPECT_FALSE(std::filesystem::exists(path.Get()));
  }
  EXPECT_FALSE(std::filesystem::exists(path.Get()));
}

TEST(CI3BlockProfileRuntime, ExplicitFlushWritesCanonicalAggregate)
{
  TemporaryPath path;
  std::unique_ptr<BlockProfileRuntime> runtime = CreateBlockProfileRuntime(path.String().c_str());
  ASSERT_NE(runtime, nullptr);
  GekkoOPInfo info{};
  const PPCAnalyst::CodeOp operation = MakeSupportedOperation(&info);
  runtime->ObserveBlock(false, std::span<const PPCAnalyst::CodeOp>{&operation, 1});
  const std::string expected = SerializeBlockProfile(runtime->GetData());
  ASSERT_TRUE(runtime->Flush());
  std::string actual;
  ASSERT_TRUE(File::ReadFileToString(path.String(), actual));
  EXPECT_EQ(actual, expected);
}

TEST(CI3BlockProfileRuntime, ExplicitFlushOverwritesStaleOutput)
{
  TemporaryPath path;
  ASSERT_TRUE(File::WriteStringToFile(path.String(), "stale"));
  std::unique_ptr<BlockProfileRuntime> runtime = CreateBlockProfileRuntime(path.String().c_str());
  ASSERT_NE(runtime, nullptr);
  ASSERT_TRUE(runtime->Flush());
  std::string actual;
  ASSERT_TRUE(File::ReadFileToString(path.String(), actual));
  EXPECT_EQ(actual, SerializeBlockProfile(runtime->GetData()));
}

TEST(CI3BlockProfileRuntime, InvalidOutputTargetReturnsFailure)
{
  TemporaryPath directory(true);
  std::unique_ptr<BlockProfileRuntime> runtime =
      CreateBlockProfileRuntime(directory.String().c_str());
  ASSERT_NE(runtime, nullptr);
  EXPECT_FALSE(runtime->Flush());
}
}  // namespace
''',
)

replace_once(
    "Source/UnitTests/Core/CMakeLists.txt",
    "  ../../Core/Core/PowerPC/CI3/BlockProfile.cpp\n"
    "  ../../Core/Core/PowerPC/CI3/BlockProfileJson.cpp\n",
    "",
)
replace_once(
    "Source/UnitTests/Core/CMakeLists.txt",
    "  PowerPC/CI3BlockProfileJsonTest.cpp\n",
    "  PowerPC/CI3BlockProfileJsonTest.cpp\n"
    "  PowerPC/CI3BlockProfileRuntimeTest.cpp\n",
)

workflow = ROOT / ".github/workflows/ci3-powerpc-differential.yml"
text = workflow.read_text(encoding="utf-8")
text = text.replace(
    '      - "Source/Core/Core/PowerPC/CI3/BlockProfileJson.h"\n',
    '      - "Source/Core/Core/PowerPC/CI3/BlockProfileJson.h"\n'
    '      - "Source/Core/Core/PowerPC/CI3/BlockProfileRuntime.cpp"\n'
    '      - "Source/Core/Core/PowerPC/CI3/BlockProfileRuntime.h"\n'
    '      - "Source/Core/Core/PowerPC/CachedInterpreter/CachedInterpreter.cpp"\n'
    '      - "Source/Core/Core/PowerPC/CachedInterpreter/CachedInterpreter.h"\n',
)
text = text.replace(
    '      - "Source/UnitTests/Core/PowerPC/CI3BlockProfileJsonTest.cpp"\n',
    '      - "Source/UnitTests/Core/PowerPC/CI3BlockProfileJsonTest.cpp"\n'
    '      - "Source/UnitTests/Core/PowerPC/CI3BlockProfileRuntimeTest.cpp"\n',
)
text = text.replace(
    "--gtest_filter='CI3PowerPCIntegerDifferential.*:CI3BlockProfile.*:CI3BlockProfileJson.*'",
    "--gtest_filter='CI3PowerPCIntegerDifferential.*:CI3BlockProfile.*:CI3BlockProfileJson.*:CI3BlockProfileRuntime.*'",
)
workflow.write_text(text, encoding="utf-8")

write(
    "docs/ci3/experiments/EXP-20260817-004/runtime-v1.md",
    '''# EXP-20260817-004 runtime integration v1

This slice connects aggregate-only profiling to Cached Interpreter through the non-empty
`DOLPHIN_CI3_BLOCK_PROFILE_PATH` environment variable.

The disabled path allocates no session and performs no file I/O. When enabled, successfully
finalized compilations contribute their existing analyzed `PPCAnalyst::CodeOp` span. Canonical
schema-v1 JSON is written only during explicit orderly shutdown. No guest instruction word,
address, disassembly, ordered trace, title identifier, or proprietary content is retained.

The output remains compilation-weighted, not execution-weighted and not a unique-block census.
Tests cover disabled activation, construction/destruction side effects, canonical explicit flush,
stale-file overwrite, invalid-target failure, and all earlier CI3 regressions.

Passing establishes only a privacy-bounded opt-in instrumentation route. It does not establish a
legal workload profile, profiling overhead, a CI3 executor, a Dolphin speedup, a game or iPhone
result, or Gate 2 completion.

The design and implementation are substantially AI-assisted and remain confined to this
experimental fork.
''',
)

for relative in [
    ".github/workflows/ci3-apply-runtime-patch.yml",
    ".github/workflows/ci3-export-runtime-sources.yml",
    ".github/workflows/ci3-export-runtime-payload.yml",
    ".github/workflows/ci3-apply-runtime-now.yml",
    ".github/workflows/ci3-apply-runtime-direct.yml",
    "Tools/ci3/exp004/apply_runtime_integration.py",
]:
    (ROOT / relative).unlink(missing_ok=True)
