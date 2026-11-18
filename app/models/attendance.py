from sqlalchemy import (String, Integer, Date, DateTime, ForeignKey, Time, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.databased import Base
from datetime import time

class Attendance(Base):
    __tablename__ = "attendances"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    date: Mapped[Date] = mapped_column(Date, nullable=False)
    check_in: Mapped[time] = mapped_column(Time, nullable=False)
    check_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Absent")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="attendances")
    data = None