# Packet-71 AND: exact static loads and a four-input receiver

The packet-71 gate can drive finite branched and cyclic loads without changing
its internal odometer. Two separated copies can also feed a height-two
receiver, giving a one-stabilization four-input AND with an arbitrarily long
presence-output wire. These constructions use the ordinary sinkless sandpile
on the infinite square lattice, with threshold four and signed coordinates.

This extends the earlier straight, unloaded output rays. It does **not**
regenerate a 71-grain packet, so it does not establish a cascade of identical
packet gates. The four-input construction composes their presence outputs
using a conventional threshold receiver.

## 1. Exact once-toppling criterion over a nonuniform background

Let `H` be any nonnegative, finite-support integer configuration, not
necessarily stable, and let `S` be a finite proposed toppling set. Write

\[
d_S(x)=|N(x)\cap S|,\qquad
F(x)=H(x)-4\mathbf1_S(x)+d_S(x).
\]

The stabilization of `H` has odometer exactly `1_S` if and only if both of
the following conditions hold:

1. Starting with `P = ∅`, repeatedly add a site `x ∈ S \ P` for which
   `H(x) + d_P(x) ≥ 4`. This process reaches all of `S`.
2. `0 ≤ F(x) ≤ 3` for every lattice site `x`.

The first condition is equivalently the finite forbidden-subset test

\[
\forall\varnothing\ne T\subseteq S\quad
\exists x\in T:\quad H(x)+d_{S\setminus T}(x)\ge4.
\]

This criterion is exact, including for multiple roots and mixed height-two
and height-three cells. It is an operational certificate, rather than a
final-height calculation alone.

**Proof.** In the iterative test, a newly added site has never toppled and
has already received `d_P(x)` grains. Toppling it once is therefore legal.
If the process reaches `S`, its recorded order is a legal once-each schedule.
The stated `F` is its endpoint, by the literal toppling rule. If that endpoint
is stable, it is a completed stabilization, and Abelian uniqueness fixes the
odometer. Conversely, any stabilization with odometer `1_S` supplies such a
legal order and has the stated stable endpoint. If the iterative test stops
with nonempty `T`, every member of `T` fails its threshold even after all
sites in `S \ T` have toppled; this proves the subset equivalence. ∎

Only `supp(H) ∪ S ∪ N(S)` needs to be inspected. This is an exact finite
support check on the infinite lattice, not an artificial boundary.

## 2. Exact height-three load theorem

Suppose a base input configuration `η` has a known finite legal stabilization
with odometer `u` and stable final state `h`. Choose a finite set `L` of sites
that initially have height zero, and add three grains at each of them. A
particularly useful case has `u = 0` on `L`, so they are genuinely new load
cells.

The combined configuration has odometer

\[
u+\mathbf1_L
\]

if and only if:

- every connected component of `L` contains a site with `h(x) ≥ 1`;
- for every `x ∈ L`, `1 ≤ h(x) + d_L(x) ≤ 4`;
- for every `x ∉ L`, `h(x) + d_L(x) ≤ 3`.

For an intended false input, the combined odometer equals the original `u`
if and only if `h(x) = 0` at every `x ∈ L`.

**Proof.** Replay the recorded base schedule first, postponing any topplings
beyond that schedule. It
remains legal because the added grains are nonnegative. Its endpoint is
`H = h + 3·1_L`. At a load cell, at least one original grain makes it an
initial trigger; every other height-three load cell requires one already
toppled neighbor. Thus the operational condition in Section 1 becomes
component reachability from the trigger set. The endpoint is

\[
F(x)=
\begin{cases}
h(x)+d_L(x)-1,&x\in L,\\
h(x)+d_L(x),&x\notin L.
\end{cases}
\]

Its exact stability conditions are the displayed inequalities. For false
inputs, no further topplings are necessary or possible precisely when
`h + 3·1_L` is already stable, equivalent to `h|_L = 0`. Necessity of the
odometer statements follows by continuing the legal base schedule and using
Abelian uniqueness. ∎

The inequalities quantify the feedback budget. A base output port ending at
height two accepts one return grain. A triggered load cell with `h = 1`
accepts at most three neighbors in the load. An ordinary load cell with
`h = 0` can have all four neighbors in the load. Cycles and degree-four
branching are allowed. Exterior cells matter just as much as wire cells:
enclosing a zero cell with four active neighbors makes that cell topple.

The older [formal proof at its pinned commit](https://github.com/heartpunk/sandpiles/blob/3772b917954b8ba0c90ef9905c0e6e98c15e214a/formal/anneal-kernel/lean/UnitTopplingLoad.lean),
also available as [draft PR #3](https://github.com/heartpunk/sandpiles/pull/3), proves the
single-root, zero-exterior specialization with an explicit rooted order in
Lean. The nonuniform-background extension and composition here are proved
mathematically and checked by an independent executable; they have not been
added to that Lean formalization.

## 3. Packet-71 loads with branching, turns, loops, and multiple roots

Use the existing precharged packet-71 gate: core heights `(1,1,2,2)` at
`(0,0),(0,1),(1,0),(1,1)`, eight ports at height three, and additions `71a`
and `71b` to the two upper core cells. Its unloaded true-input odometer has
422 unit topplings. Each port ends at height two, and each first outward
neighbor has height one. For the three false inputs, those outward neighbors
have height zero.

The executable constructs two explicit all-scale families. All listed
segments include their endpoints, and every load site starts at height three.

**A branched loop, scale `s ≥ 1`.** Put a stem from `(-5,-1)` to `(-14,-1)`;
put both horizontal arms from `(-9,-1)` to `(-9,-1 ± 5s)`; and add the
rectangle boundary with rows `-14-10s, -14` and columns `-1-5s, -1+5s`.
There are exactly `50s+9` load cells. The sole trigger is `(-5,-1)`.
The branch at `(-9,-1)` has degree four, and the rectangular cycle is part
of the same load.

**A loop with two roots, scale `s ≥ 1`.** Put stems from `(-5,-1)` to
`(-10,-1)` and from `(-5,2)` to `(-10,2)`. Add the rectangle boundary with
rows `-10-8s, -10` and columns `-1-4s, 2+4s`. There are exactly `32s+16`
load cells. The two triggers are `(-5,-1)` and `(-5,2)`; they belong to one
connected component and may initiate it in either order.

For these coordinate families, the load conditions are immediate away from
the two first outward-neighbor positions: each trigger has one load neighbor,
all other active degrees are at most four, and no exterior cell has four
load neighbors. Near the gate, the finite base-state margin check in the
executable verifies the remaining inequality. These near-gate neighborhoods
are identical for every scale. Thus every member of either family transmits
`ab` at every load site, with unchanged base odometer. The true total is
`422 + |L|`.

The independent replay includes scales `1,2,7`:

| Load | Cells | True unit topplings |
|---|---:|---:|
| Branched loop, 1 | 59 | 481 |
| Branched loop, 2 | 109 | 531 |
| Branched loop, 7 | 359 | 781 |
| Two-root loop, 1 | 48 | 470 |
| Two-root loop, 2 | 80 | 502 |
| Two-root loop, 7 | 240 | 662 |

All four Boolean inputs are replayed for each load.

### Arbitrary stable contents in a rectangular receiver bay

There is a useful interface guarantee stronger than certifying individual
wire patterns. Suppose `L` passes the all-height-three load theorem for a
particular source input and the base odometer is zero on `L`. For **any**
static load heights `b(x) ∈ {0,1,2,3}`
supported on that same `L`, monotonicity gives

\[
u\ \le\ u_{\eta+b}\ \le\ u+\mathbf1_L.
\]

Therefore the source odometer is unchanged everywhere outside `L`, and no
load site topples more than once. The exact active subset is obtained by
the threshold-bootstrap procedure of Section 1 applied to `h+b` on `L`.
The upper comparison supplies endpoint stability automatically; equivalently,
one can check it directly from the all-height-three margin inequalities.
For any false source input satisfying `h|_L=0`, every such stable load is
entirely silent.

For a particularly simple reusable geometry, let `w,h ≥ 1`. Put a stem
from `(-5,-1)` to `(-10,-1)`. Add a filled `w×h` rectangle whose bottom row
is `-10`, whose rows extend upward, and whose columns include `-1`. The
executable chooses its left column as `-1-floor(w/2)`. This load has `wh+5`
sites. Its first stem cell is the only root, interior rectangle cells may
have degree four, and every exterior neighbor receives at most two load
grains. The gate-adjacent geometry is the same safe first outward step as
above. Consequently this is a receiver bay of **arbitrary finite size and
arbitrary stable contents**, with an unchanged packet-71 source and at most
one toppling per cell. The five stem cells outside the rectangle can be
kept at height three; the rectangle's contents are unrestricted stable heights.

The guarantee concerns the specified bay and stem, with the existing gate
background and zeros elsewhere. It does not cover additional unspecified
material that creates new routes back to the source.

The audit exhausts all 256 stable height assignments in a `2×2` bay for all
four source inputs, giving 1,024 exact static replays. On a true input the
five stem cells always topple; the number of active bay cells is `0,1,2,3,4`
for respectively `192,36,18,6,4` assignments. Every false input is silent in
the stem and bay. A `41×23` bay is also checked with six deterministic
contents, including all zero, all three, and four mixed patterns; its true
active-load sizes are `5,69,102,114,198,948`.

## 4. Two packet gates compose into a four-input presence AND

For any integer separation `s ≥ 12` and output length `ℓ ≥ 1`, put two
copies of the precharged packet gate at offsets `(0,-s)` and `(0,s)`.
Supply Boolean packet inputs `a,b` to the left copy and `c,d` to the right.
The new cells are:

- a height-three left input wire `(1,j)`, `6-s ≤ j ≤ -1`;
- a height-three right input wire `(1,j)`, `1 ≤ j ≤ s-5`;
- a height-two receiver `v = (1,0)`;
- a height-three output wire `(i,0)`, `2 ≤ i ≤ ℓ+1`.

The left wire attaches to the left gate's port `(1,5-s)`; the right wire
attaches to the right gate's port `(1,s-4)`. No extra clock or later addition
is used.

Write `p = ab` and `q = cd`. The exact combined odometer is the sum of the
two unloaded source odometers and

\[
p\mathbf1_{W_L}+q\mathbf1_{W_R}
+pq\mathbf1_{\{v\}\cup W_O}.
\]

In particular, the receiver and every output cell topple exactly `abcd`
times. The source odometers, including their other seven ports, are unchanged.

| Left signal `ab` | Right signal `cd` | Receiver final height | Output topplings |
|---:|---:|---:|---:|
| 0 | 0 | 2 | 0 |
| 0 | 1 | 3 | 0 |
| 1 | 0 | 3 | 0 |
| 1 | 1 | 1 | 1 |

**Proof for every `s,ℓ` in the stated ranges.** The separated base avalanches
have disjoint supports and halos: each base final state is supported in
rows `[-5,5]`, columns `[-5,6]` relative to its offset. Replay both source
stabilizations first, postponing every new cell. If `p = 1`, topple the left
wire toward the receiver; if `q = 1`, do the same on the right. Every such
step is legal. Each source port receives one return grain and rises from
two to three, without further toppling.

The receiver now has height `2+p+q`. With fewer than two signals it stays
stable and the output remains dormant. With both signals it topples once;
then topple the output wire outward. The output's return grain leaves the
receiver at height one. Input-wire endpoints accept the receiver's return
grain while staying below threshold. Other wire cells finish at heights
at most one. Around the junction, each exterior site receives at most two
grains. Near a source, the geometry and stable margins are exactly those of
the certified straight output wire; lengthening the empty corridor introduces
only height-zero exterior sites. The displayed legal schedule therefore ends
stable and proves the exact odometer. ∎

For the all-true input, the total number of unit topplings is

\[
844+(s-6)+(s-5)+1+\ell=834+2s+\ell.
\]

The executable replays **all 16 packet-input combinations**, including exact
source-odometer preservation, for `(s,ℓ) = (12,1), (20,9), (37,1001)`.
Their all-true totals are `859`, `883`, and `1909`.

## 5. Verification and deliberately failing geometries

Run from the repository root:

```sh
python3 research/packet71_loads.py --output research/packet71_loads_audit.json
```

The program has no third-party dependencies and imports neither the original
discovery code nor its certificate. Its simulator performs literal legal unit
topplings in a sparse dictionary indexed by `Z²`. Each run checks stability,
mass conservation, and the discrete-Laplacian reconstruction of the final
state. Each intended incremental odometer also gets a separate bootstrap-order
and endpoint certificate before comparison with the full static simulation.

The report contains deterministic odometer and final-state hashes for 24 load
cases and 48 receiver cases, plus aggregate hashes for 1,048 arbitrary-bay
cases. It additionally enumerates all 2,304 choices of
a nonempty subset of a `3×3` square and a designated root in that subset.
The once-toppling criterion agrees with independent stabilization on all of
them: 1,029 are exact unit loads and 1,275 fail.

Two explicit failure fixtures distinguish the local hazards:

- A height-three plus sign triggered at its center makes the center topple
  twice: the intended once-each endpoint has height four at the trigger.
- The boundary of a `3×3` square triggered at a corner also topples its
  zero-height central hole: four incoming grains activate an exterior site.

These show why connectivity or a visual impression of a wire is insufficient.
The complete exterior margin test is essential.

The generated JSON report has SHA-256

```text
e086b47379ec7498faefe394edebc7b7d9704014fce0909899ae717008f784eb
```

This is a finite, one-use presence circuit. No packet regeneration, reset,
functional completeness, universality, complexity hardness, or literature
priority is asserted.
