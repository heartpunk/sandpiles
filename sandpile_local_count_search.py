#!/usr/bin/env python3
"""Exhaust a Hamming ball around a near count-coded crossing."""

from __future__ import annotations

import argparse
import itertools

import numpy as np

from sandpile_crossing_search import Ports, stabilize


SEED = np.array(
    [
        [1, 3, 3, 0],
        [2, 3, 3, 1],
        [3, 3, 0, 3],
        [3, 3, 3, 2],
    ],
    dtype=np.int8,
)


def response(base: np.ndarray, pulse: int) -> tuple[int, int, int, int]:
    n = base.shape[0]
    mid = n // 2
    ports = Ports((0, mid), (mid, 0), (n - 1, mid), (mid, n - 1))
    north = stabilize(base, ((ports.north, pulse),))
    west = stabilize(base, ((ports.west, pulse),))
    return (
        int(north[ports.south]),
        int(west[ports.south]),
        int(north[ports.east]),
        int(west[ports.east]),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pulse", type=int, default=8)
    parser.add_argument("--radius", type=int, default=4)
    args = parser.parse_args()

    seed_flat = SEED.ravel()
    checked = 0
    best_margin = -10**9
    best_sum = -10**9
    best: tuple[np.ndarray, tuple[int, int, int, int]] | None = None

    for distance in range(args.radius + 1):
        for positions in itertools.combinations(range(seed_flat.size), distance):
            alternatives = [
                tuple(value for value in range(4) if value != int(seed_flat[p]))
                for p in positions
            ]
            for replacements in itertools.product(*alternatives):
                candidate = seed_flat.copy()
                for p, value in zip(positions, replacements):
                    candidate[p] = value
                candidate = candidate.reshape(SEED.shape)
                r = response(candidate, args.pulse)
                margins = (r[0] - r[1], r[3] - r[2])
                minimum = min(margins)
                total = sum(margins)
                checked += 1
                if (minimum, total) > (best_margin, best_sum):
                    best_margin, best_sum = minimum, total
                    best = (candidate.copy(), r)
                if minimum >= 1:
                    print(
                        f"FOUND distance={distance} checked={checked} "
                        f"response={r} margins={margins}",
                        flush=True,
                    )
                    print(candidate, flush=True)
                    return
        print(
            f"completed_radius={distance} checked={checked} "
            f"best_margin={best_margin} best_sum={best_sum}",
            flush=True,
        )

    assert best is not None
    print(
        f"NO CANDIDATE checked={checked} best_margin={best_margin} "
        f"best_sum={best_sum} response={best[1]}",
        flush=True,
    )
    print(best[0], flush=True)


if __name__ == "__main__":
    main()
