import io
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .exports import HEADINGS, SIGNATURES, _docx_photos, _pdf_photos
from .letterhead import NumberedCanvas, docx_letterhead, pdf_letterhead, sign_line
from .pack import _docx_table, _pdf_table

PLAN = [
    ("Introduction", "introduction", []),
    ("Executive summary", "executive_summary", []),
    ("Activities implemented", "activities_text", ["activities"]),
    ("Performance against targets", "targets_text", ["targets"]),
    ("Achievements by department", "achievements_text", ["by_department"]),
    ("Field coverage", "coverage_text", ["by_sub_county"]),
    ("Registers and measured results", "register_text", ["registers", "measured"]),
    ("Statistical tables", None, ["summary", "by_type", "breakdown"]),
    ("Challenges", "challenges", []),
    ("Actions taken", "actions_taken", []),
    ("Recommendations", "recommendations", []),
    ("PHOTOS", "photos", []),
    ("Conclusion", "conclusion", []),
]


def _paragraphs(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _blocks(data, tables, sections):
    out = []
    number = 0
    for title, key, table_keys in PLAN:
        if key == "photos":
            if data.get("photos"):
                out.append(("PHOTOS", "", []))
            continue
        text = (sections.get(key) or "").strip() if key else ""
        tabs = []
        for k in table_keys:
            value = tables.get(k)
            if not value:
                continue
            for t in value if isinstance(value, list) else [value]:
                if t["rows"]:
                    tabs.append(t)
        if not text and not tabs:
            continue
        number += 1
        out.append(("%d. %s" % (number, title), text, tabs))
    return out


def make_narrative_docx(data, tables, sections):
    doc = Document()
    docx_letterhead(doc, data)
    doc.add_paragraph("Reporting period: " + data["period"])
    if data["filters"]:
        doc.add_paragraph(data["filters"])
    for title, text, tabs in _blocks(data, tables, sections):
        if title == "PHOTOS":
            _docx_photos(doc, data["photos"])
            continue
        doc.add_heading(title, level=2)
        for para in _paragraphs(text):
            doc.add_paragraph(para)
        for t in tabs:
            p = doc.add_paragraph()
            p.add_run(t["title"]).bold = True
            _docx_table(doc, t)
    doc.add_paragraph()
    for label in SIGNATURES:
        doc.add_paragraph(sign_line(label, data, False))
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_narrative_pdf(data, tables, sections):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=28, bottomMargin=58
    )
    styles = getSampleStyleSheet()
    center = ParagraphStyle(
        "center", parent=styles["Normal"], alignment=1, fontSize=12, leading=15
    )
    body = ParagraphStyle(
        "body", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=4
    )
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10)
    width = A4[0] - 72
    story = list(pdf_letterhead(data, width))
    story.append(Paragraph("Reporting period: " + escape(data["period"]), body))
    if data["filters"]:
        story.append(Paragraph(escape(data["filters"]), body))
    for title, text, tabs in _blocks(data, tables, sections):
        if title == "PHOTOS":
            _pdf_photos(story, data["photos"], styles, cell, width)
            continue
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>%s</b>" % escape(title), styles["Heading2"]))
        for para in _paragraphs(text):
            story.append(Paragraph(escape(para), body))
        for t in tabs:
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>%s</b>" % escape(t["title"]), styles["Heading4"]))
            story.append(_pdf_table(t, cell, width))
    story.append(Spacer(1, 24))
    for label in SIGNATURES:
        story.append(
            Paragraph(sign_line(label, data, True), styles["Normal"])
        )
        story.append(Spacer(1, 14))
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()
