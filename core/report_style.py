"""Shared table and chart styling for downloaded reports (PDF and Word)."""
import re
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import KeepTogether, Paragraph, Table, TableStyle 

GREEN = "#1f5c3a"
HEAD_BG = "#e6ece6"
ZEBRA = "#f4f8f4"
_NUM = re.compile(r"^-?\d[\d,]*(\.\d+)?%?$")


def numeric_cols(t):
    """Columns (after the first) that hold only numbers, percentages or dashes."""
    cols = set()
    for i in range(1, len(t["header"])):
        vals = [str(r[i]).strip() for r in t["rows"] if i < len(r)]
        if vals and all(v in ("-", "") or _NUM.match(v) for v in vals) and any(_NUM.match(v) for v in vals):
            cols.add(i)
    return cols


# ------------------------------------------------------------------ PDF
def pdf_table(t, cell, width):
    count = len(t["header"])
    weights = t.get("weights") or [1.0 / count] * count
    right = ParagraphStyle("cellr", parent=cell, alignment=2)
    nums = numeric_cols(t)

    def para(text, i, bold=False):
        txt = escape(str(text))
        if bold:
            txt = "<b>%s</b>" % txt
        return Paragraph(txt, right if i in nums else cell)

    rows = [[para(h, i, True) for i, h in enumerate(t["header"])]]
    for r in t["rows"]:
        rows.append([para(v, i) for i, v in enumerate(r)])
    tbl = Table(rows, colWidths=[width * w for w in weights], repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b9c4b9")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(HEAD_BG)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(ZEBRA)]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return tbl


def chart_sets(data):
    sets = []
    sub = [(r["name"], r["activities"]) for r in data.get("by_sub_county") or []]
    kinds = sorted(
        [(r["name"], r["activities"]) for r in data.get("by_type") or []],
        key=lambda kv: (-kv[1], kv[0]),
    )
    if sub:
        sets.append(("Activities by sub-county", sub[:10]))
    if kinds:
        sets.append(("Activities by activity type", kinds[:8]))
    return sets


def _short(text, n=42):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def pdf_charts(data, width, heading_style):
    out = []
    for title, rows in chart_sets(data):
        label_w = width * 0.40
        bar_max = width * 0.48
        row_h = 15
        height = row_h * len(rows) + 6
        d = Drawing(width, height)
        top = max(v for _, v in rows) or 1
        for i, (name, value) in enumerate(rows):
            y = height - (i + 1) * row_h
            d.add(String(label_w - 6, y + 3, _short(name), fontName="Helvetica", fontSize=8, textAnchor="end"))
            length = max(2, bar_max * value / top) if value else 0
            if length:
                d.add(Rect(label_w, y + 1, length, row_h - 5, fillColor=colors.HexColor(GREEN), strokeColor=None))
            d.add(String(label_w + length + 4, y + 3, str(value), fontName="Helvetica-Bold", fontSize=8))
        out.append(KeepTogether([Paragraph("<b>%s</b>" % escape(title), heading_style), d]))
    return out


# ----------------------------------------------------------------- Word
def _shade(cell, hex_fill):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill.lstrip("#"))
    tcpr.append(shd)


def _row_flags(row, header=False):
    from docx.oxml import OxmlElement

    trpr = row._tr.get_or_add_trPr()
    trpr.append(OxmlElement("w:cantSplit"))
    if header:
        trpr.append(OxmlElement("w:tblHeader"))


def docx_table(doc, t):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    table = doc.add_table(rows=1, cols=len(t["header"]))
    table.style = "Table Grid"
    nums = numeric_cols(t)

    def fill(cell, text, i, bold=False):
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(str(text))
        run.font.size = Pt(9)
        run.bold = bold
        if i in nums:
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    for i, h in enumerate(t["header"]):
        cell = table.rows[0].cells[i]
        fill(cell, h, i, True)
        _shade(cell, HEAD_BG)
    _row_flags(table.rows[0], header=True)
    for n, row in enumerate(t["rows"]):
        r = table.add_row()
        _row_flags(r)
        for i, value in enumerate(row):
            fill(r.cells[i], value, i)
            if n % 2 == 1:
                _shade(r.cells[i], ZEBRA)
    return table


def docx_charts(doc, data):
    from docx.shared import Inches, Pt, RGBColor

    for title, rows in chart_sets(data):
        doc.add_heading(title, level=2)
        top = max(v for _, v in rows) or 1
        table = doc.add_table(rows=0, cols=3)
        table.autofit = False
        for name, value in rows:
            cells = table.add_row().cells
            for c, w in zip(cells, (Inches(2.4), Inches(3.4), Inches(0.6))):
                c.width = w
            cells[0].text = ""
            r0 = cells[0].paragraphs[0].add_run(_short(name))
            r0.font.size = Pt(9)
            n = max(1, round(20 * value / top)) if value else 0
            cells[1].text = ""
            r1 = cells[1].paragraphs[0].add_run("█" * n)
            r1.font.size = Pt(9)
            r1.font.color.rgb = RGBColor.from_string(GREEN.lstrip("#"))
            cells[2].text = ""
            r2 = cells[2].paragraphs[0].add_run(str(value))
            r2.font.size = Pt(9)
            r2.bold = True
        for col, w in zip(table.columns, (Inches(2.4), Inches(3.4), Inches(0.6))):
            col.width = w
