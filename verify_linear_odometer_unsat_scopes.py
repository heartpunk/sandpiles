#!/usr/bin/env python3
"""Reproduce the bounded MILP audit behind the global rigidity theorem.

This checks the fully general (independent u and v, nonsymmetric eta)
inverse problem on ordinary Z^2.  Status 2 is HiGHS' proven-infeasible
status.  The accompanying mathematical theorem is stronger and does not
depend on these finite bounds.
"""

from __future__ import annotations

import argparse

from sandpile_linear_odometer_milp_z2 import solve_once


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    checked = 0
    for size in (5, 7, 9):
        for pulse in range(1, 25):
            search_args = argparse.Namespace(
                size=size,
                pulse=pulse,
                inset=1,
                max_odometer=64,
                timeout=args.timeout,
                symmetric=False,
                canonical_outputs=False,
                allow_zero_cross=False,
                no_output_constraints=False,
                north_output_only=False,
                no_first_topple_constraints=False,
                force_common_center=False,
                single_channel=False,
            )
            report = solve_once(search_args, seed=1)
            if report["status"] != 2:
                raise AssertionError(
                    f"expected proven infeasible, got {report}"
                )
            checked += 1
    print(
        "PASS: HiGHS proved all "
        f"{checked} scopes infeasible "
        "(n=5,7,9; p=1..24; 0<=u,v<=64)"
    )


if __name__ == "__main__":
    main()
