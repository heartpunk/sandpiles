#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

// Exact family scan for the fixed stable background
//
//     A=0  B=0
//     D=2  C=2
//
// on the infinite square lattice (implemented inside a checked, very large
// zero boundary).  A packet p is a hit when adding ap at A and bp at B makes
// the odometer parities at (C,D) equal (a,b), for every a,b in {0,1,2,3}.
//
// Three incremental trajectories certify all axis and diagonal cases.  Only
// the six remaining unequal positive pairs are then stabilized from scratch.

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
        stamp_(kSide * kSide),
        queued_(kSide * kSide) {
    pending_.reserve(kSide * kSide);
    reset();
  }

  void reset() {
    ++generation_;
    if (generation_ == 0) {
      std::fill(stamp_.begin(), stamp_.end(), 0);
      generation_ = 1;
    }
    pending_.clear();
    radius_ = 0;
    touch(kA);
    touch(kB);
    touch(kD);
    touch(kC);
    state_[kD] = 2;
    state_[kC] = 2;
  }

  void add(Count at_a, Count at_b) {
    if (at_a) seed(kA, at_a);
    if (at_b) seed(kB, at_b);
    while (!pending_.empty()) {
      const int site = pending_.back();
      pending_.pop_back();
      queued_[site] = 0;
      const Count amount = state_[site] / 4;
      if (!amount) continue;
      state_[site] -= 4 * amount;
      odometer_[site] += amount;
      const int row = site / kSide;
      const int column = site % kSide;
      if (row <= 0 || row >= kSide - 1 ||
          column <= 0 || column >= kSide - 1) {
        std::cerr << "boundary reached; increase kSide\n";
        std::abort();
      }
      radius_ = std::max(
          radius_,
          std::max(std::abs(row - kCenter),
                   std::abs(column - kCenter)));
      for (const int neighbor :
           {site - kSide, site + kSide, site - 1, site + 1}) {
        touch(neighbor);
        state_[neighbor] += amount;
        enqueue(neighbor);
      }
      enqueue(site);
    }
  }

  Output output() const {
    return {value(odometer_, kC), value(odometer_, kD)};
  }

  int radius() const {
    return radius_;
  }

 private:
  Count value(const std::vector<Count>& field, int site) const {
    return stamp_[site] == generation_ ? field[site] : 0;
  }

  void touch(int site) {
    if (stamp_[site] == generation_) return;
    stamp_[site] = generation_;
    state_[site] = 0;
    odometer_[site] = 0;
    queued_[site] = 0;
  }

  void enqueue(int site) {
    if (state_[site] >= 4 && !queued_[site]) {
      queued_[site] = 1;
      pending_.push_back(site);
    }
  }

  void seed(int site, Count amount) {
    touch(site);
    state_[site] += amount;
    enqueue(site);
  }

  std::vector<Count> state_;
  std::vector<Count> odometer_;
  std::vector<std::uint32_t> stamp_;
  std::vector<std::uint8_t> queued_;
  std::vector<int> pending_;
  std::uint32_t generation_ = 0;
  int radius_ = 0;
};

bool correct(const Output& output, int a, int b) {
  return ((output[0] & 1) == (a & 1)) &&
         ((output[1] & 1) == (b & 1));
}

struct Trajectory {
  std::vector<Output> output;
  std::vector<int> radius_at_step;
  int radius = 0;
};

void fill_trajectory(
    Trajectory& result, int length, Count at_a, Count at_b) {
  result.output.resize(length + 1);
  result.radius_at_step.resize(length + 1);
  Pile pile;
  for (int grains = 1; grains <= length; ++grains) {
    pile.add(at_a, at_b);
    result.output[grains] = pile.output();
    result.radius_at_step[grains] = pile.radius();
  }
  result.radius = pile.radius();
}

}  // namespace

int main(int argc, char** argv) {
  int maximum_pulse = 50000;
  bool filter_only = false;
  if (argc == 3 && std::string(argv[1]) == "--maximum-pulse") {
    maximum_pulse = std::stoi(argv[2]);
  } else if (
      argc == 4 && std::string(argv[1]) == "--maximum-pulse" &&
      std::string(argv[3]) == "--filter-only") {
    maximum_pulse = std::stoi(argv[2]);
    filter_only = true;
  } else if (argc != 1) {
    std::cerr << "usage: " << argv[0]
              << " [--maximum-pulse P [--filter-only]]\n";
    return 2;
  }
  if (maximum_pulse < 1 || maximum_pulse > 150000) {
    std::cerr << "supported range is 1..150000\n";
    return 2;
  }

  const int length = 3 * maximum_pulse;
  Trajectory a_only;
  Trajectory b_only;
  Trajectory equal;
  std::thread a_thread(
      fill_trajectory, std::ref(a_only), length, 1, 0);
  std::thread b_thread(
      fill_trajectory, std::ref(b_only), length, 0, 1);
  std::thread equal_thread(
      fill_trajectory, std::ref(equal), length, 1, 1);
  a_thread.join();
  b_thread.join();
  equal_thread.join();

  // Reflection in the vertical axis swaps A<->B and C<->D.  Consequently
  // only one orientation of each unequal pair needs its own trajectory.
  Trajectory mixed_12;
  Trajectory mixed_13;
  Trajectory mixed_23;
  if (!filter_only) {
    std::thread thread_12(
        fill_trajectory, std::ref(mixed_12), maximum_pulse, 1, 2);
    std::thread thread_13(
        fill_trajectory, std::ref(mixed_13), maximum_pulse, 1, 3);
    std::thread thread_23(
        fill_trajectory, std::ref(mixed_23), maximum_pulse, 2, 3);
    thread_12.join();
    thread_13.join();
    thread_23.join();
  }

  std::vector<int> hits;
  std::vector<int> axis_equal_values;
  std::vector<int> after_12_values;
  std::vector<int> after_13_values;
  std::vector<int> after_23_values;
  std::uint64_t axis_equal_candidates = 0;
  for (int pulse = 1; pulse <= maximum_pulse; ++pulse) {
    bool valid = true;
    for (int amplitude = 1; amplitude <= 3; ++amplitude) {
      valid &= correct(
          a_only.output[amplitude * pulse], amplitude, 0);
      valid &= correct(
          b_only.output[amplitude * pulse], 0, amplitude);
      valid &= correct(
          equal.output[amplitude * pulse], amplitude, amplitude);
    }
    if (!valid) continue;
    ++axis_equal_candidates;
    axis_equal_values.push_back(pulse);
    if (filter_only) continue;
    valid &= correct(mixed_12.output[pulse], 1, 2);
    if (valid) after_12_values.push_back(pulse);
    valid &= correct(mixed_13.output[pulse], 1, 3);
    if (valid) after_13_values.push_back(pulse);
    valid &= correct(mixed_23.output[pulse], 2, 3);
    if (valid) after_23_values.push_back(pulse);
    if (!valid) continue;
    hits.push_back(pulse);
    std::cout << "FULL HIT p=" << pulse;
    if (hits.size() > 1) {
      std::cout << " gap=" << pulse - hits[hits.size() - 2];
    }
    std::cout << " max_case_radius="
              << equal.radius_at_step[3 * pulse] << "\n";
    std::cout.flush();
  }

  std::cout << "SCAN DONE max=" << maximum_pulse
            << " axis_equal_candidates=" << axis_equal_candidates
            << " full_hits=" << hits.size()
            << " radii=(" << a_only.radius << ","
            << b_only.radius << "," << equal.radius << ")\n";
  std::cout << "hits:";
  for (const int hit : hits) std::cout << " " << hit;
  std::cout << "\naxis_equal_candidates:";
  for (const int candidate : axis_equal_values) {
    std::cout << " " << candidate;
  }
  if (!filter_only) {
    std::cout << "\nafter_(1,2):";
    for (const int candidate : after_12_values) {
      std::cout << " " << candidate;
    }
    std::cout << "\nafter_(1,3):";
    for (const int candidate : after_13_values) {
      std::cout << " " << candidate;
    }
    std::cout << "\nafter_(2,3):";
    for (const int candidate : after_23_values) {
      std::cout << " " << candidate;
    }
  }
  std::cout << "\ngaps:";
  for (std::size_t index = 1; index < hits.size(); ++index) {
    std::cout << " " << hits[index] - hits[index - 1];
  }
  std::cout << "\n";
}
