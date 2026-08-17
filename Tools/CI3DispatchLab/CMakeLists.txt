cmake_minimum_required(VERSION 3.20)

project(CI3DispatchLab LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)

function(ci3_configure_target target)
  if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(${target} PRIVATE -Wall -Wextra)
  endif()
endfunction()

add_executable(ci3_dispatch_lab main.cpp)
ci3_configure_target(ci3_dispatch_lab)

add_executable(ci3_state_lab state_lab.cpp state_engines.cpp state_boundary.cpp)
ci3_configure_target(ci3_state_lab)

enable_testing()
add_test(
  NAME ci3_dispatch_lab_verify
  COMMAND ci3_dispatch_lab --iterations 7 --repetitions 1 --trace-length 97 --seed 0x12345678
          --verify-only)
add_test(
  NAME ci3_state_lab_verify
  COMMAND ci3_state_lab --iterations 7 --repetitions 1 --trace-length 97 --seed 0x12345678
          --verify-only)
