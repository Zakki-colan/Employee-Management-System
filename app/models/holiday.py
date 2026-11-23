from datetime import date
from sqlalchemy import Integer, String, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.databased import Base

class Holiday(Base):

    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column( Integer, primary_key=True, index=True )
    holiday_name: Mapped[str] = mapped_column( String(100), nullable=False )
    holiday_date: Mapped[date] = mapped_column( Date, nullable=False, unique=True )