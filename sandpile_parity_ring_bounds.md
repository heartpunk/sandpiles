# Sharp ring bounds for one-grain parity crossings

## Setting

Let

\[
Q_n=\{0,\ldots,n-1\}^2\subset\mathbb Z^2
\]

and let the background \(\eta:\mathbb Z^2\to\{0,1,2,3\}\) be zero
outside \(Q_n\).  A toppling at \(x\) removes four grains from \(x\) and
sends one grain to each von Neumann neighbor.  Write \(u_a\) for the
stabilization odometer after adding a finite configuration \(a\).

For \(x=(i,j)\in Q_n\), define its boundary depth by

\[
\rho(x)=\min(i,j,n-1-i,n-1-j).
\]

Depth zero is the boundary of the square and depth one is the first
interior ring.

## Lemma 1 (boundary additions topple at most once)

Suppose \(a(x)\in\{0,1\}\) and \(a\) is supported on the depth-zero
ring.  Then \(u_a(x)\leq 1\) for every \(x\).

### Proof

By odometer monotonicity, it is enough to use the maximal stable
background \(\eta_{\max}=3\,1_{Q_n}\).  Let

\[
v_0=1_{Q_n}.
\]

Use the positive Laplacian

\[
\Delta v(x)=4v(x)-\sum_{y\sim x}v(y).
\]

Inside \(Q_n\), \(\Delta v_0\) is zero in the interior, one at a
non-corner boundary site, and two at a corner.  Therefore

\[
\eta_{\max}+a-\Delta v_0\leq 3
\]

on \(Q_n\).  Immediately outside the square the resulting height is at
most one, and it is zero elsewhere.  Thus \(v_0\) is a nonnegative
stabilizing toppling function.  Least action gives
\(u_a\leq v_0\leq 1\).  The same conclusion for every
\(\eta\leq\eta_{\max}\) follows by monotonicity.  \(\square\)

The argument permits any number of distinct boundary sites to receive
one grain simultaneously.

More generally, if every boundary site receives at most \(q\) grains,
where \(q\in\{1,2,3\}\), then every site topples at most \(q\) times.
To see this, dominate the additions by putting \(q\) grains on *every*
boundary site and use \(v=q\,1_{Q_n}\).  At a non-corner boundary site
the Laplacian of \(v\) is \(q\), at a corner it is \(2q\), and outside
the square the resulting height is \(q\leq3\).  Thus \(u\leq v\leq q\).
In particular, even a two-grain boundary pulse cannot exploit parity:
the argument in the theorem below again collapses it to presence.
Parity can first become nontrivial at count three.

## Lemma 2 (first-interior-ring additions topple at most twice)

Assume \(n\geq 5\).  Suppose \(a(x)\in\{0,1\}\) and \(a\) is supported
on the depth-one ring.  Then \(u_a(x)\leq 2\) for every \(x\).

### Proof

Again use \(\eta_{\max}=3\,1_{Q_n}\), and define

\[
v_1(x)=
\begin{cases}
1,&\rho(x)=0,\\
2,&\rho(x)\geq 1,\\
0,&x\notin Q_n.
\end{cases}
\]

The ring-by-ring Laplacian is elementary:

- on depth at least two, \(\Delta v_1=0\);
- on depth one, \(\Delta v_1=1\), except at the four diagonal
  near-corners \((1,1)\), etc., where it is two;
- on a non-corner boundary site, \(\Delta v_1=0\);
- at a boundary corner, \(\Delta v_1=2\).

Consequently, \(\Delta v_1\geq a\) wherever \(a\) may be nonzero, and
\(\Delta v_1\geq0\) everywhere else in \(Q_n\).  The configuration
\(\eta_{\max}+a-\Delta v_1\) is stable in \(Q_n\); the only grains
outside \(Q_n\) have height one.  Hence \(v_1\) is stabilizing.  Least
action and monotonicity give

\[
u_a\leq v_1\leq2.
\]

\(\square\)

This argument also permits any number of distinct depth-one sites to
receive one grain simultaneously.

## Corollary (the forced depth-one truth table)

Let \(N,W,S,E\) be four distinct terminals in the alternating planar
order appropriate for a crossing.  Starting from the same stable
background, add one grain at \(N\), at \(W\), or at both, and denote the
three odometers by \(u_N,u_W,u_{NW}\).  Suppose the desired outputs are
the odometer parities at \(S,E\):

\[
\begin{array}{c|cc}
 &S&E\\\hline
N&1&0\\
W&0&1\\
NW&1&1
\end{array}
\quad(\bmod 2).
\]

If the input sites are both at depth zero, Lemma 1 says every odometer
value is zero or one.  Parity is therefore exactly avalanche presence.

If the input sites are both at depth one, Lemma 2 and monotonicity give

\[
u_N,u_W\leq u_{NW}\leq2.
\]

At \(S\), both \(u_N(S)\) and \(u_{NW}(S)\) are odd, hence both equal
one.  Since \(u_W(S)\) is even and no larger than \(u_{NW}(S)=1\), it
equals zero.  At \(E\), symmetrically,

\[
u_W(E)=u_{NW}(E)=1,\qquad u_N(E)=0.
\]

Thus a parity crossover at depth zero or one would have an ordinary
presence/absence truth table at its two designated outputs.

There is an important distinction between the two depths:

- At depth zero, the terminals lie on the boundary in alternating
  order, so the standard planar sandpile no-crossing theorem applies
  and rules the gate out.
- At depth one, the terminals are internal to \(Q_n\).  Toppling paths
  may use the outer ring, and two paths joining alternating points of
  the *inner* square are not topologically forced to intersect in the
  full square.  Therefore the usual boundary-terminal no-crossing
  theorem does **not** by itself rule this case out.

The rigorous depth-one conclusion is the forced exact count vector

\[
(u_N(S),u_N(E),u_W(S),u_W(E),u_{NW}(S),u_{NW}(E))
=(1,0,0,1,1,1).
\]

Whether such an internally routed presence gate exists requires a
separate construction or impossibility argument.  \(\square\)

## Lead-compatibility corollary

Although the isolated depth-one table is not ruled out, it cannot be
extended to an ordinary four-sided one-grain interface.

More precisely, suppose four lead gadgets could connect the internal
\(N,W,S,E\) terminals to four exterior boundary terminals in alternating
order, while preserving the clean one-grain presence signals forced
above.  Compose the leads with the putative internal gadget.  The
resulting finite stable configuration would route avalanche presence
from the exterior north terminal to the exterior south terminal but not
east, and from exterior west to exterior east but not south.  That is
exactly a standard boundary-terminal presence crossover, contradicting
the planar sandpile no-crossing theorem.

Thus a depth-one gadget may at best spend its one-cell outer annulus to
route around the internal terminals; it cannot simultaneously expose
four ordinary presence leads.  This is a composability obstruction, not
an isolated-truth-table impossibility.

## A depth-two construction

The following stable \(7\times7\) core, surrounded by zeros, attains
depth two:

```text
0 0 0 0 3 0 0
0 0 3 3 3 2 0
0 3 2 3 3 3 0
0 3 3 0 3 3 3
3 3 3 3 2 2 0
0 2 3 3 2 0 0
0 0 0 3 0 0 0
```

With zero-indexed ports

\[
N=(2,3),\quad W=(3,2),\quad S=(4,3),\quad E=(3,4),
\]

the exact output toppling counts are

\[
\begin{array}{c|cc}
 &S&E\\\hline
N&1&2\\
W&2&1\\
NW&3&3 .
\end{array}
\]

The even cross-talk is invisible modulo two.  Exact legal toppling
traces and final stable states are recorded in
`sandpile_parity_p1_certificate.json`.

This construction shows how count three permits parity to hide
cross-talk.  It does not, without an additional depth-one impossibility
argument, prove a depth lower bound.  In the centered axial-port family,
four distinct terminals at depth two first exist when \(n=7\).

## Scope

The supersolutions are proved for an axis-aligned square (and the same
ring calculation works for sufficiently thick axis-aligned
rectangles).  The actual nonzero support of the background may be any
subset of the square, because it is dominated by the all-three square.
For a completely arbitrary finite shape, graph-distance rings can have
concave corners whose Laplacian has the wrong sign, so the argument
does not automatically generalize.
