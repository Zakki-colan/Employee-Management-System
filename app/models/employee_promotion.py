from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.databased import Base


class EmployeePromotion(Base):
    __tablename__ = "employee_promotions"
    __table_args__ = (Index("ix_employee_promotions_employee_history", "employee_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    promoted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    previous_position: Mapped[str] = mapped_column(String(100))
    new_position: Mapped[str] = mapped_column(String(100))
    previous_salary: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    new_salary: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    reason: Mapped[str] = mapped_column(String(500))
    promoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
