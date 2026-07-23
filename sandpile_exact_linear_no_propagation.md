# Exact-linear sandpile responses cannot propagate on \(\mathbb Z^2\)

This note uses the ordinary Abelian sandpile on the infinite square lattice,
with no sinks.  Write

\[
  (Lu)(x)=4u(x)-\sum_{y\sim x}u(y)
\]

for the positive graph Laplacian.  If a pulse \(m\) is stabilized with
odometer \(u\), the state change is

\[
  r=m-Lu.
\]

All functions below are integer-valued, and \(u\ge 0\) has finite support.

## Stability forces a unit residual

Suppose one background \(\eta:\mathbb Z^2\to\{0,1,2,3\}\) has

\[
  \eta+a r\in\{0,1,2,3\}^{\mathbb Z^2}
  \qquad(a=0,1,2,3).
\]

At each cell \(x\), both \(\eta(x)\) and
\(\eta(x)+3r(x)\) lie in an interval of width three.  Hence

\[
  3|r(x)|\le 3,
  \qquad\text{so}\qquad |r(x)|\le 1.
\]

For two exact-linear responses \(u,v\), with
\[
  \eta+a(m-Lu)+b(n-Lv)
\]
stable for all \(a,b\in\{0,1,2,3\}\), setting \(b=0\) or \(a=0\) gives the
same unit bound separately for each channel.  No assumption about legal
toppling order is needed for this necessary condition.

## Unit-residual bounding-box theorem

**Theorem.** Let \(m:\mathbb Z^2\to\mathbb N\) have finite support \(S\), and
let \(u:\mathbb Z^2\to\mathbb N\) be finitely supported.  If

\[
  |m-Lu|\le 1
\]

pointwise, then

\[
  \operatorname{supp}(u)\subseteq
  [\min_{s\in S}s_1,\max_{s\in S}s_1]\times
  [\min_{s\in S}s_2,\max_{s\in S}s_2].
\]

Here an empty source set is interpreted separately: it forces \(u=0\).

### Outside-support consequences

Put \(U=\operatorname{supp}(u)\).  If \(x\notin U\), then

\[
  (m-Lu)(x)=m(x)+\sum_{y\sim x}u(y).
\]

Therefore every outside vertex adjacent to \(U\) obeys

\[
  \sum_{y\sim x}u(y)\le 1.
\]

This remains true when \(x\in S\): in that case the left side above also
contains the positive integer \(m(x)\), so such a source cannot be adjacent
to \(U\) at all.

Two consequences will be used repeatedly.

1. Every cell of \(U\) adjacent to the outside has value exactly \(1\).
2. No outside vertex is adjacent to two cells of \(U\).

The first follows because a positive integer \(u(y)\) is one of the terms in
an outside neighbor's sum.  The second follows because two positive integer
terms would make that sum at least two.

### The northeast extremal cell

Assume \(U\ne\varnothing\).  Choose \(A\in U\) on the topmost occupied row,
and among that row choose the rightmost occupied cell.  The north and east
neighbors of \(A\) are outside \(U\), so \(u(A)=1\).

Only the west and south neighbors can contribute to \(Lu(A)\).  If the west
neighbor belongs to \(U\), it is itself a boundary cell: its north neighbor
is above the globally topmost occupied row.  It therefore has value \(1\).

If the south neighbor belongs to \(U\), it is also a boundary cell.  Indeed,
if the southeast cell belonged to \(U\), the outside east neighbor of \(A\)
would be adjacent both to \(A\) and to that southeast cell, contradicting
outside consequence 2.  Thus the south neighbor has an outside east
neighbor and consequently has value \(1\).

It follows that

\[
  (Lu)(A)
  =4u(A)-u(A-\mathbf e_1)-u(A-\mathbf e_2)
  \ge 4-1-1=2.
\]

If \(A\notin S\), then \(m(A)=0\) and the unit-residual hypothesis would give
\(|Lu(A)|\le1\), a contradiction.  Thus \(A\in S\).  In particular, the
largest second coordinate attained by \(U\) is attained by a source, so it
cannot exceed the largest second coordinate in \(S\).

Reflecting vertically gives the lower bound on the second coordinate.
Swapping the two coordinates, and then reflecting, gives the upper and lower
bounds on the first coordinate.  This proves the theorem.

## Single-source classification

**Corollary.** Let \(p\ge1\), \(s\in\mathbb Z^2\), and suppose

\[
  |p\delta_s-Lu|\le1.
\]

Then either

\[
  u=0,\quad p=1,
\]

or

\[
  u=\delta_s,\quad p\in\{3,4,5\}.
\]

The bounding box of the singleton source is the singleton \(\{s\}\), so a
nonzero \(u\) is supported only at \(s\).  An outside neighbor then gives
\(u(s)\le1\), hence \(u(s)=1\).  At the source,

\[
  |p-4|\le1,
\]

which gives \(p\in\{3,4,5\}\).  If \(u=0\), the source itself gives \(p\le1\).

The nonzero cases are sharp and legally realizable:

- \(p=3\): put height \(3\) at \(s\);
- \(p=4\): put any stable height at \(s\);
- \(p=5\): put height \(0\) at \(s\);

and put height \(0\) at the four neighbors.  For \(a=0,1,2,3\), adding
\(ap\) grains topples \(s\) exactly \(a\) times and no other cell topples.
The state evolves, but the response never propagates.

## Consequence for the proposed parity crossover

Suppose a proposed full-alphabet module has exact odometers

\[
  w_{a,b}=a u+b v
  \qquad(a,b\in\{0,1,2,3\})
\]

for single-site pulses at \(N\) and \(W\).  Its stable final states have the
form

\[
  \eta+a(p\delta_N-Lu)+b(p\delta_W-Lv).
\]

The unit-residual lemma and single-source classification force

\[
  \operatorname{supp}(u)\subseteq\{N\},\qquad
  \operatorname{supp}(v)\subseteq\{W\}.
\]

Thus neither response can reach even an adjacent output cell.  An
exactly-linear evolving-state carrier, and therefore an exactly-linear
parity crossover, is impossible on ordinary \(\mathbb Z^2\), for every
finite gadget size and every pulse.

This does **not** rule out:

- a one-shot Boolean parity crossover;
- a module whose internal odometer depends nonlinearly on the amplitude;
- output taps whose parities compose even though the full odometer is not
  \(a u+b v\);
- sinked or weighted graphs.

Those are genuinely different escape routes.

## Higher-dimensional extension

The bounding-box theorem extends to \(\mathbb Z^d\) for every \(d\ge2\), with

\[
  (Lu)(x)=2d\,u(x)-\sum_{y\sim x}u(y).
\]

For one coordinate \(i\), choose a cell \(A\) maximizing coordinate \(i\),
then, within that top layer, maximizing any other coordinate \(j\ne i\).
The \(+\mathbf e_i\) and \(+\mathbf e_j\) neighbors are outside.  Every
neighbor of \(A\) tangent to the top layer is a boundary cell because its
\(\mathbf e_i\) neighbor is outside.  The
\(-\mathbf e_i\) neighbor, if present, is a boundary cell because otherwise
the outside \(+\mathbf e_j\) neighbor of \(A\) would touch two support cells.
All contributing neighbors therefore have value \(1\), and at most
\(2d-2\) of them contribute.  Hence

\[
  Lu(A)\ge 2d-(2d-2)=2,
\]

forcing \(A\) to be a source.  Reflections give both bounds in every
coordinate.

For a singleton source this again forces \(u=\delta_s\), now with

\[
  p\in\{2d-1,2d,2d+1\}.
\]

The argument is specifically multidimensional.  In one dimension,
nontrivial integer tents can satisfy the analogous unit-Laplacian bound.

## Search and novelty status

The theorem was found while auditing inverse-synthesis searches.  A corrected
MILP formulation, with independent \(u,v\), a one-cell residual halo, and
ordinary infinite-lattice replay, returned infeasible for all

\[
  n\in\{5,7,9\},\quad p\in\{1,\ldots,24\},\quad
  0\le u,v\le64.
\]

The proof above removes all three bounds and explains the solver output.

As a sanity check,
`sandpile_linear_response_rigidity_test.py` checks \(718{,}305\) small finite
integer fields exhaustively and another \(100{,}000\) randomized fields.  It
finds no exception to the corner-rigidity classification.  This computation
is not used in the proof.

Targeted searches for combinations of “finitely supported integer
function,” “square-lattice discrete Laplacian,” “unit/bounded Laplacian,” and
“sandpile odometer” did not locate this exact extremal-cell statement.  That
is evidence only, not a claim of literature novelty.
