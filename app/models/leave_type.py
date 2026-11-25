from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.databased import Base


class LeaveType(Base):
    __tablename__ = "leave_types"

    id: Mapped[int] = mapped_column( Integer, primary_key=True, index=True )
    name: Mapped[str] = mapped_column( String(50), unique=True, nullable=False )
    is_active: Mapped[bool] = mapped_column( Boolean, default=True, nullable=False )
    leaves = relationship( "Leave", back_populates="leave_type_detail", )