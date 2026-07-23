#!/usr/bin/env python3
"""Generate the certificate for the minimal packet-672 half-adder."""

from __future__ import annotations

import json
from pathlib import Path

from verify_halfadder672_certificate import (
    CORE,
    PACKET,
    compute_case,
    initial_state,
    output_tables,
    stabilize_unitwise,
    support_summary,
)


OUTPUT = Path("halfadder672_certificate.json")

EXPECTED_TABLES = {
    "sum_east": [
        [0, 63, 196, 355],
        [49, 176, 333, 514],
        [164, 317, 488, 683],
        [305, 480, 667, 864],
    ],
    "carry_east": [
        [0, 110, 294, 504],
        [76, 255, 462, 695],
        [224, 428, 650, 896],
        [398, 623, 860, 1109],
    ],
    "sum_west": [
        [0, 49, 164, 305],
        [63, 176, 317, 480],
        [196, 333, 488, 667],
        [355, 514, 683, 864],
    ],
    "carry_west": [
        [0, 76, 224, 398],
        [110, 255, 428, 623],
        [294, 462, 650, 860],
        [504, 695, 896, 1109],
    ],
}

PACKET_672_HITS = [
    {
        "core_row_major_A_B_D_C": [0, 3, 3, 2],
        "carry_taps": [[1, -2], [-1, 3]],
        "sum_taps": [[-3, 3], [-3, -2]],
    },
    {
        "core_row_major_A_B_D_C": [1, 3, 2, 2],
        "carry_taps": [[-1, 3], [1, -2]],
        "sum_taps": [[-3, 3], [3, -2], [-3, -2]],
    },
    {
        "core_row_major_A_B_D_C": [1, 3, 2, 3],
        "carry_taps": [[-1, 3], [-1, -2]],
        "sum_taps": [[-3, 3]],
    },
    {
        "core_row_major_A_B_D_C": [1, 3, 3, 2],
        "carry_taps": [[-1, -2]],
        "sum_taps": [[-3, -2]],
    },
    {
        "core_row_major_A_B_D_C": [2, 3, 2, 2],
        "carry_taps": [[-1, -2]],
        "sum_taps": [[-3, -2]],
    },
    {
        "core_row_major_A_B_D_C": [3, 0, 2, 3],
        "carry_taps": [[1, 3], [-1, -2]],
        "sum_taps": [[-3, 3], [-3, -2]],
    },
    {
        "core_row_major_A_B_D_C": [3, 1, 2, 2],
        "carry_taps": [[-1, -2], [1, 3]],
        "sum_taps": [[3, 3], [-3, 3], [-3, -2]],
    },
    {
        "core_row_major_A_B_D_C": [3, 1, 2, 3],
        "carry_taps": [[-1, 3]],
        "sum_taps": [[-3, 3]],
    },
    {
        "core_row_major_A_B_D_C": [3, 1, 3, 2],
        "carry_taps": [[-1, -2], [-1, 3]],
        "sum_taps": [[-3, -2]],
    },
    {
        "core_row_major_A_B_D_C": [3, 2, 2, 2],
        "carry_taps": [[-1, 3]],
        "sum_taps": [[-3, 3]],
    },
]


def main() -> None:
    cases = [
        compute_case(CORE, PACKET, a, b)
        for a in range(4)
        for b in range(4)
    ]
    tables = output_tables(cases)
    if tables != EXPECTED_TABLES:
        raise AssertionError("packet-672 output tables changed")

    output_pairs = sum(
        len(hit["carry_taps"]) * len(hit["sum_taps"])
        for hit in PACKET_672_HITS
    )
    if output_pairs != 28:
        raise AssertionError("packet-672 hit-pair count changed")

    dominating_initial = initial_state((3, 3, 3, 3), PACKET, 3, 3)
    _, dominating_odometer, _ = stabilize_unitwise(dominating_initial)
    dominating_support = support_summary(dominating_odometer)
    if (
        dominating_support["linf_radius_from_origin"] != 23
        or dominating_support[
            "bounding_box_row_min_row_max_col_min_col_max"
        ] != [-23, 23, -22, 23]
        or dominating_support["sites"] != 1774
    ):
        raise AssertionError("dominating-support bound changed")

    truth_table = [
        [
            [(a & 1) ^ (b & 1), (a & 1) & (b & 1)]
            for b in range(4)
        ]
        for a in range(4)
    ]

    certificate = {
        "title": (
            "Minimal equal-packet full-alphabet odometer-parity "
            "half-adder in the fixed stable-2x2-core search class on "
            "the ordinary infinite square lattice"
        ),
        "model": {
            "lattice": "Z^2 with radius-one von Neumann neighbors",
            "threshold": 4,
            "sink": None,
            "outside_background": 0,
            "stabilization": (
                "ordinary conservative Abelian sandpile stabilization "
                "with finite support"
            ),
        },
        "encoding": {
            "core_row_major_A_B_D_C": list(CORE),
            "core_rows": [[0, 3], [3, 2]],
            "input_ports": {"A": [0, 0], "B": [0, 1]},
            "packet_size": PACKET,
            "input_alphabet": [0, 1, 2, 3],
            "input_additions": "672a at A and 672b at B",
            "canonical_output_ports": {
                "SUM": [-3, 3],
                "CARRY": [-1, 3],
            },
            "all_output_ports_for_this_core": {
                "SUM": [[-3, 3], [-3, -2]],
                "CARRY": [[1, -2], [-1, 3]],
            },
            "readout": "parity of total local odometer values",
            "semantic_map": (
                "SUM=(a mod 2) XOR (b mod 2), "
                "CARRY=(a mod 2) AND (b mod 2)"
            ),
        },
        "truth_table_rows_a_columns_b_entries_sum_carry": truth_table,
        "output_count_tables_rows_a_columns_b": tables,
        "cases": cases,
        "minimality": {
            "scope": (
                "All 4^4 stable backgrounds on the fixed 2x2 support, "
                "zeros elsewhere, fixed inputs A=(0,0), B=(0,1), one "
                "equal positive integer packet p, amplitudes a,b in "
                "{0,1,2,3}, and two role-labelled external lattice "
                "sites whose odometer parities are SUM and CARRY."
            ),
            "packets_exhausted": [1, 672],
            "stable_cores_per_packet": 256,
            "core_packet_pairs_through_671": 256 * 671,
            "core_packet_pairs_through_672": 256 * 672,
            "half_adder_hits_for_packets_1_through_671": 0,
            "least_packet": 672,
            "core_packet_hits_at_packet_672": 10,
            "role_labelled_output_pairs_at_packet_672": 28,
            "packet_672_hits": PACKET_672_HITS,
            "allowing_core_sites_as_outputs": (
                "An additional exhaustive run allowing the four seeded "
                "core sites as taps produced the same least packet, "
                "same ten cores, and same 28 output pairs."
            ),
            "conclusion": (
                "p=672 is globally minimal in the stated fixed "
                "equal-packet class. The witness core is not unique at "
                "p=672."
            ),
            "independent_exhaustive_implementations": [
                {
                    "file": "audit_halfadder672_exhaustive.cpp",
                    "method": (
                        "generation-stamped dense arrays, batched legal "
                        "topplings, and a FIFO work queue"
                    ),
                    "observed_summary": (
                        "core_packet_pairs=172032, "
                        "half_adder_core_packet_hits=10, "
                        "half_adder_output_pairs=28, "
                        "hits_before_672=0, least_packet=672"
                    ),
                },
                {
                    "file": "audit_halfadder672_unit_exhaustive.cpp",
                    "method": (
                        "fresh dense-array resets, exactly one legal "
                        "toppling per event, and a LIFO work stack"
                    ),
                    "observed_summary": (
                        "core_packet_pairs=172032, "
                        "hits_before_672=0, hits_at_672=10, "
                        "output_pairs_at_672=28"
                    ),
                },
            ],
        },
        "dense_search_boundary_exactness": {
            "dominating_configuration": (
                "all-3 stable 2x2 core with the largest tested "
                "additions, 2016 grains at each input"
            ),
            "monotonicity_argument": (
                "This initial state pointwise dominates every stable "
                "2x2 core and every a,b<=3, p<=672 candidate. Odometer "
                "monotonicity therefore makes its toppling support "
                "contain every support in the exhaustive search."
            ),
            "dominating_odometer_bounding_box": dominating_support[
                "bounding_box_row_min_row_max_col_min_col_max"
            ],
            "dominating_odometer_linf_radius_from_origin": (
                dominating_support["linf_radius_from_origin"]
            ),
            "dominating_odometer_support_sites": dominating_support["sites"],
            "dense_board_side": 129,
            "dense_board_origin_margin": 64,
            "conclusion": (
                "Every audited avalanche stays at least 40 lattice "
                "steps from the artificial boundary, so the dense "
                "calculation agrees with the infinite lattice."
            ),
        },
        "verification": {
            "independent_sparse_infinite_verifier": (
                "verify_halfadder672_certificate.py"
            ),
            "independence": (
                "The verifier uses signed-coordinate dictionaries, a "
                "lexicographic heap, and exactly one legal toppling per "
                "event; it shares no stabilization code with the dense "
                "exhaustive implementation."
            ),
            "all_16_legal_stabilizations_checked": True,
            "all_16_final_states_stable": True,
            "all_16_discrete_laplacian_equations_checked": True,
            "all_16_mass_conservation_checks_pass": True,
            "all_16_sparse_state_and_odometer_hashes_recorded": True,
            "reproduction_commands": [
                "python3 generate_halfadder672_certificate.py",
                "python3 verify_halfadder672_certificate.py",
                (
                    "g++ -O3 -std=c++20 -Wall -Wextra -pedantic "
                    "audit_halfadder672_exhaustive.cpp "
                    "-o audit_halfadder672"
                ),
                "./audit_halfadder672",
                "./audit_halfadder672 --allow-core-outputs",
                (
                    "g++ -O3 -std=c++20 -Wall -Wextra -pedantic "
                    "audit_halfadder672_unit_exhaustive.cpp "
                    "-o audit_halfadder672_unit"
                ),
                "./audit_halfadder672_unit",
                (
                    "g++ -O3 -std=c++20 -Wall -Wextra -pedantic "
                    "audit_halfadder672_composition.cpp "
                    "-o audit_halfadder672_composition"
                ),
                "./audit_halfadder672_composition",
            ],
        },
        "composition_caveat": {
            "status": (
                "This is a decisive two-output Boolean primitive as a "
                "local odometer observable, but not yet a cascadable "
                "sandpile circuit gate."
            ),
            "reason": (
                "The SUM and CARRY values are irregular toppling counts, "
                "not normalized 672-grain packets. Attaching a receiver "
                "also feeds grains back through undirected Z^2 edges and "
                "can change the producing avalanche."
            ),
            "bounded_negative_audit": (
                "For each complete 16-value output-count alphabet, all "
                "256 stable 2x2 cores, each of the four core cells as "
                "the input, and every reached lattice site as a possible "
                "tap were tested as isolated abstract parity decoders. "
                "Neither the SUM nor CARRY alphabet had a hit."
            ),
            "bounded_audit_source": (
                "audit_halfadder672_composition.cpp"
            ),
            "scope_warning": (
                "That finite negative result rules out only this tiny "
                "isolated decoder family. It is not a no-go theorem for "
                "larger decoders, wires, or physically coupled modules."
            ),
        },
    }

    OUTPUT.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT}")
    print("canonical table entries are (SUM,CARRY)")
    for a, row in enumerate(truth_table):
        print(f"a={a}: {row}")


if __name__ == "__main__":
    main()
