#!/usr/bin/env python3
"""Pure-stdlib verifier for the finite 2x2 parity-crossover certificate.

This intentionally does not import the search code or NumPy.  It:

1. replays every recorded toppling and rejects an illegal step;
2. reconstructs and checks each final state and odometer;
3. repeats the complete 256-background search for pulses 1 through 15
   with an independent stack stabilizer; and
4. checks that no exhaustive-search avalanche reaches the padded boundary.
"""

from __future__ import annotations

import itertools
import json
from collections import deque
from pathlib import Path


CERTIFICATE = Path("finite_2x2_parity_crossover_certificate.json")
EXPECTED_COUNTS = [0] * 14 + [17]
DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def blank_matrix(size: int) -> list[list[int]]:
    return [[0 for _ in range(size)] for _ in range(size)]


def copy_matrix(matrix: list[list[int]]) -> list[list[int]]:
    return [row[:] for row in matrix]


def add_inputs(
    state: list[list[int]],
    additions: list[dict[str, object]],
) -> None:
    for addition in additions:
        row, column = addition["position"]
        state[row][column] += addition["amount"]


def topple(
    state: list[list[int]],
    row: int,
    column: int,
) -> None:
    size = len(state)
    state[row][column] -= 4
    for delta_row, delta_column in DIRECTIONS:
        next_row = row + delta_row
        next_column = column + delta_column
        if 0 <= next_row < size and 0 <= next_column < size:
            state[next_row][next_column] += 1


def replay_case(
    background: list[list[int]],
    case: dict[str, object],
) -> tuple[list[list[int]], list[list[int]]]:
    state = copy_matrix(background)
    add_inputs(state, case["additions"])
    odometer = blank_matrix(len(state))
    for step_number, (row, column) in enumerate(case["legal_trace"]):
        if state[row][column] < 4:
            raise AssertionError(
                f"illegal toppling at trace step {step_number}: "
                f"{(row, column)} has height {state[row][column]}"
            )
        topple(state, row, column)
        odometer[row][column] += 1
    if any(value >= 4 for row in state for value in row):
        raise AssertionError("recorded legal trace does not stabilize")
    return state, odometer


def stabilize(
    background: list[list[int]],
    additions: tuple[tuple[tuple[int, int], int], ...],
) -> tuple[list[list[int]], list[list[int]]]:
    """Independent LIFO/queue hybrid stabilizer."""
    state = copy_matrix(background)
    size = len(state)
    odometer = blank_matrix(size)
    pending: deque[tuple[int, int]] = deque()
    queued: set[tuple[int, int]] = set()

    for (row, column), amount in additions:
        state[row][column] += amount
    for row in range(size):
        for column in range(size):
            if state[row][column] >= 4:
                pending.append((row, column))
                queued.add((row, column))

    while pending:
        row, column = pending.pop()
        queued.discard((row, column))
        number = state[row][column] // 4
        if not number:
            continue
        state[row][column] -= 4 * number
        odometer[row][column] += number
        for delta_row, delta_column in DIRECTIONS:
            next_row = row + delta_row
            next_column = column + delta_column
            if not (0 <= next_row < size and 0 <= next_column < size):
                continue
            state[next_row][next_column] += number
            position = (next_row, next_column)
            if (
                state[next_row][next_column] >= 4
                and position not in queued
            ):
                pending.append(position)
                queued.add(position)
    return state, odometer


def boundary_zero(matrix: list[list[int]]) -> bool:
    return (
        not any(matrix[0])
        and not any(matrix[-1])
        and all(row[0] == 0 and row[-1] == 0 for row in matrix)
    )


def exhaustive_counts(
    size: int,
    padding: int,
) -> tuple[list[int], list[dict[str, object]]]:
    a_input = (padding, padding)
    b_input = (padding, padding + 1)
    d_output = (padding + 1, padding)
    c_output = (padding + 1, padding + 1)
    targets = ((1, 0), (0, 1), (1, 1))
    counts: list[int] = []
    pulse_15_solutions: list[dict[str, object]] = []

    for pulse in range(1, 16):
        count = 0
        for core in itertools.product(range(4), repeat=4):
            background = blank_matrix(size)
            for offset, value in enumerate(core):
                row = padding + offset // 2
                column = padding + offset % 2
                background[row][column] = value
            additions = (
                ((a_input, pulse),),
                ((b_input, pulse),),
                ((a_input, pulse), (b_input, pulse)),
            )
            output_counts: list[list[int]] = []
            crossing = True
            for case_additions, target in zip(additions, targets):
                final, odometer = stabilize(background, case_additions)
                if not boundary_zero(odometer):
                    raise AssertionError(
                        "exhaustive-search avalanche reached boundary"
                    )
                if any(value >= 4 for row in final for value in row):
                    raise AssertionError("independent stabilizer failed")
                outputs = [
                    odometer[c_output[0]][c_output[1]],
                    odometer[d_output[0]][d_output[1]],
                ]
                output_counts.append(outputs)
                if tuple(value & 1 for value in outputs) != target:
                    crossing = False
            if crossing:
                count += 1
                if pulse == 15:
                    pulse_15_solutions.append(
                        {
                            "core_row_major": list(core),
                            "output_counts_c_d": {
                                "a": output_counts[0],
                                "b": output_counts[1],
                                "both": output_counts[2],
                            },
                        }
                    )
        counts.append(count)
    return counts, pulse_15_solutions


def main() -> None:
    certificate = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    background = certificate["background"]
    size = certificate["model"]["finite_board_used_for_certificate"]
    padding = certificate["model"]["padding"]
    ports = certificate["core"]["ports"]
    c_output = ports["a_output_c_bottom_right"]
    d_output = ports["b_output_d_bottom_left"]
    expected_parities = {"a": [1, 0], "b": [0, 1], "both": [1, 1]}

    if len(background) != size or any(len(row) != size for row in background):
        raise AssertionError("certificate board dimensions disagree")

    for name, case in certificate["cases"].items():
        final, odometer = replay_case(background, case)
        if final != case["final_configuration"]:
            raise AssertionError(f"{name}: recorded final state disagrees")
        if odometer != case["odometer"]:
            raise AssertionError(f"{name}: recorded odometer disagrees")
        counts = [
            odometer[c_output[0]][c_output[1]],
            odometer[d_output[0]][d_output[1]],
        ]
        if counts != case["output_counts_c_d"]:
            raise AssertionError(f"{name}: recorded output counts disagree")
        if [value & 1 for value in counts] != expected_parities[name]:
            raise AssertionError(f"{name}: output parity is wrong")
        if not boundary_zero(odometer):
            raise AssertionError(f"{name}: witness reached board boundary")

    counts, solutions = exhaustive_counts(size, padding)
    if counts != EXPECTED_COUNTS:
        raise AssertionError(
            f"independent enumeration got {counts}, expected {EXPECTED_COUNTS}"
        )
    recorded_counts = [
        item["solutions"]
        for item in certificate["minimality"]["enumeration"]
    ]
    if counts != recorded_counts:
        raise AssertionError("recorded enumeration counts disagree")

    recorded_solutions = [
        {
            "core_row_major": item["core_row_major"],
            "output_counts_c_d": item["output_counts_c_d"],
        }
        for item in certificate["minimality"]["pulse_15_solutions"]
    ]
    if solutions != recorded_solutions:
        raise AssertionError("recorded pulse-15 solution list disagrees")

    print("PASS: all recorded toppling traces are legal and stabilizing")
    print("PASS: witness odometers, finals, and crossing parities agree")
    print("PASS: all 11,520 exhaustive-search avalanches stay in padding")
    print("PASS: pulse counts 1..15 are", counts)


if __name__ == "__main__":
    main()
