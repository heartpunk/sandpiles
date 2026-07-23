#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <utility>
#include <vector>

// Exhaustive audit for a full-alphabet odometer-parity half-adder in the
// ordinary Abelian sandpile on Z^2.
//
// Scope:
//   * zeros outside a stable 2x2 core;
//   * all 4^4 stable cores, stored in row-major A,B,D,C order;
//   * inputs A=(0,0), B=(0,1);
//   * one equal positive integer packet p at both inputs;
//   * amplitudes a,b in {0,1,2,3};
//   * two distinct external lattice taps;
//   * tap odometer parities XOR(a mod 2,b mod 2) and
//     AND(a mod 2,b mod 2), respectively.
//
// The 129x129 array is an implementation detail.  The all-3 core with the
// largest additions dominates every audited initial configuration.  Its
// odometer support is measured below and checked to remain far from the
// artificial boundary.

namespace {

constexpr int kSide = 129;
constexpr int kMiddle = kSide / 2;
constexpr int kOrigin = kMiddle * kSide + kMiddle;
constexpr int kA = kOrigin;
constexpr int kB = kOrigin + 1;
constexpr int kD = kOrigin + kSide;
constexpr int kC = kD + 1;
constexpr int kDefaultMaximumPacket = 672;

using Count = std::int64_t;
using Core = std::array<int, 4>;

struct Bounds {
  int row_min = 0;
  int row_max = 0;
  int column_min = 0;
  int column_max = 0;
  int sites = 0;
  int linf_radius = 0;
};

class Pile {
 public:
  Pile()
      : state_(kSide * kSide),
        odometer_(kSide * kSide),
        stamp_(kSide * kSide),
        queued_(kSide * kSide) {
    touched_.reserve(4096);
    pending_.reserve(4096);
  }

  void reset(const Core& core) {
    ++generation_;
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

  // Advance the common packet size p by one.  By abelian composition, after
  // p calls this run has exactly the final state and total odometer obtained
  // by stabilizing core + p*a at A + p*b at B in one shot.
  void increment_packet(int a, int b) {
    if (a) add(kA, a);
    if (b) add(kB, b);
    std::size_t head = 0;
    while (head < pending_.size()) {
      const int site = pending_[head++];
      queued_[site] = 0;
      const Count amount = state_[site] / 4;
      if (!amount) continue;

      const int row = site / kSide;
      const int column = site % kSide;
      if (row <= 0 || row >= kSide - 1 ||
          column <= 0 || column >= kSide - 1) {
        std::cerr << "artificial array boundary reached\n";
        std::abort();
      }

      state_[site] -= 4 * amount;
      odometer_[site] += amount;
      const std::array<int, 4> neighbors = {
          site - kSide, site + kSide, site - 1, site + 1};
      for (const int neighbor : neighbors) {
        touch(neighbor);
        state_[neighbor] += amount;
        enqueue(neighbor);
      }
    }
    pending_.clear();
  }

  const std::vector<int>& touched() const { return touched_; }

  Count odometer(int site) const {
    return stamp_[site] == generation_ ? odometer_[site] : 0;
  }

  Bounds odometer_bounds() const {
    Bounds result;
    bool first = true;
    for (const int site : touched_) {
      if (!odometer_[site]) continue;
      const int row = site / kSide - kMiddle;
      const int column = site % kSide - kMiddle;
      if (first) {
        result.row_min = result.row_max = row;
        result.column_min = result.column_max = column;
        first = false;
      } else {
        result.row_min = std::min(result.row_min, row);
        result.row_max = std::max(result.row_max, row);
        result.column_min = std::min(result.column_min, column);
        result.column_max = std::max(result.column_max, column);
      }
      ++result.sites;
      result.linf_radius = std::max(
          result.linf_radius, std::max(std::abs(row), std::abs(column)));
    }
    return result;
  }

 private:
  void touch(int site) {
    if (stamp_[site] == generation_) return;
    stamp_[site] = generation_;
    state_[site] = 0;
    odometer_[site] = 0;
    queued_[site] = 0;
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
  std::vector<std::uint32_t> stamp_;
  std::vector<std::uint8_t> queued_;
  std::vector<int> touched_;
  std::vector<int> pending_;
  std::uint32_t generation_ = 0;
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

std::pair<int, int> coordinate(int site) {
  return {site / kSide - kMiddle, site % kSide - kMiddle};
}

std::uint16_t target_signature(bool carry) {
  std::uint16_t result = 0;
  for (int a = 0; a < 4; ++a) {
    for (int b = 0; b < 4; ++b) {
      const bool bit = carry ? ((a & 1) && (b & 1))
                             : ((a & 1) ^ (b & 1));
      if (bit) result |= std::uint16_t(1U << (4 * a + b));
    }
  }
  return result;
}

void print_sites(const std::vector<int>& sites) {
  for (const int site : sites) {
    const auto [row, column] = coordinate(site);
    std::cout << "(" << row << "," << column << ")";
  }
}

}  // namespace

int main(int argc, char** argv) {
  int maximum_packet = kDefaultMaximumPacket;
  bool allow_core_outputs = false;
  for (int index = 1; index < argc; ++index) {
    const std::string argument = argv[index];
    if (argument == "--allow-core-outputs") {
      allow_core_outputs = true;
    } else if (argument == "--maximum-packet" && index + 1 < argc) {
      maximum_packet = std::stoi(argv[++index]);
    } else {
      std::cerr
          << "usage: " << argv[0]
          << " [--maximum-packet P] [--allow-core-outputs]\n";
      return 2;
    }
  }
  if (maximum_packet <= 0 ||
      maximum_packet > kDefaultMaximumPacket) {
    std::cerr << "this audit is dimensioned for 1 <= P <= 672\n";
    return 2;
  }

  const std::uint16_t carry_target = target_signature(true);
  const std::uint16_t sum_target = target_signature(false);
  std::array<Pile, 16> runs;
  std::vector<std::uint16_t> signatures(kSide * kSide);
  std::vector<std::uint32_t> signature_stamp(kSide * kSide);
  std::vector<int> candidate_sites;
  candidate_sites.reserve(4096);
  std::uint32_t signature_generation = 0;

  std::uint64_t core_packet_pairs = 0;
  std::uint64_t half_adder_core_packet_hits = 0;
  std::uint64_t half_adder_output_pairs = 0;
  std::uint64_t hits_before_672 = 0;
  int least_packet = std::numeric_limits<int>::max();
  std::vector<Core> least_cores;

  for (int code = 0; code < 256; ++code) {
    const Core core = decode_core(code);
    for (Pile& run : runs) run.reset(core);

    for (int packet = 1; packet <= maximum_packet; ++packet) {
      ++core_packet_pairs;
      for (int a = 0; a < 4; ++a) {
        for (int b = 0; b < 4; ++b) {
          runs[4 * a + b].increment_packet(a, b);
        }
      }

      ++signature_generation;
      candidate_sites.clear();
      for (int input = 0; input < 16; ++input) {
        for (const int site : runs[input].touched()) {
          if (!(runs[input].odometer(site) & 1)) continue;
          if (signature_stamp[site] != signature_generation) {
            signature_stamp[site] = signature_generation;
            signatures[site] = 0;
            candidate_sites.push_back(site);
          }
          signatures[site] |= std::uint16_t(1U << input);
        }
      }

      std::vector<int> carry_sites;
      std::vector<int> sum_sites;
      for (const int site : candidate_sites) {
        if (!allow_core_outputs && is_core_site(site)) continue;
        if (signatures[site] == carry_target) carry_sites.push_back(site);
        if (signatures[site] == sum_target) sum_sites.push_back(site);
      }
      if (carry_sites.empty() || sum_sites.empty()) continue;

      ++half_adder_core_packet_hits;
      half_adder_output_pairs +=
          static_cast<std::uint64_t>(carry_sites.size()) *
          static_cast<std::uint64_t>(sum_sites.size());
      if (packet < 672) ++hits_before_672;
      if (packet < least_packet) {
        least_packet = packet;
        least_cores.clear();
      }
      if (packet == least_packet) least_cores.push_back(core);

      std::cout << "HALF_ADDER packet=" << packet
                << " core=(" << core[0] << "," << core[1] << ","
                << core[2] << "," << core[3] << ") carry=";
      print_sites(carry_sites);
      std::cout << " sum=";
      print_sites(sum_sites);
      std::cout << "\n";
    }
  }

  Pile dominating;
  dominating.reset({3, 3, 3, 3});
  for (int packet = 1; packet <= maximum_packet; ++packet) {
    dominating.increment_packet(3, 3);
  }
  const Bounds bounds = dominating.odometer_bounds();
  if (bounds.linf_radius >= kMiddle - 2) {
    std::cerr << "dominating support is too close to the boundary\n";
    return 3;
  }

  std::cout << "AUDIT DONE maximum_packet=" << maximum_packet
            << " allow_core_outputs=" << allow_core_outputs
            << " core_packet_pairs=" << core_packet_pairs
            << " half_adder_core_packet_hits="
            << half_adder_core_packet_hits
            << " half_adder_output_pairs=" << half_adder_output_pairs
            << " hits_before_672=" << hits_before_672
            << " least_packet="
            << (half_adder_core_packet_hits ? least_packet : 0)
            << " least_core_count=" << least_cores.size()
            << " dominating_sites=" << bounds.sites
            << " dominating_bbox=[" << bounds.row_min << ","
            << bounds.row_max << "," << bounds.column_min << ","
            << bounds.column_max << "]"
            << " dominating_linf_radius=" << bounds.linf_radius
            << "\n";

  if (maximum_packet == kDefaultMaximumPacket &&
      !allow_core_outputs) {
    const bool witness_present =
        least_packet == 672 &&
        std::find(
            least_cores.begin(), least_cores.end(), Core{0, 3, 3, 2}) !=
            least_cores.end();
    return hits_before_672 == 0 &&
                   half_adder_core_packet_hits == 10 &&
                   half_adder_output_pairs == 28 &&
                   least_cores.size() == 10 &&
                   witness_present &&
                   bounds.sites == 1774 &&
                   bounds.row_min == -23 &&
                   bounds.row_max == 23 &&
                   bounds.column_min == -22 &&
                   bounds.column_max == 23 &&
                   bounds.linf_radius == 23
               ? 0
               : 4;
  }
  if (maximum_packet == kDefaultMaximumPacket &&
      allow_core_outputs) {
    return hits_before_672 == 0 &&
                   half_adder_core_packet_hits == 10 &&
                   half_adder_output_pairs == 28 &&
                   least_cores.size() == 10 &&
                   least_packet == 672
               ? 0
               : 5;
  }
  return 0;
}
