# Sandpiles

Open, AI-produced research on unconventional computation in the ordinary
two-dimensional Abelian sandpile.

## Current results

### Packet 71: parity AND and an extensible eight-output gate

From the stable core

```text
1 1
2 2
```

add `71a` and `71b` grains at the two top cells. For every
`a,b in {0,1,2,3}`, two exterior sites have odometer parity

```text
(a mod 2) AND (b mod 2).
```

An exhaustive audit of all 256 stable `2 x 2` cores, every common packet
`1 <= p <= 71`, all sixteen inputs, and every reached exterior site finds no
such tap below 71 and exactly sixteen at 71.

The Boolean restriction is physically stronger. Eight initially empty
boundary cells receive exactly one grain iff `a=b=1`, without toppling.
Precharge those cells and arbitrary finite outward fuse wires to height three
before supplying the inputs. In the three false cases no output-wire cell
topples; in the true case every cell of all eight wires topples exactly once.
The construction is therefore a clockless eight-output AND gate under the
packet encoding `1 = 71 grains`, with ordinary avalanche-presence outputs.

See [the packet-71 audit](sandpile_packet71_and_latch_audit.md), its independent
Python certificate, and the independent C++ exhaustive audit.

### Packet 672: a full-alphabet odometer-parity half-adder

From the stable core

```text
0 3
3 2
```

add `672a` and `672b` grains at the two top cells. At the exterior sites
`SUM=(-3,3)` and `CARRY=(-1,3)`,

```text
u(SUM)   mod 2 = (a mod 2) XOR (b mod 2)
u(CARRY) mod 2 = (a mod 2) AND (b mod 2)
```

for all sixteen `a,b in {0,1,2,3}`. Two independent exhaustive engines find
no half-adder in the same 256-core, equal-packet class below 672; at 672 there
are ten cores and 28 role-labelled output pairs.

This is a decisive nonlinear two-output local observable, but its integer
output counts are not yet normalized packets and attaching a receiver can
feed back into the same avalanche. See
[the packet-672 audit](sandpile_halfadder672_audit.md).

### Packet 925: a crossed parity identity

The repository began with an exact four-terminal odometer-parity identity
on the infinite square lattice. From the stable `2 x 2` seed

```text
0 0
2 2
```

add `925a` and `925b` grains at the two top cells, with
`a,b in {0,1,2,3}`. After stabilization, the odometer parities at the
oppositely paired bottom cells are exactly `(a mod 2, b mod 2)` for all
sixteen inputs.

This is a crossed local readout, not yet a classical composable crossing
gate. The distinction, exact table, scoped minimality result, analytic
no-propagation theorem, literature context, and failed composition audits
are in the paper:

**[A Four-Terminal Odometer-Parity Identity in the Planar Abelian
Sandpile](paper/four_terminal_odometer_parity_identity.pdf)**

## Contribution statement

OpenAI Codex produced the specific construction, searches, proofs, code,
verification, literature framing, and manuscript in a ChatGPT work session
on 23 July 2026.

Sophie (`heartpunk`) had not encountered this sandpile problem before that
session. Her contribution was to pose a broad challenge, filter proposed
directions by whether they seemed interesting, encourage the system to keep
trying, request a publishable write-up, and make the work public. She did not
derive or independently verify the technical results.

Hosting this repository under `heartpunk` denotes publication stewardship,
not technical authorship. The technical claims are unreviewed AI-produced
research and should be checked independently.

## Reproduce the results

The packet-71 certificates and scoped exhaustive audit:

```bash
python3 generate_packet71_and_latch_certificate.py
python3 verify_packet71_and_latch_certificate.py

c++ -O3 -std=c++20 sandpile_packet71_and_latch_audit.cpp -o audit71
./audit71 packet71_and_latch_cpp_audit.json
```

The packet-672 half-adder certificates and two independent scoped exhaustive
audits:

```bash
python3 generate_halfadder672_certificate.py
python3 verify_halfadder672_certificate.py

c++ -O3 -std=c++20 audit_halfadder672_exhaustive.cpp -o audit672
./audit672

c++ -O3 -std=c++20 audit_halfadder672_unit_exhaustive.cpp -o audit672-unit
./audit672-unit
```

The original packet-925 checks require only Python 3:

```bash
python3 verify_packet925_full_alphabet_certificate.py
python3 audit_full_alphabet_925_witness.py
```

The scoped minimality audit requires a C++20 compiler:

```bash
c++ -O3 -std=c++20 audit_full_alphabet_925.cpp -o audit925
./audit925 --maximum-pulse 925
```

The exact packet-family scan through `100000` is:

```bash
c++ -O3 -std=c++20 -pthread scan_full_alphabet_0022.cpp -o scan100k
./scan100k --maximum-pulse 100000
```

The PDF also embeds its certificate, verifiers, proof notes, scan audit, and
typesetting source as file attachments.

## Repository contents

The root intentionally preserves the research scripts and their relative
imports. It includes:

- exact certificates and independent verifiers;
- dense and sparse exhaustive searches;
- packet-family scans and replay audits;
- analytic no-go proofs;
- parity-wire, normalizer, reset, and interface experiments;
- bounded negative composition results;
- exploratory Python, C++, Z3, and JavaScript programs.

The unsuccessful searches are included because they delimit the result and
make the path to later claims auditable.

## Ongoing direction

Further work will be committed publicly. The immediate target is to close the
encoding gap between packet inputs, parity observables, and ordinary fuse-wire
outputs without losing exactness under physical attachment. No claim of
functional completeness, a crossover gate, P-completeness, or universality is
made.

## License

Use this however you want.

Everything in the repository is released under
[CC0-1.0](LICENSE-CC0): use, copy, modify, publish, redistribute, sell, or
build on it for any purpose. Attribution is appreciated but not required.

Source code is additionally available under the [MIT License](LICENSE).
You may choose either license for code.
