#include "state_engines.h"

#include <algorithm>
#include <charconv>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace
{

volatile std::uint64_t g_sink = 0;

struct Options
{
  std::uint64_t iterations = 10000;
  std::size_t repetitions = 7;
  std::size_t trace_length = 256;
  std::uint64_t seed = 0x51A7E5EED1234567ULL;
  bool verify_only = false;
};

std::string CompilerName()
{
#if defined(__clang__)
  return std::string("clang-") + __clang_version__;
#elif defined(__GNUC__)
  return std::string("gcc-") + __VERSION__;
#else
  return "unknown";
#endif
}

std::string ArchitectureName()
{
#if defined(__aarch64__) || defined(_M_ARM64)
  return "aarch64";
#elif defined(__x86_64__) || defined(_M_X64)
  return "x86_64";
#else
  return "unknown";
#endif
}

std::string Hex(std::uint64_t value)
{
  std::ostringstream stream;
  stream << "0x" << std::hex << std::setw(16) << std::setfill('0') << value;
  return stream.str();
}

template <typename T>
T ParseInteger(std::string_view text, const char* option)
{
  T value{};
  int base = 10;
  if (text.size() > 2 && text[0] == '0' && (text[1] == 'x' || text[1] == 'X'))
  {
    text.remove_prefix(2);
    base = 16;
  }
  const auto [end, error] =
      std::from_chars(text.data(), text.data() + text.size(), value, base);
  if (error != std::errc{} || end != text.data() + text.size())
    throw std::invalid_argument(std::string("invalid value for ") + option);
  return value;
}

Options ParseOptions(int argc, char** argv)
{
  Options options{};
  for (int i = 1; i < argc; ++i)
  {
    const std::string_view arg = argv[i];
    auto require_value = [&](const char* option) -> std::string_view {
      if (++i >= argc)
        throw std::invalid_argument(std::string("missing value for ") + option);
      return argv[i];
    };

    if (arg == "--iterations")
      options.iterations =
          ParseInteger<std::uint64_t>(require_value("--iterations"), "--iterations");
    else if (arg == "--repetitions")
      options.repetitions =
          ParseInteger<std::size_t>(require_value("--repetitions"), "--repetitions");
    else if (arg == "--trace-length")
      options.trace_length =
          ParseInteger<std::size_t>(require_value("--trace-length"), "--trace-length");
    else if (arg == "--seed")
      options.seed = ParseInteger<std::uint64_t>(require_value("--seed"), "--seed");
    else if (arg == "--verify-only")
      options.verify_only = true;
    else
      throw std::invalid_argument(std::string("unknown option: ") + std::string(arg));
  }

  if (options.iterations == 0 || options.repetitions == 0 || options.trace_length == 0)
    throw std::invalid_argument("iterations, repetitions, and trace length must be non-zero");
  return options;
}

struct Engine
{
  std::string name;
  std::string boundary_mode;
  std::uint64_t boundaries_per_run = 0;
  std::function<std::uint64_t()> run;
};

struct TimingResult
{
  double median_ns_per_op = 0;
  double min_ns_per_op = 0;
  double max_ns_per_op = 0;
  std::uint64_t checksum = 0;
};

TimingResult Measure(const Engine& engine, const Options& options, std::uint64_t total_ops)
{
  g_sink = engine.run();
  std::vector<double> samples;
  samples.reserve(options.repetitions);
  std::uint64_t checksum = 0;

  for (std::size_t repetition = 0; repetition < options.repetitions; ++repetition)
  {
    const auto start = std::chrono::steady_clock::now();
    checksum = engine.run();
    const auto stop = std::chrono::steady_clock::now();
    g_sink = checksum;
    const double elapsed_ns =
        std::chrono::duration<double, std::nano>(stop - start).count();
    samples.push_back(elapsed_ns / static_cast<double>(total_ops));
  }

  std::sort(samples.begin(), samples.end());
  double median = samples[samples.size() / 2];
  if (samples.size() % 2 == 0)
    median = (samples[samples.size() / 2 - 1] + samples[samples.size() / 2]) / 2.0;
  return {median, samples.front(), samples.back(), checksum};
}

std::uint64_t BoundaryCount(std::uint64_t total_ops, std::uint64_t iterations,
                            std::size_t interval)
{
  if (interval == 0)
    return iterations;
  return (total_ops + interval - 1) / interval;
}

}  // namespace

int main(int argc, char** argv)
{
  using namespace CI3StateLab;

  try
  {
    const Options options = ParseOptions(argc, argv);
    if (options.trace_length > std::numeric_limits<std::uint64_t>::max() / options.iterations)
      throw std::overflow_error("total operation count overflow");

    const std::uint64_t total_ops =
        static_cast<std::uint64_t>(options.trace_length) * options.iterations;
    const std::vector<Op> trace = MakeTrace(options.trace_length, options.seed);
    const CI3StateModel initial_state = MakeInitialState(options.seed);

    std::vector<Engine> engines;
    engines.push_back({"state-promotable", "none", 0, [&] {
                         return RunStateNoBoundary(trace, options.iterations, initial_state);
                       }});
    engines.push_back({"state-boundary-every-op", "every-op", total_ops, [&] {
                         return RunStateEveryOp(trace, options.iterations, initial_state);
                       }});
    engines.push_back(
        {"state-boundary-4", "every-4", BoundaryCount(total_ops, options.iterations, 4),
         [&] { return RunStateEvery4(trace, options.iterations, initial_state); }});
    engines.push_back(
        {"state-boundary-16", "every-16",
         BoundaryCount(total_ops, options.iterations, 16),
         [&] { return RunStateEvery16(trace, options.iterations, initial_state); }});
    engines.push_back({"state-boundary-per-trace", "per-trace", options.iterations, [&] {
                         return RunStatePerTrace(trace, options.iterations, initial_state);
                       }});
    engines.push_back({"pinned-promotable", "none", 0, [&] {
                         return RunPinnedNoBoundary(trace, options.iterations, initial_state);
                       }});
    engines.push_back({"pinned-boundary-every-op", "every-op", total_ops, [&] {
                         return RunPinnedEveryOp(trace, options.iterations, initial_state);
                       }});
    engines.push_back(
        {"pinned-boundary-4", "every-4", BoundaryCount(total_ops, options.iterations, 4),
         [&] { return RunPinnedEvery4(trace, options.iterations, initial_state); }});
    engines.push_back(
        {"pinned-boundary-16", "every-16",
         BoundaryCount(total_ops, options.iterations, 16),
         [&] { return RunPinnedEvery16(trace, options.iterations, initial_state); }});
    engines.push_back({"pinned-boundary-per-trace", "per-trace", options.iterations, [&] {
                         return RunPinnedPerTrace(trace, options.iterations, initial_state);
                       }});

    std::cout << "{\"kind\":\"environment\",\"compiler\":\"" << CompilerName()
              << "\",\"architecture\":\"" << ArchitectureName() << "\",\"trace_length\":"
              << options.trace_length << ",\"iterations\":" << options.iterations
              << ",\"repetitions\":" << options.repetitions << ",\"seed\":\""
              << Hex(options.seed) << "\"}\n";

    const std::uint64_t reference_checksum = engines.front().run();
    for (const Engine& engine : engines)
    {
      const std::uint64_t checksum = engine.run();
      if (checksum != reference_checksum)
      {
        std::cerr << "verification failed for " << engine.name << ": expected "
                  << Hex(reference_checksum) << ", got " << Hex(checksum) << '\n';
        return 2;
      }
    }

    if (options.verify_only)
    {
      std::cout << "{\"kind\":\"verification\",\"engines\":" << engines.size()
                << ",\"checksum\":\"" << Hex(reference_checksum)
                << "\",\"status\":\"pass\"}\n";
      return 0;
    }

    for (const Engine& engine : engines)
    {
      const TimingResult result = Measure(engine, options, total_ops);
      std::cout << std::fixed << std::setprecision(4)
                << "{\"kind\":\"benchmark\",\"engine\":\"" << engine.name
                << "\",\"boundary_mode\":\"" << engine.boundary_mode
                << "\",\"boundaries_per_run\":" << engine.boundaries_per_run
                << ",\"trace_length\":" << options.trace_length
                << ",\"iterations\":" << options.iterations
                << ",\"repetitions\":" << options.repetitions
                << ",\"median_ns_per_op\":" << result.median_ns_per_op
                << ",\"min_ns_per_op\":" << result.min_ns_per_op
                << ",\"max_ns_per_op\":" << result.max_ns_per_op
                << ",\"checksum\":\"" << Hex(result.checksum) << "\"}\n";
    }
    return 0;
  }
  catch (const std::exception& error)
  {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
