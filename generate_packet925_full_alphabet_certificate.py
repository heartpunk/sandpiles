#!/usr/bin/env python3
"""Generate the compact certificate for the packet-925 crossover."""

from __future__ import annotations

import json
from pathlib import Path

from verify_packet925_full_alphabet_certificate import (
    compute_case,
    initial_state,
    stabilize_sparse,
    support_summary,
)


OUTPUT = Path("packet925_full_alphabet_certificate.json")
CORE = (0, 0, 2, 2)
PACKET = 925


def main() -> None:
    cases = [
        compute_case(CORE, PACKET, a, b)
        for a in range(4)
        for b in range(4)
    ]
    table = [
        [
            cases[4 * a + b]["output_counts_C_D"]
            for b in range(4)
        ]
        for a in range(4)
    ]
    expected = [
        [[0, 0], [300, 237], [698, 572], [1130, 941]],
        [[237, 300], [625, 625], [1073, 1010], [1531, 1405]],
        [[572, 698], [1010, 1073], [1456, 1456], [1946, 1883]],
        [[941, 1130], [1405, 1531], [1883, 1946], [2371, 2371]],
    ]
    if table != expected:
        raise AssertionError("packet-925 output table changed")

    dominating_initial = initial_state((3, 3, 3, 3), PACKET, 3, 3)
    _, dominating_odometer, _, _ = stabilize_sparse(dominating_initial)
    dominating_support = support_summary(dominating_odometer)
    if (
        dominating_support["linf_radius_from_origin"] != 27
        or dominating_support[
            "bounding_box_row_min_row_max_col_min_col_max"
        ] != [-27, 27, -26, 27]
    ):
        raise AssertionError("dominating-support bound changed")

    certificate = {
        "title": (
            "Unique minimal equal-packet full-alphabet parity crossover "
            "in the fixed stable-2x2-core encoding class on the ordinary "
            "infinite square lattice"
        ),
        "model": {
            "lattice": "Z^2 with von Neumann neighbors",
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
            "core_rows": [[0, 0], [2, 2]],
            "ports": {
                "A_input": [0, 0],
                "B_input": [0, 1],
                "C_output_for_A": [1, 1],
                "D_output_for_B": [1, 0],
            },
            "cyclic_port_order": ["A", "B", "C", "D"],
            "crossing_channels": ["A-C", "B-D"],
            "packet_size": PACKET,
            "input_alphabet": [0, 1, 2, 3],
            "input_additions": "925a at A and 925b at B",
            "readout": (
                "parity of total toppling counts at C,D after "
                "stabilizing from the original core"
            ),
            "semantic_map": "(C mod 2,D mod 2)=(a mod 2,b mod 2)",
        },
        "output_count_table_rows_a_columns_b": table,
        "cases": cases,
        "minimality": {
            "scope": (
                "All 4^4 stable backgrounds on the fixed 2x2 support, "
                "zeros elsewhere, fixed ports A,B,C,D, one equal "
                "positive integer packet p, input multiplicities "
                "a,b in {0,1,2,3}, and C,D odometer-parity readout."
            ),
            "packets_exhausted": [1, 925],
            "stable_cores_per_packet": 256,
            "core_packet_pairs_through_924": 256 * 924,
            "core_packet_pairs_through_925": 256 * 925,
            "full_hits_for_packets_1_through_924": 0,
            "full_hits_at_packet_925": 1,
            "unique_packet_925_core_row_major": list(CORE),
            "boolean_three_case_filter_hits_through_925": 12693,
            "conclusion": (
                "p=925 is globally minimal in the stated fixed "
                "equal-packet class, and (0,0,2,2) is its unique core."
            ),
            "independent_exhaustive_implementations": [
                {
                    "file": "sandpile_2x2_full_alphabet_fast.cpp",
                    "representation": (
                        "257x257 generation-stamped dense array; "
                        "incremental single-grain Abelian updates"
                    ),
                },
                {
                    "file": (
                        "sandpile_2x2_full_alphabet_"
                        "sparse_exhaustive.cpp"
                    ),
                    "representation": (
                        "unordered sparse maps on literal signed Z^2; "
                        "independent fail-fast full-alphabet test"
                    ),
                    "observed_summary": (
                        "maximum_pulse=925, core_packet_pairs=236800, "
                        "boolean_hits=12693, full_hits=1, "
                        "least_full_pulse=925"
                    ),
                },
            ],
        },
        "dense_search_boundary_exactness": {
            "dominating_configuration": (
                "all-3 2x2 core with the largest tested additions, "
                "2775 grains at each input"
            ),
            "monotonicity_argument": (
                "This initial state dominates every stable 2x2 core "
                "and every a,b<=3, p<=925 candidate, so its toppling "
                "support contains every exhaustive-search support."
            ),
            "dominating_odometer_linf_radius_from_origin": (
                dominating_support["linf_radius_from_origin"]
            ),
            "dominating_odometer_bounding_box": dominating_support[
                "bounding_box_row_min_row_max_col_min_col_max"
            ],
            "dominating_odometer_support_sites": dominating_support["sites"],
            "dense_board_side": 257,
            "dense_board_origin_margin": 128,
            "conclusion": (
                "No candidate can approach the artificial dense-board "
                "boundary; the dense exhaustive calculation equals Z^2."
            ),
        },
        "verification": {
            "pure_stdlib_sparse_infinite_verifier": (
                "verify_packet925_full_alphabet_certificate.py"
            ),
            "all_16_legal_stabilizations_checked": True,
            "all_16_final_states_stable": True,
            "all_16_discrete_laplacian_equations_checked": True,
            "all_16_mass_conservation_checks_pass": True,
            "all_16_sparse_state_and_odometer_hashes_recorded": True,
            "reproduction_commands": [
                "python3 generate_packet925_full_alphabet_certificate.py",
                "python3 verify_packet925_full_alphabet_certificate.py",
                (
                    "g++ -O3 -std=c++20 "
                    "sandpile_2x2_full_alphabet_sparse_exhaustive.cpp "
                    "-o packet_search"
                ),
                "./packet_search --maximum-pulse 925",
            ],
        },
        "composition_caveat": (
            "This is a full 16-case input-alphabet parity crossover, "
            "but its output counts are not re-encoded as 925-grain "
            "packets. It is therefore not, by itself, a cascadable "
            "packet gate or an exact-reset module."
        ),
    }
    OUTPUT.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT}")
    for a, row in enumerate(table):
        print(f"a={a}: {row}")


if __name__ == "__main__":
    main()
