#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <queue>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using Site = std::int64_t;

static Site pack(int row, int column) {
  return (static_cast<Site>(row) << 32) ^
         static_cast<std::uint32_t>(column);
}

static std::pair<int, int> unpack(Site site) {
  return {static_cast<int>(site >> 32),
          static_cast<int>(static_cast<std::uint32_t>(site))};
}

constexpr int A = 0;
constexpr int B = 1;
constexpr int D = 2;
constexpr int C = 3;

class Pile {
 public:
  explicit Pile(const std::array<int, 4>& core) {
    state_[pack(0, 0)] = core[A];
    state_[pack(0, 1)] = core[B];
    state_[pack(1, 0)] = core[D];
    state_[pack(1, 1)] = core[C];
  }

  void add(int a_grains, int b_grains) {
    std::queue<Site> queue;
    std::unordered_map<Site, bool> queued;
    auto seed = [&](Site site, int amount) {
      state_[site] += amount;
      if (state_[site] >= 4 && !queued[site]) {
        queued[site] = true;
        queue.push(site);
      }
    };
    if (a_grains) seed(pack(0, 0), a_grains);
    if (b_grains) seed(pack(0, 1), b_grains);
    while (!queue.empty()) {
      const Site site = queue.front();
      queue.pop();
      queued[site] = false;
      const int amount = state_[site] / 4;
      if (!amount) continue;
      state_[site] -= 4 * amount;
      odometer_[site] += amount;
      const auto [row, column] = unpack(site);
      for (const Site neighbor :
           {pack(row - 1, column), pack(row + 1, column),
            pack(row, column - 1), pack(row, column + 1)}) {
        state_[neighbor] += amount;
        if (state_[neighbor] >= 4 && !queued[neighbor]) {
          queued[neighbor] = true;
          queue.push(neighbor);
        }
      }
    }
  }

  std::array<int, 2> outputs() const {
    return {get(odometer_, pack(1, 1)),
            get(odometer_, pack(1, 0))};
  }

 private:
  static int get(const std::unordered_map<Site, int>& values, Site site) {
    const auto found = values.find(site);
    return found == values.end() ? 0 : found->second;
  }

  std::unordered_map<Site, int> state_;
  std::unordered_map<Site, int> odometer_;
};

static std::array<int, 2> run(const std::array<int, 4>& core,
                              int a_grains, int b_grains) {
  Pile pile(core);
  pile.add(a_grains, b_grains);
  return pile.outputs();
}

int main(int argc, char** argv) {
  int maximum_pulse = 10000;
  if (argc == 3 && std::string(argv[1]) == "--maximum-pulse") {
    maximum_pulse = std::stoi(argv[2]);
  } else if (argc != 1) {
    std::cerr << "usage: " << argv[0] << " [--maximum-pulse N]\n";
    return 2;
  }
  int best_errors = 33;
  std::array<int, 4> best_core{};
  int best_pulse = 0;
  std::array<std::array<std::array<int, 2>, 4>, 4> best_table{};
  std::uint64_t boolean_hits = 0;

  for (int code = 0; code < 256; ++code) {
    int value = code;
    std::array<int, 4> core{};
    for (int q = 3; q >= 0; --q) {
      core[q] = value % 4;
      value /= 4;
    }
    Pile north(core);
    Pile west(core);
    Pile both(core);
    for (int pulse = 1; pulse <= maximum_pulse; ++pulse) {
      north.add(1, 0);
      west.add(0, 1);
      both.add(1, 1);
      const auto n = north.outputs();
      const auto w = west.outputs();
      const auto nw = both.outputs();
      if ((n[0] & 1) != 1 || (n[1] & 1) != 0 ||
          (w[0] & 1) != 0 || (w[1] & 1) != 1 ||
          (nw[0] & 1) != 1 || (nw[1] & 1) != 1) {
        continue;
      }
      ++boolean_hits;
      int errors = 0;
      std::array<std::array<std::array<int, 2>, 4>, 4> table{};
      for (int a = 0; a < 4; ++a) {
        for (int b = 0; b < 4; ++b) {
          table[a][b] = run(core, a * pulse, b * pulse);
          errors += ((table[a][b][0] & 1) != (a & 1));
          errors += ((table[a][b][1] & 1) != (b & 1));
        }
      }
      if (errors < best_errors) {
        best_errors = errors;
        best_core = core;
        best_pulse = pulse;
        best_table = table;
        std::cout << "best errors=" << errors << " pulse=" << pulse
                  << " core=(" << core[0] << "," << core[1] << ","
                  << core[2] << "," << core[3] << ")\n";
        std::cout.flush();
      }
      if (errors == 0) {
        std::cout << "FULL HIT\n";
        goto finished;
      }
    }
    if ((code + 1) % 16 == 0) {
      std::cout << "cores=" << code + 1 << "/256 boolean_hits="
                << boolean_hits << " best_errors=" << best_errors << "\n";
      std::cout.flush();
    }
  }

finished:
  std::cout << "DONE max_pulse=" << maximum_pulse
            << " boolean_hits=" << boolean_hits
            << " best_errors=" << best_errors
            << " best_pulse=" << best_pulse << " best_core=("
            << best_core[0] << "," << best_core[1] << ","
            << best_core[2] << "," << best_core[3] << ")\n";
  for (int a = 0; a < 4; ++a) {
    std::cout << "a=" << a << ":";
    for (int b = 0; b < 4; ++b) {
      std::cout << " (" << best_table[a][b][0] << ","
                << best_table[a][b][1] << ")";
    }
    std::cout << "\n";
  }
}
