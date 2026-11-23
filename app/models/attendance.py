from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, datetime
from app.databased import Base


class Attendance(Base):
    __tablename__ = "attendances"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column( Integer, ForeignKey("employees.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column( String(20), nullable=False, default="PRESENT" )
    created_at: Mapped[datetime] = mapped_column( DateTime(timezone=True), server_default=func.now() )
    employee = relationship( "Employee", foreign_keys=[employee_id], back_populates="attendances" )

    __table_args__ = (
        Index( "uq_attendances_one_open_session", "employee_id", unique=True, postgresql_where=(check_out.is_(None)), ), )