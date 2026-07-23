#!/usr/bin/env python3
"""Generate the deterministic certificate for the packet-71 AND latch."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from verify_packet71_and_latch_certificate import (
    AND_TAPS,
    CERTIFIED_FUSE_LENGTHS,
    CERTIFIED_PRECHARGED_FUSE_LENGTHS,
    CORE,
    EXPECTED_LEFT_TABLE,
    EXPECTED_RIGHT_TABLE,
    FUSE_DIRECTIONS,
    MEMORY_CELLS,
    PACKET,
    compute_bound_case,
    compute_fuse_clock_case,
    compute_fuse_write_case,
    compute_individual_clock_case,
    compute_precharged_fuse_case,
    compute_simultaneous_clock_case,
    compute_write_case,
)


OUTPUT = Path(__file__).with_name("packet71_and_latch_certificate.json")


def main() -> None:
    write_cases = [
        compute_write_case(a, b)[0]
        for a in range(4)
        for b in range(4)
    ]
    left_table = [
        [
            write_cases[4 * a + b]["and_tap_counts_left_right"][0]
            for b in range(4)
        ]
        for a in range(4)
    ]
    right_table = [
        [
            write_cases[4 * a + b]["and_tap_counts_left_right"][1]
            for b in range(4)
        ]
        for a in range(4)
    ]
    if left_table != [list(row) for row in EXPECTED_LEFT_TABLE]:
        raise AssertionError("left output table changed")
    if right_table != [list(row) for row in EXPECTED_RIGHT_TABLE]:
        raise AssertionError("right output table changed")

    boolean_inputs = tuple(
        (a, b) for a in range(2) for b in range(2)
    )
    simultaneous_clock_cases = [
        compute_simultaneous_clock_case(a, b)[0]
        for a, b in boolean_inputs
    ]
    individual_clock_cases = [
        compute_individual_clock_case(a, b, index)[0]
        for a, b in boolean_inputs
        for index in range(len(MEMORY_CELLS))
    ]
    fuse_write_cases = [
        compute_fuse_write_case(a, b, length)[0]
        for length in CERTIFIED_FUSE_LENGTHS
        for a, b in boolean_inputs
    ]
    fuse_clock_cases = [
        compute_fuse_clock_case(a, b, length)[0]
        for length in CERTIFIED_FUSE_LENGTHS
        for a, b in boolean_inputs
    ]
    precharged_fuse_cases = [
        compute_precharged_fuse_case(a, b, length)[0]
        for length in CERTIFIED_PRECHARGED_FUSE_LENGTHS
        for a, b in boolean_inputs
    ]
    support_bound_cases = [
        compute_bound_case(
            CORE,
            3,
            3,
            "witness_maximum_full_alphabet_input",
        ),
        compute_bound_case(
            (3, 3, 3, 3),
            3,
            3,
            "all_three_core_class_dominator_at_p71",
        ),
    ]

    certificate = {
        "certificate_schema_version": 1,
        "title": (
            "Packet-71 one-stabilization Boolean AND with eight "
            "arbitrary-length fuse outputs"
        ),
        "model": {
            "lattice": "ordinary infinite square lattice Z^2",
            "neighbors": "von Neumann",
            "threshold": 4,
            "sink": None,
            "outside_background": 0,
            "dynamics": (
                "conservative Abelian stabilization from finite support"
            ),
        },
        "encoding": {
            "core_row_major_A_B_D_C": list(CORE),
            "core_rows": [[1, 1], [2, 2]],
            "ports": {
                "A_input": [0, 0],
                "B_input": [0, 1],
            },
            "packet_size": PACKET,
            "full_input_alphabet": [0, 1, 2, 3],
            "write_additions": "71a at A and 71b at B",
            "and_taps": [list(site) for site in AND_TAPS],
            "memory_cells": [list(site) for site in MEMORY_CELLS],
            "outward_fuse_directions_by_memory_index": [
                list(direction) for direction in FUSE_DIRECTIONS
            ],
            "computationally_replayed_fuse_lengths": list(
                CERTIFIED_FUSE_LENGTHS
            ),
            "computationally_replayed_precharged_fuse_lengths": list(
                CERTIFIED_PRECHARGED_FUSE_LENGTHS
            ),
            "full_alphabet_readout": (
                "odometer parity at each AND tap"
            ),
            "Boolean_memory_readout": (
                "final stable height at each initially zero memory cell"
            ),
            "clock_protocol": (
                "after the Boolean write has stabilized, add three "
                "grains to each selected memory cell and stabilize again"
            ),
            "primary_integrated_protocol": (
                "initialize all eight memory ports and every cell of "
                "their outward finite fuse rays at height three, add "
                "the two Boolean data packets, and stabilize once"
            ),
        },
        "certified_claims": {
            "one_stabilization_eight_output_fuse_AND": (
                "For Boolean packet inputs, precharging all eight ports "
                "and arbitrary finite outward height-three fuse rays "
                "makes no port or fuse cell topple on false inputs. "
                "On input (1,1), every port and every fuse cell topples "
                "exactly once. No separate read clock is used."
            ),
            "full_alphabet_AND": (
                "For every a,b in {0,1,2,3}, each AND-tap odometer "
                "has parity (a mod 2)(b mod 2)."
            ),
            "Boolean_exact_taps": (
                "For a,b in {0,1}, both AND taps topple exactly ab times."
            ),
            "Boolean_eight_cell_latch": (
                "For a,b in {0,1}, all eight memory cells have write "
                "odometer zero and final height ab."
            ),
            "simultaneous_clocked_emission": (
                "Clocking all eight memory cells is globally silent "
                "when ab=0. When a=b=1, all eight clocked cells topple "
                "exactly once; the total incremental activity is 66."
            ),
            "individual_clocked_emission": (
                "Each memory cell separately has the same false-silent, "
                "true-topples-once clock semantics."
            ),
            "arbitrary_finite_outward_fuses": (
                "Precharge any common finite number L of outward ray "
                "cells to height three. The Boolean write leaves every "
                "ray cell unchanged. After adding three grains to every "
                "memory port, false cases are globally silent, while "
                "the true case makes every port and every fuse cell "
                "topple exactly once. The all-L statement follows by "
                "one-dimensional induction; L=1,2,8,32,100 are replayed "
                "in this certificate."
            ),
        },
        "left_and_tap_table_rows_a_columns_b": left_table,
        "right_and_tap_table_rows_a_columns_b": right_table,
        "write_cases": write_cases,
        "simultaneous_eight_output_clock_cases": (
            simultaneous_clock_cases
        ),
        "individual_output_clock_cases": individual_clock_cases,
        "fuse_write_cases": fuse_write_cases,
        "fuse_clock_cases": fuse_clock_cases,
        "precharged_fuse_AND_cases": precharged_fuse_cases,
        "support_bound_cases": support_bound_cases,
        "verification": {
            "verifier": "verify_packet71_and_latch_certificate.py",
            "implementation": (
                "pure Python standard library; signed sparse Z^2 "
                "dictionaries; deterministic synchronous legal waves"
            ),
            "independent_of_discovery_search_code": True,
            "checks": [
                "every wave batch expands to legal unit topplings",
                "every recorded final configuration is stable",
                "discrete-Laplacian reconstruction at every affected site",
                "mass conservation on the sinkless infinite lattice",
                "full-alphabet tap tables and reflection symmetry",
                "all Boolean memory heights and write odometers",
                "simultaneous and individual clock semantics",
                "outward fuse-ray write quiescence and clock propagation",
                "integrated precharged fuse AND in one stabilization",
                "sparse SHA-256 hashes and support bounds",
            ],
            "reproduction_commands": [
                "python3 generate_packet71_and_latch_certificate.py",
                "python3 verify_packet71_and_latch_certificate.py",
            ],
        },
        "scope_caveats": {
            "composition": (
                "The outward fuses export conventional one-toppling "
                "signals for arbitrary finite distance. A fresh copy "
                "of this module expects a 71-grain packet, so the result "
                "still does not establish a closed self-cascade. "
                "Arbitrary loads beyond the unloaded fuse terminals "
                "have not been audited."
            ),
            "clocking": (
                "The primary precharged-fuse construction uses no "
                "external read clock. The zero-height latch variant is "
                "a separate two-phase corollary that does use a clock."
            ),
            "reuse": (
                "No reset or repeated-use property is asserted; this is "
                "a one-shot state-writing primitive."
            ),
            "minimality": (
                "This certificate verifies the displayed witness only. "
                "It does not certify an exhaustive minimality search."
            ),
            "novelty": (
                "No claim of priority or literature novelty is made by "
                "this computational certificate."
            ),
            "universality": (
                "No claim of functional completeness, circuit "
                "universality, or complexity-class hardness is made."
            ),
        },
    }

    encoded = (
        json.dumps(certificate, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    OUTPUT.write_bytes(encoded)
    print(f"wrote {OUTPUT.name} ({len(encoded)} bytes)")
    print(f"certificate_sha256={hashlib.sha256(encoded).hexdigest()}")
    print("left table:")
    for row in left_table:
        print(row)
    print("right table:")
    for row in right_table:
        print(row)


if __name__ == "__main__":
    main()
