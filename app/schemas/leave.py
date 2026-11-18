from datetime import date, datetime
from typing import Literal
from pydantic import (BaseModel, ConfigDict, Field, model_validator )

class LeaveCreate(BaseModel):
    leave_type: str = Field(min_length=2, max_length=100)
    start_date: date
    end_date: date
    reason: str = Field(min_length=3)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("End Date Can't be before the Start Date")
        return self


class LeaveDecision(BaseModel):
    status: Literal["ACCEPTED", "REJECTED"]

class LeaveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int 
    employee_id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    status: str
    approved_by: int | None
    created_at: datetime | None = None