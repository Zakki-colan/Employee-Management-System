from datetime import date, datetime
from typing import Literal
from pydantic import Field
from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator
)


class LeaveCreate(BaseModel):
    leave_type: Literal[ "Sick Leave", "Casual Leave", "Annual Leave","Emergency Leave" ]
    start_date: date
    end_date: date
    reason: str = Field( min_length=3, max_length=500 )

    @model_validator(mode="after")
    def validate_dates(self):

        if self.start_date < date.today():
            raise ValueError("Start date cannot be in the past")

        if self.end_date < self.start_date:
            raise ValueError("End date cannot be before the start date")

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


class LeaveListResponse(LeaveResponse):
    reason: str | None
    leave_days: int