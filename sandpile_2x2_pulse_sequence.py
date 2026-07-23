#!/usr/bin/env python3
"""Explore parity-crossing pulse values for the all-three 2x2 seed on Z^2.

Stabilizations are updated one grain at a time in a sparse, unbounded lattice,
so every prefix p is exact and there is no artificial boundary.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque


A = (0, 0)
B = (0, 1)
D = (1, 0)
C = (1, 1)
DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))


class InfiniteSandpile:
    def __init__(self) -> None:
        self.state: defaultdict[tuple[int, int], int] = defaultdict(int)
        self.odometer: defaultdict[tuple[int, int], int] = defaultdict(int)
        for site in (A, B, C, D):
            self.state[site] = 3

    def add_and_stabilize(self, additions: tuple[tuple[int, int], ...]) -> None:
        pending: deque[tuple[int, int]] = deque()
        queued: set[tuple[int, int]] = set()
        for site in additions:
            self.state[site] += 1
            if self.state[site] >= 4 and site not in queued:
                pending.append(site)
                queued.add(site)
        while pending:
            site = pending.popleft()
            queued.discard(site)
            amount = self.state[site] // 4
            if amount == 0:
                continue
            self.state[site] -= 4 * amount
            self.odometer[site] += amount
            row, column = site
            for dr, dc in DIRECTIONS:
                neighbor = (row + dr, column + dc)
                self.state[neighbor] += amount
                if self.state[neighbor] >= 4 and neighbor not in queued:
                    pending.append(neighbor)
                    queued.add(neighbor)

    def radius(self) -> int:
        active = (
            site for site, value in self.odometer.items() if value
        )
        return max(
            (max(abs(row), abs(column)) for row, column in active),
            default=0,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--maximum-pulse", type=int, default=100_000)
    parser.add_argument("--show", type=int, default=100)
    args = parser.parse_args()
    one = InfiniteSandpile()
    both = InfiniteSandpile()
    hits: list[int] = []
    for pulse in range(1, args.maximum_pulse + 1):
        one.add_and_stabilize((A,))
        both.add_and_stabilize((A, B))
        c, d = one.odometer[C], one.odometer[D]
        cc, dd = both.odometer[C], both.odometer[D]
        if c % 2 == 1 and d % 2 == 0 and cc % 2 == 1 and dd % 2 == 1:
            hits.append(pulse)
    print(
        f"searched p=1..{args.maximum_pulse}; hits={len(hits)}; "
        f"one_radius={one.radius()}; both_radius={both.radius()}"
    )
    print("first_hits", hits[: args.show])
    if hits:
        gaps = [right - left for left, right in zip(hits, hits[1:])]
        print("first_gaps", gaps[: args.show])


if __name__ == "__main__":
    main()
