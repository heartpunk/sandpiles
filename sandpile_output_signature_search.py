#!/usr/bin/env python3
"""Find exact full-alphabet parity taps in a computed 2x2 avalanche family."""

from __future__ import annotations

import argparse

from sandpile_2x2_full_alphabet_search import stabilize


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", nargs=4, type=int, default=(0, 0, 0, 1))
    parser.add_argument("--pulse", type=int, default=2769)
    args = parser.parse_args()
    core = tuple(args.core)
    runs = {
        (a, b): stabilize(core, a * args.pulse, b * args.pulse)
        for a in range(4)
        for b in range(4)
    }
    sites = set().union(*(odometer.keys() for odometer in runs.values()))
    target_a = tuple(a & 1 for a in range(4) for b in range(4))
    target_b = tuple(b & 1 for a in range(4) for b in range(4))

    def signature(site: tuple[int, int]) -> tuple[int, ...]:
        return tuple(
            runs[a, b][site] & 1
            for a in range(4)
            for b in range(4)
        )

    def signature_word(site: tuple[int, int]) -> int:
        return sum(bit << index for index, bit in enumerate(signature(site)))

    target_a_word = sum(
        bit << index for index, bit in enumerate(target_a)
    )
    target_b_word = sum(
        bit << index for index, bit in enumerate(target_b)
    )
    a_taps = sorted(site for site in sites if signature(site) == target_a)
    b_taps = sorted(site for site in sites if signature(site) == target_b)
    southeast = [
        site for site in a_taps if site[0] > 0 and site[1] > 0
    ]
    southwest = [
        site for site in b_taps if site[0] > 0 and site[1] <= 0
    ]
    print(
        f"core={core} pulse={args.pulse} active_sites={len(sites)} "
        f"exact_a_taps={len(a_taps)} exact_b_taps={len(b_taps)}"
    )
    print("a_taps_first", a_taps[:100])
    print("b_taps_first", b_taps[:100])
    print("southeast_a_first", southeast[:100])
    print("southwest_b_first", southwest[:100])
    if southeast and southwest:
        print(
            "GEOMETRIC FULL-ALPHABET TAP PAIR",
            southeast[0],
            southwest[0],
        )
    words = {site: signature_word(site) for site in sites}
    adjacent_a_pairs = []
    adjacent_b_pairs = []
    for row, column in sites:
        site = (row, column)
        for neighbor in ((row + 1, column), (row, column + 1)):
            if neighbor not in sites:
                continue
            combined = words[site] ^ words[neighbor]
            midpoint_row = row + neighbor[0]
            midpoint_column = column + neighbor[1]
            if (
                combined == target_a_word
                and midpoint_row > 0
                and midpoint_column > 0
            ):
                adjacent_a_pairs.append((site, neighbor))
            if (
                combined == target_b_word
                and midpoint_row > 0
                and midpoint_column <= 1
            ):
                adjacent_b_pairs.append((site, neighbor))
    print("adjacent_a_pairs_first", adjacent_a_pairs[:100])
    print("adjacent_b_pairs_first", adjacent_b_pairs[:100])
    southwest_sites = [
        site for site in sites if site[0] > 0 and site[1] <= 0
    ]
    southeast_sites = [
        site for site in sites if site[0] > 0 and site[1] > 0
    ]
    word_to_southwest: dict[int, tuple[int, int]] = {}
    arbitrary_b_pair = None
    for site in southwest_sites:
        wanted = words[site] ^ target_b_word
        if wanted in word_to_southwest:
            arbitrary_b_pair = (word_to_southwest[wanted], site)
            break
        word_to_southwest.setdefault(words[site], site)
    print("arbitrary_southwest_b_pair", arbitrary_b_pair)
    word_to_southeast: dict[int, tuple[int, int]] = {}
    arbitrary_a_pair = None
    for site in southeast_sites:
        wanted = words[site] ^ target_a_word
        if wanted in word_to_southeast:
            arbitrary_a_pair = (word_to_southeast[wanted], site)
            break
        word_to_southeast.setdefault(words[site], site)
    print("arbitrary_southeast_a_pair", arbitrary_a_pair)

    def minimum_pair(
        candidates: list[tuple[int, int]], target_word: int
    ) -> tuple[int, tuple[tuple[int, int], tuple[int, int]]] | None:
        groups: dict[int, list[tuple[int, int]]] = {}
        for site in candidates:
            groups.setdefault(words[site], []).append(site)
        best = None
        for site in candidates:
            for other in groups.get(words[site] ^ target_word, []):
                if site == other:
                    continue
                distance = (
                    abs(site[0] - other[0])
                    + abs(site[1] - other[1])
                )
                candidate = (distance, tuple(sorted((site, other))))
                if best is None or candidate < best:
                    best = candidate
        return best

    print(
        "minimum_southeast_a_pair",
        minimum_pair(southeast_sites, target_a_word),
    )
    print(
        "minimum_southwest_b_pair",
        minimum_pair(southwest_sites, target_b_word),
    )
    if (southeast or adjacent_a_pairs) and (
        southwest or adjacent_b_pairs
    ):
        print("GEOMETRIC ONE/TWO-RAIL FULL-ALPHABET CROSSOVER FOUND")


if __name__ == "__main__":
    main()
