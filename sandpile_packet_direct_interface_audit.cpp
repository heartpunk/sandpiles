#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <utility>
#include <vector>

// Exhaust every rotation/reflection and every free-neighbor placement of two
// copies of the tiny parity-preserving 2x2 packet transducer around the two
// bottom taps of the p=925 gate.  This is a bounded physical-composition
// audit: all feedback is included on ordinary infinite-like Z^2.

constexpr int SIDE = 257;
constexpr int CENTER = SIDE / 2;
constexpr int PACKET = 925;

using Coord = std::pair<int, int>;

static int site(Coord coordinate) {
  return (CENTER + coordinate.first) * SIDE +
         CENTER + coordinate.second;
}

static Coord add(Coord left, Coord right) {
  return {left.first + right.first, left.second + right.second};
}

static Coord negate(Coord value) {
  return {-value.first, -value.second};
}

static constexpr std::array<Coord, 4> DIRECTIONS = {{
    {-1, 0}, {1, 0}, {0, -1}, {0, 1},
}};

struct Variant {
  std::map<Coord, int> cells;
  Coord input;
  Coord output;
};

class Pile {
 public:
  Pile()
      : state_(SIDE * SIDE), odometer_(SIDE * SIDE),
        touched_(SIDE * SIDE), queued_(SIDE * SIDE) {
    touched_sites_.reserve(8192);
    queue_.reserve(8192);
  }

  void reset(const std::map<Coord, int>& background) {
    for (const int x : touched_sites_) {
      state_[x] = 0;
      odometer_[x] = 0;
      touched_[x] = 0;
      queued_[x] = 0;
    }
    touched_sites_.clear();
    for (const auto& [coordinate, height] : background) {
      const int x = site(coordinate);
      touch(x);
      state_[x] = height;
    }
  }

  void add_grains(int x, int amount) {
    touch(x);
    state_[x] += amount;
    if (state_[x] >= 4 && !queued_[x]) {
      queued_[x] = 1;
      queue_.push_back(x);
    }
  }

  void stabilize() {
    std::size_t head = 0;
    while (head < queue_.size()) {
      const int x = queue_[head++];
      queued_[x] = 0;
      const int amount = state_[x] / 4;
      if (!amount) continue;
      state_[x] -= 4 * amount;
      odometer_[x] += amount;
      for (const int neighbor :
           {x - SIDE, x + SIDE, x - 1, x + 1}) {
        touch(neighbor);
        state_[neighbor] += amount;
        if (state_[neighbor] >= 4 && !queued_[neighbor]) {
          queued_[neighbor] = 1;
          queue_.push_back(neighbor);
        }
      }
    }
    queue_.clear();
  }

  int odometer(Coord coordinate) const {
    return odometer_[site(coordinate)];
  }

 private:
  void touch(int x) {
    if (touched_[x]) return;
    touched_[x] = 1;
    touched_sites_.push_back(x);
  }

  std::vector<int> state_;
  std::vector<int> odometer_;
  std::vector<std::uint8_t> touched_;
  std::vector<std::uint8_t> queued_;
  std::vector<int> touched_sites_;
  std::vector<int> queue_;
};

static std::vector<Variant> variants_for(
    Coord gate_tap, const std::set<Coord>& gate_cells) {
  std::vector<Variant> result;
  for (const Coord toward_input : DIRECTIONS) {
    const Coord input = add(gate_tap, toward_input);
    if (gate_cells.count(input)) continue;
    for (const Coord first_axis : DIRECTIONS) {
      for (const Coord second_axis : DIRECTIONS) {
        if (first_axis.first * second_axis.first +
                first_axis.second * second_axis.second !=
            0) {
          continue;
        }
        // Background [[1,0],[1,1]] in the ordered (first,second)
        // coordinate frame.
        std::map<Coord, int> cells = {
            {input, 1},
            {add(input, first_axis), 1},
            {add(input, second_axis), 0},
            {add(add(input, first_axis), second_axis), 1},
        };
        bool overlaps_gate = false;
        for (const auto& [coordinate, _] : cells) {
          overlaps_gate |= gate_cells.count(coordinate);
        }
        if (overlaps_gate || cells.size() != 4) continue;

        const std::array<Coord, 3> relative_outputs = {
            add(negate(first_axis), negate(second_axis)),
            add(negate(first_axis), second_axis),
            add(first_axis, negate(second_axis)),
        };
        for (const Coord relative : relative_outputs) {
          const Coord output = add(input, relative);
          if (gate_cells.count(output) || cells.count(output)) continue;
          result.push_back({cells, input, output});
        }
      }
    }
  }
  return result;
}

int main() {
  const Coord A{0, 0};
  const Coord B{0, 1};
  const Coord D{1, 0};
  const Coord C{1, 1};
  const std::map<Coord, int> gate = {
      {A, 0}, {B, 0}, {D, 2}, {C, 2},
  };
  const std::set<Coord> gate_cells = {A, B, D, C};
  const auto a_variants = variants_for(C, gate_cells);
  const auto b_variants = variants_for(D, gate_cells);
  std::cout << "a_variants=" << a_variants.size()
            << " b_variants=" << b_variants.size() << "\n";

  Pile pile;
  int best_errors = 33;
  int checked = 0;
  for (const Variant& a_variant : a_variants) {
    for (const Variant& b_variant : b_variants) {
      std::set<Coord> a_cells;
      for (const auto& [coordinate, _] : a_variant.cells) {
        a_cells.insert(coordinate);
      }
      bool overlap = false;
      for (const auto& [coordinate, _] : b_variant.cells) {
        overlap |= a_cells.count(coordinate);
      }
      overlap |= a_cells.count(b_variant.output);
      overlap |= b_variant.cells.count(a_variant.output);
      overlap |= a_variant.output == b_variant.output;
      if (overlap) continue;

      std::map<Coord, int> background = gate;
      background.insert(
          a_variant.cells.begin(), a_variant.cells.end());
      background.insert(
          b_variant.cells.begin(), b_variant.cells.end());
      if (background.size() !=
          gate.size() + a_variant.cells.size() +
              b_variant.cells.size()) {
        continue;
      }

      int errors = 0;
      std::array<std::array<std::array<int, 2>, 4>, 4> table{};
      for (int a = 0; a < 4; ++a) {
        for (int b = 0; b < 4; ++b) {
          pile.reset(background);
          pile.add_grains(site(A), a * PACKET);
          pile.add_grains(site(B), b * PACKET);
          pile.stabilize();
          const int a_output = pile.odometer(a_variant.output);
          const int b_output = pile.odometer(b_variant.output);
          table[a][b] = {a_output, b_output};
          errors += ((a_output & 1) != (a & 1));
          errors += ((b_output & 1) != (b & 1));
        }
      }
      ++checked;
      if (errors < best_errors) {
        best_errors = errors;
        std::cout << "best_errors=" << errors
                  << " a_input=(" << a_variant.input.first << ","
                  << a_variant.input.second << ")"
                  << " a_output=(" << a_variant.output.first << ","
                  << a_variant.output.second << ")"
                  << " b_input=(" << b_variant.input.first << ","
                  << b_variant.input.second << ")"
                  << " b_output=(" << b_variant.output.first << ","
                  << b_variant.output.second << ")\n";
        for (int a = 0; a < 4; ++a) {
          std::cout << "a=" << a << ":";
          for (int b = 0; b < 4; ++b) {
            std::cout << " (" << table[a][b][0] << ","
                      << table[a][b][1] << ")";
          }
          std::cout << "\n";
        }
      }
      if (!errors) {
        std::cout << "DIRECT TWO-STAGE COMPOSITION HIT\n";
        return 0;
      }
    }
  }
  std::cout << "DONE checked=" << checked
            << " best_errors=" << best_errors << "\n";
}
