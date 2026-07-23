#!/usr/bin/env python3
"""Exact full-alphabet search over every stable 2x2 background on Z^2.

Inputs a,b in {0,1,2,3} add a*p and b*p grains at the two top cells.
The diagonally paired bottom-cell odometer parities must equal a,b.
Sparse stabilization makes the computation genuinely infinite-lattice.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from itertools import product


A = (0, 0)
B = (0, 1)
D = (1, 0)
C = (1, 1)
DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def stabilize(
    core: tuple[int, int, int, int],
    a_grains: int,
    b_grains: int,
) -> defaultdict[tuple[int, int], int]:
    state: defaultdict[tuple[int, int], int] = defaultdict(int)
    odometer: defaultdict[tuple[int, int], int] = defaultdict(int)
    for site, value in zip((A, B, D, C), core, strict=True):
        state[site] = value
    state[A] += a_grains
    state[B] += b_grains
    pending = deque(site for site in (A, B) if state[site] >= 4)
    queued = set(pending)
    while pending:
        site = pending.popleft()
        queued.discard(site)
        amount = state[site] // 4
        if amount == 0:
            continue
        state[site] -= 4 * amount
        odometer[site] += amount
        row, column = site
        for dr, dc in DIRECTIONS:
            neighbor = (row + dr, column + dc)
            state[neighbor] += amount
            if state[neighbor] >= 4 and neighbor not in queued:
                pending.append(neighbor)
                queued.add(neighbor)
    return odometer


def outputs(
    core: tuple[int, int, int, int], a: int, b: int, pulse: int
) -> tuple[int, int]:
    odometer = stabilize(core, a * pulse, b * pulse)
    return odometer[C], odometer[D]


def boolean_valid(
    core: tuple[int, int, int, int], pulse: int
) -> bool:
    return all(
        tuple(value & 1 for value in outputs(core, a, b, pulse))
        == (a, b)
        for a, b in ((1, 0), (0, 1), (1, 1))
    )


def full_valid(
    core: tuple[int, int, int, int], pulse: int
) -> tuple[bool, tuple[tuple[tuple[int, int], ...], ...]]:
    return full_valid_scales(core, pulse, pulse)


def full_valid_scales(
    core: tuple[int, int, int, int], a_pulse: int, b_pulse: int
) -> tuple[bool, tuple[tuple[tuple[int, int], ...], ...]]:
    table = tuple(
        tuple(
            (
                lambda odometer: (odometer[C], odometer[D])
            )(stabilize(core, a * a_pulse, b * b_pulse))
            for b in range(4)
        )
        for a in range(4)
    )
    valid = all(
        tuple(value & 1 for value in table[a][b])
        == (a & 1, b & 1)
        for a in range(4)
        for b in range(4)
    )
    return valid, table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--maximum-pulse", type=int, default=500)
    args = parser.parse_args()
    boolean_hits = 0
    best_errors = 33
    best = None
    for pulse in range(1, args.maximum_pulse + 1):
        pulse_hits = 0
        for core in product(range(4), repeat=4):
            if not boolean_valid(core, pulse):
                continue
            boolean_hits += 1
            pulse_hits += 1
            valid, table = full_valid(core, pulse)
            errors = sum(
                ((table[a][b][0] & 1) != (a & 1))
                + ((table[a][b][1] & 1) != (b & 1))
                for a in range(4)
                for b in range(4)
            )
            if errors < best_errors:
                best_errors = errors
                best = pulse, core, table
                print(
                    f"best errors={errors} pulse={pulse} core={core}",
                    flush=True,
                )
            if valid:
                print(
                    f"FULL HIT pulse={pulse} core={core} table={table}",
                    flush=True,
                )
                return
        if pulse_hits:
            print(
                f"pulse={pulse} boolean_hits={pulse_hits} "
                f"cumulative={boolean_hits}",
                flush=True,
            )
    print(
        f"NO FULL HIT pulses=1..{args.maximum_pulse}; "
        f"boolean_hits={boolean_hits}; best_errors={best_errors}; best={best}"
    )


if __name__ == "__main__":
    main()
