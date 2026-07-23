#!/usr/bin/env python3
"""Scan explicit three-arm all-3 networks for an isolated amplitude output.

The construction idea is conservation-driven: a height-3 output q with a
quiescent receiver to its east will topple exactly k times if its west, north,
and south neighbors each deliver k grains.  We therefore thicken a planar
three-arm skeleton into all-3 corridors, then carve a four-cell zero buffer
around the east receiver.
"""

from __future__ import annotations

import argparse

import numpy as np

from sandpile_crossing_search import stabilize
from sandpile_parity_wire_search import final_state_from_odometer


Coord = tuple[int, int]


def segment(start: Coord, end: Coord) -> set[Coord]:
    row, column = start
    target_row, target_column = end
    result = {(row, column)}
    while row != target_row:
        row += 1 if target_row > row else -1
        result.add((row, column))
    while column != target_column:
        column += 1 if target_column > column else -1
        result.add((row, column))
    return result


def candidate(
    height: int,
    width: int,
    middle: int,
    junction_column: int,
    output_column: int,
    detour: int,
    radius: int,
) -> tuple[np.ndarray, Coord, Coord, frozenset[Coord]]:
    output = (middle, output_column)
    skeleton: set[Coord] = set()
    skeleton |= segment(
        (middle, radius),
        (middle, output_column - 1),
    )
    skeleton |= segment(
        (middle, junction_column),
        (middle - detour, junction_column),
    )
    skeleton |= segment(
        (middle - detour, junction_column),
        (middle - detour, output_column),
    )
    skeleton |= segment(
        (middle - detour, output_column),
        (middle - 1, output_column),
    )
    skeleton |= segment(
        (middle, junction_column),
        (middle + detour, junction_column),
    )
    skeleton |= segment(
        (middle + detour, junction_column),
        (middle + detour, output_column),
    )
    skeleton |= segment(
        (middle + detour, output_column),
        (middle + 1, output_column),
    )

    core = np.zeros((height, width), dtype=np.int8)
    for row, column in skeleton:
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                rr, cc = row + dr, column + dc
                if 0 <= rr < height and 0 <= cc < width:
                    core[rr, cc] = 3

    receiver = (middle, output_column + 1)
    forbidden = frozenset(
        {
            receiver,
            (middle - 1, output_column + 1),
            (middle + 1, output_column + 1),
            (middle, output_column + 2),
        }
    )
    for position in forbidden:
        core[position] = 0
    source = (middle, 0)
    core[source] = 3
    core[output] = 3
    return core, source, output, forbidden


def scan(maximum_output_column: int, padding: int) -> None:
    best = None
    checked = 0
    for radius in (1, 2, 3):
        for output_column in range(8, maximum_output_column + 1):
            width = output_column + radius + 5
            for detour in range(4, 13):
                middle = detour + radius + 3
                height = 2 * middle + 1
                for junction_column in range(
                    radius + 2,
                    output_column - radius - 1,
                ):
                    core, source, output, forbidden = candidate(
                        height,
                        width,
                        middle,
                        junction_column,
                        output_column,
                        detour,
                        radius,
                    )
                    board = np.zeros(
                        (height + 2 * padding, width + 2 * padding),
                        dtype=np.int8,
                    )
                    board[
                        padding : padding + height,
                        padding : padding + width,
                    ] = core
                    source_global = (
                        padding + source[0],
                        padding + source[1],
                    )
                    output_global = (
                        padding + output[0],
                        padding + output[1],
                    )
                    receiver_global = (
                        padding + middle,
                        padding + output_column + 1,
                    )
                    forbidden_global = tuple(
                        (padding + row, padding + column)
                        for row, column in forbidden
                    )
                    counts = []
                    forbidden_activity = 0
                    receiver_final = []
                    boundary_activity = 0
                    for amount in (1, 2, 3):
                        odometer = stabilize(
                            board,
                            ((source_global, amount),),
                        )
                        final = final_state_from_odometer(
                            board,
                            source_global,
                            amount,
                            odometer,
                        )
                        counts.append(int(odometer[output_global]))
                        forbidden_activity += sum(
                            int(odometer[position])
                            for position in forbidden_global
                        )
                        receiver_final.append(
                            int(final[receiver_global])
                        )
                        boundary_activity += (
                            int(odometer[0, :].sum())
                            + int(odometer[-1, :].sum())
                            + int(odometer[1:-1, 0].sum())
                            + int(odometer[1:-1, -1].sum())
                        )
                    checked += 1
                    exact_error = sum(
                        abs(got - want)
                        for got, want in zip(counts, (1, 2, 3))
                    )
                    receiver_error = sum(
                        abs(got - want)
                        for got, want in zip(
                            receiver_final,
                            (1, 2, 3),
                        )
                    )
                    score = (
                        boundary_activity * 1_000_000
                        + forbidden_activity * 10_000
                        + exact_error * 1_000
                        + receiver_error
                    )
                    record = (
                        score,
                        exact_error,
                        forbidden_activity,
                        receiver_error,
                        counts,
                        receiver_final,
                        radius,
                        output_column,
                        detour,
                        junction_column,
                        core,
                    )
                    if best is None or record[0] < best[0]:
                        best = record
                        print(
                            f"checked={checked} score={score} "
                            f"counts={counts} receiver={receiver_final} "
                            f"forbidden={forbidden_activity} "
                            f"radius={radius} qcol={output_column} "
                            f"detour={detour} junction={junction_column}",
                            flush=True,
                        )
                    if (
                        exact_error == 0
                        and forbidden_activity == 0
                        and receiver_error == 0
                        and boundary_activity == 0
                    ):
                        print("ISOLATED EXACT TRIPOD FOUND", flush=True)
                        print(core, flush=True)
                        return
    assert best is not None
    print(f"NO EXACT TRIPOD in {checked} templates", flush=True)
    print(
        "best:",
        best[:-1],
        flush=True,
    )
    print(best[-1], flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--maximum-output-column", type=int, default=24)
    parser.add_argument("--padding", type=int, default=5)
    args = parser.parse_args()
    scan(args.maximum_output_column, args.padding)


if __name__ == "__main__":
    main()
