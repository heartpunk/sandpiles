# Exact-reset no-go theorems for planar full-alphabet sandpile crossings

These statements concern the standard Abelian sandpile on the infinite square
lattice \(\mathbb Z^2\).  A configuration is stable when every height is in
\(\{0,1,2,3\}\).  For a finitely supported function
\(f:\mathbb Z^2\to\mathbb Z\), use the positive-Laplacian convention

\[
(\Delta f)(x)=4f(x)-\sum_{y\sim x}f(y).
\]

Thus, if a stabilization has odometer \(u\), adding \(p\) grains at \(s\)
changes the configuration by

\[
p\delta_s-\Delta u.
\]

## Lemma 1: a one-grain pulse cannot exactly reset a finite core

Suppose a one-grain pulse at \(s\) has a nonzero, finitely supported odometer
\(u\), every cell in a finite core \(C\) returns to its initial height, and
every cell outside \(C\) remains untoppled.  Assume \(s\in C\), as is necessary
for a transmitting reset gate.  Then this is impossible.

Indeed, exact reset on \(C\) gives

\[
\Delta u=\delta_s\qquad\text{on }C.
\]

An outside cell \(x\notin C\), which does not topple, receives

\[
q(x)=\sum_{y\sim x}u(y)\ge 0.
\]

Toppling on the infinite square lattice preserves both total mass and the two
first spatial moments.  Since exactly one grain was added and the core reset,

\[
\sum_{x\notin C}q(x)=1,\qquad
\sum_{x\notin C}x\,q(x)=s.
\]

The first equality and integrality say that \(q\) is one grain at a single
outside vertex \(z\).  The second equality then says \(z=s\), contradicting
\(s\in C\) and \(z\notin C\).

This explains why a resetting construction has to begin with pulses larger
than one grain.  It does not obstruct a transient, evolving-state one-grain
gate.

## Theorem 2: two exact-reset channels have disjoint supports

Let \(N,W\in\mathbb Z^2\) be sources and let
\(u,v:\mathbb Z^2\to\mathbb N\) be nonzero, finitely supported integer
odometers for one positive north pulse and one positive west pulse,
respectively.  Write

\[
U=\operatorname{supp}(u),\qquad
V=\operatorname{supp}(v),\qquad
C=U\cup V.
\]

Assume:

1. \(N\in U\), \(W\in V\), and the pulses contain \(p_N,p_W>0\) grains.
2. Each pulse exactly resets the whole common core \(C\):

   \[
   \Delta u=p_N\delta_N\quad\text{on }C,\qquad
   \Delta v=p_W\delta_W\quad\text{on }C.
   \]

3. Cells outside \(C\) are initially zero, never topple, and act only as
   finite-capacity garbage for inputs \(a,b\in\{0,1,2,3\}\).  Equivalently,
   defining the one-pulse deposits

   \[
   q_u(x)=\sum_{y\sim x}u(y),\qquad
   q_v(x)=\sum_{y\sim x}v(y)
   \quad (x\notin C),
   \]

   the input \((a,b)=(3,3)\) must leave

   \[
   3q_u(x)+3q_v(x)\le 3,
   \]

   or, by integrality,

   \[
   q_u(x)+q_v(x)\le 1
   \quad\text{for every }x\notin C.
   \]

Then

\[
U\cap V=\varnothing.
\]

### Proof

First, \(U\) is connected.  If \(K\) were a connected component of \(U\) not
containing \(N\), the reset equation would give \(\Delta u=0\) on \(K\).
But summing the Laplacian over \(K\) gives

\[
\sum_{x\in K}\Delta u(x)
=
\sum_{\substack{x\in K,\ y\notin K\\x\sim y}}
\bigl(u(x)-u(y)\bigr).
\]

Because \(K\) is a support component, every \(u(x)\) on the inner endpoint is
positive and every \(u(y)\) on the outer endpoint is zero.  The right side is
strictly positive, contradicting the zero left side.  Thus every support
component contains \(N\), so there is only one.  The same argument makes \(V\)
connected.

Next, there is no lattice edge from \(U\) to \(C\setminus U\).  If
\(x\in C\setminus U\), then \(u(x)=0\), and \(x\ne N\).  Exact reset at \(x\)
therefore says

\[
0=\Delta u(x)=-\sum_{y\sim x}u(y).
\]

All terms are nonnegative, so every neighbor also has \(u(y)=0\).  Swapping
\(u\) and \(v\) gives the analogous no-edge statement for \(V\).

Suppose now that \(U\cap V\ne\varnothing\).  Start at a common vertex and
follow a path in the connected set \(V\).  If that path ever left \(U\), its
first exiting edge would run from \(U\) to
\(V\setminus U\subseteq C\setminus U\), contradicting the preceding
no-edge statement.  Hence \(V\subseteq U\).  By symmetry \(U\subseteq V\), so
\(U=V=C\).

The common support is finite and nonempty, so it has a boundary edge
\(y\sim x\) with \(y\in C\) and \(x\notin C\).  Since both odometers are
positive at every vertex of their common support,

\[
q_u(x)\ge u(y)\ge 1,\qquad
q_v(x)\ge v(y)\ge 1.
\]

Consequently \(q_u(x)+q_v(x)\ge2\), contradicting the garbage-capacity
hypothesis.  Therefore \(U\cap V=\varnothing\).  \(\square\)

## Corollary 3: no planar full-alphabet crossover of this reset type

Assume the gadget lies in a topological disk and has four distinct terminal
vertices \(N,W,S,E\) on its boundary in that cyclic order.  Assume the north
one-pulse support contains \(N\) and \(S\), while the west one-pulse support
contains \(W\) and \(E\).

Connectedness supplies a lattice path in \(U\) from \(N\) to \(S\) and a
lattice path in \(V\) from \(W\) to \(E\).  Two paths joining alternating
boundary pairs in a disk must intersect (the planar crosscut/Jordan-curve
lemma).  Square-lattice edges only cross at lattice vertices, so this gives
\(U\cap V\ne\varnothing\), contradicting Theorem 2.

Hence an exact-reset, inert-garbage planar crossover for the full alphabet
\(\{0,1,2,3\}\) does not exist for **any** pulse sizes, support shapes, or
finite dimensions.

## Scope

The obstruction is deliberately sharp.  It rules out the proposed
architecture in which both channels reset a common finite core after every
pulse and all expelled mass accumulates in outside cells that never topple.
It does **not** rule out:

- a junction whose central state evolves across amplitudes \(0,1,2,3\);
- garbage cells that topple as part of a larger controlled mechanism;
- a finite graph with designated sinks;
- a one-shot Boolean parity crossover.

The controlled-state plus-junction search targets the first escape hatch.
