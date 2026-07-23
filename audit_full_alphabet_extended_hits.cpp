#include <array>
#include <cstdint>
#include <deque>
#include <future>
#include <iostream>
#include <string>
#include <vector>

// Independent batched replay for packets found by scan_full_alphabet_0022.
// Unlike that scanner, this starts every alphabet case from scratch and
// topples the full legal quotient from the front of a FIFO queue.

namespace {

constexpr int kSide = 769;
constexpr int kCenter = kSide / 2;
constexpr int kA = kCenter * kSide + kCenter;
constexpr int kB = kA + 1;
constexpr int kD = kA + kSide;
constexpr int kC = kD + 1;
using Count = std::int64_t;

struct Result {
  Count c = 0;
  Count d = 0;
  Count total_topplings = 0;
  int radius = 0;
  bool stable = false;
};

Result run(int pulse, int a, int b) {
  std::vector<Count> state(kSide * kSide);
  std::vector<Count> odometer(kSide * kSide);
  std::vector<std::uint8_t> queued(kSide * kSide);
  std::deque<int> queue;
  state[kD] = 2;
  state[kC] = 2;
  state[kA] += static_cast<Count>(a) * pulse;
  state[kB] += static_cast<Count>(b) * pulse;
  auto enqueue = [&](int site) {
    if (state[site] >= 4 && !queued[site]) {
      queued[site] = 1;
      queue.push_back(site);
    }
  };
  enqueue(kA);
  enqueue(kB);
  while (!queue.empty()) {
    const int site = queue.front();
    queue.pop_front();
    queued[site] = 0;
    const Count amount = state[site] / 4;
    if (!amount) continue;
    state[site] -= 4 * amount;
    odometer[site] += amount;
    const int row = site / kSide;
    const int column = site % kSide;
    if (row <= 0 || row >= kSide - 1 ||
        column <= 0 || column >= kSide - 1) {
      throw std::runtime_error("array boundary reached");
    }
    for (const int neighbor :
         {site - kSide, site + kSide, site - 1, site + 1}) {
      state[neighbor] += amount;
      enqueue(neighbor);
    }
  }

  Result result;
  result.c = odometer[kC];
  result.d = odometer[kD];
  result.stable = true;
  for (int row = 0; row < kSide; ++row) {
    for (int column = 0; column < kSide; ++column) {
      const int site = row * kSide + column;
      if (state[site] < 0 || state[site] >= 4) result.stable = false;
      result.total_topplings += odometer[site];
      if (odometer[site]) {
        result.radius = std::max(
            result.radius,
            std::max(std::abs(row - kCenter),
                     std::abs(column - kCenter)));
      }
    }
  }
  return result;
}

}  // namespace

int main(int argc, char** argv) {
  std::vector<int> pulses = {925, 14509, 17993};
  if (argc > 1) {
    pulses.clear();
    for (int index = 1; index < argc; ++index) {
      pulses.push_back(std::stoi(argv[index]));
    }
  }
  for (const int pulse : pulses) {
    bool valid = true;
    int maximum_radius = 0;
    std::array<std::future<Result>, 16> futures;
    for (int a = 0; a < 4; ++a) {
      for (int b = 0; b < 4; ++b) {
        futures[a * 4 + b] = std::async(
            std::launch::async, run, pulse, a, b);
      }
    }
    std::cout << "p=" << pulse << "\n";
    for (int a = 0; a < 4; ++a) {
      std::cout << "a=" << a << ":";
      for (int b = 0; b < 4; ++b) {
        const Result result = futures[a * 4 + b].get();
        valid &= result.stable;
        valid &= ((result.c & 1) == (a & 1));
        valid &= ((result.d & 1) == (b & 1));
        maximum_radius = std::max(maximum_radius, result.radius);
        std::cout << " (" << result.c << "," << result.d << ")";
      }
      std::cout << "\n";
    }
    std::cout << "valid=" << valid
              << " max_radius=" << maximum_radius << "\n";
    if (!valid) return 1;
  }
}
