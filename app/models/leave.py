from datetime import datetime
from sqlalchemy import (String, Integer, DateTime, ForeignKey, Text, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.databased import Base

class Leave(Base):
    __tablename__ = "leaves"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True) 
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[datetime] = mapped_column( DateTime(timezone=True), nullable=False )
    end_date: Mapped[datetime] = mapped_column( DateTime(timezone=True), nullable=False )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending")
    approved_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column( DateTime(timezone=True), server_default=func.now() )
    employee = relationship( "Employee", foreign_keys=[employee_id], back_populates="leaves", )
    approver = relationship("User", foreign_keys=[approved_by], back_populates="approved_leaves")