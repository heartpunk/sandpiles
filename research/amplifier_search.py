#!/usr/bin/env python3
"""Independently audit the passive-load bound on the infinite square lattice.

Uses only Python's standard library. There are no production research imports,
finite array boundaries, or sinks. Every non-source kth toppling receives a
checked earlier neighboring kth ancestor. The finite experiments check the
implementation; the universal proof is in passive_amplification.md.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
import hashlib
import itertools
import json
from pathlib import Path
import random
from typing import Iterable, TypedDict


Coord = tuple[int, int]
Configuration = dict[Coord, int]
Event = tuple[Coord, int, int | None]
DIRS = ((-1, 0), (0, -1), (0, 1), (1, 0))


class RunResult(TypedDict):
    u: Configuration
    final: Configuration
    events: int
    ancestry_edges: int
    sources: set[Coord]


class TracedRunResult(RunResult, total=False):
    trace: list[Event]
    trace_sha256: str


def neighbors(position: Coord) -> Iterable[Coord]:
    """Return the four literal lattice neighbors in a fixed order."""
    return ((position[0] + dr, position[1] + dc) for dr, dc in DIRS)


def moments(configuration: Configuration) -> tuple[int, int, int, int]:
    """Return mass, both first moments, and the squared-distance moment."""
    return (
        sum(configuration.values()),
        sum(p[0] * value for p, value in configuration.items()),
        sum(p[1] * value for p, value in configuration.items()),
        sum((p[0] ** 2 + p[1] ** 2) * value
            for p, value in configuration.items()),
    )


def run(
    initial: Configuration,
    additions: Configuration,
    trace: bool = False,
) -> TracedRunResult:
    """Stabilize with FIFO unit events and check every chronological ancestor.

    A non-source's kth event must have an earlier neighboring kth event. We
    record that parent and inherit its source root. Separately, every complete
    odometer superlevel component is checked for contact with an input source.
    """
    assert all(isinstance(value, int) and 0 <= value <= 3
               for value in initial.values())
    assert all(isinstance(amount, int) and amount >= 0
               for amount in additions.values())
    sources = {p for p, amount in additions.items() if amount}
    heights = defaultdict(int, initial)
    for position, amount in additions.items():
        heights[position] += amount
    before = moments(heights)
    queue = deque(sorted(p for p in heights if heights[p] >= 4))
    times: defaultdict[Coord, list[int]] = defaultdict(list)
    events: list[Event] = []
    roots: list[Coord] = []
    ancestor_count = 0

    while queue:
        position = queue.popleft()
        assert heights[position] >= 4
        k = len(times[position]) + 1
        parent = None
        if position not in sources:
            eligible = [q for q in neighbors(position) if len(times[q]) >= k]
            assert eligible, (position, k, "missing earlier kth ancestor")
            neighbor = min(eligible)
            parent = times[neighbor][k - 1]
            assert parent < len(events)
            previous_position, previous_k, _ = events[parent]
            assert previous_k == k and previous_position == neighbor
            root = roots[parent]
            assert root in sources
            ancestor_count += 1
        else:
            root = position

        roots.append(root)
        times[position].append(len(events))
        events.append((position, k, parent))
        heights[position] -= 4
        if heights[position] >= 4:
            queue.append(position)
        for neighbor in neighbors(position):
            heights[neighbor] += 1
            if heights[neighbor] == 4:
                queue.append(neighbor)

    assert all(0 <= value <= 3 for value in heights.values())
    odometer = {p: len(site_times) for p, site_times in times.items() if site_times}
    final = {p: value for p, value in heights.items() if value}
    after = moments(final)
    assert before[:3] == after[:3]
    assert after[3] - before[3] == 4 * len(events)
    for position in set(initial) | set(additions) | set(heights) | set(odometer):
        reconstructed = (
            initial.get(position, 0)
            + additions.get(position, 0)
            - 4 * odometer.get(position, 0)
            + sum(odometer.get(q, 0) for q in neighbors(position))
        )
        assert reconstructed == final.get(position, 0)

    # Check connected components without using the chronological parent links.
    for k in range(1, max(odometer.values(), default=0) + 1):
        unseen = {p for p, count in odometer.items() if count >= k}
        while unseen:
            root = min(unseen)
            unseen.remove(root)
            todo = [root]
            hits_source = root in sources
            while todo:
                position = todo.pop()
                for neighbor in neighbors(position):
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        todo.append(neighbor)
                        hits_source |= neighbor in sources
            assert hits_source, ("source-free superlevel component", k)

    result: TracedRunResult = {
        "u": odometer,
        "final": final,
        "events": len(events),
        "ancestry_edges": ancestor_count,
        "sources": sources,
    }
    if trace:
        result["trace"] = events
        result["trace_sha256"] = hashlib.sha256(
            json.dumps(events, separators=(",", ":")).encode()
        ).hexdigest()
    return result


def synchronous(
    initial: Configuration,
    additions: Configuration,
) -> tuple[Configuration, Configuration]:
    """Independently stabilize using simultaneous legal batches, not FIFO."""
    heights = defaultdict(int, initial)
    odometer: defaultdict[Coord, int] = defaultdict(int)
    for position, amount in additions.items():
        heights[position] += amount
    while True:
        wave = {p: value // 4 for p, value in heights.items() if value >= 4}
        if not wave:
            break
        for position, count in wave.items():
            heights[position] -= 4 * count
            odometer[position] += count
            for neighbor in neighbors(position):
                heights[neighbor] += count
    return (
        {p: count for p, count in odometer.items() if count},
        {p: value for p, value in heights.items() if value},
    )


def cut_check(result: RunResult, load: set[Coord]) -> bool:
    """Check the complete boundary cap and, when applicable, bridge bound.

    The load may be disconnected. Its boundary includes all adjacent lattice
    sites outside it, including initially empty sites. Return whether the cut
    has exactly one edge with a toppled endpoint on each side.
    """
    assert not load & result["sources"]
    boundary = {q for p in load for q in neighbors(p) if q not in load}
    odometer = result["u"]
    inside = max((odometer.get(p, 0) for p in load), default=0)
    outside = max((odometer.get(p, 0) for p in boundary), default=0)
    assert inside <= outside
    active_edges = [
        (p, q)
        for p in load
        for q in neighbors(p)
        if q not in load and odometer.get(p, 0) and odometer.get(q, 0)
    ]
    bridge = len(active_edges) == 1
    if bridge:
        entrance, source_side = active_edges[0]
        assert inside <= odometer[entrance] <= odometer[source_side]
    return bridge


def clean_record(
    initial: Configuration,
    additions: Configuration,
    result: TracedRunResult,
) -> dict:
    """Serialize a small example, including its complete legal history."""
    def rows(configuration: Configuration) -> list[list[int]]:
        return [[p[0], p[1], value]
                for p, value in sorted(configuration.items()) if value]

    return {
        "initial": rows(initial),
        "additions": rows(additions),
        "odometer": rows(result["u"]),
        "final": rows(result["final"]),
        "unit_topplings": result["events"],
        "ancestry_edges": result["ancestry_edges"],
        "trace_sha256": result["trace_sha256"],
        "legal_history": result["trace"],
    }


def audit(random_cases: int = 128, seed: int = 20261002) -> dict:
    """Run the documented finite suite and return its deterministic report."""
    summary = {
        "schema": 1,
        "model": "sinkless infinite square lattice, threshold 4",
        "random_seed": seed,
        "categories": {},
        "legal_unit_topplings": 0,
        "checked_ancestry_edges": 0,
        "source_free_cuts_checked": 0,
        "active_bridge_cuts_checked": 0,
        "independent_synchronous_replays": 0,
    }

    def record(
        category: str,
        initial: Configuration,
        additions: Configuration,
        subsets: Iterable[set[Coord]] = (),
        replay: bool = False,
        trace: bool = False,
    ) -> TracedRunResult:
        """Check one configuration, selected cuts, and an optional replay."""
        result = run(initial, additions, trace)
        categories = summary["categories"]
        categories[category] = categories.get(category, 0) + 1
        summary["legal_unit_topplings"] += result["events"]
        summary["checked_ancestry_edges"] += result["ancestry_edges"]
        odometer = result["u"]
        loads = [set(odometer) - result["sources"]] + list(subsets)

        # Inspect active portions of source-free half-planes and their complete
        # boundaries. Omitted inactive sites have count zero by construction.
        for axis in range(2):
            for value in sorted({p[axis] for p in result["sources"]}):
                for sign in (-1, 1):
                    load = {p for p in odometer if sign * (p[axis] - value) > 0}
                    if not load & result["sources"]:
                        loads.append(load)
        for load in loads:
            if load & result["sources"]:
                continue
            summary["active_bridge_cuts_checked"] += cut_check(result, load)
            summary["source_free_cuts_checked"] += 1
        if replay:
            second_odometer, second_final = synchronous(initial, additions)
            assert result["u"] == second_odometer
            assert result["final"] == second_final
            summary["independent_synchronous_replays"] += 1
        return result

    core = ((0, 0), (0, 1), (1, 0), (1, 1))
    subsets = [
        {position for i, position in enumerate(core) if mask & (1 << i)}
        for mask in range(16)
    ]
    for heights in itertools.product(range(4), repeat=4):
        initial = dict(zip(core, heights))
        for amounts in itertools.product(range(4), repeat=4):
            record("exhaustive_2x2", initial, dict(zip(core, amounts)), subsets)
    for heights in itertools.product(range(4), repeat=4):
        initial = dict(zip(core, heights))
        for amount in (4, 7, 16, 31, 71):
            record("single_source_packets", initial, {(0, 0): amount}, subsets)

    rng = random.Random(seed)
    for _ in range(random_cases):
        radius = rng.randrange(2, 9)
        initial = {
            (row, column): rng.choices((0, 1, 2, 3), weights=(1, 1, 1, 7))[0]
            for row in range(-radius, radius + 1)
            for column in range(-radius, radius + 1)
        }
        sources = rng.sample(sorted(initial), rng.randrange(1, 5))
        additions = {position: rng.randrange(1, 101) for position in sources}
        record("random_large", initial, additions, replay=True)

    initial = {}
    additions = {(0, 0): 24}
    unloaded = record(
        "feedback_examples", initial, additions, replay=True, trace=True
    )
    chamber = {(row, column): 3
               for row in range(-1, 2) for column in range(2, 5)}
    loaded = record(
        "feedback_examples", chamber, additions, replay=True, trace=True
    )
    source, port, entrance = (0, 0), (0, 1), (0, 2)
    assert (unloaded["u"][source], unloaded["u"][port],
            unloaded["final"][port]) == (7, 1, 3)
    assert (loaded["u"][source], loaded["u"][port],
            loaded["u"][entrance]) == (7, 2, 2)

    # Replay the unloaded history while postponing chamber activity. The
    # entrance's first toppling then makes the port's second toppling legal.
    postponed = defaultdict(int, chamber)
    postponed[source] += 24
    for site, kth, parent in unloaded["trace"]:
        assert postponed[site] >= 4
        postponed[site] -= 4
        for neighbor in neighbors(site):
            postponed[neighbor] += 1
    assert postponed[port] == 3 and postponed[entrance] == 4
    postponed[entrance] -= 4
    for neighbor in neighbors(entrance):
        postponed[neighbor] += 1
    assert postponed[port] == 4
    load = {position for position in loaded["u"] if position[1] >= 2}
    boundary = {q for position in load for q in neighbors(position) if q not in load}
    assert max(loaded["u"][position] for position in load) == 2
    assert max(loaded["u"].get(q, 0) for q in boundary) == 2
    summary["feedback_example"] = {
        "unloaded": clean_record(initial, additions, unloaded),
        "loaded": clean_record(chamber, additions, loaded),
        "comparison": {
            "source": [0, 0],
            "port": [0, 1],
            "entrance": [0, 2],
            "unloaded_port_topplings": 1,
            "loaded_port_topplings": 2,
            "postponed_chamber_port_height": 3,
            "postponed_chamber_entrance_height": 4,
            "port_height_after_entrance_topples": 4,
            "loaded_receiver_maximum": 2,
            "loaded_complete_boundary_maximum": 2,
        },
    }

    summary["direct_injection_examples"] = []
    for radius in (1, 2, 3, 5, 10):
        square = {(row, column): 3
                  for row in range(-radius, radius + 1)
                  for column in range(-radius, radius + 1)}
        result = record(
            "direct_injection", square, {(0, 0): 1}, replay=True, trace=True
        )
        summary["direct_injection_examples"].append({
            "radius": radius,
            "source_topplings": result["u"][(0, 0)],
            "maximum_topplings": max(result["u"].values()),
            "unit_topplings": result["events"],
            "trace_sha256": result["trace_sha256"],
        })
    summary["total_configurations"] = sum(summary["categories"].values())
    summary["status"] = "all checks passed"
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--random-cases", type=int, default=128)
    parser.add_argument("--seed", type=int, default=20261002)
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).with_name("amplifier_search_results.json"),
    )
    args = parser.parse_args()
    if not __debug__:
        raise SystemExit("Audit requires assertions: do not use -O or PYTHONOPTIMIZE.")
    if args.random_cases < 0:
        parser.error("--random-cases must be nonnegative")
    summary = audit(args.random_cases, args.seed)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    compact = {key: value for key, value in summary.items()
               if key not in ("feedback_example", "direct_injection_examples")}
    print(json.dumps(compact, indent=2, sort_keys=True))
    print(f"Results: {args.output}")


if __name__ == "__main__":
    main()
