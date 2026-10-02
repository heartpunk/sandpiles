#!/usr/bin/env python3
"""Compile the standalone Lean theorem in Anneal's pinned Lean/Mathlib world."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "lean" / "UnitTopplingLoad.lean"


def generated_environment() -> tuple[Path, Path]:
    result = subprocess.run(
        ["cargo", "anneal", "generate", "--lib"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stdout.flush()
    if result.returncode:
        raise SystemExit(result.returncode)

    workspace_prefix = "Lean workspace generated at: "
    workspace_line = next(
        (
            line
            for line in result.stdout.splitlines()
            if line.startswith(workspace_prefix)
        ),
        None,
    )
    if workspace_line is None:
        raise SystemExit("could not parse `cargo anneal generate` output")

    workspace = Path(workspace_line.removeprefix(workspace_prefix))
    toolchain_result = subprocess.run(
        ["cargo", "anneal", "toolchain-path"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    # Anneal reports <toolchain-root>/aeneas/bin.
    toolchain_lines = [
        line for line in toolchain_result.stdout.splitlines() if line.strip()
    ]
    if not toolchain_lines:
        raise SystemExit("`cargo anneal toolchain-path` returned no path")
    toolchain = Path(toolchain_lines[-1].strip()).parent.parent
    if not workspace.is_dir() or not toolchain.is_dir():
        raise SystemExit("Anneal reported a missing workspace or toolchain")
    return workspace, toolchain


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"missing theorem source: {SOURCE}")

    workspace, toolchain = generated_environment()
    lean_root = toolchain / "lean"
    lake = lean_root / "bin" / "lake"
    if not lake.is_file():
        raise SystemExit(f"missing Anneal-managed Lake binary: {lake}")

    environment = os.environ.copy()
    environment.pop("CI", None)
    environment["LAKE_CACHE_DIR"] = str(toolchain / "lake-cache")
    environment["MATHLIB_NO_CACHE_ON_UPDATE"] = "1"
    environment["LEAN_SYSROOT"] = str(lean_root)
    environment["PATH"] = (
        f"{lean_root / 'bin'}{os.pathsep}{environment.get('PATH', '')}"
    )
    lean_library = lean_root / "lib"
    library_variable = (
        "DYLD_LIBRARY_PATH" if sys.platform == "darwin" else "LD_LIBRARY_PATH"
    )
    inherited_library_path = environment.get(library_variable)
    environment[library_variable] = (
        f"{lean_library}{os.pathsep}{lean_library / 'lean'}"
        f"{os.pathsep}{inherited_library_path}"
        if inherited_library_path
        else f"{lean_library}{os.pathsep}{lean_library / 'lean'}"
    )

    subprocess.run(
        [
            lake,
            "--keep-toolchain",
            "build",
            "Mathlib.Data.Finset.Card",
        ],
        cwd=workspace,
        env=environment,
        check=True,
    )
    subprocess.run(
        [
            lake,
            "--keep-toolchain",
            "env",
            "lean",
            "-DwarningAsError=true",
            SOURCE,
        ],
        cwd=workspace,
        env=environment,
        check=True,
    )
    print(f"PASS {SOURCE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
