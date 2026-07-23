# Sandpiles

Open, AI-produced research on unconventional computation in the ordinary
two-dimensional Abelian sandpile.

The repository begins with an exact four-terminal odometer-parity identity
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

## Reproduce the main result

The quick checks require only Python 3:

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

Further work will be committed publicly. The immediate target is a genuine
nonlinear computational primitive under odometer-parity signaling, followed
by a load-tested interface that can turn a local observable into a physically
composable signal.

## License

Use this however you want.

Everything in the repository is released under
[CC0-1.0](LICENSE-CC0): use, copy, modify, publish, redistribute, sell, or
build on it for any purpose. Attribution is appreciated but not required.

Source code is additionally available under the [MIT License](LICENSE).
You may choose either license for code.
