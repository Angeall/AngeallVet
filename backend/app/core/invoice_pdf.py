"""Simple, dependency-light invoice / quote PDF generation (free tier).

This is the DEFAULT output for every clinic: a clean A4 PDF rendered locally with
fpdf2 (pure-python, no system libraries). The premium ``invoice_ninja`` module
swaps this for Invoice Ninja's compliant PDF + Peppol e-invoicing.

Core PDF fonts are Latin-1 only, so text is sanitised and amounts use the "EUR"
suffix rather than the € glyph (a Unicode TTF could be added later for €).
"""
from __future__ import annotations

from decimal import Decimal


def _s(value) -> str:
    """Make a string safe for the Latin-1 core fonts (drop unsupported glyphs)."""
    return str(value if value is not None else "").encode("latin-1", "replace").decode("latin-1")


def _money(value) -> str:
    """Format an amount the French way: 1 234,56 EUR."""
    n = float(value or 0)
    s = f"{n:,.2f}".replace(",", " ").replace(".", ",")
    return f"{s} EUR"


def _qty(value) -> str:
    n = float(value or 0)
    return str(int(n)) if n == int(n) else f"{n:.2f}".replace(".", ",")


def _date(value) -> str:
    try:
        return value.strftime("%d/%m/%Y")
    except Exception:
        return _s(value or "")


def _new_pdf():
    from fpdf import FPDF

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    return pdf


def _header(pdf, clinic, *, title: str, number: str, meta: list):
    from fpdf.enums import XPos, YPos

    # Clinic identity (left)
    pdf.set_xy(15, 15)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(110, 8, _s(getattr(clinic, "clinic_name", None) or "Clinique vétérinaire"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    lines = []
    if clinic:
        if clinic.address:
            lines.append(clinic.address)
        cp_city = " ".join(p for p in [getattr(clinic, "postal_code", None), getattr(clinic, "city", None)] if p)
        if cp_city:
            lines.append(cp_city)
        if getattr(clinic, "country", None):
            lines.append(clinic.country)
        contact = "  ".join(p for p in [getattr(clinic, "phone", None), getattr(clinic, "email", None)] if p)
        if contact:
            lines.append(contact)
        ids = "  ".join(
            f"{lbl} {val}" for lbl, val in [
                ("SIRET", getattr(clinic, "siret", None)),
                ("TVA", getattr(clinic, "vat_number", None)),
            ] if val
        )
        if ids:
            lines.append(ids)
    for ln in lines:
        pdf.cell(110, 4.5, _s(ln), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Document title + number + meta (right)
    pdf.set_xy(125, 15)
    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(65, 9, _s(title), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(125)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(65, 6, _s(number), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    for label, val in meta:
        pdf.set_x(125)
        pdf.cell(65, 5, _s(f"{label} : {val}"), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(20, 20, 20)
    pdf.ln(4)


def _client_block(pdf, client):
    from fpdf.enums import XPos, YPos

    y = max(pdf.get_y(), 52)
    pdf.set_xy(125, y)
    pdf.set_draw_color(220, 220, 220)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(65, 5, "FACTURÉ À", align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(125)
    pdf.set_font("Helvetica", "", 9)
    name = f"{getattr(client, 'first_name', '') or ''} {getattr(client, 'last_name', '') or ''}".strip()
    parts = [name]
    if getattr(client, "address", None):
        parts.append(client.address)
    cp_city = " ".join(p for p in [getattr(client, "postal_code", None), getattr(client, "city", None)] if p)
    if cp_city:
        parts.append(cp_city)
    if getattr(client, "vat_number", None):
        parts.append(f"TVA {client.vat_number}")
    for p in parts:
        pdf.set_x(125)
        pdf.cell(65, 4.5, _s(p), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)


def _lines_table(pdf, lines):
    from fpdf.enums import XPos, YPos

    # Column widths (sum = 180mm usable)
    w_desc, w_qty, w_pu, w_vat, w_tot = 92, 16, 28, 16, 28
    pdf.set_y(max(pdf.get_y(), 90))
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(241, 245, 249)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(w_desc, 7, "  Désignation", fill=True)
    pdf.cell(w_qty, 7, "Qté", align="C", fill=True)
    pdf.cell(w_pu, 7, "PU HT", align="R", fill=True)
    pdf.cell(w_vat, 7, "TVA", align="C", fill=True)
    pdf.cell(w_tot, 7, "Total HT", align="R", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(20, 20, 20)
    fill = False
    for ln in lines:
        desc = _s(ln.description)
        if len(desc) > 60:
            desc = desc[:57] + "..."
        disc = float(getattr(ln, "discount_percent", 0) or 0)
        if disc:
            desc += _s(f"  (-{_qty(disc)}%)")
        pdf.set_fill_color(250, 250, 251)
        pdf.cell(w_desc, 6.5, "  " + desc, fill=fill)
        pdf.cell(w_qty, 6.5, _qty(ln.quantity), align="C", fill=fill)
        pdf.cell(w_pu, 6.5, _money(ln.unit_price), align="R", fill=fill)
        pdf.cell(w_vat, 6.5, _s(f"{_qty(ln.vat_rate)}%"), align="C", fill=fill)
        pdf.cell(w_tot, 6.5, _money(ln.line_total), align="R", fill=fill,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        fill = not fill


def _vat_breakdown(lines):
    """Group lines by VAT rate -> {rate: (base_ht, vat_amount)}."""
    by_rate = {}
    for ln in lines:
        rate = Decimal(str(getattr(ln, "vat_rate", 0) or 0))
        base = Decimal(str(getattr(ln, "line_total", 0) or 0))
        cur = by_rate.get(rate, Decimal(0))
        by_rate[rate] = cur + base
    return {rate: (base, (base * rate / Decimal(100))) for rate, base in by_rate.items()}


def _totals(pdf, *, subtotal, vat_table, total, amount_paid=None):
    from fpdf.enums import XPos, YPos

    pdf.ln(2)
    x = 120
    pdf.set_font("Helvetica", "", 9)
    pdf.set_x(x)
    pdf.cell(40, 6, "Total HT", align="R")
    pdf.cell(30, 6, _money(subtotal), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    for rate in sorted(vat_table):
        _, vat_amount = vat_table[rate]
        pdf.set_x(x)
        pdf.cell(40, 6, _s(f"TVA {_qty(rate)}%"), align="R")
        pdf.cell(30, 6, _money(vat_amount), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(x)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(40, 8, "Total TTC", align="R", border="T")
    pdf.cell(30, 8, _money(total), align="R", border="T", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if amount_paid is not None:
        paid = float(amount_paid or 0)
        due = float(total or 0) - paid
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(x)
        pdf.cell(40, 6, "Réglé", align="R")
        pdf.cell(30, 6, _money(paid), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if abs(due) >= 0.01:
            pdf.set_x(x)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(40, 6, "Reste à payer", align="R")
            pdf.cell(30, 6, _money(due), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _footer_note(pdf, note):
    from fpdf.enums import XPos, YPos

    if not note:
        return
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(180, 4.5, _s(note), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(20, 20, 20)


def render_invoice_pdf(invoice, lines, client, clinic) -> bytes:
    """Render a simple invoice PDF and return the raw bytes."""
    pdf = _new_pdf()
    meta = [("Date", _date(invoice.issue_date))]
    if getattr(invoice, "due_date", None):
        meta.append(("Échéance", _date(invoice.due_date)))
    _header(pdf, clinic, title="FACTURE", number=_s(invoice.invoice_number), meta=meta)
    _client_block(pdf, client)
    _lines_table(pdf, lines)
    _totals(
        pdf,
        subtotal=invoice.subtotal,
        vat_table=_vat_breakdown(lines),
        total=invoice.total,
        amount_paid=getattr(invoice, "amount_paid", None),
    )
    _footer_note(pdf, getattr(invoice, "notes", None))
    return bytes(pdf.output())


def render_estimate_pdf(estimate, lines, client, clinic) -> bytes:
    """Render a simple quote (devis) PDF and return the raw bytes."""
    pdf = _new_pdf()
    meta = [("Date", _date(estimate.issue_date))]
    if getattr(estimate, "valid_until", None):
        meta.append(("Valable jusqu'au", _date(estimate.valid_until)))
    _header(pdf, clinic, title="DEVIS", number=_s(estimate.estimate_number), meta=meta)
    _client_block(pdf, client)
    _lines_table(pdf, lines)
    _totals(pdf, subtotal=estimate.subtotal, vat_table=_vat_breakdown(lines), total=estimate.total)
    if getattr(estimate, "signed_at", None):
        from fpdf.enums import XPos, YPos

        pdf.ln(6)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 5, _s(f"Devis accepté et signé le {_date(estimate.signed_at)}."),
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    _footer_note(pdf, getattr(estimate, "notes", None))
    return bytes(pdf.output())
