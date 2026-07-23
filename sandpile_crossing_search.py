#!/usr/bin/env python3
"""Search for amplitude-coded crossings in the 2D von Neumann sandpile.

This is exploratory synthesis, not a proof.  A candidate is a stable n x n
configuration.  A pulse is added at either the north or west input.  We ask
for independent propagation to the south or east output respectively.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import itertools
import random
from typing import Iterable

import numpy as np


Coord = tuple[int, int]


@dataclass(frozen=True)
class Ports:
    north: Coord
    west: Coord
    south: Coord
    east: Coord


def stabilize(base: np.ndarray, additions: Iterable[tuple[Coord, int]]) -> np.ndarray:
    """Return the odometer after legal sequential stabilization with a sink boundary."""
    state = base.astype(np.int32, copy=True)
    n, m = state.shape
    for (r, c), amount in additions:
        state[r, c] += amount

    odo = np.zeros_like(state)
    queued = np.zeros_like(state, dtype=np.bool_)
    q: deque[Coord] = deque()
    for r, c in np.argwhere(state >= 4):
        q.append((int(r), int(c)))
        queued[r, c] = True

    while q:
        r, c = q.popleft()
        queued[r, c] = False
        k = int(state[r, c] // 4)
        if k == 0:
            continue
        state[r, c] -= 4 * k
        odo[r, c] += k
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < n and 0 <= cc < m:
                state[rr, cc] += k
                if state[rr, cc] >= 4 and not queued[rr, cc]:
                    queued[rr, cc] = True
                    q.append((rr, cc))
    return odo


def evaluate(base: np.ndarray, ports: Ports, pulse: int) -> tuple[int, dict[str, np.ndarray]]:
    """Lower is better. Zero satisfies the basic Boolean crossing specification."""
    runs = {
        "N": stabilize(base, ((ports.north, pulse),)),
        "W": stabilize(base, ((ports.west, pulse),)),
        "NW": stabilize(base, ((ports.north, pulse), (ports.west, pulse))),
    }

    n_s = int(runs["N"][ports.south])
    n_e = int(runs["N"][ports.east])
    w_s = int(runs["W"][ports.south])
    w_e = int(runs["W"][ports.east])
    b_s = int(runs["NW"][ports.south])
    b_e = int(runs["NW"][ports.east])

    # Logical specification: N->S only and W->E only.  The combined-input
    # conditions follow from odometer monotonicity.  Missing a desired
    # propagation is weighted more heavily than crosstalk so evolution first
    # discovers two live channels and only then tries to decouple them.
    errors = (
        10 * int(n_s == 0)
        + int(n_e != 0)
        + int(w_s != 0)
        + 10 * int(w_e == 0)
    )

    # Shape the search before logical satisfaction.  Reward desired output counts,
    # punish contamination strongly, and prefer combined behavior close to the
    # corresponding single-input behavior.
    shaped = (
        max(0, 2 - n_s)
        + 5 * n_e
        + 5 * w_s
        + max(0, 2 - w_e)
        + max(0, n_s - b_s)
        + max(0, w_e - b_e)
        + abs(b_s - n_s)
        + abs(b_e - w_e)
    )

    # Avoid solutions that simply light almost the entire boundary.  Input ports
    # are excluded, and intended output for each run is not penalized.
    boundary = [(0, j) for j in range(base.shape[1])]
    boundary += [(base.shape[0] - 1, j) for j in range(base.shape[1])]
    boundary += [(i, 0) for i in range(1, base.shape[0] - 1)]
    boundary += [(i, base.shape[1] - 1) for i in range(1, base.shape[0] - 1)]
    allowed = {
        "N": {ports.north, ports.south},
        "W": {ports.west, ports.east},
        "NW": {ports.north, ports.west, ports.south, ports.east},
    }
    leakage = sum(
        int(odo[p])
        for name, odo in runs.items()
        for p in boundary
        if p not in allowed[name]
    )

    return errors * 100_000 + shaped * 100 + leakage, runs


def symmetrize(x: np.ndarray) -> np.ndarray:
    """Reflect the upper triangle across the main diagonal."""
    return np.triu(x) + np.triu(x, 1).T


def mutate(
    x: np.ndarray, rng: random.Random, rate: float, symmetric: bool
) -> np.ndarray:
    y = x.copy()
    if symmetric:
        mask = np.zeros_like(y, dtype=np.bool_)
        for r in range(y.shape[0]):
            for c in range(r, y.shape[1]):
                if rng.random() < rate:
                    mask[r, c] = True
    else:
        mask = np.fromiter(
            (rng.random() < rate for _ in range(y.size)),
            dtype=np.bool_,
            count=y.size,
        ).reshape(y.shape)
    for r, c in np.argwhere(mask):
        old = int(y[r, c])
        y[r, c] = rng.randrange(3)
        if y[r, c] >= old:
            y[r, c] += 1
        if symmetric:
            y[c, r] = y[r, c]
    return y


def crossover(
    a: np.ndarray, b: np.ndarray, rng: random.Random, symmetric: bool
) -> np.ndarray:
    if symmetric:
        mask = np.fromiter(
            (rng.random() < 0.5 for _ in range(a.size)),
            dtype=np.bool_,
            count=a.size,
        ).reshape(a.shape)
        mask = np.triu(mask)
        return symmetrize(np.where(mask, a, b))
    if rng.random() < 0.5:
        cut = rng.randrange(1, a.shape[0])
        return np.vstack((a[:cut], b[cut:]))
    cut = rng.randrange(1, a.shape[1])
    return np.hstack((a[:, :cut], b[:, cut:]))


def search(
    n: int,
    pulse: int,
    population_size: int,
    generations: int,
    seed: int,
    symmetric: bool,
) -> None:
    rng = random.Random(seed)
    mid = n // 2
    ports = Ports((0, mid), (mid, 0), (n - 1, mid), (mid, n - 1))

    def fresh() -> np.ndarray:
        # Bias toward threshold-ready cells without filling the whole board with 3s.
        candidate = np.array(
            rng.choices((0, 1, 2, 3), weights=(5, 2, 3, 6), k=n * n),
            dtype=np.int8,
        ).reshape((n, n))
        return symmetrize(candidate) if symmetric else candidate

    population = [fresh() for _ in range(population_size)]
    best_score = 10**18
    best: np.ndarray | None = None
    best_runs: dict[str, np.ndarray] | None = None

    for generation in range(generations):
        ranked = []
        for candidate in population:
            score, runs = evaluate(candidate, ports, pulse)
            ranked.append((score, candidate, runs))
        ranked.sort(key=lambda item: item[0])

        if ranked[0][0] < best_score:
            best_score, best, best_runs = ranked[0]
            print(f"generation={generation} score={best_score}", flush=True)
            print(best, flush=True)
            print(
                {
                    name: {
                        "S": int(odo[ports.south]),
                        "E": int(odo[ports.east]),
                        "total": int(odo.sum()),
                    }
                    for name, odo in best_runs.items()
                },
                flush=True,
            )

        if best_score < 100_000:
            assert best is not None and best_runs is not None
            print("BASIC CROSSING SPECIFICATION SATISFIED", flush=True)
            for name, odo in best_runs.items():
                print(name, flush=True)
                print(odo, flush=True)
            return

        elite_count = max(4, population_size // 10)
        elites = [item[1] for item in ranked[:elite_count]]
        next_population = [x.copy() for x in elites]
        mutation_rate = max(1.0 / (n * n), 0.08 * (1 - generation / generations))
        while len(next_population) < population_size:
            a = rng.choice(elites)
            b = rng.choice(elites)
            child = crossover(a, b, rng, symmetric)
            child = mutate(child, rng, mutation_rate, symmetric)
            next_population.append(child)
        population = next_population

    print("no candidate found", flush=True)
    if best is not None:
        print(f"best score={best_score}", flush=True)
        print(best, flush=True)


def exhaustive_search(n: int, pulse: int, symmetric: bool) -> None:
    """Exhaust all stable configurations for tiny boards."""
    mid = n // 2
    ports = Ports((0, mid), (mid, 0), (n - 1, mid), (mid, n - 1))
    positions = (
        [(r, c) for r in range(n) for c in range(r, n)]
        if symmetric
        else [(r, c) for r in range(n) for c in range(n)]
    )
    total = 4 ** len(positions)
    best_score = 10**18
    best: np.ndarray | None = None
    for index, values in enumerate(itertools.product(range(4), repeat=len(positions))):
        candidate = np.zeros((n, n), dtype=np.int8)
        for (r, c), value in zip(positions, values):
            candidate[r, c] = value
            if symmetric:
                candidate[c, r] = value
        score, runs = evaluate(candidate, ports, pulse)
        if score < best_score:
            best_score = score
            best = candidate.copy()
        if score < 100_000:
            print(f"EXACT CANDIDATE index={index}/{total}", flush=True)
            print(candidate, flush=True)
            for name, odo in runs.items():
                print(name, flush=True)
                print(odo, flush=True)
            return
        if index and index % 100_000 == 0:
            print(f"checked={index}/{total} best_score={best_score}", flush=True)
    print(f"EXHAUSTED total={total} best_score={best_score}", flush=True)
    print(best, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=7)
    parser.add_argument("--pulse", type=int, default=4)
    parser.add_argument("--population", type=int, default=600)
    parser.add_argument("--generations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--symmetric",
        action="store_true",
        help="restrict candidates to reflection symmetry across the NW-SE diagonal",
    )
    parser.add_argument(
        "--exhaustive",
        action="store_true",
        help="exhaust all stable configurations (only practical for tiny boards)",
    )
    args = parser.parse_args()
    if args.size < 2:
        parser.error("--size must be an integer >= 2")
    if args.exhaustive:
        exhaustive_search(args.size, args.pulse, args.symmetric)
    else:
        search(
            args.size,
            args.pulse,
            args.population,
            args.generations,
            args.seed,
            args.symmetric,
        )


if __name__ == "__main__":
    main()
