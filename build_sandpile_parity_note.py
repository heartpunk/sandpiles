#!/usr/bin/env python3
"""Build the public-facing sandpile crossed-identity research note."""

from __future__ import annotations

import hashlib
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from pypdf import PdfWriter


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output" / "pdf" / "four_terminal_odometer_parity_identity.pdf"
RAW_OUTPUT = ROOT / "tmp" / "pdfs" / "four_terminal_odometer_parity_identity.raw.pdf"

ATTACHMENTS = [
    "packet925_full_alphabet_certificate.json",
    "verify_packet925_full_alphabet_certificate.py",
    "audit_full_alphabet_925_witness.py",
    "audit_full_alphabet_925.cpp",
    "sandpile_2x2_full_alphabet_fast.cpp",
    "sandpile_2x2_full_alphabet_sparse_exhaustive.cpp",
    "scan_full_alphabet_0022.cpp",
    "audit_full_alphabet_extended_hits.cpp",
    "sandpile_exact_linear_no_propagation.md",
    "sandpile_packet_composition_audit.md",
    "sandpile_0022_packet_family_100k_audit.md",
    "build_sandpile_parity_note.py",
]

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("DV", FONT_DIR / "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DV-Bold", FONT_DIR / "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVM", FONT_DIR / "DejaVuSansMono.ttf"))
pdfmetrics.registerFont(TTFont("DVM-Bold", FONT_DIR / "DejaVuSansMono-Bold.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-Bold")

INK = HexColor("#172033")
MUTED = HexColor("#5B6472")
TEAL = HexColor("#087F8C")
TEAL_DARK = HexColor("#075E68")
TEAL_PALE = HexColor("#EAF6F7")
GOLD = HexColor("#D69522")
GOLD_PALE = HexColor("#FFF5DF")
BLUE_PALE = HexColor("#EEF3FA")
LINE = HexColor("#D9DEE7")
PAPER = HexColor("#FCFCFA")
WHITE = colors.white


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="NoteTitle",
        fontName="DV-Bold",
        fontSize=26,
        leading=31,
        textColor=INK,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="NoteSubtitle",
        fontName="DV",
        fontSize=11.5,
        leading=16.5,
        textColor=MUTED,
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        name="Byline",
        fontName="DV-Bold",
        fontSize=9.5,
        leading=13,
        textColor=TEAL_DARK,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="Version",
        fontName="DV",
        fontSize=8,
        leading=11,
        textColor=MUTED,
    )
)
styles.add(
    ParagraphStyle(
        name="AbstractLabel",
        fontName="DV-Bold",
        fontSize=8.5,
        leading=11,
        textColor=TEAL_DARK,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="Abstract",
        fontName="DV",
        fontSize=9.3,
        leading=13.5,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="H1",
        fontName="DV-Bold",
        fontSize=16,
        leading=20,
        textColor=INK,
        spaceBefore=11,
        spaceAfter=8,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        name="H2",
        fontName="DV-Bold",
        fontSize=11.5,
        leading=15,
        textColor=TEAL_DARK,
        spaceBefore=9,
        spaceAfter=5,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        name="Body",
        fontName="DV",
        fontSize=9.15,
        leading=13.2,
        textColor=INK,
        alignment=TA_LEFT,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        name="Small",
        fontName="DV",
        fontSize=7.7,
        leading=10.7,
        textColor=MUTED,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="Caption",
        fontName="DV",
        fontSize=7.6,
        leading=10.2,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="Equation",
        fontName="DV",
        fontSize=10.4,
        leading=15,
        textColor=INK,
        alignment=TA_CENTER,
        spaceBefore=3,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="TheoremTitle",
        fontName="DV-Bold",
        fontSize=9.4,
        leading=12.5,
        textColor=TEAL_DARK,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="TheoremBody",
        fontName="DV",
        fontSize=8.65,
        leading=12.4,
        textColor=INK,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="NoteCode",
        fontName="DVM",
        fontSize=7.2,
        leading=9.5,
        textColor=INK,
        leftIndent=6,
        rightIndent=6,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="Reference",
        fontName="DV",
        fontSize=7.6,
        leading=10.6,
        textColor=INK,
        leftIndent=13,
        firstLineIndent=-13,
        spaceAfter=5,
    )
)


def P(text: str, style: str = "Body") -> Paragraph:
    return Paragraph(text, styles[style])


def heading(number: str, title: str) -> Paragraph:
    return P(f'<font color="{TEAL.hexval()}">{number}</font>&nbsp;&nbsp;{title}', "H1")


def theorem_box(title: str, body: list[str], tint=TEAL_PALE) -> Table:
    flows: list[Flowable] = [P(title, "TheoremTitle")]
    for paragraph in body:
        flows.append(P(paragraph, "TheoremBody"))
    box = Table([[flows]], colWidths=[166 * mm], hAlign="LEFT")
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), tint),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LINEBEFORE", (0, 0), (0, -1), 3, TEAL),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return box


class CrossingDiagram(Flowable):
    def __init__(self, width: float = 160 * mm, height: float = 58 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, avail_width, avail_height):
        return min(self.width, avail_width), self.height

    @staticmethod
    def _arrow(canvas, x1, y1, x2, y2, color, width=3.2, halo=False):
        if halo:
            canvas.setStrokeColor(WHITE)
            canvas.setLineWidth(width + 3.6)
            canvas.line(x1, y1, x2, y2)
        canvas.setStrokeColor(color)
        canvas.setFillColor(color)
        canvas.setLineWidth(width)
        canvas.line(x1, y1, x2, y2)
        dx, dy = x2 - x1, y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        size = 7
        canvas.drawPath(
            _triangle_path(
                canvas,
                (x2, y2),
                (x2 - size * ux + 3.7 * px, y2 - size * uy + 3.7 * py),
                (x2 - size * ux - 3.7 * px, y2 - size * uy - 3.7 * py),
            ),
            fill=1,
            stroke=0,
        )

    def draw(self):
        c = self.canv
        w = min(self.width, self._availWidth if hasattr(self, "_availWidth") else self.width)
        cx = w / 2
        cell = 27 * mm
        x0 = cx - cell
        y0 = 6 * mm
        coords = {
            "A": (x0, y0 + cell),
            "B": (x0 + cell, y0 + cell),
            "D": (x0, y0),
            "C": (x0 + cell, y0),
        }
        fills = {"A": BLUE_PALE, "B": GOLD_PALE, "D": GOLD_PALE, "C": BLUE_PALE}
        values = {"A": "0", "B": "0", "D": "2", "C": "2"}
        for label, (x, y) in coords.items():
            c.setFillColor(fills[label])
            c.setStrokeColor(LINE)
            c.setLineWidth(1)
            c.roundRect(x, y, cell, cell, 3 * mm, fill=1, stroke=1)
            c.setFillColor(INK)
            c.setFont("DV-Bold", 12)
            c.drawCentredString(x + cell / 2, y + cell * 0.70, label)
            c.setFillColor(MUTED)
            c.setFont("DV", 8)
            c.drawCentredString(x + cell / 2, y + cell * 0.13, f"height {values[label]}")
        a = (coords["A"][0] + cell * 0.72, coords["A"][1] + cell * 0.36)
        cpt = (coords["C"][0] + cell * 0.28, coords["C"][1] + cell * 0.64)
        b = (coords["B"][0] + cell * 0.28, coords["B"][1] + cell * 0.36)
        d = (coords["D"][0] + cell * 0.72, coords["D"][1] + cell * 0.64)
        self._arrow(c, *a, *cpt, TEAL, width=3.4)
        self._arrow(c, *b, *d, GOLD, width=3.4, halo=True)
        c.setFont("DV-Bold", 8.2)
        c.setFillColor(TEAL_DARK)
        c.drawRightString(x0 - 5 * mm, y0 + cell * 1.56, "input 925a")
        c.setFillColor(GOLD)
        c.drawString(x0 + 2 * cell + 5 * mm, y0 + cell * 1.56, "input 925b")
        c.setFillColor(TEAL_DARK)
        c.drawString(x0 + 2 * cell + 5 * mm, y0 + cell * 0.35, "read u(C) mod 2")
        c.setFillColor(GOLD)
        c.drawRightString(x0 - 5 * mm, y0 + cell * 0.35, "read u(D) mod 2")


def _triangle_path(canvas, p1, p2, p3):
    path = canvas.beginPath()
    path.moveTo(*p1)
    path.lineTo(*p2)
    path.lineTo(*p3)
    path.close()
    return path


class HitBarcode(Flowable):
    def __init__(self, hits: list[int], width=166 * mm, height=28 * mm):
        super().__init__()
        self.hits = hits
        self.width = width
        self.height = height

    def wrap(self, avail_width, avail_height):
        return min(self.width, avail_width), self.height

    def draw(self):
        c = self.canv
        w = self.width
        left = 7 * mm
        right = w - 7 * mm
        y = 11 * mm
        c.setStrokeColor(LINE)
        c.setLineWidth(1.2)
        c.line(left, y, right, y)
        for value in (0, 25_000, 50_000, 75_000, 100_000):
            x = left + (right - left) * value / 100_000
            c.setStrokeColor(LINE)
            c.line(x, y - 2.5 * mm, x, y + 2.5 * mm)
            c.setFont("DV", 6.5)
            c.setFillColor(MUTED)
            label = f"{value // 1000}k" if value else "0"
            c.drawCentredString(x, y - 6 * mm, label)
        for index, value in enumerate(self.hits):
            x = left + (right - left) * value / 100_000
            c.setStrokeColor(TEAL if index < 6 else GOLD)
            c.setLineWidth(2)
            c.line(x, y - 1.4 * mm, x, y + 6.4 * mm)
            c.setFillColor(TEAL if index < 6 else GOLD)
            c.circle(x, y + 6.4 * mm, 1.5, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont("DV", 6.5)
        c.drawRightString(right, y + 10 * mm, "11 exact packet hits")


def table_style(header_bg=INK, header_fg=WHITE, font_size=7.3):
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("TEXTCOLOR", (0, 0), (-1, 0), header_fg),
            ("FONTNAME", (0, 0), (-1, 0), "DV-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "DV"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("LEADING", (0, 0), (-1, -1), font_size + 3),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HexColor("#F7F8FA")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def first_page(canvas, doc):
    canvas.saveState()
    canvas.setTitle("A Four-Terminal Odometer-Parity Identity in the Planar Abelian Sandpile")
    canvas.setAuthor("OpenAI Codex")
    canvas.setSubject("Exact witness, scoped minimality computation, and exact-linear no-propagation theorem")
    canvas.setKeywords("Abelian sandpile, odometer, parity, crossed identity, computational complexity")
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, A4[1] - 5 * mm, A4[0], 5 * mm, fill=1, stroke=0)
    canvas.restoreState()


def later_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, A4[1] - 14 * mm, A4[0] - doc.rightMargin, A4[1] - 14 * mm)
    canvas.setFont("DV", 6.8)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, A4[1] - 10.7 * mm, "FOUR-TERMINAL ODOMETER-PARITY IDENTITY")
    canvas.drawRightString(A4[0] - doc.rightMargin, 9.5 * mm, str(doc.page))
    canvas.restoreState()


def build_story() -> list[Flowable]:
    story: list[Flowable] = []

    story.extend(
        [
            Spacer(1, 11 * mm),
            P("A Four-Terminal<br/>Odometer-Parity Identity", "NoteTitle"),
            P(
                "An exact crossed terminal map in the ordinary two-dimensional "
                "Abelian sandpile, with a scoped minimality computation and an "
                "exact-linear no-propagation theorem",
                "NoteSubtitle",
            ),
            Spacer(1, 2 * mm),
            P("Technical research and manuscript: OpenAI Codex", "Byline"),
            P(
                "Broad prompt, interest filtering, encouragement, and publication "
                "stewardship: Sophie<br/>Version 0.2 · 23 July 2026",
                "Version",
            ),
            Spacer(1, 11 * mm),
            CrossingDiagram(),
            P(
                "<b>Figure 1.</b> The four-cell seed. The logical pairings A-C and "
                "B-D cross in cyclic port order A,B,C,D. The cells show initial "
                "heights; all other lattice cells start at zero.",
                "Caption",
            ),
            Spacer(1, 5 * mm),
        ]
    )
    abstract = [
        P("ABSTRACT", "AbstractLabel"),
        P(
            "We exhibit an exact one-shot crossed identity in the ordinary "
            "conservative Abelian sandpile on the infinite square lattice. From "
            "the stable seed [[0,0],[2,2]], add 925a and 925b grains at the two "
            "top cells, where a,b are in {0,1,2,3}. After stabilization, the "
            "parities of the odometer at the diagonally opposite bottom cells "
            "are exactly (a mod 2,b mod 2) for all sixteen inputs. Exhaustion of "
            "all 256 stable 2 x 2 seeds and equal packet sizes p <= 925 proves "
            "that this is the unique first witness in that explicit class. We "
            "also prove that a full-odometer exactly linear four-symbol response "
            "cannot propagate away from a single-site source on Z<super>2</super>; "
            "the positive witness necessarily escapes through nonlinear internal "
            "dynamics. The construction is a local odometer observable, not yet "
            "a composable crossing gate. Exact certificates, independent "
            "implementations, and the bounded composition audit are described.",
            "Abstract",
        ),
    ]
    abstract_box = Table([[abstract]], colWidths=[166 * mm])
    abstract_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(abstract_box)
    story.append(Spacer(1, 5 * mm))
    story.append(
        Table(
            [
                [
                    P(
                        "<b>Contribution statement.</b> OpenAI Codex produced "
                        "the construction, searches, proofs, code, verification, "
                        "literature framing, and manuscript. Sophie had not "
                        "encountered this sandpile problem before this session. "
                        "She supplied the broad challenge, interest feedback, "
                        "encouragement, and decision to publish; she did not "
                        "derive or independently verify the technical results. "
                        "Hosting under heartpunk denotes publication stewardship, "
                        "not technical authorship. This is an unreviewed "
                        "AI-produced preprint. The note is released under "
                        "CC0-1.0; accompanying code is also available under MIT.",
                        "Small",
                    )
                ]
            ],
            colWidths=[166 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F4F5F7")),
                    ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            ),
        )
    )
    story.append(PageBreak())

    story.extend(
        [
            heading("1", "Why a different signal encoding matters"),
            P(
                "The Abelian sandpile is a canonical example of complex global "
                "behavior generated by a local deterministic rule [1,2]. Its "
                "prediction problem is P-complete in dimension at least three, "
                "while the complexity of the ordinary two-dimensional model has "
                "remained open [3,5]. Standard hardness reductions encode "
                "circuits as chains of topplings. In two dimensions, those chains "
                "cannot generally cross.",
            ),
            P(
                "Gajardo and Goles proved a no-crossing result when a bit is "
                "encoded by the presence or absence of an avalanche [4]. Their "
                "gate notion uses one-grain inputs at non-corner boundary ports "
                "and requires independent transport to opposite sides. Later work "
                "stresses that this restriction leaves unconventional signal "
                "encodings open [6], while obtaining crossings after changing "
                "the neighborhood, weights, or uniformity assumptions [6,7].",
            ),
            P(
                "This note studies the parity of the <i>odometer</i> - the number "
                "of times a selected cell topples. Prior work has used total "
                "toppling parity and vertex-resolved toppling counts [9,10], and "
                "periodic particle-count responses are natural in general Abelian "
                "processors [8]. The result here is deliberately narrow: a "
                "specific crossed local readout, not a classical crossing gate "
                "and not a proof of P-completeness.",
            ),
            heading("2", "Model and definition"),
            P(
                "Work on the infinite square lattice Z<super>2</super> with the "
                "four von Neumann neighbors. A configuration η assigns a "
                "nonnegative integer height to each cell. A cell of height at "
                "least four may topple, losing four grains and sending one grain "
                "to each neighbor. We consider finite initial mass, for which "
                "stabilization terminates. The final stable state and the number "
                "of topplings at every cell are independent of legal toppling "
                "order [2].",
            ),
            P(
                "Write u(x) for this order-independent toppling count and call u "
                "the odometer. With the positive graph Laplacian",
            ),
            P("(Lu)(x) = 4u(x) - Σ<sub>y~x</sub> u(y),", "Equation"),
            P(
                "an initial stable background η and added mass m satisfy "
                "η<sub>final</sub> = η + m - Lu.",
            ),
            theorem_box(
                "Definition 2.1 - Full-alphabet crossed odometer-parity identity",
                [
                    "Choose four ports A,B,C,D in cyclic order and a positive "
                    "packet size p. For a,b in {0,1,2,3}, add ap grains at A and "
                    "bp grains at B. The module realizes a full-alphabet "
                    "crossed odometer-parity identity when",
                    "<para align='center'><b>(u(C) mod 2, u(D) mod 2) = "
                    "(a mod 2, b mod 2)</b></para>",
                    "for all sixteen inputs. In cyclic terminal order A,B,C,D, "
                    "the pairings A-C and B-D cross. This describes the terminal "
                    "map; it does not assert independently composable wires.",
                ],
            ),
            heading("3", "The exact four-cell witness"),
            P(
                "Set A=(0,0), B=(0,1), D=(1,0), C=(1,1), with stable background "
                "heights η(A)=η(B)=0 and η(C)=η(D)=2; put zero everywhere else. "
                "The witness uses packet size p=925.",
            ),
            theorem_box(
                "Theorem 3.1 - Exact 925-packet crossed identity",
                [
                    "For every a,b in {0,1,2,3}, stabilize after adding 925a "
                    "grains at A and 925b grains at B. Then",
                    "<para align='center'><b>(u(C),u(D)) ≡ (a,b) (mod 2).</b></para>",
                ],
            ),
            Spacer(1, 3 * mm),
        ]
    )

    exact_data = [
        ["a \\ b", "0", "1", "2", "3"],
        ["0", "(0, 0)", "(300, 237)", "(698, 572)", "(1130, 941)"],
        ["1", "(237, 300)", "(625, 625)", "(1073, 1010)", "(1531, 1405)"],
        ["2", "(572, 698)", "(1010, 1073)", "(1456, 1456)", "(1946, 1883)"],
        ["3", "(941, 1130)", "(1405, 1531)", "(1883, 1946)", "(2371, 2371)"],
    ]
    exact_table = Table(
        exact_data,
        colWidths=[18 * mm, 33 * mm, 36 * mm, 39 * mm, 40 * mm],
        repeatRows=1,
    )
    exact_table.setStyle(table_style(font_size=7.15))
    story.extend(
        [
            KeepTogether(
                [
                    exact_table,
                    P(
                        "<b>Table 1.</b> Exact output counts (u(C),u(D)); rows are a and "
                        "columns are b. Reducing each ordered pair modulo two gives "
                        "(a mod 2,b mod 2).",
                        "Caption",
                    ),
                ]
            ),
            P(
                "The behavior is not secretly linear. For example, with b=0 the "
                "C-output is 237 at a=1 but 572 at a=2, rather than 474. The full "
                "odometer changes nonlinearly even though the two selected "
                "parities obey a linear two-bit law.",
            ),
            P(
                "At the largest input a=b=3, the exact stabilization contains "
                "568,110 unit topplings, 2,434 toppled cells, and L-infinity "
                "toppling radius 27 about A=(0,0) (graph-distance radius 40). "
                "Thus the observable is produced by a spatially extended "
                "avalanche, despite the four-cell seed.",
            ),
            heading("4", "Scoped minimality and exact verification"),
            theorem_box(
                "Theorem 4.1 - Unique first witness in the fixed 2 x 2 class",
                [
                    "Consider every one of the 4<super>4</super>=256 stable "
                    "backgrounds supported on the designated 2 x 2 core, zero "
                    "background outside it, the fixed ports A,B,C,D above, one "
                    "equal positive integer packet p, the full input alphabet "
                    "{0,1,2,3}, and parity readout at C,D. No witness exists for "
                    "1 <= p <= 924. At p=925 exactly one witness exists: "
                    "[[0,0],[2,2]].",
                ],
            ),
            P(
                "This is a finite exhaustive theorem about the stated encoding "
                "class, not a claim of minimality among arbitrary larger "
                "backgrounds, unequal packets, other ports, or other readouts.",
            ),
            P(
                "Two exhaustive C++ implementations independently check all "
                "236,800 core-packet pairs through p=925. One uses a dense "
                "generation-stamped array and legal quotient topplings; the "
                "other uses a separate case ordering and exact unit topplings. "
                "The latter finds 12,634 Boolean candidates and 77 candidates "
                "surviving the axis/equal tests through p=924, but zero full hits.",
            ),
            P(
                "Finite arrays are justified by domination. The all-three core "
                "with 2,775 grains at each input dominates every searched case. "
                "Its independently computed toppling bounds are rows [-27,27] "
                "and columns [-26,27], leaving exactly 100 unused lattice layers "
                "between the support and the boundary of the 257 x 257 search "
                "array.",
            ),
            P(
                "A third verifier, "
                "<font name='DVM'>audit_full_alphabet_925_witness.py</font>, "
                "operates sparsely on signed Z<super>2</super>. "
                "For all sixteen witness cases it checks legal expansion of every "
                "batched step, final stability, mass conservation, the Laplacian "
                "identity at every affected cell, and hashes of the complete "
                "final state and odometer. The canonical aggregate SHA-256 is:",
            ),
            Table(
                [[P("23b19081729d9303e5acaae0565a5dbce<br/>2296fbd5cb360bdab94f47f279b92ff", "NoteCode")]],
                colWidths=[166 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), BLUE_PALE),
                        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                ),
            ),
            heading("5", "An exact-linear no-propagation theorem"),
            P(
                "The most obvious route to a reusable four-symbol wire would make "
                "the odometer scale exactly with the input amplitude. The next "
                "result rules out that route on the ordinary lattice.",
            ),
            P(
                "Let m be a finitely supported nonnegative pulse, let u be a "
                "finitely supported nonnegative integer odometer candidate, and "
                "set r=m-Lu. Suppose one stable background η remains stable under "
                "η+ar for a=0,1,2,3. Since both η(x) and η(x)+3r(x) lie in an "
                "interval of width three, |r(x)| <= 1 at every cell.",
            ),
            theorem_box(
                "Theorem 5.1 - Unit-residual bounding box",
                [
                    "Let S=supp(m). If |m-Lu| <= 1 pointwise, then supp(u) is "
                    "contained in the smallest axis-aligned bounding box of S.",
                ],
            ),
            P("<b>Proof.</b> Put U=supp(u). At any x outside U,"),
            P("(m-Lu)(x) = m(x) + Σ<sub>y~x</sub> u(y).", "Equation"),
            P(
                "The unit bound implies two boundary facts: every cell of U "
                "touching the outside has value one, and no outside cell touches "
                "two cells of U. Choose the rightmost cell A in the topmost "
                "occupied row of U. Its north and east neighbors are outside, so "
                "u(A)=1. Any occupied west neighbor is a boundary cell of value "
                "one. Any occupied south neighbor must also be a boundary cell "
                "of value one; otherwise the outside east neighbor of A would "
                "touch both A and the southeast cell. Therefore",
            ),
            P("(Lu)(A) >= 4 - 1 - 1 = 2.", "Equation"),
            P(
                "If A were not a source, then m(A)=0 and |m(A)-Lu(A)|>=2, "
                "contradicting the unit bound. Hence the top-right extremal cell "
                "of U is a source. Reflections and exchange of coordinates give "
                "all four bounding-box inequalities. □",
            ),
            theorem_box(
                "Corollary 5.2 - Single-source exact-linear responses are local",
                [
                    "For m=pδ<sub>s</sub>, the unit-residual condition implies "
                    "either u=0 and p=1, or u=δ<sub>s</sub> and "
                    "p in {3,4,5}. In particular, a nonzero exact-linear response "
                    "cannot reach even a nearest neighbor of its source.",
                ],
                tint=GOLD_PALE,
            ),
            P(
                "<b>Proof.</b> Theorem 5.1 confines u to the singleton source, so "
                "u=kδ<sub>s</sub>. At a neighbor of s the residual equals k, hence "
                "k is 0 or 1. If k=0, the residual at s forces p=1. If k=1, the "
                "residual at s is p-4, forcing p in {3,4,5}. □",
            ),
            P(
                "If a two-input module had exact odometers "
                "w<sub>a,b</sub>=au+bv for all a,b in {0,1,2,3}, restricting to "
                "one axis at a time would confine u and v to their respective "
                "input cells. Therefore no exactly linear full-alphabet carrier, "
                "and hence no exactly linear crossed identity, can propagate on "
                "ordinary Z<super>2</super>. The 925-packet witness avoids the "
                "theorem precisely because its internal odometer is nonlinear.",
            ),
            heading("6", "A sparse packet family, not a one-off"),
            P(
                "For the fixed seed [[0,0],[2,2]], an exact scan of every packet "
                "1 <= p <= 100,000 finds eleven full-alphabet hits:",
            ),
            P(
                "<b>925, 14,509, 17,993, 25,929, 27,889, 45,016, 50,958, "
                "63,430, 67,004, 76,725, 77,458.</b>",
                "Equation",
            ),
            HitBarcode(
                [925, 14509, 17993, 25929, 27889, 45016, 50958, 63430, 67004, 76725, 77458]
            ),
            P(
                "<b>Figure 2.</b> Exact packet hits through 100,000. The apparent "
                "irregularity is descriptive only; the finite scan does not prove "
                "aperiodicity or any asymptotic density.",
                "Caption",
            ),
            P(
                "All eleven observed packets are composite, but 45,016 and several "
                "later hits are even, so oddness and the initial 1 mod 4 pattern "
                "are not necessary. The gcd of the ten successive gaps is one, "
                "so the hits are not confined to a single residue class modulo "
                "any m>1; they also do not form a constant-gap progression. No "
                "prime packet appears through 100,000; no theorem excludes one "
                "later.",
            ),
            P(
                "Reflection symmetry reduces the sixteen cases to five exact "
                "incremental trajectories: the A-only, equal-input, 1:2, 1:3, and "
                "2:3 rays. Abelianness makes each accumulated trajectory exactly "
                "equivalent to one-shot stabilization. Through 100,000, 224 "
                "packets survive the axis/equal conditions and eleven survive all "
                "cases. Every hit was separately replayed from scratch.",
            ),
            heading("7", "Composition status: the exact boundary"),
            theorem_box(
                "What has and has not been established",
                [
                    "<b>Established:</b> an exact full-alphabet crossed identity "
                    "as a local odometer observable; unique first witness in the "
                    "stated 2 x 2 class; a global theorem excluding exact-linear "
                    "propagation.",
                    "<b>Not established:</b> packet re-encoding, reset, physical "
                    "cascadability, a standard crossing gate, or P-completeness of "
                    "ordinary two-dimensional sandpile prediction.",
                ],
                tint=GOLD_PALE,
            ),
            P(
                "The output counts in Table 1 are measurements inside the same "
                "avalanche, not fresh 925-grain packets. Abstractly injecting "
                "those sixteen counts into a separate 2 x 2 seed [[1,0],[1,1]] "
                "does yield a parity-preserving compressor, reducing the largest "
                "count from 2,371 to 779. Physical attachment is different: "
                "ordinary lattice edges are undirected, so the downstream cells "
                "feed grains back and change the producing avalanche.",
            ),
            P(
                "Bounded exhaustive audits found no physical composition in the "
                "tested families: no suitable tap in all-three 5 x L wires for "
                "4 <= L <= 64, no exact pair in direct symmetric arms for "
                "4 <= L <= 32, and no success among 164 nonoverlapping placements "
                "of two rotated/reflected tiny compressors. These are finite "
                "negative results, not a universal no-composition theorem. They "
                "identify one-way isolation or a feedback-tolerant nonlinear "
                "transducer as the missing primitive.",
            ),
            heading("8", "Reproducibility and epistemic status"),
        ]
    )

    artifact_rows = [
        ["Artifact", "Purpose"],
        ["packet925_full_alphabet_certificate.json", "Compact per-case certificate and hashes"],
        ["verify_packet925_full_alphabet_certificate.py", "Sparse Z² witness verifier"],
        ["audit_full_alphabet_925_witness.py", "Independent witness replay and aggregate hash"],
        ["sandpile_2x2_full_alphabet_fast.cpp", "Dense p <= 925 exhaustive implementation"],
        ["sandpile_2x2_full_alphabet_sparse_exhaustive.cpp", "Sparse p <= 925 exhaustive implementation"],
        ["audit_full_alphabet_925.cpp", "Independent p <= 925 minimality audit"],
        ["scan_full_alphabet_0022.cpp", "Exact five-trajectory scan through 100,000"],
        ["audit_full_alphabet_extended_hits.cpp", "From-scratch replay of every family hit"],
        ["sandpile_exact_linear_no_propagation.md", "Full analytic proof"],
        ["sandpile_packet_composition_audit.md", "Bounded composition audit"],
        ["sandpile_0022_packet_family_100k_audit.md", "Detailed 100,000-packet scan audit"],
    ]
    artifact_table = LongTable(artifact_rows, colWidths=[90 * mm, 76 * mm], repeatRows=1)
    artifact_table.setStyle(table_style(font_size=6.75))
    story.extend(
        [
            artifact_table,
            Spacer(1, 3 * mm),
            KeepTogether(
                [
                    P("<b>Quick witness check</b>", "Small"),
                    Table(
                        [
                            [
                                P(
                                    "python3 verify_packet925_full_alphabet_certificate.py"
                                    "<br/>python3 audit_full_alphabet_925_witness.py",
                                    "NoteCode",
                                )
                            ]
                        ],
                        colWidths=[166 * mm],
                        style=TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, -1), BLUE_PALE),
                                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                ("TOPPADDING", (0, 0), (-1, -1), 5),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                            ]
                        ),
                    ),
                    Spacer(1, 3 * mm),
                ]
            ),
            P(
                "Reference witness verification requires only the Python standard "
                "library. The exhaustive programs require a C++20 compiler. The "
                "principal verifier reports: 16/16 sparse infinite-lattice "
                "stabilizations pass; every batch expands to legal unit topplings; "
                "stability, Laplacian reconstruction, mass conservation, parity, "
                "and all recorded hashes agree.",
            ),
            P(
                "All listed files are embedded as PDF attachments. Extract them "
                "with <font name='DVM'>pdfdetach -saveall this-note.pdf</font>; "
                "the embedded README gives exact commands.",
            ),
            P(
                "The finite witness and scoped minimality claims have unusually "
                "strong computational support: distinct state representations, "
                "queue disciplines, case orderings, and sparse versus dense "
                "lattices agree. The bounding-box theorem is analytic and does not "
                "depend on computation. Nevertheless, this document is a preprint, "
                "and its novelty has not been peer reviewed.",
            ),
            P(
                "In a targeted literature search, we found no prior construction "
                "recovering two input parities at oppositely paired output "
                "terminals as parities of local odometer values in the ordinary "
                "two-dimensional von Neumann sandpile, and no matching statement "
                "of the unit-residual bounding-box theorem. That absence is "
                "evidence, not proof of priority. Public circulation should "
                "describe the results as apparently unreported pending expert "
                "literature review.",
            ),
            heading("9", "Discussion"),
            P(
                "The main conceptual result is not that a tiny local gadget "
                "behaves like an ordinary wire. It does not. Rather, a globally "
                "extended nonlinear avalanche can preserve two crossing parity "
                "coordinates exactly across a four-symbol input alphabet. The "
                "observable is simple even though the internal dynamics are not.",
            ),
            P(
                "The positive construction and negative theorem sharply divide "
                "the search space. Any future composable encoding cannot demand "
                "exactly additive odometers across amplitudes. It must exploit "
                "nonlinearity while maintaining a stable quotient observable - "
                "parity here, perhaps another residue or finite-state signature "
                "elsewhere - and it must tolerate or control undirected feedback.",
            ),
            P(
                "That combination makes the result relevant to the long-running "
                "two-dimensional prediction problem without overstating its "
                "consequence. It supplies a concrete alternative encoding, a "
                "minimal exact witness in a transparent class, and a proof that "
                "the obvious linear route is impossible. The next mathematical "
                "question is whether a feedback-tolerant nonlinear transducer can "
                "turn this one-shot observable into a reusable signal.",
            ),
            heading("References", ""),
        ]
    )

    refs = [
        (
            "[1] P. Bak, C. Tang, and K. Wiesenfeld. "
            "<i>Self-organized criticality: An explanation of 1/f noise.</i> "
            "Physical Review Letters 59(4), 381-384 (1987). "
            '<link href="https://doi.org/10.1103/PhysRevLett.59.381" '
            f'color="{TEAL_DARK.hexval()}">doi:10.1103/PhysRevLett.59.381</link>.'
        ),
        (
            "[2] D. Dhar. <i>Self-organized critical state of sandpile automaton "
            "models.</i> Physical Review Letters 64(14), 1613-1616 (1990). "
            '<link href="https://doi.org/10.1103/PhysRevLett.64.1613" '
            f'color="{TEAL_DARK.hexval()}">doi:10.1103/PhysRevLett.64.1613</link>.'
        ),
        (
            "[3] C. Moore and M. Nilsson. <i>The computational complexity of "
            "sandpiles.</i> Journal of Statistical Physics 96, 205-224 (1999). "
            '<link href="https://doi.org/10.1023/A:1004524500416" '
            f'color="{TEAL_DARK.hexval()}">doi:10.1023/A:1004524500416</link>.'
        ),
        (
            "[4] A. Gajardo and E. Goles. <i>Crossing information in "
            "two-dimensional sandpiles.</i> Theoretical Computer Science 369(1-3), "
            "463-469 (2006). "
            '<link href="https://doi.org/10.1016/j.tcs.2006.09.022" '
            f'color="{TEAL_DARK.hexval()}">doi:10.1016/j.tcs.2006.09.022</link>.'
        ),
        (
            "[5] E. Formenti and K. Perrot. <i>How hard is it to predict "
            "sandpiles on lattices? A survey.</i> Fundamenta Informaticae "
            "171(1-4), 189-219 (2020). "
            '<link href="https://doi.org/10.3233/FI-2020-1879" '
            f'color="{TEAL_DARK.hexval()}">doi:10.3233/FI-2020-1879</link>.'
        ),
        (
            "[6] P. Concha-Vega, E. Goles, P. Montealegre, and K. Perrot. "
            "<i>Sandpiles prediction and crossover on Z<super>2</super> within "
            "Moore neighborhood.</i> Natural Computing 24, 29-66 (2025). "
            '<link href="https://doi.org/10.1007/s11047-024-10002-9" '
            f'color="{TEAL_DARK.hexval()}">doi:10.1007/s11047-024-10002-9</link>.'
        ),
        (
            "[7] P. Concha-Vega, A. Loubière, and K. Perrot. "
            "<i>Non-Uniform and Weighted Crossing Gates in Two-Dimensional "
            "Sandpiles.</i> arXiv:2606.26943 (2026). "
            '<link href="https://arxiv.org/abs/2606.26943" '
            f'color="{TEAL_DARK.hexval()}">arXiv:2606.26943</link>.'
        ),
        (
            "[8] A. E. Holroyd, L. Levine, and P. Winkler. "
            "<i>Abelian logic gates.</i> Combinatorics, Probability and Computing "
            "28(3), 388-422 (2019). "
            '<link href="https://doi.org/10.1017/S0963548318000482" '
            f'color="{TEAL_DARK.hexval()}">doi:10.1017/S0963548318000482</link>.'
        ),
        (
            "[9] D. Dhar. <i>Extended operator algebra for Abelian sandpile "
            "models.</i> Physica A 224(1-2), 162-168 (1996). "
            '<link href="https://doi.org/10.1016/0378-4371(95)00320-7" '
            f'color="{TEAL_DARK.hexval()}">doi:10.1016/0378-4371(95)00320-7</link>.'
        ),
        (
            "[10] D. Austin, M. Chambers, R. Funke, L. D. García Puente, and "
            "L. Keough. <i>The multivariate avalanche polynomial.</i> "
            "Australasian Journal of Combinatorics 72(2), 421-445 (2018). "
            '<link href="https://arxiv.org/abs/1605.02713" '
            f'color="{TEAL_DARK.hexval()}">arXiv:1605.02713</link>.'
        ),
    ]
    for ref in refs:
        story.append(P(ref, "Reference"))
    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    RAW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(RAW_OUTPUT),
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=20 * mm,
        bottomMargin=17 * mm,
        title="A Four-Terminal Odometer-Parity Identity",
        author="OpenAI Codex",
        subject="Exact ordinary two-dimensional Abelian sandpile result",
    )
    doc.build(build_story(), onFirstPage=first_page, onLaterPages=later_page)

    writer = PdfWriter(clone_from=RAW_OUTPUT)
    readme = (
        "Embedded reproducibility bundle for "
        "'A Four-Terminal Odometer-Parity Identity'.\n\n"
        "Quick witness check:\n"
        "  python3 verify_packet925_full_alphabet_certificate.py\n\n"
        "Independent replay and aggregate hash:\n"
        "  python3 audit_full_alphabet_925_witness.py\n\n"
        "Scoped minimality audit (C++20):\n"
        "  c++ -O3 -std=c++20 audit_full_alphabet_925.cpp -o audit925\n"
        "  ./audit925 --maximum-pulse 925\n\n"
        "Full packet-family scan:\n"
        "  c++ -O3 -std=c++20 -pthread scan_full_alphabet_0022.cpp -o scan100k\n"
        "  ./scan100k --maximum-pulse 100000\n\n"
        "Replay all eleven hits from scratch:\n"
        "  c++ -O3 -std=c++20 audit_full_alphabet_extended_hits.cpp -o replay_hits\n"
        "  ./replay_hits 925 14509 17993 25929 27889 45016 50958 63430 "
        "67004 76725 77458\n\n"
        "The remaining files document the analytic no-propagation theorem and "
        "bounded composition audit. The two sandpile_2x2_full_alphabet source "
        "files provide independent dense and sparse exhaustive implementations.\n"
    )
    writer.add_attachment("README_EMBEDDED_ARTIFACTS.txt", readme)
    for relative_path in ATTACHMENTS:
        path = ROOT / relative_path
        writer.add_attachment(path.name, path.read_bytes())
    with OUTPUT.open("wb") as handle:
        writer.write(handle)

    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(f"wrote {OUTPUT}")
    print(f"sha256 {digest}")


if __name__ == "__main__":
    main()
