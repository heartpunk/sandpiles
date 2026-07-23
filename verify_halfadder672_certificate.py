#!/usr/bin/env python3
"""Independent verifier for the packet-672 odometer-parity half-adder.

This verifier uses only the Python standard library and literal signed
coordinates on the infinite lattice Z^2.  It does not import, call, or share
the finite-array implementation used by the exhaustive search.  Every heap
event performs exactly one legal toppling.
"""

from __future__ import annotations

import hashlib
import heapq
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path


Coord = tuple[int, int]
CERTIFICATE = Path("halfadder672_certificate.json")
DIRECTIONS: tuple[Coord, ...] = ((-1, 0), (0, -1), (0, 1), (1, 0))
A = (0, 0)
B = (0, 1)
D = (1, 0)
C = (1, 1)
CORE_SITES = (A, B, D, C)
CORE = (0, 3, 3, 2)
PACKET = 672

SUM_EAST = (-3, 3)
CARRY_EAST = (-1, 3)
SUM_WEST = (-3, -2)
CARRY_WEST = (1, -2)
OUTPUT_SITES = (SUM_EAST, CARRY_EAST, SUM_WEST, CARRY_WEST)


def nonzero(values: Mapping[Coord, int]) -> dict[Coord, int]:
    return {site: value for site, value in values.items() if value}


def digest_sparse(values: Mapping[Coord, int]) -> str:
    encoded = "".join(
        f"{row},{column}:{value}\n"
        for (row, column), value in sorted(nonzero(values).items())
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def support_summary(values: Mapping[Coord, int]) -> dict[str, object]:
    sites = list(nonzero(values))
    if not sites:
        return {
            "sites": 0,
            "bounding_box_row_min_row_max_col_min_col_max": None,
            "l1_radius_from_origin": 0,
            "linf_radius_from_origin": 0,
        }
    rows = [site[0] for site in sites]
    columns = [site[1] for site in sites]
    return {
        "sites": len(sites),
        "bounding_box_row_min_row_max_col_min_col_max": [
            min(rows),
            max(rows),
            min(columns),
            max(columns),
        ],
        "l1_radius_from_origin": max(
            abs(row) + abs(column) for row, column in sites
        ),
        "linf_radius_from_origin": max(
            max(abs(row), abs(column)) for row, column in sites
        ),
    }


def initial_state(
    core: tuple[int, int, int, int],
    packet: int,
    a: int,
    b: int,
) -> dict[Coord, int]:
    state: defaultdict[Coord, int] = defaultdict(int)
    for site, height in zip(CORE_SITES, core, strict=True):
        state[site] = height
    state[A] += packet * a
    state[B] += packet * b
    return nonzero(state)


def stabilize_unitwise(
    initial: Mapping[Coord, int],
) -> tuple[dict[Coord, int], dict[Coord, int], int]:
    """Stabilize using lexicographic, exactly-one-at-a-time topplings."""
    state: defaultdict[Coord, int] = defaultdict(int, initial)
    odometer: defaultdict[Coord, int] = defaultdict(int)
    pending = [site for site, height in state.items() if height >= 4]
    heapq.heapify(pending)
    queued = set(pending)
    maximum_pending = len(pending)

    def enqueue(site: Coord) -> None:
        if state[site] >= 4 and site not in queued:
            heapq.heappush(pending, site)
            queued.add(site)

    while pending:
        site = heapq.heappop(pending)
        queued.remove(site)
        if state[site] < 4:
            continue

        state[site] -= 4
        odometer[site] += 1
        enqueue(site)
        row, column = site
        for delta_row, delta_column in DIRECTIONS:
            neighbor = (row + delta_row, column + delta_column)
            state[neighbor] += 1
            enqueue(neighbor)
        maximum_pending = max(maximum_pending, len(pending))

    return nonzero(state), nonzero(odometer), maximum_pending


def reconstruct_final(
    initial: Mapping[Coord, int],
    odometer: Mapping[Coord, int],
) -> dict[Coord, int]:
    reconstructed: defaultdict[Coord, int] = defaultdict(int, initial)
    for (row, column), amount in odometer.items():
        reconstructed[(row, column)] -= 4 * amount
        for delta_row, delta_column in DIRECTIONS:
            reconstructed[(row + delta_row, column + delta_column)] += amount
    return nonzero(reconstructed)


def compute_case(
    core: tuple[int, int, int, int],
    packet: int,
    a: int,
    b: int,
) -> dict[str, object]:
    initial = initial_state(core, packet, a, b)
    final, odometer, maximum_pending = stabilize_unitwise(initial)
    reconstructed = reconstruct_final(initial, odometer)
    if reconstructed != final:
        raise AssertionError(f"{(a, b)}: discrete-Laplacian check failed")
    if any(height < 0 or height >= 4 for height in final.values()):
        raise AssertionError(f"{(a, b)}: final state is not stable")
    if sum(initial.values()) != sum(final.values()):
        raise AssertionError(f"{(a, b)}: mass was not conserved")

    counts = [odometer.get(site, 0) for site in OUTPUT_SITES]
    parities = [count & 1 for count in counts]
    expected = [
        (a & 1) ^ (b & 1),
        (a & 1) & (b & 1),
        (a & 1) ^ (b & 1),
        (a & 1) & (b & 1),
    ]
    if parities != expected:
        raise AssertionError(
            f"{(a, b)}: got parities {parities}, expected {expected}"
        )

    return {
        "a": a,
        "b": b,
        "additions_at_A_B": [packet * a, packet * b],
        "output_counts_sum_east_carry_east_sum_west_carry_west": counts,
        "output_parities_sum_east_carry_east_sum_west_carry_west": (
            parities
        ),
        "target_parities_sum_carry_sum_carry": expected,
        "initial_mass": sum(initial.values()),
        "final_mass": sum(final.values()),
        "total_unit_topplings": sum(odometer.values()),
        "maximum_site_topplings": max(odometer.values(), default=0),
        "maximum_pending_heap": maximum_pending,
        "odometer_support": support_summary(odometer),
        "final_support": support_summary(final),
        "odometer_sha256": digest_sparse(odometer),
        "final_configuration_sha256": digest_sparse(final),
        "checks": {
            "every_toppling_individually_legal": True,
            "final_stable": True,
            "discrete_laplacian_reconstruction": True,
            "mass_conserved_on_Z2": True,
            "all_four_output_parities_correct": True,
        },
    }


def output_tables(
    cases: list[dict[str, object]],
) -> dict[str, list[list[int]]]:
    names = ("sum_east", "carry_east", "sum_west", "carry_west")
    result: dict[str, list[list[int]]] = {}
    for output_index, name in enumerate(names):
        result[name] = [
            [
                cases[4 * a + b][
                    "output_counts_sum_east_carry_east_sum_west_carry_west"
                ][output_index]
                for b in range(4)
            ]
            for a in range(4)
        ]
    return result


def compare_records(
    observed: Iterable[dict[str, object]],
    recorded: Iterable[dict[str, object]],
) -> None:
    observed_list = list(observed)
    recorded_list = list(recorded)
    if observed_list == recorded_list:
        return
    for index, (left, right) in enumerate(
        zip(observed_list, recorded_list)
    ):
        if left != right:
            raise AssertionError(
                f"certificate case {index} disagrees:\n"
                f"observed={left}\nrecorded={right}"
            )
    raise AssertionError("certificate case count disagrees")


def main() -> None:
    certificate = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    core = tuple(certificate["encoding"]["core_row_major_A_B_D_C"])
    packet = certificate["encoding"]["packet_size"]
    if core != CORE or packet != PACKET:
        raise AssertionError("unexpected certificate core or packet")

    observed = [
        compute_case(core, packet, a, b)
        for a in range(4)
        for b in range(4)
    ]
    compare_records(observed, certificate["cases"])
    tables = output_tables(observed)
    if tables != certificate["output_count_tables_rows_a_columns_b"]:
        raise AssertionError("recorded output tables disagree")

    for a in range(4):
        for b in range(4):
            case = observed[4 * a + b]
            parities = case[
                "output_parities_sum_east_carry_east_sum_west_carry_west"
            ]
            if parities != [
                (a & 1) ^ (b & 1),
                (a & 1) & (b & 1),
                (a & 1) ^ (b & 1),
                (a & 1) & (b & 1),
            ]:
                raise AssertionError("half-adder truth-table check failed")

    print("PASS: 16/16 sparse infinite-lattice stabilizations")
    print("PASS: every toppling was individually legal")
    print("PASS: stability, Laplacian reconstruction, and mass conservation")
    print("PASS: two SUM taps and two CARRY taps realize the half-adder")
    print("PASS: all sparse state and odometer hashes match the certificate")


if __name__ == "__main__":
    main()
