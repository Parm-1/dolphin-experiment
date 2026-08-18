// Copyright 2026 Dolphin Emulator Project
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
