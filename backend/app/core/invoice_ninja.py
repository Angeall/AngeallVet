"""Thin client for an Invoice Ninja instance (v5 REST API).

AngeallVet stays the source of care + billing data; we *push* finalised invoices
to the clinic's Invoice Ninja instance, which owns the legally-compliant output:
PDF, EN 16931 UBL and Peppol e-invoicing (B2B). Connection details are stored per
tenant in ClinicSettings. The exact endpoint paths below follow Invoice Ninja v5;
they are isolated here so they can be tuned to a specific instance version.
"""

import httpx

# ISO 3166-1 numeric country codes used by Invoice Ninja's `country_id`.
_COUNTRY_ID = {
    "belgique": "56", "belgium": "56", "belgië": "56",
    "france": "250",
    "luxembourg": "442",
    "pays-bas": "528", "netherlands": "528",
}


class InvoiceNinjaError(Exception):
    pass


def country_id(name):
    return _COUNTRY_ID.get((name or "").strip().lower())


class InvoiceNinjaClient:
    def __init__(self, base_url, token, timeout=20.0):
        self.base = (base_url or "").rstrip("/")
        self.headers = {
            "X-Api-Token": token or "",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        self.timeout = timeout

    def _request(self, method, path, **kwargs):
        url = f"{self.base}/api/v1/{path.lstrip('/')}"
        try:
            resp = httpx.request(method, url, headers=self.headers, timeout=self.timeout, **kwargs)
        except httpx.HTTPError as exc:
            raise InvoiceNinjaError(f"connexion impossible ({exc})")
        if resp.status_code >= 400:
            raise InvoiceNinjaError(f"HTTP {resp.status_code} — {resp.text[:300]}")
        return resp

    def create_client(self, payload) -> str:
        return self._request("POST", "clients", json=payload).json()["data"]["id"]

    def create_invoice(self, payload) -> dict:
        return self._request("POST", "invoices", json=payload).json()["data"]

    def email_invoice(self, invoice_id) -> None:
        # v5 bulk action — emails the PDF (B2C) and dispatches the Peppol e-invoice
        # when e-invoicing is enabled and the client carries a Peppol/VAT routing id.
        self._request("POST", "invoices/bulk", json={"action": "email", "ids": [invoice_id]})

    def download_pdf(self, invoice_id) -> bytes:
        return self._request("GET", f"invoices/{invoice_id}/download").content


def client_payload(client) -> dict:
    """Map an AngeallVet client to an Invoice Ninja client."""
    name = f"{client.last_name} {client.first_name}".strip() or client.email or f"Client {client.id}"
    payload = {
        "name": name,
        "vat_number": client.vat_number or "",
        "address1": client.address or "",
        "city": client.city or "",
        "postal_code": client.postal_code or "",
        "contacts": [{
            "first_name": client.first_name or "",
            "last_name": client.last_name or "",
            "email": client.email or "",
        }],
    }
    cid = country_id(client.country)
    if cid:
        payload["country_id"] = cid
    return payload


def invoice_payload(in_client_id, invoice, lines) -> dict:
    """Map an AngeallVet invoice (+ its lines) to an Invoice Ninja invoice."""
    items = [{
        "notes": line.description or "",
        "quantity": float(line.quantity or 0),
        "cost": float(line.unit_price or 0),
        "tax_name1": "TVA",
        "tax_rate1": float(line.vat_rate or 0),
    } for line in lines]
    return {
        "client_id": in_client_id,
        "po_number": invoice.invoice_number,  # cross-reference to our number
        "line_items": items,
        "public_notes": invoice.notes or "",
    }
