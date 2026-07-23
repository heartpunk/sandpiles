#!/usr/bin/env python3
"""Generate and independently check the integrated parity-crossover witness.

The output is a JSON certificate containing the finite background, legal
toppling traces, odometers, final configurations, extension tests, a bend
test, and the complete input-amplitude table for a,b in {0,1,2,3}.
"""

from __future__ import annotations

from collections import deque
import json
from pathlib import Path

import numpy as np

from sandpile_crossing_search import stabilize
from sandpile_parity_crossing_search import stabilize_flat


OUTPUT = Path("integrated_parity_crossover_certificate.json")

GATE = np.array(
    [
        [3, 2, 3, 2, 3, 2],
        [3, 0, 0, 3, 2, 2],
        [2, 2, 3, 3, 3, 3],
        [3, 3, 3, 1, 3, 3],
        [3, 3, 3, 2, 0, 1],
        [1, 2, 3, 3, 1, 0],
    ],
    dtype=np.int64,
)


def straight_board(
    wire_length: int, padding: int = 3
) -> tuple[np.ndarray, dict[str, tuple[int, int]]]:
    size = 6 + wire_length + 2 * padding
    board = np.zeros((size, size), dtype=np.int64)
    offset = padding
    board[offset : offset + 6, offset : offset + 6] = GATE
    board[
        offset + 6 : offset + 6 + wire_length,
        offset + 1 : offset + 6,
    ] = 3
    board[
        offset + 1 : offset + 6,
        offset + 6 : offset + 6 + wire_length,
    ] = 3
    ports = {
        "north_input": (offset + 2, offset + 3),
        "west_input": (offset + 3, offset + 2),
        "south_output": (
            offset + 6 + wire_length - 3,
            offset + 3,
        ),
        "east_output": (
            offset + 3,
            offset + 6 + wire_length - 3,
        ),
    }
    return board, ports


def additions_for(
    ports: dict[str, tuple[int, int]], north: int, west: int
) -> tuple[tuple[tuple[int, int], int], ...]:
    additions: list[tuple[tuple[int, int], int]] = []
    if north:
        additions.append((ports["north_input"], north))
    if west:
        additions.append((ports["west_input"], west))
    return tuple(additions)


def legal_stabilization(
    base: np.ndarray,
    additions: tuple[tuple[tuple[int, int], int], ...],
) -> tuple[np.ndarray, np.ndarray, list[list[int]]]:
    """Topple one lexicographically first unstable site at a time."""
    state = base.astype(np.int64, copy=True)
    for position, amount in additions:
        state[position] += amount

    rows, columns = state.shape
    odometer = np.zeros_like(state)
    trace: list[list[int]] = []
    while True:
        unstable = np.argwhere(state >= 4)
        if not len(unstable):
            break
        row, column = (int(value) for value in unstable[0])
        if state[row, column] < 4:
            raise AssertionError("trace attempted an illegal toppling")
        trace.append([row, column])
        state[row, column] -= 4
        odometer[row, column] += 1
        if row:
            state[row - 1, column] += 1
        if row + 1 < rows:
            state[row + 1, column] += 1
        if column:
            state[row, column - 1] += 1
        if column + 1 < columns:
            state[row, column + 1] += 1
    return state, odometer, trace


def independently_check(
    base: np.ndarray,
    additions: tuple[tuple[tuple[int, int], int], ...],
    final: np.ndarray,
    odometer: np.ndarray,
) -> None:
    numpy_odometer = stabilize(base, additions)
    if not np.array_equal(numpy_odometer, odometer):
        raise AssertionError("legal trace and NumPy stabilizer disagree")

    size = base.shape[0]
    flat_additions = tuple(
        (position[0] * size + position[1], amount)
        for position, amount in additions
    )
    flat_odometer = np.array(
        stabilize_flat(
            tuple(int(value) for value in base.flat),
            size,
            flat_additions,
        ),
        dtype=np.int64,
    ).reshape(base.shape)
    if not np.array_equal(flat_odometer, odometer):
        raise AssertionError("flat and NumPy stabilizers disagree")

    reconstructed = base.astype(np.int64, copy=True)
    for position, amount in additions:
        reconstructed[position] += amount
    reconstructed -= 4 * odometer
    reconstructed[:-1, :] += odometer[1:, :]
    reconstructed[1:, :] += odometer[:-1, :]
    reconstructed[:, :-1] += odometer[:, 1:]
    reconstructed[:, 1:] += odometer[:, :-1]
    if not np.array_equal(reconstructed, final):
        raise AssertionError("Laplacian reconstruction disagrees")
    if int(final.min()) < 0 or int(final.max()) > 3:
        raise AssertionError("final configuration is not stable")
    if np.any(odometer[0, :]) or np.any(odometer[-1, :]):
        raise AssertionError("avalanche reached the horizontal board edge")
    if np.any(odometer[:, 0]) or np.any(odometer[:, -1]):
        raise AssertionError("avalanche reached the vertical board edge")
    if int(base.sum()) + sum(amount for _, amount in additions) != int(
        final.sum()
    ):
        raise AssertionError("mass was not conserved")


def output_counts(
    odometer: np.ndarray, ports: dict[str, tuple[int, int]]
) -> list[int]:
    return [
        int(odometer[ports["south_output"]]),
        int(odometer[ports["east_output"]]),
    ]


def extension_tests() -> list[dict[str, object]]:
    tests: list[dict[str, object]] = []
    for length in (5, 10, 20, 50):
        board, ports = straight_board(length)
        cases: dict[str, object] = {}
        for name, north, west in (
            ("north", 1, 0),
            ("west", 0, 1),
            ("both", 1, 1),
        ):
            additions = additions_for(ports, north, west)
            odometer = stabilize(board, additions)
            cases[name] = {
                "output_counts": output_counts(odometer, ports),
                "total_topplings": int(odometer.sum()),
                "maximum_site_topplings": int(odometer.max()),
            }
        tests.append(
            {
                "wire_length": length,
                "ports": {key: list(value) for key, value in ports.items()},
                "cases": cases,
            }
        )
    return tests


def bend_test(
    vertical_length: int = 20,
    horizontal_length: int = 15,
    east_length: int = 15,
    padding: int = 3,
) -> dict[str, object]:
    size = (
        6
        + vertical_length
        + horizontal_length
        + 2 * padding
    )
    board = np.zeros((size, size), dtype=np.int64)
    offset = padding
    board[offset : offset + 6, offset : offset + 6] = GATE

    # South-going corridor.
    board[
        offset + 6 : offset + 6 + vertical_length,
        offset + 1 : offset + 6,
    ] = 3
    # Its five-by-five overlap turns east.
    turn_top = offset + 6 + vertical_length - 5
    board[
        turn_top : turn_top + 5,
        offset + 1 : offset + 1 + horizontal_length,
    ] = 3
    # Independent straight east output.
    board[
        offset + 1 : offset + 6,
        offset + 6 : offset + 6 + east_length,
    ] = 3

    ports = {
        "north_input": (offset + 2, offset + 3),
        "west_input": (offset + 3, offset + 2),
        "south_then_east_output": (
            turn_top + 2,
            offset + 1 + horizontal_length - 3,
        ),
        "east_output": (
            offset + 3,
            offset + 6 + east_length - 3,
        ),
    }
    cases: dict[str, object] = {}
    for name, north, west in (
        ("north", 1, 0),
        ("west", 0, 1),
        ("both", 1, 1),
    ):
        additions: list[tuple[tuple[int, int], int]] = []
        if north:
            additions.append((ports["north_input"], 1))
        if west:
            additions.append((ports["west_input"], 1))
        odometer = stabilize(board, tuple(additions))
        cases[name] = {
            "output_counts": [
                int(odometer[ports["south_then_east_output"]]),
                int(odometer[ports["east_output"]]),
            ],
            "total_topplings": int(odometer.sum()),
            "maximum_site_topplings": int(odometer.max()),
        }
    return {
        "vertical_length": vertical_length,
        "horizontal_length": horizontal_length,
        "east_length": east_length,
        "ports": {key: list(value) for key, value in ports.items()},
        "cases": cases,
    }


def amplitude_table(
    board: np.ndarray, ports: dict[str, tuple[int, int]]
) -> list[dict[str, object]]:
    table: list[dict[str, object]] = []
    for north in range(4):
        for west in range(4):
            additions = additions_for(ports, north, west)
            odometer = stabilize(board, additions)
            counts = output_counts(odometer, ports)
            table.append(
                {
                    "north_amplitude": north,
                    "west_amplitude": west,
                    "output_counts": counts,
                    "output_parities": [value & 1 for value in counts],
                    "target_input_parities": [north & 1, west & 1],
                    "parity_linear": [
                        value & 1 for value in counts
                    ]
                    == [north & 1, west & 1],
                    "total_topplings": int(odometer.sum()),
                }
            )
    return table


def main() -> None:
    board, ports = straight_board(5)
    cases: dict[str, object] = {}
    for name, north, west in (
        ("north", 1, 0),
        ("west", 0, 1),
        ("both", 1, 1),
    ):
        additions = additions_for(ports, north, west)
        final, odometer, trace = legal_stabilization(board, additions)
        independently_check(board, additions, final, odometer)
        cases[name] = {
            "additions": [
                {"position": list(position), "amount": amount}
                for position, amount in additions
            ],
            "output_counts": output_counts(odometer, ports),
            "output_parities": [
                value & 1 for value in output_counts(odometer, ports)
            ],
            "total_topplings": int(odometer.sum()),
            "maximum_site_topplings": int(odometer.max()),
            "legal_trace": trace,
            "odometer": odometer.tolist(),
            "final_configuration": final.tolist(),
        }

    certificate = {
        "title": "Integrated parity crossover with scalable output wires",
        "model": {
            "lattice": "2D square von Neumann lattice",
            "threshold": 4,
            "outside_background": 0,
            "semantics": (
                "A legal toppling subtracts four grains at a site and "
                "adds one grain to each orthogonal neighbor."
            ),
        },
        "status": {
            "decisive_claim": (
                "For Boolean one-grain additions at the two inputs, "
                "the south/east output odometer parities reproduce the "
                "north/west bits, and both output corridors can be "
                "extended arbitrarily."
            ),
            "composability_limit": (
                "The complete amplitude table shows that this witness is "
                "not parity-linear for arbitrary 0..3 input amplitudes; "
                "a parity-linear or resetting input interface remains open."
            ),
        },
        "gate_background_6x6": GATE.tolist(),
        "base_wire_length": 5,
        "board_shape": list(board.shape),
        "ports": {key: list(value) for key, value in ports.items()},
        "background": board.tolist(),
        "cases": cases,
        "extension_tests": extension_tests(),
        "bend_test": bend_test(),
        "amplitude_table_0_through_3": amplitude_table(board, ports),
        "verification": {
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


if __name__ == "__main__":
    main()
