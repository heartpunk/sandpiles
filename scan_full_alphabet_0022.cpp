#include <array>
#include <cstdint>
#include <cstdlib>
#include <future>
#include <iostream>
#include <string>
#include <vector>

// Scan equal packets for the fixed core [[0,0],[2,2]] beyond the first hit.
// Axis and equal-amplitude cases are read from three incremental trajectories;
// only candidates surviving all of those are tested on the six unequal pairs.

namespace {

constexpr int kSide = 1025;
constexpr int kCenter = kSide / 2;
constexpr int kA = kCenter * kSide + kCenter;
constexpr int kB = kA + 1;
constexpr int kD = kA + kSide;
constexpr int kC = kD + 1;
using Count = std::int64_t;
using Output = std::array<Count, 2>;

class Pile {
 public:
  Pile()
      : state_(kSide * kSide),
        odometer_(kSide * kSide),
        queued_(kSide * kSide) {
    pending_.reserve(kSide * kSide);
    reset();
  }

  void reset() {
    std::fill(state_.begin(), state_.end(), 0);
    std::fill(odometer_.begin(), odometer_.end(), 0);
    std::fill(queued_.begin(), queued_.end(), 0);
    pending_.clear();
    state_[kD] = 2;
    state_[kC] = 2;
  }

  void add(Count at_a, Count at_b) {
    state_[kA] += at_a;
    state_[kB] += at_b;
    enqueue(kA);
    enqueue(kB);
    while (!pending_.empty()) {
      const int site = pending_.back();
      pending_.pop_back();
      queued_[site] = 0;
      if (state_[site] < 4) continue;
      state_[site] -= 4;
      ++odometer_[site];
      enqueue(site);
      const int row = site / kSide;
      const int column = site % kSide;
      if (row <= 0 || row >= kSide - 1 ||
          column <= 0 || column >= kSide - 1) {
        std::cerr << "increase kSide\n";
        std::abort();
      }
      for (const int neighbor :
           {site - kSide, site + kSide, site - 1, site + 1}) {
        ++state_[neighbor];
        enqueue(neighbor);
      }
    }
  }

  Output output() const { return {odometer_[kC], odometer_[kD]}; }

  int radius() const {
    int result = 0;
    for (int row = 0; row < kSide; ++row) {
      for (int column = 0; column < kSide; ++column) {
        if (!odometer_[row * kSide + column]) continue;
        result = std::max(
            result,
            std::max(std::abs(row - kCenter),
                     std::abs(column - kCenter)));
      }
    }
    return result;
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

bool correct(const Output& output, int a, int b) {
  return ((output[0] & 1) == (a & 1)) &&
         ((output[1] & 1) == (b & 1));
}

struct Trajectory {
  std::vector<Output> output;
  int radius = 0;
};

Trajectory build_trajectory(
    int length, int a_step, int b_step) {
  Trajectory result;
  result.output.resize(length + 1);
  Pile pile;
  for (int grains = 1; grains <= length; ++grains) {
    pile.add(a_step, b_step);
    result.output[grains] = pile.output();
  }
  result.radius = pile.radius();
  return result;
}

Output swapped(Output output) {
  std::swap(output[0], output[1]);
  return output;
}

}  // namespace

int main(int argc, char** argv) {
  int maximum_pulse = 10000;
  if (argc == 3 && std::string(argv[1]) == "--maximum-pulse") {
    maximum_pulse = std::stoi(argv[2]);
  } else if (argc != 1) {
    std::cerr << "usage: " << argv[0] << " [--maximum-pulse P]\n";
    return 2;
  }
  if (maximum_pulse < 1 || maximum_pulse > 100000) {
    std::cerr << "supported range is 1..100000\n";
    return 2;
  }

  const int length = 3 * maximum_pulse;
  auto axis_future = std::async(
      std::launch::async, build_trajectory, length, 1, 0);
  auto equal_future = std::async(
      std::launch::async, build_trajectory, length, 1, 1);
  auto mixed12_future = std::async(
      std::launch::async, build_trajectory,
      maximum_pulse, 1, 2);
  auto mixed13_future = std::async(
      std::launch::async, build_trajectory,
      maximum_pulse, 1, 3);
  auto mixed23_future = std::async(
      std::launch::async, build_trajectory,
      maximum_pulse, 2, 3);
  const Trajectory axis = axis_future.get();
  const Trajectory equal = equal_future.get();
  const std::array<Trajectory, 3> mixed = {{
      mixed12_future.get(),
      mixed13_future.get(),
      mixed23_future.get(),
  }};
  const std::array<std::array<int, 2>, 3> mixed_inputs = {{
      {1, 2}, {1, 3}, {2, 3},
  }};
  std::vector<int> hits;
  std::uint64_t axis_equal_candidates = 0;
  for (int pulse = 1; pulse <= maximum_pulse; ++pulse) {
    bool valid = true;
    for (int amplitude = 1; amplitude <= 3; ++amplitude) {
      valid &= correct(
          axis.output[amplitude * pulse], amplitude, 0);
      valid &= correct(
          swapped(axis.output[amplitude * pulse]), 0, amplitude);
      valid &= correct(
          equal.output[amplitude * pulse], amplitude, amplitude);
    }
    if (!valid) continue;
    ++axis_equal_candidates;
    for (std::size_t index = 0; index < mixed.size(); ++index) {
      const auto& input = mixed_inputs[index];
      if (!correct(
              mixed[index].output[pulse],
              input[0], input[1])) {
        valid = false;
        break;
      }
    }
    if (valid) {
      hits.push_back(pulse);
      std::cout << "FULL HIT p=" << pulse;
      if (hits.size() > 1) {
        std::cout << " gap=" << pulse - hits[hits.size() - 2];
      }
      std::cout << "\n";
    }
  }

  std::cout << "SCAN DONE max=" << maximum_pulse
            << " axis_equal_candidates=" << axis_equal_candidates
            << " full_hits=" << hits.size()
            << " max_axis_radius=" << axis.radius
            << " max_equal_trajectory_radius=" << equal.radius
            << " mixed_radii=(" << mixed[0].radius << ","
            << mixed[1].radius << "," << mixed[2].radius << ")"
            << "\nfirst_hits:";
  const std::size_t show = std::min<std::size_t>(hits.size(), 30);
  for (std::size_t index = 0; index < show; ++index) {
    std::cout << " " << hits[index];
  }
  std::cout << "\nfirst_gaps:";
  for (std::size_t index = 1; index < show; ++index) {
    std::cout << " " << hits[index] - hits[index - 1];
  }
  std::cout << "\n";
}
