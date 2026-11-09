import io
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4 
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from .letterhead import NumberedCanvas, docx_letterhead, pdf_letterhead, sign_line
from .report_style import _row_flags, docx_charts, docx_table, pdf_charts, pdf_table
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HEADINGS = [
    "SOROTI DISTRICT LOCAL GOVERNMENT",
    "PRODUCTION DEPARTMENT",
    "MONTHLY PROGRESS REPORT",
]
SIGNATURES = ["Prepared by", "Reviewed by", "Approved by"]


def build_tables(data):
    s = data["summary"]
    return [
        {
            "title": "Summary",
            "header": ["Indicator", "Total"],
            "rows": [
                ["Approved activities", s["activities"]],
                ["Men reached", s["men"]],
                ["Women reached", s["women"]],
                ["Total people reached", s["reached"]],
                ["Youth", s["youth"]],
                ["Persons with disability", s["pwd"]],
            ],
        },
        {
            "title": "By department",
            "header": ["Department", "Activities", "People reached"],
            "rows": [
                [r["name"], r["activities"], r["reached"]]
                for r in data["by_department"]
            ],
        },
        {
            "title": "By sub-county",
            "header": ["Sub-county", "Activities", "People reached"],
            "rows": [
                [r["name"], r["activities"], r["reached"]]
                for r in data["by_sub_county"]
            ],
        },
        {
            "title": "By activity type",
            "header": ["Activity type", "Activities", "People reached"],
            "rows": [
                [r["name"], r["activities"], r["reached"]] for r in data["by_type"]
            ],
        },
        {
            "title": "Activities implemented",
            "header": ["Date", "Time", "Activity", "Department", "Officer", "Location", "Reached"],
            "weights": [0.12, 0.13, 0.19, 0.11, 0.14, 0.18, 0.13],
            "rows": [
                [
                    a["date"],
                    a.get("time", "-"),
                    a["type"],
                    a["department"],
                    a["officer"],
                    a["location"],
                    a["reached"],
                ]
                for a in data["activities"]
            ],
        },
    ]


def _docx_photos(doc, photos):
    doc.add_heading("Photographic evidence", level=2)
    table = doc.add_table(rows=0, cols=2)
    for i in range(0, len(photos), 2):
        row = table.add_row()
        _row_flags(row)
        cells = row.cells
        for j, ph in enumerate(photos[i : i + 2]):
            para = cells[j].paragraphs[0]
            try:
                para.add_run().add_picture(ph["path"], width=Inches(3.0))
            except Exception:
                para.add_run("[photo unavailable]")
            caption = cells[j].add_paragraph(ph["caption"])
            for run in caption.runs:
                run.font.size = Pt(8)


def make_docx(data, tables):
    doc = Document()
    docx_letterhead(doc, data)
    doc.add_paragraph("Reporting period: " + data["period"])
    if data["filters"]:
        doc.add_paragraph(data["filters"])
    main = [t for t in tables if not t.get("annex")]
    annex = [t for t in tables if t.get("annex")]
    for t in main:
        if t["title"] == "Activities implemented":
            docx_charts(doc, data)
        doc.add_heading(t["title"], level=2)
        if not t["rows"]:
            doc.add_paragraph("No records.")
            continue
        docx_table(doc, t)
    if data.get("photos"):
        _docx_photos(doc, data["photos"])
    doc.add_paragraph()
    for n, label in enumerate(SIGNATURES):
        p = doc.add_paragraph(sign_line(label, data, False))
        p.paragraph_format.keep_with_next = n < len(SIGNATURES) - 1
        p.paragraph_format.keep_together = True
    if annex:
        doc.add_page_break()
        doc.add_heading("Annex: Registers and measured results", level=1)
        for t in annex:
            doc.add_heading(t["title"], level=2)
            docx_table(doc, t)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _pdf_photos(story, photos, styles, cell, width):
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Photographic evidence</b>", styles["Heading3"]))
    col = width / 2.0
    max_w = col - 12
    blocks = []
    for ph in photos:
        try:
            w, h = ImageReader(ph["path"]).getSize()
            scale = min(max_w / w, 190.0 / h)
            img = Image(ph["path"], width=w * scale, height=h * scale)
        except Exception:
            img = Paragraph("[photo unavailable]", cell)
        blocks.append([img, Paragraph(escape(ph["caption"]), cell)])
    rows = []
    for i in range(0, len(blocks), 2):
        pair = blocks[i : i + 2]
        if len(pair) == 1:
            pair.append("")
        rows.append(pair)
    tbl = Table(rows, colWidths=[col, col])
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(tbl)


def make_pdf(data, tables):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=28, bottomMargin=58
    )
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10)
    h3 = ParagraphStyle("h3k", parent=styles["Heading3"], keepWithNext=1)
    width = A4[0] - 72
    story = list(pdf_letterhead(data, width))
    story.append(
        Paragraph("Reporting period: " + escape(data["period"]), styles["Normal"])
    )
    if data["filters"]:
        story.append(Paragraph(escape(data["filters"]), styles["Normal"]))
    main = [t for t in tables if not t.get("annex")]
    annex = [t for t in tables if t.get("annex")]

    def add_table(t):
        story.append(Spacer(1, 12))
        story.append(Paragraph("<b>%s</b>" % escape(t["title"]), h3))
        if not t["rows"]:
            story.append(Paragraph("No records.", styles["Normal"]))
            return
        story.append(pdf_table(t, cell, width))

    for t in main:
        if t["title"] == "Activities implemented":
            story.append(Spacer(1, 12))
            story.extend(pdf_charts(data, width, h3))
        add_table(t)
    if data.get("photos"):
        _pdf_photos(story, data["photos"], styles, cell, width)
    sign = [Spacer(1, 24)]
    for label in SIGNATURES:
        sign.append(Paragraph(sign_line(label, data, True), styles["Normal"]))
        sign.append(Spacer(1, 14))
    story.append(KeepTogether(sign))
    if annex:
        story.append(PageBreak())
        story.append(Paragraph("<b>Annex: Registers and measured results</b>", styles["Heading2"]))
        for t in annex:
            add_table(t)
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()
