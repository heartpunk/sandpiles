#!/usr/bin/env python3
"""Render the exact packet-71 four-input layout as an accessible static SVG.

Run from the repository root:
    python3 research/render_figures.py

The figure is derived from packet71_loads.py, including an independently
replayed true odometer and all sixteen input cases. It uses no raster images,
third-party dependencies, finite boundary, or network resources.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def main() -> None:
    if not __debug__:
        raise SystemExit("Figure checks require assertions: do not use -O or PYTHONOPTIMIZE.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path,
                        default=Path(__file__).with_name("packet71_loads.py"))
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).parent / "figures" / "packet71-composition.svg")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("packet71_loads", args.model)
    assert spec and spec.loader
    model = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = model
    spec.loader.exec_module(model)

    separation, length = 12, 9
    left, right, receiver, output = model.receiver_layout(separation, length)
    decoration = dict.fromkeys(left | right | output, 3)
    decoration[receiver] = 2
    background = model.plus(model.gate(0, 0, (0, -separation)),
                            model.gate(0, 0, (0, separation)), decoration)
    packet_cells = {(0, -12): "a", (0, -11): "b", (0, 12): "c", (0, 13): "d"}
    true_input = model.plus(background, dict.fromkeys(packet_cells, 71))
    final, odometer = model.stabilize(true_input)
    assert sum(odometer.values()) == 867
    assert all(odometer[x] == 1 for x in left | right | {receiver} | output)
    for bits in itertools.product(range(2), repeat=4):
        initial = model.plus(background, {x: 71 * bit for x, bit in zip(packet_cells, bits)})
        h, u = model.stabilize(initial)
        expected = bits[0] * bits[1] * bits[2] * bits[3]
        assert u.get(receiver, 0) == expected
        assert all(u.get(x, 0) == expected for x in output)

    ns = "http://www.w3.org/2000/svg"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}svg", {
        "width": "1280", "height": "1270", "viewBox": "0 0 1280 1270",
        "role": "img", "aria-labelledby": "title description",
    })

    def element(tag: str, attributes: dict | None = None, value: str | None = None):
        node = ET.SubElement(root, f"{{{ns}}}{tag}", {k: str(v) for k, v in (attributes or {}).items()})
        if value is not None:
            node.text = value
        return node

    element("title", {"id": "title"}, "Two packet-71 gates feed one four-input presence AND")
    element("desc", {"id": "description"},
            "Two exact square-lattice panels show the same geometry: source cores at "
            "column offsets minus twelve and plus twelve, six and seven input-wire cells, "
            "a height-two receiver at row one column zero, and nine output cells. "
            "The upper panel labels stable initial grain heights before adding seventy-one "
            "grains at each selected input a, b, c, d. The lower panel labels actual "
            "odometer counts when all four inputs are one. The two source avalanches "
            "contribute eight hundred forty-four unit topplings and the new cells twenty-three. "
            "Every new cell topples once. The truth table says the receiver and output "
            "topple only when both source signals ab and cd are one. Adjacency is undirected: "
            "every toppling sends one grain to each of four lattice neighbors. "
            "The construction is a one-use presence circuit and does not regenerate input packets.")
    element("style", value="""
      text { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #182c3d; }
      .heading { font-size: 30px; font-weight: 700; }
      .panel-title { font-size: 23px; font-weight: 650; }
      .body { font-size: 17px; }
      .small { font-size: 14px; }
      .muted { fill: #506374; }
      .cell { font-size: 12px; font-weight: 600; text-anchor: middle; dominant-baseline: central; }
      .coordinate { font-size: 11px; fill: #607282; text-anchor: middle; }
      .input-letter { font-size: 8px; fill: #ffffff; font-weight: 700; }
    """)

    def rect(x, y, w, h, fill, stroke="none", radius=0):
        return element("rect", {"x": x, "y": y, "width": w, "height": h,
                                "fill": fill, "stroke": stroke, "rx": radius})

    def text(x, y, value, cls="body", **attrs):
        return element("text", {"x": x, "y": y, "class": cls, **attrs}, value)

    def lines(x, y, values, cls="body", step=25):
        for i, value in enumerate(values):
            text(x, y + step * i, value, cls)

    def line(x1, y1, x2, y2, stroke="#d9e0e6", width=1):
        element("line", {"x1": x1, "y1": y1, "x2": x2, "y2": y2,
                         "stroke": stroke, "stroke-width": width})

    colors = {"source": "#627383", "core": "#253e51", "input": "#c5e3fa",
              "receiver": "#ffd292", "output": "#bee8d1"}
    rect(0, 0, 1280, 1270, "#f5f7f9")
    text(42, 51, "Two packet sources. One four-input AND.", "heading")
    text(42, 84, "Exact square-lattice geometry · one stabilization · finite, one-use presence circuit", "body muted")

    plot_x, cell = 61, 24
    rows, columns = range(-5, 12), range(-17, 19)
    core_cells = {(r, c + shift) for shift in (-12, 12) for r in (0, 1) for c in (0, 1)}

    def panel(top, title, subtitle, values, initial):
        rect(28, top, 1224, 517, "#ffffff", "#dfe5eb", 12)
        text(48, top + 35, title, "panel-title")
        text(48, top + 62, subtitle, "small muted")
        grid_y = top + 90
        for r in rows:
            for c in columns:
                x, y = plot_x + (c + 17) * cell, grid_y + (r + 5) * cell
                site = (r, c)
                value = values.get(site, 0)
                fill = "#fafbfd"
                foreground = "#182c3d"
                if value:
                    fill = colors["source"]
                    foreground = "#ffffff"
                    if site in left | right:
                        fill, foreground = colors["input"], "#113e60"
                    elif site == receiver:
                        fill, foreground = colors["receiver"], "#663e00"
                    elif site in output:
                        fill, foreground = colors["output"], "#17472f"
                    elif initial and site in core_cells:
                        fill = colors["core"]
                rect(x, y, cell, cell, fill, "#e5eaf0")
                if value:
                    label = text(x + 12, y + 12, str(value), "cell", style=f"fill:{foreground}")
                    label.append(ET.Element(f"{{{ns}}}title"))
                    label[-1].text = f"Site ({r},{c}): {'initial grains' if initial else 'unit topplings'} {value}"
                if initial and site in packet_cells:
                    text(x + 2, y + 8, packet_cells[site], "input-letter")
        for c in range(-16, 19, 4):
            text(plot_x + (c + 17) * cell + 12, grid_y - 9, str(c), "coordinate")
        for r in (-4, 0, 4, 8):
            text(plot_x - 13, grid_y + (r + 5) * cell + 16, str(r), "coordinate")
        text(plot_x + 410, grid_y + 425, "column c", "coordinate")
        text(plot_x - 19, grid_y - 9, "r", "coordinate")

    panel(111, "1 · Stable material before the input packets",
          "Cell numerals are grain heights. Blank sites start at zero; the marked input cells each receive 71 × their bit.",
          background, True)
    panel(651, "2 · Actual odometer when a = b = c = d = 1",
          "Cell numerals are numbers of legal unit topplings, not grains. Blank sites never topple.",
          odometer, False)

    side = 949
    text(side, 229, "Inputs and material", "body", **{"font-weight": "650"})
    lines(side, 258, ["Left core: add 71a and 71b.", "Right core: add 71c and 71d.",
                      "a, b, c, d are Boolean bits."], "small", 23)
    for y, color, label in [(343, colors["source"], "Precharged source gates"),
                             (378, colors["input"], "Height-three input wires"),
                             (413, colors["receiver"], "Height-two AND receiver"),
                             (448, colors["output"], "Height-three output wire")]:
        rect(side, y - 17, 18, 18, color, "#ced7df", 2)
        text(side + 27, y - 2, label, "small")
    lines(side, 501, ["All edges are undirected.", "Each toppling sends one grain", "to each of four neighbors.",
                      "Return grains are included."], "small muted", 23)

    text(side, 770, "What the signals mean", "body", **{"font-weight": "650"})
    lines(side, 798, ["p = ab       q = cd", "A signal is one toppling."], "small", 23)
    x_positions = [side + 14, side + 58, side + 131, side + 217]
    for x, label in zip(x_positions, ("p", "q", "receiver", "output")):
        text(x, 862, label, "small", **{"text-anchor": "middle", "font-weight": "650"})
    line(side, 873, side + 252, 873)
    for index, (p, q) in enumerate(itertools.product(range(2), repeat=2)):
        y = 899 + index * 33
        if p * q:
            rect(side - 2, y - 22, 258, 31, "#e7f4ed", radius=3)
        for x, value in zip(x_positions, (p, q, p * q, p * q)):
            text(x, y, str(value), "body", **{"text-anchor": "middle"})
    lines(side, 1042, ["True-case activity:", "844 source + 23 new topplings", "= 867 unit topplings."], "small", 23)
    text(side, 1125, "The source counts are unchanged.", "small", **{"font-weight": "600"})

    lines(42, 1206,
          ["The output encodes abcd as avalanche presence. It does not regenerate a 71-grain input packet.",
           "Generated from research/packet71_loads.py: separation 12, output length 9. All 16 input cases are checked."],
          "small muted", 24)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space="  ")
    args.output.write_text(ET.tostring(root, encoding="unicode") + "\n")
    print(f"PASS: {args.output} (exact source-derived layout; true unit topplings 867)")


if __name__ == "__main__":
    main()
