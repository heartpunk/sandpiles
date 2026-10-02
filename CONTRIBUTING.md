# Contributing to Sandpiles

Start with the [research tour](research/README.md). Reproductions,
counterexamples, literature connections, clearer proofs, and useful failed
searches are all welcome. A small result with a complete record is easier
to build on than a large unsupported claim.

The research is AI-produced and remains open to independent correction.
Please preserve the distinction between who proposed an idea, who wrote an
artifact, and who checked it. Human and AI-assisted contributions are both
welcome; describe material assistance and verification honestly.

## Reproduce before extending

The [tour's short reproduction path](research/README.md#reproduce-the-short-path)
checks the packet-71 witness, attached-load audit, and optional Lean proof.
Report the commit you tested, operating system, interpreter/compiler
versions, exact command, and result. Keep generated files separate until
you have compared them with the checked-in records.

For a proposed fix, explain the failing case first. Include a small input
that someone else can run and the expected result. A changed hash alone is
not an explanation of a changed claim.

## A useful construction or counterexample

Provide these together in an issue or pull request:

- **Model and initial state:** coordinates and heights; which sites are
  initially zero; every external addition; any sinks, altered thresholds,
  or other departures from the ordinary lattice.
- **Interface:** which sites are inputs and outputs; whether a signal is a
  grain packet, a toppling count, its parity, or a stable final height; which
  downstream components are physically present.
- **Claim:** exact input alphabet, output behavior, and scope. State whether
  it concerns one use, repeated use, a finite search, or an all-size theorem.
- **Evidence:** executable input and an independent replay where practical.
  Check legal topplings, final stability, the Laplacian reconstruction, and
  mass conservation. Include exterior cells; do not silently truncate an
  avalanche at an array boundary.
- **Failure or comparison:** identify the previous claim affected, the first
  discrepancy, and whether feedback or a changed assumption explains it.

A counterexample to a conditional theorem must satisfy its hypotheses.
For the passive-load bound, that includes a stable source-free load and a
cap on its **complete boundary in the attached execution**. A terminal that
topples once before attachment and twice afterward does not contradict the
theorem; it is an informative failure of the proposed interface contract.

## Keep claims easy to check

Before submitting, check that:

1. A local odd/even odometer identity is not called a composable gate without
   an attached receiver and a stated material encoding.
2. Search minima name the complete searched class, parameter ranges,
   stopping conditions, and method for ruling out boundary truncation.
3. Finite experiments and mathematical family proofs are labelled separately.
   A Lean claim names the exact theorem and formal model, not the repository
   as a whole.
4. A successful local checker verifies legality as well as endpoint
   arithmetic. An algebraically stable candidate odometer alone may not be
   the legal stabilization.
5. Literature claims cite primary sources and distinguish classical tools
   from the specific construction or application. Avoid priority claims
   without a defensible literature review.

## Make the result reusable

Use deterministic inputs, fixed seeds for randomized checks, and explicit
command-line options. Prefer small verifiers with few dependencies. Preserve
the old result or explain why it is superseded; keep informative failures
and their scope. For a new research direction, add a short note under
`research/` linking the program, certificate, evidence, and next open
question, then update the [tour](research/README.md).

Pull requests should lead with the changed claim or behavior, give the
reason for the change, and list the checks actually run. Small focused
contributions are easier to review. Please do not present a failing or
unrun check as a pass.

The repository is released under [CC0](LICENSE-CC0); code is also available
under [MIT](LICENSE). If an artifact has different provenance or licensing,
identify that before adding it. The goal is for other people to be able to
understand, verify, reuse, and extend the work.
