import io
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .exports import HEADINGS, SIGNATURES, build_tables
from .letterhead import NumberedCanvas, docx_letterhead, pdf_letterhead
from .report_style import docx_table as _docx_table, pdf_table as _pdf_table


def _section_tables(data):
    return [t for t in build_tables(data) if t["title"] != "By sub-county"] + data.get("register_tables", [])


def make_pack_pdf(title, period_label, sections, empty):
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
    story = list(pdf_letterhead({"title": title}, width))
    story.append(Paragraph("Reporting period: " + escape(period_label), styles["Normal"]))
    for i, (heading, data) in enumerate(sections):
        if i:
            story.append(PageBreak())
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>%s</b>" % escape(heading), styles["Heading2"]))
        for t in _section_tables(data):
            story.append(Spacer(1, 8))
            story.append(Paragraph("<b>%s</b>" % escape(t["title"]), styles["Heading3"]))
            if not t["rows"]:
                story.append(Paragraph("No records.", styles["Normal"]))
                continue
            story.append(_pdf_table(t, cell, width))
    if empty:
        story.append(Spacer(1, 14))
        story.append(
            Paragraph(
                "No approved activities in this period: " + escape(", ".join(empty)),
                styles["Normal"],
            )
        )
    story.append(Spacer(1, 24))
    for label in SIGNATURES:
        story.append(
            Paragraph(
                "%s: ______________________ &nbsp;&nbsp; Date: ____________" % label,
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 14))
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


def make_pack_docx(title, period_label, sections, empty):
    doc = Document()
    docx_letterhead(doc, {"title": title})
    doc.add_paragraph("Reporting period: " + period_label)
    for i, (heading, data) in enumerate(sections):
        if i:
            doc.add_page_break()
        doc.add_heading(heading, level=1)
        for t in _section_tables(data):
            doc.add_heading(t["title"], level=2)
            if not t["rows"]:
                doc.add_paragraph("No records.")
                continue
            _docx_table(doc, t)
    if empty:
        doc.add_paragraph()
        doc.add_paragraph("No approved activities in this period: " + ", ".join(empty))
    doc.add_paragraph()
    for label in SIGNATURES:
        doc.add_paragraph("%s: ______________________    Date: ____________" % label)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
