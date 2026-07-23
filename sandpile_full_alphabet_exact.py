#!/usr/bin/env python3
"""Exact 3x3 search for a parity-linear sandpile crossover.

The background is supported on a 3x3 core embedded in a 7x7 zero window.
For a logical pulse p, inputs a,b in {0,1,2,3} add a*p grains at the
north port and b*p grains at the west port.  A full-alphabet crossover
requires

    u_S(a,b) == a (mod 2)
    u_E(a,b) == b (mod 2)

for all sixteen input pairs.  Candidates are first filtered by the four
Boolean cases, then the full table is evaluated exactly.  Incremental
stabilization is valid by the Abelian property.
"""

from __future__ import annotations

import argparse
from collections import deque
import itertools


def add_one(
    state: list[int],
    odometer: list[int],
    side: int,
    position: int,
) -> None:
    """Add one grain and legally stabilize in place."""
    state[position] += 1
    if state[position] < 4:
        return
    queue = deque((position,))
    queued = [False] * len(state)
    queued[position] = True
    while queue:
        current = queue.popleft()
        queued[current] = False
        amount = state[current] // 4
        if not amount:
            continue
        state[current] -= 4 * amount
        odometer[current] += amount
        row, column = divmod(current, side)
        if row:
            neighbor = current - side
            state[neighbor] += amount
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if row + 1 < side:
            neighbor = current + side
            state[neighbor] += amount
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if column:
            neighbor = current - 1
            state[neighbor] += amount
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if column + 1 < side:
            neighbor = current + 1
            state[neighbor] += amount
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)


def add_pulse(
    state: list[int],
    odometer: list[int],
    side: int,
    position: int,
    pulse: int,
) -> None:
    for _ in range(pulse):
        add_one(state, odometer, side, position)


def table_for(
    initial: list[int],
    side: int,
    north: int,
    west: int,
    south: int,
    east: int,
    pulse: int,
) -> tuple[tuple[tuple[int, int], ...], int]:
    """Return the 4x4 output-count table and outer-boundary activity."""
    zero_odo = [0] * len(initial)
    north_states: list[tuple[list[int], list[int]]] = [
        (initial.copy(), zero_odo.copy())
    ]
    for _ in range(3):
        state = north_states[-1][0].copy()
        odometer = north_states[-1][1].copy()
        add_pulse(state, odometer, side, north, pulse)
        north_states.append((state, odometer))

    table: list[tuple[int, int]] = []
    boundary_activity = 0
    boundary = tuple(
        position
        for position in range(side * side)
        if (
            position < side
            or position >= side * (side - 1)
            or position % side == 0
            or position % side == side - 1
        )
    )
    for a in range(4):
        state = north_states[a][0].copy()
        odometer = north_states[a][1].copy()
        for b in range(4):
            if b:
                add_pulse(state, odometer, side, west, pulse)
            table.append((odometer[south], odometer[east]))
            boundary_activity += sum(odometer[q] for q in boundary)
    return tuple(table), boundary_activity


def parity_errors(table: tuple[tuple[int, int], ...]) -> int:
    return sum(
        (south & 1) != (a & 1) or (east & 1) != (b & 1)
        for a in range(4)
        for b in range(4)
        for south, east in (table[4 * a + b],)
    )


def bit_errors(table: tuple[tuple[int, int], ...]) -> int:
    return sum(
        ((south & 1) != (a & 1)) + ((east & 1) != (b & 1))
        for a in range(4)
        for b in range(4)
        for south, east in (table[4 * a + b],)
    )


def boolean_valid(table: tuple[tuple[int, int], ...]) -> bool:
    for a, b in ((0, 0), (0, 1), (1, 0), (1, 1)):
        south, east = table[4 * a + b]
        if (south & 1) != a or (east & 1) != b:
            return False
    return True


def print_table(table: tuple[tuple[int, int], ...]) -> None:
    for a in range(4):
        print(
            f"a={a}: "
            + " ".join(
                f"{table[4 * a + b][0]},{table[4 * a + b][1]}"
                for b in range(4)
            ),
            flush=True,
        )


def search(max_pulse: int, padding: int) -> None:
    core_side = 3
    side = core_side + 2 * padding
    mid = padding + 1
    north = padding * side + mid
    west = mid * side + padding
    south = (padding + 2) * side + mid
    east = mid * side + padding + 2
    core_positions = tuple(
        (padding + row) * side + padding + column
        for row in range(3)
        for column in range(3)
    )

    boolean_hits = [0] * (max_pulse + 1)
    best: list[tuple[int, tuple[int, ...], tuple[tuple[int, int], ...]] | None] = [
        None
    ] * (max_pulse + 1)
    full_hits = 0

    for index, core in enumerate(itertools.product(range(4), repeat=9)):
        initial = [0] * (side * side)
        for position, value in zip(core_positions, core):
            initial[position] = value
        north_state = initial.copy()
        west_state = initial.copy()
        both_state = initial.copy()
        north_odometer = [0] * (side * side)
        west_odometer = [0] * (side * side)
        both_odometer = [0] * (side * side)
        boundary = tuple(
            position
            for position in range(side * side)
            if (
                position < side
                or position >= side * (side - 1)
                or position % side == 0
                or position % side == side - 1
            )
        )
        for pulse in range(1, max_pulse + 1):
            add_one(north_state, north_odometer, side, north)
            add_one(west_state, west_odometer, side, west)
            add_one(both_state, both_odometer, side, north)
            add_one(both_state, both_odometer, side, west)
            boolean_counts = (
                north_odometer[south],
                north_odometer[east],
                west_odometer[south],
                west_odometer[east],
                both_odometer[south],
                both_odometer[east],
            )
            if tuple(value & 1 for value in boolean_counts) != (
                1,
                0,
                0,
                1,
                1,
                1,
            ):
                continue
            if any(
                north_odometer[q]
                or west_odometer[q]
                or both_odometer[q]
                for q in boundary
            ):
                continue
            table, boundary_activity = table_for(
                initial, side, north, west, south, east, pulse
            )
            if boundary_activity:
                continue
            assert boolean_valid(table)
            boolean_hits[pulse] += 1
            errors = bit_errors(table)
            candidate = (errors, core, table)
            if best[pulse] is None or errors < best[pulse][0]:
                best[pulse] = candidate
            if errors == 0:
                full_hits += 1
                print(
                    f"FULL-ALPHABET HIT core_index={index} pulse={pulse}",
                    flush=True,
                )
                print(core[0:3], core[3:6], core[6:9], sep="\n")
                print_table(table)
                return
        if index and index % 10_000 == 0:
            current = min(
                (
                    (candidate[0], pulse)
                    for pulse, candidate in enumerate(best)
                    if candidate is not None
                ),
                default=None,
            )
            print(
                f"checked={index}/262144 best_bit_errors,pulse={current}",
                flush=True,
            )

    print(
        f"EXHAUSTED 3x3 cores={4**9} pulses=1..{max_pulse} "
        f"full_hits={full_hits}",
        flush=True,
    )
    for pulse in range(1, max_pulse + 1):
        if not boolean_hits[pulse]:
            continue
        assert best[pulse] is not None
        errors, core, table = best[pulse]
        print(
            f"pulse={pulse} boolean_hits={boolean_hits[pulse]} "
            f"best_full_bit_errors={errors}",
            flush=True,
        )
        print(core[0:3], core[3:6], core[6:9], sep="\n")
        print_table(table)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pulse", type=int, default=64)
    parser.add_argument("--padding", type=int, default=3)
    args = parser.parse_args()
    if args.max_pulse < 1:
        parser.error("--max-pulse must be positive")
    if args.padding < 2:
        parser.error("--padding must be at least 2")
    search(args.max_pulse, args.padding)


if __name__ == "__main__":
    main()
