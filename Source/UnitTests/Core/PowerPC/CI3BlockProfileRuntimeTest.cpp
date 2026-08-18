// Copyright 2026 Dolphin Emulator Project
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
