from typing import Optional
from datetime import date
from pydantic import BaseModel, ConfigDict


# --- Rules ---
class ComponentBase(BaseModel):
    scope: str = "all"               # all | category | product
    product_type: Optional[str] = None   # scope=category: medication|food|supply|service
    product_id: Optional[int] = None     # scope=product
    basis: str = "revenue"           # profit | revenue | per_unit | per_line
    value: float = 0.0


class ComponentResponse(ComponentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True
    components: list[ComponentBase] = []


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    components: list[ComponentResponse] = []


# --- Programs ---
class ProgramDayBase(BaseModel):
    weekday: int                     # 0 = Monday .. 6 = Sunday
    rule_id: Optional[int] = None


class ProgramDayResponse(ProgramDayBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ProgramCreate(BaseModel):
    name: str
    is_active: bool = True
    days: list[ProgramDayBase] = []


class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    is_active: bool
    days: list[ProgramDayResponse] = []


# --- Assignment & overrides ---
class VetProgramAssign(BaseModel):
    program_id: Optional[int] = None


class DayOverrideRequest(BaseModel):
    user_id: int
    date: date
    rule_id: Optional[int] = None    # null -> clear the override
