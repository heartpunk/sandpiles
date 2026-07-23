#!/usr/bin/env node
/*
 * Inverse synthesis of an evolving-state, full-alphabet parity crossover.
 *
 * By default we ask for a north-input odometer u and take the west
 * odometer to be u transposed.  Pass --independent to search independent
 * odometers u and v (and a nonsymmetric eta).
 * For pulse p, the one-step state changes are
 *
 *   r_N = p delta_N - Delta u,   r_W = r_N^T.
 *
 * If one stable background eta makes eta+a*r_N+b*r_W stable for every
 * a,b=0..3, then a*u+b*u^T is an algebraic stabilizing vector for the full
 * alphabet.  Integrality makes the stability condition extremely rigid:
 * at each cell |r_N|+|r_W| <= 1.
 *
 * Z3 solves those exact linear constraints.  Each model is then replayed by
 * an ordinary legal stabilizer for all 16 inputs; algebraic solutions that
 * are not least/legal odometers are blocked and the search continues.
 */

const { init } = require("z3-solver");

function numberArg(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? Number(process.argv[index + 1]) : fallback;
}

async function main() {
  const n = numberArg("--size", 5);
  const pulse = numberArg("--pulse", 1);
  const inset = numberArg("--inset", 1);
  const maxOdometer = numberArg("--max-odometer", 20);
  const maxModels = numberArg("--max-models", 1000);
  const timeout = numberArg("--timeout-ms", 600000);
  const canonical = !process.argv.includes("--parity-only");
  const independent = process.argv.includes("--independent");
  const allowZeroCross = process.argv.includes("--allow-zero-cross");

  if (n < 3 || n % 2 === 0) throw new Error("--size must be odd >=3");
  if (inset < 0 || inset >= Math.floor(n / 2)) {
    throw new Error("--inset is invalid");
  }
  const m = n + 2;
  const middle = Math.floor(n / 2);
  const coreAt = (row, column) => row * n + column;
  const extAt = (row, column) => row * m + column;
  const coreCells = [...Array(n * n).keys()];
  const extCells = [...Array(m * m).keys()];
  const rc = (position, side) => [
    Math.floor(position / side),
    position % side,
  ];
  const transposeCore = (position) => {
    const [row, column] = rc(position, n);
    return coreAt(column, row);
  };
  const transposeExt = (position) => {
    const [row, column] = rc(position, m);
    return extAt(column, row);
  };
  const ports = {
    north: coreAt(inset, middle),
    west: coreAt(middle, inset),
    south: coreAt(n - 1 - inset, middle),
    east: coreAt(middle, n - 1 - inset),
  };

  const { Context } = await init();
  const { Solver, Int, Sum, And, Or, If } =
    new Context("linear_odometer");
  const solver = new Solver();
  solver.set("timeout", timeout);
  const u = coreCells.map((q) => Int.const(`u_${q}`));
  const v = independent
    ? coreCells.map((q) => Int.const(`v_${q}`))
    : coreCells.map((q) => u[transposeCore(q)]);
  const eta = extCells.map((q) => Int.const(`eta_${q}`));
  for (const q of coreCells) {
    solver.add(And(u[q].ge(0), u[q].le(maxOdometer)));
    if (independent) {
      solver.add(And(v[q].ge(0), v[q].le(maxOdometer)));
    }
  }
  for (const q of extCells) {
    solver.add(And(eta[q].ge(0), eta[q].le(3)));
    if (!independent) {
      solver.add(eta[q].eq(eta[transposeExt(q)]));
    }
  }
  const fieldExt = (field, row, column) => {
    if (row < 1 || row > n || column < 1 || column > n) return 0;
    return field[coreAt(row - 1, column - 1)];
  };
  const sum = (terms) => {
    if (terms.length === 0) return 0;
    if (terms.length === 1) return terms[0];
    return Sum(...terms);
  };
  const makeResidual = (field, sourceCore) => {
    const sourceRow = 1 + Math.floor(sourceCore / n);
    const sourceColumn = 1 + (sourceCore % n);
    const result = [];
    for (const q of extCells) {
      const [row, column] = rc(q, m);
      const center = fieldExt(field, row, column);
      const incoming = sum([
        fieldExt(field, row - 1, column),
        fieldExt(field, row + 1, column),
        fieldExt(field, row, column - 1),
        fieldExt(field, row, column + 1),
      ].filter((value) => value !== 0));
      const isSource = row === sourceRow && column === sourceColumn;
      result.push(
        (typeof center === "number" ? Int.val(0) : center.mul(-4))
          .add(incoming)
          .add(isSource ? pulse : 0)
      );
    }
    return result;
  };
  const residualU = makeResidual(u, ports.north);
  const residualV = makeResidual(v, ports.west);

  for (const q of extCells) {
    const rn = residualU[q];
    const rw = residualV[q];
    solver.add(
      Or(
        And(rn.eq(0), rw.eq(0)),
        And(rn.eq(1), rw.eq(0)),
        And(rn.eq(-1), rw.eq(0)),
        And(rn.eq(0), rw.eq(1)),
        And(rn.eq(0), rw.eq(-1))
      )
    );
    for (let a = 0; a <= 3; a++) {
      for (let b = 0; b <= 3; b++) {
        const final = eta[q].add(rn.mul(a)).add(rw.mul(b));
        solver.add(And(final.ge(0), final.le(3)));
      }
    }
  }
  solver.add(u[ports.north].gt(0));
  solver.add(v[ports.west].gt(0));
  if (canonical) {
    solver.add(u[ports.south].eq(1));
    solver.add(u[ports.east].eq(2));
    solver.add(v[ports.south].eq(2));
    solver.add(v[ports.east].eq(1));
  } else {
    solver.add(u[ports.south].mod(2).eq(1));
    solver.add(u[ports.east].mod(2).eq(0));
    solver.add(v[ports.south].mod(2).eq(0));
    solver.add(v[ports.east].mod(2).eq(1));
    if (!allowZeroCross) {
      solver.add(u[ports.east].gt(0));
      solver.add(v[ports.south].gt(0));
    }
  }

  // If the full table is exactly linear, stabilizing the already-stable
  // state at (a,b) after one additional pulse must begin at the newly
  // modified input cell.  These are necessary conditions and substantially
  // prune algebraic-but-nonlegal models.
  const northExt = extAt(1 + inset, 1 + middle);
  const westExt = extAt(1 + middle, 1 + inset);
  for (let a = 0; a < 3; a++) {
    for (let b = 0; b <= 3; b++) {
      solver.add(
        eta[northExt]
          .add(residualU[northExt].mul(a))
          .add(residualV[northExt].mul(b))
          .add(pulse)
          .ge(4)
      );
    }
  }
  for (let a = 0; a <= 3; a++) {
    for (let b = 0; b < 3; b++) {
      solver.add(
        eta[westExt]
          .add(residualU[westExt].mul(a))
          .add(residualV[westExt].mul(b))
          .add(pulse)
          .ge(4)
      );
    }
  }

  function legalTable(uValues, vValues, etaValues) {
    const side = m + 4;
    const offset = 2;
    const boardAt = (row, column) => row * side + column;
    const base = Array(side * side).fill(0);
    for (let row = 0; row < m; row++) {
      for (let column = 0; column < m; column++) {
        base[boardAt(offset + row, offset + column)] =
          etaValues[extAt(row, column)];
      }
    }
    const north = boardAt(offset + 1 + inset, offset + 1 + middle);
    const west = boardAt(offset + 1 + middle, offset + 1 + inset);
    const expectedNorth = Array(side * side).fill(0);
    const expectedWest = Array(side * side).fill(0);
    for (let row = 0; row < n; row++) {
      for (let column = 0; column < n; column++) {
        expectedNorth[
          boardAt(offset + 1 + row, offset + 1 + column)
        ] = uValues[coreAt(row, column)];
        expectedWest[
          boardAt(offset + 1 + row, offset + 1 + column)
        ] = vValues[coreAt(row, column)];
      }
    }
    const tables = [];
    for (let a = 0; a <= 3; a++) {
      tables.push([]);
      for (let b = 0; b <= 3; b++) {
        const state = base.slice();
        const odo = Array(side * side).fill(0);
        state[north] += a * pulse;
        state[west] += b * pulse;
        const queue = [];
        const queued = new Uint8Array(side * side);
        for (let q = 0; q < state.length; q++) {
          if (state[q] >= 4) {
            queue.push(q);
            queued[q] = 1;
          }
        }
        let head = 0;
        while (head < queue.length) {
          const q = queue[head++];
          queued[q] = 0;
          const amount = Math.floor(state[q] / 4);
          if (!amount) continue;
          state[q] -= 4 * amount;
          odo[q] += amount;
          const row = Math.floor(q / side);
          const column = q % side;
          for (const neighbor of [
            row ? q - side : -1,
            row + 1 < side ? q + side : -1,
            column ? q - 1 : -1,
            column + 1 < side ? q + 1 : -1,
          ]) {
            if (neighbor < 0) continue;
            state[neighbor] += amount;
            if (state[neighbor] >= 4 && !queued[neighbor]) {
              queued[neighbor] = 1;
              queue.push(neighbor);
            }
          }
        }
        for (let q = 0; q < odo.length; q++) {
          const expected =
            a * expectedNorth[q] + b * expectedWest[q];
          if (odo[q] !== expected) return null;
        }
        tables[a].push([
          odo[boardAt(
            offset + 1 + n - 1 - inset,
            offset + 1 + middle
          )],
          odo[boardAt(
            offset + 1 + middle,
            offset + 1 + n - 1 - inset
          )],
        ]);
      }
    }
    return tables;
  }

  console.log(JSON.stringify({
    n, pulse, inset, maxOdometer, maxModels, timeout, canonical,
    independent, allowZeroCross, ports,
  }));
  for (let attempt = 1; attempt <= maxModels; attempt++) {
    const result = await solver.check();
    if (String(result) !== "sat") {
      console.log(String(result), `after_models=${attempt - 1}`);
      return;
    }
    const model = solver.model();
    const value = (expression) =>
      Number(model.eval(expression).toString());
    const uValues = u.map(value);
    const vValues = v.map(value);
    const etaValues = eta.map(value);
    const table = legalTable(uValues, vValues, etaValues);
    if (table !== null) {
      const grid = (values, side) =>
        [...Array(side).keys()].map((row) =>
          values.slice(row * side, (row + 1) * side)
        );
      console.log("FULL LINEAR ODOMETER CROSSING FOUND");
      console.log(JSON.stringify({
        u: grid(uValues, n),
        v: grid(vValues, n),
        eta: grid(etaValues, m),
        residualU: grid(residualU.map(value), m),
        residualV: grid(residualV.map(value), m),
        table,
      }));
      return;
    }
    if (attempt % 100 === 0) {
      console.log(`blocked_nonleast_models=${attempt}`);
    }
    solver.add(Or(
      ...u.map((expression, q) => expression.neq(uValues[q])),
      ...(independent
        ? v.map((expression, q) => expression.neq(vValues[q]))
        : []),
      ...eta.map((expression, q) => expression.neq(etaValues[q]))
    ));
  }
  console.log(`no legal hit in ${maxModels} algebraic models`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
