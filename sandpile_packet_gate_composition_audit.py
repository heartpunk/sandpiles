#!/usr/bin/env python3
"""Bounded composition audit for the p=925 two-by-two packet crossover.

The packet gate is the infinite-lattice background

    0 0
    2 2

with inputs at (0,0),(0,1), packet size 925, and diagonal odometer
outputs (1,1),(1,0).  This script independently reconstructs its complete
amplitude table and tests the exact all-height-3 5xL wire on every output
count appearing in that table.

It also provides helpers for testing physically coupled interfaces; unlike
abstractly feeding an odometer count into a fresh wire, a coupled interface
allows feedback through the undirected lattice.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable, Mapping


Coord = tuple[int, int]
DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))
PACKET = 925
GATE_BACKGROUND = {
    (0, 0): 0,
    (0, 1): 0,
    (1, 0): 2,
    (1, 1): 2,
}
A_INPUT = (0, 0)
B_INPUT = (0, 1)
A_TAP = (1, 1)
B_TAP = (1, 0)
TINY_INTERFACE_BACKGROUND = {
    (0, 0): 1,
    (0, 1): 0,
    (1, 0): 1,
    (1, 1): 1,
}
TINY_INTERFACE_INPUT = (0, 0)
TINY_INTERFACE_TAP = (-1, -1)


def stabilize(
    background: Mapping[Coord, int],
    additions: Iterable[tuple[Coord, int]],
) -> tuple[dict[Coord, int], dict[Coord, int]]:
    """Legally stabilize a finite background on the infinite square lattice."""
    state: defaultdict[Coord, int] = defaultdict(int)
    state.update(background)
    odometer: defaultdict[Coord, int] = defaultdict(int)
    pending: deque[Coord] = deque()
    queued: set[Coord] = set()

    def enqueue(site: Coord) -> None:
        if state[site] >= 4 and site not in queued:
            pending.append(site)
            queued.add(site)

    for site, amount in additions:
        state[site] += amount
        enqueue(site)
    while pending:
        site = pending.popleft()
        queued.discard(site)
        amount = state[site] // 4
        if not amount:
            continue
        state[site] -= 4 * amount
        odometer[site] += amount
        row, column = site
        for delta_row, delta_column in DIRECTIONS:
            neighbor = (row + delta_row, column + delta_column)
            state[neighbor] += amount
            enqueue(neighbor)
    if any(value >= 4 or value < 0 for value in state.values()):
        raise AssertionError("stabilizer returned a nonstable state")
    return dict(state), dict(odometer)


def packet_table() -> tuple[tuple[tuple[int, int], ...], ...]:
    table = []
    for a in range(4):
        row = []
        for b in range(4):
            _, odometer = stabilize(
                GATE_BACKGROUND,
                ((A_INPUT, a * PACKET), (B_INPUT, b * PACKET)),
            )
            output = (
                odometer.get(A_TAP, 0),
                odometer.get(B_TAP, 0),
            )
            if (output[0] & 1, output[1] & 1) != (a & 1, b & 1):
                raise AssertionError(
                    f"packet gate parity failed at {(a, b)}: {output}"
                )
            row.append(output)
        table.append(tuple(row))
    return tuple(table)


def horizontal_wire(length: int) -> dict[Coord, int]:
    if length < 4:
        raise ValueError("the proved wire family requires length >= 4")
    return {
        (row, column): 3
        for row in range(5)
        for column in range(length)
    }


def isolated_wire_counts(
    length: int, amount: int
) -> tuple[int, ...]:
    _, odometer = stabilize(
        horizontal_wire(length),
        (((2, 0), amount),),
    )
    # These are exactly the taps covered by the k<=3 theorem.
    return tuple(
        odometer.get((2, column), 0)
        for column in range(length - 2)
    )


def coupled_horizontal_arms(length: int) -> dict[Coord, int]:
    """Natural direct east/west attachment to the two bottom gate taps.

    The east arm's input edge is immediately east of the 2x2 core and the
    west arm is its reflection.  Because each arm is five cells wide, its
    input edge is adjacent to both cells on that side of the core; the
    stabilization therefore includes the unavoidable undirected feedback.
    """
    background = dict(GATE_BACKGROUND)
    for row in range(-1, 4):
        for offset in range(length):
            background[row, 2 + offset] = 3
            background[row, -1 - offset] = 3
    return background


def coupled_arm_runs(
    length: int,
) -> dict[tuple[int, int], tuple[tuple[int, ...], tuple[int, ...]]]:
    background = coupled_horizontal_arms(length)
    runs = {}
    for a in range(4):
        for b in range(4):
            _, odometer = stabilize(
                background,
                ((A_INPUT, a * PACKET), (B_INPUT, b * PACKET)),
            )
            east = tuple(
                odometer.get((1, 2 + offset), 0)
                for offset in range(length - 2)
            )
            west = tuple(
                odometer.get((1, -1 - offset), 0)
                for offset in range(length - 2)
            )
            runs[a, b] = east, west
    return runs


def quotient_interfaces(
    counts: set[int], maximum_stages: int = 4
) -> list[tuple[int, ...]]:
    """Search ideal sinked one-cell divider chains.

    A height-h cell with three absorbing neighbors and one output neighbor
    topples floor((k+h)/4) times.  This is more favorable than an ordinary
    Z^2 attachment because it suppresses all feedback, so failure here rules
    out this simplest absorbing/divide-by-four interface family.
    """
    surviving: list[tuple[int, ...]] = []
    frontier = [((), {count: count for count in counts})]
    for _ in range(maximum_stages):
        next_frontier = []
        for prefix, values in frontier:
            for height in range(4):
                transformed = {
                    original: (value + height) // 4
                    for original, value in values.items()
                }
                candidate = prefix + (height,)
                if all(
                    (transformed[count] & 1) == (count & 1)
                    for count in counts
                ):
                    surviving.append(candidate)
                next_frontier.append((candidate, transformed))
        frontier = next_frontier
    return surviving


def tiny_interface_counts(counts: set[int]) -> dict[int, int]:
    result = {}
    for amount in counts:
        _, odometer = stabilize(
            TINY_INTERFACE_BACKGROUND,
            ((TINY_INTERFACE_INPUT, amount),),
        )
        result[amount] = odometer.get(TINY_INTERFACE_TAP, 0)
    return result


def good_isolated_wire_taps(
    counts: set[int], maximum_length: int
) -> list[tuple[int, int]]:
    hits = []
    for length in range(4, maximum_length + 1):
        by_amount = {
            amount: isolated_wire_counts(length, amount)
            for amount in counts
        }
        for column in range(length - 2):
            if all(
                (by_amount[amount][column] & 1) == (amount & 1)
                for amount in counts
            ):
                hits.append((length, column))
    return hits


def main() -> None:
    table = packet_table()
    print("packet table a,b -> A_tap,B_tap")
    for a, row in enumerate(table):
        print(f"a={a}:", " ".join(str(output) for output in row))

    counts = {
        value
        for row in table
        for output in row
        for value in output
    }
    print("distinct output counts", sorted(counts))
    for length in (4, 5, 6, 8, 12, 20):
        failures = []
        for amount in sorted(counts):
            taps = isolated_wire_counts(length, amount)
            bad = tuple(
                (column, count)
                for column, count in enumerate(taps)
                if (count & 1) != (amount & 1)
            )
            if bad:
                failures.append((amount, bad))
        print(
            f"isolated 5x{length}: "
            f"{len(counts) - len(failures)}/{len(counts)} "
            "packet counts preserve parity at every theorem tap"
        )
        if failures:
            print(" failures", failures)

    good_wire_taps = good_isolated_wire_taps(counts, 64)
    print(
        "isolated 5xL taps preserving every packet-count parity, "
        "4<=L<=64:",
        good_wire_taps,
    )

    tiny_map = tiny_interface_counts(counts)
    if not all(
        (output & 1) == (amount & 1)
        for amount, output in tiny_map.items()
    ):
        raise AssertionError("tiny interface did not preserve packet parity")
    print(
        "ordinary-Z2 tiny interface [[1,0],[1,1]], input (0,0), "
        "tap (-1,-1):",
        sorted(tiny_map.items()),
    )
    reduced_counts = set(tiny_map.values())
    print(
        "isolated 5xL taps preserving every reduced-count parity, "
        "4<=L<=64:",
        good_isolated_wire_taps(reduced_counts, 64),
    )
    second_tiny_map = tiny_interface_counts(reduced_counts)
    second_stage_failures = [
        (amount, output)
        for amount, output in sorted(second_tiny_map.items())
        if (amount & 1) != (output & 1)
    ]
    print(
        "feeding the reduced alphabet through the same tiny interface "
        "again fails at:",
        second_stage_failures,
    )

    coupled_hits = []
    for length in range(4, 33):
        runs = coupled_arm_runs(length)
        east_hits = [
            offset
            for offset in range(length - 2)
            if all(
                (runs[a, b][0][offset] & 1) == (a & 1)
                for a in range(4)
                for b in range(4)
            )
        ]
        west_hits = [
            offset
            for offset in range(length - 2)
            if all(
                (runs[a, b][1][offset] & 1) == (b & 1)
                for a in range(4)
                for b in range(4)
            )
        ]
        if east_hits and west_hits:
            coupled_hits.append((length, east_hits, west_hits))
    print(
        "direct symmetric east/west arm attachments with exact remote "
        "full-alphabet taps, 4<=L<=32:",
        coupled_hits,
    )

    quotient_hits = quotient_interfaces(counts)
    print(
        "ideal sinked one-cell quotient chains preserving all packet parities",
        quotient_hits,
    )
    for amount in range(10000):
        independent_topplings = sum(
            (amount + height) // 4 for height in range(4)
        )
        if independent_topplings != amount:
            raise AssertionError("four-height quotient identity failed")
    print(
        "ideal four-rail absorbing identity verified for 0<=k<10000: "
        "sum_{h=0}^3 floor((k+h)/4) = k"
    )


if __name__ == "__main__":
    main()
