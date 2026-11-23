from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

class AttendanceManualCreate(BaseModel):
    employee_id: int
    date: date
    check_in: datetime | None = None
    check_out: datetime | None = None
    status: Literal["PRESENT", "ABSENT", "HALF_DAY", "LATE"] = "PRESENT"   

class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    date: date
    check_in: datetime
    check_out: datetime | None
    status: str
    created_at: datetime | None = None