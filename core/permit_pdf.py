import io
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from .permit_models import ANIMAL_OTHER, ANIMAL_SLAUGHTER, ANIMAL_SUB, FISH

W, H = A4
LM, RM = 58, W - 58
T, TB, TI = "Times-Roman", "Times-Bold", "Times-Italic"
VAL = "Helvetica-Bold"

_ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
         "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _below_thousand(n):
    out = []
    if n >= 100:
        out.append(_ONES[n // 100] + " hundred")
        n %= 100
        if n:
            out.append("and")
    if n >= 20:
        out.append(_TENS[n // 10] + ("-" + _ONES[n % 10] if n % 10 else ""))
    elif n > 0:
        out.append(_ONES[n])
    return " ".join(out)


def number_in_words(n):
    n = int(n)
    if n == 0:
        return "zero"
    parts = []
    for value, name in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= value:
            parts.append(_below_thousand(n // value) + " " + name)
            n %= value
    if n:
        parts.append(("and " if parts and n < 100 else "") + _below_thousand(n))
    return " ".join(parts)


def shillings_in_words(n):
    text = number_in_words(n) + " Uganda shillings only"
    return text[0].upper() + text[1:]


def _d(value):
    return value.strftime("%d %B %Y") if value else ""


# ---------------------------------------------------------------- drawing
def _fit(text, maxw, size=10.5):
    text = " ".join(str(text or "").split())
    while size > 7 and stringWidth(text, VAL, size) > maxw:
        size -= 0.5
    if stringWidth(text, VAL, size) > maxw:
        while text and stringWidth(text + "...", VAL, size) > maxw:
            text = text[:-1]
        text += "..."
    return text, size


def _put(c, x, y, text, maxw):
    text, size = _fit(text, max(maxw, 10))
    c.setFont(VAL, size)
    c.drawString(x, y + 1, text)


def line(c, y, label, value="", x=LM, end=RM, size=12):
    c.setFont(T, size)
    c.drawString(x, y, label)
    x0 = x + stringWidth(label, T, size) + 5
    c.setLineWidth(0.4)
    c.line(x0, y - 2, end, y - 2)
    if value:
        _put(c, x0 + 3, y, value, end - x0 - 6)


def pair(c, y, l1, v1, l2, v2, split=0.5, size=12):
    mid = LM + (RM - LM) * split
    line(c, y, l1, v1, x=LM, end=mid - 10, size=size)
    line(c, y, l2, v2, x=mid, end=RM, size=size)


def days_line(c, y, pre, value, post="days", x=LM, size=12, blank=64):
    c.setFont(T, size)
    c.drawString(x, y, pre)
    x0 = x + stringWidth(pre, T, size) + 5
    c.setLineWidth(0.4)
    c.line(x0, y - 2, x0 + blank, y - 2)
    if value != "":
        text, s = _fit(str(value), blank - 4)
        c.setFont(VAL, s)
        c.drawCentredString(x0 + blank / 2, y + 1, text)
    c.setFont(T, size)
    c.drawString(x0 + blank + 5, y, post)
    return x0 + blank + 5 + stringWidth(post, T, size)


def para(c, y, text, size=11.5, x=LM, font=T, gap=4):
    c.setFont(font, size)
    for ln in simpleSplit(text, font, size, RM - x):
        c.drawString(x, y, ln)
        y -= size + 3
    return y - gap


EMBLEM_FILES = ("coat_of_arms.png", "coat_of_arms.jpg", "coat_of_arms.jpeg")


def emblem_path():
    """The national coat of arms image, if it has been placed in core/static/core/."""
    folder = Path(__file__).resolve().parent / "static" / "core"
    for name in EMBLEM_FILES:
        path = folder / name
        if path.exists():
            return path
    return None


def draw_emblem(c, y_top, height=56):
    """Draw the coat of arms centred, top edge at y_top. Returns the height used (0 if no image)."""
    path = emblem_path()
    if path is None:
        return 0
    try:
        img = ImageReader(str(path))
        iw, ih = img.getSize()
        width = height * iw / ih
        c.drawImage(img, (W - width) / 2, y_top - height, width=width, height=height, mask="auto")
    except Exception:
        return 0
    return height


def header(c, title_dept, dy=0):
    c.setFont(TB, 13)
    c.drawCentredString(W / 2, H - 52 - dy, "SOROTI DISTRICT LOCAL GOVERNMENT")
    c.setFont(T, 11)
    c.drawCentredString(W / 2, H - 67 - dy, title_dept)


def footer(c, permit, url):
    size = 72
    widget = qr.QrCodeWidget(url)
    b = widget.getBounds()
    bw, bh = b[2] - b[0], b[3] - b[1]
    d = Drawing(size, size, transform=[size / bw, 0, 0, size / bh, 0, 0])
    d.add(widget)
    renderPDF.draw(d, c, RM - size, 34)
    c.setFillGray(0.35)
    c.setFont("Helvetica", 7.5)
    c.drawString(LM, 70, "System reference: %s" % permit.code)
    c.drawString(LM, 60, "Valid until: %s" % _d(permit.valid_until))
    c.drawString(LM, 50, "Scan the code to check that this permit is genuine and still valid.")
    c.drawString(LM, 40, "Recorded in SDLG-Production MIS, Soroti District Local Government.")
    c.setFillGray(0)
    if permit.status == "cancelled":
        c.saveState()
        c.translate(W / 2, H / 2)
        c.rotate(35)
        c.setFillColorRGB(0.8, 0.1, 0.1)
        c.setFillAlpha(0.22)
        c.setFont("Helvetica-Bold", 90)
        c.drawCentredString(0, 0, "CANCELLED")
        c.restoreState()


def signature_block(c, y, permit, officer_label):
    c.setLineWidth(0.5)
    c.line(LM, y, LM + 175, y)
    c.line(LM + 235, y, RM, y)
    _put(c, LM + 4, y + 2, _d(permit.issue_date), 165)
    c.setFont(T, 12)
    c.drawString(LM, y - 14, "Date")
    c.drawString(LM + 235, y - 14, officer_label)
    c.setFont("Helvetica", 8.5)
    c.drawString(LM + 235, y - 28, "Name: %s" % permit.issued_by)
    return y - 52


# ----------------------------------------------------------------- animals
SUBTITLE = {
    ANIMAL_SUB: "(Subcounty to subcounty)",
    ANIMAL_SLAUGHTER: "(From one district to another for slaughter purposes only.)",
    ANIMAL_OTHER: "(From one district to another for the purposes other than slaughter.)",
}
COND_1 = ("This permit is issued subject to observance of and compliance with the particulars "
          "furnished and set out in (a) to (%s) of this permit.")
COND_ROAD = ("None of the animals to which this permit relates shall be sold, exchanged or "
             "slaughtered on the road.")
COND_HIDES = ("The hides of any animals which have died while being moved %s be produced for "
              "inspection on arrival at the destination.")
COND_HERD = ("No animals shall be herded, kraaled or watered together with stock resident in "
             "areas through which the animals pass.")


def draw_animal(c, p):
    dy = draw_emblem(c, H - 32)
    dy = dy + 4 if dy else 0
    header(c, "Production Department - Veterinary Services", dy)
    y = H - 100 - dy
    if p.permit_type == ANIMAL_SUB:
        c.setFont(T, 11)
        c.drawRightString(RM, y + 18, "Second Schedule, rules 10, 11")
    c.setFont(TB, 17)
    c.drawCentredString(W / 2, y, "Movement Permit")
    c.setFont(T, 12.5)
    c.drawCentredString(W / 2, y - 18, SUBTITLE[p.permit_type])
    y -= 56
    line(c, y, "No.", p.book_number or p.code, end=LM + 230)
    y -= 36

    rows = []
    if p.permit_type == ANIMAL_SUB:
        line(c, y, "County of", p.county)
        y -= 25
        line(c, y, "Name", p.holder_name)
        y -= 25
        rows = [
            ("(a)  is allowed to move", p.movement_text),
            ("(b)  from", p.from_place),
            ("(c)  to", p.to_place),
            None,
            ("(e)  via", p.via),
            ("(f)  for the purpose of", p.purpose),
        ]
        last = "f"
    elif p.permit_type == ANIMAL_SLAUGHTER:
        line(c, y, "Permission is granted to", p.holder_name)
        y -= 25
        rows = [
            ("(a)  to remove for slaughter only", p.movement_text),
            ("(b)  bearing the following brand", p.brand),
            ("(c)  within the next", "%s day(s)" % p.valid_days),
            ("(d)  from", p.from_place),
            ("(e)  to", p.to_place),
            ("(f)  via", p.via),
            "slaughter",
        ]
        last = "g"
    else:
        line(c, y, "Permission is granted to", p.holder_name)
        y -= 25
        rows = [
            ("(a)  to remove", p.movement_text),
            ("(b)  within the next", "%s day(s)" % p.valid_days),
            ("(c)  from", p.from_place),
            ("(d)  to", p.to_place),
            ("(e)  via", p.via),
            ("(f)  for the purpose of", p.purpose),
        ]
        last = "f"

    for r in rows:
        if r is None:
            days_line(c, y, "(d)  within the next", p.valid_days, "days", x=LM + 26)
        elif r == "slaughter":
            days_line(c, y, "(g)  to be slaughtered within", p.slaughter_within_days or "", "days", x=LM + 26)
        else:
            line(c, y, r[0], r[1], x=LM + 26)
        y -= 25

    y = signature_block(c, y - 22, p, p.officer_caption)

    c.setFont(T, 12.5)
    c.drawCentredString(W / 2, y - 6, "Condition." if p.permit_type == ANIMAL_SUB else "Conditions.")
    y -= 32
    if p.permit_type == ANIMAL_SUB:
        y = para(c, y, COND_1 % last)
    elif p.permit_type == ANIMAL_SLAUGHTER:
        y = para(c, y, "(1)  " + COND_1 % last, x=LM + 18)
        y = para(c, y, "(2)  " + COND_ROAD, x=LM + 18)
        y = para(c, y, "(3)  " + COND_HIDES % "must", x=LM + 18)
        y = para(c, y, "(4)  " + COND_HERD, x=LM + 18)
    else:
        y = para(c, y, "(1)  " + COND_1 % last, x=LM + 18)
        y = para(c, y, "(2)  " + COND_ROAD, x=LM + 18)
        y = para(c, y, "(3)  " + COND_HIDES % "shall", x=LM + 18)


# -------------------------------------------------------------------- fish
def draw_fish(c, p, copy_label):
    c.setFont(T, 12.5)
    c.drawCentredString(W / 2, H - 46, "SECOND SCHEDULE")
    c.drawRightString(RM, H - 62, "Rule 8(1) (a)")
    c.setFont("Helvetica", 8)
    c.drawString(LM, H - 46, copy_label)
    draw_emblem(c, H - 52, height=52)
    c.setFont(T, 12.5)
    y = H - 118
    c.drawString(LM, y, "Serial No.")
    _put(c, LM + 62, y, p.book_number or p.code, 160)
    c.setLineWidth(0.4)
    c.line(LM + 60, y - 2, LM + 230, y - 2)
    y -= 22
    c.setFont(T, 13)
    c.drawCentredString(W / 2, y, "DEPARTMENT OF FISHERIES RESOURCES")
    c.drawCentredString(W / 2, y - 15, "FISH MOVEMENT PERMIT")
    y -= 40
    c.setFont(T, 12)
    c.drawString(LM, y, "(Valid in Uganda only)")
    y -= 18
    c.drawString(LM, y, "Section A")
    y -= 21
    line(c, y, "Name", p.holder_name)
    y -= 21
    line(c, y, "Address", p.address)
    y -= 21
    y = para(c, y, "The bearer is authorised to move fish and/or fishery products from one part of "
                   "Uganda to another part as per details below and in accordance with the Fish "
                   "(Quality Assurance) Rules, (1998)", size=12, gap=10)
    pair(c, y, "Fish species (indicate local name)", p.fish_species, "Quantity (kg)", p.quantity_text, split=0.66)
    y -= 24
    c.setFont(T, 12)
    c.drawString(LM, y, "Form (Fresh/Smoked/Salted/Sun dried)")
    y -= 20
    line(c, y, "", p.get_fish_form_display() if p.fish_form else "")
    y -= 24
    c.setFont(T, 12)
    c.drawString(LM, y, "Details of origin")
    y -= 21
    site = p.origin_landing_site.name if p.origin_landing_site_id else ""
    pair(c, y, "(i) Lake", p.origin_lake, "(ii) Landing site", site)
    y -= 23
    pair(c, y, "(iii) Fish market", p.origin_market, "(iv) District", p.origin_district)
    y -= 23
    pair(c, y, "Destination", p.to_place, "District", p.dest_district, split=0.55)
    y -= 26
    pair(c, y, "Mode of transport", p.transport_mode, "Regn. No.", p.vehicle_reg, split=0.55)
    y -= 27
    c.setFont(T, 12)
    c.drawString(LM, y, "Section B Attestation")
    y -= 20
    y = para(c, y, "I the undersigned official certify that the fish has been inspected and conforms "
                   "to the provisions of the Fish Act and statutory instruments made under it.",
             size=12, gap=12)
    pair(c, y, "Date of issue", _d(p.issue_date), "Permit validity",
         "%s day(s), until %s" % (p.valid_days, _d(p.valid_until)), split=0.46)
    y -= 26
    # fees paid ... (Ug. Shs.) ... (in words)
    c.setFont(T, 12)
    c.drawString(LM, y, "Fees paid")
    x1 = LM + stringWidth("Fees paid", T, 12) + 5
    c.line(x1, y - 2, x1 + 70, y - 2)
    if p.fee:
        _put(c, x1 + 3, y, "{:,}".format(p.fee), 64)
    c.drawString(x1 + 76, y, "(Ug. Shs.)")
    x2 = x1 + 76 + stringWidth("(Ug. Shs.)", T, 12) + 5
    x3 = RM - stringWidth("(in words)", T, 12) - 5
    c.line(x2, y - 2, x3, y - 2)
    if p.fee:
        _put(c, x2 + 3, y, shillings_in_words(p.fee), x3 - x2 - 6)
    c.drawString(x3 + 5, y, "(in words)")
    y -= 27
    pair(c, y, "Issuing Officer", p.issued_by, "Title", p.officer_post, split=0.55)
    y -= 27
    line(c, y, "Signature and official stamp", "", end=LM + 360)
    y -= 26
    c.setFont("Helvetica", 9)
    c.drawString(LM, y, "Original to the owner of the fish")
    c.drawString(LM, y - 12, "Duplicate to the Commissioner for Fisheries")


# -------------------------------------------------------------------- main
def make_permit_pdf(permit, verify_url):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("Movement permit %s" % permit.code)
    c.setAuthor("SDLG-Production MIS")
    if permit.permit_type == FISH:
        for label in ("ORIGINAL COPY - for the owner of the fish",
                      "DUPLICATE COPY - for the Commissioner for Fisheries"):
            draw_fish(c, permit, label)
            footer(c, permit, verify_url)
            c.showPage()
    else:
        draw_animal(c, permit)
        footer(c, permit, verify_url)
        c.showPage()
    c.save()
    return buf.getvalue()
