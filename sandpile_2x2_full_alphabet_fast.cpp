#include <array>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

constexpr int SIDE = 257;
constexpr int ORIGIN = (SIDE / 2) * SIDE + SIDE / 2;
constexpr int A = ORIGIN;
constexpr int B = ORIGIN + 1;
constexpr int D = ORIGIN + SIDE;
constexpr int C = ORIGIN + SIDE + 1;

class Pile {
 public:
  Pile()
      : state_(SIDE * SIDE), odometer_(SIDE * SIDE),
        stamp_(SIDE * SIDE), queued_(SIDE * SIDE) {}

  void reset(const std::array<int, 4>& core) {
    ++generation_;
    if (generation_ == 0) {
      std::fill(stamp_.begin(), stamp_.end(), 0);
      generation_ = 1;
    }
    touch(A); touch(B); touch(D); touch(C);
    state_[A] = core[0];
    state_[B] = core[1];
    state_[D] = core[2];
    state_[C] = core[3];
  }

  void add(int a_grains, int b_grains) {
    queue_.clear();
    head_ = 0;
    if (a_grains) seed(A, a_grains);
    if (b_grains) seed(B, b_grains);
    while (head_ < queue_.size()) {
      const int site = queue_[head_++];
      queued_[site] = 0;
      const int amount = state_[site] / 4;
      if (!amount) continue;
      state_[site] -= 4 * amount;
      odometer_[site] += amount;
      for (const int neighbor :
           {site - SIDE, site + SIDE, site - 1, site + 1}) {
        touch(neighbor);
        state_[neighbor] += amount;
        if (state_[neighbor] >= 4 && !queued_[neighbor]) {
          queued_[neighbor] = 1;
          queue_.push_back(neighbor);
        }
      }
    }
  }

  std::array<int, 2> outputs() const {
    return {odometer_[C], odometer_[D]};
  }

 private:
  void touch(int site) {
    if (stamp_[site] == generation_) return;
    stamp_[site] = generation_;
    state_[site] = 0;
    odometer_[site] = 0;
    queued_[site] = 0;
  }

  void seed(int site, int amount) {
    touch(site);
    state_[site] += amount;
    if (state_[site] >= 4 && !queued_[site]) {
      queued_[site] = 1;
      queue_.push_back(site);
    }
  }

  std::vector<int> state_;
  std::vector<int> odometer_;
  std::vector<std::uint32_t> stamp_;
  std::vector<std::uint8_t> queued_;
  std::vector<int> queue_;
  std::size_t head_ = 0;
  std::uint32_t generation_ = 0;
};

int main(int argc, char** argv) {
  int maximum_pulse = 5000;
  int asymmetric_minimum = 0;
  int asymmetric_maximum = 0;
  int asymmetric_core_code = 0;
  if (argc == 3 && std::string(argv[1]) == "--maximum-pulse") {
    maximum_pulse = std::stoi(argv[2]);
  } else if (
      argc == 5 && std::string(argv[1]) == "--asymmetric-min" &&
      std::string(argv[3]) == "--asymmetric-max") {
    asymmetric_minimum = std::stoi(argv[2]);
    asymmetric_maximum = std::stoi(argv[4]);
  } else if (
      argc == 7 && std::string(argv[1]) == "--asymmetric-min" &&
      std::string(argv[3]) == "--asymmetric-max" &&
      std::string(argv[5]) == "--core-code") {
    asymmetric_minimum = std::stoi(argv[2]);
    asymmetric_maximum = std::stoi(argv[4]);
    asymmetric_core_code = std::stoi(argv[6]);
  } else if (argc != 1) {
    std::cerr << "usage: " << argv[0]
              << " [--maximum-pulse N | --asymmetric-min L "
                 "--asymmetric-max H [--core-code C]]\n";
    return 2;
  }

  Pile north, west, both, scratch;
  if (asymmetric_minimum) {
    int value = asymmetric_core_code;
    std::array<int, 4> core{};
    for (int q = 3; q >= 0; --q) {
      core[q] = value % 4;
      value /= 4;
    }
    std::vector<int> axis_valid;
    for (int pulse = asymmetric_minimum;
         pulse <= asymmetric_maximum; ++pulse) {
      bool valid = true;
      for (int amplitude = 1; amplitude <= 3; ++amplitude) {
        scratch.reset(core);
        scratch.add(amplitude * pulse, 0);
        const auto output = scratch.outputs();
        valid &= ((output[0] & 1) == (amplitude & 1));
        valid &= ((output[1] & 1) == 0);
      }
      if (valid) axis_valid.push_back(pulse);
    }
    std::cout << "axis_valid=" << axis_valid.size() << "\n";
    int best = 33;
    int best_a = 0;
    int best_b = 0;
    for (const int a_pulse : axis_valid) {
      for (const int b_pulse : axis_valid) {
        int errors = 0;
        for (int a = 0; a < 4; ++a) {
          for (int b = 0; b < 4; ++b) {
            scratch.reset(core);
            scratch.add(a * a_pulse, b * b_pulse);
            const auto output = scratch.outputs();
            errors += ((output[0] & 1) != (a & 1));
            errors += ((output[1] & 1) != (b & 1));
          }
        }
        if (errors < best) {
          best = errors;
          best_a = a_pulse;
          best_b = b_pulse;
          std::cout << "asymmetric best errors=" << best
                    << " a_pulse=" << best_a
                    << " b_pulse=" << best_b << "\n";
          std::cout.flush();
        }
        if (!errors) {
          std::cout << "ASYMMETRIC FULL HIT\n";
          return 0;
        }
      }
    }
    std::cout << "ASYMMETRIC DONE best_errors=" << best
              << " a_pulse=" << best_a << " b_pulse=" << best_b
              << "\n";
    return 0;
  }

  int best_errors = 33;
  int best_pulse = 0;
  std::array<int, 4> best_core{};
  std::array<std::array<std::array<int, 2>, 4>, 4> best_table{};
  std::uint64_t boolean_hits = 0;
  std::uint64_t full_hits = 0;

  for (int code = 0; code < 256; ++code) {
    int value = code;
    std::array<int, 4> core{};
    for (int q = 3; q >= 0; --q) {
      core[q] = value % 4;
      value /= 4;
    }
    north.reset(core);
    west.reset(core);
    both.reset(core);
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
      bool pruned = false;
      for (int a = 0; a < 4; ++a) {
        for (int b = 0; b < 4; ++b) {
          scratch.reset(core);
          scratch.add(a * pulse, b * pulse);
          table[a][b] = scratch.outputs();
          errors += ((table[a][b][0] & 1) != (a & 1));
          errors += ((table[a][b][1] & 1) != (b & 1));
          if (
              (best_errors > 0 && errors >= best_errors)
              || (best_errors == 0 && errors > 0)
          ) {
            pruned = true;
            break;
          }
        }
        if (pruned) break;
      }
      if (errors < best_errors) {
        best_errors = errors;
        best_pulse = pulse;
        best_core = core;
        best_table = table;
        std::cout << "best errors=" << errors << " pulse=" << pulse
                  << " core=(" << core[0] << "," << core[1] << ","
                  << core[2] << "," << core[3] << ")\n";
        std::cout.flush();
      }
      if (!pruned && errors == 0) {
        ++full_hits;
        std::cout << "FULL HIT pulse=" << pulse << " core=("
                  << core[0] << "," << core[1] << ","
                  << core[2] << "," << core[3] << ")\n";
      }
    }
    if ((code + 1) % 16 == 0) {
      std::cout << "cores=" << code + 1 << "/256 boolean_hits="
                << boolean_hits << " best_errors=" << best_errors << "\n";
      std::cout.flush();
    }
  }

  std::cout << "DONE max_pulse=" << maximum_pulse
            << " boolean_hits=" << boolean_hits
            << " full_hits=" << full_hits
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
