#!/usr/bin/env python3
"""Synthesize a count-coded crossing in the 2D von Neumann sandpile.

Both Boolean values are active signals.  A low input and a high input inject
different amounts of sand at the same port.  The output bit is decoded by a
threshold on the output cell's odometer.  Thus the north bit crosses to the
south output and the west bit crosses to the east output even if all four
input combinations create avalanches.

This is exploratory synthesis.  Any candidate must subsequently be checked
for composability and against the literature.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import itertools
import random

import numpy as np

from sandpile_crossing_search import Ports, crossover, mutate, stabilize


@dataclass(frozen=True)
class Metrics:
    margin_s: int
    margin_e: int
    intended_gains: tuple[int, int, int, int]
    s_values: tuple[int, int, int, int]
    e_values: tuple[int, int, int, int]
    crosstalk: int
    activity: int


def evaluate(
    base: np.ndarray, ports: Ports, low: int, high: int
) -> tuple[int, Metrics, dict[str, np.ndarray]]:
    additions = {
        "LL": ((ports.north, low), (ports.west, low)),
        "HL": ((ports.north, high), (ports.west, low)),
        "LH": ((ports.north, low), (ports.west, high)),
        "HH": ((ports.north, high), (ports.west, high)),
    }
    runs = {name: stabilize(base, add) for name, add in additions.items()}
    order = ("LL", "HL", "LH", "HH")
    s = tuple(int(runs[name][ports.south]) for name in order)
    e = tuple(int(runs[name][ports.east]) for name in order)

    # At S, N is the intended bit: LL/LH must lie below HL/HH.
    # At E, W is the intended bit: LL/HL must lie below LH/HH.
    margin_s = min(s[1], s[3]) - max(s[0], s[2])
    margin_e = min(e[2], e[3]) - max(e[0], e[1])
    intended_gains = (
        s[1] - s[0],
        s[3] - s[2],
        e[2] - e[0],
        e[3] - e[1],
    )

    # Prefer exact restoration within each decoded level, although threshold
    # separation alone is sufficient for a first candidate.
    crosstalk = (
        abs(s[0] - s[2])
        + abs(s[1] - s[3])
        + abs(e[0] - e[1])
        + abs(e[2] - e[3])
    )
    activity = sum(int(odo.sum()) for odo in runs.values())
    # Staged fitness: first make both intended channels responsive in both
    # contexts, then seek a single separating output threshold, then suppress
    # residual within-band crosstalk.
    gain_deficit = sum(max(0, 1 - gain) for gain in intended_gains)
    margin_deficit = max(0, 1 - margin_s) + max(0, 1 - margin_e)
    score = (
        gain_deficit * 1_000_000
        + margin_deficit * 100_000
        + crosstalk * 1_000
        + activity
    )
    return (
        score,
        Metrics(
            margin_s,
            margin_e,
            intended_gains,
            s,
            e,
            crosstalk,
            activity,
        ),
        runs,
    )


def search(
    n: int,
    low: int,
    high: int,
    population_size: int,
    generations: int,
    seed: int,
    symmetric: bool,
) -> None:
    rng = random.Random(seed)
    mid = n // 2
    ports = Ports((0, mid), (mid, 0), (n - 1, mid), (mid, n - 1))

    def fresh() -> np.ndarray:
        candidate = np.array(
            rng.choices((0, 1, 2, 3), weights=(4, 2, 3, 7), k=n * n),
            dtype=np.int8,
        ).reshape((n, n))
        if symmetric:
            candidate = np.triu(candidate) + np.triu(candidate, 1).T
        return candidate

    population = [fresh() for _ in range(population_size)]
    best_score = 10**18
    best: np.ndarray | None = None
    best_metrics: Metrics | None = None
    best_runs: dict[str, np.ndarray] | None = None

    for generation in range(generations):
        ranked = []
        for candidate in population:
            score, metrics, runs = evaluate(candidate, ports, low, high)
            ranked.append((score, candidate, metrics, runs))
        ranked.sort(key=lambda item: item[0])
        score, candidate, metrics, runs = ranked[0]

        if score < best_score:
            best_score = score
            best = candidate.copy()
            best_metrics = metrics
            best_runs = runs
            print(
                f"generation={generation} score={score} metrics={metrics}",
                flush=True,
            )
            print(candidate, flush=True)

        if metrics.margin_s >= 1 and metrics.margin_e >= 1:
            print("COUNT-CODED CROSSING FOUND", flush=True)
            print(candidate, flush=True)
            print(metrics, flush=True)
            for name, odo in runs.items():
                print(name, flush=True)
                print(odo, flush=True)
            return

        elite_count = max(4, population_size // 10)
        elites = [item[1] for item in ranked[:elite_count]]
        next_population = [x.copy() for x in elites]
        mutation_rate = max(1.0 / (n * n), 0.1 * (1 - generation / generations))
        while len(next_population) < population_size:
            a = rng.choice(elites)
            b = rng.choice(elites)
            child = crossover(a, b, rng, symmetric)
            child = mutate(child, rng, mutation_rate, symmetric)
            next_population.append(child)
        population = next_population

    print("no candidate found", flush=True)
    print(f"best_score={best_score} metrics={best_metrics}", flush=True)
    print(best, flush=True)
    if best_runs is not None:
        for name, odo in best_runs.items():
            print(name, odo, sep="\n", flush=True)


def exhaustive_zero_low(n: int, high: int, symmetric: bool) -> None:
    """Exhaust tiny gadgets for the low=0 threshold-coded special case."""
    mid = n // 2
    ports = Ports((0, mid), (mid, 0), (n - 1, mid), (mid, n - 1))
    positions = (
        [(r, c) for r in range(n) for c in range(r, n)]
        if symmetric
        else [(r, c) for r in range(n) for c in range(n)]
    )
    total = 4 ** len(positions)
    best_margin = -10**9
    best: tuple[np.ndarray, tuple[int, int, int, int]] | None = None
    for index, values in enumerate(itertools.product(range(4), repeat=len(positions))):
        base = np.zeros((n, n), dtype=np.int8)
        for (r, c), value in zip(positions, values):
            base[r, c] = value
            if symmetric:
                base[c, r] = value
        north = stabilize(base, ((ports.north, high),))
        west = stabilize(base, ((ports.west, high),))
        response = (
            int(north[ports.south]),
            int(west[ports.south]),
            int(north[ports.east]),
            int(west[ports.east]),
        )
        margin = min(response[0] - response[1], response[3] - response[2])
        if margin > best_margin:
            best_margin = margin
            best = (base.copy(), response)
        if margin >= 1:
            print(f"EXACT COUNT CROSSING index={index}/{total}", flush=True)
            print(f"response=(N->S,W->S,N->E,W->E)={response}", flush=True)
            print(base, flush=True)
            print("N", north, sep="\n", flush=True)
            print("W", west, sep="\n", flush=True)
            return
    assert best is not None
    print(
        f"EXHAUSTED total={total} best_margin={best_margin} "
        f"response={best[1]}",
        flush=True,
    )
    print(best[0], flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=7)
    parser.add_argument("--low", type=int, default=4)
    parser.add_argument("--high", type=int, default=8)
    parser.add_argument("--population", type=int, default=800)
    parser.add_argument("--generations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--symmetric", action="store_true")
    parser.add_argument("--exhaustive", action="store_true")
    args = parser.parse_args()
    if args.size < 2:
        parser.error("--size must be an integer >= 2")
    if args.low < 0 or args.high <= args.low:
        parser.error("require 0 <= --low < --high")
    if args.exhaustive:
        if args.low != 0:
            parser.error("--exhaustive currently requires --low 0")
        exhaustive_zero_low(args.size, args.high, args.symmetric)
    else:
        search(
            args.size,
            args.low,
            args.high,
            args.population,
            args.generations,
            args.seed,
            args.symmetric,
        )


if __name__ == "__main__":
    main()
