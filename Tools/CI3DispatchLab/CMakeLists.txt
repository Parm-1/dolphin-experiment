cmake_minimum_required(VERSION 3.20)

project(CI3DispatchLab LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)

add_executable(ci3_dispatch_lab main.cpp)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(ci3_dispatch_lab PRIVATE -Wall -Wextra)
endif()

enable_testing()
add_test(
  NAME ci3_dispatch_lab_verify
  COMMAND ci3_dispatch_lab --iterations 7 --repetitions 1 --trace-length 97 --seed 0x12345678
          --verify-only)
