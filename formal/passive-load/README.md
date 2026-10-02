# Operational passive-load bound

This independent Lean development proves the no-amplification result in
[`research/passive_amplification.md`](../../research/passive_amplification.md).
It uses only Lean's bundled `Std`, with no Mathlib, Rust translation, or
dependency downloads beyond the pinned Lean toolchain.

The four checked statements are:

- `passive_bound`: every site of an initially stable, source-free load has
  toppling count at most the maximum allowed at its complete external boundary;
- `one_toppling_interface`: boundary counts at most one imply load counts at
  most one;
- `incoming_bound`: total delivery into any load site is at most four times
  the boundary cap;
- `packet71_requires_cap18`: 71 incoming grains require a boundary allowance
  of at least 18 topplings.

These are properties of every **finite legal execution prefix**. Final
stability, existence of stabilization, and uniqueness are not assumed or
needed. Boundary counts are counts in the actual attached execution, not
counts from an isolated upstream gate.

## Model

The vertex type is unrestricted, so the theorem covers the infinite lattice.
`squareGrid` instantiates its four neighbors on `Int × Int`. A configuration's
height is its initial height plus external additions plus its four incoming
neighbor counts, minus four times its own toppling count. `Execution` starts
with all counts zero and increments one count only when that site's current
height is at least four. Counts and starting heights are natural numbers;
the reconstructed height is an integer.

The general `Grid` structure describes four incoming neighbor functions.
The theorem needs no graph axioms; `squareGrid` gives the ordinary undirected
square-lattice instance. The formal result does not claim that every arbitrary
choice of four functions is an undirected lattice.

The `load` can have any shape, and need not be finite or connected. Its sites
must start at height at most three and receive no external additions. The
boundary hypothesis includes every outside neighbor of every load site.

## Reproduce

With [elan](https://github.com/leanprover/elan) installed:

```sh
python3 formal/passive-load/verify.py
```

`lean-toolchain` pins Lean **4.27.0**. The runner accepts an explicit `LEAN`
executable, then searches `PATH` and the conventional elan location. It checks
the compiler version, compiles with warnings treated as errors, and checks the
axiom report of each of the four named theorems. No Lake project is needed.

The direct command, from this directory, is:

```sh
lean -DwarningAsError=true PassiveLoad.lean
```

Verified locally with Lean 4.27.0, commit
`db93fe1608548721853390a10cd40580fe7d22ae`, on arm64 macOS. All four theorem
reports contain only `propext`, `Classical.choice`, and `Quot.sound`; none
depends on `sorryAx` or a custom axiom.

## Scope

The proof certifies the operational maximum principle and its numerical
packet consequence. It does not certify the separate packet-71 witness,
the attached four-input conjunction geometry, the chronological path theorem,
or the bridge-feedback corollary in Lean. Those have independent mathematical
arguments and computational checks described in the research notes.

The trusted base is Lean's kernel, its standard axioms above, the compiler
binary used to check the source, and the interpretation of this explicit
operational model. The Python runner is an audit convenience, not an axiom.
