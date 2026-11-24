from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.databased import Base

class EmployeeDocument(Base):
    __tablename__ = "employee_documents"

    id: Mapped[int] = mapped_column( Integer, primary_key=True, index=True )
    employee_id: Mapped[int] = mapped_column( Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False )
    document_name: Mapped[str] = mapped_column( String(150), nullable=False )
    document_type: Mapped[str] = mapped_column( String(50), nullable=False)
    file_path: Mapped[str] = mapped_column( String(255), nullable=False )
    uploaded_at: Mapped[datetime] = mapped_column( DateTime(timezone=True), server_default=func.now(), nullable=False )