#!/usr/bin/env python3
"""Independent sparse infinite-lattice audit of the p=925 witness.

Stabilization is by synchronous legal waves on dictionaries, not by the
fixed-array queue used by the search program.  Every result is checked
against the Laplacian equation and mass conservation, then serialized to
a canonical SHA-256 digest.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from typing import Iterable


Site = tuple[int, int]
A = (0, 0)
B = (0, 1)
D = (1, 0)
C = (1, 1)
PULSE = 925
DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))
WITNESS_CORE = (0, 0, 2, 2)

EXPECTED_TABLE = (
    ((0, 0), (300, 237), (698, 572), (1130, 941)),
    ((237, 300), (625, 625), (1073, 1010), (1531, 1405)),
    ((572, 698), (1010, 1073), (1456, 1456), (1946, 1883)),
    ((941, 1130), (1405, 1531), (1883, 1946), (2371, 2371)),
)


def neighbors(site: Site) -> Iterable[Site]:
    row, column = site
    for delta_row, delta_column in DIRECTIONS:
        yield row + delta_row, column + delta_column


def initial_state(
    core: tuple[int, int, int, int],
    a: int,
    b: int,
    pulse: int,
) -> dict[Site, int]:
    state = {
        A: core[0],
        B: core[1],
        D: core[2],
        C: core[3],
    }
    state[A] += a * pulse
    state[B] += b * pulse
    return state


def stabilize(
    core: tuple[int, int, int, int],
    a: int,
    b: int,
    pulse: int,
) -> tuple[dict[Site, int], dict[Site, int], int]:
    state: defaultdict[Site, int] = defaultdict(
        int, initial_state(core, a, b, pulse)
    )
    odometer: defaultdict[Site, int] = defaultdict(int)
    frontier = {site for site, height in state.items() if height >= 4}
    rounds = 0

    while frontier:
        # Every listed site is already unstable.  Its quotient topplings can
        # be linearized into legal single-site topplings in any order.
        batch = {
            site: state[site] // 4
            for site in frontier
            if state[site] >= 4
        }
        if not batch:
            raise AssertionError("nonempty wave made no progress")
        affected: set[Site] = set()
        for site, amount in batch.items():
            state[site] -= 4 * amount
            odometer[site] += amount
            affected.add(site)
            for neighbor in neighbors(site):
                state[neighbor] += amount
                affected.add(neighbor)
        frontier = {site for site in affected if state[site] >= 4}
        rounds += 1

    final = {site: height for site, height in state.items() if height}
    odo = {site: count for site, count in odometer.items() if count}
    return final, odo, rounds


def audit_case(
    core: tuple[int, int, int, int],
    a: int,
    b: int,
    pulse: int,
    *,
    check_witness_output: bool = True,
) -> dict[str, object]:
    initial = initial_state(core, a, b, pulse)
    final, odometer, rounds = stabilize(core, a, b, pulse)
    universe = set(initial) | set(final) | set(odometer)
    for site in tuple(odometer):
        universe.update(neighbors(site))

    for site in universe:
        expected = initial.get(site, 0) - 4 * odometer.get(site, 0)
        expected += sum(odometer.get(neighbor, 0) for neighbor in neighbors(site))
        if final.get(site, 0) != expected:
            raise AssertionError(
                f"Laplacian mismatch at {site}: "
                f"{final.get(site, 0)} != {expected}"
            )
    if any(not 0 <= height <= 3 for height in final.values()):
        raise AssertionError("final configuration is not stable")
    if sum(final.values()) != sum(initial.values()):
        raise AssertionError("infinite-lattice mass was not conserved")

    output = (odometer.get(C, 0), odometer.get(D, 0))
    if check_witness_output and output != EXPECTED_TABLE[a][b]:
        raise AssertionError(
            f"unexpected output at {(a, b)}: {output}"
        )
    if check_witness_output and (
        output[0] & 1, output[1] & 1
    ) != (a & 1, b & 1):
        raise AssertionError(f"wrong parity at {(a, b)}")

    support = tuple(odometer)
    radius = max(
        (max(abs(row), abs(column)) for row, column in support),
        default=0,
    )
    bounds = (
        min((row for row, _ in support), default=0),
        max((row for row, _ in support), default=0),
        min((column for _, column in support), default=0),
        max((column for _, column in support), default=0),
    )
    return {
        "input": [a, b],
        "output": list(output),
        "rounds": rounds,
        "toppling_radius_linf_from_A": radius,
        "toppling_bounds": list(bounds),
        "odometer": [
            [row, column, count]
            for (row, column), count in sorted(odometer.items())
        ],
        "final": [
            [row, column, height]
            for (row, column), height in sorted(final.items())
        ],
    }


def main() -> None:
    cases = [
        audit_case(WITNESS_CORE, a, b, PULSE)
        for a in range(4)
        for b in range(4)
    ]

    # One sparse run proves the fixed-array radius cutoff for the whole
    # exhaustive search: this configuration pointwise dominates every stable
    # 2x2 core, every p <= 925, and every a,b <= 3.
    dominating = audit_case(
        (3, 3, 3, 3),
        3,
        3,
        PULSE,
        check_witness_output=False,
    )
    if dominating["toppling_radius_linf_from_A"] != 27:
        raise AssertionError("dominating radius changed")
    if dominating["toppling_bounds"] != [-27, 27, -26, 27]:
        raise AssertionError("dominating support bounds changed")

    encoded = json.dumps(
        {
            "model": "infinite Z2, synchronous legal waves",
            "pulse": PULSE,
            "core": WITNESS_CORE,
            "cases": cases,
            "dominating_run": dominating,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    digest = hashlib.sha256(encoded).hexdigest()

    print("output table (C,D):")
    for a in range(4):
        print("a=%d:" % a, " ".join(map(str, EXPECTED_TABLE[a])))
    print(
        "dominating radius=27 bounds=(-27,27,-26,27); "
        "all 16 witness cases stable, conservative, and Laplacian-exact"
    )
    print("canonical_sha256=" + digest)


if __name__ == "__main__":
    main()
