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
from reportlab.platypus import (
    Image,
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
        cells = table.add_row().cells
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
    for t in tables:
        doc.add_heading(t["title"], level=2)
        if not t["rows"]:
            doc.add_paragraph("No records.")
            continue
        table = doc.add_table(rows=1, cols=len(t["header"]))
        table.style = "Table Grid"
        for i, h in enumerate(t["header"]):
            cell = table.rows[0].cells[i]
            cell.text = h
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
        for row in t["rows"]:
            cells = table.add_row().cells
            for i, value in enumerate(row):
                cells[i].text = str(value)
    if data.get("photos"):
        _docx_photos(doc, data["photos"])
    doc.add_paragraph()
    for label in SIGNATURES:
        doc.add_paragraph(sign_line(label, data, False))
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
    center = ParagraphStyle(
        "center", parent=styles["Normal"], alignment=1, fontSize=12, leading=15
    )
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10)
    width = A4[0] - 72
    story = list(pdf_letterhead(data, width))
    story.append(
        Paragraph("Reporting period: " + escape(data["period"]), styles["Normal"])
    )
    if data["filters"]:
        story.append(Paragraph(escape(data["filters"]), styles["Normal"]))
    for t in tables:
        story.append(Spacer(1, 12))
        story.append(Paragraph("<b>%s</b>" % escape(t["title"]), styles["Heading3"]))
        if not t["rows"]:
            story.append(Paragraph("No records.", styles["Normal"]))
            continue
        count = len(t["header"])
        weights = t.get("weights") or [1.0 / count] * count
        rows = [[Paragraph("<b>%s</b>" % escape(str(h)), cell) for h in t["header"]]]
        for r in t["rows"]:
            rows.append([Paragraph(escape(str(v)), cell) for v in r])
        tbl = Table(rows, colWidths=[width * w for w in weights], repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6ece6")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(tbl)
    if data.get("photos"):
        _pdf_photos(story, data["photos"], styles, cell, width)
    story.append(Spacer(1, 24))
    for label in SIGNATURES:
        story.append(
            Paragraph(sign_line(label, data, True), styles["Normal"])
        )
        story.append(Spacer(1, 14))
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()
