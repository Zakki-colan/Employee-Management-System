from datetime import datetime, date
from sqlalchemy import (
    CheckConstraint, String, Integer, Numeric, DateTime, Date, ForeignKey, Text, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.databased import Base

class Leave(Base):
    __tablename__ = "leaves"
    __table_args__ = (
        CheckConstraint(
            "half_day_session IS NULL OR "
            "(half_day_session IN (1, 2) AND start_date = end_date AND leave_days = 0.5)",
            name="ck_leaves_half_day_session",
        ),
    )

    id: Mapped[int] = mapped_column( Integer, primary_key=True, index=True )

    employee_id: Mapped[int] = mapped_column( Integer, ForeignKey("employees.id"), nullable=False )

    leave_type_id: Mapped[int] = mapped_column( Integer, ForeignKey("leave_types.id"), nullable=False )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    leave_days: Mapped[float] = mapped_column(
        Numeric(11, 1, asdecimal=False), nullable=False, default=0, server_default="0"
    )
    half_day_session: Mapped[int | None] = mapped_column(Integer, nullable=True)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column( String(20), nullable=False, default="PENDING" )

    assigned_to_user_id: Mapped[int | None] = mapped_column( Integer, ForeignKey("users.id"), nullable=True )

    approved_by: Mapped[int | None] = mapped_column( Integer, ForeignKey("users.id"), nullable=True )

    created_at: Mapped[datetime] = mapped_column( DateTime(timezone=True), server_default=func.now() )

    employee = relationship( "Employee", foreign_keys=[employee_id], back_populates="leaves" )

    leave_type_detail = relationship( "LeaveType", back_populates="leaves" )

    assigned_approver = relationship( "User", foreign_keys=[assigned_to_user_id], back_populates="assigned_leaves" )

    approver = relationship( "User", foreign_keys=[approved_by], back_populates="approved_leaves" )

    @property
    def leave_type(self) -> str:
        return self.leave_type_detail.name
