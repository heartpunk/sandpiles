# Why a load must be checked with its source attached

A site that topples once before a receiver is attached can topple twice after
attachment. Here is a small exact example, followed by the independent checks
used for the passive-count theorem. It gives a concrete reason to record a
loading contract alongside a sandpile gadget's output table.

This note is a research record dated 2 October 2026. It is not a claim of
literature priority, a new universal amplifier, or a failure of the packet-71
construction.

## A nine-cell chamber changes a one-toppling output

Use the ordinary infinite square lattice: stable heights are 0, 1, 2, or 3;
each legal toppling sends one grain to each of four neighbors. Coordinates
below are `(row, column)`. An **odometer** is simply a site's total number of
topplings.

Start with every site empty. Add 24 grains at the source `s=(0,0)` and
stabilize. The site immediately to its right, `p=(0,1)`, topples once and
finishes at height three. This looks like a usable one-shot output if one
only counts its topplings.

Now repeat the experiment with a charged chamber already in place. The
chamber consists of the nine sites

```text
rows -1, 0, 1; columns 2, 3, 4
```

Each starts at height three; every other site starts at zero. Add the same
24 grains at the same source, with no further input. The chamber entrance is
`t=(0,2)`, immediately to the right of `p`.

| Measured quantity | Without chamber | With chamber |
|---|---:|---:|
| Source `s` topplings | 7 | 7 |
| Output site `p` topplings | 1 | 2 |
| Entrance `t` topplings | 0 | 2 |
| Maximum topplings inside the chamber | 0 | 2 |
| Total unit topplings everywhere | 11 | 27 |

The final loaded odometer is zero outside this displayed region:

```text
                 column
               -1  0  1  2  3  4
row -1          0  2  1  1  1  1
row  0          1  7  2  2  2  1
row  1          0  2  1  1  1  1
                   s  p  t
```

Both runs are reproduced with two different legal stabilization orders. The
[result record](amplifier_search_results.json) includes their complete initial
states, final states, odometers, and legal unit-event histories.

## Where the second toppling comes from

The feedback can be seen without trusting a search program.

Run the unloaded experiment's eleven legal topplings while the chamber is
present, postponing any newly unstable chamber site. This remains a legal
schedule: the chamber has not sent any grains back yet. At this point `p` is
at height three, while `t` has its original three grains plus the one emitted
by `p`, so `t` is at height four.

Topple `t` once. It sends a grain back to `p`, raising `p` from three to four.
The second toppling of `p` is now legal. The audit explicitly replays these
steps and checks the heights `3`, `4`, and then `4` at the indicated sites.

This is why an output count measured in isolation is not itself a loading
contract. A receiver can change the count it was meant to read. The
packet-71 ports have a different certified final state, and their protected
receiver constructions require their own proof; this example does not
replace that proof.

## Why this does not contradict the passive-count bound

The [passive-count theorem](passive_amplification.md) uses counts in the
**combined execution**. If every site immediately outside a source-free load
that can send activity into it topples at most `K` times, every site inside
it also topples at most `K` times.

In the loaded example, take the receiver region to be the half-plane
`column >= 2`, including initially empty surrounding sites. The actual
maximum immediately outside its boundary is two, and its actual maximum
inside is also two. The theorem holds exactly. Substituting the unloaded
value one would be the mistake.

For a preserved one-shot interface, `K=1`. Enlarging a passive receiver,
precharging more stable sites, or combining many distinct one-shot inputs
cannot make any receiver site topple twice. At most four grains can be
emitted into one target site, one from each neighbor. Regenerating a specified
71-grain packet therefore requires changing that interface or another
assumption.

## What the executable audit checks

Run from the repository root:

```sh
python3 research/amplifier_search.py
```

The script also works from any working directory when given its absolute
path. Its default output is `amplifier_search_results.json` beside the
script. To keep the checked-in record untouched, choose an output path:

```sh
python3 research/amplifier_search.py --output /tmp/amplifier-audit.json
```

Python 3.10 or newer is required; only its standard library is used.
Assertions must remain enabled: the audit rejects `-O` and `PYTHONOPTIMIZE`. The default deterministic audit
covers 66,951 configurations:

- All 256 stable `2 x 2` cores, with every four-site addition vector in
  `{0,1,2,3}^4`: 65,536 configurations.
- All 256 cores with a single-source packet of 4, 7, 16, 31, or 71 grains:
  1,280 configurations.
- 128 seeded random finite stable backgrounds, with one to four sources.
- The two feedback experiments above and five direct-injection comparisons.

Across these configurations it verifies 410,024 legal unit topplings,
232,640 earlier-neighbor ancestry edges, 556,619 source-free cuts, and
17,349 cuts with exactly one active bridge. All checks pass. A second
synchronous-batch stabilizer independently reproduces the 128 random cases
and all seven illustrative cases.

For every non-source site's kth toppling, the history records a neighboring
site's earlier kth toppling. Following those earlier events reaches a site
that received external input. Separately, the audit checks that every
connected component at every odometer level reaches a source. It also checks
final stability, the exact grain-balance equation, mass conservation, both
first spatial moments, and the second-moment increase of four per toppling.
The lattice uses signed coordinates and grows when needed; it has no
artificial boundary or sink.

In the two saved histories, each event is `[site, k, parent]`, where `site` is
a coordinate pair, `k` is its one-based toppling number, and `parent` is the
zero-based index of an earlier neighboring kth event. A null parent marks an
externally driven site. The recorded SHA-256 hashes cover the compact JSON
encoding of those histories.

These finite checks exercise the implementation and illustrate the theorem's
assumptions. They do not prove the statement for all sizes; the chronological
proof in the accompanying note does that.

## A useful contrast: directly dropping one grain inside a reservoir

One externally added grain at the center of an all-height-three square can
cause repeated topplings. The audit records maximum counts 2, 3, 4, 6, and 11
for square side lengths 3, 5, 7, 11, and 21 respectively.

There is no contradiction here either. That grain was dropped directly at an
interior source, in addition to whatever its neighbors later send. A grain
emitted by a neighbor that topples only once is already one of the four
neighbor contributions. The direct-drop experiment and a physical one-shot
fuse attachment are different inputs.
