"""Veterinarian commission / billing-rule engine.

An admin builds named **rules** (commission schemes). Each rule is a list of
**components**: a scope (everything / a product category / a specific product),
a basis (% of profit, % of revenue, fixed per unit, fixed per line) and a value.
The most specific matching component wins (product > category > all).

A **program** is a reusable weekly schedule (weekday -> rule) assigned per vet
(``User.billing_program_id``). For a given day a **day override** can replace the
program's rule (changed from the stats page). Commission is computed on the
*encaissé* (paid amounts), attributed to the payment date.
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, Date, DateTime, ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BillingRule(Base):
    __tablename__ = "billing_rules"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    description = Column(String(500))
    is_active = Column(Boolean, default=True)
    # "components": per-line scheme (the default). "tier": a flat bonus picked
    # from brackets of the vet's global revenue/profit over the period.
    rule_type = Column(String(20), nullable=False, default="components")
    tier_basis = Column(String(20))  # tier rules: revenue | profit
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    components = relationship(
        "BillingRuleComponent", back_populates="rule", cascade="all, delete-orphan"
    )
    tiers = relationship(
        "BillingRuleTier", back_populates="rule", cascade="all, delete-orphan"
    )


class BillingRuleComponent(Base):
    __tablename__ = "billing_rule_components"

    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey("billing_rules.id"), nullable=False, index=True)
    scope = Column(String(20), nullable=False, default="all")  # all | category | product
    product_type = Column(String(20))  # scope=category: medication|food|supply|service
    product_id = Column(Integer, ForeignKey("products.id"))  # scope=product
    basis = Column(String(20), nullable=False, default="revenue")  # profit|revenue|per_unit|per_line
    value = Column(Numeric(10, 2), nullable=False, default=0)

    rule = relationship("BillingRule", back_populates="components")


class BillingRuleTier(Base):
    """One bracket of a tier rule: pay ``amount`` when the vet's global
    revenue/profit for the period is ``<= up_to``. ``up_to`` NULL = the top
    bracket ("and above")."""

    __tablename__ = "billing_rule_tiers"

    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey("billing_rules.id"), nullable=False, index=True)
    up_to = Column(Numeric(12, 2))  # null = top bracket
    amount = Column(Numeric(10, 2), nullable=False, default=0)

    rule = relationship("BillingRule", back_populates="tiers")


class BillingProgram(Base):
    __tablename__ = "billing_programs"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    days = relationship(
        "BillingProgramDay", back_populates="program", cascade="all, delete-orphan"
    )


class BillingProgramDay(Base):
    __tablename__ = "billing_program_days"

    id = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey("billing_programs.id"), nullable=False, index=True)
    weekday = Column(Integer, nullable=False)  # 0 = Monday .. 6 = Sunday
    rule_id = Column(Integer, ForeignKey("billing_rules.id"))  # null = no commission that day

    program = relationship("BillingProgram", back_populates="days")

    __table_args__ = (UniqueConstraint("program_id", "weekday", name="uq_program_weekday"),)


class BillingDayOverride(Base):
    """Per-vet, per-day rule override (set from the stats page)."""

    __tablename__ = "billing_day_overrides"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    rule_id = Column(Integer, ForeignKey("billing_rules.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_override_user_date"),)
