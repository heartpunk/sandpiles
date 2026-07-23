# Packet 672: a minimal full-alphabet odometer-parity half-adder

## Exact primitive

Work in the ordinary conservative Abelian sandpile on the infinite square
lattice. A site topples at height four and sends one grain to each of its
four von Neumann neighbors. The background is zero except for the stable
`2 x 2` core

```text
          column 0   column 1
row 0        0           3       <- inputs A, B
row 1        3           2
```

For `a,b` in `{0,1,2,3}`, add `672a` grains at `A=(0,0)` and `672b`
grains at `B=(0,1)`, then stabilize. Let `u` be the total odometer.
The following external sites are one canonical pair of outputs:

```text
SUM   = (-3,3)
CARRY = (-1,3)
```

Their exact count table `(u(SUM),u(CARRY))`, with rows indexed by `a` and
columns by `b`, is

```text
             b=0          b=1          b=2          b=3
a=0         (0,0)       (63,110)    (196,294)    (355,504)
a=1        (49,76)     (176,255)    (333,462)    (514,695)
a=2       (164,224)    (317,428)    (488,650)    (683,896)
a=3       (305,398)    (480,623)    (667,860)   (864,1109)
```

Consequently, on all 16 inputs,

```text
u(SUM)   mod 2 = (a mod 2) XOR (b mod 2)
u(CARRY) mod 2 = (a mod 2) AND (b mod 2).
```

The same core has a second SUM tap at `(-3,-2)` and a second CARRY tap at
`(1,-2)`. Their integer counts differ, but their parities obey the same
truth table.

This is a nonlinear two-output Boolean primitive: CARRY has algebraic
degree two over the input parity bits.

## Independently reproduced witness

`verify_halfadder672_certificate.py` uses sparse dictionaries on literal
signed coordinates in `Z^2`, a lexicographic heap, and exactly one legal
toppling at a time. It independently checks all 16 cases, including:

- legality of every toppling;
- stability of every final configuration;
- the discrete-Laplacian reconstruction equation;
- conservation of total mass on the sinkless lattice;
- both copies of the SUM and CARRY parity truth tables;
- SHA-256 hashes of every full sparse odometer and final state.

The generated records are in `halfadder672_certificate.json`.

## Scoped exhaustive minimality

`audit_halfadder672_exhaustive.cpp` exhausts:

- all `4^4 = 256` stable `2 x 2` cores in a zero background;
- every equal integer packet `1 <= p <= 672`;
- all 16 amplitudes `a,b in {0,1,2,3}`;
- every external lattice site reached by any run as a possible SUM or
  CARRY tap.

There are `256 * 672 = 172032` core-packet pairs. The result is:

```text
no half-adder hit for 1 <= p <= 671
least packet: p = 672
core-packet hits at p = 672: 10
role-labelled (CARRY,SUM) output pairs at p = 672: 28
```

Thus `p=672` is globally minimal in this fixed equal-packet search class.
The displayed core is a witness, but it is not the unique core at the
minimal packet. The certificate records all ten cores and every valid
tap. A second exhaustive run allowing the four seeded core sites as
possible outputs produced the same threshold and the same hits.

This minimality statement does not quantify over larger backgrounds,
different input geometry, unequal packet sizes, or other readout rules.

An independent exhaustive implementation,
`audit_halfadder672_unit_exhaustive.cpp`, repeats all `172032` core-packet
checks using fresh array resets, a LIFO work stack, and exactly one legal
toppling per event. It independently returns the same zero hits below
`672`, ten cores at `672`, and 28 role-labelled output pairs.

## Finite-array exactness

The exhaustive implementation uses a `129 x 129` array centered at the
origin. The all-height-three core with the largest additions, `2016`
grains at each input, pointwise dominates every audited initial state.
Its exact odometer support has

```text
bounding box: rows -23..23, columns -22..23
L-infinity radius: 23
support sites: 1774
```

Odometer monotonicity therefore bounds every audited toppling support by
this one. The artificial boundary is at coordinate magnitude 64, so no
audited avalanche comes close to it. The dense calculation is exactly
the same as stabilization on the infinite lattice.

## Composition caveat

This object is a half-adder as a pair of local odometer observables. It is
not yet a cascadable circuit gate.

The integer outputs above are irregular counts rather than normalized
`672`-grain packets. More importantly, an attached receiver participates
in the same stabilization: ordinary square-lattice edges are undirected,
so it can feed grains back and change the avalanche that produced the
output.

`audit_halfadder672_composition.cpp` supplies one bounded negative result.
For each of the complete 16-value SUM and CARRY alphabets, it tests:

- all 256 stable `2 x 2` decoder cores;
- each of their four cells as the abstract input;
- every reached lattice site as the possible parity output.

The exact result is

```text
decoder searches: 2048
candidate taps examined: 1021952
SUM decoder hits: 0
CARRY decoder hits: 0
```

This rules out only a tiny isolated decoder family. It is not a no-go
theorem for larger decoders, parity wires, isolators, or physically
coupled modules.

## Reproduction

```bash
python3 generate_halfadder672_certificate.py
python3 verify_halfadder672_certificate.py

g++ -O3 -std=c++20 -Wall -Wextra -pedantic \
  audit_halfadder672_exhaustive.cpp -o audit_halfadder672
./audit_halfadder672
./audit_halfadder672 --allow-core-outputs

g++ -O3 -std=c++20 -Wall -Wextra -pedantic \
  audit_halfadder672_unit_exhaustive.cpp -o audit_halfadder672_unit
./audit_halfadder672_unit

g++ -O3 -std=c++20 -Wall -Wextra -pedantic \
  audit_halfadder672_composition.cpp -o audit_halfadder672_composition
./audit_halfadder672_composition
```
