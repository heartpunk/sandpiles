# Anneal formal track

This directory contains two deliberately separated proof layers.

The Rust crate is a translation smoke kernel, not a new sandpile result. It
establishes that one pinned pipeline can:

1. compile safe Rust with `unsafe_code = "forbid"`;
2. translate the actual Rust functions through Charon and Aeneas;
3. prove their generated specifications in Lean 4; and
4. reject a missing proof in these specifications when `--allow-sorry` is
   absent.

The two functions encode the final-height arithmetic needed by the
unit-toppling load theorem:

- a non-trigger cell accepts exactly degrees 1 through 4 and returns
  `degree - 1`, which is at most 3;
- a trigger cell accepts exactly degrees 0 through 3 and returns `degree`,
  which is at most 3.

The subtraction proof is not a wrapping-arithmetic shortcut. It invokes
Aeneas's checked `U8.sub_spec`, proves that subtracting one cannot underflow,
and carries the resulting value equation into the postcondition.

The Rust crate alone does not prove graph connectivity, schedule legality,
stabilization uniqueness, the load theorem, or a circuit.

[`lean/UnitTopplingLoad.lean`](lean/UnitTopplingLoad.lean) is the next layer.
It proves that an explicit rooted order is a legal, operational once-each
execution; that `List.foldl` of the literal toppling function reaches the
closed-form endpoint; and an exact iff characterization of endpoint
stability. On the square lattice, that characterization reduces to the two
local degree conditions in the accompanying mathematical note.

The standalone Lean theorem does not re-formalize Abelian uniqueness or
least action, discharge the concrete square-lattice geometry, or prove a
circuit.

## Reproduce

The local `rust-toolchain.toml` selects the nightly matching Anneal's managed
Rust compiler. Install the exact Anneal release and its published toolchain:

```bash
cargo install cargo-anneal --version 0.1.0-alpha.24 --locked
cargo anneal setup
```

Then run, from this directory:

```bash
cargo fmt --check
cargo test
cargo anneal verify
python3 verify_lean.py
```

The Anneal verification must be run without `--allow-sorry`.
`verify_lean.py` generates Anneal's exact Lake workspace, ensures the one
required Mathlib module is built from the vendored source, and compiles the
standalone theorem with warnings treated as errors.

One hosted-sandbox caveat affected this validation run. Lean discovers its
executable through `/proc/<pid>/exe`; this environment permits the equivalent
`/proc/self/exe` path but denies the numeric form. The run therefore used a
local `LD_PRELOAD` shim that redirects only that path lookup. The official Lean
4.30.0-rc2 binary exhibited the same failure without the shim, confirming that
this was a procfs policy issue rather than a version substitution. Linux
environments with normal procfs permissions do not need this workaround.

The validated Linux x86-64 tuple is:

```text
cargo-anneal 0.1.0-alpha.24
archive SHA-256 d3d7bbcdfd2645f10e3e64a85b3e848197033992337c969a45576a3d0ec517d9
Rust 1.98.0-nightly (f8a08b688 2026-05-30)
Lean 4.30.0-rc2 (3dc1a088)
Charon 0.1.210
Aeneas 42c0e90dacf486f7d3ed5b6cde3a9a81f04915a4
```

## Trust boundary

After successful verification, neither the generated Rust specifications nor
the standalone load theorem contains `sorry`, `admit`, or a declared `axiom`.
Lean's `#print axioms` reports the same dependency set for the two audited
Rust specification theorems and the audited load-characterization theorem:

```text
[propext, Classical.choice, Quot.sound]
```

In particular, neither theorem depends on `sorryAx` or a project-specific
axiom. The packaged Anneal/Aeneas environment does contain unrelated axioms
and admitted declarations; the theorem-level dependency check is why this note
does not claim that every upstream module is admission-free.

The standalone theorem's trusted computing base is Lean, Mathlib, and the
three standard axioms above. The Rust specifications additionally trust the
Rust/Charon/Aeneas translation chain. Anneal provisions the exact toolchain
and generated workspace used for both checks.
