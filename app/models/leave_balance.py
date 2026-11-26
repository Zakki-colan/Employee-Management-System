from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.databased import Base


class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    __table_args__ = (UniqueConstraint("employee_id", "leave_type", "year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True )
    
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False )
    
    leave_type: Mapped[str] = mapped_column(String(50), nullable=False )
    
    total_days: Mapped[int] = mapped_column(Integer, nullable=False)
    
    used_days: Mapped[float] = mapped_column( Numeric(11, 1, asdecimal=False), default=0, nullable=False )
    
    year: Mapped[int] = mapped_column(Integer, nullable=False )