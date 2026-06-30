"""Tests for the veterinarian commission engine (computed on the encaissé)."""

from datetime import date
from decimal import Decimal

from app.core.commissions import compute_commissions
from app.models.user import User, UserRole
from app.models.client import Client
from app.models.inventory import Product, ProductType
from app.models.billing import Invoice, InvoiceLine, InvoiceVeterinarian, Payment, InvoiceStatus
from app.models.billing_rules import BillingRule, BillingRuleComponent, BillingDayOverride


def _worked_example(db, payday, paid_amount=None):
    """Facture FAC-1024 partagée entre 2 vétos, règle « Standard » :
    - médicament : 50 % du bénéfice
    - acte (service) : 30 % du CA HT
    - produit Vaccin : bonus 3 €/unité (prioritaire sur la catégorie)
    """
    a = User(pb_user_id="vetA", email="a@t.com", first_name="Alice", last_name="A", role=UserRole.VETERINARIAN, is_active=True)
    b = User(pb_user_id="vetB", email="b@t.com", first_name="Bob", last_name="B", role=UserRole.VETERINARIAN, is_active=True)
    db.add_all([a, b])
    cli = Client(first_name="Jean", last_name="Dupont")
    db.add(cli)
    db.flush()

    med = Product(name="Antibiotique", product_type=ProductType.MEDICATION, purchase_price=Decimal("15"), selling_price=Decimal("40"))
    vac = Product(name="Vaccin Rage", product_type=ProductType.MEDICATION, purchase_price=Decimal("10"), selling_price=Decimal("25"))
    db.add_all([med, vac])
    db.flush()

    rule = BillingRule(name="Standard", is_active=True)
    db.add(rule)
    db.flush()
    db.add_all([
        BillingRuleComponent(rule_id=rule.id, scope="category", product_type="medication", basis="profit", value=Decimal("50")),
        BillingRuleComponent(rule_id=rule.id, scope="category", product_type="service", basis="revenue", value=Decimal("30")),
        BillingRuleComponent(rule_id=rule.id, scope="product", product_id=vac.id, basis="per_unit", value=Decimal("3")),
    ])

    total = Decimal("155")
    inv = Invoice(invoice_number="FAC-1024", client_id=cli.id, status=InvoiceStatus.PAID, total=total, amount_paid=total)
    db.add(inv)
    db.flush()
    db.add_all([
        InvoiceLine(invoice_id=inv.id, product_id=med.id, description="Antibiotique", quantity=Decimal("2"), unit_price=Decimal("40"), line_total=Decimal("80")),
        InvoiceLine(invoice_id=inv.id, product_id=None, description="Consultation", quantity=Decimal("1"), unit_price=Decimal("50"), line_total=Decimal("50")),
        InvoiceLine(invoice_id=inv.id, product_id=vac.id, description="Vaccin Rage", quantity=Decimal("1"), unit_price=Decimal("25"), line_total=Decimal("25")),
    ])
    db.add_all([
        InvoiceVeterinarian(invoice_id=inv.id, user_id=a.id),
        InvoiceVeterinarian(invoice_id=inv.id, user_id=b.id),
    ])
    db.add_all([
        BillingDayOverride(user_id=a.id, date=payday, rule_id=rule.id),
        BillingDayOverride(user_id=b.id, date=payday, rule_id=rule.id),
    ])
    amount = paid_amount if paid_amount is not None else total
    db.add(Payment(invoice_id=inv.id, amount=amount, payment_method="card", payment_date=payday))
    db.commit()
    return a, b, rule


def test_commission_worked_example(db):
    """43 € de commission sur la facture, partagés ÷ 2 -> 21,50 € par véto."""
    payday = date(2026, 6, 15)
    a, b, _ = _worked_example(db, payday)
    res = compute_commissions(db, payday, payday)
    by_user = {v["user_id"]: v for v in res["veterinarians"]}
    assert by_user[a.id]["commission"] == 21.50
    assert by_user[b.id]["commission"] == 21.50
    assert res["total"] == 43.0


def test_commission_partial_payment_scales(db):
    """Demi-paiement (77,50 € sur 155 €) -> commission divisée par deux."""
    payday = date(2026, 6, 16)
    a, b, _ = _worked_example(db, payday, paid_amount=Decimal("77.5"))
    res = compute_commissions(db, payday, payday)
    by_user = {v["user_id"]: v for v in res["veterinarians"]}
    assert by_user[a.id]["commission"] == 10.75
    assert by_user[b.id]["commission"] == 10.75


def test_commission_no_rule_means_zero(db):
    """Sans règle applicable ce jour-là, aucune commission."""
    payday = date(2026, 6, 17)
    _worked_example(db, payday)
    db.query(BillingDayOverride).delete()
    db.commit()
    res = compute_commissions(db, payday, payday)
    assert res["total"] == 0.0
