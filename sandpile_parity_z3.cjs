#!/usr/bin/env node
/*
 * Exact synthesis/UNSAT checker for a parity-coded crossover in the standard
 * von Neumann Abelian sandpile.
 *
 * A stable n x n core is surrounded by one quiescent layer.  We add one grain
 * at N, W, or both and run deterministic parallel toppling until stable.  The
 * logical outputs are the parities of the odometers at S and E:
 *
 *                 N run   W run   NW run
 *     south         1       0        1
 *     east          0       1        1       (all modulo 2).
 *
 * Parallel toppling is only a convenient canonical legal schedule.  Once the
 * final state is stable, its odometer is the ordinary Abelian stabilization
 * odometer.
 *
 * For an exact exhaustive claim, choose --horizon at least the total number of
 * topplings made by the pointwise-maximal all-3 core under the two-input
 * experiment.  Odometer monotonicity then bounds every stable background, and
 * every nonterminal parallel round contains at least one toppling.
 */

const { init } = require("z3-solver");

function numberArg(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? Number(process.argv[index + 1]) : fallback;
}

async function main() {
  const coreSize = numberArg("--size", 5);
  const inset = numberArg("--port-inset", 1);
  const padding = numberArg("--padding", 1);
  const horizon = numberArg("--horizon", 40);
  const timeout = numberArg("--timeout-ms", 600000);
  const symmetric = process.argv.includes("--symmetric");
  const canonical = process.argv.includes("--canonical-counts");

  if (!Number.isInteger(coreSize) || coreSize < 3) {
    throw new Error("--size must be an integer >= 3");
  }
  if (
    !Number.isInteger(inset)
    || inset < 0
    || inset >= Math.floor(coreSize / 2)
  ) {
    throw new Error("--port-inset must lie between 0 and floor(size/2)-1");
  }
  if (!Number.isInteger(padding) || padding < 1) {
    throw new Error("--padding must be a positive integer");
  }
  if (!Number.isInteger(horizon) || horizon < 1) {
    throw new Error("--horizon must be a positive integer");
  }

  const boardSize = coreSize + 2 * padding;
  const area = boardSize * boardSize;
  const middle = Math.floor(coreSize / 2);
  const at = (row, column) => row * boardSize + column;
  const rowColumn = (position) => [
    Math.floor(position / boardSize),
    position % boardSize,
  ];
  const localAt = (row, column) =>
    at(padding + row, padding + column);
  const cells = [...Array(area).keys()];
  const coreCells = [];
  for (let row = 0; row < coreSize; row++) {
    for (let column = 0; column < coreSize; column++) {
      coreCells.push(localAt(row, column));
    }
  }
  const coreSet = new Set(coreCells);
  const boundaryCells = cells.filter((position) => {
    const [row, column] = rowColumn(position);
    return (
      row === 0
      || row === boardSize - 1
      || column === 0
      || column === boardSize - 1
    );
  });
  const ports = {
    north: localAt(inset, middle),
    west: localAt(middle, inset),
    south: localAt(coreSize - 1 - inset, middle),
    east: localAt(middle, coreSize - 1 - inset),
  };

  const { Context } = await init();
  const {
    Solver,
    Int,
    Bool,
    If,
    Sum,
    And,
    Or,
    Not,
  } = new Context("parity_crossover");
  const solver = new Solver();
  solver.set("timeout", timeout);

  const base = cells.map((position) =>
    Int.const(`base_${position}`)
  );
  for (const position of cells) {
    if (coreSet.has(position)) {
      solver.add(And(base[position].ge(0), base[position].le(3)));
    } else {
      solver.add(base[position].eq(0));
    }
  }
  if (symmetric) {
    for (let row = 0; row < coreSize; row++) {
      for (let column = row + 1; column < coreSize; column++) {
        solver.add(
          base[localAt(row, column)].eq(
            base[localAt(column, row)]
          )
        );
      }
    }
  }

  function encodeRun(name, additions) {
    const state = [];
    const fire = [];
    for (let time = 0; time <= horizon; time++) {
      state.push(
        cells.map((position) =>
          Int.const(`${name}_state_${time}_${position}`)
        )
      );
      if (time < horizon) {
        fire.push(
          cells.map((position) =>
            Bool.const(`${name}_fire_${time}_${position}`)
          )
        );
      }
    }

    for (const position of cells) {
      const added = additions.filter(
        (source) => source === position
      ).length;
      solver.add(state[0][position].eq(base[position].add(added)));
    }

    for (let time = 0; time < horizon; time++) {
      for (const position of cells) {
        const [row, column] = rowColumn(position);
        solver.add(
          fire[time][position].eq(state[time][position].ge(4))
        );
        const incoming = [];
        for (const [deltaRow, deltaColumn] of [
          [-1, 0],
          [1, 0],
          [0, -1],
          [0, 1],
        ]) {
          const neighborRow = row + deltaRow;
          const neighborColumn = column + deltaColumn;
          if (
            neighborRow >= 0
            && neighborRow < boardSize
            && neighborColumn >= 0
            && neighborColumn < boardSize
          ) {
            incoming.push(
              If(
                fire[time][at(neighborRow, neighborColumn)],
                1,
                0
              )
            );
          }
        }
        solver.add(
          state[time + 1][position].eq(
            state[time][position]
              .sub(If(fire[time][position], 4, 0))
              .add(Sum(...incoming))
          )
        );
      }
    }

    for (const position of cells) {
      solver.add(state[horizon][position].lt(4));
      solver.add(state[horizon][position].ge(0));
    }
    // The finite board is only a window into Z^2, not a dissipative sink.
    // Requiring its outer layer never to topple certifies that the omitted
    // infinite quiescent exterior cannot affect the computation.
    for (const position of boundaryCells) {
      for (let time = 0; time < horizon; time++) {
        solver.add(Not(fire[time][position]));
      }
    }

    const odometer = (position) =>
      Sum(
        ...fire.map((row) => If(row[position], 1, 0))
      );
    return { state, fire, odometer };
  }

  const north = encodeRun("N", [ports.north]);
  const west = encodeRun("W", [ports.west]);
  const both = encodeRun("NW", [ports.north, ports.west]);

  const counts = [
    north.odometer(ports.south),
    north.odometer(ports.east),
    west.odometer(ports.south),
    west.odometer(ports.east),
    both.odometer(ports.south),
    both.odometer(ports.east),
  ];
  const targetParity = [1, 0, 0, 1, 1, 1];
  for (let index = 0; index < counts.length; index++) {
    solver.add(counts[index].mod(2).eq(targetParity[index]));
  }
  if (canonical) {
    const targetCounts = [1, 2, 2, 1, 3, 3];
    for (let index = 0; index < counts.length; index++) {
      solver.add(counts[index].eq(targetCounts[index]));
    }
  }

  console.log(
    JSON.stringify({
      coreSize,
      inset,
      padding,
      horizon,
      timeout,
      symmetric,
      canonical,
      boardSize,
    })
  );
  const result = await solver.check();
  console.log(result);
  if (String(result) !== "sat") return;

  const model = solver.model();
  const value = (expression) =>
    Number(model.eval(expression).toString());
  const grid = [];
  for (let row = 0; row < coreSize; row++) {
    grid.push(
      [...Array(coreSize).keys()].map((column) =>
        value(base[localAt(row, column)])
      )
    );
  }
  console.log(
    JSON.stringify({
      counts: counts.map(value),
      grid,
    })
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
