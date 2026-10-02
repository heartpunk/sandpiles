#!/usr/bin/env python3
"""Check the passive-load theorems with pinned Lean and inspect their axioms."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
VERSION = "4.27.0"
THEOREMS = (
    "passive_bound",
    "one_toppling_interface",
    "incoming_bound",
    "packet71_requires_cap18",
)
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def main() -> None:
    executable = os.environ.get("LEAN") or shutil.which("lean")
    if not executable:
        candidate = Path.home() / ".elan" / "bin" / "lean"
        if candidate.is_file():
            executable = str(candidate)
    if not executable:
        raise SystemExit(f"Lean {VERSION} is required; install it with elan or set LEAN.")
    version = subprocess.run(
        [executable, "--version"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    if not re.search(rf"version {re.escape(VERSION)}(?:,|\s|\))", version):
        raise SystemExit(f"Expected Lean {VERSION}; got: {version}")
    print(version, flush=True)
    result = subprocess.run(
        [executable, "-DwarningAsError=true", "PassiveLoad.lean"],
        cwd=ROOT, check=False, capture_output=True, text=True,
    )
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    if result.returncode:
        raise SystemExit(result.returncode)
    for theorem in THEOREMS:
        pattern = rf"'Sandpile\.{theorem}' depends on axioms: \[([^\]]*)\]"
        match = re.search(pattern, result.stdout)
        if not match:
            raise SystemExit(f"Missing theorem-level axiom report: {theorem}")
        actual = {entry.strip() for entry in match.group(1).split(",") if entry.strip()}
        if not actual <= ALLOWED_AXIOMS:
            raise SystemExit(f"Unexpected axioms in {theorem}: {sorted(actual - ALLOWED_AXIOMS)}")
    print("PASS: all four operational theorems; no sorryAx or custom axioms")


if __name__ == "__main__":
    main()
