import { init } from "z3-solver";

const n = Number.parseInt(process.argv[2] ?? "7", 10);
const period = Number.parseInt(process.argv[3] ?? "66", 10);
const timeoutMs = Number.parseInt(process.argv[4] ?? "0", 10);

if (!Number.isInteger(n) || n < 1 || n > 12) {
  throw new Error("n must be an integer in [1, 12]");
}
if (!Number.isInteger(period) || period < 1 || period > (1 << n)) {
  throw new Error("period must be an integer in [1, 2^n]");
}

const { Context } = await init();
const {
  Solver,
  Bool,
  Int,
  And,
  Or,
  Not,
  If,
  Sum,
} = new Context("outer_totalistic");

const solver = new Solver();
if (timeoutMs > 0) solver.set("timeout", timeoutMs);

const edge = Array.from({ length: n }, () => Array(n).fill(null));
for (let i = 0; i < n; i++) {
  for (let j = i + 1; j < n; j++) {
    edge[i][j] = edge[j][i] = Bool.const(`e_${i}_${j}`);
  }
}

// Any nonempty set not containing vertex 0 must have an edge leaving it.
// These cut clauses are exactly the condition that the graph is connected.
for (let rawMask = 1; rawMask < (1 << (n - 1)); rawMask++) {
  const inSet = (v) => v > 0 && ((rawMask >> (v - 1)) & 1) === 1;
  const crossing = [];
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (inSet(i) !== inSet(j)) crossing.push(edge[i][j]);
    }
  }
  solver.add(Or(...crossing));
}

const rule = Array.from({ length: 2 }, (_, s) =>
  Array.from({ length: n }, (_, k) => Bool.const(`r_${s}_${k}`)),
);
const state = Array.from({ length: period }, (_, t) =>
  Array.from({ length: n }, (_, i) => Bool.const(`x_${t}_${i}`)),
);

function selectRule(stateBit, count) {
  let whenOff = rule[0][n - 1];
  let whenOn = rule[1][n - 1];
  for (let k = n - 2; k >= 0; k--) {
    whenOff = If(count.eq(k), rule[0][k], whenOff);
    whenOn = If(count.eq(k), rule[1][k], whenOn);
  }
  return If(stateBit, whenOn, whenOff);
}

for (let t = 0; t < period; t++) {
  const nextT = (t + 1) % period;
  for (let i = 0; i < n; i++) {
    const neighborTerms = [];
    for (let j = 0; j < n; j++) {
      if (i !== j) {
        neighborTerms.push(If(And(edge[i][j], state[t][j]), 1, 0));
      }
    }
    const count = Int.const(`count_${t}_${i}`);
    solver.add(count.eq(Sum(...neighborTerms)));
    solver.add(state[nextT][i].eq(selectRule(state[t][i], count)));
  }
}

// Closure plus x[0] differing from every other state forces exact period.
for (let t = 1; t < period; t++) {
  solver.add(Or(...Array.from(
    { length: n },
    (_, i) => Not(state[0][i].eq(state[t][i])),
  )));
}

// For every nontrivial cycle, rotate time and relabel vertices so this holds.
if (period > 1) solver.add(Not(state[0][0]));

const started = Date.now();
const result = await solver.check();
const elapsedMs = Date.now() - started;
console.error(JSON.stringify({ n, period, result, elapsedMs }));

if (result === "sat") {
  const model = solver.model();
  const truth = (expr) => model.eval(expr, true).toString() === "true";
  const edges = [];
  const adjacency = Array.from({ length: n }, () => 0);
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (truth(edge[i][j])) {
        edges.push([i, j]);
        adjacency[i] |= 1 << j;
        adjacency[j] |= 1 << i;
      }
    }
  }
  const ruleBits = Array.from(
    { length: 2 },
    (_, s) => Array.from({ length: n }, (_, k) => truth(rule[s][k]) ? 1 : 0),
  );
  let initial = 0;
  for (let i = 0; i < n; i++) {
    if (truth(state[0][i])) initial |= 1 << i;
  }

  const popcount = (value) => {
    let x = value;
    let count = 0;
    while (x !== 0) {
      x &= x - 1;
      count++;
    }
    return count;
  };
  const step = (configuration) => {
    let next = 0;
    for (let i = 0; i < n; i++) {
      const own = (configuration >> i) & 1;
      const onNeighbors = popcount(configuration & adjacency[i]);
      if (ruleBits[own][onNeighbors]) next |= 1 << i;
    }
    return next;
  };

  const orbit = [];
  const seen = new Map();
  let current = initial;
  while (!seen.has(current)) {
    seen.set(current, orbit.length);
    orbit.push(current);
    current = step(current);
  }
  const cycleStart = seen.get(current);
  const verifiedPeriod = orbit.length - cycleStart;
  if (cycleStart !== 0 || current !== initial || verifiedPeriod !== period) {
    throw new Error(JSON.stringify({
      message: "independent concrete simulation rejected model",
      cycleStart,
      verifiedPeriod,
      current,
      initial,
    }));
  }

  console.log(JSON.stringify({
    n,
    period,
    edges,
    rule: ruleBits,
    initial,
    orbit,
  }));
}
