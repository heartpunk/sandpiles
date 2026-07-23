#!/usr/bin/env node
/*
 * Exact synthesis of a resetting, full-alphabet sandpile parity crossover.
 *
 * We search directly for the one-pulse odometer u of the north input.  The
 * west-input odometer is its transpose.  Let
 *
 *   T = supp(u) union supp(u^T).
 *
 * A pulse of p grains resets every cell of T iff
 *
 *   Delta u = p delta_north                    on T,
 *
 * where Delta u(x) = 4u(x) - sum_{y~x}u(y).  Cells outside T never topple;
 * they merely collect q(x) = sum_{y~x}u(y) grains.  Requiring
 *
 *   q_N(x) + q_W(x) <= 1                       outside T
 *
 * means that arbitrary inputs a,b in {0,1,2,3} leave every garbage cell at
 * height at most 3.  Hence a*u + b*u^T is the exact odometer for all 16 input
 * pairs when T starts at height 3 and its complement at height 0.
 *
 * The requested tap values
 *
 *   u(south) = 1,  u(east) = 2
 *
 * give total output counts (a+2b, 2a+b), whose parities are (a,b).
 *
 * The bounding square is surrounded by implicit zero cells.  Boundary
 * leakage from the two pulses is constrained in the same way as leakage to
 * explicit zero cells.
 */

const { init } = require("z3-solver");

function numberArg(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? Number(process.argv[index + 1]) : fallback;
}

function hasArg(name) {
  return process.argv.includes(name);
}

async function main() {
  const n = numberArg("--size", 9);
  const pulse = numberArg("--pulse", 4);
  const sourceInset = numberArg("--source-inset", 1);
  const tapInset = numberArg("--tap-inset", 1);
  const maxOdometer = numberArg("--max-odometer", Math.max(40, 4 * pulse));
  const timeout = numberArg("--timeout-ms", 600000);
  const printSmt = hasArg("--print-smt");

  if (!Number.isInteger(n) || n < 3 || n % 2 === 0) {
    throw new Error("--size must be an odd integer >= 3");
  }
  for (const [name, value] of [
    ["--pulse", pulse],
    ["--source-inset", sourceInset],
    ["--tap-inset", tapInset],
    ["--max-odometer", maxOdometer],
    ["--timeout-ms", timeout],
  ]) {
    if (!Number.isInteger(value) || value < 0) {
      throw new Error(`${name} must be a nonnegative integer`);
    }
  }
  if (pulse < 1) throw new Error("--pulse must be at least 1");
  if (sourceInset >= n || tapInset >= n) {
    throw new Error("port insets must be smaller than --size");
  }

  const { Context } = await init();
  const {
    Solver,
    Int,
    Sum,
    And,
    Or,
    Not,
    Implies,
  } = new Context("reset_potential");
  const solver = new Solver();
  solver.set("timeout", timeout);

  const at = (row, column) => row * n + column;
  const rc = (position) => [
    Math.floor(position / n),
    position % n,
  ];
  const transpose = (position) => {
    const [row, column] = rc(position);
    return at(column, row);
  };
  const cells = [...Array(n * n).keys()];
  const middle = Math.floor(n / 2);
  const ports = {
    north: at(sourceInset, middle),
    west: at(middle, sourceInset),
    south: at(n - 1 - tapInset, middle),
    east: at(middle, n - 1 - tapInset),
  };

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
        && neighborRow < n
        && neighborColumn >= 0
        && neighborColumn < n
      ) {
        result.push(at(neighborRow, neighborColumn));
      }
    }
    return result;
  }
  const adjacency = cells.map(neighbors);

  const u = cells.map((position) => Int.const(`u_${position}`));
  const westAt = (position) => u[transpose(position)];
  for (const position of cells) {
    solver.add(And(u[position].ge(0), u[position].le(maxOdometer)));
  }

  const sumOrZero = (terms) => {
    if (terms.length === 0) return 0;
    if (terms.length === 1) return terms[0];
    return Sum(...terms);
  };
  const incomingNorth = (position) =>
    sumOrZero(adjacency[position].map((neighbor) => u[neighbor]));
  const incomingWest = (position) =>
    sumOrZero(adjacency[position].map((neighbor) => westAt(neighbor)));
  const laplacianNorth = (position) =>
    u[position].mul(4).sub(incomingNorth(position));

  // The north source must genuinely topple.  The transpose condition then
  // makes the west source topple under the west pulse.
  solver.add(u[ports.north].gt(0));

  for (const position of cells) {
    const northActive = u[position].gt(0);
    const westActive = westAt(position).gt(0);
    const core = Or(northActive, westActive);
    const northCharge = position === ports.north ? pulse : 0;

    // Every common-core cell returns to its original height after a north
    // pulse.  Transposition supplies the analogous west-pulse equations.
    solver.add(
      Implies(core, laplacianNorth(position).eq(northCharge))
    );

    // A cell outside the common core is inert garbage.  Across one pulse of
    // each input it receives at most one grain total, so any a,b <= 3 leave
    // it stable.
    solver.add(
      Implies(
        Not(core),
        incomingNorth(position).add(incomingWest(position)).le(1)
      )
    );
  }

  // Implicit cells immediately outside the bounding square are also garbage.
  // Each is adjacent to exactly one boundary cell of the square.
  for (let offset = 0; offset < n; offset++) {
    for (const boundary of [
      at(0, offset),
      at(n - 1, offset),
      at(offset, 0),
      at(offset, n - 1),
    ]) {
      solver.add(u[boundary].add(westAt(boundary)).le(1));
    }
  }

  // Canonical parity-linear mixing matrix:
  // north -> (south,east) = (1,2), west -> (2,1).
  solver.add(u[ports.south].eq(1));
  solver.add(u[ports.east].eq(2));

  console.log(JSON.stringify({
    n,
    pulse,
    sourceInset,
    tapInset,
    maxOdometer,
    timeout,
    ports,
  }));
  if (printSmt) console.log(solver.toString());
  const result = await solver.check();
  console.log(result);
  if (result !== "sat") return;

  const model = solver.model();
  const value = (expression) => Number(model.eval(expression).toString());
  const grid = [];
  const westGrid = [];
  const coreGrid = [];
  const garbageNorth = [];
  const garbageWest = [];
  for (let row = 0; row < n; row++) {
    grid.push([]);
    westGrid.push([]);
    coreGrid.push([]);
    garbageNorth.push([]);
    garbageWest.push([]);
    for (let column = 0; column < n; column++) {
      const position = at(row, column);
      const northValue = value(u[position]);
      const westValue = value(westAt(position));
      grid[row].push(northValue);
      westGrid[row].push(westValue);
      const core = northValue > 0 || westValue > 0;
      coreGrid[row].push(core ? 3 : 0);
      garbageNorth[row].push(core ? 0 : value(incomingNorth(position)));
      garbageWest[row].push(core ? 0 : value(incomingWest(position)));
    }
  }
  console.log(JSON.stringify({
    grid,
    westGrid,
    initialHeights: coreGrid,
    garbageNorth,
    garbageWest,
  }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
