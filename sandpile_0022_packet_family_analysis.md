# The `(0,0;2,2)` full-alphabet packet family through `p = 50,000`

## Exact scope

Work on the ordinary conservative Abelian sandpile on the infinite square
lattice, threshold 4, with zero background except for

```text
A=0  B=0
D=2  C=2 .
```

For a positive integer packet size `p` and `a,b in {0,1,2,3}`, add `ap`
grains at `A` and `bp` grains at `B`, stabilize from the original
background, and let `(u_C,u_D)` be the two odometer counts.  Call `p` a
full-alphabet hit when

```text
(u_C mod 2, u_D mod 2) = (a mod 2, b mod 2)
```

for all 16 input pairs.

The exact exhaustive result in this fixed family is

```text
1 <= p <= 50,000:
925, 14509, 17993, 25929, 27889, 45016
```

and no other packet sizes in that interval.

## Five-ray reduction

Reflection through the vertical axis preserves the background and swaps
`A <-> B` and `C <-> D`.  Thus one stabilization checks both orientations
of every unordered input pair.  The 16-case condition is equivalent to
nine nontrivial stabilizations:

- `(a,0)` for `a=1,2,3`;
- `(a,a)` for `a=1,2,3`;
- `(1,2)`, `(1,3)`, and `(2,3)`.

These nine stabilizations lie on only five Abelian rays:

```text
(k,0), (k,k), (k,2k), (k,3k), (2k,3k).
```

The first two rays are sampled at `k=p,2p,3p`; the other three at `k=p`.
Incrementing a ray once and stabilizing is exactly equivalent, by the
Abelian property, to adding the accumulated ray input to the original
background and stabilizing once.  This gives an exact scan, not a
simulation or heuristic.

Equivalently, reflection reduces the property to 15 parity bits: six on
the axis, three on the diagonal, and two on each of the three mixed rays.

## Exact filter cascade

For all `p=1,...,50,000`, the cumulative survivor counts are:

| Conditions imposed | Survivors |
|---|---:|
| axis and equal-input cases | 119 |
| plus `(1,2)` | 46 |
| plus `(1,3)` | 23 |
| plus `(2,3)` | 6 |

The last six are precisely the full hits above.  This is useful
structurally: the result is a rare simultaneous phase alignment of five
one-parameter sandpile evolutions, rather than a single Boolean
coincidence.

## Arithmetic and scale checks

| `p` | factorization | parity | maximum `L_infinity` toppling radius, at `(a,b)=(3,3)` |
|---:|---|---|---:|
| 925 | `5^2 * 37` | odd | 27 |
| 14509 | `11 * 1319` | odd | 108 |
| 17993 | `19 * 947` | odd | 120 |
| 25929 | `3^2 * 43 * 67` | odd | 144 |
| 27889 | `167^2` | odd | 149 |
| 45016 | `2^3 * 17 * 331` | even | 190 |

Consequences and failed simple hypotheses:

- Hits are **not odd-only**: `p=45016` is an exact even hit.
- They are **not prime-only**: every hit through 50,000 is composite.
  No theorem excluding a future prime hit is known.
- The first five happen to be `1 mod 4`, but the sixth is `0 mod 4`.
  Thus `p=1 mod 4` is not necessary.  The six hit values do not share any
  nontrivial congruence class: the gcd of their differences is 1.
- The gaps `13584, 3484, 7936, 1960, 17127` do not suggest a fixed
  period.  This finite computation does not prove aperiodicity.
- The radius jump `27 -> 108` between the first two hits looks like a
  factor-4 scaling at first, but
  `14509 = 16*925 - 291`, the odometers do not obey a corresponding
  exact scaling, and the later radii break a fixed scale ratio.
  The values `p/R^2` lie between about 1.24 and 1.27, consistent with
  ordinary square-root bulk growth rather than an identified exact
  renormalization.

No compact modular recurrence or renormalization law survived these
checks.  The honest current description is: sparse, irregular exact
alignments of five correlated Abelian rays.

## Verification and source files

Primary exact scanner:

```text
scan_full_alphabet_0022_family.cpp
```

It uses a 1025-by-1025 dense lattice, legal quotient topplings, and the
five incremental rays above.  The pointwise-dominating endpoint
`a=b=3, p=50,000` has toppling radius 200, far inside the 512-site board
margin; monotonicity therefore proves the whole scan agrees with the
infinite lattice.

Independent replay:

```text
audit_full_alphabet_extended_hits.cpp
```

All 96 cases (16 inputs for each of the six hits) were independently
restarted from scratch and replayed with a FIFO batched toppling order.
Every case was stable and had the required output parity.  The largest
observed hit radius was 190.

Reproduction:

```sh
g++ -O3 -std=c++20 -pthread scan_full_alphabet_0022_family.cpp -o scan_family
./scan_family --maximum-pulse 50000

g++ -O3 -std=c++20 audit_full_alphabet_extended_hits.cpp -o audit_hits
./audit_hits 925 14509 17993 25929 27889 45016
```

This family analysis does not alter or extend the separately certified
global minimality statement for `p=925`; it only classifies the fixed
`(0,0,2,2)` core through `p=50,000`.
