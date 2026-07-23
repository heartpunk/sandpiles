#!/usr/bin/env python3
"""Generate exact certificates for resetting parity crossovers with sinks."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from sandpile_crossing_search import stabilize
from sandpile_parity_crossing_search import stabilize_flat


OUTPUT = Path("sinked_reset_parity_crossover_certificate.json")


def laplacian(odometer: np.ndarray) -> np.ndarray:
    result = 4 * odometer.copy()
    result[:-1, :] -= odometer[1:, :]
    result[1:, :] -= odometer[:-1, :]
    result[:, :-1] -= odometer[:, 1:]
    result[:, 1:] -= odometer[:, :-1]
    return result


def final_from(
    base: np.ndarray,
    additions: tuple[tuple[tuple[int, int], int], ...],
    odometer: np.ndarray,
) -> np.ndarray:
    result = base.copy()
    for position, amount in additions:
        result[position] += amount
    return result - laplacian(odometer)


def legal_trace(
    base: np.ndarray,
    additions: tuple[tuple[tuple[int, int], int], ...],
) -> tuple[np.ndarray, np.ndarray, list[list[int]]]:
    state = base.copy()
    for position, amount in additions:
        state[position] += amount
    odometer = np.zeros_like(state)
    trace: list[list[int]] = []
    while True:
        unstable = np.argwhere(state >= 4)
        if not len(unstable):
            return state, odometer, trace
        row, column = (int(value) for value in unstable[0])
        trace.append([row, column])
        state[row, column] -= 4
        odometer[row, column] += 1
        if row:
            state[row - 1, column] += 1
        if row + 1 < state.shape[0]:
            state[row + 1, column] += 1
        if column:
            state[row, column - 1] += 1
        if column + 1 < state.shape[1]:
            state[row, column + 1] += 1


def verify_case(
    base: np.ndarray,
    additions: tuple[tuple[tuple[int, int], int], ...],
    claimed_odometer: np.ndarray,
    require_trace: bool,
) -> dict[str, object]:
    numpy_odometer = stabilize(base, additions)
    if not np.array_equal(numpy_odometer, claimed_odometer):
        raise AssertionError("NumPy stabilizer rejected claimed odometer")

    n = base.shape[0]
    flat_odometer = np.array(
        stabilize_flat(
            tuple(int(value) for value in base.flat),
            n,
            tuple(
                (position[0] * n + position[1], amount)
                for position, amount in additions
            ),
        ),
        dtype=np.int64,
    ).reshape(base.shape)
    if not np.array_equal(flat_odometer, claimed_odometer):
        raise AssertionError("flat stabilizer rejected claimed odometer")

    final = final_from(base, additions, claimed_odometer)
    if not np.array_equal(final, base):
        raise AssertionError("module did not reset exactly")

    result: dict[str, object] = {
        "additions": [
            {"position": list(position), "amount": amount}
            for position, amount in additions
        ],
        "odometer": claimed_odometer.tolist(),
        "total_topplings": int(claimed_odometer.sum()),
        "final_configuration": final.tolist(),
        "laplacian_of_odometer": laplacian(
            claimed_odometer
        ).tolist(),
    }
    if require_trace:
        traced_final, traced_odometer, trace = legal_trace(
            base, additions
        )
        if not np.array_equal(traced_final, final):
            raise AssertionError("legal trace produced a different final")
        if not np.array_equal(traced_odometer, claimed_odometer):
            raise AssertionError("legal trace produced a different odometer")
        result["legal_trace"] = trace
    return result


def two_by_two() -> dict[str, object]:
    base = np.full((2, 2), 3, dtype=np.int64)
    pulse = 24
    ports = {
        "a_input": (0, 0),
        "b_input": (0, 1),
        "a_output_c": (1, 1),
        "b_output_d": (1, 0),
    }
    u_a = np.array([[7, 2], [2, 1]], dtype=np.int64)
    u_b = np.array([[2, 7], [1, 2]], dtype=np.int64)
    u_ab = u_a + u_b
    cases = {
        "a": verify_case(
            base, ((ports["a_input"], pulse),), u_a, True
        ),
        "b": verify_case(
            base, ((ports["b_input"], pulse),), u_b, True
        ),
        "both": verify_case(
            base,
            (
                (ports["a_input"], pulse),
                (ports["b_input"], pulse),
            ),
            u_ab,
            True,
        ),
    }
    for case in cases.values():
        odometer = np.array(case["odometer"], dtype=np.int64)
        counts = [
            int(odometer[ports["a_output_c"]]),
            int(odometer[ports["b_output_d"]]),
        ]
        case["output_counts_c_d"] = counts
        case["output_parities_c_d"] = [value & 1 for value in counts]
    return {
        "name": "minimal 2x2 resetting parity crossover",
        "background": base.tolist(),
        "pulse": pulse,
        "ports": {key: list(value) for key, value in ports.items()},
        "cyclic_boundary_order": [
            "a_input",
            "b_input",
            "a_output_c",
            "b_output_d",
        ],
        "reduced_laplacian": [
            [4, -1, -1, 0],
            [-1, 4, 0, -1],
            [-1, 0, 4, -1],
            [0, -1, -1, 4],
        ],
        "green_columns": {
            "L_inverse_e_a": {
                "numerator": [7, 2, 2, 1],
                "denominator": 24,
            },
            "L_inverse_e_b": {
                "numerator": [2, 7, 1, 2],
                "denominator": 24,
            },
        },
        "full_inverse": {
            "numerator_row_major_site_order": [
                [7, 2, 2, 1],
                [2, 7, 1, 2],
                [2, 1, 7, 2],
                [1, 2, 2, 7],
            ],
            "denominator": 24,
            "site_order": [
                [0, 0],
                [0, 1],
                [1, 0],
                [1, 1],
            ],
        },
        "minimality": {
            "claim": (
                "p=24 is the least positive exact-reset pulse at "
                "either input, hence the least common exact-reset pulse "
                "and the least pulse for an exact-reset parity crossover "
                "on this fixed 2x2 encoding."
            ),
            "proof": (
                "The opposite-corner entry of L^-1 e_x is 1/24. "
                "If an integer pulse p resets exactly, its odometer is "
                "p L^-1 e_x and must be integral, so 24 divides p. "
                "The displayed p=24 integer Green columns show that "
                "this bound is attained."
            ),
        },
        "arbitrary_nonnegative_multiplicities": {
            "inputs": "add 24a at A and 24b at B for any a,b >= 0",
            "odometer_formula_rows": [
                ["7a+2b", "2a+7b"],
                ["2a+b", "a+2b"],
            ],
            "output_counts_c_d": ["a+2b", "2a+b"],
            "output_parities_c_d": ["a mod 2", "b mod 2"],
            "exact_final": "all-3 background",
            "proof": (
                "Set u=a*u_A+b*u_B. Then L*u=24a*e_A+"
                "24b*e_B and u is nonnegative, so u algebraically "
                "stabilizes back to all-3. Least action gives the true "
                "odometer v<=u. For w=u-v>=0, final stability implies "
                "L*w<=0; the sink-connected reduced-Laplacian maximum "
                "principle forces w=0. Thus v=u exactly."
            ),
        },
        "derivation": (
            "Direct multiplication gives L*u_a=24*e_a and "
            "L*u_b=24*e_b. Therefore all-3 plus the pulse minus "
            "L*u is all-3 again. The included legal traces prove these "
            "stabilizing vectors are the actual odometers."
        ),
        "cases": cases,
    }


def axial_five_by_five() -> dict[str, object]:
    base = np.full((5, 5), 3, dtype=np.int64)
    pulse = 102_960
    ports = {
        "north_input": (0, 1),
        "west_input": (3, 0),
        "south_output": (4, 1),
        "east_output": (3, 4),
    }
    u_n = np.array(
        [
            [10654, 35206, 12390, 4799, 1736],
            [7410, 14820, 9555, 5070, 2145],
            [4166, 7109, 5940, 3781, 1774],
            [2145, 3510, 3315, 2340, 1170],
            [904, 1471, 1470, 1094, 566],
        ],
        dtype=np.int64,
    )
    u_w = np.array(
        [
            [1736, 2145, 1774, 1170, 566],
            [4799, 5070, 3781, 2340, 1094],
            [12390, 9555, 5940, 3315, 1470],
            [35206, 14820, 7109, 3510, 1471],
            [10654, 7410, 4166, 2145, 904],
        ],
        dtype=np.int64,
    )
    cases = {
        "north": verify_case(
            base, ((ports["north_input"], pulse),), u_n, False
        ),
        "west": verify_case(
            base, ((ports["west_input"], pulse),), u_w, False
        ),
        "both": verify_case(
            base,
            (
                (ports["north_input"], pulse),
                (ports["west_input"], pulse),
            ),
            u_n + u_w,
            False,
        ),
    }
    for case in cases.values():
        odometer = np.array(case["odometer"], dtype=np.int64)
        counts = [
            int(odometer[ports["south_output"]]),
            int(odometer[ports["east_output"]]),
        ]
        case["output_counts_south_east"] = counts
        case["output_parities_south_east"] = [
            value & 1 for value in counts
        ]
    return {
        "name": "5x5 four-side axial resetting parity crossover",
        "background": base.tolist(),
        "pulse": pulse,
        "ports": {key: list(value) for key, value in ports.items()},
        "derivation": (
            "The displayed integer Green columns satisfy "
            "L*u_n=p*e_n and L*u_w=p*e_w exactly. Their sum is the "
            "both-input odometer."
        ),
        "cases": cases,
    }


def main() -> None:
    certificate = {
        "title": "Resetting parity crossovers in sinked square sandpiles",
        "model": (
            "Finite square von Neumann grid with threshold four and "
            "off-grid neighbors identified with a sink."
        ),
        "two_by_two": two_by_two(),
        "axial_five_by_five": axial_five_by_five(),
        "enumeration_summary": {
            "arbitrary_alternating_boundary_ports": {
                "n=2": (
                    "8/8 ordered alternating port labelings work; "
                    "least p=24"
                ),
                "n=3": (
                    "0/560 ordered alternating port labelings work "
                    "at any common exact-reset pulse"
                ),
                "n=4": (
                    "264/3960 ordered alternating port labelings work; "
                    "least p=6600"
                ),
                "n=5": (
                    "1032/14560 ordered alternating port labelings work; "
                    "least p=102960"
                ),
                "exact_exhaustive_artifact": (
                    "sinked_boundary_parity_crossover_exhaustive.json"
                ),
            },
            "four_distinct_side_axial_ports": (
                "The 5x5 witness is the smallest found through n=7."
            ),
        },
        "scope_caveat": (
            "These modules use their entire perimeter as a sink. They "
            "are exact resetting crossovers, but they are not directly "
            "tileable as internal gadgets in the sink-free interior of "
            "a larger standard grid."
        ),
        "general_exact_reset_lemma": (
            "Let L be the reduced toppling matrix of a finite "
            "dissipative graph sandpile and let s_v=L_vv-1 be the "
            "maximal stable state. If an integer u>=0 satisfies L*u=x "
            "for a nonnegative addition x, then stabilization of s+x "
            "has odometer exactly u and returns to s. Indeed least "
            "action gives v<=u; w=u-v>=0 and final stability gives "
            "L*w<=0; the reduced-Laplacian maximum principle gives w=0. "
            "Consequently integer Green columns compose linearly for "
            "arbitrary nonnegative input multiplicities."
        ),
        "verification": {
            "integer_laplacian_equations_checked": True,
            "final_exact_reset_checked": True,
            "two_independent_stabilizers_agree": True,
            "2x2_legal_traces_checked": True,
        },
    }
    OUTPUT.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
