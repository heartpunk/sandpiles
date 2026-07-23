#!/usr/bin/env python3
"""Regression tests for the one-grain parity ring bounds.

The important checks are symbolic in the elementary sense: the Laplacian
inequalities are checked pointwise on the maximal all-3 square, which covers
all 4^(n^2) stable backgrounds at once by monotonicity.  We additionally run
an exhaustive 3x3 test and randomized larger stabilizations as adversarial
checks against indexing mistakes.
"""

from __future__ import annotations

import argparse
import itertools
import random

import numpy as np

from sandpile_crossing_search import stabilize


Coord = tuple[int, int]


def depth(row: int, column: int, n: int) -> int:
    return min(row, column, n - 1 - row, n - 1 - column)


def supersolution(n: int, input_depth: int, padding: int = 2) -> np.ndarray:
    if input_depth not in (0, 1):
        raise ValueError("this test covers only depths zero and one")
    board = np.zeros((n + 2 * padding, n + 2 * padding), dtype=np.int16)
    for row in range(n):
        for column in range(n):
            value = (
                1
                if input_depth == 0
                else min(depth(row, column, n) + 1, 2)
            )
            board[padding + row, padding + column] = value
    return board


def positive_laplacian(values: np.ndarray) -> np.ndarray:
    result = 4 * values.copy()
    result[1:, :] -= values[:-1, :]
    result[:-1, :] -= values[1:, :]
    result[:, 1:] -= values[:, :-1]
    result[:, :-1] -= values[:, 1:]
    return result


def ring(n: int, input_depth: int, padding: int = 2) -> tuple[Coord, ...]:
    return tuple(
        (padding + row, padding + column)
        for row in range(n)
        for column in range(n)
        if depth(row, column, n) == input_depth
    )


def assert_symbolic_supersolution(n: int, input_depth: int) -> None:
    padding = 2
    values = supersolution(n, input_depth, padding)
    laplacian = positive_laplacian(values)
    core = (
        slice(padding, padding + n),
        slice(padding, padding + n),
    )
    core_laplacian = laplacian[core]
    assert np.all(core_laplacian >= 0)
    for position in ring(n, input_depth, padding):
        assert laplacian[position] >= 1

    maximal = np.zeros_like(values)
    maximal[core] = 3
    # One grain may be added at every site of the input ring at once.  This
    # dominates every smaller bundle, so it checks all bundles pointwise.
    for position in ring(n, input_depth, padding):
        maximal[position] += 1
    final = maximal - laplacian
    assert int(final.max()) <= 3
    assert int(final.min()) >= 0


def assert_boundary_amplitude_supersolution(n: int, amplitude: int) -> None:
    """Check v=q on Q against q grains on every boundary site."""
    padding = 2
    values = np.zeros((n + 2 * padding, n + 2 * padding), dtype=np.int16)
    core = (
        slice(padding, padding + n),
        slice(padding, padding + n),
    )
    values[core] = amplitude
    maximal = np.zeros_like(values)
    maximal[core] = 3
    for position in ring(n, 0, padding):
        maximal[position] += amplitude
    final = maximal - positive_laplacian(values)
    assert int(final.max()) <= 3
    assert int(final.min()) >= 0


def exhaustive_three_by_three() -> int:
    n = 3
    padding = 2
    north = (padding, padding + 1)
    west = (padding + 1, padding)
    bound = supersolution(n, 0, padding)
    checked = 0
    for flat in itertools.product(range(4), repeat=n * n):
        board = np.zeros((n + 2 * padding, n + 2 * padding), dtype=np.int8)
        board[
            padding : padding + n,
            padding : padding + n,
        ] = np.asarray(flat, dtype=np.int8).reshape((n, n))
        for additions in (
            ((north, 1),),
            ((west, 1),),
            ((north, 1), (west, 1)),
        ):
            odometer = stabilize(board, additions)
            assert np.all(odometer <= bound)
            checked += 1
    return checked


def randomized(trials: int, seed: int) -> int:
    rng = random.Random(seed)
    for _ in range(trials):
        input_depth = rng.randrange(2)
        minimum_size = 3 if input_depth == 0 else 5
        n = rng.randint(minimum_size, 35)
        padding = 3
        board = np.zeros((n + 2 * padding, n + 2 * padding), dtype=np.int8)
        board[
            padding : padding + n,
            padding : padding + n,
        ] = np.asarray(
            [rng.randrange(4) for _ in range(n * n)],
            dtype=np.int8,
        ).reshape((n, n))
        candidates = ring(n, input_depth, padding)
        bundle_size = rng.randint(1, min(8, len(candidates)))
        bundle = rng.sample(candidates, bundle_size)
        additions = tuple((position, 1) for position in bundle)
        odometer = stabilize(board, additions)
        bound = supersolution(n, input_depth, padding)
        assert np.all(odometer <= bound)
    return trials


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--random-trials", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260723)
    args = parser.parse_args()

    # These pointwise checks cover every stable background and every distinct
    # one-grain bundle for each tested size; there is no configuration loop.
    for n in range(3, 101):
        assert_symbolic_supersolution(n, 0)
        for amplitude in (1, 2, 3):
            assert_boundary_amplitude_supersolution(n, amplitude)
    for n in range(5, 101):
        assert_symbolic_supersolution(n, 1)

    exhaustive = exhaustive_three_by_three()
    random_count = randomized(args.random_trials, args.seed)
    print(
        "PASS: pointwise all-background proof checks for "
        "Q_3..Q_100; "
        f"{exhaustive:,} exhaustive 3x3 stabilizations; "
        f"{random_count:,} randomized larger stabilizations"
    )


if __name__ == "__main__":
    main()
