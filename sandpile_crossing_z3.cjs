#!/usr/bin/env node
/* Exact bounded-horizon synthesis for a count-coded sandpile crossing.
 *
 * We encode the deterministic parallel toppling dynamics for two experiments
 * sharing one stable background:
 *   N: add q grains at the north input;
 *   W: add q grains at the west input.
 *
 * If north causes strictly more south-output topplings than west does, while
 * west causes strictly more east-output topplings than north does, the two
 * outputs can decode the crossing signals by integer thresholds.
 */

const { init } = require("z3-solver");

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? Number(process.argv[i + 1]) : fallback;
}

async function main() {
  const n = arg("--size", 5);
  const pulse = arg("--pulse", 8);
  const horizon = arg("--horizon", 20);
  const timeout = arg("--timeout-ms", 120000);
  const symmetric = process.argv.includes("--symmetric");
  if (n < 2) {
    throw new Error("--size must be an integer >= 2");
  }

  const { Context } = await init();
  const { Solver, Int, Bool, If, Sum, And } = new Context("sandpile");
  const solver = new Solver();
  solver.set("timeout", timeout);

  const cells = [...Array(n * n).keys()];
  const at = (r, c) => r * n + c;
  const rc = (v) => [Math.floor(v / n), v % n];
  const mid = Math.floor(n / 2);
  const ports = {
    north: at(0, mid),
    west: at(mid, 0),
    south: at(n - 1, mid),
    east: at(mid, n - 1),
  };

  const base = cells.map((v) => Int.const(`c_${v}`));
  for (const c of base) solver.add(And(c.ge(0), c.le(3)));
  if (symmetric) {
    for (let r = 0; r < n; r++) {
      for (let c = r + 1; c < n; c++) {
        solver.add(base[at(r, c)].eq(base[at(c, r)]));
      }
    }
  }

  function encodeRun(name, source) {
    const state = [];
    const fire = [];
    for (let t = 0; t <= horizon; t++) {
      state.push(cells.map((v) => Int.const(`${name}_z_${t}_${v}`)));
      if (t < horizon) {
        fire.push(cells.map((v) => Bool.const(`${name}_f_${t}_${v}`)));
      }
    }
    for (const v of cells) {
      solver.add(
        state[0][v].eq(base[v].add(v === source ? pulse : 0))
      );
    }
    for (let t = 0; t < horizon; t++) {
      for (const v of cells) {
        const [r, c] = rc(v);
        solver.add(fire[t][v].eq(state[t][v].ge(4)));
        const incoming = [];
        for (const [dr, dc] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
          const rr = r + dr;
          const cc = c + dc;
          if (0 <= rr && rr < n && 0 <= cc && cc < n) {
            incoming.push(If(fire[t][at(rr, cc)], 1, 0));
          }
        }
        const next = state[t][v]
          .sub(If(fire[t][v], 4, 0))
          .add(incoming.length === 1 ? incoming[0] : Sum(...incoming));
        solver.add(state[t + 1][v].eq(next));
      }
    }
    for (const v of cells) solver.add(state[horizon][v].lt(4));
    const odometer = (v) => Sum(...fire.map((row) => If(row[v], 1, 0)));
    return { state, fire, odometer };
  }

  const north = encodeRun("N", ports.north);
  const west = encodeRun("W", ports.west);
  const nSouth = north.odometer(ports.south);
  const wSouth = west.odometer(ports.south);
  const nEast = north.odometer(ports.east);
  const wEast = west.odometer(ports.east);
  solver.add(nSouth.gt(wSouth));
  solver.add(wEast.gt(nEast));

  console.log(JSON.stringify({ n, pulse, horizon, symmetric, timeout }));
  const result = await solver.check();
  console.log(result);
  if (result !== "sat") return;

  const model = solver.model();
  const value = (expr) => Number(model.eval(expr).toString());
  const grid = [];
  for (let r = 0; r < n; r++) {
    grid.push([...Array(n).keys()].map((c) => value(base[at(r, c)])));
  }
  console.log(JSON.stringify({
    response: {
      north_to_south: value(nSouth),
      west_to_south: value(wSouth),
      north_to_east: value(nEast),
      west_to_east: value(wEast),
    },
    grid,
  }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
