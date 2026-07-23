// Exact exhaustive certificate for a full-alphabet AND observable and an
// eight-cell write/read-clock memory effect in the ordinary Abelian sandpile.
//
// Model:
//   * infinite square lattice Z^2;
//   * threshold four;
//   * a toppling sends one grain to each von Neumann neighbor;
//   * zero background outside a stable 2x2 core.
//
// Exhaustive search:
//   * all 4^4 = 256 stable 2x2 cores;
//   * equal packet sizes 1 <= p <= 71;
//   * inputs a,b in {0,1,2,3} at the two top core cells;
//   * every reached site outside the core as an odometer-parity tap;
//   * target parity (a mod 2) AND (b mod 2).
//
// The search uses dense incremental stabilization.  The named witness and
// memory protocol are independently replayed from scratch by a sparse
// map-based stabilizer, with exact Laplacian, stability, and mass checks.
//
// Build and run:
//   g++ -O3 -std=c++20 -Wall -Wextra -pedantic
//       sandpile_packet71_and_latch_audit.cpp
//       -o sandpile_packet71_and_latch_audit
//   ./sandpile_packet71_and_latch_audit
//       packet71_and_latch_cpp_audit.json

#include <algorithm>
#include <array>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace {

struct Coord {
  int row;
  int column;

  auto operator<=>(const Coord&) const = default;
};

constexpr std::array<Coord, 4> kDirections = {{
    {-1, 0},
    {1, 0},
    {0, -1},
    {0, 1},
}};

constexpr Coord kA{0, 0};
constexpr Coord kB{0, 1};
constexpr Coord kD{1, 0};
constexpr Coord kC{1, 1};
constexpr std::array<Coord, 4> kCoreSites = {kA, kB, kD, kC};
constexpr std::array<int, 4> kWitnessCore = {1, 1, 2, 2};
constexpr int kWitnessPacket = 71;
constexpr Coord kLeftTap{3, -1};
constexpr Coord kRightTap{3, 2};
constexpr std::array<Coord, 8> kMemorySites = {{
    {-4, -1},
    {-4, 2},
    {-1, -4},
    {-1, 5},
    {1, -4},
    {1, 5},
    {4, -1},
    {4, 2},
}};

using Core = std::array<int, 4>;
using CountTable = std::array<std::array<std::int64_t, 4>, 4>;

constexpr std::array<std::array<std::int64_t, 4>, 4>
    kExpectedLeftTable = {{
        {{0, 0, 2, 6}},
        {{0, 1, 6, 13}},
        {{4, 8, 14, 22}},
        {{10, 15, 24, 31}},
    }};

constexpr std::array<std::array<std::int64_t, 4>, 4>
    kExpectedRightTable = {{
        {{0, 0, 4, 10}},
        {{0, 1, 8, 15}},
        {{2, 6, 14, 24}},
        {{6, 13, 22, 31}},
    }};

Coord add(Coord left, Coord right) {
  return {left.row + right.row, left.column + right.column};
}

bool is_core_site(Coord coordinate) {
  return std::find(
             kCoreSites.begin(), kCoreSites.end(), coordinate
         ) != kCoreSites.end();
}

std::uint16_t and_signature() {
  std::uint16_t result = 0;
  for (int a = 0; a < 4; ++a) {
    for (int b = 0; b < 4; ++b) {
      const int bit = 4 * a + b;
      if ((a & 1) && (b & 1)) {
        result |= static_cast<std::uint16_t>(1U << bit);
      }
    }
  }
  return result;
}

Core decode_core(int code) {
  Core result{};
  for (int index = 3; index >= 0; --index) {
    result[index] = code % 4;
    code /= 4;
  }
  return result;
}

int encode_core(const Core& core) {
  int result = 0;
  for (const int height : core) {
    result = 4 * result + height;
  }
  return result;
}

std::string coord_text(Coord coordinate) {
  std::ostringstream stream;
  stream << "(" << coordinate.row << "," << coordinate.column << ")";
  return stream.str();
}

// A deliberately generous dense window.  The separately computed
// pointwise-dominating run has toppling bounds
// rows [-7,7], columns [-6,7], so radius 32 leaves a wide exact margin.
constexpr int kSide = 65;
constexpr int kCenter = kSide / 2;
constexpr int kSiteCount = kSide * kSide;

int dense_site(Coord coordinate) {
  const int row = kCenter + coordinate.row;
  const int column = kCenter + coordinate.column;
  if (row < 0 || row >= kSide || column < 0 || column >= kSide) {
    throw std::runtime_error(
        "coordinate escaped dense audit window: " + coord_text(coordinate)
    );
  }
  return row * kSide + column;
}

Coord dense_coord(int site) {
  return {
      site / kSide - kCenter,
      site % kSide - kCenter,
  };
}

class DensePile {
 public:
  DensePile()
      : state_(kSiteCount),
        odometer_(kSiteCount),
        stamp_(kSiteCount),
        queued_(kSiteCount) {
    touched_.reserve(1024);
    queue_.reserve(1024);
  }

  void reset(const Core& core) {
    ++generation_;
    if (generation_ == 0) {
      std::fill(stamp_.begin(), stamp_.end(), 0);
      generation_ = 1;
    }
    touched_.clear();
    queue_.clear();
    for (int index = 0; index < 4; ++index) {
      const int site = dense_site(kCoreSites[index]);
      touch(site);
      state_[site] = core[index];
    }
  }

  // Move from common packet p-1 to p for one fixed amplitude pair (a,b).
  // Abelian associativity makes the resulting cumulative odometer identical
  // to a direct stabilization after adding p*a and p*b grains.
  void increment_packet(int a, int b) {
    if (a) {
      seed(dense_site(kA), a);
    }
    if (b) {
      seed(dense_site(kB), b);
    }
    stabilize_queue();
  }

  const std::vector<int>& touched() const {
    return touched_;
  }

  std::int64_t odometer(int site) const {
    return odometer_[site];
  }

 private:
  void touch(int site) {
    if (stamp_[site] == generation_) {
      return;
    }
    stamp_[site] = generation_;
    state_[site] = 0;
    odometer_[site] = 0;
    queued_[site] = 0;
    touched_.push_back(site);
  }

  void seed(int site, int amount) {
    touch(site);
    state_[site] += amount;
    if (state_[site] >= 4 && !queued_[site]) {
      queued_[site] = 1;
      queue_.push_back(site);
    }
  }

  void stabilize_queue() {
    std::size_t head = 0;
    while (head < queue_.size()) {
      const int site = queue_[head++];
      queued_[site] = 0;
      const std::int64_t amount = state_[site] / 4;
      if (!amount) {
        continue;
      }
      state_[site] -= 4 * amount;
      odometer_[site] += amount;

      const int row = site / kSide;
      const int column = site % kSide;
      if (row == 0 || row + 1 == kSide ||
          column == 0 || column + 1 == kSide) {
        throw std::runtime_error(
            "a boundary site toppled in the dense audit window"
        );
      }
      for (const int neighbor : {
               site - kSide,
               site + kSide,
               site - 1,
               site + 1,
           }) {
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

  std::vector<std::int64_t> state_;
  std::vector<std::int64_t> odometer_;
  std::vector<std::uint32_t> stamp_;
  std::vector<std::uint8_t> queued_;
  std::vector<int> touched_;
  std::vector<int> queue_;
  std::uint32_t generation_ = 0;
};

struct Hit {
  int packet;
  int core_code;
  Core core;
  Coord tap;
  CountTable table;
};

struct SearchResult {
  std::int64_t logical_configurations_checked = 0;
  std::int64_t hits_before_71 = 0;
  std::vector<Hit> hits_at_71;
};

SearchResult exhaustive_search() {
  constexpr int kRuns = 16;
  const std::uint16_t target = and_signature();
  std::array<DensePile, kRuns> runs;
  std::vector<std::uint16_t> signatures(kSiteCount);
  std::vector<std::uint32_t> signature_stamp(kSiteCount);
  std::vector<int> candidates;
  candidates.reserve(1024);
  std::uint32_t signature_generation = 0;
  SearchResult result;

  for (int core_code = 0; core_code < 256; ++core_code) {
    const Core core = decode_core(core_code);
    for (DensePile& run : runs) {
      run.reset(core);
    }

    for (int packet = 1; packet <= kWitnessPacket; ++packet) {
      for (int a = 0; a < 4; ++a) {
        for (int b = 0; b < 4; ++b) {
          runs[4 * a + b].increment_packet(a, b);
        }
      }
      result.logical_configurations_checked += 16;

      ++signature_generation;
      candidates.clear();
      for (int run_index = 0; run_index < kRuns; ++run_index) {
        for (const int site : runs[run_index].touched()) {
          if (!(runs[run_index].odometer(site) & 1)) {
            continue;
          }
          if (signature_stamp[site] != signature_generation) {
            signature_stamp[site] = signature_generation;
            signatures[site] = 0;
            candidates.push_back(site);
          }
          signatures[site] |= static_cast<std::uint16_t>(
              1U << run_index
          );
        }
      }

      std::sort(candidates.begin(), candidates.end());
      for (const int site : candidates) {
        const Coord tap = dense_coord(site);
        if (is_core_site(tap) || signatures[site] != target) {
          continue;
        }
        if (packet < kWitnessPacket) {
          ++result.hits_before_71;
          continue;
        }
        CountTable table{};
        for (int a = 0; a < 4; ++a) {
          for (int b = 0; b < 4; ++b) {
            table[a][b] = runs[4 * a + b].odometer(site);
          }
        }
        result.hits_at_71.push_back({
            packet,
            core_code,
            core,
            tap,
            table,
        });
      }
    }
  }

  if (result.logical_configurations_checked !=
      static_cast<std::int64_t>(256) * 71 * 16) {
    throw std::runtime_error("exhaustive-search accounting failed");
  }
  if (result.hits_before_71 != 0) {
    throw std::runtime_error(
        "unexpected exterior full-alphabet AND tap below packet 71"
    );
  }
  if (result.hits_at_71.empty()) {
    throw std::runtime_error("no packet-71 hit was found");
  }
  return result;
}

using SparseState = std::map<Coord, std::int64_t>;

void erase_zeroes(SparseState& values) {
  for (auto iterator = values.begin(); iterator != values.end();) {
    if (iterator->second == 0) {
      iterator = values.erase(iterator);
    } else {
      ++iterator;
    }
  }
}

std::int64_t value_at(const SparseState& values, Coord coordinate) {
  const auto iterator = values.find(coordinate);
  return iterator == values.end() ? 0 : iterator->second;
}

std::int64_t mass(const SparseState& state) {
  std::int64_t result = 0;
  for (const auto& [coordinate, height] : state) {
    (void)coordinate;
    result += height;
  }
  return result;
}

struct SparseRun {
  SparseState final;
  SparseState odometer;
  std::int64_t legal_batches = 0;
  std::int64_t total_unit_topplings = 0;
};

SparseRun stabilize_sparse(SparseState initial) {
  SparseState state = initial;
  SparseState odometer;
  std::deque<Coord> pending;
  std::set<Coord> queued;
  for (const auto& [coordinate, height] : state) {
    if (height >= 4) {
      pending.push_back(coordinate);
      queued.insert(coordinate);
    }
  }

  std::int64_t legal_batches = 0;
  while (!pending.empty()) {
    const Coord coordinate = pending.front();
    pending.pop_front();
    queued.erase(coordinate);
    const std::int64_t height = value_at(state, coordinate);
    const std::int64_t amount = height / 4;
    if (!amount) {
      continue;
    }
    if (height - 4 * (amount - 1) < 4) {
      throw std::runtime_error("a sparse batch was not unitwise legal");
    }
    state[coordinate] -= 4 * amount;
    odometer[coordinate] += amount;
    ++legal_batches;
    for (const Coord direction : kDirections) {
      const Coord neighbor = add(coordinate, direction);
      state[neighbor] += amount;
      if (state[neighbor] >= 4 && !queued.contains(neighbor)) {
        queued.insert(neighbor);
        pending.push_back(neighbor);
      }
    }
  }
  erase_zeroes(state);
  erase_zeroes(odometer);

  SparseState reconstructed = initial;
  for (const auto& [coordinate, amount] : odometer) {
    reconstructed[coordinate] -= 4 * amount;
    for (const Coord direction : kDirections) {
      reconstructed[add(coordinate, direction)] += amount;
    }
  }
  erase_zeroes(reconstructed);
  if (reconstructed != state) {
    throw std::runtime_error("sparse Laplacian reconstruction failed");
  }
  for (const auto& [coordinate, height] : state) {
    (void)coordinate;
    if (height < 0 || height >= 4) {
      throw std::runtime_error("sparse final configuration is not stable");
    }
  }
  if (mass(initial) != mass(state)) {
    throw std::runtime_error("mass was not conserved on Z^2");
  }

  std::int64_t total = 0;
  for (const auto& [coordinate, amount] : odometer) {
    (void)coordinate;
    total += amount;
  }
  return {state, odometer, legal_batches, total};
}

SparseState initial_core(const Core& core) {
  SparseState state;
  for (int index = 0; index < 4; ++index) {
    if (core[index]) {
      state[kCoreSites[index]] = core[index];
    }
  }
  return state;
}

SparseRun direct_run(const Core& core, int packet, int a, int b) {
  SparseState state = initial_core(core);
  state[kA] += static_cast<std::int64_t>(packet) * a;
  state[kB] += static_cast<std::int64_t>(packet) * b;
  return stabilize_sparse(std::move(state));
}

CountTable direct_table(
    const Core& core,
    int packet,
    Coord tap
) {
  CountTable table{};
  for (int a = 0; a < 4; ++a) {
    for (int b = 0; b < 4; ++b) {
      const SparseRun run = direct_run(core, packet, a, b);
      table[a][b] = value_at(run.odometer, tap);
    }
  }
  return table;
}

struct Bounds {
  bool empty = true;
  int minimum_row = 0;
  int maximum_row = 0;
  int minimum_column = 0;
  int maximum_column = 0;
};

Bounds bounds_of(const SparseState& values) {
  Bounds bounds;
  for (const auto& [coordinate, value] : values) {
    if (!value) {
      continue;
    }
    if (bounds.empty) {
      bounds.empty = false;
      bounds.minimum_row = bounds.maximum_row = coordinate.row;
      bounds.minimum_column = bounds.maximum_column = coordinate.column;
    } else {
      bounds.minimum_row = std::min(bounds.minimum_row, coordinate.row);
      bounds.maximum_row = std::max(bounds.maximum_row, coordinate.row);
      bounds.minimum_column =
          std::min(bounds.minimum_column, coordinate.column);
      bounds.maximum_column =
          std::max(bounds.maximum_column, coordinate.column);
    }
  }
  return bounds;
}

std::int64_t maximum_value(const SparseState& values) {
  std::int64_t result = 0;
  for (const auto& [coordinate, value] : values) {
    (void)coordinate;
    result = std::max(result, value);
  }
  return result;
}

struct MemoryCase {
  int a;
  int b;
  SparseRun write;
  std::array<std::int64_t, 8> memory_write_odometers{};
  std::array<std::int64_t, 8> memory_after_write{};
  SparseRun read;
  std::array<std::int64_t, 8> memory_read_odometers{};
  std::array<std::int64_t, 8> memory_after_read{};
};

std::vector<MemoryCase> audit_memory_protocol() {
  std::vector<MemoryCase> result;
  for (int a = 0; a <= 1; ++a) {
    for (int b = 0; b <= 1; ++b) {
      SparseState write_initial = initial_core(kWitnessCore);
      write_initial[kA] += kWitnessPacket * a;
      write_initial[kB] += kWitnessPacket * b;
      SparseRun write = stabilize_sparse(std::move(write_initial));

      MemoryCase record;
      record.a = a;
      record.b = b;
      record.write = write;
      for (int index = 0; index < 8; ++index) {
        const Coord memory = kMemorySites[index];
        record.memory_write_odometers[index] =
            value_at(write.odometer, memory);
        record.memory_after_write[index] =
            value_at(write.final, memory);
        if (record.memory_write_odometers[index] != 0) {
          throw std::runtime_error(
              "a memory cell toppled during the write phase"
          );
        }
        if (record.memory_after_write[index] != a * b) {
          throw std::runtime_error(
              "a memory cell did not store the Boolean AND"
          );
        }
      }

      SparseState read_initial = write.final;
      for (const Coord memory : kMemorySites) {
        read_initial[memory] += 3;
      }
      SparseRun read = stabilize_sparse(std::move(read_initial));
      record.read = read;
      for (int index = 0; index < 8; ++index) {
        const Coord memory = kMemorySites[index];
        record.memory_read_odometers[index] =
            value_at(read.odometer, memory);
        record.memory_after_read[index] =
            value_at(read.final, memory);
      }

      if (a * b == 0) {
        if (!read.odometer.empty() || read.total_unit_topplings != 0) {
          throw std::runtime_error(
              "a false memory value caused read-clock topplings"
          );
        }
      } else {
        if (read.total_unit_topplings != 66) {
          throw std::runtime_error(
              "the true read-clock case did not make 66 topplings"
          );
        }
        for (const std::int64_t count : record.memory_read_odometers) {
          if (count != 1) {
            throw std::runtime_error(
                "a true memory cell did not topple exactly once on read"
            );
          }
        }
      }
      result.push_back(std::move(record));
    }
  }
  return result;
}

Coord outward_direction(Coord memory) {
  if (memory.row == -4) {
    return {-1, 0};
  }
  if (memory.row == 4) {
    return {1, 0};
  }
  if (memory.column == -4) {
    return {0, -1};
  }
  if (memory.column == 5) {
    return {0, 1};
  }
  throw std::runtime_error(
      "memory site has no defined outward fuse direction"
  );
}

std::vector<Coord> fuse_cells(int length) {
  if (length < 0) {
    throw std::runtime_error("fuse length must be nonnegative");
  }
  std::vector<Coord> result;
  result.reserve(8 * length);
  std::set<Coord> unique;
  for (const Coord memory : kMemorySites) {
    const Coord direction = outward_direction(memory);
    Coord current = memory;
    for (int step = 0; step < length; ++step) {
      current = add(current, direction);
      if (!unique.insert(current).second) {
        throw std::runtime_error("two fuse rays intersected");
      }
      result.push_back(current);
    }
  }
  return result;
}

struct FuseCase {
  int a;
  int b;
  std::int64_t write_total_unit_topplings;
  std::int64_t read_total_unit_topplings;
  std::int64_t read_support_sites;
  bool ports_and_fuses_topple_once;
};

struct FuseRegression {
  int length;
  int fuse_cell_count;
  std::vector<FuseCase> cases;
};

std::vector<FuseRegression> audit_fuse_rays() {
  constexpr std::array<int, 5> kLengths = {1, 2, 8, 32, 100};
  std::vector<FuseRegression> result;
  for (const int length : kLengths) {
    const std::vector<Coord> fuses = fuse_cells(length);
    FuseRegression regression;
    regression.length = length;
    regression.fuse_cell_count = static_cast<int>(fuses.size());

    for (int a = 0; a <= 1; ++a) {
      for (int b = 0; b <= 1; ++b) {
        SparseState write_initial = initial_core(kWitnessCore);
        for (const Coord fuse : fuses) {
          write_initial[fuse] = 3;
        }
        write_initial[kA] += kWitnessPacket * a;
        write_initial[kB] += kWitnessPacket * b;
        const SparseRun write =
            stabilize_sparse(std::move(write_initial));

        for (const Coord memory : kMemorySites) {
          if (value_at(write.odometer, memory) != 0 ||
              value_at(write.final, memory) != a * b) {
            throw std::runtime_error(
                "fuse attachment changed a memory write"
            );
          }
        }
        for (const Coord fuse : fuses) {
          if (value_at(write.odometer, fuse) != 0 ||
              value_at(write.final, fuse) != 3) {
            throw std::runtime_error(
                "a fuse ray was touched during Boolean write"
            );
          }
        }

        SparseState read_initial = write.final;
        for (const Coord memory : kMemorySites) {
          read_initial[memory] += 3;
        }
        const SparseRun read =
            stabilize_sparse(std::move(read_initial));
        bool once = true;
        for (const Coord memory : kMemorySites) {
          once &= value_at(read.odometer, memory) == a * b;
        }
        for (const Coord fuse : fuses) {
          once &= value_at(read.odometer, fuse) == a * b;
        }
        if (!once) {
          throw std::runtime_error(
              "a port or fuse cell had the wrong read odometer"
          );
        }
        if (a * b == 0 && !read.odometer.empty()) {
          throw std::runtime_error(
              "a false fuse-ray read was not completely quiescent"
          );
        }
        // Relative to the unattached true read, every added height-three
        // fuse cell topples once and no other odometer count changes.
        const std::int64_t expected_true_total = 66 + 8 * length;
        if (a * b == 1 &&
            read.total_unit_topplings != expected_true_total) {
          throw std::runtime_error(
              "true fuse-ray read total is not 66 + 8*length"
          );
        }
        regression.cases.push_back({
            a,
            b,
            write.total_unit_topplings,
            read.total_unit_topplings,
            static_cast<std::int64_t>(read.odometer.size()),
            once,
        });
      }
    }
    result.push_back(std::move(regression));
  }
  return result;
}

struct IntegratedGateCase {
  int a;
  int b;
  std::int64_t total_unit_topplings;
  std::int64_t odometer_support_sites;
  bool all_ports_and_fuses_topple_exactly_ab_times;
  bool if_false_all_ports_and_fuses_remain_at_height_three;
};

struct IntegratedGateRegression {
  int length;
  int precharged_output_cell_count;
  std::vector<IntegratedGateCase> cases;
};

std::vector<IntegratedGateRegression> audit_integrated_gate() {
  constexpr std::array<int, 7> kLengths = {
      0, 1, 2, 8, 32, 100, 500,
  };
  std::vector<IntegratedGateRegression> result;
  for (const int length : kLengths) {
    const std::vector<Coord> fuses = fuse_cells(length);
    IntegratedGateRegression regression;
    regression.length = length;
    regression.precharged_output_cell_count =
        static_cast<int>(kMemorySites.size() + fuses.size());

    for (int a = 0; a <= 1; ++a) {
      for (int b = 0; b <= 1; ++b) {
        SparseState initial = initial_core(kWitnessCore);
        for (const Coord memory : kMemorySites) {
          initial[memory] = 3;
        }
        for (const Coord fuse : fuses) {
          initial[fuse] = 3;
        }
        initial[kA] += kWitnessPacket * a;
        initial[kB] += kWitnessPacket * b;
        const SparseRun run = stabilize_sparse(std::move(initial));

        bool exact_output_odometers = true;
        bool false_output_heights = true;
        for (const Coord memory : kMemorySites) {
          exact_output_odometers &=
              value_at(run.odometer, memory) == a * b;
          if (a * b == 0) {
            false_output_heights &=
                value_at(run.final, memory) == 3;
          }
        }
        for (const Coord fuse : fuses) {
          exact_output_odometers &=
              value_at(run.odometer, fuse) == a * b;
          if (a * b == 0) {
            false_output_heights &=
                value_at(run.final, fuse) == 3;
          }
        }
        if (!exact_output_odometers || !false_output_heights) {
          throw std::runtime_error(
              "integrated precharged gate output behavior failed"
          );
        }

        const std::int64_t expected_total =
            a == 0 && b == 0
                ? 0
                : a * b == 0
                    ? 109
                    : 422 + 8 * length;
        if (run.total_unit_topplings != expected_total) {
          throw std::runtime_error(
              "integrated precharged gate total changed"
          );
        }
        regression.cases.push_back({
            a,
            b,
            run.total_unit_topplings,
            static_cast<std::int64_t>(run.odometer.size()),
            exact_output_odometers,
            false_output_heights,
        });
      }
    }
    result.push_back(std::move(regression));
  }
  return result;
}

void write_coord(std::ostream& output, Coord coordinate) {
  output << "[" << coordinate.row << "," << coordinate.column << "]";
}

void write_core(std::ostream& output, const Core& core) {
  output << "[[" << core[0] << "," << core[1] << "],["
         << core[2] << "," << core[3] << "]]";
}

void write_table(std::ostream& output, const CountTable& table) {
  output << "[";
  for (int a = 0; a < 4; ++a) {
    if (a) {
      output << ",";
    }
    output << "[";
    for (int b = 0; b < 4; ++b) {
      if (b) {
        output << ",";
      }
      output << table[a][b];
    }
    output << "]";
  }
  output << "]";
}

template <std::size_t Size>
void write_integer_array(
    std::ostream& output,
    const std::array<std::int64_t, Size>& values
) {
  output << "[";
  for (std::size_t index = 0; index < Size; ++index) {
    if (index) {
      output << ",";
    }
    output << values[index];
  }
  output << "]";
}

void write_sparse(std::ostream& output, const SparseState& values) {
  output << "[";
  bool first = true;
  for (const auto& [coordinate, value] : values) {
    if (!first) {
      output << ",";
    }
    first = false;
    output << "[" << coordinate.row << "," << coordinate.column
           << "," << value << "]";
  }
  output << "]";
}

void write_bounds(std::ostream& output, const Bounds& bounds) {
  if (bounds.empty) {
    output << "null";
    return;
  }
  output << "["
         << bounds.minimum_row << ","
         << bounds.maximum_row << ","
         << bounds.minimum_column << ","
         << bounds.maximum_column << "]";
}

void write_json(
    const std::string& output_path,
    const SearchResult& search,
    const SparseRun& dominating,
    const std::vector<MemoryCase>& memory_cases,
    const std::vector<FuseRegression>& fuse_regressions,
    const std::vector<IntegratedGateRegression>& integrated_regressions
) {
  std::ofstream output(output_path);
  if (!output) {
    throw std::runtime_error("could not open JSON output path");
  }

  output << "{\n";
  output << "  \"title\":\"Packet-71 full-alphabet AND and "
            "eight-cell read-clock certificate\",\n";
  output << "  \"model\":{"
            "\"lattice\":\"infinite Z^2\","
            "\"threshold\":4,"
            "\"neighborhood\":\"von Neumann\","
            "\"background_outside_core\":0},\n";
  output << "  \"exhaustive_search\":{\n";
  output << "    \"core_sites_A_B_D_C\":[[0,0],[0,1],[1,0],[1,1]],\n";
  output << "    \"input_sites_A_B\":[[0,0],[0,1]],\n";
  output << "    \"stable_cores_checked\":256,\n";
  output << "    \"equal_packet_range\":[1,71],\n";
  output << "    \"amplitude_alphabet\":[0,1,2,3],\n";
  output << "    \"logical_configurations_checked\":"
         << search.logical_configurations_checked << ",\n";
  output << "    \"tap_scope\":\"every reached site outside the four "
            "core sites\",\n";
  output << "    \"target\":\"odometer parity equals "
            "(a mod 2) AND (b mod 2)\",\n";
  output << "    \"target_signature_hex\":\"a0a0\",\n";
  output << "    \"hits_for_packets_1_through_70\":"
         << search.hits_before_71 << ",\n";
  output << "    \"packet_71_hit_count\":"
         << search.hits_at_71.size() << ",\n";
  output << "    \"packet_71_hits\":[\n";
  for (std::size_t index = 0; index < search.hits_at_71.size(); ++index) {
    const Hit& hit = search.hits_at_71[index];
    output << "      {\"core_code\":" << hit.core_code << ",\"core\":";
    write_core(output, hit.core);
    output << ",\"tap\":";
    write_coord(output, hit.tap);
    output << ",\"count_table_rows_a_columns_b\":";
    write_table(output, hit.table);
    output << "}";
    if (index + 1 != search.hits_at_71.size()) {
      output << ",";
    }
    output << "\n";
  }
  output << "    ],\n";
  output << "    \"dense_window_side\":65,\n";
  output << "    \"dominating_case\":{"
            "\"core\":[[3,3],[3,3]],"
            "\"packet\":71,"
            "\"amplitudes\":[3,3],"
            "\"odometer_support_sites\":"
         << dominating.odometer.size()
         << ",\"odometer_bounds_row_min_row_max_col_min_col_max\":";
  write_bounds(output, bounds_of(dominating.odometer));
  output << ",\"total_unit_topplings\":"
         << dominating.total_unit_topplings
         << ",\"maximum_site_topplings\":"
         << maximum_value(dominating.odometer)
         << "},\n";
  output << "    \"exact_window_argument\":\"The dominating initial "
            "configuration pointwise dominates every searched case. "
            "Odometer monotonicity confines all searched topplings to its "
            "reported support, strictly inside the 65x65 window.\"\n";
  output << "  },\n";

  output << "  \"specified_witness\":{\n";
  output << "    \"packet\":71,\n";
  output << "    \"core\":";
  write_core(output, kWitnessCore);
  output << ",\n";
  output << "    \"left_tap\":[3,-1],\n";
  output << "    \"right_tap\":[3,2],\n";
  output << "    \"left_count_table_rows_a_columns_b\":";
  write_table(output, kExpectedLeftTable);
  output << ",\n";
  output << "    \"right_count_table_rows_a_columns_b\":";
  write_table(output, kExpectedRightTable);
  output << ",\n";
  output << "    \"both_output_parity_tables\":["
            "[[0,0,0,0],[0,1,0,1],[0,0,0,0],[0,1,0,1]],"
            "[[0,0,0,0],[0,1,0,1],[0,0,0,0],[0,1,0,1]]],\n";
  output << "    \"independent_sparse_replay\":true\n";
  output << "  },\n";

  output << "  \"boolean_write_read_clock\":{\n";
  output << "    \"boolean_inputs\":[[0,0],[0,1],[1,0],[1,1]],\n";
  output << "    \"memory_sites\":[";
  for (std::size_t index = 0; index < kMemorySites.size(); ++index) {
    if (index) {
      output << ",";
    }
    write_coord(output, kMemorySites[index]);
  }
  output << "],\n";
  output << "    \"write_rule\":\"stabilize after adding 71a at A and "
            "71b at B\",\n";
  output << "    \"read_clock_rule\":\"after write stabilization, add "
            "three grains simultaneously to every memory site and "
            "stabilize again\",\n";
  output << "    \"cases\":[\n";
  for (std::size_t index = 0; index < memory_cases.size(); ++index) {
    const MemoryCase& record = memory_cases[index];
    output << "      {\"input\":[" << record.a << "," << record.b << "],";
    output << "\"write_total_unit_topplings\":"
           << record.write.total_unit_topplings << ",";
    output << "\"write_odometer_support_sites\":"
           << record.write.odometer.size() << ",";
    output << "\"memory_write_odometers\":";
    write_integer_array(output, record.memory_write_odometers);
    output << ",\"memory_heights_after_write\":";
    write_integer_array(output, record.memory_after_write);
    output << ",\"read_incremental_total_unit_topplings\":"
           << record.read.total_unit_topplings << ",";
    output << "\"read_incremental_odometer_support_sites\":"
           << record.read.odometer.size() << ",";
    output << "\"memory_read_incremental_odometers\":";
    write_integer_array(output, record.memory_read_odometers);
    output << ",\"memory_heights_after_read\":";
    write_integer_array(output, record.memory_after_read);
    output << ",\"read_incremental_odometer\":";
    write_sparse(output, record.read.odometer);
    output << "}";
    if (index + 1 != memory_cases.size()) {
      output << ",";
    }
    output << "\n";
  }
  output << "    ],\n";
  output << "    \"verified_statement\":\"During write, all eight memory "
            "cells have odometer zero and finish at height a*b. A false "
            "stored value makes the read clock completely quiescent. A "
            "true stored value makes every memory cell topple exactly once "
            "and causes 66 incremental unit topplings in total.\"\n";
  output << "  },\n";
  output << "  \"integrated_height_three_fuse_rays\":{\n";
  output << "    \"geometry\":\"From each memory port, attach a "
            "one-cell-wide outward ray whose cells all start at height "
            "three. Top ports point up, bottom ports down, left ports "
            "left, and right ports right.\",\n";
  output << "    \"tested_lengths\":[1,2,8,32,100],\n";
  output << "    \"regressions\":[\n";
  for (std::size_t index = 0; index < fuse_regressions.size(); ++index) {
    const FuseRegression& regression = fuse_regressions[index];
    output << "      {\"length\":" << regression.length
           << ",\"fuse_cell_count\":" << regression.fuse_cell_count
           << ",\"cases\":[";
    for (std::size_t case_index = 0;
         case_index < regression.cases.size();
         ++case_index) {
      const FuseCase& record = regression.cases[case_index];
      if (case_index) {
        output << ",";
      }
      output << "{\"input\":[" << record.a << "," << record.b << "],"
             << "\"write_total_unit_topplings\":"
             << record.write_total_unit_topplings << ","
             << "\"read_incremental_total_unit_topplings\":"
             << record.read_total_unit_topplings << ","
             << "\"read_incremental_odometer_support_sites\":"
             << record.read_support_sites << ","
             << "\"all_ports_and_fuse_cells_topple_exactly_ab_times\":"
             << (record.ports_and_fuses_topple_once ? "true" : "false")
             << "}";
    }
    output << "]}";
    if (index + 1 != fuse_regressions.size()) {
      output << ",";
    }
    output << "\n";
  }
  output << "    ],\n";
  output << "    \"verified_statement\":\"For every tested finite "
            "length, the rays remain at height three and never topple "
            "during Boolean write. A false read is silent. A true read "
            "makes every memory port and every fuse cell topple exactly "
            "once, with total incremental topplings 66 + 8L.\"\n";
  output << "  },\n";
  output << "  \"integrated_precharged_boolean_and_gate\":{\n";
  output << "    \"construction\":\"Precharge all eight output ports and "
            "every cell of each optional outward fuse ray to height three "
            "before applying the Boolean packet inputs. No separate clock "
            "addition is used.\",\n";
  output << "    \"signal\":\"A port or fuse cell topples during the "
            "input avalanche\",\n";
  output << "    \"tested_lengths\":[0,1,2,8,32,100,500],\n";
  output << "    \"regressions\":[\n";
  for (std::size_t index = 0;
       index < integrated_regressions.size();
       ++index) {
    const IntegratedGateRegression& regression =
        integrated_regressions[index];
    output << "      {\"length\":" << regression.length
           << ",\"precharged_output_cell_count\":"
           << regression.precharged_output_cell_count
           << ",\"cases\":[";
    for (std::size_t case_index = 0;
         case_index < regression.cases.size();
         ++case_index) {
      const IntegratedGateCase& record =
          regression.cases[case_index];
      if (case_index) {
        output << ",";
      }
      output << "{\"input\":[" << record.a << "," << record.b << "],"
             << "\"total_unit_topplings\":"
             << record.total_unit_topplings << ","
             << "\"odometer_support_sites\":"
             << record.odometer_support_sites << ","
             << "\"all_ports_and_fuses_topple_exactly_ab_times\":"
             << (
                    record.all_ports_and_fuses_topple_exactly_ab_times
                        ? "true"
                        : "false"
                )
             << ",\"if_false_all_ports_and_fuses_remain_at_height_three\":"
             << (
                    record
                        .if_false_all_ports_and_fuses_remain_at_height_three
                        ? "true"
                        : "false"
                )
             << "}";
    }
    output << "]}";
    if (index + 1 != integrated_regressions.size()) {
      output << ",";
    }
    output << "\n";
  }
  output << "    ],\n";
  output << "    \"verified_statement\":\"For every tested length, every "
            "precharged output port and fuse cell has odometer exactly "
            "a*b. Thus false Boolean inputs leave every output cell "
            "untoppled at height three, while input 11 makes every output "
            "cell topple exactly once. The true total is 422 + 8L.\"\n";
  output << "  },\n";
  output << "  \"checks\":{"
            "\"dense_search_exhaustive\":true,"
            "\"sparse_batches_unitwise_legal\":true,"
            "\"sparse_final_states_stable\":true,"
            "\"sparse_laplacian_reconstruction\":true,"
            "\"mass_conserved\":true}\n";
  output << "}\n";
}

void validate_hit_tables_sparse(SearchResult& search) {
  for (Hit& hit : search.hits_at_71) {
    const CountTable direct = direct_table(
        hit.core,
        hit.packet,
        hit.tap
    );
    if (direct != hit.table) {
      throw std::runtime_error(
          "dense and sparse hit tables disagree at core " +
          std::to_string(hit.core_code) + ", tap " +
          coord_text(hit.tap)
      );
    }
  }
}

void validate_named_witness(const SearchResult& search) {
  if (direct_table(
          kWitnessCore,
          kWitnessPacket,
          kLeftTap
      ) != kExpectedLeftTable) {
    throw std::runtime_error("left witness table is incorrect");
  }
  if (direct_table(
          kWitnessCore,
          kWitnessPacket,
          kRightTap
      ) != kExpectedRightTable) {
    throw std::runtime_error("right witness table is incorrect");
  }

  bool found_left = false;
  bool found_right = false;
  const int witness_code = encode_core(kWitnessCore);
  for (const Hit& hit : search.hits_at_71) {
    if (hit.core_code != witness_code) {
      continue;
    }
    found_left |= hit.tap == kLeftTap && hit.table == kExpectedLeftTable;
    found_right |= hit.tap == kRightTap && hit.table == kExpectedRightTable;
  }
  if (!found_left || !found_right) {
    throw std::runtime_error(
        "exhaustive search did not enumerate both named witness taps"
    );
  }
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc > 2) {
      std::cerr << "usage: " << argv[0]
                << " [certificate-output.json]\n";
      return 2;
    }
    const std::string output_path =
        argc == 2
            ? argv[1]
            : "packet71_and_latch_cpp_audit.json";

    SearchResult search = exhaustive_search();
    validate_hit_tables_sparse(search);
    validate_named_witness(search);

    const SparseRun dominating =
        direct_run(Core{3, 3, 3, 3}, 71, 3, 3);
    const Bounds dominating_bounds = bounds_of(dominating.odometer);
    if (dominating_bounds.empty ||
        dominating_bounds.minimum_row != -7 ||
        dominating_bounds.maximum_row != 7 ||
        dominating_bounds.minimum_column != -6 ||
        dominating_bounds.maximum_column != 7) {
      throw std::runtime_error("dominating support bounds changed");
    }

    const std::vector<MemoryCase> memory_cases =
        audit_memory_protocol();
    const std::vector<FuseRegression> fuse_regressions =
        audit_fuse_rays();
    const std::vector<IntegratedGateRegression>
        integrated_regressions = audit_integrated_gate();
    write_json(
        output_path,
        search,
        dominating,
        memory_cases,
        fuse_regressions,
        integrated_regressions
    );

    std::cout << "PASS exhaustive cores=256 packets=1..71 "
              << "amplitudes=4x4 configurations="
              << search.logical_configurations_checked << "\n";
    std::cout << "PASS exterior AND hits packets=1..70: 0\n";
    std::cout << "PASS packet=71 hits="
              << search.hits_at_71.size() << "\n";
    for (const Hit& hit : search.hits_at_71) {
      std::cout << "HIT core_code=" << hit.core_code
                << " core=(" << hit.core[0] << "," << hit.core[1]
                << "," << hit.core[2] << "," << hit.core[3]
                << ") tap=" << coord_text(hit.tap) << "\n";
    }
    std::cout << "PASS named core=((1,1),(2,2)) taps=(3,-1),(3,2)"
              << " exact tables and full-alphabet AND parity\n";
    std::cout << "PASS dominating bounds=(-7,7,-6,7) support="
              << dominating.odometer.size()
              << " topplings=" << dominating.total_unit_topplings
              << "\n";
    std::cout << "PASS memory write/read-clock cases=4; "
              << "false reads quiescent; true read topplings=66\n";
    std::cout << "PASS integrated height-three fuse rays "
              << "lengths=1,2,8,32,100; true totals=66+8L\n";
    std::cout << "PASS integrated precharged Boolean AND gate "
              << "lengths=0,1,2,8,32,100,500; true totals=422+8L\n";
    std::cout << "WROTE " << output_path << "\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "FAIL " << error.what() << "\n";
    return 1;
  }
}
