#!/usr/bin/env python3
"""DEPRECATED sink-boundary prototype; do not use for ordinary Z^2 claims.

This early prototype omits the one-cell residual halo and replays on a sink
boundary.  It is retained only to document the audit trail.  The corrected
ordinary-infinite-lattice formulation is
``sandpile_linear_odometer_milp_z2.py``.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import random

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from sandpile_crossing_search import stabilize


@dataclass(frozen=True)
class Layout:
    area: int
    eta: np.ndarray
    u: np.ndarray
    v: np.ndarray
    ru: np.ndarray
    rv: np.ndarray
    zero: np.ndarray
    up: np.ndarray
    down: np.ndarray
    vp: np.ndarray
    vdown: np.ndarray
    parity: np.ndarray
    count: int


def layout_for(area: int) -> Layout:
    cursor = 0

    def take(count: int) -> np.ndarray:
        nonlocal cursor
        result = np.arange(cursor, cursor + count)
        cursor += count
        return result

    return Layout(
        area=area,
        eta=take(area),
        u=take(area),
        v=take(area),
        ru=take(area),
        rv=take(area),
        zero=take(area),
        up=take(area),
        down=take(area),
        vp=take(area),
        vdown=take(area),
        parity=take(4),
        count=cursor,
    )


class Constraints:
    def __init__(self, variable_count: int) -> None:
        self.variable_count = variable_count
        self.rows: list[int] = []
        self.columns: list[int] = []
        self.data: list[float] = []
        self.lower: list[float] = []
        self.upper: list[float] = []

    def add(
        self,
        terms: dict[int, float],
        lower: float,
        upper: float,
    ) -> None:
        row = len(self.lower)
        for column, coefficient in terms.items():
            if coefficient:
                self.rows.append(row)
                self.columns.append(column)
                self.data.append(coefficient)
        self.lower.append(lower)
        self.upper.append(upper)

    def equality(self, terms: dict[int, float], value: float) -> None:
        self.add(terms, value, value)

    def build(self) -> LinearConstraint:
        matrix = coo_matrix(
            (self.data, (self.rows, self.columns)),
            shape=(len(self.lower), self.variable_count),
        ).tocsr()
        return LinearConstraint(matrix, self.lower, self.upper)


def neighbors(position: int, n: int) -> tuple[int, ...]:
    row, column = divmod(position, n)
    result = []
    for delta_row, delta_column in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        neighbor_row = row + delta_row
        neighbor_column = column + delta_column
        if 0 <= neighbor_row < n and 0 <= neighbor_column < n:
            result.append(neighbor_row * n + neighbor_column)
    return tuple(result)


def numeric_stabilize(
    eta: np.ndarray,
    n: int,
    north: int,
    west: int,
    pulse: int,
    a: int,
    b: int,
) -> tuple[np.ndarray, np.ndarray]:
    board = eta.reshape((n, n)).astype(np.int64)
    additions = []
    if a:
        additions.append((divmod(north, n), a * pulse))
    if b:
        additions.append((divmod(west, n), b * pulse))
    odometer = stabilize(board, tuple(additions)).astype(np.int64)
    initial = board.copy()
    initial[divmod(north, n)] += a * pulse
    initial[divmod(west, n)] += b * pulse
    laplacian = 4 * odometer.copy()
    laplacian[1:, :] -= odometer[:-1, :]
    laplacian[:-1, :] -= odometer[1:, :]
    laplacian[:, 1:] -= odometer[:, :-1]
    laplacian[:, :-1] -= odometer[:, 1:]
    return odometer.ravel(), (initial - laplacian).ravel()


def solve_once(args: argparse.Namespace, seed: int) -> dict[str, object]:
    n = args.size
    area = n * n
    layout = layout_for(area)
    middle = n // 2
    inset = args.inset
    if not (0 <= inset < n // 2):
        raise ValueError("--inset must satisfy 0 <= inset < size // 2")
    north = inset * n + middle
    west = middle * n + inset
    south = (n - 1 - inset) * n + middle
    east = middle * n + n - 1 - inset
    if args.target_row is not None or args.target_column is not None:
        if args.target_row is None or args.target_column is None:
            raise ValueError("--target-row and --target-column must be used together")
        if not (
            0 <= args.target_row < n and 0 <= args.target_column < n
        ):
            raise ValueError("target coordinates must lie in the grid")
        south = args.target_row * n + args.target_column
    ports = (north, west, south, east)
    constraints = Constraints(layout.count)

    lower = np.full(layout.count, -np.inf)
    upper = np.full(layout.count, np.inf)
    lower[layout.eta], upper[layout.eta] = 0, 3
    lower[layout.u], upper[layout.u] = 0, args.max_odometer
    lower[layout.v], upper[layout.v] = 0, args.max_odometer
    lower[layout.ru], upper[layout.ru] = (
        -args.max_residual,
        args.max_residual,
    )
    lower[layout.rv], upper[layout.rv] = (
        -args.max_residual,
        args.max_residual,
    )
    for selector in (
        layout.zero,
        layout.up,
        layout.down,
        layout.vp,
        layout.vdown,
    ):
        lower[selector], upper[selector] = 0, 1
    lower[layout.parity] = 0
    upper[layout.parity] = args.max_odometer // 2

    for position in range(area):
        row_u = {
            int(layout.ru[position]): 1,
            int(layout.u[position]): 4,
        }
        row_v = {
            int(layout.rv[position]): 1,
            int(layout.v[position]): 4,
        }
        for neighbor in neighbors(position, n):
            row_u[int(layout.u[neighbor])] = -1
            row_v[int(layout.v[neighbor])] = -1
        if not (args.free_source_laplacian and position == north):
            constraints.equality(
                row_u,
                args.pulse if position == north else 0,
            )
        constraints.equality(
            row_v,
            0 if args.single_channel else (
                args.pulse if position == west else 0
            ),
        )
        if not args.allow_overlap:
            selectors = (
                layout.zero[position],
                layout.up[position],
                layout.down[position],
                layout.vp[position],
                layout.vdown[position],
            )
            constraints.equality(
                {int(selector): 1 for selector in selectors},
                1,
            )
            constraints.equality(
                {
                    int(layout.ru[position]): 1,
                    int(layout.up[position]): -1,
                    int(layout.down[position]): 1,
                },
                0,
            )
            constraints.equality(
                {
                    int(layout.rv[position]): 1,
                    int(layout.vp[position]): -1,
                    int(layout.vdown[position]): 1,
                },
                0,
            )
            # eta <= 3 * (1 - rising)
            constraints.add(
                {
                    int(layout.eta[position]): 1,
                    int(layout.up[position]): 3,
                    int(layout.vp[position]): 3,
                },
                -np.inf,
                3,
            )
            # eta >= 3 * falling
            constraints.add(
                {
                    int(layout.eta[position]): 1,
                    int(layout.down[position]): -3,
                    int(layout.vdown[position]): -3,
                },
                0,
                np.inf,
            )

    if args.zero_halo:
        if inset < 1:
            raise ValueError("--zero-halo requires --inset >= 1")
        # This turns the finite-array calculation into an exact calculation
        # on ordinary Z^2, rather than a sink-boundary approximation.  Both
        # response odometers vanish on the outer ring.  Consequently their
        # support is separated from the omitted exterior by one zero layer;
        # the Laplacian equations on that layer account for every grain
        # emitted by the active region, and all still-more-exterior
        # Laplacian/residual values are identically zero.
        for row in range(n):
            for column in range(n):
                if row in (0, n - 1) or column in (0, n - 1):
                    position = row * n + column
                    constraints.equality({int(layout.u[position]): 1}, 0)
                    constraints.equality({int(layout.v[position]): 1}, 0)

    if args.symmetric:
        for row in range(n):
            for column in range(row + 1, n):
                left = row * n + column
                right = column * n + row
                constraints.equality(
                    {
                        int(layout.eta[left]): 1,
                        int(layout.eta[right]): -1,
                    },
                    0,
                )
                constraints.equality(
                    {
                        int(layout.u[left]): 1,
                        int(layout.v[right]): -1,
                    },
                    0,
                )
                constraints.equality(
                    {
                        int(layout.v[left]): 1,
                        int(layout.u[right]): -1,
                    },
                    0,
                )

    output_values = (
        layout.u[south],
        layout.u[east],
        layout.v[south],
        layout.v[east],
    )
    parity_offsets = (1, 0, 0, 1)
    if args.output_pattern == "cross":
        selected_outputs = range(4)
    elif args.output_pattern == "u-straight":
        selected_outputs = (0,)
    elif args.output_pattern == "u-straight-cross-even":
        selected_outputs = (0, 1)
    elif args.output_pattern == "none":
        selected_outputs = ()
    else:
        raise ValueError(f"unknown output pattern: {args.output_pattern}")
    if args.no_parity:
        selected_outputs = ()
    for output_number in selected_outputs:
        value_index = output_values[output_number]
        parity_variable = layout.parity[output_number]
        offset = parity_offsets[output_number]
        if output_number == 0 and args.target_value is not None:
            constraints.equality(
                {int(value_index): 1},
                args.target_value,
            )
        else:
            constraints.equality(
                {int(value_index): 1, int(parity_variable): -2},
                offset,
            )
    if selected_outputs:
        if args.canonical_outputs:
            for value_index, target in zip(output_values, (1, 2, 2, 1)):
                constraints.equality(
                    {int(value_index): 1},
                    target,
                )

    if not args.no_start:
        # A nonzero response must start at the only externally modified cell.
        for a in range(3):
            for b in range(4):
                constraints.add(
                    {
                        int(layout.eta[north]): 1,
                        int(layout.ru[north]): a,
                        int(layout.rv[north]): b,
                    },
                    4 - args.pulse,
                    np.inf,
                )
        if not args.single_channel:
            for a in range(4):
                for b in range(3):
                    constraints.add(
                        {
                            int(layout.eta[west]): 1,
                            int(layout.ru[west]): a,
                            int(layout.rv[west]): b,
                        },
                        4 - args.pulse,
                        np.inf,
                    )

    rng = random.Random(seed)
    objective = np.zeros(layout.count)
    # Primarily minimize activity; tiny random integer perturbations expose
    # different feasible extreme points across trials.
    for position in range(area):
        objective[layout.u[position]] = 100 + rng.randrange(11)
        objective[layout.v[position]] = 100 + rng.randrange(11)
        objective[layout.eta[position]] = rng.randrange(3)
        objective[layout.up[position]] = rng.randrange(3)
        objective[layout.down[position]] = rng.randrange(3)
        objective[layout.vp[position]] = rng.randrange(3)
        objective[layout.vdown[position]] = rng.randrange(3)

    result = milp(
        objective,
        integrality=(
            np.zeros(layout.count)
            if args.continuous
            else np.ones(layout.count)
        ),
        bounds=Bounds(lower, upper),
        constraints=constraints.build(),
        options={"time_limit": args.timeout, "presolve": True},
    )
    if result.x is None:
        return {
            "seed": seed,
            "status": int(result.status),
            "message": result.message,
        }

    solution = np.rint(result.x).astype(np.int64)
    eta = solution[layout.eta]
    u = solution[layout.u]
    v = solution[layout.v]
    ru = solution[layout.ru]
    rv = solution[layout.rv]
    legal = True
    failure: tuple[int, int] | None = None
    for a in range(4):
        for b in (range(1) if args.single_channel else range(4)):
            actual_odometer, actual_final = numeric_stabilize(
                eta, n, north, west, args.pulse, a, b
            )
            expected_odometer = a * u + b * v
            expected_final = eta + a * ru + b * rv
            if not (
                np.array_equal(actual_odometer, expected_odometer)
                and np.array_equal(actual_final, expected_final)
            ):
                legal = False
                failure = (a, b)
                break
        if not legal:
            break

    grid = lambda values: values.reshape((n, n)).tolist()
    return {
        "seed": seed,
        "status": int(result.status),
        "message": result.message,
        "legal": legal,
        "failure": failure,
        "objective": float(result.fun),
        "output_matrix": [
            int(u[south]),
            int(u[east]),
            int(v[south]),
            int(v[east]),
        ],
        "eta": grid(eta),
        "u": grid(u),
        "v": grid(v),
        "ru": grid(ru),
        "rv": grid(rv),
        "ports": ports,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=5)
    parser.add_argument("--inset", type=int, default=0)
    parser.add_argument("--target-row", type=int)
    parser.add_argument("--target-column", type=int)
    parser.add_argument("--target-value", type=int)
    parser.add_argument("--pulse", type=int, default=4)
    parser.add_argument("--max-odometer", type=int, default=3)
    parser.add_argument("--max-residual", type=int, default=1)
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--symmetric", action="store_true")
    parser.add_argument("--canonical-outputs", action="store_true")
    parser.add_argument("--no-parity", action="store_true")
    parser.add_argument(
        "--output-pattern",
        choices=("cross", "u-straight", "u-straight-cross-even", "none"),
        default="cross",
    )
    parser.add_argument("--no-start", action="store_true")
    parser.add_argument("--allow-overlap", action="store_true")
    parser.add_argument("--zero-halo", action="store_true")
    parser.add_argument("--single-channel", action="store_true")
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--free-source-laplacian", action="store_true")
    args = parser.parse_args()

    for trial in range(args.trials):
        result = solve_once(args, args.seed + trial)
        print(result, flush=True)
        if result.get("legal"):
            print("LEGAL LINEAR JUNCTION FOUND", flush=True)
            return


if __name__ == "__main__":
    main()
