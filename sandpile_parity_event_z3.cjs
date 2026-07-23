#!/usr/bin/env node
/*
 * Exact event-order SMT synthesis for a one-grain parity crossover.
 *
 * This is equivalent to sandpile_parity_z3.cjs, but avoids unrolling many
 * mostly idle parallel time steps.  Each potential toppling event receives a
 * symbolic layer.  An event is required to be legal using all events in
 * strictly earlier layers; events in the same layer are already legal before
 * any of them fires, so they can be serialized in arbitrary order.
 *
 * Per-cell odometer bounds are computed by stabilizing the pointwise maximal
 * all-3 background with both inputs active.  Monotonicity of the Abelian
 * sandpile odometer makes those rigorous bounds for all three experiments and
 * for every stable background.
 */

const { init } = require("z3-solver");

function numberArg(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? Number(process.argv[index + 1]) : fallback;
}

function maximalOdometer(coreSize, north, west) {
  const area = coreSize * coreSize;
  const state = new Array(area).fill(3);
  state[north] += 1;
  state[west] += 1;
  const odometer = new Array(area).fill(0);
  const queue = [];
  const queued = new Array(area).fill(false);
  for (let position = 0; position < area; position++) {
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
    const row = Math.floor(position / coreSize);
    const column = position % coreSize;
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
        && neighborRow < coreSize
        && neighborColumn >= 0
        && neighborColumn < coreSize
      ) {
        const neighbor = neighborRow * coreSize + neighborColumn;
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
  const coreSize = numberArg("--size", 5);
  const inset = numberArg("--port-inset", 1);
  const timeout = numberArg("--timeout-ms", 600000);
  const symmetric = process.argv.includes("--symmetric");
  const canonical = process.argv.includes("--canonical-counts");
  const clean = process.argv.includes("--clean-counts");
  const relaxed = process.argv.includes("--relaxed");
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

  const area = coreSize * coreSize;
  const cells = [...Array(area).keys()];
  const at = (row, column) => row * coreSize + column;
  const rowColumn = (position) => [
    Math.floor(position / coreSize),
    position % coreSize,
  ];
  const middle = Math.floor(coreSize / 2);
  const ports = {
    north: at(inset, middle),
    west: at(middle, inset),
    south: at(coreSize - 1 - inset, middle),
    east: at(middle, coreSize - 1 - inset),
  };
  const upper = maximalOdometer(
    coreSize,
    ports.north,
    ports.west
  );
  const eventBound = upper.reduce((left, right) => left + right, 0);

  const { Context } = await init();
  const {
    Solver,
    Int,
    If,
    Sum,
    And,
    Implies,
  } = new Context("parity_event_crossover");
  const solver = new Solver();
  solver.set("timeout", timeout);

  const base = cells.map((position) =>
    Int.const(`base_${position}`)
  );
  for (const position of cells) {
    solver.add(And(base[position].ge(0), base[position].le(3)));
  }
  if (symmetric) {
    for (let row = 0; row < coreSize; row++) {
      for (let column = row + 1; column < coreSize; column++) {
        solver.add(
          base[at(row, column)].eq(base[at(column, row)])
        );
      }
    }
  }

  function neighbors(position) {
    const [row, column] = rowColumn(position);
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
        && neighborRow < coreSize
        && neighborColumn >= 0
        && neighborColumn < coreSize
      ) {
        result.push(at(neighborRow, neighborColumn));
      }
    }
    return result;
  }
  const adjacency = cells.map(neighbors);

  function encodeRun(name, sources) {
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
      for (let event = 1; event <= upper[position]; event++) {
        const exists = odometer[position].ge(event);
        if (relaxed) continue;
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
        const addition = sources.filter(
          (source) => source === position
        ).length;
        const incoming =
          incomingEvents.length === 0 ? 0 : Sum(...incomingEvents);
        // Immediately before its kth toppling, this site has already made
        // exactly k-1 topplings and has received every strictly earlier
        // neighboring toppling.
        solver.add(
          Implies(
            exists,
            base[position]
              .add(addition)
              .add(incoming)
              .sub(4 * (event - 1))
              .ge(4)
          )
        );
      }

      const addition = sources.filter(
        (source) => source === position
      ).length;
      const received = adjacency[position].map(
        (neighbor) => odometer[neighbor]
      );
      const finalHeight = base[position]
        .add(addition)
        .sub(odometer[position].mul(4))
        .add(received.length === 0 ? 0 : Sum(...received));
      solver.add(And(finalHeight.ge(0), finalHeight.le(3)));
    }
    return { odometer, layer };
  }

  const north = encodeRun("N", [ports.north]);
  const west = encodeRun("W", [ports.west]);
  const both = encodeRun("NW", [ports.north, ports.west]);
  const counts = [
    north.odometer[ports.south],
    north.odometer[ports.east],
    west.odometer[ports.south],
    west.odometer[ports.east],
    both.odometer[ports.south],
    both.odometer[ports.east],
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
  if (clean) {
    const targetCounts = [1, 0, 0, 1, 1, 1];
    for (let index = 0; index < counts.length; index++) {
      solver.add(counts[index].eq(targetCounts[index]));
    }
    // The intended singleton outputs are nonzero, so the only initially
    // unstable site in each singleton experiment must fire.
    solver.add(base[ports.north].eq(3));
    solver.add(base[ports.west].eq(3));
    // No-islands comparison for u_N versus u_W: the component of
    // {u_N > u_W} containing S must contain the sole positive source N.
    // The symmetric statement holds at W.
    solver.add(
      north.odometer[ports.north].gt(
        west.odometer[ports.north]
      )
    );
    solver.add(
      west.odometer[ports.west].gt(
        north.odometer[ports.west]
      )
    );
  }

  console.log(
    JSON.stringify({
      coreSize,
      inset,
      timeout,
      symmetric,
      canonical,
      clean,
      relaxed,
      eventBound,
      perCellUpperBound: Array.from(
        { length: coreSize },
        (_, row) =>
          upper.slice(row * coreSize, (row + 1) * coreSize)
      ),
    })
  );
  const result = await solver.check();
  console.log(result);
  if (String(result) !== "sat") return;

  const model = solver.model();
  const value = (expression) =>
    Number(model.eval(expression).toString());
  const grid = Array.from({ length: coreSize }, (_, row) =>
    [...Array(coreSize).keys()].map((column) =>
      value(base[at(row, column)])
    )
  );
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
