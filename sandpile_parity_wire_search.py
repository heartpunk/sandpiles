#!/usr/bin/env python3
"""Search for a parity-preserving sandpile wire/transducer.

A finite stable rectangular core is embedded in a zero background.  The input
is the middle cell of the core's left edge and the output is the corresponding
cell of its right edge.  Starting from the *same* background, inject k grains
at the input for k = 0, 1, 2, 3 and record the output odometer.

The strongest target is the exact map

    output_topplings(k) = k.

The weaker target is parity preservation:

    output_topplings(k) mod 2 = k mod 2.

Directly adding k grains at the input is locally identical to having an
external neighboring vertex topple k times into that input.  The padded
embedding checks that no avalanche reaches the artificial sink boundary.

This is exploratory synthesis, not a proof.  Every reported candidate is
replayed with the independent NumPy stabilizer in sandpile_crossing_search.py.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
from dataclasses import dataclass
import itertools
import random

import numpy as np

from sandpile_crossing_search import stabilize as numpy_stabilize


Coord = tuple[int, int]


@dataclass(frozen=True)
class WireMetrics:
    counts: tuple[int, int, int]
    increments: tuple[int, int, int]
    parities: tuple[int, int, int]
    parity_mismatches: int
    exact_error: int
    boundary_topplings: int
    padding_topplings: int
    side_leakage: int
    activity: int


def ports(height: int, width: int, padding: int) -> tuple[Coord, Coord]:
    row = padding + height // 2
    return (row, padding), (row, padding + width - 1)


def embedded_board(
    core: tuple[int, ...] | np.ndarray,
    height: int,
    width: int,
    padding: int,
) -> np.ndarray:
    board = np.zeros(
        (height + 2 * padding, width + 2 * padding),
        dtype=np.int8,
    )
    board[
        padding : padding + height,
        padding : padding + width,
    ] = np.asarray(core, dtype=np.int8).reshape((height, width))
    return board


def stabilize_flat_in_place(
    state: list[int],
    odometer: list[int],
    height: int,
    width: int,
    addition: int,
) -> None:
    """Add one grain and update the legal stabilization in place."""
    state[addition] += 1
    queue: deque[int] = deque()
    queued = [False] * len(state)
    if state[addition] >= 4:
        queue.append(addition)
        queued[addition] = True

    while queue:
        position = queue.popleft()
        queued[position] = False
        count = state[position] // 4
        if count == 0:
            continue
        state[position] -= 4 * count
        odometer[position] += count
        row, column = divmod(position, width)
        if row:
            neighbor = position - width
            state[neighbor] += count
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if row + 1 < height:
            neighbor = position + width
            state[neighbor] += count
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if column:
            neighbor = position - 1
            state[neighbor] += count
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if column + 1 < width:
            neighbor = position + 1
            state[neighbor] += count
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)


def flat_runs(
    core: tuple[int, ...],
    height: int,
    width: int,
    padding: int,
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    board_height = height + 2 * padding
    board_width = width + 2 * padding
    state = [0] * (board_height * board_width)
    for core_row in range(height):
        start = (padding + core_row) * board_width + padding
        source = core_row * width
        state[start : start + width] = core[source : source + width]

    input_coord, _ = ports(height, width, padding)
    input_position = input_coord[0] * board_width + input_coord[1]
    odometer = [0] * len(state)
    results = []
    for _ in range(3):
        stabilize_flat_in_place(
            state,
            odometer,
            board_height,
            board_width,
            input_position,
        )
        results.append(tuple(odometer))
    return results[0], results[1], results[2]


def metrics_from_runs(
    runs: tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]],
    height: int,
    width: int,
    padding: int,
) -> WireMetrics:
    board_height = height + 2 * padding
    board_width = width + 2 * padding
    input_coord, output_coord = ports(height, width, padding)
    output_position = output_coord[0] * board_width + output_coord[1]
    counts = tuple(run[output_position] for run in runs)
    increments = (
        counts[0],
        counts[1] - counts[0],
        counts[2] - counts[1],
    )
    parities = tuple(count & 1 for count in counts)
    parity_mismatches = sum(
        got != want for got, want in zip(parities, (1, 0, 1))
    )
    exact_error = sum(abs(got - want) for got, want in zip(counts, (1, 2, 3)))

    outer_boundary = {
        row * board_width + column
        for row in range(board_height)
        for column in range(board_width)
        if (
            row == 0
            or row == board_height - 1
            or column == 0
            or column == board_width - 1
        )
    }
    core_positions = {
        (padding + row) * board_width + padding + column
        for row in range(height)
        for column in range(width)
    }
    input_position = input_coord[0] * board_width + input_coord[1]
    output_position = output_coord[0] * board_width + output_coord[1]
    side_boundary = {
        position
        for position in core_positions
        if position not in (input_position, output_position)
        and (
            (position // board_width) in (padding, padding + height - 1)
            or (position % board_width) in (padding, padding + width - 1)
        )
    }
    final_run = runs[-1]
    boundary_topplings = sum(final_run[p] for p in outer_boundary)
    padding_topplings = sum(
        count
        for position, count in enumerate(final_run)
        if position not in core_positions
    )
    side_leakage = sum(final_run[p] for p in side_boundary)
    activity = sum(final_run)
    return WireMetrics(
        counts=counts,
        increments=increments,
        parities=parities,
        parity_mismatches=parity_mismatches,
        exact_error=exact_error,
        boundary_topplings=boundary_topplings,
        padding_topplings=padding_topplings,
        side_leakage=side_leakage,
        activity=activity,
    )


def evaluate(
    core: tuple[int, ...],
    height: int,
    width: int,
    padding: int,
) -> tuple[int, WireMetrics]:
    runs = flat_runs(core, height, width, padding)
    metrics = metrics_from_runs(runs, height, width, padding)
    score = (
        metrics.boundary_topplings * 100_000_000
        + metrics.parity_mismatches * 1_000_000
        + metrics.exact_error * 10_000
        + metrics.padding_topplings * 100
        + metrics.side_leakage * 10
        + metrics.activity
    )
    return score, metrics


def independently_verify(
    core: tuple[int, ...],
    height: int,
    width: int,
    padding: int,
) -> WireMetrics:
    board = embedded_board(core, height, width, padding)
    input_coord, output_coord = ports(height, width, padding)
    numpy_runs = tuple(
        numpy_stabilize(board, ((input_coord, amount),))
        for amount in (1, 2, 3)
    )
    numpy_counts = tuple(int(run[output_coord]) for run in numpy_runs)

    flat = flat_runs(core, height, width, padding)
    flat_metrics = metrics_from_runs(flat, height, width, padding)
    if numpy_counts != flat_metrics.counts:
        raise AssertionError(
            f"independent stabilizers disagree: NumPy={numpy_counts}, "
            f"flat={flat_metrics.counts}"
        )
    for flat_run, numpy_run in zip(flat, numpy_runs):
        if flat_run != tuple(int(value) for value in numpy_run.flat):
            raise AssertionError("independent odometers disagree")
    return flat_metrics


def report_candidate(
    label: str,
    core: tuple[int, ...],
    height: int,
    width: int,
    padding: int,
) -> None:
    checked = independently_verify(core, height, width, padding)
    if checked.boundary_topplings:
        raise AssertionError("candidate reaches the artificial sink boundary")
    print(label, flush=True)
    print(
        np.asarray(core, dtype=np.int8).reshape((height, width)),
        flush=True,
    )
    print(checked, flush=True)


def final_state_from_odometer(
    base: np.ndarray,
    input_coord: Coord,
    amount: int,
    odometer: np.ndarray,
) -> np.ndarray:
    """Reconstruct eta + amount*delta_input - Delta*odometer."""
    final = base.astype(np.int32, copy=True)
    final[input_coord] += amount
    final -= 4 * odometer
    final[1:, :] += odometer[:-1, :]
    final[:-1, :] += odometer[1:, :]
    final[:, 1:] += odometer[:, :-1]
    final[:, :-1] += odometer[:, 1:]
    if np.any(final < 0) or np.any(final >= 4):
        raise AssertionError("reconstructed state is not stable")
    return final


def exact_five_by_five_certificate(padding: int) -> None:
    """Print and independently verify the smallest exact hit found so far."""
    height = width = 5
    core = (3,) * 25
    board = embedded_board(core, height, width, padding)
    input_coord = (padding + 2, padding)
    output_one = (padding + 2, padding + 1)
    output_two = (padding + 2, padding + 2)
    reflected_state_port = (padding + 2, padding - 1)
    flat = flat_runs(core, height, width, padding)

    print("EXACT 5x5 ALL-THREES TRANSDUCER", flush=True)
    print("local input=(2,0), local outputs=(2,1),(2,2)", flush=True)
    print(
        "west exterior state port is local=(2,-1)",
        flush=True,
    )
    for amount in range(4):
        if amount == 0:
            odometer = np.zeros_like(board, dtype=np.int32)
        else:
            odometer = numpy_stabilize(
                board,
                ((input_coord, amount),),
            )
            if tuple(int(value) for value in odometer.flat) != flat[amount - 1]:
                raise AssertionError("flat and NumPy stabilizers disagree")
        final = final_state_from_odometer(
            board,
            input_coord,
            amount,
            odometer,
        )
        outer_boundary_topplings = (
            int(odometer[0, :].sum())
            + int(odometer[-1, :].sum())
            + int(odometer[1:-1, 0].sum())
            + int(odometer[1:-1, -1].sum())
        )
        counts = (
            int(odometer[output_one]),
            int(odometer[output_two]),
        )
        reflected = int(final[reflected_state_port])
        if counts != (amount, amount):
            raise AssertionError(
                f"exact output failed at k={amount}: {counts}"
            )
        if reflected != amount:
            raise AssertionError(
                f"state interface failed at k={amount}: {reflected}"
            )
        if outer_boundary_topplings:
            raise AssertionError("avalanche reached artificial boundary")
        print(
            f"k={amount} output_odometers={counts} "
            f"west_exterior_final={reflected} "
            f"outer_boundary_odometer={outer_boundary_topplings}",
            flush=True,
        )
        print("core odometer", flush=True)
        print(
            odometer[
                padding : padding + height,
                padding : padding + width,
            ],
            flush=True,
        )
        print("one-cell-halo final state", flush=True)
        print(
            final[
                padding - 1 : padding + height + 1,
                padding - 1 : padding + width + 1,
            ],
            flush=True,
        )


def expected_five_by_length_odometer(
    length: int,
    amount: int,
    padding: int,
) -> np.ndarray:
    """Closed form for the all-3 5 x length strip, for amount <= 3."""
    result = np.zeros(
        (5 + 2 * padding, length + 2 * padding),
        dtype=np.int32,
    )
    if amount >= 1:
        result[padding : padding + 5, padding : padding + length] += 1
    if amount >= 2:
        result[
            padding + 1 : padding + 4,
            padding : padding + length - 1,
        ] += 1
    if amount >= 3:
        result[
            padding + 2,
            padding : padding + length - 2,
        ] += 1
    return result


def verify_five_by_length_theorem(
    maximum_length: int,
    padding: int,
) -> None:
    """Mechanically check the explicit arbitrary-length wire formula."""
    if maximum_length < 4:
        raise ValueError("maximum length must be at least 4")
    for length in range(4, maximum_length + 1):
        core = (3,) * (5 * length)
        board = embedded_board(core, 5, length, padding)
        input_coord = (padding + 2, padding)
        flat = flat_runs(core, 5, length, padding)
        for amount in range(4):
            expected = expected_five_by_length_odometer(
                length,
                amount,
                padding,
            )
            actual = (
                np.zeros_like(board, dtype=np.int32)
                if amount == 0
                else numpy_stabilize(board, ((input_coord, amount),))
            )
            if not np.array_equal(actual, expected):
                raise AssertionError(
                    f"closed form failed at length={length}, k={amount}"
                )
            if amount and tuple(int(value) for value in actual.flat) != flat[amount - 1]:
                raise AssertionError(
                    f"independent stabilizers disagree at L={length}, k={amount}"
                )
            final = final_state_from_odometer(
                board,
                input_coord,
                amount,
                actual,
            )
            if np.any(final < 0) or np.any(final >= 4):
                raise AssertionError("closed form does not stabilize")

            # Every centerline tap with two columns of tail remaining carries
            # exactly k topplings.
            taps = actual[
                padding + 2,
                padding : padding + length - 2,
            ]
            if not np.all(taps == amount):
                raise AssertionError(
                    f"tap failed at length={length}, k={amount}"
                )
    print(
        "PASS: explicit 5xL all-threes amplitude-wire formula for "
        f"every 4 <= L <= {maximum_length}, k=0,1,2,3; "
        "two independent stabilizers agree and all final states are stable",
        flush=True,
    )
    print(
        "u1 = 1 on 5xL; "
        "u2 = u1 + 1 on inner 3x(L-1); "
        "u3 = u2 + 1 on center 1x(L-2)",
        flush=True,
    )


def exhaustive(
    height: int,
    width: int,
    padding: int,
    stop_at_exact: bool,
) -> None:
    total = 4 ** (height * width)
    exact_count = 0
    parity_count = 0
    first_exact: tuple[int, ...] | None = None
    first_parity: tuple[int, ...] | None = None
    best: tuple[int, tuple[int, ...], WireMetrics] | None = None

    for index, core in enumerate(
        itertools.product(range(4), repeat=height * width)
    ):
        score, metrics = evaluate(core, height, width, padding)
        candidate = (score, core, metrics)
        if best is None or candidate[0] < best[0]:
            best = candidate
        if (
            metrics.parity_mismatches == 0
            and metrics.boundary_topplings == 0
        ):
            parity_count += 1
            first_parity = first_parity or core
        if (
            metrics.exact_error == 0
            and metrics.boundary_topplings == 0
        ):
            exact_count += 1
            first_exact = first_exact or core
            if stop_at_exact:
                report_candidate(
                    f"EXACT WIRE FOUND index={index}/{total}",
                    core,
                    height,
                    width,
                    padding,
                )
                return
        if index and index % 100_000 == 0:
            print(f"checked={index}/{total}", flush=True)

    assert best is not None
    print(
        f"EXHAUSTED shape={height}x{width} backgrounds={total} "
        f"parity_solutions={parity_count} exact_solutions={exact_count}",
        flush=True,
    )
    if first_exact is not None:
        report_candidate(
            "FIRST EXACT WIRE",
            first_exact,
            height,
            width,
            padding,
        )
    elif first_parity is not None:
        report_candidate(
            "FIRST PARITY WIRE",
            first_parity,
            height,
            width,
            padding,
        )
    else:
        _, core, metrics = best
        print("NO PARITY WIRE; BEST", flush=True)
        print(
            np.asarray(core, dtype=np.int8).reshape((height, width)),
            flush=True,
        )
        print(metrics, flush=True)


def mutate(
    core: tuple[int, ...],
    rng: random.Random,
    rate: float,
) -> tuple[int, ...]:
    result = list(core)
    for position, value in enumerate(result):
        if rng.random() < rate:
            replacement = rng.randrange(3)
            if replacement >= value:
                replacement += 1
            result[position] = replacement
    return tuple(result)


def crossover(
    left: tuple[int, ...],
    right: tuple[int, ...],
    rng: random.Random,
) -> tuple[int, ...]:
    return tuple(
        a if rng.random() < 0.5 else b
        for a, b in zip(left, right)
    )


def genetic_search(
    height: int,
    width: int,
    padding: int,
    population_size: int,
    generations: int,
    seed: int,
) -> None:
    rng = random.Random(seed)

    def fresh() -> tuple[int, ...]:
        return tuple(
            rng.choices((0, 1, 2, 3), weights=(3, 2, 3, 7), k=height * width)
        )

    population = [fresh() for _ in range(population_size)]
    best_score = 10**30
    best_core: tuple[int, ...] | None = None
    best_metrics: WireMetrics | None = None
    for generation in range(generations):
        ranked = []
        for core in population:
            score, metrics = evaluate(core, height, width, padding)
            ranked.append((score, core, metrics))
        ranked.sort(key=lambda item: item[0])
        score, core, metrics = ranked[0]
        if score < best_score:
            best_score = score
            best_core = core
            best_metrics = metrics
            print(
                f"generation={generation} score={score} metrics={metrics}",
                flush=True,
            )
            print(
                np.asarray(core, dtype=np.int8).reshape((height, width)),
                flush=True,
            )
        if (
            metrics.exact_error == 0
            and metrics.boundary_topplings == 0
        ):
            report_candidate(
                f"EXACT WIRE FOUND generation={generation}",
                core,
                height,
                width,
                padding,
            )
            return
        if (
            metrics.parity_mismatches == 0
            and metrics.boundary_topplings == 0
        ):
            # Keep searching for the exact affine map, but verify the weaker hit.
            independently_verify(core, height, width, padding)

        elite_count = max(4, population_size // 10)
        elites = [item[1] for item in ranked[:elite_count]]
        next_population = elites.copy()
        mutation_rate = max(
            1.0 / (height * width),
            0.12 * (1 - generation / generations),
        )
        while len(next_population) < population_size:
            child = crossover(
                rng.choice(elites),
                rng.choice(elites),
                rng,
            )
            next_population.append(mutate(child, rng, mutation_rate))
        population = next_population

    assert best_core is not None and best_metrics is not None
    print(
        f"no exact wire found; best_score={best_score} "
        f"best_metrics={best_metrics}",
        flush=True,
    )
    report_candidate(
        "BEST CANDIDATE",
        best_core,
        height,
        width,
        padding,
    )


def random_search(
    height: int,
    width: int,
    padding: int,
    samples: int,
    seed: int,
) -> None:
    """Search the rugged parity objective without assuming local smoothness."""
    rng = random.Random(seed)
    best: tuple[int, tuple[int, ...], WireMetrics] | None = None
    count_patterns: Counter[tuple[int, int, int]] = Counter()
    for index in range(samples):
        # Sweep the threshold-ready density instead of baking in one prior.
        weight_three = 1 + (index % 16)
        core = tuple(
            rng.choices(
                (0, 1, 2, 3),
                weights=(5, 2, 3, weight_three),
                k=height * width,
            )
        )
        score, metrics = evaluate(core, height, width, padding)
        count_patterns[metrics.counts] += 1
        candidate = (score, core, metrics)
        if best is None or candidate[0] < best[0]:
            best = candidate
        if (
            metrics.parity_mismatches == 0
            and metrics.boundary_topplings == 0
        ):
            report_candidate(
                f"PARITY WIRE FOUND sample={index}/{samples}",
                core,
                height,
                width,
                padding,
            )
            return
        if index and index % 100_000 == 0:
            assert best is not None
            print(
                f"checked={index}/{samples} best={best[2]}",
                flush=True,
            )
    assert best is not None
    print(
        f"no parity wire in {samples} random cores; best={best[2]}",
        flush=True,
    )
    print(
        np.asarray(best[1], dtype=np.int8).reshape((height, width)),
        flush=True,
    )
    print(
        f"most_common_count_patterns={count_patterns.most_common(20)}",
        flush=True,
    )


def parse_shape(text: str) -> tuple[int, int]:
    try:
        height_text, width_text = text.lower().split("x", 1)
        height, width = int(height_text), int(width_text)
    except (ValueError, AttributeError) as error:
        raise argparse.ArgumentTypeError("shape must look like 3x4") from error
    if height < 1 or width < 2:
        raise argparse.ArgumentTypeError("require height >= 1 and width >= 2")
    return height, width


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shape", type=parse_shape, default=(3, 3))
    parser.add_argument("--padding", type=int, default=3)
    parser.add_argument("--exhaustive", action="store_true")
    parser.add_argument("--stop-at-exact", action="store_true")
    parser.add_argument("--population", type=int, default=800)
    parser.add_argument("--generations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--random-samples", type=int, default=0)
    parser.add_argument("--certificate", action="store_true")
    parser.add_argument("--strip-theorem-max-length", type=int, default=0)
    args = parser.parse_args()
    if args.padding < 1:
        parser.error("--padding must be positive")
    height, width = args.shape
    selected_modes = sum(
        bool(mode)
        for mode in (
            args.exhaustive,
            args.random_samples,
            args.certificate,
            args.strip_theorem_max_length,
        )
    )
    if selected_modes > 1:
        parser.error(
            "choose only one of --exhaustive, --random-samples, --certificate"
        )
    if args.certificate:
        exact_five_by_five_certificate(args.padding)
    elif args.strip_theorem_max_length:
        verify_five_by_length_theorem(
            args.strip_theorem_max_length,
            args.padding,
        )
    elif args.exhaustive:
        exhaustive(
            height,
            width,
            args.padding,
            args.stop_at_exact,
        )
    elif args.random_samples:
        random_search(
            height,
            width,
            args.padding,
            args.random_samples,
            args.seed,
        )
    else:
        genetic_search(
            height,
            width,
            args.padding,
            args.population,
            args.generations,
            args.seed,
        )


if __name__ == "__main__":
    main()
