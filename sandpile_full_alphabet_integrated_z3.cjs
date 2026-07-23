#!/usr/bin/env node
/*
 * Exact full-alphabet synthesis in the integrated 6x6-gate topology.
 *
 * The only symbolic cells are a 6x6 gate.  Fixed all-height-3 output
 * rectangles continue south and east, exactly as in the certified Boolean
 * parity crossover.  Inputs a,b in {0,1,2,3} are added directly at the two
 * gate ports.  For all 15 nonzero input pairs, a legal event-layer
 * stabilization is encoded and the remote output odometer parities are
 * required to equal (a mod 2,b mod 2).
 *
 * Event bounds come from the pointwise maximal gate (all height 3) with
 * additions (3,3).  Monotonicity of the Abelian-sandpile odometer makes these
 * rigorous bounds for every stable symbolic gate and every encoded input.
 */

const { init } = require("z3-solver");

function numberArg(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? Number(process.argv[index + 1]) : fallback;
}

function maximalOdometer(boardSize, base, sources) {
  const state = base.slice();
  for (const [position, amount] of sources) state[position] += amount;
  const odometer = new Array(state.length).fill(0);
  const queue = [];
  const queued = new Array(state.length).fill(false);
  for (let position = 0; position < state.length; position++) {
    if (state[position] >= 4) {
      queue.push(position);
      queued[position] = true;
    }
  }
  for (let head = 0; head < queue.length; head++) {
    const position = queue[head];
    queued[position] = false;
    const count = Math.floor(state[position] / 4);
    if (count === 0) continue;
    state[position] -= 4 * count;
    odometer[position] += count;
    const row = Math.floor(position / boardSize);
    const column = position % boardSize;
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
        const neighbor = neighborRow * boardSize + neighborColumn;
        state[neighbor] += count;
        if (state[neighbor] >= 4 && !queued[neighbor]) {
          queue.push(neighbor);
          queued[neighbor] = true;
        }
      }
    }
  }
  return odometer;
}

async function main() {
  const coreSize = numberArg("--size", 11);
  const padding = numberArg("--padding", 3);
  const timeout = numberArg("--timeout-ms", 1800000);
  const symmetric = process.argv.includes("--symmetric");
  if (!Number.isInteger(coreSize) || coreSize < 11) {
    throw new Error("--size must be an integer >= 11");
  }
  if (!Number.isInteger(padding) || padding < 2) {
    throw new Error("--padding must be an integer >= 2");
  }

  const boardSize = coreSize + 2 * padding;
  const area = boardSize * boardSize;
  const at = (row, column) => row * boardSize + column;
  const coreAt = (row, column) => at(padding + row, padding + column);
  const rc = (position) => [
    Math.floor(position / boardSize),
    position % boardSize,
  ];
  const cells = [...Array(area).keys()];
  const ports = {
    north: coreAt(2, 3),
    west: coreAt(3, 2),
    south: coreAt(coreSize - 3, 3),
    east: coreAt(3, coreSize - 3),
  };

  const fixed = new Array(area).fill(0);
  const gatePositions = [];
  for (let row = 0; row < 6; row++) {
    for (let column = 0; column < 6; column++) {
      gatePositions.push(coreAt(row, column));
    }
  }
  for (let row = 6; row < coreSize; row++) {
    for (let column = 1; column < 6; column++) {
      fixed[coreAt(row, column)] = 3;
    }
  }
  for (let row = 1; row < 6; row++) {
    for (let column = 6; column < coreSize; column++) {
      fixed[coreAt(row, column)] = 3;
    }
  }

  const maximalBase = fixed.slice();
  for (const position of gatePositions) maximalBase[position] = 3;
  const upper = maximalOdometer(
    boardSize,
    maximalBase,
    [[ports.north, 3], [ports.west, 3]]
  );
  const eventBound = upper.reduce((left, right) => left + right, 0);

  const { Context } = await init();
  const {
    Solver,
    Int,
    Sum,
    And,
    Implies,
    If,
  } = new Context("full_alphabet_integrated");
  const solver = new Solver();
  solver.set("timeout", timeout);

  const gateSet = new Set(gatePositions);
  const base = cells.map((position) => Int.const(`base_${position}`));
  for (const position of cells) {
    if (gateSet.has(position)) {
      solver.add(And(base[position].ge(0), base[position].le(3)));
    } else {
      solver.add(base[position].eq(fixed[position]));
    }
  }
  if (symmetric) {
    for (let row = 0; row < 6; row++) {
      for (let column = row + 1; column < 6; column++) {
        solver.add(
          base[coreAt(row, column)].eq(base[coreAt(column, row)])
        );
      }
    }
  }
  const baseAt = (position) => base[position];

  function neighbors(position) {
    const [row, column] = rc(position);
    const result = [];
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
        result.push(at(neighborRow, neighborColumn));
      }
    }
    return result;
  }
  const adjacency = cells.map(neighbors);
  const sumOrZero = (terms) => {
    if (terms.length === 0) return 0;
    if (terms.length === 1) return terms[0];
    return Sum(...terms);
  };

  function encodeRun(name, northAmount, westAmount) {
    const odometer = cells.map((position) =>
      Int.const(`${name}_odo_${position}`)
    );
    const layer = cells.map((position) =>
      [...Array(upper[position]).keys()].map((zeroBased) =>
        Int.const(`${name}_time_${position}_${zeroBased + 1}`)
      )
    );

    for (const position of cells) {
      solver.add(
        And(
          odometer[position].ge(0),
          odometer[position].le(upper[position])
        )
      );
      const addition =
        (position === ports.north ? northAmount : 0) +
        (position === ports.west ? westAmount : 0);

      for (let event = 1; event <= upper[position]; event++) {
        const exists = odometer[position].ge(event);
        solver.add(
          Implies(
            exists,
            And(
              layer[position][event - 1].ge(1),
              layer[position][event - 1].le(eventBound)
            )
          )
        );
        if (event > 1) {
          solver.add(
            Implies(
              exists,
              layer[position][event - 2].lt(
                layer[position][event - 1]
              )
            )
          );
        }

        const incomingEvents = [];
        for (const neighbor of adjacency[position]) {
          for (
            let neighborEvent = 1;
            neighborEvent <= upper[neighbor];
            neighborEvent++
          ) {
            incomingEvents.push(
              If(
                And(
                  odometer[neighbor].ge(neighborEvent),
                  layer[neighbor][neighborEvent - 1].lt(
                    layer[position][event - 1]
                  )
                ),
                1,
                0
              )
            );
          }
        }
        solver.add(
          Implies(
            exists,
            baseAt(position)
              .add(addition)
              .add(sumOrZero(incomingEvents))
              .sub(4 * (event - 1))
              .ge(4)
          )
        );
      }

      const finalHeight = baseAt(position)
        .add(addition)
        .sub(odometer[position].mul(4))
        .add(
          sumOrZero(
            adjacency[position].map((neighbor) => odometer[neighbor])
          )
        );
      solver.add(And(finalHeight.ge(0), finalHeight.le(3)));

      const [row, column] = rc(position);
      if (
        row === 0
        || column === 0
        || row === boardSize - 1
        || column === boardSize - 1
      ) {
        // Certifies that the padded finite computation is also an
        // infinite-lattice computation.
        solver.add(odometer[position].eq(0));
      }
    }
    return odometer;
  }

  const runs = [];
  for (let north = 0; north < 4; north++) {
    for (let west = 0; west < 4; west++) {
      if (north === 0 && west === 0) continue;
      const odometer = encodeRun(`R_${north}_${west}`, north, west);
      solver.add(
        odometer[ports.south].mod(2).eq(north & 1)
      );
      solver.add(
        odometer[ports.east].mod(2).eq(west & 1)
      );
      runs.push({ north, west, odometer });
    }
  }

  console.log(JSON.stringify({
    coreSize,
    padding,
    boardSize,
    timeout,
    symmetric,
    eventBound,
    nonzeroUpperCells: upper.filter((value) => value > 0).length,
    maximumPerCellUpper: Math.max(...upper),
  }));
  const result = await solver.check();
  console.log(String(result));
  if (String(result) !== "sat") return;

  const model = solver.model();
  const value = (expression) =>
    Number(model.eval(expression).toString());
  const gate = [];
  for (let row = 0; row < 6; row++) {
    gate.push([]);
    for (let column = 0; column < 6; column++) {
      gate[row].push(value(baseAt(coreAt(row, column))));
    }
  }
  const table = runs.map(({ north, west, odometer }) => ({
    north,
    west,
    south: value(odometer[ports.south]),
    east: value(odometer[ports.east]),
  }));
  console.log(JSON.stringify({ gate, table }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
