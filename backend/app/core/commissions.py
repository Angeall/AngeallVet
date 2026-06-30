"""Commission computation on the *encaissé* (paid amounts).

For every payment in the period (by ``payment_date``):
  - it belongs to an invoice; fraction paid = payment.amount / invoice.total;
  - the invoice is shared between its veterinarians -> each gets 1/N;
  - for each invoice line, the day's rule picks the most specific component and
    computes a commission (profit / revenue / per-unit / per-line);
  - that line commission is scaled by the paid fraction and the vet's share.

The day's rule for a vet is the per-day override, else the vet's weekly program
slot for that weekday, else none (no commission).
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.models.user import User
from app.models.inventory import Product
from app.models.billing import Invoice, Payment, InvoiceStatus
from app.models.billing_rules import BillingRule, BillingProgramDay, BillingDayOverride

ZERO = Decimal("0")


def _d(v) -> Decimal:
    return Decimal(str(v)) if v is not None else ZERO


def line_category(line, product) -> str:
    """Classify a line. A line without a product is treated as an act (service)."""
    if product is not None:
        pt = product.product_type
        return pt.value if hasattr(pt, "value") else str(pt)
    return "service"


def pick_component(components, line, category):
    """Most specific matching component wins: product > category > all."""
    chosen, chosen_rank = None, 0
    for c in components:
        if c.scope == "product" and line.product_id is not None and c.product_id == line.product_id:
            rank = 3
        elif c.scope == "category" and c.product_type == category:
            rank = 2
        elif c.scope == "all":
            rank = 1
        else:
            continue
        if rank > chosen_rank:
            chosen, chosen_rank = c, rank
    return chosen


def line_commission(line, component, product) -> Decimal:
    """Commission on a line for a component, before share / paid fraction."""
    if component is None:
        return ZERO
    value = _d(component.value)
    qty = _d(line.quantity)
    line_total = _d(line.line_total)  # HT, after discount
    if component.basis == "profit":
        cost = _d(product.purchase_price) * qty if product else ZERO
        return (line_total - cost) * value / 100
    if component.basis == "revenue":
        return line_total * value / 100
    if component.basis == "per_unit":
        return value * qty
    if component.basis == "per_line":
        return value
    return ZERO


def tier_line_base(line, product, basis: str) -> Decimal:
    """The base a line contributes to a tier rule: HT revenue, or margin (profit)."""
    line_total = _d(line.line_total)  # HT, after discount
    if basis == "profit":
        cost = _d(product.purchase_price) * _d(line.quantity) if product else ZERO
        return line_total - cost
    return line_total  # revenue


def tier_bonus(tiers, base: Decimal) -> Decimal:
    """Flat amount for the bracket the base falls into.

    Tiers are ordered by ``up_to`` ascending (NULL = top bracket, sorted last);
    the first tier with ``base <= up_to`` (or the NULL/top tier) wins. A base
    above every finite threshold with no NULL tier falls back to the highest.
    """
    ordered = sorted(tiers, key=lambda t: (t.up_to is None, _d(t.up_to)))
    if not ordered:
        return ZERO
    for t in ordered:
        if t.up_to is None or base <= _d(t.up_to):
            return _d(t.amount)
    return _d(ordered[-1].amount)


def resolve_rule_id(db: Session, user: User, on_date) -> Optional[int]:
    """The rule that applies to a vet on a date: day override > program slot > none."""
    override = (
        db.query(BillingDayOverride)
        .filter(BillingDayOverride.user_id == user.id, BillingDayOverride.date == on_date)
        .first()
    )
    if override:
        return override.rule_id
    if user.billing_program_id:
        day = (
            db.query(BillingProgramDay)
            .filter(
                BillingProgramDay.program_id == user.billing_program_id,
                BillingProgramDay.weekday == on_date.weekday(),
            )
            .first()
        )
        if day:
            return day.rule_id
    return None


def compute_commissions(db: Session, date_from, date_to, veterinarian_id: Optional[int] = None):
    payments = (
        db.query(Payment)
        .filter(Payment.payment_date >= date_from, Payment.payment_date <= date_to)
        .all()
    )
    if not payments:
        return {"veterinarians": [], "total": 0.0}

    invoice_ids = {p.invoice_id for p in payments}
    invoices = (
        db.query(Invoice)
        .options(selectinload(Invoice.lines), selectinload(Invoice.veterinarians))
        .filter(Invoice.id.in_(invoice_ids))
        .all()
    )
    inv_map = {inv.id: inv for inv in invoices}

    product_ids = {l.product_id for inv in invoices for l in inv.lines if l.product_id}
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids))} if product_ids else {}

    rule_cache, user_cache, resolve_cache = {}, {}, {}

    def get_rule(rid):
        if rid is None:
            return None
        if rid not in rule_cache:
            rule_cache[rid] = (
                db.query(BillingRule)
                .options(selectinload(BillingRule.components), selectinload(BillingRule.tiers))
                .filter(BillingRule.id == rid).first()
            )
        return rule_cache[rid]

    def get_user(uid):
        if uid not in user_cache:
            user_cache[uid] = db.query(User).filter(User.id == uid).first()
        return user_cache[uid]

    def resolve(user, on_date):
        key = (user.id, on_date)
        if key not in resolve_cache:
            resolve_cache[key] = resolve_rule_id(db, user, on_date)
        return resolve_cache[key]

    agg = {}
    # Tier rules accrue a global base per (vet, rule); the flat bonus is applied
    # once, after the period is fully accumulated.
    tier_acc = {}

    for p in payments:
        inv = inv_map.get(p.invoice_id)
        if not inv or inv.status == InvoiceStatus.CANCELLED:
            continue
        total = _d(inv.total)
        if total <= 0:
            continue
        fraction = _d(p.amount) / total
        vets = list(inv.veterinarians)
        if not vets:
            continue
        share = Decimal(1) / Decimal(len(vets))

        for iv in vets:
            if veterinarian_id is not None and iv.user_id != veterinarian_id:
                continue
            user = get_user(iv.user_id)
            if not user:
                continue
            rid = resolve(user, p.payment_date)
            rule = get_rule(rid)
            paid_share = _d(p.amount) * share

            commission = ZERO
            if rule is not None and rule.rule_type == "tier":
                # Accrue the global base (HT revenue or margin) on the encaissé;
                # the bracket bonus is applied once after the loop.
                basis = rule.tier_basis or "revenue"
                base = ZERO
                for line in inv.lines:
                    base += tier_line_base(line, products.get(line.product_id), basis)
                ta = tier_acc.setdefault((iv.user_id, rid), {"base": ZERO, "rule": rule})
                ta["base"] += base * fraction * share
            else:
                components = rule.components if rule else []
                for line in inv.lines:
                    product = products.get(line.product_id)
                    comp = pick_component(components, line, line_category(line, product))
                    commission += line_commission(line, comp, product)
                commission = commission * fraction * share

            a = agg.setdefault(iv.user_id, {
                "user_id": iv.user_id,
                "name": f"{user.first_name} {user.last_name}",
                "commission": ZERO, "paid": ZERO, "by_day": {},
            })
            a["commission"] += commission
            a["paid"] += paid_share
            day_key = p.payment_date.isoformat()
            d = a["by_day"].setdefault(day_key, {
                "date": day_key, "rule_id": rid,
                "rule_name": rule.name if rule else None,
                "commission": ZERO, "paid": ZERO,
            })
            d["commission"] += commission
            d["paid"] += paid_share

    # Apply the tier bonuses now the global base per (vet, rule) is complete.
    for (uid, rid), ta in tier_acc.items():
        a = agg.get(uid)
        if a is None:
            continue
        rule = ta["rule"]
        bonus = tier_bonus(rule.tiers, ta["base"])
        a["commission"] += bonus
        a.setdefault("bonuses", []).append({
            "rule_id": rid,
            "rule_name": rule.name,
            "basis": rule.tier_basis or "revenue",
            "base": round(float(ta["base"]), 2),
            "amount": round(float(bonus), 2),
        })

    vets_out = []
    grand = ZERO
    for a in agg.values():
        grand += a["commission"]
        vets_out.append({
            "user_id": a["user_id"],
            "name": a["name"],
            "commission": round(float(a["commission"]), 2),
            "paid": round(float(a["paid"]), 2),
            "bonuses": a.get("bonuses", []),
            "by_day": sorted(
                ({**d, "commission": round(float(d["commission"]), 2), "paid": round(float(d["paid"]), 2)}
                 for d in a["by_day"].values()),
                key=lambda x: x["date"],
            ),
        })
    vets_out.sort(key=lambda x: x["commission"], reverse=True)
    return {"veterinarians": vets_out, "total": round(float(grand), 2)}
