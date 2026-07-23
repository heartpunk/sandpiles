#!/usr/bin/env python3
"""Exhaust and certify the minimal-pulse 2x2 parity crossover.

The search space is every stable background on a designated 2x2 core,
surrounded by zeros on the ordinary square lattice.  Equal pulses are added
at the two top sites.  The diagonally opposite bottom sites are read by
odometer parity.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np

from sandpile_crossing_search import stabilize
from sandpile_parity_crossing_search import stabilize_flat


OUTPUT = Path("finite_2x2_parity_crossover_certificate.json")
PADDING = 3
BOARD_SIZE = 2 + 2 * PADDING
PULSE = 15

A_INPUT = (PADDING, PADDING)
B_INPUT = (PADDING, PADDING + 1)
D_OUTPUT = (PADDING + 1, PADDING)
C_OUTPUT = (PADDING + 1, PADDING + 1)

TARGET = {
    "a": (1, 0),
    "b": (0, 1),
    "both": (1, 1),
}


def board_for(core: tuple[int, int, int, int]) -> np.ndarray:
    board = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.int64)
    board[
        PADDING : PADDING + 2,
        PADDING : PADDING + 2,
    ] = np.array(core, dtype=np.int64).reshape((2, 2))
    return board


def cases_for(
    board: np.ndarray, pulse: int
) -> dict[str, tuple[np.ndarray, tuple[tuple[int, int], ...]]]:
    additions = {
        "a": ((A_INPUT, pulse),),
        "b": ((B_INPUT, pulse),),
        "both": ((A_INPUT, pulse), (B_INPUT, pulse)),
    }
    return {
        name: (stabilize(board, values), values)
        for name, values in additions.items()
    }


def output_counts(odometer: np.ndarray) -> tuple[int, int]:
    return int(odometer[C_OUTPUT]), int(odometer[D_OUTPUT])


def boundary_odometer_is_zero(odometer: np.ndarray) -> bool:
    return not (
        np.any(odometer[0, :])
        or np.any(odometer[-1, :])
        or np.any(odometer[:, 0])
        or np.any(odometer[:, -1])
    )


def is_crossing(
    runs: dict[str, tuple[np.ndarray, tuple[tuple[int, int], ...]]]
) -> bool:
    return all(
        tuple(value & 1 for value in output_counts(runs[name][0]))
        == TARGET[name]
        for name in TARGET
    )


def legal_trace(
    board: np.ndarray,
    additions: tuple[tuple[tuple[int, int], int], ...],
) -> tuple[np.ndarray, np.ndarray, list[list[int]]]:
    state = board.copy()
    for position, amount in additions:
        state[position] += amount
    odometer = np.zeros_like(state)
    trace: list[list[int]] = []
    while True:
        unstable = np.argwhere(state >= 4)
        if not len(unstable):
            return state, odometer, trace
        row, column = (int(value) for value in unstable[0])
        trace.append([row, column])
        state[row, column] -= 4
        odometer[row, column] += 1
        if row:
            state[row - 1, column] += 1
        if row + 1 < BOARD_SIZE:
            state[row + 1, column] += 1
        if column:
            state[row, column - 1] += 1
        if column + 1 < BOARD_SIZE:
            state[row, column + 1] += 1


def final_from(
    board: np.ndarray,
    additions: tuple[tuple[tuple[int, int], int], ...],
    odometer: np.ndarray,
) -> np.ndarray:
    final = board.copy()
    for position, amount in additions:
        final[position] += amount
    final -= 4 * odometer
    final[:-1, :] += odometer[1:, :]
    final[1:, :] += odometer[:-1, :]
    final[:, :-1] += odometer[:, 1:]
    final[:, 1:] += odometer[:, :-1]
    return final


def independently_verify(
    board: np.ndarray,
    additions: tuple[tuple[tuple[int, int], int], ...],
    odometer: np.ndarray,
    final: np.ndarray,
) -> None:
    flat_additions = tuple(
        (position[0] * BOARD_SIZE + position[1], amount)
        for position, amount in additions
    )
    flat_odometer = np.array(
        stabilize_flat(
            tuple(int(value) for value in board.flat),
            BOARD_SIZE,
            flat_additions,
        ),
        dtype=np.int64,
    ).reshape(board.shape)
    if not np.array_equal(flat_odometer, odometer):
        raise AssertionError("independent stabilizers disagree")
    if not np.array_equal(
        final_from(board, additions, odometer), final
    ):
        raise AssertionError("Laplacian reconstruction disagrees")
    if int(final.min()) < 0 or int(final.max()) > 3:
        raise AssertionError("final configuration is unstable")
    if not boundary_odometer_is_zero(odometer):
        raise AssertionError("avalanche reached padded boundary")
    if int(board.sum()) + sum(
        amount for _, amount in additions
    ) != int(final.sum()):
        raise AssertionError("mass was not conserved")


def exhaustive_counts(
    maximum_pulse: int,
) -> tuple[list[dict[str, int]], list[dict[str, object]]]:
    summary: list[dict[str, int]] = []
    final_solutions: list[dict[str, object]] = []
    for pulse in range(1, maximum_pulse + 1):
        count = 0
        for core in itertools.product(range(4), repeat=4):
            runs = cases_for(board_for(core), pulse)
            if not all(
                boundary_odometer_is_zero(run[0])
                for run in runs.values()
            ):
                raise AssertionError(
                    "padding was reached during exhaustive search"
                )
            if not is_crossing(runs):
                continue
            count += 1
            if pulse == maximum_pulse:
                final_solutions.append(
                    {
                        "core_row_major": list(core),
                        "core_rows": [
                            list(core[:2]),
                            list(core[2:]),
                        ],
                        "output_counts_c_d": {
                            name: list(output_counts(run[0]))
                            for name, run in runs.items()
                        },
                    }
                )
        summary.append({"pulse": pulse, "solutions": count})
    return summary, final_solutions


def amplitude_table(board: np.ndarray) -> list[dict[str, object]]:
    table: list[dict[str, object]] = []
    for a in range(4):
        for b in range(4):
            additions: list[tuple[tuple[int, int], int]] = []
            if a:
                additions.append((A_INPUT, PULSE * a))
            if b:
                additions.append((B_INPUT, PULSE * b))
            odometer = stabilize(board, tuple(additions))
            counts = output_counts(odometer)
            parities = [value & 1 for value in counts]
            target = [a & 1, b & 1]
            table.append(
                {
                    "a_pulse_multiplicity": a,
                    "b_pulse_multiplicity": b,
                    "output_counts_c_d": list(counts),
                    "output_parities_c_d": parities,
                    "target_parities": target,
                    "parity_linear": parities == target,
                    "total_topplings": int(odometer.sum()),
                }
            )
    return table


def main() -> None:
    all_three_core = (3, 3, 3, 3)
    board = board_for(all_three_core)
    runs = cases_for(board, PULSE)
    if not is_crossing(runs):
        raise AssertionError("all-3 witness no longer crosses")

    cases: dict[str, object] = {}
    for name, (expected_odometer, additions) in runs.items():
        final, odometer, trace = legal_trace(board, additions)
        if not np.array_equal(odometer, expected_odometer):
            raise AssertionError("legal trace and queue stabilizer disagree")
        independently_verify(board, additions, odometer, final)
        counts = output_counts(odometer)
        cases[name] = {
            "additions": [
                {"position": list(position), "amount": amount}
                for position, amount in additions
            ],
            "output_counts_c_d": list(counts),
            "output_parities_c_d": [
                value & 1 for value in counts
            ],
            "total_topplings": int(odometer.sum()),
            "maximum_site_topplings": int(odometer.max()),
            "legal_trace": trace,
            "odometer": odometer.tolist(),
            "final_configuration": final.tolist(),
        }

    enumeration, pulse_15_solutions = exhaustive_counts(PULSE)
    expected = [0] * 14 + [17]
    if [item["solutions"] for item in enumeration] != expected:
        raise AssertionError("exhaustive minimality counts changed")

    certificate = {
        "title": (
            "Minimal-pulse parity crossover on the smallest "
            "four-distinct-port square core"
        ),
        "model": {
            "lattice": "infinite square von Neumann lattice",
            "threshold": 4,
            "outside_background": 0,
            "finite_board_used_for_certificate": BOARD_SIZE,
            "padding": PADDING,
            "reason_padding_is_exact": (
                "Every certified boundary odometer is zero, so the "
                "finite calculation equals stabilization on Z^2."
            ),
        },
        "core": {
            "background_rows": [[3, 3], [3, 3]],
            "pulse": PULSE,
            "ports": {
                "a_input_top_left": list(A_INPUT),
                "b_input_top_right": list(B_INPUT),
                "a_output_c_bottom_right": list(C_OUTPUT),
                "b_output_d_bottom_left": list(D_OUTPUT),
            },
            "cyclic_port_order": ["A", "B", "C", "D"],
            "paired_crossing_channels": ["A-C", "B-D"],
        },
        "background": board.tolist(),
        "cases": cases,
        "minimality": {
            "claim": (
                "Among all 4^4 stable backgrounds supported on this "
                "2x2 core, with zeros elsewhere, equal positive pulses "
                "p at A/B, and C/D odometer-parity readout required to "
                "give A -> (1,0), B -> (0,1), and A+B -> (1,1), no "
                "crossing exists for integer p=1 through 14. At p=15 "
                "there are exactly 17 backgrounds."
            ),
            "scope": (
                "This is minimality within the explicitly exhausted "
                "2x2-core/equal-positive-integer-pulse/fixed-port/"
                "odometer-parity encoding class. A 2x2 square is the "
                "smallest square core that can hold four distinct "
                "cyclically ordered ports. This is not a minimality "
                "claim among every larger or differently encoded gadget."
            ),
            "enumeration": enumeration,
            "pulse_15_solutions": pulse_15_solutions,
            "backgrounds_checked_per_pulse": 4**4,
            "total_background_pulse_pairs_checked": (4**4) * PULSE,
            "total_input_cases_stabilized": (4**4) * PULSE * 3,
            "all_exhaustive_search_boundary_odometers_zero": True,
        },
        "pulse_multiplicity_table_0_through_3": amplitude_table(board),
        "verification": {
            "complete_2x2_background_enumeration": True,
            "all_11520_search_avalanches_finite_inside_padding": True,
            "legal_trace_checked_at_every_step": True,
            "final_stability_checked": True,
            "laplacian_reconstruction_checked": True,
            "mass_conservation_checked": True,
            "zero_boundary_odometer_checked": True,
            "two_independent_stabilizers_agree": True,
        },
    }
    OUTPUT.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT}")
    for item in enumeration:
        print(
            f"pulse={item['pulse']} solutions={item['solutions']}"
        )


if __name__ == "__main__":
    main()
