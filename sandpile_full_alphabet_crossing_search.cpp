#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

struct Options {
  int n = 9;
  int padding = 4;
  int input_inset = 0;
  int output_tail = 2;
  int arm_half_width = 2;
  int patch_size = 7;
  int gate_size = 6;
  int pulse_scale = 1;
  int population = 3000;
  int generations = 2000;
  std::uint64_t seed = 1;
  bool symmetric = true;
  bool plus_arms = false;
  bool integrated_geometry = false;
  bool exhaustive = false;
  bool compact = false;
  std::string fitness_mode = "parity";
  int defect_depth = -1;
  bool defects_from_integrated = false;
  bool defects_from_six = false;
  bool map_elites = false;
  std::uint64_t evaluations = 20000000;
};

struct Evaluation {
  int mismatches = 0;
  int boolean_mismatches = 0;
  int axis_mismatches = 0;
  long long boolean_count_error = 0;
  long long axis_count_error = 0;
  long long boundary_activity = 0;
  long long linear_error = 0;
  long long activity = 0;
  long long selection_score = 0;
  std::uint32_t signature = 0;
  int best_diagonal = 0;
  int best_crosstalk = 0;
  std::array<std::array<std::array<int, 2>, 4>, 4> counts{};
  std::array<std::array<std::array<int, 2>, 4>, 4> parities{};

  auto rank() const {
    // Artificial-boundary activity invalidates the finite-plane certificate.
    return std::tuple(boundary_activity != 0, selection_score, mismatches,
                      boundary_activity, linear_error, activity);
  }
};

struct Candidate {
  std::vector<std::uint8_t> core;
  Evaluation evaluation;
};

static Options parse_options(int argc, char** argv) {
  Options options;
  for (int i = 1; i < argc; ++i) {
    const std::string argument = argv[i];
    auto value = [&](const std::string& flag) -> std::string {
      if (i + 1 >= argc) {
        std::cerr << "missing value after " << flag << "\n";
        std::exit(2);
      }
      return argv[++i];
    };
    if (argument == "--size") {
      options.n = std::stoi(value(argument));
    } else if (argument == "--padding") {
      options.padding = std::stoi(value(argument));
    } else if (argument == "--input-inset") {
      options.input_inset = std::stoi(value(argument));
    } else if (argument == "--output-tail") {
      options.output_tail = std::stoi(value(argument));
    } else if (argument == "--arm-half-width") {
      options.arm_half_width = std::stoi(value(argument));
    } else if (argument == "--patch-size") {
      options.patch_size = std::stoi(value(argument));
    } else if (argument == "--gate-size") {
      options.gate_size = std::stoi(value(argument));
    } else if (argument == "--pulse-scale") {
      options.pulse_scale = std::stoi(value(argument));
    } else if (argument == "--population") {
      options.population = std::stoi(value(argument));
    } else if (argument == "--generations") {
      options.generations = std::stoi(value(argument));
    } else if (argument == "--seed") {
      options.seed = std::stoull(value(argument));
    } else if (argument == "--nonsymmetric") {
      options.symmetric = false;
    } else if (argument == "--plus-arms") {
      options.plus_arms = true;
    } else if (argument == "--integrated-geometry") {
      options.integrated_geometry = true;
    } else if (argument == "--exhaustive") {
      options.exhaustive = true;
    } else if (argument == "--compact") {
      options.compact = true;
    } else if (argument == "--fitness-mode") {
      options.fitness_mode = value(argument);
    } else if (argument == "--defect-depth") {
      options.defect_depth = std::stoi(value(argument));
    } else if (argument == "--defects-from-integrated") {
      options.defects_from_integrated = true;
    } else if (argument == "--defects-from-six") {
      options.defects_from_six = true;
    } else if (argument == "--map-elites") {
      options.map_elites = true;
    } else if (argument == "--evaluations") {
      options.evaluations = std::stoull(value(argument));
    } else {
      std::cerr << "unknown argument: " << argument << "\n";
      std::exit(2);
    }
  }
  if (options.n < 5 || options.padding < 2 || options.input_inset < 0 ||
      options.output_tail < 0 || options.pulse_scale < 1 ||
      options.arm_half_width < 0 || options.patch_size < 1 ||
      options.gate_size < 6 ||
      options.defect_depth < -1 ||
      options.population < 20 || options.generations < 1) {
    std::cerr << "invalid options\n";
    std::exit(2);
  }
  if (options.input_inset >= options.n ||
      options.output_tail >= options.n ||
      options.patch_size > options.n) {
    std::cerr << "ports lie outside core\n";
    std::exit(2);
  }
  if (options.plus_arms && options.patch_size % 2 == 0) {
    std::cerr << "--patch-size must be odd in --plus-arms mode\n";
    std::exit(2);
  }
  if (options.plus_arms && options.integrated_geometry) {
    std::cerr << "--plus-arms and --integrated-geometry are exclusive\n";
    std::exit(2);
  }
  if (options.integrated_geometry &&
      options.n < options.gate_size + 5) {
    std::cerr << "--integrated-geometry requires "
                 "--size >= gate-size + 5\n";
    std::exit(2);
  }
  if (options.defects_from_integrated &&
      !options.integrated_geometry) {
    std::cerr << "--defects-from-integrated requires "
                 "--integrated-geometry\n";
    std::exit(2);
  }
  if (options.defects_from_six && !options.integrated_geometry) {
    std::cerr << "--defects-from-six requires "
                 "--integrated-geometry\n";
    std::exit(2);
  }
  if (options.defects_from_six &&
      options.defects_from_integrated) {
    std::cerr << "choose at most one defect-search baseline\n";
    std::exit(2);
  }
  if (options.fitness_mode != "parity" &&
      options.fitness_mode != "blended" &&
      options.fitness_mode != "boolean-first" &&
      options.fitness_mode != "axis-first") {
    std::cerr << "--fitness-mode must be parity, blended, "
                 "boolean-first, or axis-first\n";
    std::exit(2);
  }
  return options;
}

class Search {
 public:
  explicit Search(Options options)
      : options_(options),
        board_size_(options.n + 2 * options.padding),
        board_area_(board_size_ * board_size_),
        rng_(options.seed) {
    const int middle = options_.n / 2;
    if (options_.integrated_geometry) {
      north_ = position(2, 3);
      west_ = position(3, 2);
      south_ = position(options_.n - 3, 3);
      east_ = position(3, options_.n - 3);
    } else {
      north_ = position(options_.input_inset, middle);
      west_ = position(middle, options_.input_inset);
      south_ =
          position(options_.n - 1 - options_.output_tail, middle);
      east_ =
          position(middle, options_.n - 1 - options_.output_tail);
    }
    core_positions_.reserve(options_.n * options_.n);
    fixed_template_.assign(options_.n * options_.n, 0);
    mutable_mask_.assign(options_.n * options_.n, 1);
    const int patch_radius = options_.patch_size / 2;
    for (int row = 0; row < options_.n; ++row) {
      for (int column = 0; column < options_.n; ++column) {
        core_positions_.push_back(position(row, column));
        if (options_.integrated_geometry) {
          const bool in_gate =
              row < options_.gate_size &&
              column < options_.gate_size;
          const bool in_south_output =
              row >= options_.gate_size &&
              column >= 1 && column < 6;
          const bool in_east_output =
              column >= options_.gate_size &&
              row >= 1 && row < 6;
          const int index = row * options_.n + column;
          fixed_template_[index] =
              (in_south_output || in_east_output) ? 3 : 0;
          mutable_mask_[index] = in_gate ? 1 : 0;
          if (in_gate) mutable_positions_.push_back(index);
        } else if (options_.plus_arms) {
          const bool in_arm =
              std::abs(row - middle) <= options_.arm_half_width ||
              std::abs(column - middle) <= options_.arm_half_width;
          const bool in_patch =
              std::abs(row - middle) <= patch_radius &&
              std::abs(column - middle) <= patch_radius;
          const int index = row * options_.n + column;
          fixed_template_[index] = in_arm ? 3 : 0;
          mutable_mask_[index] = in_patch ? 1 : 0;
          if (in_patch) mutable_positions_.push_back(index);
        }
      }
    }
    if (!options_.plus_arms && !options_.integrated_geometry) {
      mutable_positions_.resize(options_.n * options_.n);
      std::iota(mutable_positions_.begin(), mutable_positions_.end(), 0);
    }
    for (int row = 0; row < board_size_; ++row) {
      for (int column = 0; column < board_size_; ++column) {
        if (row == 0 || column == 0 || row == board_size_ - 1 ||
            column == board_size_ - 1) {
          outer_boundary_.push_back(row * board_size_ + column);
        }
      }
    }
  }

  void run() {
    if (options_.map_elites) {
      run_map_elites();
      return;
    }
    if (options_.defect_depth >= 0) {
      run_defect_exhaustive();
      return;
    }
    if (options_.exhaustive) {
      run_exhaustive();
      return;
    }
    std::vector<Candidate> population;
    population.reserve(options_.population);
    population.push_back(make_all_three());
    population.push_back(make_cross());
    if ((options_.plus_arms && options_.patch_size >= 7) ||
        options_.integrated_geometry) {
      population.push_back(make_integrated_gate_seed());
    }
    if (options_.integrated_geometry) {
      population.push_back(make_amplitude_best_seed());
      population.push_back(make_amplitude_six_seed());
    }
    while (static_cast<int>(population.size()) < options_.population) {
      population.push_back(make_random());
    }

    Evaluation best_evaluation;
    best_evaluation.boundary_activity =
        std::numeric_limits<long long>::max();
    best_evaluation.mismatches = std::numeric_limits<int>::max();
    best_evaluation.selection_score =
        std::numeric_limits<long long>::max();
    std::vector<std::uint8_t> best_core;

    for (int generation = 0; generation < options_.generations;
         ++generation) {
      for (auto& candidate : population) {
        candidate.evaluation = evaluate(candidate.core);
      }
      std::sort(population.begin(), population.end(),
                [](const Candidate& left, const Candidate& right) {
                  return left.evaluation.rank() <
                         right.evaluation.rank();
                });

      if (population.front().evaluation.rank() < best_evaluation.rank()) {
        best_evaluation = population.front().evaluation;
        best_core = population.front().core;
        std::cout << "generation=" << generation
                  << " mismatches=" << best_evaluation.mismatches
                  << " boolean=" << best_evaluation.boolean_mismatches
                  << " axis=" << best_evaluation.axis_mismatches
                  << " bool_count="
                  << best_evaluation.boolean_count_error
                  << " axis_count=" << best_evaluation.axis_count_error
                  << " boundary=" << best_evaluation.boundary_activity
                  << " linear_error=" << best_evaluation.linear_error
                  << " matrix=(" << best_evaluation.best_diagonal << ","
                  << best_evaluation.best_crosstalk << ")"
                  << " activity=" << best_evaluation.activity << "\n";
        if (options_.compact) {
          print_compact_core(best_core);
        } else {
          print_core(best_core);
          print_table(best_evaluation);
        }
        std::cout.flush();
      }

      if (best_evaluation.mismatches == 0 &&
          best_evaluation.boundary_activity == 0) {
        std::cout << "FULL-ALPHABET PARITY CROSSING FOUND\n";
        print_core(best_core);
        print_table(best_evaluation);
        return;
      }

      const int elite_count = std::max(10, options_.population / 8);
      std::vector<Candidate> next;
      next.reserve(options_.population);
      for (int i = 0; i < elite_count; ++i) {
        next.push_back(population[i]);
      }
      const double progress =
          static_cast<double>(generation) / options_.generations;
      const double mutation_rate =
          std::max(1.0 / std::max<std::size_t>(
                                1, mutable_positions_.size()),
                   0.14 * (1.0 - progress));
      std::uniform_int_distribution<int> elite(0, elite_count - 1);
      const int immigrant_count = std::max(2, options_.population / 50);
      while (static_cast<int>(next.size()) <
             options_.population - immigrant_count) {
        Candidate child;
        child.core =
            crossover(population[elite(rng_)].core,
                      population[elite(rng_)].core);
        mutate(child.core, mutation_rate);
        next.push_back(std::move(child));
      }
      while (static_cast<int>(next.size()) < options_.population) {
        next.push_back(make_random());
      }
      population = std::move(next);
    }

    std::cout << "NO FULL-ALPHABET CROSSING FOUND\n";
    std::cout << "best mismatches=" << best_evaluation.mismatches
              << " boundary=" << best_evaluation.boundary_activity
              << " linear_error=" << best_evaluation.linear_error << "\n";
    print_core(best_core);
    print_table(best_evaluation);
  }

 private:
  void run_map_elites() {
    std::vector<Candidate> archive;
    std::unordered_map<std::uint32_t, std::size_t> by_signature;
    archive.reserve(100000);
    by_signature.reserve(100000);

    Evaluation best_evaluation;
    best_evaluation.boundary_activity =
        std::numeric_limits<long long>::max();
    best_evaluation.mismatches = std::numeric_limits<int>::max();
    best_evaluation.selection_score =
        std::numeric_limits<long long>::max();
    std::vector<std::uint8_t> best_core;

    auto insert = [&](Candidate candidate, std::uint64_t tested) {
      candidate.evaluation = evaluate(candidate.core);
      const std::uint32_t signature =
          candidate.evaluation.signature;
      auto found = by_signature.find(signature);
      if (found == by_signature.end()) {
        by_signature.emplace(signature, archive.size());
        archive.push_back(std::move(candidate));
      } else if (
          candidate.evaluation.rank() <
          archive[found->second].evaluation.rank()) {
        archive[found->second] = std::move(candidate);
      }
      const Candidate& retained =
          archive[by_signature.at(signature)];
      if (retained.evaluation.rank() < best_evaluation.rank()) {
        best_evaluation = retained.evaluation;
        best_core = retained.core;
        std::cout << "tested=" << tested
                  << " archive=" << archive.size()
                  << " mismatches=" << best_evaluation.mismatches
                  << " signature=" << best_evaluation.signature
                  << " linear_error=" << best_evaluation.linear_error
                  << " activity=" << best_evaluation.activity << "\n";
        print_compact_core(best_core);
        std::cout.flush();
      }
    };

    std::uint64_t tested = 0;
    insert(make_all_three(), ++tested);
    insert(make_cross(), ++tested);
    if (options_.integrated_geometry) {
      insert(make_integrated_gate_seed(), ++tested);
      insert(make_amplitude_best_seed(), ++tested);
      insert(make_amplitude_six_seed(), ++tested);
    }
    const int initial_random =
        std::min<std::uint64_t>(10000, options_.evaluations / 10);
    for (int index = 0; index < initial_random; ++index) {
      insert(make_random(), ++tested);
    }

    std::uniform_int_distribution<int> mutation_count(1, 12);
    std::bernoulli_distribution use_crossover(0.12);
    while (tested < options_.evaluations &&
           best_evaluation.mismatches != 0) {
      std::uniform_int_distribution<std::size_t> member(
          0, archive.size() - 1);
      Candidate child;
      if (use_crossover(rng_) && archive.size() >= 2) {
        child.core =
            crossover(archive[member(rng_)].core,
                      archive[member(rng_)].core);
      } else {
        child.core = archive[member(rng_)].core;
      }
      mutate_steps(child.core, mutation_count(rng_));
      insert(std::move(child), ++tested);
      if (tested % 1000000 == 0) {
        std::cout << "progress tested=" << tested
                  << " archive=" << archive.size()
                  << " best=" << best_evaluation.mismatches << "\n";
        std::cout.flush();
      }
      if (tested % 1000 == 0) {
        insert(make_random(), ++tested);
      }
    }

    if (best_evaluation.mismatches == 0) {
      std::cout << "FULL-ALPHABET PARITY CROSSING FOUND\n";
    } else {
      std::cout << "MAP-ELITES NO FULL-ALPHABET CROSSING FOUND\n";
    }
    std::cout << "tested=" << tested
              << " archive=" << archive.size()
              << " best mismatches=" << best_evaluation.mismatches
              << "\n";
    print_core(best_core);
    print_table(best_evaluation);
  }

  std::vector<int> independent_variables() const {
    std::vector<int> variables;
    if (options_.symmetric) {
      for (int row = 0; row < options_.n; ++row) {
        for (int column = row; column < options_.n; ++column) {
          const int index = row * options_.n + column;
          if (mutable_mask_[index]) variables.push_back(index);
        }
      }
    } else {
      variables = mutable_positions_;
    }
    return variables;
  }

  void run_defect_exhaustive() {
    const std::vector<int> variables = independent_variables();
    const std::vector<std::uint8_t> baseline_core =
        options_.defects_from_six
            ? make_amplitude_six_seed().core
            : (options_.defects_from_integrated
                   ? make_integrated_gate_seed().core
                   : fixed_template_);
    std::vector<std::uint8_t> core = baseline_core;
    Evaluation best_evaluation;
    best_evaluation.boundary_activity =
        std::numeric_limits<long long>::max();
    best_evaluation.mismatches = std::numeric_limits<int>::max();
    best_evaluation.selection_score =
        std::numeric_limits<long long>::max();
    std::vector<std::uint8_t> best_core;
    std::uint64_t tested = 0;

    auto consider = [&]() {
      ++tested;
      const Evaluation evaluation = evaluate(core);
      if (evaluation.rank() < best_evaluation.rank()) {
        best_evaluation = evaluation;
        best_core = core;
        std::cout << "tested=" << tested
                  << " mismatches=" << best_evaluation.mismatches
                  << " boolean=" << best_evaluation.boolean_mismatches
                  << " axis=" << best_evaluation.axis_mismatches
                  << " bool_count="
                  << best_evaluation.boolean_count_error
                  << " axis_count=" << best_evaluation.axis_count_error
                  << " boundary=" << best_evaluation.boundary_activity
                  << " linear_error=" << best_evaluation.linear_error
                  << " matrix=(" << best_evaluation.best_diagonal << ","
                  << best_evaluation.best_crosstalk << ")"
                  << " activity=" << best_evaluation.activity << "\n";
        if (options_.compact) {
          print_compact_core(best_core);
        } else {
          print_core(best_core);
          print_table(best_evaluation);
        }
        std::cout.flush();
      }
      return evaluation.mismatches == 0 &&
             evaluation.boundary_activity == 0;
    };

    bool found = consider();
    std::function<void(int, int)> enumerate =
        [&](int start, int remaining) {
          if (found) return;
          if (remaining == 0) {
            found = consider();
            return;
          }
          const int final_start =
              static_cast<int>(variables.size()) - remaining;
          for (int variable_index = start;
               variable_index <= final_start && !found;
               ++variable_index) {
            const int index = variables[variable_index];
            const auto baseline = baseline_core[index];
            const int row = index / options_.n;
            const int column = index % options_.n;
            for (int value = 0; value < 4 && !found; ++value) {
              if (value == baseline) continue;
              core[index] = static_cast<std::uint8_t>(value);
              if (options_.symmetric) {
                core[column * options_.n + row] =
                    static_cast<std::uint8_t>(value);
              }
              enumerate(variable_index + 1, remaining - 1);
            }
            core[index] = baseline;
            if (options_.symmetric) {
              core[column * options_.n + row] = baseline;
            }
          }
        };
    for (int defects = 1;
         defects <= options_.defect_depth && !found;
         ++defects) {
      enumerate(0, defects);
      std::cout << "completed_defect_depth=" << defects
                << " tested=" << tested << "\n";
      std::cout.flush();
    }

    if (found) {
      std::cout << "FULL-ALPHABET PARITY CROSSING FOUND\n";
    } else {
      std::cout << "DEFECT-EXHAUSTIVE NO FULL-ALPHABET CROSSING\n";
    }
    std::cout << "tested=" << tested
              << " best mismatches=" << best_evaluation.mismatches
              << " boundary=" << best_evaluation.boundary_activity
              << " linear_error=" << best_evaluation.linear_error << "\n";
    print_core(best_core);
    print_table(best_evaluation);
  }

  void run_exhaustive() {
    const std::vector<int> variables = independent_variables();
    if (variables.size() >= 32) {
      std::cerr << "exhaustive mode is limited to at most 31 base-4 "
                   "variables\n";
      std::exit(2);
    }
    std::uint64_t total = 1;
    for (std::size_t index = 0; index < variables.size(); ++index) {
      if (total > std::numeric_limits<std::uint64_t>::max() / 4) {
        std::cerr << "exhaustive space overflows uint64\n";
        std::exit(2);
      }
      total *= 4;
    }
    std::cout << "exhaustive variables=" << variables.size()
              << " candidates=" << total << "\n";

    Evaluation best_evaluation;
    best_evaluation.boundary_activity =
        std::numeric_limits<long long>::max();
    best_evaluation.mismatches = std::numeric_limits<int>::max();
    best_evaluation.selection_score =
        std::numeric_limits<long long>::max();
    std::vector<std::uint8_t> best_core;
    std::vector<std::uint8_t> core = fixed_template_;
    for (std::uint64_t code = 0; code < total; ++code) {
      std::uint64_t remaining = code;
      for (const int index : variables) {
        const auto digit = static_cast<std::uint8_t>(remaining & 3U);
        remaining >>= 2U;
        core[index] = digit;
        if (options_.symmetric) {
          const int row = index / options_.n;
          const int column = index % options_.n;
          core[column * options_.n + row] = digit;
        }
      }
      const Evaluation evaluation = evaluate(core);
      if (evaluation.rank() < best_evaluation.rank()) {
        best_evaluation = evaluation;
        best_core = core;
        std::cout << "candidate=" << code
                  << " mismatches=" << best_evaluation.mismatches
                  << " boolean=" << best_evaluation.boolean_mismatches
                  << " axis=" << best_evaluation.axis_mismatches
                  << " bool_count="
                  << best_evaluation.boolean_count_error
                  << " axis_count=" << best_evaluation.axis_count_error
                  << " boundary=" << best_evaluation.boundary_activity
                  << " linear_error=" << best_evaluation.linear_error
                  << " matrix=(" << best_evaluation.best_diagonal << ","
                  << best_evaluation.best_crosstalk << ")"
                  << " activity=" << best_evaluation.activity << "\n";
        if (!options_.compact) {
          print_core(best_core);
          print_table(best_evaluation);
        }
        std::cout.flush();
      }
      if (evaluation.mismatches == 0 &&
          evaluation.boundary_activity == 0) {
        std::cout << "FULL-ALPHABET PARITY CROSSING FOUND\n";
        return;
      }
    }
    std::cout << "EXHAUSTIVE NO FULL-ALPHABET CROSSING\n";
    std::cout << "best mismatches=" << best_evaluation.mismatches
              << " boundary=" << best_evaluation.boundary_activity
              << " linear_error=" << best_evaluation.linear_error << "\n";
    print_core(best_core);
    print_table(best_evaluation);
  }

  int position(int core_row, int core_column) const {
    return (options_.padding + core_row) * board_size_ +
           options_.padding + core_column;
  }

  void stabilize(std::vector<int>& state, std::vector<int>& odometer,
                 int addition_position, int addition_amount) const {
    state[addition_position] += addition_amount;
    std::vector<int> queue;
    queue.reserve(board_area_ * 2);
    std::vector<std::uint8_t> queued(board_area_, 0);
    if (state[addition_position] >= 4) {
      queue.push_back(addition_position);
      queued[addition_position] = 1;
    }
    std::size_t head = 0;
    while (head < queue.size()) {
      const int x = queue[head++];
      queued[x] = 0;
      const int count = state[x] / 4;
      if (count == 0) {
        continue;
      }
      state[x] -= 4 * count;
      odometer[x] += count;
      const int row = x / board_size_;
      const int column = x % board_size_;
      std::array<int, 4> neighbors{-1, -1, -1, -1};
      if (row > 0) neighbors[0] = x - board_size_;
      if (row + 1 < board_size_) neighbors[1] = x + board_size_;
      if (column > 0) neighbors[2] = x - 1;
      if (column + 1 < board_size_) neighbors[3] = x + 1;
      for (const int neighbor : neighbors) {
        if (neighbor < 0) continue;  // Grain falls into the sink.
        state[neighbor] += count;
        if (state[neighbor] >= 4 && !queued[neighbor]) {
          queued[neighbor] = 1;
          queue.push_back(neighbor);
        }
      }
    }
  }

  Evaluation evaluate(const std::vector<std::uint8_t>& core) const {
    Evaluation result;
    std::vector<int> base(board_area_, 0);
    for (std::size_t index = 0; index < core.size(); ++index) {
      base[core_positions_[index]] = core[index];
    }

    // Compute all sixteen states incrementally.  Abelianity makes the
    // cumulative odometer independent of whether north or west increments are
    // applied first.
    std::vector<int> north_state = base;
    std::vector<int> north_odometer(board_area_, 0);
    for (int a = 0; a < 4; ++a) {
      if (a > 0) {
        stabilize(north_state, north_odometer, north_,
                  options_.pulse_scale);
      }
      std::vector<int> state = north_state;
      std::vector<int> odometer = north_odometer;
      for (int b = 0; b < 4; ++b) {
        if (b > 0) {
          stabilize(state, odometer, west_, options_.pulse_scale);
        }
        const int south_count = odometer[south_];
        const int east_count = odometer[east_];
        result.counts[a][b] = {south_count, east_count};
        result.parities[a][b] = {south_count & 1, east_count & 1};
        const int bit = 2 * (4 * a + b);
        if (south_count & 1) result.signature |= (1U << bit);
        if (east_count & 1) result.signature |= (1U << (bit + 1));
        result.mismatches += ((south_count & 1) != (a & 1));
        result.mismatches += ((east_count & 1) != (b & 1));
        if (a <= 1 && b <= 1) {
          result.boolean_mismatches +=
              ((south_count & 1) != (a & 1));
          result.boolean_mismatches +=
              ((east_count & 1) != (b & 1));
          result.boolean_count_error +=
              std::llabs(static_cast<long long>(south_count) -
                         (a + 2 * b));
          result.boolean_count_error +=
              std::llabs(static_cast<long long>(east_count) -
                         (2 * a + b));
        }
        if (a == 0 || b == 0) {
          result.axis_mismatches +=
              ((south_count & 1) != (a & 1));
          result.axis_mismatches +=
              ((east_count & 1) != (b & 1));
          result.axis_count_error +=
              std::llabs(static_cast<long long>(south_count) -
                         (a + 2 * b));
          result.axis_count_error +=
              std::llabs(static_cast<long long>(east_count) -
                         (2 * a + b));
        }
        result.activity +=
            std::accumulate(odometer.begin(), odometer.end(), 0LL);
        for (const int boundary : outer_boundary_) {
          result.boundary_activity += odometer[boundary];
        }
      }
    }

    long long best_error = std::numeric_limits<long long>::max();
    for (int diagonal = 1; diagonal <= 11; diagonal += 2) {
      for (int crosstalk = 0; crosstalk <= 12; crosstalk += 2) {
        long long error = 0;
        for (int a = 0; a < 4; ++a) {
          for (int b = 0; b < 4; ++b) {
            const int target_s = diagonal * a + crosstalk * b;
            const int target_e = crosstalk * a + diagonal * b;
            error += std::llabs(
                static_cast<long long>(result.counts[a][b][0]) -
                target_s);
            error += std::llabs(
                static_cast<long long>(result.counts[a][b][1]) -
                target_e);
          }
        }
        if (error < best_error) {
          best_error = error;
          result.best_diagonal = diagonal;
          result.best_crosstalk = crosstalk;
        }
      }
    }
    result.linear_error = best_error;
    if (options_.fitness_mode == "parity") {
      result.selection_score =
          1000000LL * result.mismatches + result.linear_error;
    } else if (options_.fitness_mode == "blended") {
      result.selection_score =
          8LL * result.mismatches + result.linear_error;
    } else if (options_.fitness_mode == "boolean-first") {
      result.selection_score =
          1000000000LL * result.boolean_mismatches +
          1000000LL * result.boolean_count_error +
          1000LL * result.mismatches + result.linear_error;
    } else {
      result.selection_score =
          1000000000LL * result.axis_mismatches +
          1000000LL * result.axis_count_error +
          1000LL * result.mismatches + result.linear_error;
    }
    return result;
  }

  Candidate make_all_three() const {
    Candidate candidate;
    candidate.core = fixed_template_;
    for (const int index : mutable_positions_) {
      candidate.core[index] = 3;
    }
    return candidate;
  }

  Candidate make_cross() const {
    Candidate candidate;
    if (options_.plus_arms || options_.integrated_geometry) {
      candidate.core = fixed_template_;
      return candidate;
    }
    candidate.core.assign(options_.n * options_.n, 0);
    const int middle = options_.n / 2;
    for (int row = 0; row < options_.n; ++row) {
      for (int column = 0; column < options_.n; ++column) {
        if (std::abs(row - middle) <= 2 ||
            std::abs(column - middle) <= 2) {
          candidate.core[row * options_.n + column] = 3;
        }
      }
    }
    return candidate;
  }

  Candidate make_integrated_gate_seed() const {
    // Boolean p=1 crossover found by the companion integrated-gate search.
    // It was originally attached to south/east all-3 output corridors.  Here
    // we embed it at the junction of four long all-3 arms as a high-quality
    // seed for the harder amplitude-0..3 search.
    static constexpr int gate[6][6] = {
        {3, 2, 3, 2, 3, 2},
        {3, 0, 0, 3, 2, 2},
        {2, 2, 3, 3, 3, 3},
        {3, 3, 3, 1, 3, 3},
        {3, 3, 3, 2, 0, 1},
        {1, 2, 3, 3, 1, 0},
    };
    Candidate candidate;
    candidate.core = fixed_template_;
    for (const int index : mutable_positions_) {
      candidate.core[index] = 3;
    }
    const int middle = options_.n / 2;
    const int top = options_.integrated_geometry ? 0 : middle - 3;
    const int left = options_.integrated_geometry ? 0 : middle - 3;
    for (int row = 0; row < 6; ++row) {
      for (int column = 0; column < 6; ++column) {
        const int core_row = top + row;
        const int core_column = left + column;
        if (core_row < 0 || core_row >= options_.n ||
            core_column < 0 || core_column >= options_.n) {
          continue;
        }
        const int index = core_row * options_.n + core_column;
        if (mutable_mask_[index]) {
          candidate.core[index] =
              static_cast<std::uint8_t>(gate[row][column]);
        }
      }
    }
    return candidate;
  }

  Candidate make_amplitude_best_seed() const {
    // Best full-alphabet table found in the exhaustive Hamming-radius-4
    // neighborhood of the certified Boolean gate (7 of 32 parity bits
    // wrong).  Keeping it in every integrated-geometry population lets the
    // stochastic search continue from the exact neighborhood result.
    static constexpr int gate[6][6] = {
        {3, 2, 3, 2, 3, 2},
        {3, 0, 2, 3, 0, 2},
        {2, 2, 3, 3, 0, 3},
        {3, 3, 3, 1, 3, 3},
        {3, 3, 3, 2, 0, 1},
        {2, 2, 3, 3, 1, 0},
    };
    Candidate candidate;
    candidate.core = fixed_template_;
    for (const int index : mutable_positions_) {
      candidate.core[index] = 3;
    }
    for (int row = 0; row < 6; ++row) {
      for (int column = 0; column < 6; ++column) {
        const int index = row * options_.n + column;
        if (mutable_mask_[index]) {
          candidate.core[index] =
              static_cast<std::uint8_t>(gate[row][column]);
        }
      }
    }
    return candidate;
  }

  Candidate make_amplitude_six_seed() const {
    // Six-error full-alphabet table found by continuing the exact
    // radius-four witness with the large C++ evolutionary search.
    static constexpr int gate[6][6] = {
        {3, 1, 3, 0, 1, 3},
        {2, 3, 2, 0, 2, 1},
        {3, 3, 1, 3, 3, 2},
        {1, 2, 1, 3, 3, 1},
        {0, 3, 3, 3, 3, 2},
        {0, 0, 3, 3, 3, 0},
    };
    Candidate candidate;
    candidate.core = fixed_template_;
    for (const int index : mutable_positions_) {
      candidate.core[index] = 3;
    }
    for (int row = 0; row < 6; ++row) {
      for (int column = 0; column < 6; ++column) {
        candidate.core[row * options_.n + column] =
            static_cast<std::uint8_t>(gate[row][column]);
      }
    }
    return candidate;
  }

  Candidate make_random() {
    Candidate candidate;
    candidate.core = fixed_template_;
    std::discrete_distribution<int> height({2, 1, 3, 10});
    if (options_.symmetric) {
      for (int row = 0; row < options_.n; ++row) {
        for (int column = row; column < options_.n; ++column) {
          const int index = row * options_.n + column;
          if (!mutable_mask_[index]) continue;
          const auto value = static_cast<std::uint8_t>(height(rng_));
          candidate.core[index] = value;
          candidate.core[column * options_.n + row] = value;
        }
      }
    } else {
      for (const int index : mutable_positions_) {
        candidate.core[index] =
            static_cast<std::uint8_t>(height(rng_));
      }
    }
    return candidate;
  }

  std::vector<std::uint8_t> crossover(
      const std::vector<std::uint8_t>& left,
      const std::vector<std::uint8_t>& right) {
    std::vector<std::uint8_t> child = fixed_template_;
    std::bernoulli_distribution choose_left(0.5);
    if (options_.symmetric) {
      for (int row = 0; row < options_.n; ++row) {
        for (int column = row; column < options_.n; ++column) {
          const int index = row * options_.n + column;
          if (!mutable_mask_[index]) continue;
          const auto value =
              choose_left(rng_) ? left[index] : right[index];
          child[index] = value;
          child[column * options_.n + row] = value;
        }
      }
    } else {
      for (const int index : mutable_positions_) {
        child[index] =
            choose_left(rng_) ? left[index] : right[index];
      }
    }
    return child;
  }

  void mutate(std::vector<std::uint8_t>& core, double rate) {
    std::bernoulli_distribution should_mutate(rate);
    std::uniform_int_distribution<int> replacement(0, 2);
    auto mutate_value = [&](std::uint8_t value) {
      int next = replacement(rng_);
      if (next >= value) {
        ++next;
      }
      return static_cast<std::uint8_t>(next);
    };
    if (options_.symmetric) {
      for (int row = 0; row < options_.n; ++row) {
        for (int column = row; column < options_.n; ++column) {
          const int index = row * options_.n + column;
          if (!mutable_mask_[index]) continue;
          if (should_mutate(rng_)) {
            const auto value = mutate_value(core[index]);
            core[index] = value;
            core[column * options_.n + row] = value;
          }
        }
      }
    } else {
      for (const int index : mutable_positions_) {
        if (should_mutate(rng_)) {
          core[index] = mutate_value(core[index]);
        }
      }
    }
  }

  void mutate_steps(std::vector<std::uint8_t>& core, int steps) {
    std::uniform_int_distribution<std::size_t> choose(
        0, mutable_positions_.size() - 1);
    std::uniform_int_distribution<int> replacement(0, 2);
    for (int step = 0; step < steps; ++step) {
      const int index = mutable_positions_[choose(rng_)];
      int value = replacement(rng_);
      if (value >= core[index]) ++value;
      core[index] = static_cast<std::uint8_t>(value);
      if (options_.symmetric) {
        const int row = index / options_.n;
        const int column = index % options_.n;
        core[column * options_.n + row] =
            static_cast<std::uint8_t>(value);
      }
    }
  }

  void print_core(const std::vector<std::uint8_t>& core) const {
    std::cout << "core\n";
    for (int row = 0; row < options_.n; ++row) {
      for (int column = 0; column < options_.n; ++column) {
        std::cout
            << static_cast<int>(core[row * options_.n + column])
            << (column + 1 == options_.n ? '\n' : ' ');
      }
    }
  }

  void print_compact_core(
      const std::vector<std::uint8_t>& core) const {
    std::cout << "compact_core=";
    for (std::size_t index = 0; index < core.size(); ++index) {
      std::cout << static_cast<int>(core[index]);
    }
    std::cout << "\n";
  }

  static void print_table(const Evaluation& evaluation) {
    std::cout << "table a,b -> S,E [parity]\n";
    for (int a = 0; a < 4; ++a) {
      for (int b = 0; b < 4; ++b) {
        std::cout << a << "," << b << " -> "
                  << evaluation.counts[a][b][0] << ","
                  << evaluation.counts[a][b][1] << " ["
                  << evaluation.parities[a][b][0] << ","
                  << evaluation.parities[a][b][1] << "]\n";
      }
    }
  }

  Options options_;
  int board_size_;
  int board_area_;
  int north_;
  int west_;
  int south_;
  int east_;
  std::vector<int> core_positions_;
  std::vector<int> outer_boundary_;
  std::vector<std::uint8_t> fixed_template_;
  std::vector<std::uint8_t> mutable_mask_;
  std::vector<int> mutable_positions_;
  mutable std::mt19937_64 rng_;
};

int main(int argc, char** argv) {
  const Options options = parse_options(argc, argv);
  Search search(options);
  search.run();
  return 0;
}
