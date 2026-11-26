from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


LeaveStatus = Literal["PENDING", "ACCEPTED", "REJECTED", "WITHDRAWN"]
LeaveHistoryStatus = Literal["ALL", LeaveStatus]
HalfDaySession = Literal[1, 2]


class LeaveCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leave_type_id: int = Field(description="Use an active ID from GET /leaves/types.")
    start_date: date
    end_date: date
    reason: str = Field(min_length=3, max_length=500)
    half_day_session: HalfDaySession | None = Field(
        default=None,
        description="Choose 1 for Session 1 or 2 for Session 2. Omit for full-day leave.",
    )
    assigned_to_user_id: int = Field(
        gt=0,
        description="User ID of the approver. Choose an ID from GET /leaves/approvers.",
    )

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date < date.today():
            raise ValueError("Start date cannot be in the past")

        if self.end_date < self.start_date:
            raise ValueError("End date cannot be before the start date")

        if self.half_day_session is not None and self.start_date != self.end_date:
            raise ValueError("Half-day leave must start and end on the same date")

        return self


class LeaveDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ACCEPTED", "REJECTED"]


class LeaveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    leave_type_id: int
    leave_type: str
    start_date: date
    end_date: date
    leave_days: float
    half_day_session: HalfDaySession | None
    reason: str | None
    status: str
    assigned_to_user_id: int | None
    approved_by: int | None
    created_at: datetime | None = None
