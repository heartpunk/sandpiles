# Audit: packet-71 parity AND and an eight-terminal transducer

## Result at a glance

On the ordinary sinkless Abelian sandpile on the infinite square lattice,
start from the stable core

```text
1 1    <- packet inputs A, B
2 2
```

For Boolean inputs \(a,b\in\{0,1\}\), precharge eight output ports and any
finite length of their outward one-cell-wide fuse wires to height three.
Add \(71a\) grains at \(A=(0,0)\) and \(71b\) grains at \(B=(0,1)\), then
stabilize once.

- On the three false inputs, no output port or fuse cell topples.
- On input \((1,1)\), every output port and every fuse cell topples exactly
  once.

Thus each of eight unloaded output terminals carries ordinary avalanche
presence equal to \(a\mathbin{\mathrm{AND}}b\), at an arbitrarily chosen
finite distance. There is no external read clock in this primary
construction.

The same four-cell core also has a stronger full-alphabet property when the
ports and fuses are absent. Two remote sites,

\[
Q_L=(3,-1),\qquad Q_R=(3,2),
\]

have odometer parities

\[
u_{a,b}(Q_L)\equiv u_{a,b}(Q_R)
\equiv (a\bmod 2)(b\bmod 2)\pmod 2
\]

for every \(a,b\in\{0,1,2,3\}\).

The zero-height version of the eight output ports stores eight stable copies
of AND. Adding three grains later recovers the fuse emission as a two-phase
latch variant.

This is an exact packet-input/presence-output one-shot AND module with eight
conventional fuse outputs. Fuse signaling, presence-AND, and branching are
classical sandpile-circuit ingredients; the certified contribution here is
the packet-to-presence interface. Its output signals are not yet regenerated
into the 71-grain input packets expected by another copy.

## Model and coordinates

The threshold is four. A toppling removes four grains and sends one grain to
each von Neumann neighbor. There is no sink and no finite boundary.

The core is supported at

\[
A=(0,0),\quad B=(0,1),\quad D=(1,0),\quad C=(1,1)
\]

with row-major heights \((1,1,2,2)\). In the unprecharged and full-alphabet
variants, all unlisted sites start at height zero.

The eight memory cells are

\[
\begin{aligned}
R=\{&
(-4,-1),(-4,2),(-1,-4),(-1,5),\\
&(1,-4),(1,5),(4,-1),(4,2)\}.
\end{aligned}
\]

For the integrated fuse gate, every \(r\in R\) starts at height three.
The two ports with row \(-4\) point upward, the two with row \(4\) point
downward, the two with column \(-4\) point left, and the two with column
\(5\) point right. If \(d_r\) is this outward unit vector, a fuse of length
\(L\) consists of

\[
W_L(r)=\{r+k d_r:1\leq k\leq L\},
\]

with every fuse cell initially at height three. The eight rays are disjoint.
The case \(L=0\) uses the precharged ports themselves as the terminals.

## The one-stabilization fuse-AND theorem

For every finite \(L\geq0\), every Boolean input \(a,b\in\{0,1\}\), every
port \(r\in R\), and every cell \(x\in W_L(r)\), the odometer of the
precharged construction obeys

\[
u_{a,b}(r)=ab,\qquad u_{a,b}(x)=ab.
\]

Consequently all eight terminals transmit avalanche presence exactly when
both input packets are present.

For the true input, the total activity is

\[
422+8L
\]

unit topplings. The largest odometer value anywhere in the gate is 43. On a
false input, the internal packet avalanche may still occur, but all eight
ports and every fuse cell remain untoppled.

The certificate replays all four Boolean inputs jointly for

```text
L = 0, 1, 2, 8, 32, 100, 500.
```

The all-\(L\) statement has a short proof. First use the zero-height latch
calculation below: after the unprecharged write, every port has height \(ab\)
and has not toppled. Abelianity allows the static addition of three grains at
each port to be moved from after the write to before it.

For a false input, the ports therefore remain at height three, so neither a
port nor a fuse cell becomes unstable. For the true input, the no-wire
precharged calculation makes each port topple once and finish at height two.
Postpone every newly unstable fuse cell until the finite base avalanche is
stable. Then topple each ray outward in order. A height-three fuse cell
receives one grain from its predecessor, topples once, and sends one grain
to its successor. The return grain from the first fuse cell raises its port
from two to three, so the port cannot topple again. Each internal fuse cell
similarly receives at most one return grain from its successor after
toppling. Side deposits are at most one because the rays are disjoint and
separated. The resulting configuration is stable, completing a legal
toppling sequence in which every rail cell topples exactly once.

## Scoped exhaustive minimality

A separate C++ audit exhausts the following class:

- all \(4^4=256\) stable backgrounds on the fixed \(2\times2\) support,
  with zeros elsewhere;
- equal positive integer packets \(1\leq p\leq71\);
- the two top core cells as inputs;
- all sixteen amplitudes \(a,b\in\{0,1,2,3\}\);
- every reached site outside the four-cell core as a possible odometer-parity
  tap;
- target parity \((a\bmod2)(b\bmod2)\).

It checks 290,816 core-packet-input configurations. There are no exterior
full-alphabet parity-AND taps for \(p\leq70\). At \(p=71\), there are 16
oriented core/tap hits. The reflection-symmetric core
\((1,1,2,2)\) is one of them and has the two taps \(Q_L,Q_R\) used here.

Considering only reached sites is exhaustive: a valid AND tap must have odd
odometer on the odd-odd inputs and therefore must be reached.

The dense search uses a \(65\times65\) window. The all-height-three core with
the maximum tested additions pointwise dominates every search case. An
independent sparse replay puts its odometer in rows \([-7,7]\), columns
\([-6,7]\), over 174 sites, leaving a large exact margin inside the dense
window.

Thus \(p=71\) is minimal only in this stated equal-packet, stable-\(2\times2\)
core, exterior-one-tap class. This says nothing about larger backgrounds,
unequal packets, multiple-rail readouts, different input placements, or
other encodings.

## The full-alphabet AND tables

Rows are \(a=0,1,2,3\); columns are \(b=0,1,2,3\).
The exact odometer table at \(Q_L\) is

```text
 0   0   2   6
 0   1   6  13
 4   8  14  22
10  15  24  31
```

The table at \(Q_R\) is its input-reflected counterpart:

```text
 0   0   4  10
 0   1   8  15
 2   6  14  24
 6  13  22  31
```

Both tables have the parity pattern

```text
0 0 0 0
0 1 0 1
0 0 0 0
0 1 0 1
```

which is exactly parity-AND.

The computation is nonlinear in the input amplitudes. In particular, this is
not an exact-linear carrier of the form \(u_{a,b}=a u+b v\).

## Boolean write and stored fanout

For \(a,b\in\{0,1\}\), both remote taps topple exactly \(ab\) times, not only
with the correct parity:

```text
(a,b)    u(QL)  u(QR)
(0,0)      0      0
(0,1)      0      0
(1,0)      0      0
(1,1)      1      1
```

Every memory cell \(r\in R\) satisfies, after the write stabilization,

\[
u_{a,b}(r)=0,\qquad \eta'_{a,b}(r)=ab.
\]

Thus the memory cells are not merely readout taps. They are quiescent during
the write and store eight material copies of the Boolean result as stable
heights zero or one.

The Boolean write statistics are:

| input | total unit topplings | toppled sites | maximum site count |
|---|---:|---:|---:|
| \((0,0)\) | 0 | 0 | 0 |
| \((0,1)\) | 109 | 22 | 27 |
| \((1,0)\) | 109 | 22 | 27 |
| \((1,1)\) | 356 | 44 | 42 |

## Zero-height latch and clocked corollary

If the ports and outward rays start at zero instead, the Boolean write stores
the exact height bit \(ab\) at all eight ports as described above. After that
write has stabilized, add three grains to all eight ports and stabilize
again.

- For \((0,0),(0,1),(1,0)\), every memory cell changes from height zero to
  height three. No site anywhere topples.
- For \((1,1)\), all eight memory cells change from height one to height four
  and become unstable. Each of the eight clocked cells topples exactly once.

In the true simultaneous-clock case the incremental avalanche has exactly
66 unit topplings on 66 distinct sites. No site topples twice. Its odometer
support has rows \([-4,4]\), columns \([-4,5]\), and
\(\ell_\infty\) radius five.

Each memory cell was also clocked separately in all four Boolean write
states. Every false case was globally silent, and in the true case the
selected cell toppled exactly once. The amount of secondary activity depends
on which output is selected, so "topples once at the selected output" should
not be misread as an isolated one-toppling avalanche.

If outward height-three rays are present during this two-phase variant, they
remain exactly at height three throughout the write. On the true clock, every
fuse cell topples once; on a false clock, the entire incremental stabilization
is silent. The certificate replays this at \(L=1,2,8,32,100\). This clocked
description is also the Abelian decomposition used in the proof of the
primary one-stabilization theorem.

## Independent verification

`verify_packet71_and_latch_certificate.py` is a pure-standard-library sparse
verifier on signed coordinates of the literal infinite lattice. It does not
import the discovery programs, use a finite array, or add a sink.

It stabilizes by deterministic synchronous legal waves. At each wave, every
currently unstable site performs \(\lfloor h/4\rfloor\) topplings. Those
batches expand to legal unit topplings because the site is already unstable
before receiving any grains from the same wave.

For every recorded transition, the verifier checks:

- legality of every batched toppling;
- final stability;
- the discrete-Laplacian reconstruction
  \(\eta'=\eta+\text{additions}-\Delta u\);
- mass conservation on the sinkless lattice;
- exact tap counts, memory heights, and clock semantics;
- precharged one-stabilization fuse outputs and fuse final states;
- sparse SHA-256 hashes of the initial state, odometer, and final state;
- support sizes, bounding boxes, and radii.

The largest witness input, \((a,b)=(3,3)\), has 3,510 unit topplings on
174 sites. Its odometer support has rows \([-7,7]\), columns \([-6,7]\),
and \(\ell_\infty\) radius seven. The final deposited-grain support is
contained in rows \([-8,8]\), columns \([-7,8]\).

For comparison, the pointwise-dominating all-height-three \(2\times2\) core
with the same maximum additions has 3,570 unit topplings, the same odometer
bounding box, and final support in the same one-cell halo. The verifier is
sparse and boundary-free, so this bound is descriptive rather than needed
to justify an artificial cutoff.

The deterministic machine-readable record is
`packet71_and_latch_certificate.json`.

The independent exhaustive/minimality record is
`packet71_and_latch_cpp_audit.json`, generated by
`sandpile_packet71_and_latch_audit.cpp`.

Reproduce it with:

```sh
python3 generate_packet71_and_latch_certificate.py
python3 verify_packet71_and_latch_certificate.py
g++ -O3 -std=c++20 -Wall -Wextra -pedantic \
  sandpile_packet71_and_latch_audit.cpp \
  -o packet71_cpp_audit
./packet71_cpp_audit packet71_and_latch_cpp_audit.json
```

The generated certificate has SHA-256

```text
74f757359400d5cfeafcbbbcc81cf094c54d719ad7e5125fb64588dbba44ac96
```

The C++ exhaustive-audit JSON has SHA-256

```text
6c7ca343fb709a5271e0cfb4f108d844599e5457c1f70808e4e46d979ee96013
```

## Scope and nonclaims

The outward fuses are genuine one-toppling presence leads of arbitrary finite
length, but their unloaded terminal condition is what has been proved. An
arbitrary attached downstream background can feed grains back through the
undirected lattice and must be audited as part of the combined system.

The output encoding also does not match the input encoding: a fresh copy of
the module expects a 71-grain packet, while each fuse exports a one-toppling
presence signal. Thus this is not yet a closed self-cascade.

The primary precharged construction needs no external clock. The zero-height
latch is a separate clocked corollary. No reset, repeated use, functional
completeness, universality, or complexity-class hardness is asserted.

The Python certificate verifies the displayed witness, latch, and fuse
protocols. The separate C++ artifact certifies only the explicitly scoped
minimality statement above. No claim of literature priority is made.
