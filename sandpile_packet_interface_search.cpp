#include <array>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

// Exact bounded search for a tiny ordinary-Z^2 transducer whose odometer
// parity matches the parity of every output count produced by the p=925
// packet gate.  A 2x2 stable core is embedded in zeros; the packet count is
// added at its upper-left cell.  Every lattice site reached by the avalanche
// is considered as a possible output tap.

constexpr int SIDE = 257;
constexpr int ORIGIN = (SIDE / 2) * SIDE + SIDE / 2;
constexpr int A = ORIGIN;
constexpr int B = ORIGIN + 1;
constexpr int D = ORIGIN + SIDE;
constexpr int C = ORIGIN + SIDE + 1;

constexpr std::array<int, 16> COUNTS = {
    0, 237, 300, 572, 625, 698, 941, 1010,
    1073, 1130, 1405, 1456, 1531, 1883, 1946, 2371,
};
constexpr std::array<int, 16> COUNTS_STAGE2 = {
    0, 35, 50, 124, 135, 164, 239, 266,
    283, 304, 405, 426, 445, 585, 602, 779,
};

class Pile {
 public:
  Pile()
      : state_(SIDE * SIDE), odometer_(SIDE * SIDE),
        queued_(SIDE * SIDE), touched_flag_(SIDE * SIDE) {
    queue_.reserve(8192);
    touched_.reserve(8192);
  }

  void reset(const std::array<int, 4>& core) {
    for (const int site : touched_) {
      state_[site] = 0;
      odometer_[site] = 0;
      queued_[site] = 0;
      touched_flag_[site] = 0;
    }
    touched_.clear();
    touch(A); touch(B); touch(D); touch(C);
    state_[A] = core[0];
    state_[B] = core[1];
    state_[D] = core[2];
    state_[C] = core[3];
  }

  void add(int site, int grains) {
    state_[site] += grains;
    queue_.clear();
    std::size_t head = 0;
    if (state_[site] >= 4) {
      queued_[site] = 1;
      queue_.push_back(site);
    }
    while (head < queue_.size()) {
      const int current = queue_[head++];
      queued_[current] = 0;
      const int amount = state_[current] / 4;
      if (!amount) continue;
      state_[current] -= 4 * amount;
      odometer_[current] += amount;
      for (const int neighbor :
           {current - SIDE, current + SIDE,
            current - 1, current + 1}) {
        touch(neighbor);
        state_[neighbor] += amount;
        if (state_[neighbor] >= 4 && !queued_[neighbor]) {
          queued_[neighbor] = 1;
          queue_.push_back(neighbor);
        }
      }
    }
  }

  const std::vector<int>& touched() const { return touched_; }
  int odometer(int site) const { return odometer_[site]; }

 private:
  void touch(int site) {
    if (touched_flag_[site]) return;
    touched_flag_[site] = 1;
    touched_.push_back(site);
  }

  std::vector<int> state_;
  std::vector<int> odometer_;
  std::vector<std::uint8_t> queued_;
  std::vector<std::uint8_t> touched_flag_;
  std::vector<int> queue_;
  std::vector<int> touched_;
};

int main(int argc, char** argv) {
  const bool stage2 =
      argc == 2 && std::string(argv[1]) == "--stage2";
  if (argc > 2 || (argc == 2 && !stage2)) {
    std::cerr << "usage: " << argv[0] << " [--stage2]\n";
    return 2;
  }
  const auto& counts = stage2 ? COUNTS_STAGE2 : COUNTS;
  std::uint16_t target = 0;
  for (int index = 0; index < static_cast<int>(counts.size()); ++index) {
    if (counts[index] & 1) target |= std::uint16_t(1U << index);
  }

  Pile pile;
  std::vector<std::uint16_t> signature(SIDE * SIDE);
  std::vector<std::uint32_t> stamp(SIDE * SIDE);
  std::uint32_t generation = 0;
  int hits = 0;
  for (int code = 0; code < 256; ++code) {
    std::array<int, 4> core{};
    int value = code;
    for (int index = 3; index >= 0; --index) {
      core[index] = value % 4;
      value /= 4;
    }
    pile.reset(core);
    ++generation;
    int previous = 0;
    for (int index = 0; index < static_cast<int>(counts.size()); ++index) {
      pile.add(A, counts[index] - previous);
      previous = counts[index];
      for (const int site : pile.touched()) {
        if (stamp[site] != generation) {
          stamp[site] = generation;
          signature[site] = 0;
        }
        if (pile.odometer(site) & 1) {
          signature[site] |= std::uint16_t(1U << index);
        }
      }
    }
    for (const int site : pile.touched()) {
      if (signature[site] != target) continue;
      const int row = site / SIDE - SIDE / 2;
      const int column = site % SIDE - SIDE / 2;
      std::cout << "HIT core=(" << core[0] << "," << core[1]
                << "," << core[2] << "," << core[3] << ")"
                << " input=(0,0) tap=(" << row << "," << column
                << ")\n";
      ++hits;
      if (hits >= 100) {
        std::cout << "STOP hits=" << hits << "\n";
        return 0;
      }
    }
  }
  std::cout << "DONE cores=256 hits=" << hits << "\n";
}
