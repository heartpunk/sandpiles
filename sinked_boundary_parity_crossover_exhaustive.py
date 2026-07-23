#!/usr/bin/env python3
"""Exact boundary-port enumeration for resetting sandpile crossovers.

The model is the n by n square grid with threshold four and every off-grid
edge wired to a sink.  The background is the maximal stable state (all 3).

All arithmetic is exact.  We invert the reduced Laplacian over Fraction,
derive each site's least reset pulse from an adjugate column, and enumerate
every ordered quadruple of distinct boundary ports whose channel endpoints
alternate around the boundary, in both cyclic orientations.
"""

from __future__ import annotations

import itertools
import json
from collections import Counter
from fractions import Fraction
from math import gcd, lcm
from pathlib import Path


OUTPUT = Path("sinked_boundary_parity_crossover_exhaustive.json")
DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def grid_laplacian(side: int) -> list[list[int]]:
    site_count = side * side
    result = [[0 for _ in range(site_count)] for _ in range(site_count)]
    for row in range(side):
        for column in range(side):
            site = row * side + column
            result[site][site] = 4
            for delta_row, delta_column in DIRECTIONS:
                next_row = row + delta_row
                next_column = column + delta_column
                if 0 <= next_row < side and 0 <= next_column < side:
                    neighbor = next_row * side + next_column
                    result[site][neighbor] = -1
    return result


def bareiss_determinant(matrix: list[list[int]]) -> int:
    """Fraction-free exact determinant."""
    work = [row[:] for row in matrix]
    size = len(work)
    previous_pivot = 1
    sign = 1
    if size == 1:
        return work[0][0]
    for column in range(size - 1):
        if work[column][column] == 0:
            pivot_row = next(
                row
                for row in range(column + 1, size)
                if work[row][column] != 0
            )
            work[column], work[pivot_row] = (
                work[pivot_row],
                work[column],
            )
            sign = -sign
        pivot = work[column][column]
        for row in range(column + 1, size):
            for next_column in range(column + 1, size):
                numerator = (
                    work[row][next_column] * pivot
                    - work[row][column] * work[column][next_column]
                )
                if numerator % previous_pivot:
                    raise AssertionError("Bareiss division was not exact")
                work[row][next_column] = numerator // previous_pivot
            work[row][column] = 0
        previous_pivot = pivot
    return sign * work[-1][-1]


def exact_inverse(matrix: list[list[int]]) -> list[list[Fraction]]:
    """Gauss-Jordan inverse over the rational numbers."""
    size = len(matrix)
    work = [
        [Fraction(value) for value in row]
        + [Fraction(int(row_number == column)) for column in range(size)]
        for row_number, row in enumerate(matrix)
    ]
    for column in range(size):
        pivot_row = next(
            row
            for row in range(column, size)
            if work[row][column]
        )
        if pivot_row != column:
            work[column], work[pivot_row] = (
                work[pivot_row],
                work[column],
            )
        pivot = work[column][column]
        work[column] = [value / pivot for value in work[column]]
        for row in range(size):
            if row == column:
                continue
            multiplier = work[row][column]
            if multiplier:
                work[row] = [
                    value - multiplier * pivot_value
                    for value, pivot_value in zip(
                        work[row], work[column]
                    )
                ]
    return [row[size:] for row in work]


def matrix_vector(
    matrix: list[list[int]],
    vector: list[int],
) -> list[int]:
    return [
        sum(value * vector[column] for column, value in enumerate(row))
        for row in matrix
    ]


def boundary_cycle(side: int) -> list[tuple[int, int]]:
    """Boundary sites once each, clockwise from the northwest corner."""
    return (
        [(0, column) for column in range(side)]
        + [(row, side - 1) for row in range(1, side)]
        + [
            (side - 1, column)
            for column in range(side - 2, -1, -1)
        ]
        + [(row, 0) for row in range(side - 2, 0, -1)]
    )


def adjugate_column(
    inverse: list[list[Fraction]],
    determinant: int,
    site: int,
) -> list[int]:
    result: list[int] = []
    for row in range(len(inverse)):
        value = determinant * inverse[row][site]
        if value.denominator != 1:
            raise AssertionError("det(L) L^-1 was not integral")
        result.append(value.numerator)
    return result


def reset_order(determinant: int, adjugate: list[int]) -> int:
    common_divisor = determinant
    for value in adjugate:
        common_divisor = gcd(common_divisor, abs(value))
    return determinant // common_divisor


def integer_green_column(
    inverse: list[list[Fraction]],
    input_site: int,
    pulse: int,
) -> list[int]:
    result: list[int] = []
    for row in range(len(inverse)):
        value = pulse * inverse[row][input_site]
        if value.denominator != 1:
            raise AssertionError("pulse is not a reset period")
        result.append(value.numerator)
    return result


def reshape(vector: list[int], side: int) -> list[list[int]]:
    return [
        vector[row * side : (row + 1) * side]
        for row in range(side)
    ]


def enumerate_side(side: int) -> dict[str, object]:
    laplacian = grid_laplacian(side)
    determinant = bareiss_determinant(laplacian)
    inverse = exact_inverse(laplacian)
    boundary = boundary_cycle(side)
    boundary_sites = [row * side + column for row, column in boundary]
    adjugates = [
        adjugate_column(inverse, determinant, site)
        for site in boundary_sites
    ]
    orders = [
        reset_order(determinant, column)
        for column in adjugates
    ]

    solutions: list[list[object]] = []
    pulse_histogram: Counter[int] = Counter()
    boundary_count = len(boundary)
    for orientation_name, direction in (
        ("clockwise", 1),
        ("counterclockwise", -1),
    ):
        for a_index in range(boundary_count):
            for first, second, third in itertools.combinations(
                range(1, boundary_count), 3
            ):
                b_index = (a_index + direction * first) % boundary_count
                c_index = (a_index + direction * second) % boundary_count
                d_index = (a_index + direction * third) % boundary_count
                pulse = lcm(orders[a_index], orders[b_index])
                a_site = boundary_sites[a_index]
                b_site = boundary_sites[b_index]
                c_site = boundary_sites[c_index]
                d_site = boundary_sites[d_index]
                rational_responses = (
                    pulse * inverse[c_site][a_site],
                    pulse * inverse[c_site][b_site],
                    pulse * inverse[d_site][a_site],
                    pulse * inverse[d_site][b_site],
                )
                if any(value.denominator != 1 for value in rational_responses):
                    raise AssertionError("common reset pulse was nonintegral")
                responses = tuple(
                    value.numerator for value in rational_responses
                )
                if tuple(value & 1 for value in responses) != (1, 0, 0, 1):
                    continue
                pulse_histogram[pulse] += 1
                solutions.append(
                    [
                        orientation_name,
                        a_index,
                        b_index,
                        c_index,
                        d_index,
                        pulse,
                    ]
                )

    total_quadruples = (
        2
        * boundary_count
        * len(list(itertools.combinations(range(1, boundary_count), 3)))
    )
    if len(solutions) + (
        total_quadruples - len(solutions)
    ) != total_quadruples:
        raise AssertionError("enumeration accounting failed")

    canonical_witness = None
    if solutions:
        chosen = min(
            solutions,
            key=lambda item: (
                item[5],
                item[0] != "clockwise",
                item[1],
                item[2],
                item[3],
                item[4],
            ),
        )
        _, a_index, b_index, c_index, d_index, pulse = chosen
        a_site = boundary_sites[a_index]
        b_site = boundary_sites[b_index]
        c_site = boundary_sites[c_index]
        d_site = boundary_sites[d_index]
        u_a = integer_green_column(inverse, a_site, pulse)
        u_b = integer_green_column(inverse, b_site, pulse)
        expected_a = [0] * (side * side)
        expected_b = [0] * (side * side)
        expected_a[a_site] = pulse
        expected_b[b_site] = pulse
        if matrix_vector(laplacian, u_a) != expected_a:
            raise AssertionError("A witness failed L u = p e_A")
        if matrix_vector(laplacian, u_b) != expected_b:
            raise AssertionError("B witness failed L u = p e_B")
        response_matrix = [
            [u_a[c_site], u_b[c_site]],
            [u_a[d_site], u_b[d_site]],
        ]
        if [
            [value & 1 for value in row]
            for row in response_matrix
        ] != [[1, 0], [0, 1]]:
            raise AssertionError("canonical witness parity failed")
        canonical_witness = {
            "solution_record": chosen,
            "ports": {
                "A_input": list(boundary[a_index]),
                "B_input": list(boundary[b_index]),
                "C_output_for_A": list(boundary[c_index]),
                "D_output_for_B": list(boundary[d_index]),
            },
            "pulse": pulse,
            "input_reset_orders": {
                "A": orders[a_index],
                "B": orders[b_index],
            },
            "output_response_matrix_rows_C_D_columns_A_B": response_matrix,
            "output_response_matrix_mod_2": [[1, 0], [0, 1]],
            "odometer_A": reshape(u_a, side),
            "odometer_B": reshape(u_b, side),
            "odometer_both": reshape(
                [a_value + b_value for a_value, b_value in zip(u_a, u_b)],
                side,
            ),
            "exact_laplacian_checks": [
                "L * odometer_A = pulse * e_A",
                "L * odometer_B = pulse * e_B",
            ],
        }

    return {
        "side_length": side,
        "site_count": side * side,
        "boundary_cycle_clockwise": [list(site) for site in boundary],
        "boundary_site_count": boundary_count,
        "reduced_laplacian_determinant": determinant,
        "boundary_reset_orders": [
            {"position": list(position), "least_reset_pulse": order}
            for position, order in zip(boundary, orders)
        ],
        "ordered_alternating_quadruples_checked": total_quadruples,
        "orientation_convention": (
            "Every labeled A,B,C,D tuple with distinct boundary sites "
            "and alternating channel endpoints is checked exactly once: "
            "A-B-C-D clockwise or A-B-C-D counterclockwise."
        ),
        "solution_count": len(solutions),
        "solution_pulse_histogram": {
            str(pulse): count
            for pulse, count in sorted(pulse_histogram.items())
        },
        "least_solution_pulse": (
            min(pulse_histogram) if pulse_histogram else None
        ),
        "canonical_witness": canonical_witness,
        "solutions_compact": solutions,
        "compact_solution_schema": [
            "orientation",
            "A_boundary_index",
            "B_boundary_index",
            "C_boundary_index",
            "D_boundary_index",
            "least_common_reset_pulse",
        ],
    }


def main() -> None:
    enumerations = [enumerate_side(side) for side in range(2, 6)]
    expected = {
        2: (8, 24),
        3: (0, None),
        4: (264, 6600),
        5: (1032, 102960),
    }
    for enumeration in enumerations:
        side = enumeration["side_length"]
        observed = (
            enumeration["solution_count"],
            enumeration["least_solution_pulse"],
        )
        if observed != expected[side]:
            raise AssertionError(
                f"n={side}: got {observed}, expected {expected[side]}"
            )

    certificate = {
        "title": (
            "Exact exhaustive classification of small resetting "
            "boundary-port parity crossovers"
        ),
        "model": {
            "graph": (
                "n by n square grid, threshold 4, every off-grid edge "
                "connected to a sink"
            ),
            "background": "maximal stable configuration: height 3 everywhere",
            "input": (
                "equal pulse p at A or B, with exact reset required"
            ),
            "readout": (
                "toppling counts at C,D modulo 2; desired response "
                "matrix is the 2 by 2 identity"
            ),
            "crossing": (
                "four distinct boundary ports with paired endpoints "
                "A-C and B-D alternating in cyclic boundary order"
            ),
        },
        "exact_method": {
            "laplacian": "L = 4I - grid adjacency",
            "adjugate_formula": (
                "L^-1 e_x = adj(L)e_x / det(L). If g_x is that "
                "integer adjugate column, the least exact-reset pulse "
                "at x is q_x = det(L) / gcd(det(L), every entry of g_x)."
            ),
            "common_pulse": (
                "For inputs A,B the least common exact-reset pulse is "
                "q = lcm(q_A,q_B). Every common reset pulse is m q."
            ),
            "parity_filter": (
                "At q compute R=[[qG(C,A),qG(C,B)],"
                "[qG(D,A),qG(D,B)]] mod 2. Odd multiples preserve R; "
                "even multiples make it zero. Therefore a tuple works "
                "for some common reset pulse iff it works at q."
            ),
            "actual_odometer_proof": (
                "u=q L^-1 e_x is nonnegative and algebraically resets "
                "all-3. Least action gives the true odometer v<=u. "
                "Then w=u-v>=0 and stability gives Lw<=0. The reduced-"
                "Laplacian maximum principle forces w=0, hence v=u."
            ),
            "arithmetic": (
                "Pure Python exact integers/Fraction; determinant by "
                "fraction-free Bareiss elimination and inverse by "
                "rational Gauss-Jordan elimination."
            ),
        },
        "enumerations": enumerations,
        "lexicographic_optimum": {
            "objective": (
                "First minimize square side n, then pulse p, among "
                "four-distinct-boundary-port equal-pulse exact-reset "
                "parity crossovers."
            ),
            "side_length": 2,
            "pulse": 24,
            "reason_no_smaller_side": (
                "n=1 has only one boundary site and cannot supply four "
                "distinct ports."
            ),
            "classification_at_optimum": (
                "The 2x2 boundary has one four-site set. All eight "
                "alternating labelings (four cyclic starts times two "
                "orientations) work, and adjugate denominators force "
                "every input reset pulse to be a multiple of 24."
            ),
        },
        "general_theorem": (
            "For any finite dissipative graph sandpile with reduced "
            "toppling matrix L and maximal stable background "
            "s_v=L_vv-1, an equal-pulse, exactly resetting two-input "
            "parity crossover at fixed ports exists iff the integer "
            "Green columns at q=lcm(ord_coker(L)(e_A),"
            "ord_coker(L)(e_B)) have the desired 2x2 output matrix "
            "modulo 2. If it exists, q is the least pulse and precisely "
            "its odd multiples work."
        ),
        "scope_caveat": (
            "The perimeter is a sink. This classifies resetting boundary "
            "modules, not internally tileable sink-free gadgets."
        ),
    }
    OUTPUT.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT}")
    for enumeration in enumerations:
        print(
            "n={side_length}: checked={ordered_alternating_quadruples_checked} "
            "solutions={solution_count} least_p={least_solution_pulse}".format(
                **enumeration
            )
        )


if __name__ == "__main__":
    main()
