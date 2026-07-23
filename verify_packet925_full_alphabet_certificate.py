#!/usr/bin/env python3
"""Pure-stdlib verifier for the packet-925 full-alphabet crossover.

The state is a sparse dictionary on the literal infinite lattice Z^2.
No finite box, sink, NumPy code, or search implementation is used.
Each queue step performs q=floor(height/4) consecutive legal topplings:
before the last of those q topplings the height is still at least four.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Iterable


CERTIFICATE = Path("packet925_full_alphabet_certificate.json")
A = (0, 0)
B = (0, 1)
D = (1, 0)
C = (1, 1)
CORE_SITES = (A, B, D, C)
DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def nonzero(values: dict[tuple[int, int], int]) -> dict[tuple[int, int], int]:
    return {site: value for site, value in values.items() if value}


def digest_sparse(values: dict[tuple[int, int], int]) -> str:
    encoded = "".join(
        f"{row},{column}:{value}\n"
        for (row, column), value in sorted(nonzero(values).items())
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def support_summary(values: dict[tuple[int, int], int]) -> dict[str, object]:
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
) -> dict[tuple[int, int], int]:
    state: defaultdict[tuple[int, int], int] = defaultdict(int)
    for site, value in zip(CORE_SITES, core, strict=True):
        state[site] = value
    state[A] += packet * a
    state[B] += packet * b
    return nonzero(state)


def stabilize_sparse(
    initial: dict[tuple[int, int], int],
) -> tuple[
    dict[tuple[int, int], int],
    dict[tuple[int, int], int],
    int,
    int,
]:
    state: defaultdict[tuple[int, int], int] = defaultdict(int, initial)
    odometer: defaultdict[tuple[int, int], int] = defaultdict(int)
    pending = deque(site for site, height in state.items() if height >= 4)
    queued = set(pending)
    legal_batches = 0
    maximum_pending = len(pending)

    while pending:
        site = pending.popleft()
        queued.discard(site)
        height = state[site]
        amount = height // 4
        if not amount:
            continue

        # These are `amount` consecutive legal unit topplings because
        # height - 4*(amount-1) >= 4.
        if height - 4 * (amount - 1) < 4:
            raise AssertionError("batched toppling was not unitwise legal")
        state[site] -= 4 * amount
        odometer[site] += amount
        legal_batches += 1
        row, column = site
        for delta_row, delta_column in DIRECTIONS:
            neighbor = (row + delta_row, column + delta_column)
            state[neighbor] += amount
            if state[neighbor] >= 4 and neighbor not in queued:
                pending.append(neighbor)
                queued.add(neighbor)
        maximum_pending = max(maximum_pending, len(pending))

    return (
        nonzero(state),
        nonzero(odometer),
        legal_batches,
        maximum_pending,
    )


def reconstruct_final(
    initial: dict[tuple[int, int], int],
    odometer: dict[tuple[int, int], int],
) -> dict[tuple[int, int], int]:
    reconstructed: defaultdict[tuple[int, int], int] = defaultdict(
        int, initial
    )
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
    final, odometer, legal_batches, maximum_pending = stabilize_sparse(initial)
    reconstructed = reconstruct_final(initial, odometer)
    if reconstructed != final:
        raise AssertionError(f"({a},{b}): discrete-Laplacian check failed")
    if any(height < 0 or height >= 4 for height in final.values()):
        raise AssertionError(f"({a},{b}): final state is not stable")
    if sum(initial.values()) != sum(final.values()):
        raise AssertionError(f"({a},{b}): mass was not conserved")

    outputs = [odometer.get(C, 0), odometer.get(D, 0)]
    parities = [value & 1 for value in outputs]
    target = [a & 1, b & 1]
    if parities != target:
        raise AssertionError(
            f"({a},{b}): got parity {parities}, expected {target}"
        )

    return {
        "a": a,
        "b": b,
        "additions_at_A_B": [packet * a, packet * b],
        "output_counts_C_D": outputs,
        "output_parities_C_D": parities,
        "target_parities": target,
        "initial_mass": sum(initial.values()),
        "final_mass": sum(final.values()),
        "total_unit_topplings": sum(odometer.values()),
        "maximum_site_topplings": max(odometer.values(), default=0),
        "legal_toppling_batches": legal_batches,
        "maximum_pending_queue": maximum_pending,
        "odometer_support": support_summary(odometer),
        "final_support": support_summary(final),
        "odometer_sha256": digest_sparse(odometer),
        "final_configuration_sha256": digest_sparse(final),
        "checks": {
            "every_batched_toppling_unitwise_legal": True,
            "final_stable": True,
            "discrete_laplacian_reconstruction": True,
            "mass_conserved_on_Z2": True,
            "output_parity_correct": True,
        },
    }


def compare_records(
    observed: Iterable[dict[str, object]],
    recorded: Iterable[dict[str, object]],
) -> None:
    observed_list = list(observed)
    recorded_list = list(recorded)
    if observed_list != recorded_list:
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
    if core != (0, 0, 2, 2) or packet != 925:
        raise AssertionError("unexpected core or packet")

    observed = [
        compute_case(core, packet, a, b)
        for a in range(4)
        for b in range(4)
    ]
    compare_records(observed, certificate["cases"])

    table = [
        [
            observed[4 * a + b]["output_counts_C_D"]
            for b in range(4)
        ]
        for a in range(4)
    ]
    if table != certificate["output_count_table_rows_a_columns_b"]:
        raise AssertionError("recorded output table disagrees")
    for a in range(4):
        for b in range(4):
            reflected = table[b][a]
            if table[a][b] != [reflected[1], reflected[0]]:
                raise AssertionError("reflection symmetry check failed")

    print("PASS: 16/16 sparse infinite-lattice stabilizations")
    print("PASS: every batched step expands to legal unit topplings")
    print("PASS: stability, Laplacian reconstruction, and mass conservation")
    print("PASS: output parity is (a mod 2, b mod 2) for all a,b in 0..3")
    print("PASS: all sparse state and odometer hashes match the certificate")


if __name__ == "__main__":
    main()
