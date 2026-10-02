#!/usr/bin/env python3
"""Edit bay_height(), then run: python3 research/try_receiver.py

The bay is WIDTH × HEIGHT; its bottom row is -10, and column -1 crosses
its center. Five height-three stem cells connect it to the upper-left
packet-71 port. Coordinates are (row, column) on the infinite square lattice.
"""

from itertools import product

from packet71_loads import (
    chamber_load, gate, load_certificate, once_certificate, plus, stabilize,
)

WIDTH, HEIGHT = 9, 7


def bay_height(row: int, column: int) -> int:
    """Change this function; return an integer from 0 through 3 at each cell.

    This example makes a height-three entry row and central spine, with
    alternating heights one and three elsewhere. Try `return 0` or `return 3`.
    """
    return 3 if row == -10 or column == -1 else 1 + 2 * ((row + column) % 2)


def main() -> None:
    if not __debug__:
        raise SystemExit("Run without -O: the verification assertions are required.")
    load, bay = chamber_load(WIDTH, HEIGHT)
    stem = load - bay
    decoration = dict.fromkeys(stem, 3)
    for row, column in sorted(bay):
        height = bay_height(row, column)
        if type(height) is not int or not 0 <= height <= 3:
            raise ValueError(f"bay_height({row}, {column}) must be an integer in 0..3")
        decoration[(row, column)] = height

    print(f"Bay: {WIDTH} × {HEIGHT}; stem: {len(stem)} cells")
    for a, b in product(range(2), repeat=2):
        base = gate(a, b)
        base_final, base_u = stabilize(base)
        assert not (set(base) & load) and not (set(base_u) & load)
        if a * b:
            assert load_certificate(base_final, load)["valid"]
        else:
            assert all(base_final.get(x, 0) == 0 for x in load)

        # First predict the active subset, then replay the entire static setup.
        predicted = set(once_certificate(plus(base_final, decoration), load)["order"])
        assert once_certificate(plus(base_final, decoration), predicted)["valid"]
        _, actual_u = stabilize(plus(base, decoration))
        assert actual_u == plus(base_u, dict.fromkeys(predicted, 1))
        outside_load = {x: n for x, n in actual_u.items() if x not in load}
        assert outside_load == base_u  # Source and every exterior site unchanged.
        assert all(actual_u.get(x, 0) in (0, 1) for x in load)
        print(f"Input {a}{b}: active stem {len(predicted & stem)}/{len(stem)}, "
              f"active bay {len(predicted & bay)}/{len(bay)}; "
              "source unchanged; exact prediction verified")
        if a * b:
            print("True-input bay activity (# = one toppling, . = none):")
            for row in sorted({r for r, _ in bay}):
                print("".join("#" if (row, column) in predicted else "."
                              for column in sorted({c for _, c in bay})))
    print("PASS: all four inputs; no repeated load topplings or changed source counts")


if __name__ == "__main__":
    main()
