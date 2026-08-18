// Copyright 2026 Dolphin Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include <string>

#include "Core/PowerPC/CI3/BlockProfile.h"

namespace PowerPC::CI3
{

std::string SerializeBlockProfile(const BlockProfileData& data);

}  // namespace PowerPC::CI3
