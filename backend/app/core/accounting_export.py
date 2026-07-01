"""Accounting exports for the ``accounting`` module.

Turns invoices + payments into double-entry accounting rows:
- a readable **journal** workbook (sales journal, treasury journal, VAT recap);
- a **FEC** file (the French "Fichier des Écritures Comptables" standard, 18
  tab-separated columns — accepted by most accounting tools).

Account numbers follow the Belgian PCMN by default (clients 400, sales 700, VAT
to pay 451, cash 570, bank 550); a future ``ClinicSettings`` could make them
configurable.
"""
from __future__ import annotations

from datetime import date

# Default chart-of-accounts (Belgian PCMN-ish).
ACC_CLIENTS = ("400", "Clients")
ACC_SALES = ("700", "Ventes")
ACC_VAT = ("451", "TVA à payer")
ACC_CASH = ("570", "Caisse")
ACC_BANK = ("550", "Banque")

METHOD_LABELS = {
    "cash": "Espèces", "card": "Carte", "check": "Chèque",
    "transfer": "Virement", "stripe": "Stripe",
}


def _f(x) -> float:
    return round(float(x or 0), 2)


def _payment_account(method: str):
    """Cash payments hit the cash account; everything else the bank account."""
    if method == "cash":
        return ACC_CASH + ("CA", "Caisse")
    return ACC_BANK + ("BQ", "Banque")


# ─── Readable journal (workbook sheets) ──────────────────────────────────────

_JOURNAL_HEADERS = ["Date", "Journal", "Piece", "Compte", "Libelle", "Tiers", "Debit", "Credit"]


def build_journal_sheets(invoices, payments, client_names: dict, inv_map: dict | None = None):
    # ``invoices`` drives the sales journal (issued in the period); ``inv_map``
    # resolves payment pieces (a payment may settle an out-of-period invoice).
    inv_map = inv_map if inv_map is not None else {inv.id: inv for inv in invoices}

    sales = []
    for inv in sorted(invoices, key=lambda i: (i.issue_date or date.min, i.id)):
        d = inv.issue_date.isoformat() if inv.issue_date else ""
        name = client_names.get(inv.client_id, "")
        ttc, ht, vat = _f(inv.total), _f(inv.subtotal), _f(inv.total_vat)
        sales.append([d, "VT", inv.invoice_number, ACC_CLIENTS[0], ACC_CLIENTS[1], name, ttc, 0])
        sales.append([d, "VT", inv.invoice_number, ACC_SALES[0], ACC_SALES[1], "", 0, ht])
        if vat:
            sales.append([d, "VT", inv.invoice_number, ACC_VAT[0], ACC_VAT[1], "", 0, vat])

    treasury = []
    for p in sorted(payments, key=lambda x: (x.payment_date or date.min, x.id)):
        inv = inv_map.get(p.invoice_id)
        piece = inv.invoice_number if inv else f"#{p.invoice_id}"
        name = client_names.get(inv.client_id, "") if inv else ""
        d = p.payment_date.isoformat() if p.payment_date else ""
        num, lib, jrn, _ = _payment_account(p.payment_method)
        amt = _f(p.amount)
        treasury.append([d, jrn, piece, num, lib, name, amt, 0])
        treasury.append([d, jrn, piece, ACC_CLIENTS[0], ACC_CLIENTS[1], name, 0, amt])

    by_rate = {}
    for inv in invoices:
        for line in getattr(inv, "lines", []):
            rate = _f(line.vat_rate)
            base = _f(line.line_total)
            b, v = by_rate.get(rate, (0.0, 0.0))
            by_rate[rate] = (b + base, v + base * rate / 100)
    vat_rows = [[f"{r}%", round(b, 2), round(v, 2), round(b + v, 2)] for r, (b, v) in sorted(by_rate.items())]

    return [
        {"title": "Journal des ventes", "headers": _JOURNAL_HEADERS, "rows": sales},
        {"title": "Journal de tresorerie", "headers": _JOURNAL_HEADERS, "rows": treasury},
        {"title": "Recap TVA", "headers": ["Taux", "Base HT", "TVA", "TTC"], "rows": vat_rows},
    ]


# ─── FEC (Fichier des Écritures Comptables) ──────────────────────────────────

_FEC_HEADER = [
    "JournalCode", "JournalLib", "EcritureNum", "EcritureDate", "CompteNum",
    "CompteLib", "CompAuxNum", "CompAuxLib", "PieceRef", "PieceDate",
    "EcritureLib", "Debit", "Credit", "EcritureLet", "DateLet", "ValidDate",
    "Montantdevise", "Idevise",
]


def _fec_date(d) -> str:
    return d.strftime("%Y%m%d") if d else ""


def _fec_amount(x) -> str:
    return f"{_f(x):.2f}".replace(".", ",")  # FEC uses a decimal comma


def build_fec(invoices, payments, client_names: dict, inv_map: dict | None = None) -> str:
    inv_map = inv_map if inv_map is not None else {inv.id: inv for inv in invoices}
    lines = ["\t".join(_FEC_HEADER)]
    num = 0

    def emit(jrn, jrnlib, edate, compte, comptelib, aux, auxlib, piece, lib, debit, credit):
        # A tab/CR/LF inside a text field (client name, invoice number) would
        # corrupt the tab-separated column/row layout — strip them.
        def c(x):
            return str(x).replace("\t", " ").replace("\r", " ").replace("\n", " ")
        lines.append("\t".join([
            c(jrn), c(jrnlib), str(num), _fec_date(edate), c(compte), c(comptelib),
            c(aux), c(auxlib), c(piece), _fec_date(edate), c(lib),
            _fec_amount(debit), _fec_amount(credit), "", "", _fec_date(edate), "", "",
        ]))

    for inv in sorted(invoices, key=lambda i: (i.issue_date or date.min, i.id)):
        num += 1
        d = inv.issue_date
        name = client_names.get(inv.client_id, "")
        aux = str(inv.client_id or "")
        lib = f"Facture {inv.invoice_number}"
        emit("VT", "Ventes", d, ACC_CLIENTS[0], ACC_CLIENTS[1], aux, name, inv.invoice_number, lib, inv.total, 0)
        emit("VT", "Ventes", d, ACC_SALES[0], ACC_SALES[1], "", "", inv.invoice_number, lib, 0, inv.subtotal)
        if _f(inv.total_vat):
            emit("VT", "Ventes", d, ACC_VAT[0], ACC_VAT[1], "", "", inv.invoice_number, lib, 0, inv.total_vat)

    for p in sorted(payments, key=lambda x: (x.payment_date or date.min, x.id)):
        num += 1
        inv = inv_map.get(p.invoice_id)
        d = p.payment_date
        name = client_names.get(inv.client_id, "") if inv else ""
        aux = str(inv.client_id) if inv and inv.client_id else ""
        piece = inv.invoice_number if inv else f"#{p.invoice_id}"
        acc_num, acc_lib, jrn, jrnlib = _payment_account(p.payment_method)
        lib = f"Reglement {piece}"
        emit(jrn, jrnlib, d, acc_num, acc_lib, "", "", piece, lib, p.amount, 0)
        emit(jrn, jrnlib, d, ACC_CLIENTS[0], ACC_CLIENTS[1], aux, name, piece, lib, 0, p.amount)

    return "\n".join(lines) + "\n"
