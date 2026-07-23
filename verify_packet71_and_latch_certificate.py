#!/usr/bin/env python3
"""Pure-stdlib verifier for the packet-71 AND latch witness.

The verifier works directly on sparse dictionaries indexed by the literal
infinite lattice Z^2.  It does not import the discovery/search programs, use a
finite box, or introduce a sink.  Stabilization proceeds in synchronous legal
waves.  Within a wave, each unstable site performs floor(height/4) topplings;
those batched topplings can be expanded into legal unit topplings because the
site was already unstable before any incoming grains from the same wave.

The certificate covers four deliberately separate claims:

1. with height-three output ports and outward fuse rays, one stabilization
   transmits Boolean AND exactly once along all eight finite rays;
2. two remote odometer taps compute full-alphabet parity AND;
3. on Boolean inputs, eight initially zero cells store exact copies of AND
   without toppling during the write;
4. a later three-grain clock at all eight cells is silent on false inputs and
   makes every output cell topple exactly once on the true input.

These checks do not establish a closed packet-to-packet cascade, reusability,
minimality, universality, or literature novelty.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping


Site = tuple[int, int]
Sparse = dict[Site, int]

CERTIFICATE = Path(__file__).with_name(
    "packet71_and_latch_certificate.json"
)

THRESHOLD = 4
PACKET = 71
A = (0, 0)
B = (0, 1)
D = (1, 0)
C = (1, 1)
CORE_SITES = (A, B, D, C)
CORE = (1, 1, 2, 2)
Q_LEFT = (3, -1)
Q_RIGHT = (3, 2)
AND_TAPS = (Q_LEFT, Q_RIGHT)
MEMORY_CELLS = (
    (-4, -1),
    (-4, 2),
    (-1, -4),
    (-1, 5),
    (1, -4),
    (1, 5),
    (4, -1),
    (4, 2),
)
FUSE_DIRECTIONS = (
    (-1, 0),
    (-1, 0),
    (0, -1),
    (0, 1),
    (0, -1),
    (0, 1),
    (1, 0),
    (1, 0),
)
CERTIFIED_FUSE_LENGTHS = (1, 2, 8, 32, 100)
CERTIFIED_PRECHARGED_FUSE_LENGTHS = (0, 1, 2, 8, 32, 100, 500)
DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))

EXPECTED_LEFT_TABLE = (
    (0, 0, 2, 6),
    (0, 1, 6, 13),
    (4, 8, 14, 22),
    (10, 15, 24, 31),
)
EXPECTED_RIGHT_TABLE = (
    (0, 0, 4, 10),
    (0, 1, 8, 15),
    (2, 6, 14, 24),
    (6, 13, 22, 31),
)
EXPECTED_WITNESS_MAXIMUM = {
    "total_unit_topplings": 3510,
    "maximum_site_topplings": 165,
    "odometer_sites": 174,
    "odometer_box": [-7, 7, -6, 7],
    "odometer_linf_radius": 7,
    "final_box": [-8, 8, -7, 8],
}
EXPECTED_CLASS_DOMINATOR = {
    "total_unit_topplings": 3570,
    "maximum_site_topplings": 167,
    "odometer_sites": 174,
    "odometer_box": [-7, 7, -6, 7],
    "odometer_linf_radius": 7,
    "final_box": [-8, 8, -7, 8],
}


def neighbors(site: Site) -> tuple[Site, Site, Site, Site]:
    row, column = site
    return (
        (row - 1, column),
        (row + 1, column),
        (row, column - 1),
        (row, column + 1),
    )


def nonzero(values: Mapping[Site, int]) -> Sparse:
    return {site: value for site, value in values.items() if value}


def add_grains(
    base: Mapping[Site, int],
    additions: Iterable[tuple[Site, int]],
) -> Sparse:
    result: defaultdict[Site, int] = defaultdict(int, base)
    for site, amount in additions:
        if amount < 0:
            raise ValueError("grain additions must be nonnegative")
        result[site] += amount
    return nonzero(result)


def fuse_rays(length: int) -> tuple[tuple[Site, ...], ...]:
    """Return the eight disjoint outward rays, excluding their ports."""
    if length < 0:
        raise ValueError("fuse length must be nonnegative")
    rays = tuple(
        tuple(
            (
                port[0] + distance * direction[0],
                port[1] + distance * direction[1],
            )
            for distance in range(1, length + 1)
        )
        for port, direction in zip(
            MEMORY_CELLS,
            FUSE_DIRECTIONS,
            strict=True,
        )
    )
    flattened = [site for ray in rays for site in ray]
    if len(set(flattened)) != len(flattened):
        raise AssertionError("outward fuse rays overlap")
    forbidden = set(CORE_SITES) | set(MEMORY_CELLS)
    if forbidden.intersection(flattened):
        raise AssertionError("a fuse ray overlaps the core or a port")
    return rays


def fuse_background(length: int) -> Sparse:
    return {
        site: 3
        for ray in fuse_rays(length)
        for site in ray
    }


def initial_state(
    core: tuple[int, int, int, int],
    packet: int,
    a: int,
    b: int,
) -> Sparse:
    if any(height < 0 or height >= THRESHOLD for height in core):
        raise ValueError("core must be stable")
    background = {
        site: height
        for site, height in zip(CORE_SITES, core, strict=True)
        if height
    }
    return add_grains(
        background,
        ((A, packet * a), (B, packet * b)),
    )


def digest_sparse(values: Mapping[Site, int]) -> str:
    encoded = "".join(
        f"{row},{column}:{value}\n"
        for (row, column), value in sorted(nonzero(values).items())
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def support_summary(values: Mapping[Site, int]) -> dict[str, object]:
    sites = list(nonzero(values))
    if not sites:
        return {
            "sites": 0,
            "bounding_box_row_min_row_max_col_min_col_max": None,
            "l1_radius_from_origin": 0,
            "linf_radius_from_origin": 0,
        }
    rows = [row for row, _ in sites]
    columns = [column for _, column in sites]
    return {
        "sites": len(sites),
        "bounding_box_row_min_row_max_col_min_col_max": [
            min(rows),
            max(rows),
            min(columns),
            max(columns),
        ],
        "l1_radius_from_origin": max(
            abs(row) + abs(column) for row, column in sites
        ),
        "linf_radius_from_origin": max(
            max(abs(row), abs(column)) for row, column in sites
        ),
    }


def stabilize_synchronous(
    initial: Mapping[Site, int],
) -> tuple[Sparse, Sparse, dict[str, int]]:
    """Stabilize on Z^2 using deterministic synchronous legal waves."""
    state: defaultdict[Site, int] = defaultdict(int, initial)
    odometer: defaultdict[Site, int] = defaultdict(int)
    frontier = {
        site for site, height in state.items() if height >= THRESHOLD
    }
    waves = 0
    wave_sites = 0
    maximum_wave_sites = len(frontier)
    maximum_batch_at_one_site = 0

    while frontier:
        batch = {
            site: state[site] // THRESHOLD
            for site in sorted(frontier)
            if state[site] >= THRESHOLD
        }
        if not batch:
            raise AssertionError("nonempty frontier made no progress")

        affected: set[Site] = set()
        for site, amount in batch.items():
            height = state[site]
            if height - THRESHOLD * (amount - 1) < THRESHOLD:
                raise AssertionError(
                    "batched toppling is not expandable into legal units"
                )
            state[site] -= THRESHOLD * amount
            odometer[site] += amount
            affected.add(site)
            for neighbor in neighbors(site):
                state[neighbor] += amount
                affected.add(neighbor)

        waves += 1
        wave_sites += len(batch)
        maximum_wave_sites = max(maximum_wave_sites, len(batch))
        maximum_batch_at_one_site = max(
            maximum_batch_at_one_site,
            max(batch.values()),
        )
        frontier = {
            site for site in affected if state[site] >= THRESHOLD
        }

    return (
        nonzero(state),
        nonzero(odometer),
        {
            "synchronous_waves": waves,
            "wave_site_batches": wave_sites,
            "maximum_wave_sites": maximum_wave_sites,
            "maximum_batch_topplings_at_one_site": (
                maximum_batch_at_one_site
            ),
        },
    )


def reconstruct_final(
    initial: Mapping[Site, int],
    odometer: Mapping[Site, int],
) -> Sparse:
    reconstructed: defaultdict[Site, int] = defaultdict(int, initial)
    for site, amount in odometer.items():
        reconstructed[site] -= THRESHOLD * amount
        for neighbor in neighbors(site):
            reconstructed[neighbor] += amount
    return nonzero(reconstructed)


def audit_transition(
    initial: Mapping[Site, int],
    label: str,
) -> tuple[dict[str, object], Sparse, Sparse]:
    final, odometer, execution = stabilize_synchronous(initial)
    reconstructed = reconstruct_final(initial, odometer)
    if reconstructed != final:
        raise AssertionError(f"{label}: Laplacian reconstruction failed")
    if any(height < 0 or height >= THRESHOLD for height in final.values()):
        raise AssertionError(f"{label}: final state is not stable")
    if sum(initial.values()) != sum(final.values()):
        raise AssertionError(f"{label}: mass conservation failed")

    record: dict[str, object] = {
        "label": label,
        "initial_mass": sum(initial.values()),
        "final_mass": sum(final.values()),
        "total_unit_topplings": sum(odometer.values()),
        "maximum_site_topplings": max(odometer.values(), default=0),
        **execution,
        "initial_support": support_summary(initial),
        "odometer_support": support_summary(odometer),
        "final_support": support_summary(final),
        "initial_configuration_sha256": digest_sparse(initial),
        "odometer_sha256": digest_sparse(odometer),
        "final_configuration_sha256": digest_sparse(final),
        "checks": {
            "all_wave_batches_expand_to_legal_unit_topplings": True,
            "final_state_stable": True,
            "discrete_laplacian_reconstruction": True,
            "mass_conserved_on_Z2": True,
        },
    }
    return record, final, odometer


def compute_write_case(
    a: int,
    b: int,
) -> tuple[dict[str, object], Sparse, Sparse]:
    initial = initial_state(CORE, PACKET, a, b)
    record, final, odometer = audit_transition(
        initial,
        f"write_a{a}_b{b}",
    )
    counts = [odometer.get(tap, 0) for tap in AND_TAPS]
    parities = [count & 1 for count in counts]
    target = (a & 1) * (b & 1)
    if parities != [target, target]:
        raise AssertionError(
            f"write ({a},{b}): parity-AND taps failed"
        )

    memory_heights = [final.get(site, 0) for site in MEMORY_CELLS]
    memory_odometers = [odometer.get(site, 0) for site in MEMORY_CELLS]
    boolean_interface_checked = a in (0, 1) and b in (0, 1)
    if boolean_interface_checked:
        exact_target = a * b
        if counts != [exact_target, exact_target]:
            raise AssertionError(
                f"write ({a},{b}): Boolean exact AND taps failed"
            )
        if memory_heights != [exact_target] * len(MEMORY_CELLS):
            raise AssertionError(
                f"write ({a},{b}): stored AND heights failed"
            )
        if any(memory_odometers):
            raise AssertionError(
                f"write ({a},{b}): a memory cell toppled"
            )

    record.update(
        {
            "a": a,
            "b": b,
            "additions_at_A_B": [PACKET * a, PACKET * b],
            "and_tap_counts_left_right": counts,
            "and_tap_parities_left_right": parities,
            "target_parity_and": target,
            "memory_cell_final_heights": memory_heights,
            "memory_cell_write_odometers": memory_odometers,
            "boolean_memory_interface_checked": (
                boolean_interface_checked
            ),
        }
    )
    checks = dict(record["checks"])
    checks["full_alphabet_parity_AND_at_both_taps"] = True
    if boolean_interface_checked:
        checks["Boolean_exact_count_AND_at_both_taps"] = True
        checks["eight_quiescent_cells_store_exact_AND"] = True
    record["checks"] = checks
    return record, final, odometer


def compute_simultaneous_clock_case(
    a: int,
    b: int,
) -> tuple[dict[str, object], Sparse, Sparse]:
    _, write_final, _ = compute_write_case(a, b)
    initial = add_grains(
        write_final,
        ((site, 3) for site in MEMORY_CELLS),
    )
    record, final, odometer = audit_transition(
        initial,
        f"clock_all_eight_after_a{a}_b{b}",
    )
    target = a * b
    output_counts = [odometer.get(site, 0) for site in MEMORY_CELLS]
    if target == 0:
        if odometer:
            raise AssertionError(
                f"clock ({a},{b}): false input was not globally silent"
            )
    else:
        if output_counts != [1] * len(MEMORY_CELLS):
            raise AssertionError(
                "clock (1,1): not every memory cell toppled exactly once"
            )
        if sum(odometer.values()) != 66:
            raise AssertionError(
                "clock (1,1): total incremental activity changed"
            )

    record.update(
        {
            "write_input_a_b": [a, b],
            "clock_addition_per_memory_cell": 3,
            "clocked_memory_cells": [list(site) for site in MEMORY_CELLS],
            "clock_output_odometers": output_counts,
            "target_AND": target,
            "global_false_silence": target == 0,
        }
    )
    checks = dict(record["checks"])
    checks["clock_false_cases_have_no_topplings_anywhere"] = (
        target == 0
    )
    checks["clock_true_case_topples_all_eight_outputs_once"] = (
        target == 1
    )
    record["checks"] = checks
    return record, final, odometer


def compute_individual_clock_case(
    a: int,
    b: int,
    memory_index: int,
) -> tuple[dict[str, object], Sparse, Sparse]:
    if not 0 <= memory_index < len(MEMORY_CELLS):
        raise IndexError("memory index out of range")
    site = MEMORY_CELLS[memory_index]
    _, write_final, _ = compute_write_case(a, b)
    initial = add_grains(write_final, ((site, 3),))
    record, final, odometer = audit_transition(
        initial,
        f"clock_memory_{memory_index}_after_a{a}_b{b}",
    )
    target = a * b
    if target == 0 and odometer:
        raise AssertionError(
            f"individual clock ({a},{b},{memory_index}) was not silent"
        )
    if target == 1 and odometer.get(site, 0) != 1:
        raise AssertionError(
            f"individual clock true output {memory_index} was not one"
        )
    record.update(
        {
            "write_input_a_b": [a, b],
            "memory_index": memory_index,
            "clocked_site": list(site),
            "clock_addition": 3,
            "clocked_site_odometer": odometer.get(site, 0),
            "target_AND": target,
            "global_false_silence": target == 0,
        }
    )
    checks = dict(record["checks"])
    checks["individual_clock_semantics"] = True
    record["checks"] = checks
    return record, final, odometer


def compute_fuse_write_case(
    a: int,
    b: int,
    length: int,
) -> tuple[dict[str, object], Sparse, Sparse]:
    if a not in (0, 1) or b not in (0, 1):
        raise ValueError("fuse theorem uses the Boolean input alphabet")
    rays = fuse_rays(length)
    fuse_sites = tuple(site for ray in rays for site in ray)
    background = {
        site: height
        for site, height in zip(CORE_SITES, CORE, strict=True)
        if height
    }
    background.update(fuse_background(length))
    initial = add_grains(
        background,
        ((A, PACKET * a), (B, PACKET * b)),
    )
    record, final, odometer = audit_transition(
        initial,
        f"fuse_write_L{length}_a{a}_b{b}",
    )
    target = a * b
    tap_counts = [odometer.get(tap, 0) for tap in AND_TAPS]
    memory_heights = [final.get(site, 0) for site in MEMORY_CELLS]
    memory_odometers = [odometer.get(site, 0) for site in MEMORY_CELLS]
    fuse_heights = [final.get(site, 0) for site in fuse_sites]
    fuse_odometers = [odometer.get(site, 0) for site in fuse_sites]
    if tap_counts != [target, target]:
        raise AssertionError(
            f"fuse write L={length}, ({a},{b}): exact taps failed"
        )
    if memory_heights != [target] * len(MEMORY_CELLS):
        raise AssertionError(
            f"fuse write L={length}, ({a},{b}): memory failed"
        )
    if any(memory_odometers):
        raise AssertionError(
            f"fuse write L={length}, ({a},{b}): port toppled"
        )
    if fuse_heights != [3] * len(fuse_sites):
        raise AssertionError(
            f"fuse write L={length}, ({a},{b}): fuse precharge changed"
        )
    if any(fuse_odometers):
        raise AssertionError(
            f"fuse write L={length}, ({a},{b}): fuse cell toppled"
        )

    record.update(
        {
            "a": a,
            "b": b,
            "fuse_length": length,
            "fuse_cell_count": len(fuse_sites),
            "fuse_terminal_sites": [
                list(ray[-1]) for ray in rays if ray
            ],
            "and_tap_counts_left_right": tap_counts,
            "memory_cell_final_heights": memory_heights,
            "memory_cell_write_odometers": memory_odometers,
            "all_fuse_cells_remain_height_three": True,
            "all_fuse_cell_write_odometers_zero": True,
        }
    )
    checks = dict(record["checks"])
    checks["Boolean_AND_write_unchanged_by_fuses"] = True
    checks["all_fuse_cells_quiescent_during_write"] = True
    record["checks"] = checks
    return record, final, odometer


def compute_fuse_clock_case(
    a: int,
    b: int,
    length: int,
) -> tuple[dict[str, object], Sparse, Sparse]:
    write_record, write_final, _ = compute_fuse_write_case(
        a,
        b,
        length,
    )
    del write_record
    rays = fuse_rays(length)
    fuse_sites = tuple(site for ray in rays for site in ray)
    initial = add_grains(
        write_final,
        ((site, 3) for site in MEMORY_CELLS),
    )
    record, final, odometer = audit_transition(
        initial,
        f"fuse_clock_L{length}_a{a}_b{b}",
    )
    target = a * b
    port_counts = [odometer.get(site, 0) for site in MEMORY_CELLS]
    fuse_counts = [odometer.get(site, 0) for site in fuse_sites]
    terminal_counts = [
        odometer.get(ray[-1], 0) for ray in rays if ray
    ]
    if target == 0:
        if odometer:
            raise AssertionError(
                f"fuse clock L={length}, ({a},{b}) was not silent"
            )
    else:
        if port_counts != [1] * len(MEMORY_CELLS):
            raise AssertionError(
                f"fuse clock L={length}: not every port toppled once"
            )
        if fuse_counts != [1] * len(fuse_sites):
            raise AssertionError(
                f"fuse clock L={length}: not every fuse cell toppled once"
            )
        if max(odometer.values(), default=0) != 1:
            raise AssertionError(
                f"fuse clock L={length}: some site toppled twice"
            )
        expected_activity = 66 + 8 * length
        if sum(odometer.values()) != expected_activity:
            raise AssertionError(
                f"fuse clock L={length}: activity is not "
                f"{expected_activity}"
            )

    record.update(
        {
            "write_input_a_b": [a, b],
            "fuse_length": length,
            "fuse_cell_count": len(fuse_sites),
            "clock_addition_per_memory_cell": 3,
            "clock_output_port_odometers": port_counts,
            "fuse_terminal_odometers": terminal_counts,
            "all_fuse_cell_odometers_equal_target_AND": (
                fuse_counts == [target] * len(fuse_sites)
            ),
            "target_AND": target,
            "global_false_silence": target == 0,
        }
    )
    checks = dict(record["checks"])
    checks["false_fuse_clocks_globally_silent"] = target == 0
    checks["true_fuse_ports_and_cells_topple_exactly_once"] = (
        target == 1
    )
    record["checks"] = checks
    return record, final, odometer


def compute_precharged_fuse_case(
    a: int,
    b: int,
    length: int,
) -> tuple[dict[str, object], Sparse, Sparse]:
    """One-stabilization AND with height-3 ports and outward fuse rays."""
    if a not in (0, 1) or b not in (0, 1):
        raise ValueError(
            "precharged fuse theorem uses the Boolean input alphabet"
        )
    rays = fuse_rays(length)
    fuse_sites = tuple(site for ray in rays for site in ray)
    background = {
        site: height
        for site, height in zip(CORE_SITES, CORE, strict=True)
        if height
    }
    background.update({site: 3 for site in MEMORY_CELLS})
    background.update(fuse_background(length))
    initial = add_grains(
        background,
        ((A, PACKET * a), (B, PACKET * b)),
    )
    record, final, odometer = audit_transition(
        initial,
        f"precharged_fuse_L{length}_a{a}_b{b}",
    )
    target = a * b
    port_counts = [odometer.get(site, 0) for site in MEMORY_CELLS]
    fuse_counts = [odometer.get(site, 0) for site in fuse_sites]
    output_sites = [
        ray[-1] if ray else port
        for port, ray in zip(MEMORY_CELLS, rays, strict=True)
    ]
    output_counts = [odometer.get(site, 0) for site in output_sites]
    if port_counts != [target] * len(MEMORY_CELLS):
        raise AssertionError(
            f"precharged L={length}, ({a},{b}): port AND failed"
        )
    if fuse_counts != [target] * len(fuse_sites):
        raise AssertionError(
            f"precharged L={length}, ({a},{b}): fuse AND failed"
        )
    if output_counts != [target] * len(output_sites):
        raise AssertionError(
            f"precharged L={length}, ({a},{b}): terminal AND failed"
        )

    port_final_heights = [
        final.get(site, 0) for site in MEMORY_CELLS
    ]
    if target == 0:
        if port_final_heights != [3] * len(MEMORY_CELLS):
            raise AssertionError(
                f"precharged L={length}: false port precharge changed"
            )
        if [final.get(site, 0) for site in fuse_sites] != (
            [3] * len(fuse_sites)
        ):
            raise AssertionError(
                f"precharged L={length}: false fuse precharge changed"
            )
    else:
        expected_port_height = 2 if length == 0 else 3
        if port_final_heights != (
            [expected_port_height] * len(MEMORY_CELLS)
        ):
            raise AssertionError(
                f"precharged L={length}: true final port height changed"
            )
        for ray in rays:
            expected_ray_heights = (
                [1] * (len(ray) - 1) + [0] if ray else []
            )
            if [final.get(site, 0) for site in ray] != (
                expected_ray_heights
            ):
                raise AssertionError(
                    f"precharged L={length}: ray final state changed"
                )
        expected_activity = 422 + 8 * length
        if sum(odometer.values()) != expected_activity:
            raise AssertionError(
                f"precharged L={length}: activity is not "
                f"{expected_activity}"
            )
        if max(odometer.values(), default=0) != 43:
            raise AssertionError(
                f"precharged L={length}: maximum site count changed"
            )

    record.update(
        {
            "a": a,
            "b": b,
            "fuse_length": length,
            "precharged_port_height": 3,
            "precharged_fuse_height": 3,
            "fuse_cell_count": len(fuse_sites),
            "output_terminal_sites": [list(site) for site in output_sites],
            "memory_port_odometers": port_counts,
            "output_terminal_odometers": output_counts,
            "all_fuse_cell_odometers_equal_target_AND": (
                fuse_counts == [target] * len(fuse_sites)
            ),
            "memory_port_final_heights": port_final_heights,
            "target_AND": target,
            "one_stabilization_no_external_clock": True,
        }
    )
    checks = dict(record["checks"])
    checks["precharged_ports_emit_AND"] = True
    checks["all_outward_fuse_cells_transmit_AND_once"] = True
    record["checks"] = checks
    return record, final, odometer


def compute_bound_case(
    core: tuple[int, int, int, int],
    a: int,
    b: int,
    label: str,
) -> dict[str, object]:
    initial = initial_state(core, PACKET, a, b)
    record, _, _ = audit_transition(initial, label)
    record.update(
        {
            "core_row_major_A_B_D_C": list(core),
            "a": a,
            "b": b,
            "additions_at_A_B": [PACKET * a, PACKET * b],
        }
    )
    return record


def compare_records(
    observed: Iterable[dict[str, object]],
    recorded: Iterable[dict[str, object]],
    label: str,
) -> None:
    observed_list = list(observed)
    recorded_list = list(recorded)
    if observed_list == recorded_list:
        return
    for index, (left, right) in enumerate(
        zip(observed_list, recorded_list)
    ):
        if left != right:
            raise AssertionError(
                f"{label} record {index} disagrees:\n"
                f"observed={left}\nrecorded={right}"
            )
    raise AssertionError(
        f"{label} record count differs: "
        f"{len(observed_list)} != {len(recorded_list)}"
    )


def check_bound_record(
    record: Mapping[str, object],
    expected: Mapping[str, object],
) -> None:
    odometer_support = record["odometer_support"]
    final_support = record["final_support"]
    if not isinstance(odometer_support, Mapping):
        raise AssertionError("odometer support record has wrong type")
    if not isinstance(final_support, Mapping):
        raise AssertionError("final support record has wrong type")
    observed = {
        "total_unit_topplings": record["total_unit_topplings"],
        "maximum_site_topplings": record["maximum_site_topplings"],
        "odometer_sites": odometer_support["sites"],
        "odometer_box": odometer_support[
            "bounding_box_row_min_row_max_col_min_col_max"
        ],
        "odometer_linf_radius": odometer_support[
            "linf_radius_from_origin"
        ],
        "final_box": final_support[
            "bounding_box_row_min_row_max_col_min_col_max"
        ],
    }
    if observed != dict(expected):
        raise AssertionError(
            f"{record['label']}: support bound changed: {observed}"
        )


def main() -> None:
    certificate = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    encoding = certificate["encoding"]
    if tuple(encoding["core_row_major_A_B_D_C"]) != CORE:
        raise AssertionError("certificate core changed")
    if encoding["packet_size"] != PACKET:
        raise AssertionError("certificate packet changed")
    if tuple(map(tuple, encoding["and_taps"])) != AND_TAPS:
        raise AssertionError("certificate AND taps changed")
    if tuple(map(tuple, encoding["memory_cells"])) != MEMORY_CELLS:
        raise AssertionError("certificate memory cells changed")

    write_cases = [
        compute_write_case(a, b)[0]
        for a in range(4)
        for b in range(4)
    ]
    compare_records(write_cases, certificate["write_cases"], "write")

    left_table = [
        [
            write_cases[4 * a + b]["and_tap_counts_left_right"][0]
            for b in range(4)
        ]
        for a in range(4)
    ]
    right_table = [
        [
            write_cases[4 * a + b]["and_tap_counts_left_right"][1]
            for b in range(4)
        ]
        for a in range(4)
    ]
    if left_table != [list(row) for row in EXPECTED_LEFT_TABLE]:
        raise AssertionError("left full-alphabet table changed")
    if right_table != [list(row) for row in EXPECTED_RIGHT_TABLE]:
        raise AssertionError("right full-alphabet table changed")
    if left_table != certificate["left_and_tap_table_rows_a_columns_b"]:
        raise AssertionError("recorded left table disagrees")
    if right_table != certificate["right_and_tap_table_rows_a_columns_b"]:
        raise AssertionError("recorded right table disagrees")
    for a in range(4):
        for b in range(4):
            if left_table[a][b] != right_table[b][a]:
                raise AssertionError("reflection symmetry failed")

    boolean_inputs = tuple(
        (a, b) for a in range(2) for b in range(2)
    )
    clock_cases = [
        compute_simultaneous_clock_case(a, b)[0]
        for a, b in boolean_inputs
    ]
    true_clock = clock_cases[-1]
    true_clock_support = true_clock["odometer_support"]
    if not isinstance(true_clock_support, Mapping):
        raise AssertionError("true clock support record has wrong type")
    if (
        true_clock["total_unit_topplings"] != 66
        or true_clock["maximum_site_topplings"] != 1
        or true_clock_support["sites"] != 66
        or true_clock_support[
            "bounding_box_row_min_row_max_col_min_col_max"
        ] != [-4, 4, -4, 5]
    ):
        raise AssertionError("simultaneous true-clock support changed")
    compare_records(
        clock_cases,
        certificate["simultaneous_eight_output_clock_cases"],
        "simultaneous clock",
    )

    individual_clock_cases = [
        compute_individual_clock_case(a, b, index)[0]
        for a, b in boolean_inputs
        for index in range(len(MEMORY_CELLS))
    ]
    compare_records(
        individual_clock_cases,
        certificate["individual_output_clock_cases"],
        "individual clock",
    )

    fuse_write_cases = [
        compute_fuse_write_case(a, b, length)[0]
        for length in CERTIFIED_FUSE_LENGTHS
        for a, b in boolean_inputs
    ]
    compare_records(
        fuse_write_cases,
        certificate["fuse_write_cases"],
        "fuse write",
    )
    fuse_clock_cases = [
        compute_fuse_clock_case(a, b, length)[0]
        for length in CERTIFIED_FUSE_LENGTHS
        for a, b in boolean_inputs
    ]
    compare_records(
        fuse_clock_cases,
        certificate["fuse_clock_cases"],
        "fuse clock",
    )

    precharged_fuse_cases = [
        compute_precharged_fuse_case(a, b, length)[0]
        for length in CERTIFIED_PRECHARGED_FUSE_LENGTHS
        for a, b in boolean_inputs
    ]
    compare_records(
        precharged_fuse_cases,
        certificate["precharged_fuse_AND_cases"],
        "precharged fuse",
    )

    observed_bounds = [
        compute_bound_case(
            CORE,
            3,
            3,
            "witness_maximum_full_alphabet_input",
        ),
        compute_bound_case(
            (3, 3, 3, 3),
            3,
            3,
            "all_three_core_class_dominator_at_p71",
        ),
    ]
    check_bound_record(observed_bounds[0], EXPECTED_WITNESS_MAXIMUM)
    check_bound_record(observed_bounds[1], EXPECTED_CLASS_DOMINATOR)
    compare_records(
        observed_bounds,
        certificate["support_bound_cases"],
        "support bound",
    )

    print("PASS: 16/16 full-alphabet sparse Z^2 write stabilizations")
    print("PASS: both remote tap parities equal parity-AND")
    print("PASS: 4/4 Boolean writes store AND in eight quiescent cells")
    print("PASS: three false simultaneous clocks are globally silent")
    print("PASS: the true simultaneous clock emits once at all 8 cells")
    print("PASS: all 32 individual-output clock checks")
    print(
        "PASS: outward fuse rays at L=1,2,8,32,100 "
        "are write-quiescent and clock-exact"
    )
    print(
        "PASS: one-stabilization precharged fuse AND at "
        "L=0,1,2,8,32,100,500"
    )
    print("PASS: legality, stability, Laplacian, mass, hashes, and bounds")


if __name__ == "__main__":
    main()
