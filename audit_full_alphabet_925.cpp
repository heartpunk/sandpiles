#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

// Independent exhaustive checker for the 2x2 full-alphabet result.
//
// This intentionally differs from sandpile_2x2_full_alphabet_fast.cpp:
//   * every queue event performs exactly one legal toppling;
//   * axis and equal-input trajectories are tabulated through 3*P;
//   * those tables reject six more alphabet cases before any scratch run;
//   * only the six unequal mixed cases are stabilized from scratch.

namespace {

constexpr int kSide = 129;
constexpr int kCenter = kSide / 2;
constexpr int kA = kCenter * kSide + kCenter;
constexpr int kB = kA + 1;
constexpr int kD = kA + kSide;
constexpr int kC = kD + 1;
constexpr int kDefaultMaximumPulse = 925;

using Count = std::int64_t;
using Core = std::array<int, 4>;
using Output = std::array<Count, 2>;

class Pile {
 public:
  Pile()
      : state_(kSide * kSide),
        odometer_(kSide * kSide),
        queued_(kSide * kSide) {
    pending_.reserve(kSide * kSide);
  }

  void reset(const Core& core) {
    std::fill(state_.begin(), state_.end(), 0);
    std::fill(odometer_.begin(), odometer_.end(), 0);
    std::fill(queued_.begin(), queued_.end(), 0);
    pending_.clear();
    state_[kA] = core[0];
    state_[kB] = core[1];
    state_[kD] = core[2];
    state_[kC] = core[3];
  }

  void add(Count at_a, Count at_b) {
    if (at_a) {
      state_[kA] += at_a;
      enqueue(kA);
    }
    if (at_b) {
      state_[kB] += at_b;
      enqueue(kB);
    }
    while (!pending_.empty()) {
      const int site = pending_.back();
      pending_.pop_back();
      queued_[site] = 0;
      if (state_[site] < 4) continue;

      // Exactly one legal toppling, rather than a batched quotient.
      state_[site] -= 4;
      ++odometer_[site];
      enqueue(site);
      const int row = site / kSide;
      const int column = site % kSide;
      if (row <= 0 || row >= kSide - 1 ||
          column <= 0 || column >= kSide - 1) {
        std::cerr << "array boundary reached\n";
        std::abort();
      }
      const std::array<int, 4> neighbors = {
          site - kSide, site + kSide, site - 1, site + 1};
      for (const int neighbor : neighbors) {
        ++state_[neighbor];
        enqueue(neighbor);
      }
    }
  }

  Output output() const { return {odometer_[kC], odometer_[kD]}; }

  int toppling_radius() const {
    int radius = 0;
    for (int row = 0; row < kSide; ++row) {
      for (int column = 0; column < kSide; ++column) {
        if (!odometer_[row * kSide + column]) continue;
        radius = std::max(
            radius,
            std::max(std::abs(row - kCenter),
                     std::abs(column - kCenter)));
      }
    }
    return radius;
  }

  bool stable() const {
    for (const Count height : state_) {
      if (height < 0 || height >= 4) return false;
    }
    return true;
  }

 private:
  void enqueue(int site) {
    if (state_[site] >= 4 && !queued_[site]) {
      queued_[site] = 1;
      pending_.push_back(site);
    }
  }

  std::vector<Count> state_;
  std::vector<Count> odometer_;
  std::vector<std::uint8_t> queued_;
  std::vector<int> pending_;
};

Core decode_core(int code) {
  Core core{};
  for (int index = 3; index >= 0; --index) {
    core[index] = code % 4;
    code /= 4;
  }
  return core;
}

bool parity(const Output& output, int a, int b) {
  return ((output[0] & 1) == (a & 1)) &&
         ((output[1] & 1) == (b & 1));
}

Output run(const Core& core, int pulse, int a, int b) {
  Pile pile;
  pile.reset(core);
  pile.add(static_cast<Count>(a) * pulse,
           static_cast<Count>(b) * pulse);
  if (!pile.stable()) std::abort();
  return pile.output();
}

void fnv_word(std::uint64_t& hash, std::uint64_t word) {
  for (int byte = 0; byte < 8; ++byte) {
    hash ^= (word >> (8 * byte)) & 0xffU;
    hash *= UINT64_C(1099511628211);
  }
}

std::uint64_t mix(std::uint64_t value) {
  value += UINT64_C(0x9e3779b97f4a7c15);
  value = (value ^ (value >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
  value = (value ^ (value >> 27)) * UINT64_C(0x94d049bb133111eb);
  return value ^ (value >> 31);
}

}  // namespace

int main(int argc, char** argv) {
  int maximum_pulse = kDefaultMaximumPulse;
  if (argc == 3 && std::string(argv[1]) == "--maximum-pulse") {
    maximum_pulse = std::stoi(argv[2]);
  } else if (argc != 1) {
    std::cerr << "usage: " << argv[0] << " [--maximum-pulse P]\n";
    return 2;
  }
  if (maximum_pulse <= 0 ||
      maximum_pulse > kDefaultMaximumPulse) {
    std::cerr << "this audit is dimensioned for 1 <= P <= 925\n";
    return 2;
  }

  // Exact finite-array justification.  This maximal stable core and maximal
  // two-input addition dominate every configuration examined below.
  Pile dominating;
  dominating.reset({3, 3, 3, 3});
  dominating.add(3LL * maximum_pulse, 3LL * maximum_pulse);
  const int dominating_radius = dominating.toppling_radius();
  if (!dominating.stable() || dominating_radius >= kCenter - 2) {
    std::cerr << "dominating run does not fit safely\n";
    return 3;
  }

  const std::array<std::array<int, 2>, 6> mixed_cases = {{
      {1, 2}, {2, 1}, {1, 3},
      {3, 1}, {2, 3}, {3, 2},
  }};

  std::uint64_t boolean_candidates = 0;
  std::uint64_t axis_equal_candidates = 0;
  std::uint64_t full_hits = 0;
  int least_hit = std::numeric_limits<int>::max();
  Core least_core{};
  std::uint64_t fnv = UINT64_C(1469598103934665603);
  std::uint64_t split = UINT64_C(0x243f6a8885a308d3);

  for (int code = 0; code < 256; ++code) {
    const Core core = decode_core(code);
    const int trajectory_length = 3 * maximum_pulse;
    std::vector<Output> a_only(trajectory_length + 1);
    std::vector<Output> b_only(trajectory_length + 1);
    std::vector<Output> equal(trajectory_length + 1);
    Pile a_pile;
    Pile b_pile;
    Pile equal_pile;
    a_pile.reset(core);
    b_pile.reset(core);
    equal_pile.reset(core);
    for (int grains = 1; grains <= trajectory_length; ++grains) {
      a_pile.add(1, 0);
      b_pile.add(0, 1);
      equal_pile.add(1, 1);
      a_only[grains] = a_pile.output();
      b_only[grains] = b_pile.output();
      equal[grains] = equal_pile.output();
    }

    for (int pulse = 1; pulse <= maximum_pulse; ++pulse) {
      const std::array<Output, 3> boolean_outputs = {
          a_only[pulse], b_only[pulse], equal[pulse]};
      fnv_word(fnv, static_cast<std::uint64_t>(code));
      fnv_word(fnv, static_cast<std::uint64_t>(pulse));
      for (const Output& output : boolean_outputs) {
        fnv_word(fnv, static_cast<std::uint64_t>(output[0]));
        fnv_word(fnv, static_cast<std::uint64_t>(output[1]));
      }
      split ^= mix(
          static_cast<std::uint64_t>(code) << 48 ^
          static_cast<std::uint64_t>(pulse) << 32 ^
          static_cast<std::uint64_t>(boolean_outputs[0][0]) << 16 ^
          static_cast<std::uint64_t>(boolean_outputs[2][1]));
      split = (split << 17) | (split >> 47);

      if (!parity(a_only[pulse], 1, 0) ||
          !parity(b_only[pulse], 0, 1) ||
          !parity(equal[pulse], 1, 1)) {
        continue;
      }
      ++boolean_candidates;

      bool valid = true;
      for (int amplitude = 2; amplitude <= 3; ++amplitude) {
        valid &= parity(
            a_only[amplitude * pulse], amplitude, 0);
        valid &= parity(
            b_only[amplitude * pulse], 0, amplitude);
        valid &= parity(
            equal[amplitude * pulse], amplitude, amplitude);
      }
      if (!valid) continue;
      ++axis_equal_candidates;

      for (const auto& input : mixed_cases) {
        const Output output =
            run(core, pulse, input[0], input[1]);
        fnv_word(fnv, static_cast<std::uint64_t>(code));
        fnv_word(fnv, static_cast<std::uint64_t>(pulse));
        fnv_word(fnv, static_cast<std::uint64_t>(input[0]));
        fnv_word(fnv, static_cast<std::uint64_t>(input[1]));
        fnv_word(fnv, static_cast<std::uint64_t>(output[0]));
        fnv_word(fnv, static_cast<std::uint64_t>(output[1]));
        if (!parity(output, input[0], input[1])) {
          valid = false;
          break;
        }
      }
      if (!valid) continue;

      ++full_hits;
      if (pulse < least_hit) {
        least_hit = pulse;
        least_core = core;
      }
      std::cout << "FULL HIT p=" << pulse << " core=("
                << core[0] << "," << core[1] << ","
                << core[2] << "," << core[3] << ")\n";
    }
  }

  std::cout << "AUDIT DONE maximum_pulse=" << maximum_pulse
            << " dominating_radius=" << dominating_radius
            << " boolean_candidates=" << boolean_candidates
            << " axis_equal_candidates=" << axis_equal_candidates
            << " full_hits=" << full_hits
            << " least_hit="
            << (full_hits ? least_hit : 0)
            << " least_core=(" << least_core[0] << ","
            << least_core[1] << "," << least_core[2] << ","
            << least_core[3] << ")"
            << " fnv64=0x" << std::hex << fnv
            << " mix64=0x" << split << std::dec << "\n";

  if (maximum_pulse == kDefaultMaximumPulse) {
    return (
        dominating_radius == 27 && full_hits == 1 &&
        least_hit == 925 && least_core == Core{0, 0, 2, 2})
        ? 0
        : 4;
  }
  return 0;
}
