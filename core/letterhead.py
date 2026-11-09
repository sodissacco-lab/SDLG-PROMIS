"""Official letterhead and footer for every downloaded report (PDF and Word).

Matches the district's Quarterly Report paper: coat of arms on the left, the
centred contact block, the district emblem with flag bars on the right.
Edit the constants below if a phone number or address changes."""
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle

STATIC = Path(__file__).resolve().parent / "static" / "core"
ARMS = STATIC / "letterhead_arms.png"
EMBLEM = STATIC / "letterhead_district.jpeg"

DISTRICT = "SOROTI DISTRICT LOCAL GOVERNMENT"
DEFAULT_SECTOR = "PRODUCTION DEPARTMENT"
EMAIL_1 = "sorotidlg@gmail.com"
EMAIL_2 = "sorotidlg.admin@soroti.go.ug"
WEBSITE = "www.soroti.go.ug"
PLOT = "Plot No. 6-8 Kennedy square"
SACAO_TEL = "SACAO: +256(0)772 279288"
AFO_TEL = "AFO: +256(0)782024799"
POBOX = "P.O Box 61, Soroti."
BLUE = "#0563C1"
GREEN = "#1f5c3a"


def sector_line(department=None, sub_county=None):
    """Second heading line, e.g. 'ASURET FISHERIES SECTOR'."""
    dept = str(department.name).upper() if department else ""
    sub = str(sub_county.name).upper() if sub_county else ""
    if dept and sub:
        return "%s %s SECTOR" % (sub, dept)
    if sub:
        return "%s SUB-COUNTY SECTOR" % sub
    if dept:
        return "%s DEPARTMENT" % dept
    return DEFAULT_SECTOR


def _ordinal(n):
    if 10 <= n % 100 <= 20:
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def date_text(d=None):
    d = d or date.today()
    return "%s %s, %d" % (_ordinal(d.day), d.strftime("%B"), d.year)


# ------------------------------------------------------------------ PDF
def _fit(path, width):
    w, h = ImageReader(str(path)).getSize()
    return Image(str(path), width=width, height=width * h / w)


def pdf_letterhead(data, width):
    """List of flowables for the top of the first page."""
    f = "Times-Bold"
    mid = ParagraphStyle("lh", fontName=f, fontSize=10, leading=11.5, alignment=TA_CENTER)
    cap = ParagraphStyle("cap", fontName=f, fontSize=6.5, leading=8, alignment=TA_CENTER)
    link = ' color="%s"' % BLUE
    centre = [
        Paragraph(escape(DISTRICT), mid),
        Paragraph(escape(data.get("sector_line") or DEFAULT_SECTOR), mid),
        Paragraph('Email: &nbsp;<link href="mailto:%s"%s><u>%s</u></link>' % (EMAIL_1, link, EMAIL_1), mid),
        Paragraph('<link href="mailto:%s"%s><u>%s</u></link>' % (EMAIL_2, link, EMAIL_2), mid),
        Paragraph('Website: <link href="http://%s"%s><u>%s</u></link>' % (WEBSITE, link, WEBSITE), mid),
        Paragraph(escape(PLOT), mid),
        Paragraph(escape(SACAO_TEL), mid),
        Paragraph(escape(AFO_TEL), mid),
    ]
    side, mid_w = 1.3 * inch, 3.7 * inch
    left, right = [], []
    if ARMS.exists():
        arms = _fit(ARMS, 1.1 * inch)
        arms.hAlign = "RIGHT"
        cap.alignment = TA_RIGHT
        left = [arms, Paragraph("THE REPUBLIC OF UGANDA", cap)]
    if EMBLEM.exists():
        emb = _fit(EMBLEM, 1.0 * inch)
        emb.hAlign = "LEFT"
        right = [emb]
    tbl = Table([[left, centre, right]], colWidths=[side, mid_w, side])
    tbl.hAlign = "CENTER"
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    pobox = ParagraphStyle("po", fontName=f, fontSize=10, leading=13, alignment=TA_LEFT)
    when = ParagraphStyle("dt", fontName="Times-Roman", fontSize=11, leading=14, alignment=TA_RIGHT)
    title = ParagraphStyle("tt", fontName=f, fontSize=11, leading=14, alignment=TA_CENTER)
    out = [tbl, Spacer(1, 6), Paragraph(escape(POBOX), pobox), Spacer(1, 4),
           Paragraph(escape(date_text()), when), Spacer(1, 10)]
    if data.get("title"):
        out += [Paragraph(escape(str(data["title"]).upper()), title), Spacer(1, 10)]
    return out


class NumberedCanvas(rl_canvas.Canvas):
    """Draws the footer with 'Page X of Y' on every page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved = []

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            self._footer(total)
            super().showPage()
        super().save()

    def _footer(self, total):
        w, _ = A4
        left, right = 36, w - 36
        self.setStrokeColor(colors.HexColor(GREEN))
        self.setLineWidth(1.2)
        self.line(left, 44, right, 44)
        self.setLineWidth(0.4)
        self.line(left, 41.5, right, 41.5)
        self.setFillColor(colors.HexColor(GREEN))
        self.setFont("Times-Bold", 8)
        self.drawCentredString(w / 2, 31, "%s  |  %s" % (DISTRICT, "P.O Box 61, Soroti"))
        self.setFillColor(colors.HexColor("#444444"))
        self.setFont("Times-Roman", 7.5)
        self.drawCentredString(w / 2, 21, "%s  |  %s  |  %s" % (EMAIL_1, EMAIL_2, WEBSITE))
        self.setFont("Times-Italic", 7)
        self.drawString(left, 10, "Generated by SDLG-Production MIS on %s" % date_text())
        self.drawRightString(right, 10, "Page %d of %d" % (self._pageNumber, total))


# ----------------------------------------------------------------- Word
def docx_letterhead(doc, data):
    """Letterhead at the top of a python-docx Document, plus footer on every page."""
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor

    def style_run(run, size=10, bold=True, color=None, underline=False, italic=False):
        run.font.name = "Times New Roman"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        run.font.size = Pt(size)
        run.bold = bold
        run.italic = italic
        run.underline = underline
        if color:
            run.font.color.rgb = RGBColor.from_string(color)

    def para(container, text="", align=WD_ALIGN_PARAGRAPH.CENTER, first=False, **kw):
        p = container.paragraphs[0] if first else container.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        if text:
            style_run(p.add_run(text), **kw)
        return p

    def hyperlink(p, url, text, **kw):
        part = p.part
        rid = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
        h = OxmlElement("w:hyperlink")
        h.set(qn("r:id"), rid)
        r = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        rf = OxmlElement("w:rFonts")
        rf.set(qn("w:ascii"), "Times New Roman")
        rf.set(qn("w:hAnsi"), "Times New Roman")
        rpr.append(rf)
        b = OxmlElement("w:b")
        rpr.append(b)
        col = OxmlElement("w:color")
        col.set(qn("w:val"), BLUE.lstrip("#"))
        rpr.append(col)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "20")
        rpr.append(sz)
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rpr.append(u)
        r.append(rpr)
        t = OxmlElement("w:t")
        t.text = text
        r.append(t)
        h.append(r)
        p._p.append(h)

    sec = doc.sections[0]
    sec.top_margin = Inches(0.6)
    sec.bottom_margin = Inches(0.9)
    sec.left_margin = sec.right_margin = Inches(1)
    usable = 6.5

    tbl = doc.add_table(rows=1, cols=3)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    widths = (Inches(1.4), Inches(3.6), Inches(1.3))
    for col, w in zip(tbl.columns, widths):
        col.width = w
    for cell, w in zip(tbl.rows[0].cells, widths):
        cell.width = w
    left, mid, right = tbl.rows[0].cells

    lp = para(left, first=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
    if ARMS.exists():
        lp.add_run().add_picture(str(ARMS), width=Inches(1.1))
    para(left, "THE REPUBLIC OF UGANDA", align=WD_ALIGN_PARAGRAPH.RIGHT, size=5.5)

    para(mid, DISTRICT, first=True)
    para(mid, data.get("sector_line") or DEFAULT_SECTOR)
    p = para(mid)
    style_run(p.add_run("Email:   "))
    hyperlink(p, "mailto:" + EMAIL_1, EMAIL_1)
    p = para(mid)
    hyperlink(p, "mailto:" + EMAIL_2, EMAIL_2)
    p = para(mid)
    style_run(p.add_run("Website: "))
    hyperlink(p, "http://" + WEBSITE, WEBSITE)
    para(mid, PLOT)
    para(mid, SACAO_TEL)
    para(mid, AFO_TEL)

    rp = para(right, first=True, align=WD_ALIGN_PARAGRAPH.LEFT)
    if EMBLEM.exists():
        rp.add_run().add_picture(str(EMBLEM), width=Inches(1.0))

    p = para(doc, POBOX, align=WD_ALIGN_PARAGRAPH.LEFT, size=11)
    p.paragraph_format.space_before = Pt(6)
    p = para(doc, date_text(), align=WD_ALIGN_PARAGRAPH.RIGHT, size=11, bold=False)
    p.paragraph_format.space_before = Pt(6)
    if data.get("title"):
        p = para(doc, str(data["title"]).upper(), size=12)
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(8)

    # ---- footer on every page
    foot = sec.footer
    foot.is_linked_to_previous = False
    fp = foot.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ppr = fp._p.get_or_add_pPr()
    border = OxmlElement("w:pBdr")
    top = OxmlElement("w:top")
    for k, v in (("val", "double"), ("sz", "6"), ("space", "4"), ("color", GREEN.lstrip("#"))):
        top.set(qn("w:" + k), v)
    border.append(top)
    ppr.append(border)
    style_run(fp.add_run("%s  |  P.O Box 61, Soroti" % DISTRICT), size=8, color=GREEN.lstrip("#"))
    f2 = foot.add_paragraph()
    f2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_run(f2.add_run("%s  |  %s  |  %s" % (EMAIL_1, EMAIL_2, WEBSITE)), size=7.5, bold=False, color="444444")
    f3 = foot.add_paragraph()
    f3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_run(f3.add_run("Generated by SDLG-Production MIS on %s  |  Page " % date_text()), size=7, bold=False, italic=True, color="444444")
    def field(par, instr):
        def piece(make):
            run = par.add_run()
            style_run(run, size=7, bold=False, italic=True, color="444444")
            run._r.append(make())
        def ch(typ):
            def make():
                el = OxmlElement("w:fldChar")
                el.set(qn("w:fldCharType"), typ)
                return el
            return make
        def code():
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = " %s " % instr
            return el
        def shown():
            el = OxmlElement("w:t")
            el.text = "1"
            return el
        for make in (ch("begin"), code, ch("separate"), shown, ch("end")):
            piece(make)

    field(f3, "PAGE")
    style_run(f3.add_run(" of "), size=7, bold=False, italic=True, color="444444")
    field(f3, "NUMPAGES")


def sign_line(label, data, html=True):
    """'Prepared by' carries the officer's name; the other lines stay blank to sign."""
    name = (data or {}).get("prepared_by") if label == "Prepared by" else ""
    if not name:
        if html:
            return "%s: ______________________ &nbsp;&nbsp; Date: ____________" % label
        return "%s: ______________________    Date: ____________" % label
    if html:
        return "%s: <u>%s</u> &nbsp;&nbsp; Date: <u>%s</u>" % (label, escape(name), date_text())
    return "%s: %s    Date: %s" % (label, name, date_text())
