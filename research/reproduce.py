#!/usr/bin/env python3
"""Reproduce the maintained sandpile witnesses and compare the new audit records.

Run from any directory. Requires Python 3.10+; --lean additionally requires
the pinned Lean compiler. Scratch reports are temporary and never overwrite
the checked-in evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def run(script: str, *args: str) -> None:
    print(f"\nChecking {script}", flush=True)
    subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean", action="store_true", help="also check all four Lean theorems")
    args = parser.parse_args()
    if not __debug__:
        raise SystemExit("Audits require assertions: do not use -O or PYTHONOPTIMIZE.")
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is required.")
    for script in (
        "verify_packet71_and_latch_certificate.py",
        "verify_halfadder672_certificate.py",
        "verify_packet925_full_alphabet_certificate.py",
    ):
        run(script)
    run("research/try_receiver.py")
    with tempfile.TemporaryDirectory(prefix="sandpiles-audit-") as directory:
        for script, record in (
            ("packet71_loads.py", "packet71_loads_audit.json"),
            ("amplifier_search.py", "amplifier_search_results.json"),
        ):
            generated = Path(directory) / record
            run(f"research/{script}", "--output", str(generated))
            expected = json.loads((ROOT / "research" / record).read_text())
            actual = json.loads(generated.read_text())
            if actual != expected:
                raise SystemExit(f"FAIL: generated {record} differs from the checked-in record")
            print(f"PASS: {record} matches the checked-in evidence", flush=True)
        figure = Path(directory) / "packet71-composition.svg"
        run("research/render_figures.py", "--output", str(figure))
        if figure.read_bytes() != (ROOT / "research/figures/packet71-composition.svg").read_bytes():
            raise SystemExit("FAIL: the generated composition figure differs from its source")
        print("PASS: the composition figure matches its executable source", flush=True)
    if args.lean:
        run("formal/passive-load/verify.py")
    print("\nPASS: all requested checks completed", flush=True)
    if not args.lean:
        print("Lean was not requested; use --lean to check the formal theorem too.")


if __name__ == "__main__":
    main()
