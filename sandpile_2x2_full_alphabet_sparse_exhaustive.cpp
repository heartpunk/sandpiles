#include <array>
#include <cstdint>
#include <iostream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

using Site = std::uint64_t;
using Count = std::int64_t;

static Site pack(std::int32_t row, std::int32_t column) {
  return (static_cast<Site>(static_cast<std::uint32_t>(row)) << 32) |
         static_cast<std::uint32_t>(column);
}

static std::pair<std::int32_t, std::int32_t> unpack(Site site) {
  return {
      static_cast<std::int32_t>(static_cast<std::uint32_t>(site >> 32)),
      static_cast<std::int32_t>(static_cast<std::uint32_t>(site)),
  };
}

constexpr int A_INDEX = 0;
constexpr int B_INDEX = 1;
constexpr int D_INDEX = 2;
constexpr int C_INDEX = 3;

const Site A = pack(0, 0);
const Site B = pack(0, 1);
const Site D = pack(1, 0);
const Site C = pack(1, 1);

class SparsePile {
 public:
  explicit SparsePile(const std::array<int, 4>& core) {
    state_.reserve(4096);
    odometer_.reserve(4096);
    state_[A] = core[A_INDEX];
    state_[B] = core[B_INDEX];
    state_[D] = core[D_INDEX];
    state_[C] = core[C_INDEX];
  }

  void add(Count a_grains, Count b_grains) {
    std::vector<Site> pending;
    std::unordered_set<Site> queued;
    pending.reserve(4096);
    queued.reserve(4096);
    std::size_t head = 0;

    auto enqueue_if_unstable = [&](Site site) {
      if (state_[site] >= 4 && queued.insert(site).second) {
        pending.push_back(site);
      }
    };
    if (a_grains) {
      state_[A] += a_grains;
      enqueue_if_unstable(A);
    }
    if (b_grains) {
      state_[B] += b_grains;
      enqueue_if_unstable(B);
    }

    while (head < pending.size()) {
      const Site site = pending[head++];
      queued.erase(site);
      const Count amount = state_[site] / 4;
      if (!amount) continue;
      state_[site] -= 4 * amount;
      odometer_[site] += amount;
      const auto [row, column] = unpack(site);
      const std::array<Site, 4> neighbors = {
          pack(row - 1, column),
          pack(row + 1, column),
          pack(row, column - 1),
          pack(row, column + 1),
      };
      for (const Site neighbor : neighbors) {
        state_[neighbor] += amount;
        enqueue_if_unstable(neighbor);
      }
    }
  }

  std::array<Count, 2> outputs() const {
    return {get(odometer_, C), get(odometer_, D)};
  }

 private:
  static Count get(
      const std::unordered_map<Site, Count>& values, Site site) {
    const auto found = values.find(site);
    return found == values.end() ? 0 : found->second;
  }

  std::unordered_map<Site, Count> state_;
  std::unordered_map<Site, Count> odometer_;
};

static std::array<Count, 2> run(
    const std::array<int, 4>& core, int pulse, int a, int b) {
  SparsePile pile(core);
  pile.add(static_cast<Count>(a) * pulse,
           static_cast<Count>(b) * pulse);
  return pile.outputs();
}

static bool has_target_parity(
    const std::array<Count, 2>& output, int a, int b) {
  return ((output[0] & 1) == (a & 1)) &&
         ((output[1] & 1) == (b & 1));
}

int main(int argc, char** argv) {
  int maximum_pulse = 925;
  if (argc == 3 && std::string(argv[1]) == "--maximum-pulse") {
    maximum_pulse = std::stoi(argv[2]);
  } else if (argc != 1) {
    std::cerr << "usage: " << argv[0] << " [--maximum-pulse N]\n";
    return 2;
  }

  const std::array<std::array<int, 2>, 12> remaining_cases = {{
      {3, 0}, {0, 3}, {2, 0}, {0, 2},
      {1, 2}, {2, 1}, {1, 3}, {3, 1},
      {2, 2}, {2, 3}, {3, 2}, {3, 3},
  }};
  std::uint64_t boolean_hits = 0;
  std::uint64_t full_hits = 0;
  int least_full_pulse = 0;

  for (int code = 0; code < 256; ++code) {
    int value = code;
    std::array<int, 4> core{};
    for (int index = 3; index >= 0; --index) {
      core[index] = value % 4;
      value /= 4;
    }
    SparsePile a_only(core);
    SparsePile b_only(core);
    SparsePile both(core);

    for (int pulse = 1; pulse <= maximum_pulse; ++pulse) {
      a_only.add(1, 0);
      b_only.add(0, 1);
      both.add(1, 1);
      if (!has_target_parity(a_only.outputs(), 1, 0) ||
          !has_target_parity(b_only.outputs(), 0, 1) ||
          !has_target_parity(both.outputs(), 1, 1)) {
        continue;
      }
      ++boolean_hits;

      bool valid = true;
      for (const auto& input : remaining_cases) {
        if (!has_target_parity(
                run(core, pulse, input[0], input[1]),
                input[0], input[1])) {
          valid = false;
          break;
        }
      }
      if (!valid) continue;

      ++full_hits;
      if (!least_full_pulse || pulse < least_full_pulse) {
        least_full_pulse = pulse;
      }
      std::cout << "FULL HIT pulse=" << pulse << " core=("
                << core[0] << "," << core[1] << ","
                << core[2] << "," << core[3] << ")\n";
      for (int a = 0; a < 4; ++a) {
        std::cout << "a=" << a << ":";
        for (int b = 0; b < 4; ++b) {
          const auto output = run(core, pulse, a, b);
          std::cout << " (" << output[0] << "," << output[1] << ")";
        }
        std::cout << "\n";
      }
    }
  }

  std::cout << "DONE maximum_pulse=" << maximum_pulse
            << " core_packet_pairs="
            << static_cast<std::uint64_t>(maximum_pulse) * 256
            << " boolean_hits=" << boolean_hits
            << " full_hits=" << full_hits
            << " least_full_pulse=" << least_full_pulse << "\n";
}
