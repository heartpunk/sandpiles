#!/usr/bin/env python3
"""Search unequal input-packet sizes for a 2x2 full-alphabet crossover."""

from __future__ import annotations

import argparse

from sandpile_2x2_full_alphabet_search import C, D, stabilize


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", nargs=4, type=int, default=(1, 2, 2, 3))
    parser.add_argument("--minimum-pulse", type=int, default=150)
    parser.add_argument("--maximum-pulse", type=int, default=300)
    args = parser.parse_args()
    core = tuple(args.core)
    cache: dict[tuple[int, int], tuple[int, int]] = {}

    def result(a_grains: int, b_grains: int) -> tuple[int, int]:
        key = (a_grains, b_grains)
        if key not in cache:
            odometer = stabilize(core, a_grains, b_grains)
            cache[key] = odometer[C], odometer[D]
        return cache[key]

    best_errors = 33
    best = None
    for a_pulse in range(args.minimum_pulse, args.maximum_pulse + 1):
        for b_pulse in range(args.minimum_pulse, args.maximum_pulse + 1):
            table = tuple(
                tuple(
                    result(a * a_pulse, b * b_pulse)
                    for b in range(4)
                )
                for a in range(4)
            )
            errors = sum(
                ((table[a][b][0] & 1) != (a & 1))
                + ((table[a][b][1] & 1) != (b & 1))
                for a in range(4)
                for b in range(4)
            )
            if errors < best_errors:
                best_errors = errors
                best = a_pulse, b_pulse, table
                print(
                    f"best errors={errors} a_pulse={a_pulse} "
                    f"b_pulse={b_pulse}",
                    flush=True,
                )
            if errors == 0:
                print(
                    f"FULL HIT core={core} a_pulse={a_pulse} "
                    f"b_pulse={b_pulse} table={table}",
                    flush=True,
                )
                return
    print(
        f"NO HIT core={core} range={args.minimum_pulse}.."
        f"{args.maximum_pulse} best_errors={best_errors} best={best}"
    )


if __name__ == "__main__":
    main()
