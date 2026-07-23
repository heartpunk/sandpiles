#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

// Independent exhaustive checker for audit_halfadder672_exhaustive.cpp.
//
// Deliberate implementation differences:
//   * exactly one legal toppling per queue event;
//   * complete array resets between cores instead of generation stamps;
//   * a LIFO work stack instead of a batched FIFO queue;
//   * transient candidate flags instead of signature generations.

namespace {

constexpr int kSide = 129;
constexpr int kMiddle = kSide / 2;
constexpr int kOrigin = kMiddle * kSide + kMiddle;
constexpr int kA = kOrigin;
constexpr int kB = kOrigin + 1;
constexpr int kD = kOrigin + kSide;
constexpr int kC = kD + 1;
constexpr int kMaximumPacket = 672;

using Count = std::int64_t;
using Core = std::array<int, 4>;

class UnitPile {
 public:
  UnitPile()
      : state_(kSide * kSide),
        odometer_(kSide * kSide),
        touched_flag_(kSide * kSide),
        queued_(kSide * kSide) {
    touched_.reserve(4096);
    pending_.reserve(4096);
  }

  void reset(const Core& core) {
    std::fill(state_.begin(), state_.end(), 0);
    std::fill(odometer_.begin(), odometer_.end(), 0);
    std::fill(touched_flag_.begin(), touched_flag_.end(), 0);
    std::fill(queued_.begin(), queued_.end(), 0);
    touched_.clear();
    pending_.clear();
    touch(kA);
    touch(kB);
    touch(kD);
    touch(kC);
    state_[kA] = core[0];
    state_[kB] = core[1];
    state_[kD] = core[2];
    state_[kC] = core[3];
  }

  void increment_packet(int a, int b) {
    if (a) add(kA, a);
    if (b) add(kB, b);
    while (!pending_.empty()) {
      const int site = pending_.back();
      pending_.pop_back();
      queued_[site] = 0;
      if (state_[site] < 4) continue;

      const int row = site / kSide;
      const int column = site % kSide;
      if (row <= 0 || row >= kSide - 1 ||
          column <= 0 || column >= kSide - 1) {
        std::cerr << "artificial array boundary reached\n";
        std::abort();
      }

      // Exactly one legal toppling.
      state_[site] -= 4;
      ++odometer_[site];
      enqueue(site);
      const std::array<int, 4> neighbors = {
          site - kSide, site + kSide, site - 1, site + 1};
      for (const int neighbor : neighbors) {
        touch(neighbor);
        ++state_[neighbor];
        enqueue(neighbor);
      }
    }
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

  void add(int site, Count amount) {
    touch(site);
    state_[site] += amount;
    enqueue(site);
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

bool is_core_site(int site) {
  return site == kA || site == kB || site == kD || site == kC;
}

std::uint16_t target_signature(bool carry) {
  std::uint16_t result = 0;
  for (int a = 0; a < 4; ++a) {
    for (int b = 0; b < 4; ++b) {
      const bool value = carry ? ((a & 1) && (b & 1))
                               : ((a & 1) ^ (b & 1));
      if (value) result |= std::uint16_t(1U << (4 * a + b));
    }
  }
  return result;
}

}  // namespace

int main(int argc, char** argv) {
  int maximum_packet = kMaximumPacket;
  if (argc == 3 && std::string(argv[1]) == "--maximum-packet") {
    maximum_packet = std::stoi(argv[2]);
  } else if (argc != 1) {
    std::cerr << "usage: " << argv[0] << " [--maximum-packet P]\n";
    return 2;
  }
  if (maximum_packet <= 0 || maximum_packet > kMaximumPacket) {
    std::cerr << "this audit is dimensioned for 1 <= P <= 672\n";
    return 2;
  }

  const std::uint16_t carry_target = target_signature(true);
  const std::uint16_t sum_target = target_signature(false);
  std::array<UnitPile, 16> runs;
  std::vector<std::uint16_t> signatures(kSide * kSide);
  std::vector<std::uint8_t> candidate_flag(kSide * kSide);
  std::vector<int> candidate_sites;
  candidate_sites.reserve(4096);

  std::uint64_t core_packet_pairs = 0;
  std::uint64_t hits_before_672 = 0;
  std::uint64_t hits_at_672 = 0;
  std::uint64_t output_pairs_at_672 = 0;

  for (int code = 0; code < 256; ++code) {
    const Core core = decode_core(code);
    for (UnitPile& run : runs) run.reset(core);

    for (int packet = 1; packet <= maximum_packet; ++packet) {
      ++core_packet_pairs;
      for (int a = 0; a < 4; ++a) {
        for (int b = 0; b < 4; ++b) {
          runs[4 * a + b].increment_packet(a, b);
        }
      }

      candidate_sites.clear();
      for (int input = 0; input < 16; ++input) {
        for (const int site : runs[input].touched()) {
          if (!(runs[input].odometer(site) & 1)) continue;
          if (!candidate_flag[site]) {
            candidate_flag[site] = 1;
            signatures[site] = 0;
            candidate_sites.push_back(site);
          }
          signatures[site] |= std::uint16_t(1U << input);
        }
      }

      int carry_sites = 0;
      int sum_sites = 0;
      for (const int site : candidate_sites) {
        if (is_core_site(site)) continue;
        carry_sites += signatures[site] == carry_target;
        sum_sites += signatures[site] == sum_target;
      }
      if (carry_sites && sum_sites) {
        if (packet < 672) {
          ++hits_before_672;
        } else {
          ++hits_at_672;
          output_pairs_at_672 +=
              static_cast<std::uint64_t>(carry_sites) * sum_sites;
        }
      }
      for (const int site : candidate_sites) candidate_flag[site] = 0;
    }
  }

  std::cout << "UNIT AUDIT DONE maximum_packet=" << maximum_packet
            << " core_packet_pairs=" << core_packet_pairs
            << " hits_before_672=" << hits_before_672
            << " hits_at_672=" << hits_at_672
            << " output_pairs_at_672=" << output_pairs_at_672 << "\n";

  if (maximum_packet == kMaximumPacket) {
    return hits_before_672 == 0 && hits_at_672 == 10 &&
                   output_pairs_at_672 == 28
               ? 0
               : 3;
  }
  return 0;
}
