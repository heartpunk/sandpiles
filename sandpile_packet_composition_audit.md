# Composition audit for the `p = 925` packet-parity gate

## Exact gate

Work on the ordinary undirected Abelian sandpile on the infinite square
lattice, with threshold four and zero background except for this stable
`2 x 2` core:

```text
          column 0   column 1
row 0        0           0       <- inputs A, B
row 1        2           2       <- taps D, C
```

Put `925a` grains at `A = (0,0)` and `925b` grains at `B = (0,1)`, where
`a,b` range over `{0,1,2,3}`.  Read the odometers at the diagonal bottom
cells

```text
A-output = C = (1,1)
B-output = D = (1,0).
```

The complete exact odometer table `(u(C),u(D))` is

```text
              b=0          b=1          b=2           b=3
a=0          (0,0)       (300,237)    (698,572)     (1130,941)
a=1        (237,300)     (625,625)   (1073,1010)   (1531,1405)
a=2        (572,698)   (1010,1073)  (1456,1456)   (1946,1883)
a=3       (941,1130)  (1405,1531)  (1883,1946)   (2371,2371)
```

Thus, for all 16 inputs,

```text
(u(C) mod 2, u(D) mod 2) = (a mod 2, b mod 2).
```

An exhaustive search of every stable `2 x 2` core (all `4^4 = 256`) and
every common packet size `1 <= p <= 925` found exactly one full-alphabet
hit in this oriented search: `p=925`, core `(0,0,2,2)`.  A separate sparse
infinite-lattice Python stabilizer independently reproduces the table.

## Why composition is not automatic

The values above are odometer values *inside the gate's avalanche*.  They
are not grains emitted along directed edges.  There are two different
questions:

1. **Abstract injection.** Take a number `k` from the table, start a fresh
   gadget, and add `k` grains to its input.
2. **Physical coupling.** Place that gadget next to the gate and stabilize
   the single combined configuration.

The first is an alphabet test.  It is not a proof of the second, because
ordinary `Z^2` edges are undirected: the added cells alter the original
avalanche and feed grains back into the gate.

## Existing `5 x L` all-height-three wire: bounded no

The previously proved wire carries input amplitudes `k=0,1,2,3` exactly:
at every theorem tap its odometer is `k`.  That theorem does not extend to
the packet gate's output alphabet.

Even under the more favorable **abstract-injection** interpretation, every
center-line theorem tap of every `5 x L` wire with `4 <= L <= 64` was
tested on all 16 distinct packet counts.  There were no taps whose
odometer parity matched the input-count parity on the whole alphabet.

Under **physical coupling**, two natural mirror-symmetric height-three
arms were attached directly east and west of the gate, with all feedback
included.  Every remote center tap for `4 <= L <= 32` was tested; there
were again no exact two-channel hits.

These are finite exhaustive negative results for the stated families, not
an impossibility theorem for arbitrary wires.

## A tiny abstract parity re-encoder

There is a surprisingly small ordinary-`Z^2` gadget that preserves parity
on the gate's complete count alphabet under abstract injection.  Start
with the stable core

```text
1 0
1 1
```

in zeros, add `k` grains to its upper-left cell `(0,0)`, and read the
odometer at the exterior diagonal cell `(-1,-1)`.  Its exact map is

```text
0    -> 0
237  -> 35
300  -> 50
572  -> 124
625  -> 135
698  -> 164
941  -> 239
1010 -> 266
1073 -> 283
1130 -> 304
1405 -> 405
1456 -> 426
1531 -> 445
1883 -> 585
1946 -> 602
2371 -> 779
```

Every arrow preserves parity, and the maximum count falls from `2371` to
`779`.

Search scope: all 256 stable `2 x 2` cores, input fixed at the upper-left
cell, and every lattice cell reached by each avalanche as a possible tap.
There are six oriented hits: the two cores

```text
1 0      1 1
1 1      0 1
```

each with the three symmetry-related exterior taps `(-1,-1)`, `(-1,1)`,
and `(1,-1)`.

This does not yet solve composition:

- Applying the displayed transducer again to the reduced alphabet fails.
- Repeating the complete 256-core/every-reached-tap search on that reduced
  alphabet gives zero hits.
- Abstractly injecting the reduced alphabet into every `5 x L` theorem tap
  for `4 <= L <= 64` gives zero hits.
- For physical coupling, every rotation/reflection and every free-neighbor
  placement of one copy at each gate tap was enumerated.  There were 16
  variants per channel and 164 nonoverlapping pairs.  None worked; the
  best pair still made 10 errors among the 32 output parity bits.

So this is an exact alphabet re-encoder, but not a demonstrated attachable
second stage.

## An exact absorbing four-rail identity

If one-way absorbing receivers are allowed, there is a universal answer.
A one-cell receiver initially at height `h`, with its outgoing grains
prevented from returning, topples

```text
floor((k+h)/4)
```

times after receiving `k` grains.  Four independent receivers of heights
`0,1,2,3` obey

```text
sum(h=0..3) floor((k+h)/4) = k
```

for every nonnegative integer `k`, not merely the 16 gate counts.  To see
this, write `k=4q+r`; among `k,k+1,k+2,k+3`, exactly `r` cross the next
multiple of four, so the sum is `4q+r=k`.

This is an exact, lossless four-rail re-encoding.  The unresolved physical
problem is implementing the required isolation and aggregation in the
sinkless undirected square lattice.

## Bottom line

The `2 x 2`, `p=925` object is already a decisive full-alphabet parity
crossover **as a local odometer observable**.  It is not yet a composable
circuit crossover.  The audit localizes the obstruction: the arithmetic
can be re-encoded exactly, but the ordinary lattice lacks an established
one-way isolation primitive that lets a downstream gadget observe an
odometer count without changing the avalanche that produced it.

## Reproducible artifacts

- `sandpile_2x2_full_alphabet_fast.cpp`: exhaustive gate search.
- `sandpile_packet_gate_composition_audit.py`: independent sparse
  infinite-lattice table reconstruction; abstract wire tests; natural
  coupled-arm tests; exact four-rail identity.
- `sandpile_packet_interface_search.cpp`: exhaustive tiny abstract
  transducer searches on the original and reduced alphabets.
- `sandpile_packet_direct_interface_audit.cpp`: exhaustive bounded
  physical two-transducer attachment search.
