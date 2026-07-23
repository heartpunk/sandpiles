#!/usr/bin/env python3
"""Adversarial tests for the sandpile odometer component-comparison lemma.

For stabilizable configurations eta and zeta with odometers u and v, every
connected component of {u > v} should meet {eta > zeta}; symmetrically, every
component of {v > u} should meet {zeta > eta}.

This file is evidence and regression protection, not the proof.  The proof is
the least-action splicing argument described in the accompanying research
notes/conversation.
"""

from __future__ import annotations

import argparse
from collections import deque
import itertools
import random


def stabilize(
    adjacency: list[dict[int, int]],
    sink_edges: list[int],
    initial: tuple[int, ...],
) -> tuple[int, ...]:
    """Stabilize an undirected finite multigraph with a dissipative sink."""
    n = len(initial)
    state = list(initial)
    odometer = [0] * n
    degree = [
        sink_edges[x] + sum(adjacency[x].values())
        for x in range(n)
    ]
    queue = deque(x for x in range(n) if state[x] >= degree[x])
    queued = [state[x] >= degree[x] for x in range(n)]

    while queue:
        x = queue.popleft()
        queued[x] = False
        count = state[x] // degree[x]
        if count == 0:
            continue
        state[x] -= count * degree[x]
        odometer[x] += count
        for y, multiplicity in adjacency[x].items():
            state[y] += count * multiplicity
            if state[y] >= degree[y] and not queued[y]:
                queued[y] = True
                queue.append(y)
    return tuple(odometer)


def components(
    adjacency: list[dict[int, int]], vertices: set[int]
) -> list[set[int]]:
    remaining = set(vertices)
    result: list[set[int]] = []
    while remaining:
        root = remaining.pop()
        component = {root}
        stack = [root]
        while stack:
            x = stack.pop()
            for y in adjacency[x]:
                if y in remaining:
                    remaining.remove(y)
                    component.add(y)
                    stack.append(y)
        result.append(component)
    return result


def assert_no_islands(
    adjacency: list[dict[int, int]],
    eta: tuple[int, ...],
    zeta: tuple[int, ...],
    u: tuple[int, ...],
    v: tuple[int, ...],
) -> None:
    positive_sources = {x for x in range(len(eta)) if eta[x] > zeta[x]}
    negative_sources = {x for x in range(len(eta)) if zeta[x] > eta[x]}

    for component in components(
        adjacency, {x for x in range(len(eta)) if u[x] > v[x]}
    ):
        assert component & positive_sources, (
            "positive island",
            adjacency,
            eta,
            zeta,
            u,
            v,
            component,
        )
    for component in components(
        adjacency, {x for x in range(len(eta)) if v[x] > u[x]}
    ):
        assert component & negative_sources, (
            "negative island",
            adjacency,
            eta,
            zeta,
            u,
            v,
            component,
        )


def path_graph(n: int) -> tuple[list[dict[int, int]], list[int]]:
    adjacency = [dict() for _ in range(n)]
    for x in range(n - 1):
        adjacency[x][x + 1] = 1
        adjacency[x + 1][x] = 1
    sink_edges = [0] * n
    sink_edges[0] = 1
    sink_edges[-1] += 1
    return adjacency, sink_edges


def exhaustive_path(n: int, max_height: int) -> int:
    adjacency, sink_edges = path_graph(n)
    configurations = list(
        itertools.product(range(max_height + 1), repeat=n)
    )
    odometers = {
        eta: stabilize(adjacency, sink_edges, eta)
        for eta in configurations
    }
    checked = 0
    for eta in configurations:
        for zeta in configurations:
            assert_no_islands(
                adjacency, eta, zeta, odometers[eta], odometers[zeta]
            )
            checked += 1
    return checked


def random_graph(
    rng: random.Random, n: int
) -> tuple[list[dict[int, int]], list[int]]:
    adjacency = [dict() for _ in range(n)]

    # First add a random spanning tree.
    for x in range(1, n):
        y = rng.randrange(x)
        multiplicity = rng.randint(1, 3)
        adjacency[x][y] = multiplicity
        adjacency[y][x] = multiplicity

    # Then add arbitrary extra multiedges.
    for x in range(n):
        for y in range(x + 1, n):
            if y not in adjacency[x] and rng.random() < 0.25:
                multiplicity = rng.randint(1, 3)
                adjacency[x][y] = multiplicity
                adjacency[y][x] = multiplicity

    # One sink edge already makes the connected graph dissipative; random
    # extras exercise varying boundary dissipation.
    sink_edges = [0] * n
    sink_edges[rng.randrange(n)] = rng.randint(1, 3)
    for x in range(n):
        if rng.random() < 0.2:
            sink_edges[x] += rng.randint(1, 3)
    return adjacency, sink_edges


def randomized(trials: int, seed: int) -> int:
    rng = random.Random(seed)
    for _ in range(trials):
        n = rng.randint(2, 12)
        adjacency, sink_edges = random_graph(rng, n)
        degree = [
            sink_edges[x] + sum(adjacency[x].values())
            for x in range(n)
        ]
        eta = tuple(rng.randint(0, 8 * degree[x] + 20) for x in range(n))
        zeta = tuple(rng.randint(0, 8 * degree[x] + 20) for x in range(n))
        u = stabilize(adjacency, sink_edges, eta)
        v = stabilize(adjacency, sink_edges, zeta)
        assert_no_islands(adjacency, eta, zeta, u, v)
    return trials


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--random-trials", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=20260723)
    args = parser.parse_args()

    exhaustive = exhaustive_path(n=3, max_height=5)
    random_count = randomized(args.random_trials, args.seed)
    print(
        f"PASS: {exhaustive:,} exhaustive ordered pairs on the 3-path; "
        f"{random_count:,} randomized pairs on undirected multigraphs"
    )


if __name__ == "__main__":
    main()
