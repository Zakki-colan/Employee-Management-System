from sqlalchemy import String, Integer, Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.databased import Base

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column( Integer, primary_key=True, index=True )
    full_name: Mapped[str] = mapped_column("name", String(100), nullable=False)
    phone: Mapped[str] = mapped_column( "phone_number", String(15), unique=True, nullable=False
)
    hire_date: Mapped[Date] = mapped_column(Date, nullable=False)
    position: Mapped[str] = mapped_column(String(100), nullable=False)
    salary: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
    department_id: Mapped[int] = mapped_column( Integer, ForeignKey("departments.id"), nullable=False)
    user_id: Mapped[int] = mapped_column( Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="employee")
    department = relationship("Department", back_populates="employees")
    leaves = relationship( "Leave",foreign_keys="Leave.employee_id", back_populates="employee",)
    attendances = relationship("Attendance", back_populates="employee")
