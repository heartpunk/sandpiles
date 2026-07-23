#!/usr/bin/env python3
"""Brute-force and randomized checks of the corner-rigidity lemma.

The mathematical proof is in ``sandpile_exact_linear_no_propagation.md``.
This program searches directly for a finite nonnegative integer field u
and a source s in supp(u) such that |Lu| <= 1 away from s, but u is not
the unit mass at s.
"""

from __future__ import annotations

import itertools
import random

import numpy as np


def laplacian_with_halo(u: np.ndarray) -> np.ndarray:
    """Return the Z^2 Laplacian, including the one-cell exterior halo."""
    padded = np.pad(u, 1)
    lap = 4 * padded.copy()
    lap[1:, :] -= padded[:-1, :]
    lap[:-1, :] -= padded[1:, :]
    lap[:, 1:] -= padded[:, :-1]
    lap[:, :-1] -= padded[:, 1:]
    return lap


def check_field(u: np.ndarray) -> None:
    """Raise if u is a counterexample for some exceptional source."""
    if not np.any(u):
        return
    lap = laplacian_with_halo(u)
    bad = set(map(tuple, np.argwhere(np.abs(lap) > 1)))
    support = {
        (int(row + 1), int(column + 1))
        for row, column in np.argwhere(u > 0)
    }
    possible_sources = support if not bad else support.intersection(bad)
    for source in possible_sources:
        if bad.issubset({source}):
            source_value = int(lap[source])
            is_unit_source = (
                len(support) == 1
                and int(u[source[0] - 1, source[1] - 1]) == 1
            )
            if not is_unit_source:
                raise AssertionError(
                    "counterexample found\n"
                    f"u=\n{u}\nLu (with halo)=\n{lap}\n"
                    f"source={source}, Lu(source)={source_value}"
                )


def exhaustive(shape: tuple[int, int], value_count: int) -> int:
    checked = 0
    area = shape[0] * shape[1]
    for values in itertools.product(range(value_count), repeat=area):
        check_field(np.array(values, dtype=np.int16).reshape(shape))
        checked += 1
    return checked


def randomized(
    trials: int,
    *,
    max_side: int,
    max_value: int,
    seed: int,
) -> int:
    rng = random.Random(seed)
    for _ in range(trials):
        rows = rng.randrange(1, max_side + 1)
        columns = rng.randrange(1, max_side + 1)
        u = np.zeros((rows, columns), dtype=np.int16)
        for row in range(rows):
            for column in range(columns):
                if rng.random() < 0.55:
                    u[row, column] = rng.randrange(max_value + 1)
        check_field(u)
    return trials


def main() -> None:
    total = 0
    # Rich height patterns in a compact box.
    total += exhaustive((3, 3), 4)  # 4^9 = 262,144 fields.
    # Every support shape in a larger box.
    total += exhaustive((4, 4), 2)  # 2^16 = 65,536 fields.
    # Long thin supports with higher heights.
    total += exhaustive((2, 4), 5)  # 5^8 = 390,625 fields.
    total += randomized(
        100_000,
        max_side=9,
        max_value=12,
        seed=0x5A17,
    )
    print(f"PASS: checked {total:,} finite fields; no counterexample")


if __name__ == "__main__":
    main()
