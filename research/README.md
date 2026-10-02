# Start here: what these sandpiles compute

This project studies computation in the **ordinary two-dimensional Abelian
sandpile**. It contains exact small constructions, reproducible searches,
failed approaches, and proofs of limitations. The current useful interface
is a packet-triggered AND gate whose one-shot outputs can drive other
presence-based circuitry. A passive converter preserving those one-shot
outputs cannot regenerate the large input packets.

The work is AI-produced research stewarded by `heartpunk`. The
[contribution statement](../README.md#contribution-statement) records its
origins and distinguishes stewardship from technical authorship. Independent
reproduction, corrections, and extensions are welcome; the evidence below
is intended to make them practical.

## The model in a minute

Place a nonnegative integer number of grains at each point of the square
lattice. Heights **0, 1, 2, and 3 are stable**. A site with at least four
grains may topple: it loses four and sends one to each of its north, south,
east, and west neighbors. Those neighbors may then topple. There are no
designated sinks, walls, diagonal transfers, or altered thresholds in the
physical constructions here; unspecified sites start at zero.

After a finite configuration stabilizes, `u(x)`, its **odometer**, is the
number of times site `x` toppled. Legal toppling order does not change the
final state or odometer. This lets a proof choose a convenient order even
when the intended experiment supplies all inputs at once.

Three things must be kept separate:

| Kind of result | What is actually available |
|---|---|
| Odometer readout | An observer calculates whether a site's toppling count is odd or even. |
| Presence signal | A designated site topples once for true and zero times for false. |
| Attached circuit | A downstream component is present during the same stabilization, and the claimed behavior survives the grains it sends back. |

A numerical parity pattern is not automatically a physical signal that
another gate can consume. Attaching a receiver changes the initial
configuration and can change the original avalanche. This distinction is
central to the project.

## The earlier constructions

A **packet p** means adding `p × a` grains at one input and `p × b` at the
other. The full alphabet is `a,b ∈ {0,1,2,3}`; Boolean operation restricts
them to `{0,1}`.

| Construction | Exact result | Limit of that result |
|---|---|---|
| [Packet 925](../paper/four_terminal_odometer_parity_identity.pdf) | A four-cell seed gives crossed input-parity readouts for all sixteen full-alphabet inputs. | A crossed local observable, not an attached crossover gate. |
| [Packet 672](../sandpile_halfadder672_audit.md) | Two exterior odometer parities give XOR and AND of the input parity bits: a half-adder readout. | The output counts are not normalized packets; this is not base-four addition. |
| [Packet 71](../sandpile_packet71_and_latch_audit.md) | Exterior parity-AND readouts work over the full alphabet. For Boolean inputs, eight precharged terminals and outward fuse wires topple exactly once iff both packets arrive. | Its one-shot output encoding differs from its 71-grain input encoding. |

The minimum-packet claims in those notes are exhaustive only within their
stated search classes. They are not global lower bounds on all sandpile
implementations.

## What the October follow-up establishes

### The passive packet-converter route has a precise obstruction

An initially stable region that receives no external additions cannot have
a larger toppling count than the largest count at its complete incoming
boundary. If every interface site topples at most once **after attachment**,
every downstream site also topples at most once. Many separate one-shot
inputs do not change that conclusion.

The proof fits in one thought: before the first `(K+1)`st toppling in the
load, its four neighbors have each toppled at most K times. Its height is
at most `3 + 4K - 4K = 3`, so that toppling cannot be legal.

A target receives at most four grains when the boundary cap is one. Gross
delivery of 71 grains through its four incident edges requires a boundary
cap of at least **18**; delivery through one edge requires at least 71.
These are necessary conditions, not sufficient designs. Feedback that makes
an interface topple repeatedly changes the hypothesis.

Read [the proof and bridge-feedback consequence](passive_amplification.md)
or the [small Lean development](../formal/passive-load/README.md).

### Presence outputs can nevertheless do useful attached work

The [load and composition note](packet71_loads.md) gives an exact test for
a proposed once-each toppling set: find a legal order, then check that the
entire final configuration—including exterior deposits—is stable.
For height-three loads this becomes a connectivity test plus local height
inequalities. It supports turns, branches, loops, and multiple entry points.

It also gives a **safe receiver bay**: a rectangular region joined by an
isolated stem. Any static stable pattern inside the certified bay preserves
the source gate's odometer exactly, and every load cell topples at most
once. A threshold-propagation calculation gives the subset that activates.

Two packet-71 gates can feed a height-two receiver. It needs both incoming
grains to topple and then starts an output fuse:

```text
      71a  71b                              71c  71d
        \  /                                  \  /
    [packet-71 AND] -- signal ab --> (2) <-- signal cd -- [packet-71 AND]
                                     |
                                     v
                              output signal abcd
```

`(2)` is the receiver's initial height. This is a logical layout; the
[coordinate construction](packet71_loads.md) and
[literal lattice diagram](figures/packet71-composition.svg) show the physical
positions. It works in one stabilization, with no later clock, for every
integer gate separation `s ≥ 12` and output length `ℓ ≥ 1`. The original
gates retain their exact odometers. This is an attached four-input AND using
ordinary presence signals, not a cascade of identical packet-input gates.

### Try changing a receiver

Run this complete example from the repository root:

```sh
python3 research/try_receiver.py
```

Then edit only `bay_height(row, column)` in [the example](try_receiver.py).
Return an integer from zero through three. The default makes a central spine
and entry row at height three, with alternating heights one and three around
them. Try an empty bay (`return 0`), a full bay (`return 3`), or your own
pattern. `WIDTH` and `HEIGHT` select positive integer dimensions.

The example builds the actual stable material before supplying any packets.
For all four Boolean inputs, it predicts which cells activate and compares
that prediction with a literal infinite-lattice stabilization. It checks
every source count, all exterior counts, and the one-toppling bound. The
printed grid shows the true-input bay's activity.

Safe attachment does not require every bay cell to activate. A quiet cell
can be the correct result of its chosen height. The guarantee applies to
this geometry and stable contents; adding material elsewhere needs a new
boundary check.

## Which evidence supports which claim?

| Claim | Evidence to inspect | Scope |
|---|---|---|
| Earlier packet truth tables | Linked audit notes, stored certificates, independent Python/C++ programs | Exact recorded constructions and explicitly bounded searches |
| Passive cut bound and one-shot corollary | [`PassiveLoad.lean`](../formal/passive-load/PassiveLoad.lean): `passive_bound`, `one_toppling_interface` | Every finite legal execution prefix in the explicit model; includes the infinite square lattice |
| Incoming bound and numerical 18 | Same file: `incoming_bound`, `packet71_requires_cap18` | All four incoming edges, actual attached boundary counts |
| Kth-toppling paths and bridge return bound | [Self-contained mathematical proofs](passive_amplification.md) | General statements; not included in the Lean proof |
| Exact load criterion, safe bay, all-size circuit families | [Mathematical arguments](packet71_loads.md) | General conditions and the coordinate families stated there; not Lean-formalized |
| Concrete attached examples | [`packet71_loads.py`](packet71_loads.py) and [deterministic audit](packet71_loads_audit.json) | 24 load cases, 48 four-input cases, 1,048 bay cases, 2,304 rooted small shapes, and two diagnostic failures |
| Boundary assumptions and feedback pitfalls | [Amplifier audit](amplifier_findings.md), [executable](amplifier_search.py) | Finite examples and counterexamples; not a proof by exhaustive search of all loads |

Lean checks the four named theorems under their explicit definitions and
hypotheses. It does not certify every claim in the repository. Its runner
reports the trusted standard axioms and rejects `sorryAx`; see the
[formal trust description](../formal/passive-load/README.md#scope).

Avalanche waves, fuse signaling, and threshold gates are classical sandpile
ingredients. The wave foundation goes back to
[Ivashkevich, Ktitarev, and Priezzhev (1994)](https://doi.org/10.1016/0378-4371(94)90188-0).
The repository-specific work is the exact seeds and tables, certificates,
scoped searches, explicit attachment geometries, and their application to
this encoding problem. No claim of literature priority, functional
completeness, universality, or a composable crossover is made.

## Reproduce the short path

From the repository root, use Python **3.10 or newer**:

```sh
python3 research/reproduce.py
```

This checks all three earlier packet certificates, regenerates both new
computational audits in temporary files, and compares their contents with
the checked-in records. It uses only the Python standard library and should
end with **`PASS: all requested checks completed`**. The runner also works
from another directory when given its absolute path.

To include the four formal theorems, install the pinned Lean toolchain
through [elan](https://github.com/leanprover/elan), then run:

```sh
python3 research/reproduce.py --lean
```

The formal runner requires Lean **4.27.0**, compiles with warnings as errors,
and checks all four theorem axiom reports. The
[CI workflow](../.github/workflows/research-checks.yml) is configured to
repeat the Python audits on versions 3.10 and 3.14 and check the Lean proof.

For a narrower check, the commands remain available individually:

```sh
python3 verify_packet71_and_latch_certificate.py
python3 research/packet71_loads.py --output /tmp/packet71_loads_audit.json
python3 formal/passive-load/verify.py
```

The load audit's small-shape section records **1,029 accepted and 1,275
rejected** candidates. The three all-true four-input examples have **859,
883, and 1,909** topplings. Each older audit note also gives the commands
for its longer exhaustive C++ searches; these are outside the short runner.

## Open questions

- What additional one-shot receivers can fit in the safe bay and preserve
  their input gates? Supply exact input and output contracts, not only a
  Boolean truth table.
- Can a reusable checker compose many certified load regions and check every
  shared boundary automatically?
- Can the all-size load and four-input proofs be added to Lean, including
  the bridge from coordinate geometry to legal toppling schedules?
- Can repeated interface activity be deliberately controlled, or a different
  material encoding make the parity readouts useful? Such a proposal must
  account for return grains and the actual counts after attachment.
- Which exact constructions or observations already occur in the literature?
  A sourced identification or correction is a valuable contribution.

Searching larger stable passive reservoirs while insisting that every
incoming interface stays one-shot cannot solve packet regeneration; the
cut theorem rules out that whole route. See
[how to contribute](../CONTRIBUTING.md) for a compact reproducibility and
claim checklist.
