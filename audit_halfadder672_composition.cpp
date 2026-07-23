#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

// Bounded composition audit for the packet-672 half-adder.
//
// The half-adder's two canonical taps produce the following complete,
// 16-value count alphabets.  For each alphabet this program exhausts:
//   * all 256 stable 2x2 cores in a zero background;
//   * each of the four core cells as the abstract input;
//   * every lattice site reached by the largest input as a possible tap.
// It asks whether tap-odometer parity equals input-count parity on all 16
// counts.  This is an isolated abstract decoder test, not a physical
// attachment test.  A negative result is therefore a bounded caveat, not a
// general impossibility theorem.

namespace {

constexpr int kSide = 129;
constexpr int kMiddle = kSide / 2;
constexpr int kOrigin = kMiddle * kSide + kMiddle;
constexpr int kA = kOrigin;
constexpr int kB = kOrigin + 1;
constexpr int kD = kOrigin + kSide;
constexpr int kC = kD + 1;
constexpr std::array<int, 4> kCoreSites = {kA, kB, kD, kC};

constexpr std::array<int, 16> kSumCounts = {
    0, 49, 63, 164, 176, 196, 305, 317,
    333, 355, 480, 488, 514, 667, 683, 864,
};
constexpr std::array<int, 16> kCarryCounts = {
    0, 76, 110, 224, 255, 294, 398, 428,
    462, 504, 623, 650, 695, 860, 896, 1109,
};

using Count = std::int64_t;
using Core = std::array<int, 4>;

class Pile {
 public:
  Pile()
      : state_(kSide * kSide),
        odometer_(kSide * kSide),
        touched_flag_(kSide * kSide),
        queued_(kSide * kSide) {
    touched_.reserve(4096);
    pending_.reserve(4096);
  }

  void reset(const Core& core) {
    for (const int site : touched_) {
      state_[site] = 0;
      odometer_[site] = 0;
      touched_flag_[site] = 0;
      queued_[site] = 0;
    }
    touched_.clear();
    pending_.clear();
    for (int index = 0; index < 4; ++index) {
      touch(kCoreSites[index]);
      state_[kCoreSites[index]] = core[index];
    }
  }

  void add_and_stabilize(int input, Count amount) {
    touch(input);
    state_[input] += amount;
    enqueue(input);
    std::size_t head = 0;
    while (head < pending_.size()) {
      const int site = pending_[head++];
      queued_[site] = 0;
      const Count topplings = state_[site] / 4;
      if (!topplings) continue;

      const int row = site / kSide;
      const int column = site % kSide;
      if (row <= 0 || row >= kSide - 1 ||
          column <= 0 || column >= kSide - 1) {
        std::cerr << "artificial array boundary reached\n";
        std::abort();
      }

      state_[site] -= 4 * topplings;
      odometer_[site] += topplings;
      const std::array<int, 4> neighbors = {
          site - kSide, site + kSide, site - 1, site + 1};
      for (const int neighbor : neighbors) {
        touch(neighbor);
        state_[neighbor] += topplings;
        enqueue(neighbor);
      }
    }
    pending_.clear();
  }

  const std::vector<int>& touched() const { return touched_; }
  Count odometer(int site) const { return odometer_[site]; }

 private:
  void touch(int site) {
    if (touched_flag_[site]) return;
    touched_flag_[site] = 1;
    touched_.push_back(site);
  }

  void enqueue(int site) {
    if (state_[site] >= 4 && !queued_[site]) {
      queued_[site] = 1;
      pending_.push_back(site);
    }
  }

  std::vector<Count> state_;
  std::vector<Count> odometer_;
  std::vector<std::uint8_t> touched_flag_;
  std::vector<std::uint8_t> queued_;
  std::vector<int> touched_;
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

std::pair<int, int> coordinate(int site) {
  return {site / kSide - kMiddle, site % kSide - kMiddle};
}

template <std::size_t Size>
std::uint16_t target_signature(const std::array<int, Size>& counts) {
  static_assert(Size == 16);
  std::uint16_t result = 0;
  for (int index = 0; index < 16; ++index) {
    if (counts[index] & 1) {
      result |= std::uint16_t(1U << index);
    }
  }
  return result;
}

template <std::size_t Size>
int audit_alphabet(
    const char* name,
    const std::array<int, Size>& counts,
    std::uint64_t& searches,
    std::uint64_t& taps_tested) {
  static_assert(Size == 16);
  const std::uint16_t target = target_signature(counts);
  Pile pile;
  std::vector<std::uint16_t> signatures(kSide * kSide);
  int hits = 0;

  for (int input_index = 0; input_index < 4; ++input_index) {
    const int input = kCoreSites[input_index];
    for (int code = 0; code < 256; ++code) {
      const Core core = decode_core(code);
      pile.reset(core);
      std::fill(signatures.begin(), signatures.end(), 0);
      int previous = 0;
      for (int index = 0; index < 16; ++index) {
        pile.add_and_stabilize(input, counts[index] - previous);
        previous = counts[index];
        for (const int site : pile.touched()) {
          if (pile.odometer(site) & 1) {
            signatures[site] |= std::uint16_t(1U << index);
          }
        }
      }

      ++searches;
      taps_tested += pile.touched().size();
      for (const int site : pile.touched()) {
        if (signatures[site] != target) continue;
        const auto [row, column] = coordinate(site);
        std::cout << "DECODER HIT alphabet=" << name
                  << " input_index=" << input_index
                  << " core=(" << core[0] << "," << core[1] << ","
                  << core[2] << "," << core[3] << ") tap=("
                  << row << "," << column << ")\n";
        ++hits;
      }
    }
  }
  return hits;
}

}  // namespace

int main() {
  std::uint64_t searches = 0;
  std::uint64_t taps_tested = 0;
  const int sum_hits =
      audit_alphabet("SUM", kSumCounts, searches, taps_tested);
  const int carry_hits =
      audit_alphabet("CARRY", kCarryCounts, searches, taps_tested);

  std::cout << "COMPOSITION AUDIT DONE searches=" << searches
            << " taps_tested=" << taps_tested
            << " sum_decoder_hits=" << sum_hits
            << " carry_decoder_hits=" << carry_hits << "\n";
  return sum_hits == 0 && carry_hits == 0 ? 0 : 1;
}
