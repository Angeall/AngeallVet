"""Tests for the veterinarian commission engine (computed on the encaissé)."""

from datetime import date
from decimal import Decimal

from app.core.commissions import compute_commissions
from app.models.user import User, UserRole
from app.models.client import Client
from app.models.inventory import Product, ProductType
from app.models.billing import Invoice, InvoiceLine, InvoiceVeterinarian, Payment, InvoiceStatus
from app.models.billing_rules import (
    BillingRule, BillingRuleComponent, BillingRuleTier, BillingDayOverride,
    BillingProgram, BillingProgramDay,
)


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


def _tier_rule(db, basis="revenue"):
    """Échelons : ≤12 000 € -> 400 €, ≤24 000 € -> 650 €, au-delà -> 1 000 €."""
    rule = BillingRule(name="Paliers", is_active=True, rule_type="tier", tier_basis=basis)
    db.add(rule)
    db.flush()
    db.add_all([
        BillingRuleTier(rule_id=rule.id, up_to=Decimal("12000"), amount=Decimal("400")),
        BillingRuleTier(rule_id=rule.id, up_to=Decimal("24000"), amount=Decimal("650")),
        BillingRuleTier(rule_id=rule.id, up_to=None, amount=Decimal("1000")),
    ])
    return rule


def test_tier_rule_revenue_bracket(db):
    """CA HT encaissé de 15 000 € -> tranche ≤24 000 € -> bonus 650 €."""
    payday = date(2026, 6, 20)
    vet = User(pb_user_id="vetT", email="t@t.com", first_name="Tess", last_name="T", role=UserRole.VETERINARIAN, is_active=True)
    cli = Client(first_name="Jean", last_name="Dupont")
    db.add_all([vet, cli])
    db.flush()
    rule = _tier_rule(db)
    inv = Invoice(invoice_number="FAC-T1", client_id=cli.id, status=InvoiceStatus.PAID, total=Decimal("15000"), amount_paid=Decimal("15000"))
    db.add(inv)
    db.flush()
    db.add(InvoiceLine(invoice_id=inv.id, product_id=None, description="Actes", quantity=Decimal("1"), unit_price=Decimal("15000"), line_total=Decimal("15000")))
    db.add(InvoiceVeterinarian(invoice_id=inv.id, user_id=vet.id))
    db.add(BillingDayOverride(user_id=vet.id, date=payday, rule_id=rule.id))
    db.add(Payment(invoice_id=inv.id, amount=Decimal("15000"), payment_method="card", payment_date=payday))
    db.commit()
    res = compute_commissions(db, payday, payday)
    v = res["veterinarians"][0]
    assert v["bonuses"][0]["base"] == 15000.0
    assert v["bonuses"][0]["amount"] == 650.0
    assert v["commission"] == 650.0
    assert res["total"] == 650.0


def test_tier_rule_profit_basis_scales_with_payment(db):
    """Base = marge encaissée. Demi-paiement -> marge 20 000 € → 10 000 € → 400 €."""
    payday = date(2026, 6, 21)
    vet = User(pb_user_id="vetP", email="p@t.com", first_name="Paul", last_name="P", role=UserRole.VETERINARIAN, is_active=True)
    cli = Client(first_name="Jean", last_name="Dupont")
    db.add_all([vet, cli])
    db.flush()
    prod = Product(name="Croquettes", product_type=ProductType.FOOD, purchase_price=Decimal("10000"), selling_price=Decimal("30000"))
    db.add(prod)
    db.flush()
    rule = _tier_rule(db, basis="profit")
    inv = Invoice(invoice_number="FAC-T2", client_id=cli.id, status=InvoiceStatus.PARTIAL, total=Decimal("30000"), amount_paid=Decimal("15000"))
    db.add(inv)
    db.flush()
    db.add(InvoiceLine(invoice_id=inv.id, product_id=prod.id, description="Croquettes", quantity=Decimal("1"), unit_price=Decimal("30000"), line_total=Decimal("30000")))
    db.add(InvoiceVeterinarian(invoice_id=inv.id, user_id=vet.id))
    db.add(BillingDayOverride(user_id=vet.id, date=payday, rule_id=rule.id))
    db.add(Payment(invoice_id=inv.id, amount=Decimal("15000"), payment_method="card", payment_date=payday))
    db.commit()
    res = compute_commissions(db, payday, payday)
    v = res["veterinarians"][0]
    assert v["bonuses"][0]["base"] == 10000.0
    assert v["commission"] == 400.0


def test_create_tier_rule_via_api(client, auth_headers):
    payload = {
        "name": "Paliers CA", "rule_type": "tier", "tier_basis": "revenue",
        "components": [],
        "tiers": [
            {"up_to": 12000, "amount": 400},
            {"up_to": 24000, "amount": 650},
            {"up_to": None, "amount": 1000},
        ],
    }
    r = client.post("/api/v1/billing/rules", headers=auth_headers, json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["rule_type"] == "tier"
    assert body["tier_basis"] == "revenue"
    assert len(body["tiers"]) == 3
    mine = next(x for x in client.get("/api/v1/billing/rules", headers=auth_headers).json() if x["id"] == body["id"])
    assert sorted(t["amount"] for t in mine["tiers"]) == [400.0, 650.0, 1000.0]
    assert any(t["up_to"] is None for t in mine["tiers"])


# ─── Comprehensive engine coverage ───────────────────────────────────────────

D = date(2026, 7, 1)


def _vet(db, tag):
    u = User(pb_user_id=f"vet{tag}", email=f"{tag}@t.com", first_name=tag, last_name="X",
             role=UserRole.VETERINARIAN, is_active=True)
    db.add(u)
    db.flush()
    return u


def _product(db, name="P", ptype=ProductType.MEDICATION, cost="10", price="40"):
    p = Product(name=name, product_type=ptype, purchase_price=Decimal(cost), selling_price=Decimal(price))
    db.add(p)
    db.flush()
    return p


def _components_rule(db, comps, name="R"):
    rule = BillingRule(name=name, is_active=True)
    db.add(rule)
    db.flush()
    for c in comps:
        db.add(BillingRuleComponent(rule_id=rule.id, **c))
    return rule


def _invoice(db, day, *, lines, vets, total, rule=None, paid=None, status=InvoiceStatus.PAID, number=None):
    cli = Client(first_name="Jean", last_name="Dupont")
    db.add(cli)
    db.flush()
    inv = Invoice(
        invoice_number=number or f"F-{day}-{int(total)}",
        client_id=cli.id, status=status,
        total=Decimal(str(total)), amount_paid=Decimal(str(paid if paid is not None else total)),
    )
    db.add(inv)
    db.flush()
    for ls in lines:
        db.add(InvoiceLine(
            invoice_id=inv.id, description=ls.get("description", "L"), product_id=ls.get("product_id"),
            quantity=Decimal(str(ls["quantity"])), unit_price=Decimal(str(ls["unit_price"])),
            line_total=Decimal(str(ls["line_total"])),
        ))
    for v in vets:
        db.add(InvoiceVeterinarian(invoice_id=inv.id, user_id=v.id))
        if rule is not None:
            db.add(BillingDayOverride(user_id=v.id, date=day, rule_id=rule.id))
    db.add(Payment(invoice_id=inv.id, amount=Decimal(str(paid if paid is not None else total)),
                   payment_method="card", payment_date=day))
    db.commit()
    return inv


def _commission(db, day=D, **kw):
    return compute_commissions(db, day, day, **kw)


# --- bases ---

def test_basis_revenue(db):
    vet = _vet(db, "rev")
    rule = _components_rule(db, [{"scope": "all", "basis": "revenue", "value": Decimal("10")}])
    _invoice(db, D, lines=[{"quantity": 1, "unit_price": 200, "line_total": 200}], vets=[vet], rule=rule, total=200)
    assert _commission(db)["veterinarians"][0]["commission"] == 20.0


def test_basis_profit(db):
    vet = _vet(db, "pro")
    prod = _product(db, cost="30", price="100")
    rule = _components_rule(db, [{"scope": "all", "basis": "profit", "value": Decimal("50")}])
    _invoice(db, D, lines=[{"product_id": prod.id, "quantity": 2, "unit_price": 100, "line_total": 200}], vets=[vet], rule=rule, total=200)
    assert _commission(db)["veterinarians"][0]["commission"] == 70.0  # (200 - 60) * 50%


def test_basis_per_unit(db):
    vet = _vet(db, "pu")
    prod = _product(db)
    rule = _components_rule(db, [{"scope": "all", "basis": "per_unit", "value": Decimal("5")}])
    _invoice(db, D, lines=[{"product_id": prod.id, "quantity": 3, "unit_price": 10, "line_total": 30}], vets=[vet], rule=rule, total=30)
    assert _commission(db)["veterinarians"][0]["commission"] == 15.0


def test_basis_per_line(db):
    vet = _vet(db, "pl")
    rule = _components_rule(db, [{"scope": "all", "basis": "per_line", "value": Decimal("8")}])
    _invoice(db, D, lines=[
        {"quantity": 1, "unit_price": 50, "line_total": 50},
        {"quantity": 2, "unit_price": 20, "line_total": 40},
    ], vets=[vet], rule=rule, total=90)
    assert _commission(db)["veterinarians"][0]["commission"] == 16.0  # 8 × 2 lines


def test_component_precedence_product_wins(db):
    vet = _vet(db, "prec")
    vac = _product(db, name="Vaccin", cost="10", price="25")
    rule = _components_rule(db, [
        {"scope": "all", "basis": "revenue", "value": Decimal("10")},
        {"scope": "category", "product_type": "medication", "basis": "revenue", "value": Decimal("20")},
        {"scope": "product", "product_id": vac.id, "basis": "per_unit", "value": Decimal("3")},
    ])
    _invoice(db, D, lines=[{"product_id": vac.id, "quantity": 2, "unit_price": 25, "line_total": 50}], vets=[vet], rule=rule, total=50)
    assert _commission(db)["veterinarians"][0]["commission"] == 6.0  # product 3×2, not 20% nor 10%


# --- rule resolution ---

def test_program_slot_resolution(db):
    vet = _vet(db, "prog")
    rule = _components_rule(db, [{"scope": "all", "basis": "revenue", "value": Decimal("10")}])
    prog = BillingProgram(name="Prog", is_active=True)
    db.add(prog)
    db.flush()
    db.add(BillingProgramDay(program_id=prog.id, weekday=D.weekday(), rule_id=rule.id))
    vet.billing_program_id = prog.id
    _invoice(db, D, lines=[{"quantity": 1, "unit_price": 100, "line_total": 100}], vets=[vet], rule=None, total=100)
    assert _commission(db)["veterinarians"][0]["commission"] == 10.0


def test_override_beats_program(db):
    vet = _vet(db, "ovr")
    cheap = _components_rule(db, [{"scope": "all", "basis": "revenue", "value": Decimal("5")}], name="cheap")
    rich = _components_rule(db, [{"scope": "all", "basis": "revenue", "value": Decimal("30")}], name="rich")
    prog = BillingProgram(name="P", is_active=True)
    db.add(prog)
    db.flush()
    db.add(BillingProgramDay(program_id=prog.id, weekday=D.weekday(), rule_id=cheap.id))
    vet.billing_program_id = prog.id
    _invoice(db, D, lines=[{"quantity": 1, "unit_price": 100, "line_total": 100}], vets=[vet], rule=rich, total=100)
    assert _commission(db)["veterinarians"][0]["commission"] == 30.0


# --- edge cases ---

def test_cancelled_invoice_excluded(db):
    vet = _vet(db, "cancel")
    rule = _components_rule(db, [{"scope": "all", "basis": "revenue", "value": Decimal("10")}])
    _invoice(db, D, lines=[{"quantity": 1, "unit_price": 100, "line_total": 100}], vets=[vet], rule=rule, total=100, status=InvoiceStatus.CANCELLED)
    assert _commission(db)["total"] == 0.0


def test_invoice_without_vet_ignored(db):
    rule = _components_rule(db, [{"scope": "all", "basis": "revenue", "value": Decimal("10")}])
    _invoice(db, D, lines=[{"quantity": 1, "unit_price": 100, "line_total": 100}], vets=[], rule=rule, total=100)
    assert _commission(db)["veterinarians"] == []


def test_veterinarian_filter(db):
    a, b = _vet(db, "a"), _vet(db, "b")
    rule = _components_rule(db, [{"scope": "all", "basis": "revenue", "value": Decimal("10")}])
    _invoice(db, D, lines=[{"quantity": 1, "unit_price": 100, "line_total": 100}], vets=[a, b], rule=rule, total=100)
    res = _commission(db, veterinarian_id=a.id)
    assert [v["user_id"] for v in res["veterinarians"]] == [a.id]


def test_multi_day_aggregation(db):
    vet = _vet(db, "multi")
    rule = _components_rule(db, [{"scope": "all", "basis": "revenue", "value": Decimal("10")}])
    d2 = date(2026, 7, 2)
    _invoice(db, D, lines=[{"quantity": 1, "unit_price": 100, "line_total": 100}], vets=[vet], rule=rule, total=100, number="F-d1")
    _invoice(db, d2, lines=[{"quantity": 1, "unit_price": 200, "line_total": 200}], vets=[vet], rule=rule, total=200, number="F-d2")
    v = compute_commissions(db, D, d2)["veterinarians"][0]
    assert v["commission"] == 30.0
    assert len(v["by_day"]) == 2


# --- tier edges ---

def test_tier_boundary_inclusive(db):
    vet = _vet(db, "bound")
    rule = _tier_rule(db)
    _invoice(db, D, lines=[{"quantity": 1, "unit_price": 12000, "line_total": 12000}], vets=[vet], rule=rule, total=12000)
    assert _commission(db)["veterinarians"][0]["commission"] == 400.0  # 12000 ≤ 12000


def test_tier_top_open_bracket(db):
    vet = _vet(db, "top")
    rule = _tier_rule(db)
    _invoice(db, D, lines=[{"quantity": 1, "unit_price": 50000, "line_total": 50000}], vets=[vet], rule=rule, total=50000)
    assert _commission(db)["veterinarians"][0]["commission"] == 1000.0


def test_tier_fallback_without_open_top(db):
    vet = _vet(db, "fb")
    rule = BillingRule(name="closed", is_active=True, rule_type="tier", tier_basis="revenue")
    db.add(rule)
    db.flush()
    db.add_all([
        BillingRuleTier(rule_id=rule.id, up_to=Decimal("1000"), amount=Decimal("50")),
        BillingRuleTier(rule_id=rule.id, up_to=Decimal("2000"), amount=Decimal("90")),
    ])
    _invoice(db, D, lines=[{"quantity": 1, "unit_price": 9999, "line_total": 9999}], vets=[vet], rule=rule, total=9999)
    assert _commission(db)["veterinarians"][0]["commission"] == 90.0


def test_tier_empty_means_zero(db):
    vet = _vet(db, "empty")
    rule = BillingRule(name="empty", is_active=True, rule_type="tier", tier_basis="revenue")
    db.add(rule)
    db.flush()
    _invoice(db, D, lines=[{"quantity": 1, "unit_price": 5000, "line_total": 5000}], vets=[vet], rule=rule, total=5000)
    assert _commission(db)["total"] == 0.0


def test_tier_base_split_between_vets(db):
    a, b = _vet(db, "ta"), _vet(db, "tb")
    rule = _tier_rule(db)
    _invoice(db, D, lines=[{"quantity": 1, "unit_price": 26000, "line_total": 26000}], vets=[a, b], rule=rule, total=26000)
    res = _commission(db)
    by = {v["user_id"]: v for v in res["veterinarians"]}
    assert by[a.id]["bonuses"][0]["base"] == 13000.0  # 26000 ÷ 2
    assert by[a.id]["commission"] == 650.0
    assert by[b.id]["commission"] == 650.0
    assert res["total"] == 1300.0
