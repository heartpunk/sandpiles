# Passive loads cannot increase the maximum toppling count

**Research note, 2 October 2026.** This is a self-contained application of the
classical sandpile wave principle to the packet-to-fuse interface in this
repository. No claim of priority for the underlying principle is made.

The packet-71 module supplies eight outputs that each topple once on the true
Boolean input. An arbitrary initially stable passive attachment cannot turn
those signals into a 71-grain packet while preserving a one-toppling bound
at every site through which the attachment receives activity. In fact, every
site of such an attachment topples at most once, however large or highly
charged the attachment is. Combining many distinct one-shot fuse inputs does
not remove this bound.

The result concerns the material encoding of a packet. It does not preclude
composing the outputs with gates that themselves accept one-shot fuse signals.

## Model and a chronological lemma

Use the ordinary Abelian sandpile on the infinite square lattice. Heights
before the input additions are integers in `{0,1,2,3}`. A legal toppling removes
four grains from a site of height at least four and sends one grain to each
of its four neighbors. External additions occur only at a set of source sites
`S`. They may be supplied together or at different times.

Fix a finite legal sequence of unit topplings. Let `u(x)` count the topplings
of `x` in that sequence, and let `t_k(x)` be the event index of its kth
toppling, when that event exists. Neither stabilization nor a finite bounding
box is needed for the following lemma. A terminating stabilization is one
important application.

**Lemma 1 (an earlier kth toppling).** If `x` is not a source and its kth
toppling occurs, some neighbor `y` has already toppled at least k times:

\[
t_k(y)<t_k(x).
\]

**Proof.** Immediately before its kth toppling, `x` has toppled `k-1` times.
If every neighbor had also toppled at most `k-1` times, its height would be at
most

\[
3+4(k-1)-4(k-1)=3,
\]

which makes the proposed toppling illegal. Thus a neighbor's kth toppling
has already occurred. \(\square\)

Tracing these earlier kth topplings must reach a source: event indices
strictly decrease through positive integers, and the lemma applies at every
non-source encountered. The traced vertices are distinct, because each
vertex has only one kth-toppling event.

**Corollary 2 (every odometer level is rooted at a source).** For every
`k >= 1`, every connected component of

\[
\{x:u(x)\geq k\}
\]

intersects `S`. More precisely, every site in this set has a path to a source
inside the same set, with kth-toppling times strictly decreasing along the
path toward the source.

The chronology is stronger than a statement about the final stable heights.
It prevents a passive island of high toppling counts from creating its own
first kth event. The statement applies at every finite prefix of a legal
execution, so a delayed schedule cannot evade it.

## A maximum principle across any source-free cut

Let `L` be a region containing no source. It represents the entire passive
attachment, including any initially empty sites that may become active. Its
external vertex boundary is

\[
B=\{y\notin L:\text{some }x\in L\text{ is adjacent to }y\}.
\]

**Theorem 3 (passive count bound).** If every boundary vertex satisfies
`u(y) <= K`, then every vertex of `L` satisfies

\[
u(x)\leq K.
\]

**Proof.** If some `x` in `L` toppled `K+1` times, Corollary 2 would give a path
from `x` to a source, all of whose vertices topple at least `K+1` times. Since
`L` contains no source, the path must leave `L` through `B`. This contradicts
the assumed bound on `B`. \(\square\)

Equivalently, consider the earliest `(K+1)`st toppling anywhere in `L`.
At that time, all its neighbors inside `L` have toppled at most K times;
the boundary assumption gives the same bound outside `L`. Its height is
therefore at most `3 + 4K - 4K = 3`, a contradiction.

For a completed finite stabilization this can be written

\[
\max_{x\in L}u(x)\leq\max_{y\in B}u(y),
\]

where an empty or entirely inactive boundary has maximum zero. The theorem
does not depend on the area, shape, cycles, connectivity, or stored mass of
`L`. Stable height-three reservoirs are included. Activity may feed back
across the cut: the hypothesis concerns the **actual counts in the combined
execution**, not counts measured before the load was attached.

The same proofs hold for a loopless undirected multigraph with threshold
`d(x)` equal to the degree and stable height at most `d(x)-1`. Parallel edges
are counted with multiplicity. Sink edges only reduce incoming activity.
The critical inequality is

\[
d(x)-1+d(x)(k-1)-d(x)(k-1)=d(x)-1.
\]

## Consequences for packets and one-shot fuse outputs

Suppose the complete boundary of a passive converter has `u <= K`. Every
converter site then topples at most K times. If a target site `q` receives
grains from the converter through r distinct lattice edges, the number of
grains delivered along those edges is

\[
G(q)=\sum_{\substack{x\in L\\x\sim q}}u(x)\leq rK\leq4K.
\]

This counts all deliveries, including grains that may subsequently be sent
back. It is an upper bound on gross delivery, so it also bounds net delivery.

For a one-shot interface, `K=1`. Each individual edge carries at most one
grain outward from the converter, and any single lattice target receives at
most four grains from it. There cannot be 71 such deliveries to either input
cell of a fresh packet-71 module. The same observation applies to packets
672 and 925.

More quantitatively, any passive converter that delivers p grains to one
target through r lattice edges must have some interface vertex that topples
at least

\[
\left\lceil\frac{p}{r}\right\rceil
\]

times. In the most permissive case `r=4`, a 71-grain delivery requires at
least 18 topplings at some boundary vertex. Delivery through one edge
requires at least 71 topplings there. These are necessary conditions, not
constructions attaining the bounds.

For the eight-terminal packet-71 AND, apply Theorem 3 whenever all paths by
which the downstream attachment receives activity cross terminals or wire
sites that still topple at most once in the attached system. Arbitrarily many
distinct one-toppling terminals still give `K=1`: their number is irrelevant
to the maximum. A converging network can have a very large *total* number of
topplings, but cannot concentrate them into repeated topplings at one passive
site under this interface condition.

This is not a theorem that 71 externally added grains are the only way to
obtain a desired Boolean behavior. It rules out reproducing that specified
packet delivery with this passive interface. A different one-shot receiver,
a different encoding, or a jointly redesigned gate can compute the same
Boolean function without recreating the packet.

## A bridge forces return traffic

There is a sharper conclusion for an attachment with one active entrance.
Let `L` be source-free, and suppose the only cut edge with two toppled
endpoints is `s--v`, with `s` outside `L` and `v` inside. All other cut edges
therefore have a non-toppling endpoint. This condition is evaluated in the
actual execution.

**Corollary 4 (bridge feedback bound).** For every `x` in `L`,

\[
u(x)\leq u(v)\leq u(s).
\]

**Proof.** If `x` topples k times, its kth-toppling ancestor path to a source
must cross the cut. For `k >= 1`, that path can cross only `v--s`. Both `v`
and `s` therefore topple at least k times. Applying the same argument to
`v` gives `u(v) <= u(s)`. \(\square\)

The bridge carries exactly `u(s)` grains into `L` and exactly `u(v)` grains
back. Consequently an output vertex that topples k times necessarily causes
at least k return grains across the input bridge. Delivering p grains to a
single target through r load edges forces at least `ceil(p/r)` return grains.
A purported one-way count amplifier cannot hide this feedback by using a
large stable reservoir behind the bridge.

The square lattice itself has no graph-theoretic bridges. Here the bridge is
in the actual toppling support across a specified cut. A bridge in only the
initial nonzero-height support is insufficient: initially empty surrounding
sites may topple and create additional routes. The general cut theorem above
remains valid when all those routes are included.

## What assumptions matter

- **Stable passive initial state.** Height-three storage is allowed. An
  initially unstable auxiliary site is an additional source of activity and
  falls outside the passive hypothesis.
- **No external additions inside the load.** A direct grain dropped at an
  interior site is an extra source. It is not equivalent, for this theorem,
  to a grain delivered by a neighbor whose total toppling count is capped:
  the direct drop supplies an additional contribution beyond those four
  neighbors.
- **The complete physical interface.** Looking only at a named fuse terminal
  misses side contacts. Every active route from the upstream source region
  must cross the stated boundary bound.
- **Counts after attachment.** A load may make a formerly one-shot terminal
  topple repeatedly. That changes the interface contract and can enable
  multiple waves; the theorem does not say such feedback is impossible.

No reset condition, planarity argument, probabilistic assumption, or bound
on the finite size of the load is used.

## Relation to classical avalanche waves

The classical wave decomposition topples an activated source once, relaxes
the other sites while holding the source fixed, and repeats if the source is
still unstable. Each site topples at most once within a wave. This principle
is developed by E. V. Ivashkevich, D. V. Ktitarev, and V. B. Priezzhev,
[“Waves of topplings in an Abelian sandpile,” *Physica A* 209 (1994),
347–360](https://doi.org/10.1016/0378-4371(94)90188-0), and reviewed in
[D. Dhar, “The Abelian sandpile and related models,” Section 4.5](https://arxiv.org/html/cond-mat/9808047v2).

The proof above states the elementary chronological argument directly for
multiple sources and arbitrary passive cuts. Its contribution to this
repository is the explicit interface obstruction, including the 18-toppling
necessary condition for a 71-grain delivery and the bridge return bound.
The underlying no-amplification mechanism is classical; no literature
priority is asserted.

The independent computational audit is in
[`amplifier_search.py`](amplifier_search.py), with its deterministic result
record in [`amplifier_search_results.json`](amplifier_search_results.json).
Those finite checks support implementation correctness and illustrate the
scope; the all-sizes statements follow from the proofs above.
