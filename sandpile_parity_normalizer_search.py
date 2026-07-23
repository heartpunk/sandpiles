#!/usr/bin/env python3
"""Search for a parity/amplitude normalizer with a quiescent one-cell output.

The source is the midpoint of the left edge of an n x n finite-support core.
The designated output q has a receiver r immediately to its east.  The
receiver and its other three neighbors are fixed at height zero.  A valid
exact normalizer must, for k=0,1,2,3 grains at the source,

* topple q exactly k times;
* never topple r or its three buffer neighbors; and
* leave r at height k, so the only flux into r came from q.

The parity-only relaxation requires q's odometer parity to be k mod 2 while
retaining the isolated receiver.  Candidates are independently replayed with
the flat stabilizer from sandpile_parity_wire_search.py.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import random

import numpy as np

from sandpile_crossing_search import stabilize
from sandpile_parity_wire_search import (
    embedded_board,
    final_state_from_odometer,
    flat_runs,
)


Coord = tuple[int, int]


@dataclass(frozen=True)
class NormalizerMetrics:
    output_counts: tuple[int, int, int]
    output_parities: tuple[int, int, int]
    receiver_final: tuple[int, int, int]
    parity_mismatches: int
    exact_error: int
    receiver_error: int
    forbidden_topplings: int
    artificial_boundary_topplings: int
    activity: int


def geometry(
    n: int,
    output_column: int,
) -> tuple[Coord, Coord, Coord, frozenset[Coord]]:
    middle = n // 2
    source = (middle, 0)
    output = (middle, output_column)
    receiver = (middle, output_column + 1)
    forbidden = frozenset(
        {
            receiver,
            (middle - 1, output_column + 1),
            (middle + 1, output_column + 1),
            (middle, output_column + 2),
        }
    )
    return source, output, receiver, forbidden


def apply_fixed_zeros(
    core: tuple[int, ...],
    n: int,
    forbidden: frozenset[Coord],
) -> tuple[int, ...]:
    result = list(core)
    for row, column in forbidden:
        result[row * n + column] = 0
    return tuple(result)


def evaluate(
    core: tuple[int, ...],
    n: int,
    padding: int,
    output_column: int,
) -> tuple[int, NormalizerMetrics]:
    source, output, receiver, forbidden = geometry(n, output_column)
    board = embedded_board(core, n, n, padding)
    source_global = (padding + source[0], padding + source[1])
    output_global = (padding + output[0], padding + output[1])
    receiver_global = (padding + receiver[0], padding + receiver[1])
    forbidden_global = tuple(
        (padding + row, padding + column)
        for row, column in forbidden
    )

    output_counts = []
    receiver_final = []
    forbidden_topplings = 0
    boundary_topplings = 0
    activity = 0
    for amount in (1, 2, 3):
        odometer = stabilize(board, ((source_global, amount),))
        final = final_state_from_odometer(
            board,
            source_global,
            amount,
            odometer,
        )
        output_counts.append(int(odometer[output_global]))
        receiver_final.append(int(final[receiver_global]))
        forbidden_topplings += sum(
            int(odometer[position])
            for position in forbidden_global
        )
        boundary_topplings += (
            int(odometer[0, :].sum())
            + int(odometer[-1, :].sum())
            + int(odometer[1:-1, 0].sum())
            + int(odometer[1:-1, -1].sum())
        )
        activity += int(odometer.sum())

    output_tuple = tuple(output_counts)
    receiver_tuple = tuple(receiver_final)
    parities = tuple(count & 1 for count in output_tuple)
    parity_mismatches = sum(
        got != want for got, want in zip(parities, (1, 0, 1))
    )
    exact_error = sum(
        abs(got - want)
        for got, want in zip(output_tuple, (1, 2, 3))
    )
    receiver_error = sum(
        abs(got - want)
        for got, want in zip(receiver_tuple, (1, 2, 3))
    )
    metrics = NormalizerMetrics(
        output_counts=output_tuple,
        output_parities=parities,
        receiver_final=receiver_tuple,
        parity_mismatches=parity_mismatches,
        exact_error=exact_error,
        receiver_error=receiver_error,
        forbidden_topplings=forbidden_topplings,
        artificial_boundary_topplings=boundary_topplings,
        activity=activity,
    )
    score = (
        boundary_topplings * 1_000_000_000
        + parity_mismatches * 10_000_000
        + forbidden_topplings * 1_000_000
        + receiver_error * 100_000
        + exact_error * 10_000
        + activity
    )
    return score, metrics


def independently_verify(
    core: tuple[int, ...],
    n: int,
    padding: int,
    output_column: int,
) -> NormalizerMetrics:
    score, metrics = evaluate(core, n, padding, output_column)
    del score
    flat = flat_runs(core, n, n, padding)
    board = embedded_board(core, n, n, padding)
    source, _, _, _ = geometry(n, output_column)
    source_global = (padding + source[0], padding + source[1])
    for amount, expected_flat in zip((1, 2, 3), flat):
        actual = stabilize(board, ((source_global, amount),))
        if tuple(int(value) for value in actual.flat) != expected_flat:
            raise AssertionError("independent stabilizers disagree")
    return metrics


def mutate(
    core: tuple[int, ...],
    n: int,
    forbidden: frozenset[Coord],
    rng: random.Random,
    rate: float,
) -> tuple[int, ...]:
    result = list(core)
    for position, value in enumerate(result):
        coord = divmod(position, n)
        if coord in forbidden:
            result[position] = 0
        elif rng.random() < rate:
            replacement = rng.randrange(3)
            if replacement >= value:
                replacement += 1
            result[position] = replacement
    return tuple(result)


def crossover(
    left: tuple[int, ...],
    right: tuple[int, ...],
    n: int,
    forbidden: frozenset[Coord],
    rng: random.Random,
) -> tuple[int, ...]:
    return apply_fixed_zeros(
        tuple(
            a if rng.random() < 0.5 else b
            for a, b in zip(left, right)
        ),
        n,
        forbidden,
    )


def search(
    n: int,
    padding: int,
    output_column: int,
    population_size: int,
    generations: int,
    seed: int,
) -> None:
    rng = random.Random(seed)
    _, _, _, forbidden = geometry(n, output_column)

    all_three = apply_fixed_zeros((3,) * (n * n), n, forbidden)

    def fresh() -> tuple[int, ...]:
        return apply_fixed_zeros(
            tuple(
                rng.choices(
                    (0, 1, 2, 3),
                    weights=(2, 1, 2, 9),
                    k=n * n,
                )
            ),
            n,
            forbidden,
        )

    population = [all_three]
    population.extend(fresh() for _ in range(population_size - 1))
    best: tuple[int, tuple[int, ...], NormalizerMetrics] | None = None

    for generation in range(generations):
        ranked = []
        for core in population:
            score, metrics = evaluate(
                core,
                n,
                padding,
                output_column,
            )
            ranked.append((score, core, metrics))
        ranked.sort(key=lambda item: item[0])
        candidate = ranked[0]
        if best is None or candidate[0] < best[0]:
            best = candidate
            print(
                f"generation={generation} score={candidate[0]} "
                f"metrics={candidate[2]}",
                flush=True,
            )
            print(
                np.asarray(candidate[1], dtype=np.int8).reshape((n, n)),
                flush=True,
            )

        _, core, metrics = candidate
        if (
            metrics.parity_mismatches == 0
            and metrics.forbidden_topplings == 0
            and metrics.receiver_error == 0
            and metrics.artificial_boundary_topplings == 0
        ):
            checked = independently_verify(
                core,
                n,
                padding,
                output_column,
            )
            print("ISOLATED PARITY NORMALIZER FOUND", flush=True)
            print(np.asarray(core, dtype=np.int8).reshape((n, n)), flush=True)
            print(checked, flush=True)
            return

        elite_count = max(8, population_size // 8)
        elites = [item[1] for item in ranked[:elite_count]]
        next_population = elites.copy()
        mutation_rate = max(
            1.0 / (n * n),
            0.15 * (1 - generation / generations),
        )
        while len(next_population) < population_size:
            child = crossover(
                rng.choice(elites),
                rng.choice(elites),
                n,
                forbidden,
                rng,
            )
            next_population.append(
                mutate(
                    child,
                    n,
                    forbidden,
                    rng,
                    mutation_rate,
                )
            )
        population = next_population

    assert best is not None
    print("NO NORMALIZER FOUND", flush=True)
    print(f"best_score={best[0]} metrics={best[2]}", flush=True)
    print(np.asarray(best[1], dtype=np.int8).reshape((n, n)), flush=True)


def scan_clocked_state_interface(
    padding: int,
    maximum_clock: int,
) -> None:
    """Try to read the exact-k reflected state of the 5x5 strip with a clock."""
    n = 5
    core = (3,) * 25
    board = embedded_board(core, n, n, padding)
    source = (padding + 2, padding)
    initial_odometers = []
    post_input_states = []
    for amount in range(4):
        odometer = (
            np.zeros_like(board, dtype=np.int32)
            if amount == 0
            else stabilize(board, ((source, amount),))
        )
        initial_odometers.append(odometer)
        post_input_states.append(
            final_state_from_odometer(
                board,
                source,
                amount,
                odometer,
            )
        )

    halo = tuple(
        (row, column)
        for row in range(padding - 1, padding + n + 1)
        for column in range(padding - 1, padding + n + 1)
    )
    target = (0, 1, 0, 1)
    hits = []
    for clock_position in halo:
        for clock_amount in range(1, maximum_clock + 1):
            clock_odometers = tuple(
                stabilize(state, ((clock_position, clock_amount),))
                for state in post_input_states
            )
            if any(
                int(odometer[0, :].sum())
                + int(odometer[-1, :].sum())
                + int(odometer[1:-1, 0].sum())
                + int(odometer[1:-1, -1].sum())
                for odometer in clock_odometers
            ):
                continue
            for output in halo:
                incremental_counts = tuple(
                    int(odometer[output])
                    for odometer in clock_odometers
                )
                total_counts = tuple(
                    int(before[output] + after[output])
                    for before, after in zip(
                        initial_odometers,
                        clock_odometers,
                    )
                )
                incremental_parity = tuple(
                    count & 1 for count in incremental_counts
                )
                total_parity = tuple(
                    count & 1 for count in total_counts
                )
                if incremental_parity == target:
                    hits.append(
                        (
                            sum(incremental_counts),
                            "incremental",
                            clock_position,
                            clock_amount,
                            output,
                            incremental_counts,
                        )
                    )
                if total_parity == target:
                    hits.append(
                        (
                            sum(total_counts),
                            "total",
                            clock_position,
                            clock_amount,
                            output,
                            total_counts,
                        )
                    )
    hits.sort()
    outside_hits = [
        hit
        for hit in hits
        if (
            hit[4][0] < padding
            or hit[4][0] >= padding + n
            or hit[4][1] < padding
            or hit[4][1] >= padding + n
        )
    ]
    core_boundary_hits = [
        hit
        for hit in hits
        if (
            hit[4][0] in (padding, padding + n - 1)
            or hit[4][1] in (padding, padding + n - 1)
        )
        and hit not in outside_hits
    ]
    print(
        f"CLOCK SCAN: positions={len(halo)} clock_amounts=1..{maximum_clock} "
        f"parity_hits={len(hits)}",
        flush=True,
    )
    def print_hits(label: str, selected: list[tuple]) -> None:
        print(f"{label}={len(selected)}", flush=True)
        for hit in selected[:25]:
            _, mode, clock_position, clock_amount, output, counts = hit
            print(
                f"mode={mode} clock_local="
                f"({clock_position[0]-padding},{clock_position[1]-padding}) "
                f"clock_amount={clock_amount} output_local="
                f"({output[0]-padding},{output[1]-padding}) counts={counts}",
                flush=True,
            )

    print_hits("outside-core one-cell-halo hits", outside_hits)
    print_hits("core-boundary hits", core_boundary_hits)
    print_hits(
        "outside-core TOTAL-odometer hits",
        [hit for hit in outside_hits if hit[1] == "total"],
    )
    print_hits(
        "core-boundary TOTAL-odometer hits",
        [hit for hit in core_boundary_hits if hit[1] == "total"],
    )
    unique_total_boundary = sorted(
        {
            (
                hit[4][0] - padding,
                hit[4][1] - padding,
                hit[5],
            )
            for hit in core_boundary_hits
            if hit[1] == "total"
        }
    )
    print(
        f"unique core-boundary TOTAL outputs={unique_total_boundary}",
        flush=True,
    )
    print_hits("all hits (best activity)", hits)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=7)
    parser.add_argument("--output-column", type=int, default=2)
    parser.add_argument("--padding", type=int, default=5)
    parser.add_argument("--population", type=int, default=1000)
    parser.add_argument("--generations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--clock-scan", action="store_true")
    parser.add_argument("--maximum-clock", type=int, default=16)
    args = parser.parse_args()
    if args.size < 5:
        parser.error("--size must be at least 5")
    if not (1 <= args.output_column <= args.size - 3):
        parser.error(
            "--output-column must leave room for receiver and buffer"
        )
    if args.clock_scan:
        scan_clocked_state_interface(
            args.padding,
            args.maximum_clock,
        )
    else:
        search(
            args.size,
            args.padding,
            args.output_column,
            args.population,
            args.generations,
            args.seed,
        )


if __name__ == "__main__":
    main()
