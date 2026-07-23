#!/usr/bin/env python3
"""Search for parity-coded crossings in the 2D von Neumann sandpile.

A stable background receives an equal positive pulse at the north input,
the west input, both, or neither.  The logical outputs are the parities of
the south and east output odometers.  With output order (south, east), the
required truth table is

    neither -> 00
    north   -> 10
    west    -> 01
    both    -> 11

The exhaustive mode checks every stable background on a tiny board.  The
genetic search is exploratory: every reported solution is rechecked with the
independent NumPy stabilizer from sandpile_crossing_search.py.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import itertools
import random

import numpy as np

from sandpile_crossing_search import Ports, crossover, mutate, stabilize


@dataclass(frozen=True)
class ParityMetrics:
    mismatches: int
    parities: tuple[int, int, int, int, int, int]
    counts: tuple[int, int, int, int, int, int]
    activity: int


def runs_for(
    base: np.ndarray, ports: Ports, pulse: int
) -> dict[str, np.ndarray]:
    return {
        "N": stabilize(base, ((ports.north, pulse),)),
        "W": stabilize(base, ((ports.west, pulse),)),
        "NW": stabilize(
            base,
            ((ports.north, pulse), (ports.west, pulse)),
        ),
    }


def metrics_for(
    runs: dict[str, np.ndarray], ports: Ports
) -> ParityMetrics:
    counts = (
        int(runs["N"][ports.south]),
        int(runs["N"][ports.east]),
        int(runs["W"][ports.south]),
        int(runs["W"][ports.east]),
        int(runs["NW"][ports.south]),
        int(runs["NW"][ports.east]),
    )
    parities = tuple(value & 1 for value in counts)
    target = (1, 0, 0, 1, 1, 1)
    mismatches = sum(got != want for got, want in zip(parities, target))
    activity = sum(int(odo.sum()) for odo in runs.values())
    return ParityMetrics(mismatches, parities, counts, activity)


def evaluate(
    base: np.ndarray, ports: Ports, pulse: int
) -> tuple[int, ParityMetrics, dict[str, np.ndarray]]:
    runs = runs_for(base, ports, pulse)
    metrics = metrics_for(runs, ports)

    # Exact small witnesses repeatedly realize the count vector below.  Its
    # integer distance provides a smoother hint than parity alone while parity
    # remains the primary objective.
    canonical_counts = (1, 2, 2, 1, 3, 3)
    distance = sum(
        abs(got - want)
        for got, want in zip(metrics.counts, canonical_counts)
    )
    score = (
        metrics.mismatches * 1_000_000
        + distance * 1_000
        + metrics.activity
    )
    return score, metrics, runs


def stabilize_flat(
    base: tuple[int, ...],
    n: int,
    additions: tuple[tuple[int, int], ...],
) -> tuple[int, ...]:
    """Small allocation-light reference stabilizer used by exhaustive search."""
    state = list(base)
    for position, amount in additions:
        state[position] += amount

    size = n * n
    odometer = [0] * size
    queued = [False] * size
    queue: deque[int] = deque()
    for position, value in enumerate(state):
        if value >= 4:
            queued[position] = True
            queue.append(position)

    while queue:
        position = queue.popleft()
        queued[position] = False
        amount = state[position] // 4
        if amount == 0:
            continue
        state[position] -= 4 * amount
        odometer[position] += amount
        row, column = divmod(position, n)
        if row:
            neighbor = position - n
            state[neighbor] += amount
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if row + 1 < n:
            neighbor = position + n
            state[neighbor] += amount
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if column:
            neighbor = position - 1
            state[neighbor] += amount
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if column + 1 < n:
            neighbor = position + 1
            state[neighbor] += amount
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
    return tuple(odometer)


def flat_counts(
    base: tuple[int, ...],
    n: int,
    pulse: int,
    north: int,
    west: int,
    south: int,
    east: int,
) -> tuple[int, int, int, int, int, int]:
    north_run = stabilize_flat(base, n, ((north, pulse),))
    west_run = stabilize_flat(base, n, ((west, pulse),))
    both_run = stabilize_flat(
        base,
        n,
        ((north, pulse), (west, pulse)),
    )
    return (
        north_run[south],
        north_run[east],
        west_run[south],
        west_run[east],
        both_run[south],
        both_run[east],
    )


def independently_verify(
    base: tuple[int, ...], n: int, pulse: int
) -> tuple[ParityMetrics, dict[str, np.ndarray]]:
    mid = n // 2
    ports = Ports((0, mid), (mid, 0), (n - 1, mid), (mid, n - 1))
    array = np.array(base, dtype=np.int8).reshape((n, n))
    runs = runs_for(array, ports, pulse)
    metrics = metrics_for(runs, ports)

    flat = flat_counts(
        base,
        n,
        pulse,
        ports.north[0] * n + ports.north[1],
        ports.west[0] * n + ports.west[1],
        ports.south[0] * n + ports.south[1],
        ports.east[0] * n + ports.east[1],
    )
    if flat != metrics.counts:
        raise AssertionError(
            f"stabilizers disagree: flat={flat}, numpy={metrics.counts}"
        )
    return metrics, runs


def add_and_stabilize_in_place(
    state: list[int],
    odometer: list[int],
    n: int,
    additions: tuple[int, ...],
) -> None:
    """Add one grain at each listed position and update a stabilization."""
    queued = [False] * (n * n)
    queue: deque[int] = deque()
    for position in additions:
        state[position] += 1
        if state[position] >= 4 and not queued[position]:
            queued[position] = True
            queue.append(position)

    while queue:
        position = queue.popleft()
        queued[position] = False
        amount = state[position] // 4
        if amount == 0:
            continue
        state[position] -= 4 * amount
        odometer[position] += amount
        row, column = divmod(position, n)
        if row:
            neighbor = position - n
            state[neighbor] += amount
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if row + 1 < n:
            neighbor = position + n
            state[neighbor] += amount
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if column:
            neighbor = position - 1
            state[neighbor] += amount
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if column + 1 < n:
            neighbor = position + 1
            state[neighbor] += amount
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)


def independently_verify_embedded(
    core: tuple[int, ...],
    core_size: int,
    padding: int,
    pulse: int,
    port_inset: int = 0,
) -> tuple[ParityMetrics, dict[str, np.ndarray]]:
    board_size = core_size + 2 * padding
    board = np.zeros((board_size, board_size), dtype=np.int8)
    board[
        padding : padding + core_size,
        padding : padding + core_size,
    ] = np.array(core, dtype=np.int8).reshape((core_size, core_size))
    mid = core_size // 2
    ports = Ports(
        (padding + port_inset, padding + mid),
        (padding + mid, padding + port_inset),
        (
            padding + core_size - 1 - port_inset,
            padding + mid,
        ),
        (
            padding + mid,
            padding + core_size - 1 - port_inset,
        ),
    )
    runs = runs_for(board, ports, pulse)
    metrics = metrics_for(runs, ports)
    for name, odometer in runs.items():
        boundary_activity = (
            int(odometer[0, :].sum())
            + int(odometer[-1, :].sum())
            + int(odometer[1:-1, 0].sum())
            + int(odometer[1:-1, -1].sum())
        )
        if boundary_activity:
            raise AssertionError(
                f"{name} reaches padded boundary; increase padding"
            )
    return metrics, runs


def exhaustive_embedded(
    core_size: int,
    pulses: tuple[int, ...],
    padding: int,
    symmetric: bool,
) -> None:
    """Exhaust finite-support cores surrounded by a quiescent zero lattice."""
    if core_size < 3:
        raise ValueError("the four ports require core_size >= 3")
    if padding < 1:
        raise ValueError("padding must be positive")

    board_size = core_size + 2 * padding
    board_area = board_size * board_size
    mid = core_size // 2

    def board_position(core_row: int, core_column: int) -> int:
        return (
            (padding + core_row) * board_size
            + padding
            + core_column
        )

    core_positions = tuple(
        board_position(row, column)
        for row in range(core_size)
        for column in range(core_size)
    )
    north = board_position(0, mid)
    west = board_position(mid, 0)
    south = board_position(core_size - 1, mid)
    east = board_position(mid, core_size - 1)
    boundary = tuple(
        position
        for position in range(board_area)
        if (
            position < board_size
            or position >= board_area - board_size
            or position % board_size == 0
            or position % board_size == board_size - 1
        )
    )

    requested = set(pulses)
    maximum_pulse = max(pulses)
    target = (1, 0, 0, 1, 1, 1)
    free_core_positions = (
        tuple(
            (row, column)
            for row in range(core_size)
            for column in range(row, core_size)
        )
        if symmetric
        else tuple(
            (row, column)
            for row in range(core_size)
            for column in range(core_size)
        )
    )
    total = 4 ** len(free_core_positions)
    solutions: dict[int, int] = {pulse: 0 for pulse in pulses}
    best: dict[int, tuple[int, tuple[int, ...], tuple[int, ...]]] = {}
    first_solution: dict[int, tuple[tuple[int, ...], tuple[int, ...]]] = {}
    boundary_reached = False

    for index, free_values in enumerate(
        itertools.product(range(4), repeat=len(free_core_positions))
    ):
        core_list = [0] * (core_size * core_size)
        for (row, column), value in zip(
            free_core_positions, free_values
        ):
            core_list[row * core_size + column] = value
            if symmetric:
                core_list[column * core_size + row] = value
        core = tuple(core_list)
        initial = [0] * board_area
        for position, value in zip(core_positions, core):
            initial[position] = value
        north_state = initial.copy()
        west_state = initial.copy()
        both_state = initial.copy()
        north_odometer = [0] * board_area
        west_odometer = [0] * board_area
        both_odometer = [0] * board_area

        for pulse in range(1, maximum_pulse + 1):
            add_and_stabilize_in_place(
                north_state, north_odometer, board_size, (north,)
            )
            add_and_stabilize_in_place(
                west_state, west_odometer, board_size, (west,)
            )
            add_and_stabilize_in_place(
                both_state,
                both_odometer,
                board_size,
                (north, west),
            )
            if pulse not in requested:
                continue
            counts = (
                north_odometer[south],
                north_odometer[east],
                west_odometer[south],
                west_odometer[east],
                both_odometer[south],
                both_odometer[east],
            )
            parities = tuple(value & 1 for value in counts)
            mismatches = sum(
                got != want for got, want in zip(parities, target)
            )
            activity = sum(counts)
            rank = mismatches * 1_000_000 + activity
            if pulse not in best or rank < best[pulse][0]:
                best[pulse] = (rank, core, counts)
            if mismatches == 0:
                solutions[pulse] += 1
                first_solution.setdefault(pulse, (core, counts))

        if any(
            north_odometer[position]
            or west_odometer[position]
            or both_odometer[position]
            for position in boundary
        ):
            boundary_reached = True
        if index and index % 50_000 == 0:
            print(f"checked={index}/{total}", flush=True)

    if boundary_reached:
        raise AssertionError(
            "some avalanche reached the padded boundary; increase padding"
        )
    print(
        f"EXHAUSTED EMBEDDED core={core_size} backgrounds={total} "
        f"padding={padding} symmetric={symmetric}",
        flush=True,
    )
    for pulse in pulses:
        rank, best_core, best_counts = best[pulse]
        print(
            f"pulse={pulse} solutions={solutions[pulse]} "
            f"best_mismatches={rank // 1_000_000} "
            f"best_counts={best_counts}",
            flush=True,
        )
        if pulse in first_solution:
            core, counts = first_solution[pulse]
            metrics, runs = independently_verify_embedded(
                core, core_size, padding, pulse
            )
            if metrics.mismatches:
                raise AssertionError("reported solution failed verification")
            print("FIRST EMBEDDED SOLUTION", flush=True)
            print(
                np.array(core, dtype=np.int8).reshape(
                    (core_size, core_size)
                ),
                flush=True,
            )
            print(metrics, flush=True)
            for name, odometer in runs.items():
                print(name, odometer, sep="\n", flush=True)
        else:
            print(
                "best core",
                np.array(best_core, dtype=np.int8).reshape(
                    (core_size, core_size)
                ),
                sep="\n",
                flush=True,
            )


def random_search_embedded(
    core_size: int,
    pulses: tuple[int, ...],
    padding: int,
    samples: int,
    seed: int,
    symmetric: bool,
    port_inset: int,
) -> None:
    """Randomly sample finite-support cores in a quiescent zero lattice."""
    if core_size < 3:
        raise ValueError("the four ports require core_size >= 3")
    rng = random.Random(seed)
    board_size = core_size + 2 * padding
    board_area = board_size * board_size
    mid = core_size // 2

    def board_position(core_row: int, core_column: int) -> int:
        return (
            (padding + core_row) * board_size
            + padding
            + core_column
        )

    core_positions = tuple(
        board_position(row, column)
        for row in range(core_size)
        for column in range(core_size)
    )
    north = board_position(port_inset, mid)
    west = board_position(mid, port_inset)
    south = board_position(core_size - 1 - port_inset, mid)
    east = board_position(mid, core_size - 1 - port_inset)
    boundary = tuple(
        position
        for position in range(board_area)
        if (
            position < board_size
            or position >= board_area - board_size
            or position % board_size == 0
            or position % board_size == board_size - 1
        )
    )
    requested = set(pulses)
    maximum_pulse = max(pulses)
    target = (1, 0, 0, 1, 1, 1)
    best: dict[int, tuple[int, tuple[int, ...], tuple[int, ...]]] = {}

    for index in range(samples):
        core_array = np.array(
            rng.choices(
                (0, 1, 2, 3),
                weights=(2, 1, 3, 10),
                k=core_size * core_size,
            ),
            dtype=np.int8,
        ).reshape((core_size, core_size))
        if symmetric:
            core_array = np.triu(core_array) + np.triu(
                core_array, 1
            ).T
        core = tuple(int(value) for value in core_array.flat)
        initial = [0] * board_area
        for position, value in zip(core_positions, core):
            initial[position] = value
        north_state = initial.copy()
        west_state = initial.copy()
        both_state = initial.copy()
        north_odometer = [0] * board_area
        west_odometer = [0] * board_area
        both_odometer = [0] * board_area

        for pulse in range(1, maximum_pulse + 1):
            add_and_stabilize_in_place(
                north_state, north_odometer, board_size, (north,)
            )
            add_and_stabilize_in_place(
                west_state, west_odometer, board_size, (west,)
            )
            add_and_stabilize_in_place(
                both_state,
                both_odometer,
                board_size,
                (north, west),
            )
            if pulse not in requested:
                continue
            counts = (
                north_odometer[south],
                north_odometer[east],
                west_odometer[south],
                west_odometer[east],
                both_odometer[south],
                both_odometer[east],
            )
            parities = tuple(value & 1 for value in counts)
            mismatches = sum(
                got != want for got, want in zip(parities, target)
            )
            rank = mismatches * 1_000_000 + sum(counts)
            if pulse not in best or rank < best[pulse][0]:
                best[pulse] = (rank, core, counts)
            if mismatches == 0:
                if any(
                    north_odometer[position]
                    or west_odometer[position]
                    or both_odometer[position]
                    for position in boundary
                ):
                    continue
                checked, runs = independently_verify_embedded(
                    core,
                    core_size,
                    padding * 2,
                    pulse,
                    port_inset,
                )
                if checked.mismatches:
                    raise AssertionError(
                        "embedded random candidate failed verification"
                    )
                print(
                    f"EMBEDDED PARITY CROSSING FOUND sample={index} "
                    f"pulse={pulse}",
                    flush=True,
                )
                print(core_array, flush=True)
                print(checked, flush=True)
                for name, odometer in runs.items():
                    print(name, odometer, sep="\n", flush=True)
                return
        if index and index % 50_000 == 0:
            summary = {
                pulse: rank // 1_000_000
                for pulse, (rank, _, _) in best.items()
            }
            print(
                f"checked={index}/{samples} best_mismatches={summary}",
                flush=True,
            )

    print(
        f"no embedded candidate in {samples} random cores", flush=True
    )
    for pulse in pulses:
        rank, core, counts = best[pulse]
        print(
            f"pulse={pulse} best_mismatches={rank // 1_000_000} "
            f"best_counts={counts}",
            flush=True,
        )
        print(
            np.array(core, dtype=np.int8).reshape(
                (core_size, core_size)
            ),
            flush=True,
        )


def search_embedded(
    core_size: int,
    pulse: int,
    padding: int,
    population_size: int,
    generations: int,
    seed: int,
    symmetric: bool,
    port_inset: int,
) -> None:
    """Genetic search over finite-support cores in a quiescent zero lattice."""
    if core_size < 3:
        raise ValueError("the four ports require core_size >= 3")
    rng = random.Random(seed)
    board_size = core_size + 2 * padding
    mid = core_size // 2
    ports = Ports(
        (padding + port_inset, padding + mid),
        (padding + mid, padding + port_inset),
        (
            padding + core_size - 1 - port_inset,
            padding + mid,
        ),
        (
            padding + mid,
            padding + core_size - 1 - port_inset,
        ),
    )

    def fresh() -> np.ndarray:
        candidate = np.array(
            rng.choices(
                (0, 1, 2, 3),
                weights=(2, 1, 3, 10),
                k=core_size * core_size,
            ),
            dtype=np.int8,
        ).reshape((core_size, core_size))
        return (
            np.triu(candidate) + np.triu(candidate, 1).T
            if symmetric
            else candidate
        )

    def embedded_evaluate(
        core: np.ndarray,
    ) -> tuple[int, ParityMetrics, dict[str, np.ndarray]]:
        board = np.zeros((board_size, board_size), dtype=np.int8)
        board[
            padding : padding + core_size,
            padding : padding + core_size,
        ] = core
        _, metrics, runs = evaluate(board, ports, pulse)
        canonical_counts = (1, 2, 2, 1, 3, 3)
        count_distance = sum(
            abs(got - want)
            for got, want in zip(metrics.counts, canonical_counts)
        )
        score = count_distance * 1_000_000 + metrics.activity
        boundary_activity = sum(
            int(odometer[0, :].sum())
            + int(odometer[-1, :].sum())
            + int(odometer[1:-1, 0].sum())
            + int(odometer[1:-1, -1].sum())
            for odometer in runs.values()
        )
        return score + boundary_activity * 10_000_000, metrics, runs

    population = [fresh() for _ in range(population_size)]
    best_score = 10**18
    for generation in range(generations):
        ranked = []
        for candidate in population:
            score, metrics, runs = embedded_evaluate(candidate)
            ranked.append((score, candidate, metrics, runs))
        ranked.sort(key=lambda item: item[0])
        score, candidate, metrics, runs = ranked[0]

        if score < best_score:
            best_score = score
            print(
                f"generation={generation} score={score} "
                f"metrics={metrics}",
                flush=True,
            )
            print(candidate, flush=True)

        if metrics.mismatches == 0 and score < 10_000_000:
            core = tuple(int(value) for value in candidate.flat)
            checked, checked_runs = independently_verify_embedded(
                core,
                core_size,
                padding * 2,
                pulse,
                port_inset,
            )
            if checked.mismatches:
                raise AssertionError(
                    "embedded GA candidate failed verification"
                )
            print("EMBEDDED PARITY CROSSING FOUND", flush=True)
            print(candidate, flush=True)
            print(checked, flush=True)
            for name, odometer in checked_runs.items():
                print(name, odometer, sep="\n", flush=True)
            return

        elite_count = max(4, population_size // 10)
        elites = [item[1] for item in ranked[:elite_count]]
        next_population = [candidate.copy() for candidate in elites]
        mutation_rate = max(
            1.0 / (core_size * core_size),
            0.1 * (1 - generation / generations),
        )
        while len(next_population) < population_size:
            parent_a = rng.choice(elites)
            parent_b = rng.choice(elites)
            child = crossover(parent_a, parent_b, rng, symmetric)
            child = mutate(child, rng, mutation_rate, symmetric)
            next_population.append(child)
        population = next_population

    print(
        f"no embedded candidate found; best_score={best_score}",
        flush=True,
    )


def exhaustive(n: int, pulses: tuple[int, ...]) -> None:
    if n < 3:
        raise ValueError("the four ports require n >= 3")

    mid = n // 2
    north = mid
    west = mid * n
    south = (n - 1) * n + mid
    east = mid * n + n - 1
    total = 4 ** (n * n)
    target = (1, 0, 0, 1, 1, 1)

    solutions: dict[int, int] = {pulse: 0 for pulse in pulses}
    best: dict[int, tuple[int, tuple[int, ...], tuple[int, ...]]] = {}
    first_solution: dict[int, tuple[tuple[int, ...], tuple[int, ...]]] = {}

    for index, values in enumerate(
        itertools.product(range(4), repeat=n * n)
    ):
        base = tuple(values)
        for pulse in pulses:
            counts = flat_counts(
                base, n, pulse, north, west, south, east
            )
            parities = tuple(value & 1 for value in counts)
            mismatches = sum(
                got != want for got, want in zip(parities, target)
            )
            activity = sum(counts)
            rank = mismatches * 1_000_000 + activity
            if pulse not in best or rank < best[pulse][0]:
                best[pulse] = (rank, base, counts)
            if mismatches == 0:
                solutions[pulse] += 1
                first_solution.setdefault(pulse, (base, counts))
        if index and index % 50_000 == 0:
            print(f"checked={index}/{total}", flush=True)

    print(f"EXHAUSTED size={n} backgrounds={total}", flush=True)
    for pulse in pulses:
        rank, best_base, best_counts = best[pulse]
        print(
            f"pulse={pulse} solutions={solutions[pulse]} "
            f"best_mismatches={rank // 1_000_000} "
            f"best_counts={best_counts}",
            flush=True,
        )
        if pulse in first_solution:
            base, counts = first_solution[pulse]
            metrics, runs = independently_verify(base, n, pulse)
            if metrics.mismatches:
                raise AssertionError("reported solution failed verification")
            print("FIRST SOLUTION", flush=True)
            print(np.array(base, dtype=np.int8).reshape((n, n)), flush=True)
            print(metrics, flush=True)
            for name, odometer in runs.items():
                print(name, odometer, sep="\n", flush=True)
        else:
            print(
                "best background",
                np.array(best_base, dtype=np.int8).reshape((n, n)),
                sep="\n",
                flush=True,
            )


def search(
    n: int,
    pulse: int,
    population_size: int,
    generations: int,
    seed: int,
    symmetric: bool,
) -> None:
    if n < 3:
        raise ValueError("the four ports require n >= 3")
    rng = random.Random(seed)
    mid = n // 2
    ports = Ports((0, mid), (mid, 0), (n - 1, mid), (mid, n - 1))

    def fresh() -> np.ndarray:
        candidate = np.array(
            rng.choices((0, 1, 2, 3), weights=(3, 2, 3, 7), k=n * n),
            dtype=np.int8,
        ).reshape((n, n))
        if symmetric:
            candidate = np.triu(candidate) + np.triu(candidate, 1).T
        return candidate

    population = [fresh() for _ in range(population_size)]
    best_score = 10**18
    for generation in range(generations):
        ranked = []
        for candidate in population:
            score, metrics, runs = evaluate(candidate, ports, pulse)
            ranked.append((score, candidate, metrics, runs))
        ranked.sort(key=lambda item: item[0])
        score, candidate, metrics, runs = ranked[0]

        if score < best_score:
            best_score = score
            print(
                f"generation={generation} score={score} metrics={metrics}",
                flush=True,
            )
            print(candidate, flush=True)

        if metrics.mismatches == 0:
            base = tuple(int(value) for value in candidate.flat)
            checked, checked_runs = independently_verify(base, n, pulse)
            if checked.mismatches:
                raise AssertionError("GA candidate failed verification")
            print("PARITY CROSSING FOUND", flush=True)
            print(candidate, flush=True)
            print(checked, flush=True)
            for name, odometer in checked_runs.items():
                print(name, odometer, sep="\n", flush=True)
            return

        elite_count = max(4, population_size // 10)
        elites = [item[1] for item in ranked[:elite_count]]
        next_population = [candidate.copy() for candidate in elites]
        mutation_rate = max(
            1.0 / (n * n),
            0.1 * (1 - generation / generations),
        )
        while len(next_population) < population_size:
            parent_a = rng.choice(elites)
            parent_b = rng.choice(elites)
            child = crossover(parent_a, parent_b, rng, symmetric)
            child = mutate(child, rng, mutation_rate, symmetric)
            next_population.append(child)
        population = next_population

    print(f"no candidate found; best_score={best_score}", flush=True)


def random_search(
    n: int,
    pulses: tuple[int, ...],
    samples: int,
    seed: int,
) -> None:
    """Unbiased-by-fitness random search, useful for the rugged parity objective."""
    if n < 3:
        raise ValueError("the four ports require n >= 3")
    rng = random.Random(seed)
    mid = n // 2
    north = mid
    west = mid * n
    south = (n - 1) * n + mid
    east = mid * n + n - 1
    target = (1, 0, 0, 1, 1, 1)
    best: dict[int, tuple[int, tuple[int, ...], tuple[int, ...]]] = {}

    for index in range(samples):
        # Threshold-ready cells are useful for carrying a signal across a board.
        base = tuple(
            rng.choices((0, 1, 2, 3), weights=(3, 2, 3, 7), k=n * n)
        )
        for pulse in pulses:
            counts = flat_counts(
                base, n, pulse, north, west, south, east
            )
            parities = tuple(value & 1 for value in counts)
            mismatches = sum(
                got != want for got, want in zip(parities, target)
            )
            activity = sum(counts)
            rank = mismatches * 1_000_000 + activity
            if pulse not in best or rank < best[pulse][0]:
                best[pulse] = (rank, base, counts)
            if mismatches == 0:
                checked, runs = independently_verify(base, n, pulse)
                if checked.mismatches:
                    raise AssertionError(
                        "random candidate failed verification"
                    )
                print(
                    f"PARITY CROSSING FOUND sample={index} pulse={pulse}",
                    flush=True,
                )
                print(
                    np.array(base, dtype=np.int8).reshape((n, n)),
                    flush=True,
                )
                print(checked, flush=True)
                for name, odometer in runs.items():
                    print(name, odometer, sep="\n", flush=True)
                return
        if index and index % 50_000 == 0:
            summary = {
                pulse: rank // 1_000_000
                for pulse, (rank, _, _) in best.items()
            }
            print(
                f"checked={index}/{samples} best_mismatches={summary}",
                flush=True,
            )

    print(f"no candidate in {samples} random backgrounds", flush=True)
    for pulse in pulses:
        rank, base, counts = best[pulse]
        print(
            f"pulse={pulse} best_mismatches={rank // 1_000_000} "
            f"best_counts={counts}",
            flush=True,
        )
        print(
            np.array(base, dtype=np.int8).reshape((n, n)),
            flush=True,
        )


def parse_pulses(text: str) -> tuple[int, ...]:
    pulses = tuple(
        int(part)
        for part in text.split(",")
        if part.strip()
    )
    if not pulses or any(pulse <= 0 for pulse in pulses):
        raise argparse.ArgumentTypeError(
            "pulses must be comma-separated positive integers"
        )
    return pulses


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=3)
    parser.add_argument("--pulse", type=int, default=8)
    parser.add_argument("--pulses", type=parse_pulses, default=(1, 2, 3, 4, 5, 6, 7, 8))
    parser.add_argument("--population", type=int, default=800)
    parser.add_argument("--generations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--symmetric", action="store_true")
    parser.add_argument("--exhaustive", action="store_true")
    parser.add_argument("--embedded-exhaustive", action="store_true")
    parser.add_argument("--padding", type=int, default=3)
    parser.add_argument("--random-samples", type=int, default=0)
    parser.add_argument("--embedded-random-samples", type=int, default=0)
    parser.add_argument("--embedded-ga", action="store_true")
    parser.add_argument("--port-inset", type=int, default=0)
    args = parser.parse_args()

    modes = sum(
        (
            bool(args.exhaustive),
            bool(args.embedded_exhaustive),
            bool(args.random_samples),
            bool(args.embedded_random_samples),
            bool(args.embedded_ga),
        )
    )
    if modes > 1:
        parser.error("choose only one exhaustive mode")
    if args.embedded_exhaustive:
        exhaustive_embedded(
            args.size,
            args.pulses,
            args.padding,
            args.symmetric,
        )
    elif args.exhaustive:
        exhaustive(args.size, args.pulses)
    elif args.embedded_random_samples:
        random_search_embedded(
            args.size,
            args.pulses,
            args.padding,
            args.embedded_random_samples,
            args.seed,
            args.symmetric,
            args.port_inset,
        )
    elif args.embedded_ga:
        search_embedded(
            args.size,
            args.pulse,
            args.padding,
            args.population,
            args.generations,
            args.seed,
            args.symmetric,
            args.port_inset,
        )
    elif args.random_samples:
        random_search(
            args.size,
            args.pulses,
            args.random_samples,
            args.seed,
        )
    else:
        search(
            args.size,
            args.pulse,
            args.population,
            args.generations,
            args.seed,
            args.symmetric,
        )


if __name__ == "__main__":
    main()
