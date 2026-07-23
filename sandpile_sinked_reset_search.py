#!/usr/bin/env python3
"""Search tiny open-boundary grids for exact-reset parity crossovers.

The finite n x n grid has threshold four; missing neighbors are sinks.  If L
is its reduced toppling matrix, a pulse p at x resets the all-three
configuration exactly when p L^{-1} e_x is integral.  Its entries are then
the exact toppling counts.  This script does the linear algebra over
fractions, enumerates cyclically alternating boundary terminals, and confirms
the best result by legal stabilization.
"""

from __future__ import annotations

from collections import deque
from fractions import Fraction
from itertools import combinations
from math import gcd


def lcm(a: int, b: int) -> int:
    return a // gcd(a, b) * b


def grid_laplacian(n: int) -> list[list[Fraction]]:
    size = n * n
    matrix = [[Fraction(0) for _ in range(size)] for _ in range(size)]
    for row in range(n):
        for column in range(n):
            site = row * n + column
            matrix[site][site] = Fraction(4)
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                rr, cc = row + dr, column + dc
                if 0 <= rr < n and 0 <= cc < n:
                    matrix[site][rr * n + cc] = Fraction(-1)
    return matrix


def inverse(matrix: list[list[Fraction]]) -> list[list[Fraction]]:
    size = len(matrix)
    augmented = [
        row[:] + [Fraction(int(i == j)) for j in range(size)]
        for i, row in enumerate(matrix)
    ]
    for column in range(size):
        pivot = next(
            row for row in range(column, size)
            if augmented[row][column]
        )
        augmented[column], augmented[pivot] = (
            augmented[pivot],
            augmented[column],
        )
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(size):
            if row == column or not augmented[row][column]:
                continue
            scale = augmented[row][column]
            augmented[row] = [
                left - scale * right
                for left, right in zip(
                    augmented[row], augmented[column], strict=True
                )
            ]
    return [row[size:] for row in augmented]


def perimeter(n: int) -> list[int]:
    """Clockwise perimeter, with each boundary site appearing once."""
    if n == 1:
        return [0]
    result = [column for column in range(n)]
    result += [row * n + n - 1 for row in range(1, n)]
    result += [(n - 1) * n + column for column in range(n - 2, -1, -1)]
    result += [row * n for row in range(n - 2, 0, -1)]
    return result


def integral_column(
    inv: list[list[Fraction]], site: int
) -> tuple[int, list[int]]:
    pulse = 1
    for row in inv:
        pulse = lcm(pulse, row[site].denominator)
    return pulse, [int(row[site] * pulse) for row in inv]


def legal_stabilize(
    n: int, input_site: int, pulse: int
) -> tuple[list[int], list[int]]:
    state = [3] * (n * n)
    odometer = [0] * (n * n)
    state[input_site] += pulse
    queue = deque([input_site])
    queued = [False] * (n * n)
    queued[input_site] = True
    while queue:
        site = queue.popleft()
        queued[site] = False
        amount = state[site] // 4
        if amount == 0:
            continue
        state[site] -= 4 * amount
        odometer[site] += amount
        row, column = divmod(site, n)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr, cc = row + dr, column + dc
            if 0 <= rr < n and 0 <= cc < n:
                neighbor = rr * n + cc
                state[neighbor] += amount
                if state[neighbor] >= 4 and not queued[neighbor]:
                    queued[neighbor] = True
                    queue.append(neighbor)
    return state, odometer


def search(n: int) -> list[tuple[int, tuple[int, int, int, int], tuple]]:
    inv = inverse(grid_laplacian(n))
    boundary = perimeter(n)
    columns = {site: integral_column(inv, site) for site in boundary}
    hits = []
    for indices in combinations(range(len(boundary)), 4):
        a, b, c, d = (boundary[index] for index in indices)
        pa, ua0 = columns[a]
        pb, ub0 = columns[b]
        pulse = lcm(pa, pb)
        ua = [value * (pulse // pa) for value in ua0]
        ub = [value * (pulse // pb) for value in ub0]
        table = ((ua[c], ua[d]), (ub[c], ub[d]))
        if (
            table[0][0] % 2 == 1
            and table[0][1] % 2 == 0
            and table[1][0] % 2 == 0
            and table[1][1] % 2 == 1
        ):
            hits.append((pulse, (a, b, c, d), table))
    hits.sort()
    if hits:
        pulse, terminals, table = hits[0]
        for input_site in terminals[:2]:
            final, odometer = legal_stabilize(n, input_site, pulse)
            expected_pulse, base = columns[input_site]
            expected = [
                value * (pulse // expected_pulse) for value in base
            ]
            assert final == [3] * (n * n)
            assert odometer == expected
        assert table == (
            (columns[terminals[0]][1][terminals[2]]
             * (pulse // columns[terminals[0]][0]),
             columns[terminals[0]][1][terminals[3]]
             * (pulse // columns[terminals[0]][0])),
            (columns[terminals[1]][1][terminals[2]]
             * (pulse // columns[terminals[1]][0]),
             columns[terminals[1]][1][terminals[3]]
             * (pulse // columns[terminals[1]][0])),
        )
    return hits


def coordinate(n: int, site: int) -> tuple[int, int]:
    return divmod(site, n)


def main() -> None:
    for n in range(2, 7):
        hits = search(n)
        if not hits:
            print(f"n={n}: no cyclic-boundary exact-reset parity crossover")
            continue
        pulse, terminals, table = hits[0]
        print(
            f"n={n}: hits={len(hits)} minimum_pulse={pulse} "
            f"terminals={tuple(coordinate(n, q) for q in terminals)} "
            f"single-input-output-matrix={table}"
        )


if __name__ == "__main__":
    main()
