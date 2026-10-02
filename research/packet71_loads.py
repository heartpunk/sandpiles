#!/usr/bin/env python3
"""Exact static-load and presence-composition audit for packet-71 AND.

Pure Python, sparse signed coordinates, threshold four, no sink or boundary.
No discovery code or existing certificate is imported. See packet71_loads.md
for the theorem checked by the local certificate routine.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections import Counter, deque
from pathlib import Path
from typing import Iterable, Mapping

Site = tuple[int, int]
State = dict[Site, int]
PORTS = ((-4, -1), (-4, 2), (-1, -4), (-1, 5),
         (1, -4), (1, 5), (4, -1), (4, 2))


def neighbors(x: Site) -> tuple[Site, Site, Site, Site]:
    r, c = x
    return ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))


def clean(h: Mapping[Site, int]) -> State:
    return {x: n for x, n in h.items() if n}


def plus(*states: Mapping[Site, int]) -> State:
    h: Counter[Site] = Counter()
    for state in states:
        h.update(state)
    return clean(h)


def halo(sites: Iterable[Site]) -> set[Site]:
    sites = set(sites)
    return sites | {y for x in sites for y in neighbors(x)}


def degrees(sites: Iterable[Site]) -> Counter[Site]:
    return Counter(y for x in sites for y in neighbors(x))


def reconstruct(initial: Mapping[Site, int], u: Mapping[Site, int]) -> State:
    h = Counter(initial)
    for x, n in u.items():
        h[x] -= 4 * n
        for y in neighbors(x):
            h[y] += n
    return clean(h)


def stabilize(initial: Mapping[Site, int]) -> tuple[State, State]:
    """Literal legal unit topplings, with an unbounded sparse queue."""
    assert all(isinstance(n, int) and n >= 0 for n in initial.values())
    h = Counter(initial)
    u: Counter[Site] = Counter()
    q = deque(sorted(x for x, n in h.items() if n >= 4))
    pending = set(q)
    while q:
        x = q.popleft()
        pending.remove(x)
        assert h[x] >= 4
        h[x] -= 4
        u[x] += 1
        for y in neighbors(x):
            h[y] += 1
            if h[y] >= 4 and y not in pending:
                q.append(y)
                pending.add(y)
        if h[x] >= 4 and x not in pending:
            q.append(x)
            pending.add(x)
    result = clean(h)
    odo = clean(u)
    assert all(0 <= n <= 3 for n in result.values())
    assert sum(result.values()) == sum(initial.values())
    assert reconstruct(initial, odo) == result
    return result, odo


def once_certificate(initial: Mapping[Site, int], active: set[Site]) -> dict:
    """Exact certificate for odometer = indicator(active).

    Bootstrap gives a legal once-each order or a nonempty deadlocked set.
    Endpoint arithmetic checks *all* potentially nonzero cells, including
    exterior cells. Together these tests are necessary and sufficient.
    """
    received: Counter[Site] = Counter()
    remaining = set(active)
    order: list[Site] = []
    while remaining:
        ready = sorted(x for x in remaining
                       if initial.get(x, 0) + received[x] >= 4)
        if not ready:
            break
        for x in ready:
            remaining.remove(x)
            order.append(x)
            for y in neighbors(x):
                received[y] += 1
    final = reconstruct(initial, dict.fromkeys(active, 1))
    violations = sorted((x, n) for x, n in final.items() if not 0 <= n <= 3)
    valid = not remaining and not violations
    if valid:
        replay = Counter(initial)
        for x in order:
            assert replay[x] >= 4
            replay[x] -= 4
            for y in neighbors(x):
                replay[y] += 1
        assert clean(replay) == final
    return {
        "valid": valid,
        "order": order,
        "deadlocked": sorted(remaining),
        "unstable_endpoint": violations,
        "final": final,
    }


def load_certificate(base_final: Mapping[Site, int], load: set[Site]) -> dict:
    """Equivalent, cheaper height-three-load specialization."""
    deg = degrees(load)
    roots = {x for x in load if base_final.get(x, 0) > 0}
    reached = set(roots)
    q = deque(roots)
    while q:
        for y in neighbors(q.popleft()):
            if y in load and y not in reached:
                reached.add(y)
                q.append(y)
    inside_bad = sorted(x for x in load
                        if not 1 <= base_final.get(x, 0) + deg[x] <= 4)
    outside_bad = sorted(x for x in (set(base_final) | halo(load)) - load
                         if base_final.get(x, 0) + deg[x] > 3)
    valid = reached == load and not inside_bad and not outside_bad
    general = once_certificate(plus(base_final, dict.fromkeys(load, 3)), load)
    assert valid == general["valid"]
    return {"valid": valid, "roots": sorted(roots),
            "unreached": sorted(load - reached),
            "inside_bad": inside_bad, "outside_bad": outside_bad}


def gate(a: int, b: int, offset: Site = (0, 0)) -> State:
    r, c = offset
    h = {(r, c): 1 + 71 * a, (r, c + 1): 1 + 71 * b,
         (r + 1, c): 2, (r + 1, c + 1): 2}
    for y, x in PORTS:
        h[(r + y, c + x)] = 3
    return h


def segment(a: Site, b: Site) -> set[Site]:
    r, c = a
    s, d = b
    assert r == s or c == d
    if r == s:
        return {(r, x) for x in range(min(c, d), max(c, d) + 1)}
    return {(x, c) for x in range(min(r, s), max(r, s) + 1)}


def polyline(*points: Site) -> set[Site]:
    return set().union(*(segment(a, b) for a, b in zip(points, points[1:])))


def branch_loop_load(scale: int = 1) -> set[Site]:
    """One root, multiple turns, one loop, degree-three/four branching."""
    s = scale
    stem = segment((-5, -1), (-14, -1))
    loop = polyline((-14, -1), (-14, -1 - 5 * s),
                    (-14 - 10 * s, -1 - 5 * s),
                    (-14 - 10 * s, -1 + 5 * s),
                    (-14, -1 + 5 * s), (-14, -1))
    branches = (segment((-9, -1), (-9, -1 - 5 * s))
                | segment((-9, -1), (-9, -1 + 5 * s)))
    return stem | loop | branches


def two_root_load(scale: int = 1) -> set[Site]:
    """A loop reached independently from both upper ports."""
    s = scale
    left = segment((-5, -1), (-10, -1))
    right = segment((-5, 2), (-10, 2))
    loop = polyline((-10, -1), (-10, -1 - 4 * s),
                    (-10 - 8 * s, -1 - 4 * s),
                    (-10 - 8 * s, 2 + 4 * s),
                    (-10, 2 + 4 * s), (-10, -1))
    return left | right | loop


def chamber_load(width: int, height: int) -> tuple[set[Site], set[Site]]:
    """A filled rectangular receiver bay with an isolated input stem."""
    assert width >= 1 and height >= 1
    left = -1 - width // 2
    chamber = set(itertools.product(range(-9 - height, -9),
                                    range(left, left + width)))
    load = chamber | segment((-5, -1), (-10, -1))
    assert len(load) == width * height + 5
    return load, chamber


def audit_arbitrary_chamber(width: int, height: int, exhaustive: bool) -> dict:
    load, chamber = chamber_load(width, height)
    cells = sorted(chamber)
    patterns = (itertools.product(range(4), repeat=len(cells)) if exhaustive else
                [tuple(0 for _ in cells), tuple(3 for _ in cells)] +
                [tuple(3 if c == -1 or r == -10 else
                       (3 * r * r + 5 * c * c + 7 * r * c + seed) % 4
                       for r, c in cells) for seed in range(4)])
    bases = {}
    for a, b in itertools.product(range(2), repeat=2):
        initial = gate(a, b)
        h, u = stabilize(initial)
        if a * b:
            assert load_certificate(h, load)["valid"]
        else:
            assert all(h.get(x, 0) == 0 for x in load)
        bases[(a, b)] = initial, h, u
    records = []
    sizes: dict[tuple[int, int], Counter[int]] = {bits: Counter() for bits in bases}
    pattern_count = 0
    for heights in patterns:
        pattern_count += 1
        decoration = dict.fromkeys(load - chamber, 3)
        decoration.update(zip(cells, heights))
        for bits, (base, base_h, base_u) in bases.items():
            h0 = plus(base_h, decoration)
            closure = set(once_certificate(h0, load)["order"])
            assert once_certificate(h0, closure)["valid"]
            h, u = stabilize(plus(base, decoration))
            assert u == plus(base_u, dict.fromkeys(closure, 1))
            assert all(u.get(x, 0) <= 1 for x in load)
            sizes[bits][len(closure)] += 1
            records.append([list(bits), list(heights), len(closure), digest(u), digest(h)])
    return {
        "width": width, "height": height, "stem_cells_outside_chamber": 5,
        "patterns": pattern_count, "source_input_cases": 4 * pattern_count,
        "all_stable_patterns_exhausted": exhaustive,
        "case_stream_sha256": hashlib.sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest(),
        "activity_histograms": [{"input": list(bits),
                                 "active_load_cells_and_case_counts": sorted(counts.items())}
                                for bits, counts in sizes.items()],
    }


def digest(h: Mapping[Site, int]) -> str:
    rows = [[r, c, n] for (r, c), n in sorted(h.items()) if n]
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def audit_load(name: str, load: set[Site]) -> dict:
    records = []
    for a, b in itertools.product(range(2), repeat=2):
        base = gate(a, b)
        assert not (set(base) & load)
        h, u = stabilize(base)
        assert not (set(u) & load)
        if a * b:
            cert = load_certificate(h, load)
            assert cert["valid"], cert
            roots = cert["roots"]
            expected = plus(u, dict.fromkeys(load, 1))
        else:
            assert all(h.get(x, 0) == 0 for x in load)
            expected = u
        initial = plus(base, dict.fromkeys(load, 3))
        actual_h, actual_u = stabilize(initial)
        assert actual_u == expected
        records.append({"input": [a, b], "unit_topplings": sum(actual_u.values()),
                        "odometer_sha256": digest(actual_u),
                        "final_sha256": digest(actual_h)})
    return {"name": name, "load_cells": len(load), "roots": roots,
            "maximum_internal_degree": max(degrees(load)[x] for x in load),
            "cases": records}


def receiver_layout(separation: int, output_length: int) -> tuple[set, set, Site, set]:
    assert separation >= 12 and output_length >= 1
    left = segment((1, 6 - separation), (1, -1))
    right = segment((1, 1), (1, separation - 5))
    receiver = (1, 0)
    output = segment((2, 0), (1 + output_length, 0))
    return left, right, receiver, output


def audit_receiver(separation: int, output_length: int) -> dict:
    left, right, receiver, output = receiver_layout(separation, output_length)
    decoration = dict.fromkeys(left | right | output, 3)
    decoration[receiver] = 2
    records = []
    for bits in itertools.product(range(2), repeat=4):
        a, b, c, d = bits
        p, q = a * b, c * d
        base = plus(gate(a, b, (0, -separation)), gate(c, d, (0, separation)))
        assert not (set(base) & set(decoration))
        base_h, base_u = stabilize(base)
        active = (left if p else set()) | (right if q else set())
        if p * q:
            active |= output | {receiver}
        cert = once_certificate(plus(base_h, decoration), active)
        assert cert["valid"], (bits, cert)
        h, u = stabilize(plus(base, decoration))
        assert u == plus(base_u, dict.fromkeys(active, 1))
        assert u.get(receiver, 0) == a * b * c * d
        assert all(u.get(x, 0) == a * b * c * d for x in output)
        records.append({"input": list(bits), "source_signals": [p, q],
                        "receiver_topplings": u.get(receiver, 0),
                        "unit_topplings": sum(u.values()),
                        "odometer_sha256": digest(u), "final_sha256": digest(h)})
    return {"core_column_offsets": [-separation, separation],
            "input_wire_cells": [len(left), len(right)],
            "output_wire_cells": len(output), "cases": records}


def audit_small_shapes() -> dict:
    """Exhaustive iff audit, including invalid and disconnected candidates."""
    cells = list(itertools.product(range(3), repeat=2))
    tested = good = 0
    for mask in range(1, 1 << len(cells)):
        active = {x for i, x in enumerate(cells) if mask >> i & 1}
        for root in sorted(active):
            initial = dict.fromkeys(active, 3)
            initial[root] += 1
            cert = once_certificate(initial, active)
            h, u = stabilize(initial)
            actual = u == dict.fromkeys(active, 1)
            assert cert["valid"] == actual
            good += actual
            tested += 1
    return {"grid_shape": [3, 3], "rooted_candidates": tested,
            "exact_unit_loads": good, "rejected_candidates": tested - good}


def counterexamples() -> list[dict]:
    """Minimal diagnostic fixtures for the two local failure modes."""
    result = []
    cases = {
        "root_with_four_load_neighbors": ({(0, 0), *neighbors((0, 0))}, (0, 0)),
        "enclosed_zero_cell": (set(itertools.product(range(3), repeat=2)) - {(1, 1)},
                               (0, 0)),
    }
    for name, (active, root) in cases.items():
        h = dict.fromkeys(active, 3)
        h[root] += 1
        cert = once_certificate(h, active)
        final, u = stabilize(h)
        assert not cert["valid"] and u != dict.fromkeys(active, 1)
        result.append({"name": name, "unit_topplings": sum(u.values()),
                       "repeated_sites": [[*x, n] for x, n in sorted(u.items()) if n > 1],
                       "unintended_sites": [list(x) for x in sorted(set(u) - active)],
                       "unstable_once_endpoint": [[*x, n] for x, n in cert["unstable_endpoint"]]})
    return result


def main() -> None:
    if not __debug__:
        raise SystemExit("Audits require assertions: do not use -O or PYTHONOPTIMIZE.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write deterministic JSON audit")
    args = parser.parse_args()
    report = {
        "schema": 1,
        "model": "sinkless threshold-four sandpile on the literal infinite square lattice",
        "load_examples": [audit_load(f"{name}_{scale}", maker(scale))
                          for name, maker in [("branched_loop", branch_loop_load),
                                              ("two_root_loop", two_root_load)]
                          for scale in (1, 2, 7)],
        "receiver_examples": [audit_receiver(s, length)
                              for s, length in ((12, 1), (20, 9), (37, 1001))],
        "arbitrary_chambers": [audit_arbitrary_chamber(2, 2, True),
                               audit_arbitrary_chamber(41, 23, False)],
        "small_shape_exhaustive": audit_small_shapes(),
        "counterexamples": counterexamples(),
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded)
        print(f"PASS: wrote {args.output}; SHA-256 {hashlib.sha256(encoded.encode()).hexdigest()}")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
