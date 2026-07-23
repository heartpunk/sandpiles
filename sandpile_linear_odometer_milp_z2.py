#!/usr/bin/env python3
"""Inverse synthesis for a full-alphabet linear parity junction on Z^2.

For two pulse responses u and v, put

    r = p delta_N + (neighbors(u) - 4 u)
    s = p delta_W + (neighbors(v) - 4 v).

If one stable eta has eta + a r + b s stable for every a,b in {0,1,2,3},
then a*u+b*v is an algebraic stabilizing vector for every input.  Pointwise
stability for the whole alphabet is exactly |r|+|s| <= 1.  This MILP
searches that finite inverse problem.  Every incumbent is then replayed by
an ordinary legal stabilizer on a padded piece of the *infinite* square
lattice; sink-boundary candidates are not accepted.

The one-cell eta/residual halo is essential: u and v are zero outside the
n-by-n core, but a boundary toppling deposits grains in that halo.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import json
import random
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


@dataclass(frozen=True)
class Layout:
    core_area: int
    ext_area: int
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


def layout_for(core_area: int, ext_area: int) -> Layout:
    cursor = 0

    def take(count: int) -> np.ndarray:
        nonlocal cursor
        result = np.arange(cursor, cursor + count)
        cursor += count
        return result

    return Layout(
        core_area=core_area,
        ext_area=ext_area,
        eta=take(ext_area),
        u=take(core_area),
        v=take(core_area),
        ru=take(ext_area),
        rv=take(ext_area),
        zero=take(ext_area),
        up=take(ext_area),
        down=take(ext_area),
        vp=take(ext_area),
        vdown=take(ext_area),
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


def legal_stabilize(
    base: np.ndarray,
    additions: tuple[tuple[int, int], ...],
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Stabilize on a padded board, returning final, odometer, legal trace."""
    side = base.shape[0]
    state = base.astype(np.int64, copy=True).ravel()
    for position, amount in additions:
        state[position] += amount
    odometer = np.zeros(side * side, dtype=np.int64)
    queue: deque[int] = deque()
    queued = np.zeros(side * side, dtype=np.bool_)
    for position in np.flatnonzero(state >= 4):
        queue.append(int(position))
        queued[position] = True
    trace: list[int] = []
    while queue:
        position = queue.popleft()
        queued[position] = False
        if state[position] < 4:
            continue
        # One toppling at a time makes the returned sequence a literal legal
        # certificate, rather than relying on bulk-toppling equivalence.
        state[position] -= 4
        odometer[position] += 1
        trace.append(position)
        row, column = divmod(position, side)
        for neighbor in (
            position - side if row else -1,
            position + side if row + 1 < side else -1,
            position - 1 if column else -1,
            position + 1 if column + 1 < side else -1,
        ):
            if neighbor < 0:
                continue
            state[neighbor] += 1
            if state[neighbor] >= 4 and not queued[neighbor]:
                queued[neighbor] = True
                queue.append(neighbor)
        if state[position] >= 4 and not queued[position]:
            queued[position] = True
            queue.append(position)
    return state.reshape((side, side)), odometer.reshape((side, side)), trace


def build_problem(args: argparse.Namespace, seed: int):
    n = args.size
    m = n + 2
    core_area = n * n
    ext_area = m * m
    layout = layout_for(core_area, ext_area)
    middle = n // 2
    core_at = lambda row, column: row * n + column
    ext_at = lambda row, column: row * m + column
    ports = {
        "north": core_at(args.inset, middle),
        "west": core_at(middle, args.inset),
        "south": core_at(n - 1 - args.inset, middle),
        "east": core_at(middle, n - 1 - args.inset),
    }
    ext_ports = {
        name: ext_at(1 + position // n, 1 + position % n)
        for name, position in ports.items()
    }
    constraints = Constraints(layout.count)

    lower = np.full(layout.count, -np.inf)
    upper = np.full(layout.count, np.inf)
    lower[layout.eta], upper[layout.eta] = 0, 3
    lower[layout.u], upper[layout.u] = 0, args.max_odometer
    lower[layout.v], upper[layout.v] = 0, args.max_odometer
    lower[layout.ru], upper[layout.ru] = -1, 1
    lower[layout.rv], upper[layout.rv] = -1, 1
    selectors = (
        layout.zero,
        layout.up,
        layout.down,
        layout.vp,
        layout.vdown,
    )
    for selector in selectors:
        lower[selector], upper[selector] = 0, 1
    lower[layout.parity] = 0
    upper[layout.parity] = args.max_odometer // 2

    def core_variable(field: np.ndarray, ext_row: int, ext_column: int):
        core_row = ext_row - 1
        core_column = ext_column - 1
        if 0 <= core_row < n and 0 <= core_column < n:
            return int(field[core_at(core_row, core_column)])
        return None

    for ext_position in range(ext_area):
        row, column = divmod(ext_position, m)
        for field, residual, source in (
            (layout.u, layout.ru, ext_ports["north"]),
            (layout.v, layout.rv, ext_ports["west"]),
        ):
            terms: dict[int, float] = {
                int(residual[ext_position]): 1,
            }
            center = core_variable(field, row, column)
            if center is not None:
                terms[center] = terms.get(center, 0) + 4
            for neighbor_row, neighbor_column in (
                (row - 1, column),
                (row + 1, column),
                (row, column - 1),
                (row, column + 1),
            ):
                neighbor = core_variable(field, neighbor_row, neighbor_column)
                if neighbor is not None:
                    terms[neighbor] = terms.get(neighbor, 0) - 1
            constraints.equality(
                terms,
                (
                    args.pulse
                    if ext_position == source
                    and not (args.single_channel and field is layout.v)
                    else 0
                ),
            )

        point_selectors = (
            layout.zero[ext_position],
            layout.up[ext_position],
            layout.down[ext_position],
            layout.vp[ext_position],
            layout.vdown[ext_position],
        )
        constraints.equality(
            {int(selector): 1 for selector in point_selectors},
            1,
        )
        constraints.equality(
            {
                int(layout.ru[ext_position]): 1,
                int(layout.up[ext_position]): -1,
                int(layout.down[ext_position]): 1,
            },
            0,
        )
        constraints.equality(
            {
                int(layout.rv[ext_position]): 1,
                int(layout.vp[ext_position]): -1,
                int(layout.vdown[ext_position]): 1,
            },
            0,
        )
        # Positive residual fixes eta=0; negative residual fixes eta=3.
        constraints.add(
            {
                int(layout.eta[ext_position]): 1,
                int(layout.up[ext_position]): 3,
                int(layout.vp[ext_position]): 3,
            },
            -np.inf,
            3,
        )
        constraints.add(
            {
                int(layout.eta[ext_position]): 1,
                int(layout.down[ext_position]): -3,
                int(layout.vdown[ext_position]): -3,
            },
            0,
            np.inf,
        )

    if args.symmetric:
        for row in range(m):
            for column in range(row + 1, m):
                left = ext_at(row, column)
                right = ext_at(column, row)
                constraints.equality(
                    {
                        int(layout.eta[left]): 1,
                        int(layout.eta[right]): -1,
                    },
                    0,
                )
        for row in range(n):
            for column in range(n):
                left = core_at(row, column)
                transposed = core_at(column, row)
                constraints.equality(
                    {
                        int(layout.u[left]): 1,
                        int(layout.v[transposed]): -1,
                    },
                    0,
                )

    outputs = (
        layout.u[ports["south"]],
        layout.u[ports["east"]],
        layout.v[ports["south"]],
        layout.v[ports["east"]],
    )
    if args.north_output_only:
        constraints.equality({int(outputs[0]): 1}, 1)
    elif not args.no_output_constraints:
        for value, parity, offset in zip(
            outputs, layout.parity, (1, 0, 0, 1)
        ):
            constraints.equality(
                {int(value): 1, int(parity): -2},
                offset,
            )
        if not args.allow_zero_cross:
            constraints.add({int(outputs[1]): 1}, 1, np.inf)
            constraints.add({int(outputs[2]): 1}, 1, np.inf)
        if args.canonical_outputs:
            for value, target in zip(outputs, (1, 2, 2, 1)):
                constraints.equality({int(value): 1}, target)

    # Both single-pulse odometers are required to be nonzero and to begin at
    # the only cell made unstable by the corresponding external addition.
    constraints.add({int(layout.u[ports["north"]]): 1}, 1, np.inf)
    if args.single_channel:
        for value in layout.v:
            constraints.equality({int(value): 1}, 0)
    else:
        constraints.add({int(layout.v[ports["west"]]): 1}, 1, np.inf)
    if args.force_common_center:
        center = core_at(middle, middle)
        constraints.add({int(layout.u[center]): 1}, 1, np.inf)
        constraints.add({int(layout.v[center]): 1}, 1, np.inf)
    if not args.no_first_topple_constraints:
        north = ext_ports["north"]
        west = ext_ports["west"]
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
    # Minimize activity first. Random coefficients break ties and expose
    # different vertices over multiple trials.
    for position in range(core_area):
        objective[layout.u[position]] = 1000 + rng.randrange(101)
        objective[layout.v[position]] = 1000 + rng.randrange(101)
    for position in range(ext_area):
        objective[layout.eta[position]] = rng.randrange(7)
        for selector in selectors:
            objective[selector[position]] = rng.randrange(7)

    integrality = np.ones(layout.count)
    bounds = Bounds(lower, upper)
    return (
        layout,
        constraints.build(),
        bounds,
        integrality,
        objective,
        ports,
        ext_ports,
    )


def replay(
    args: argparse.Namespace,
    solution: np.ndarray,
    layout: Layout,
    ports: dict[str, int],
) -> dict[str, object]:
    n = args.size
    m = n + 2
    side = m + 6
    offset = 3
    eta = solution[layout.eta].reshape((m, m))
    u = solution[layout.u].reshape((n, n))
    v = solution[layout.v].reshape((n, n))
    ru = solution[layout.ru].reshape((m, m))
    rv = solution[layout.rv].reshape((m, m))
    base = np.zeros((side, side), dtype=np.int64)
    base[offset : offset + m, offset : offset + m] = eta
    expected_u = np.zeros_like(base)
    expected_v = np.zeros_like(base)
    expected_u[
        offset + 1 : offset + 1 + n,
        offset + 1 : offset + 1 + n,
    ] = u
    expected_v[
        offset + 1 : offset + 1 + n,
        offset + 1 : offset + 1 + n,
    ] = v
    north_row, north_column = divmod(ports["north"], n)
    west_row, west_column = divmod(ports["west"], n)
    north = (
        (offset + 1 + north_row) * side + offset + 1 + north_column
    )
    west = (
        (offset + 1 + west_row) * side + offset + 1 + west_column
    )
    runs: dict[str, object] = {}
    legal = True
    failure = None
    for a in range(4):
        for b in range(4):
            final, odometer, trace = legal_stabilize(
                base,
                ((north, a * args.pulse), (west, b * args.pulse)),
            )
            expected_odometer = a * expected_u + b * expected_v
            expected_final = base.copy()
            expected_final[
                offset : offset + m, offset : offset + m
            ] += a * ru + b * rv
            run_legal = bool(
                np.array_equal(odometer, expected_odometer)
                and np.array_equal(final, expected_final)
                and int(final.max()) <= 3
            )
            runs[f"{a},{b}"] = {
                "legal": run_legal,
                "trace_length": len(trace),
                "south": int(
                    odometer[
                        offset + 1 + (ports["south"] // n),
                        offset + 1 + (ports["south"] % n),
                    ]
                ),
                "east": int(
                    odometer[
                        offset + 1 + (ports["east"] // n),
                        offset + 1 + (ports["east"] % n),
                    ]
                ),
            }
            if not run_legal and legal:
                legal = False
                failure = [a, b]
    return {
        "legal": legal,
        "failure": failure,
        "eta": eta.tolist(),
        "u": u.tolist(),
        "v": v.tolist(),
        "ru": ru.tolist(),
        "rv": rv.tolist(),
        "output_matrix": [
            int(u.flat[ports["south"]]),
            int(u.flat[ports["east"]]),
            int(v.flat[ports["south"]]),
            int(v.flat[ports["east"]]),
        ],
        "runs": runs,
    }


def solve_once(args: argparse.Namespace, seed: int) -> dict[str, object]:
    (
        layout,
        constraints,
        bounds,
        integrality,
        objective,
        ports,
        _ext_ports,
    ) = build_problem(args, seed)
    result = milp(
        objective,
        integrality=integrality,
        bounds=bounds,
        constraints=constraints,
        options={
            "time_limit": args.timeout,
            "presolve": True,
            "mip_rel_gap": 0,
        },
    )
    report: dict[str, object] = {
        "size": args.size,
        "pulse": args.pulse,
        "inset": args.inset,
        "max_odometer": args.max_odometer,
        "seed": seed,
        "symmetric": args.symmetric,
        "status": int(result.status),
        "message": result.message,
    }
    if result.x is None:
        return report
    solution = np.rint(result.x).astype(np.int64)
    report["objective"] = float(result.fun)
    report.update(replay(args, solution, layout, ports))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=5)
    parser.add_argument("--pulse", type=int, default=4)
    parser.add_argument("--inset", type=int, default=1)
    parser.add_argument("--max-odometer", type=int, default=64)
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--symmetric", action="store_true")
    parser.add_argument("--canonical-outputs", action="store_true")
    parser.add_argument("--allow-zero-cross", action="store_true")
    parser.add_argument("--no-output-constraints", action="store_true")
    parser.add_argument("--north-output-only", action="store_true")
    parser.add_argument("--no-first-topple-constraints", action="store_true")
    parser.add_argument("--force-common-center", action="store_true")
    parser.add_argument("--single-channel", action="store_true")
    parser.add_argument("--save", type=Path)
    args = parser.parse_args()
    if args.size < 3 or args.size % 2 == 0:
        parser.error("--size must be odd and at least 3")
    if not (0 <= args.inset < args.size // 2):
        parser.error("--inset is outside the core")

    for trial in range(args.trials):
        report = solve_once(args, args.seed + trial)
        print(json.dumps(report, separators=(",", ":")), flush=True)
        if report.get("legal"):
            if args.save is not None:
                args.save.write_text(json.dumps(report, indent=2) + "\n")
            print("LEGAL LINEAR JUNCTION FOUND", flush=True)
            return


if __name__ == "__main__":
    main()
