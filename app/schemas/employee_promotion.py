from datetime import datetime
from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from app.schemas.employee import EmployeePosition


class PromotionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_position: EmployeePosition
    new_salary: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Omit to keep the employee's current salary.",
    )
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class PromotionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    promoted_by_user_id: int | None
    previous_position: str
    new_position: str
    previous_salary: Decimal
    new_salary: Decimal
    reason: str
    promoted_at: datetime
