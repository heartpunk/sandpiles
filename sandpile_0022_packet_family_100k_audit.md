# Audit: the `[[0,0],[2,2]]` packet family through 100,000

## Model and result

The stable \(2\times2\) core is

\[
\begin{pmatrix}0&0\\2&2\end{pmatrix},
\]

with zeros elsewhere on the ordinary infinite square lattice.  A symbol
\(a\in\{0,1,2,3\}\) adds \(ap\) grains at the top-left cell \(A\), and
\(b\) adds \(bp\) grains at the top-right cell \(B\).  The diagonally
opposite bottom cells \(C,D\) are read by odometer parity.  A packet
\(p\) is a hit when

\[
 (u(C),u(D))\equiv(a,b)\pmod2
\]

for all sixteen input pairs.

The exact hits for \(1\leq p\leq100000\) are

```text
925, 14509, 17993, 25929, 27889, 45016,
50958, 63430, 67004, 76725, 77458
```

There are no further hits from 77459 through 100000.

| packet | factorization | independently replayed max radius |
|---:|:---|---:|
| 925 | \(5^2\cdot37\) | 27 |
| 14509 | \(11\cdot1319\) | 108 |
| 17993 | \(19\cdot947\) | 120 |
| 25929 | \(3^2\cdot43\cdot67\) | 144 |
| 27889 | \(167^2\) | 149 |
| 45016 | \(2^3\cdot17\cdot331\) | 190 |
| 50958 | \(2\cdot3^2\cdot19\cdot149\) | 202 |
| 63430 | \(2\cdot5\cdot6343\) | 225 |
| 67004 | \(2^2\cdot7\cdot2393\) | 231 |
| 76725 | \(3^2\cdot5^2\cdot11\cdot31\) | 247 |
| 77458 | \(2\cdot38729\) | 249 |

All eleven packets are composite.  In particular, no prime packet hit
occurs through 100000.  The factor \(38729\) in the last row is prime.

The successive gaps are

```text
13584, 3484, 7936, 1960, 17127,
5942, 12472, 3574, 9721, 733
```

with factorizations

```text
2^4*3*283, 2^2*13*67, 2^8*31, 2^3*5*7^2, 3^2*11*173,
2*2971, 2^3*1559, 2*1787, 9721, 733.
```

The last two gaps are prime.  The gap gcd is one; packet residues
include both parities and \(0,1,2\bmod4\); all ten observed gaps are
different.  Thus the data do not support a fixed congruence class,
arithmetic progression, periodic gap, or first-order affine recurrence.
This is an empirical pattern statement, not a theorem excluding more
complicated structure.

## Exact scan reduction

The scanner `scan_full_alphabet_0022.cpp` uses only legal single-site
topplings.  A trajectory is advanced from symbol count \(q\) to \(q+1\)
by adding the relevant grains to an already stable state.  By
abelianness, its accumulated odometer is exactly the one-shot odometer
from the original core.

Vertical reflection exchanges

\[
(A,B,C,D)\longleftrightarrow(B,A,D,C).
\]

It is therefore enough to compute five trajectories:

1. \(A\)-only through \(q=3P\) (the \(B\)-only values are reflected);
2. equal \(A,B\) additions through \(q=3P\);
3. mixed ratios \(1{:}2\), \(1{:}3\), and \(2{:}3\) through \(p=P\).

For each packet \(p\), the first trajectory supplies the six axis
cases at indices \(p,2p,3p\), the second supplies the three equal cases,
and the last three supply one representative of each reflected mixed
pair.  Together with the trivial zero input, these are exactly all
sixteen cases; no probabilistic filter is involved.

Through \(P=100000\), 224 packets survive the axis-and-equal conditions
and eleven survive the complete table.  The run took 85.35 seconds wall
time and 222.73 seconds CPU time on the audit host.

The largest trajectory, with \(300000\) grains at each input, has
toppling radius 282.  It pointwise dominates every scanned input pair
on this fixed core.  The \(1025\times1025\) audit array has boundary
distance 512 from the origin, leaving 230 cells beyond the toppling
support (and 229 beyond the one-cell deposited-grain ring).  The other
terminal radii were 199 for the axis trajectory and \(200,231,258\)
for the three mixed trajectories.

## Independent replays

`audit_full_alphabet_extended_hits.cpp` starts every one of the sixteen
cases from scratch and uses a different FIFO algorithm that topples the
entire currently legal quotient.  It reproduced every table above as
stable at the radii in the table.

For the first hit, `audit_full_alphabet_925_witness.py` instead uses
synchronous sparse waves directly on \(\mathbb Z^2\).  It checks
stability, mass conservation, and

\[
\eta_{\rm final}=\eta_{\rm initial}-Lu
\]

at every affected cell.  Its output-count table is

```text
a=0: (0,0)     (300,237)  (698,572)   (1130,941)
a=1: (237,300) (625,625)  (1073,1010) (1531,1405)
a=2: (572,698) (1010,1073)(1456,1456) (1946,1883)
a=3: (941,1130)(1405,1531)(1883,1946) (2371,2371)
```

The canonical serialization of all sixteen odometers and final states,
plus the dominating run, has SHA-256

```text
23b19081729d9303e5acaae0565a5dbce2296fbd5cb360bdab94f47f279b92ff
```

## Independent minimality audit

`audit_full_alphabet_925.cpp` is distinct from the discovery program:
it uses exact single topplings, tabulates trajectories through \(3p\),
checks six extra axis/equal cases before mixed runs, and uses a separate
case ordering.

It exhausts all \(4^4=256\) stable backgrounds supported on the
designated \(2\times2\) core and every equal positive integer packet.
The rerun through \(p=924\) found:

```text
boolean candidates: 12634
axis/equal survivors: 77
full hits: 0
```

At \(p=925\) it found exactly one full hit, the core
`(0,0,2,2)`.  Thus 925 is minimal in the explicitly stated
\(2\times2\)-core/equal-packet/fixed-port/odometer-parity class.  This
is not a minimality claim over arbitrary larger gadgets.

For the finite-array justification, the all-three core with 2775
grains at each input pointwise dominates every case in that exhaustive
search.  An independent sparse stabilization gives toppling bounds
rows \([-27,27]\), columns \([-26,27]\).  The discovery program's
\(257\times257\) array therefore has more than one hundred cells of
unused margin.

The exhaustive audit hashes are

```text
FNV-1a-64: fbd57dcaa65cb3e
mix64:     ae4f571f744b806f
```
