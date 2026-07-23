#!/usr/bin/env python3
"""GA search for the exact clean one-grain crossover truth table.

For inputs on the first interior ring, the ring supersolution proves every
odometer value is at most two.  Parity plus monotonicity therefore forces the
only possible output count vector:

    (N->S, N->E, W->S, W->E, NW->S, NW->E) = (1, 0, 0, 1, 1, 1).

The older parity search optimized toward (1,2,2,1,3,3), which is impossible
at this depth.  This program searches the correct target.
"""

from __future__ import annotations

import argparse
import random

import numpy as np

from sandpile_crossing_search import Ports, stabilize


TARGET = (1, 0, 0, 1, 1, 1)


def evaluate(
    core: np.ndarray,
    padding: int,
    inset: int,
) -> tuple[int, tuple[int, ...], tuple[np.ndarray, ...]]:
    n = core.shape[0]
    board = np.zeros((n + 2 * padding, n + 2 * padding), dtype=np.int8)
    board[padding : padding + n, padding : padding + n] = core
    middle = n // 2
    ports = Ports(
        (padding + inset, padding + middle),
        (padding + middle, padding + inset),
        (padding + n - 1 - inset, padding + middle),
        (padding + middle, padding + n - 1 - inset),
    )
    north = stabilize(board, ((ports.north, 1),))
    west = stabilize(board, ((ports.west, 1),))
    both = stabilize(board, ((ports.north, 1), (ports.west, 1)))
    counts = (
        int(north[ports.south]),
        int(north[ports.east]),
        int(west[ports.south]),
        int(west[ports.east]),
        int(both[ports.south]),
        int(both[ports.east]),
    )
    distance = sum(abs(got - want) for got, want in zip(counts, TARGET))
    boundary_activity = sum(
        int(odometer[0, :].sum())
        + int(odometer[-1, :].sum())
        + int(odometer[1:-1, 0].sum())
        + int(odometer[1:-1, -1].sum())
        for odometer in (north, west, both)
    )
    activity = sum(int(odometer.sum()) for odometer in (north, west, both))
    score = distance * 1_000_000 + boundary_activity * 10_000_000 + activity
    return score, counts, (north, west, both)


def symmetrize(core: np.ndarray) -> np.ndarray:
    return np.triu(core) + np.triu(core, 1).T


def search(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    numpy_rng = np.random.default_rng(args.seed)
    n = args.size

    def fresh() -> np.ndarray:
        core = np.asarray(
            rng.choices(
                (0, 1, 2, 3),
                weights=(2, 1, 3, 12),
                k=n * n,
            ),
            dtype=np.int8,
        ).reshape((n, n))
        return symmetrize(core) if args.symmetric else core

    population = [fresh() for _ in range(args.population)]
    best_score = 10**30
    for generation in range(args.generations):
        ranked = []
        for core in population:
            score, counts, runs = evaluate(core, args.padding, args.inset)
            ranked.append((score, core, counts, runs))
        ranked.sort(key=lambda item: item[0])
        score, candidate, counts, runs = ranked[0]
        if score < best_score:
            best_score = score
            print(
                f"generation={generation} score={score} counts={counts}",
                flush=True,
            )
            print(candidate, flush=True)
        if counts == TARGET and score < 10_000_000:
            checked_score, checked_counts, checked_runs = evaluate(
                candidate,
                args.padding * 2,
                args.inset,
            )
            if checked_counts != TARGET or checked_score >= 10_000_000:
                raise AssertionError("candidate failed doubled-padding replay")
            print("CLEAN ONE-GRAIN CROSSING FOUND", flush=True)
            print(candidate, flush=True)
            for name, odometer in zip(("N", "W", "NW"), checked_runs):
                print(name, odometer, sep="\n", flush=True)
            return

        elite_count = max(8, args.population // 10)
        # A common local optimum has exactly one live singleton channel.
        # Ordinary truncation selection then deletes the complementary niche
        # before crossover can combine them.  Preserve several representatives
        # of every output-count signature, and explicitly retain transposes
        # (which exchange the two channels).
        per_signature = max(2, elite_count // 12)
        signature_counts: dict[tuple[int, ...], int] = {}
        elites = []
        for _, core, counts, _ in ranked:
            used = signature_counts.get(counts, 0)
            if used >= per_signature:
                continue
            elites.append(core)
            signature_counts[counts] = used + 1
            if len(elites) == elite_count:
                break
        if len(elites) < elite_count:
            seen = {id(core) for core in elites}
            elites.extend(
                item[1]
                for item in ranked
                if id(item[1]) not in seen
            )
            elites = elites[:elite_count]
        next_population = [core.copy() for core in elites]
        if not args.symmetric:
            next_population.extend(
                core.T.copy()
                for core in elites
                if len(next_population) < args.population
            )
        mutation_rate = max(
            1.0 / (n * n),
            0.12 * (1 - generation / args.generations),
        )
        while len(next_population) < args.population:
            if rng.random() < 0.03:
                next_population.append(fresh())
                continue
            left = rng.choice(elites)
            right = rng.choice(elites)
            child = np.where(
                numpy_rng.random((n, n)) < 0.5,
                left,
                right,
            ).astype(np.int8)
            if args.symmetric:
                child = symmetrize(child)
            mask = numpy_rng.random((n, n)) < mutation_rate
            if args.symmetric:
                mask = np.triu(mask)
            for row, column in zip(*np.where(mask)):
                old = int(child[row, column])
                replacement = rng.randrange(3)
                if replacement >= old:
                    replacement += 1
                child[row, column] = replacement
                if args.symmetric:
                    child[column, row] = replacement
            next_population.append(child)
        population = next_population
    print(f"NO HIT best_score={best_score}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=7)
    parser.add_argument("--inset", type=int, default=1)
    parser.add_argument("--padding", type=int, default=3)
    parser.add_argument("--population", type=int, default=1000)
    parser.add_argument("--generations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--symmetric", action="store_true")
    args = parser.parse_args()
    search(args)


if __name__ == "__main__":
    main()
