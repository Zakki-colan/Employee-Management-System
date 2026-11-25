from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.databased import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column( Integer, primary_key=True, index=True )
    
    username: Mapped[str] = mapped_column( String(50), unique=True, nullable=False )
    
    email: Mapped[str] = mapped_column( String(100), unique=True, nullable=False )
    
    hashed_password: Mapped[str] = mapped_column( String(255), nullable=False )
    
    is_active: Mapped[bool] = mapped_column( Boolean, default=True, nullable=False )
    
    role: Mapped[str] = mapped_column( String(50), nullable=False )
    
    employee = relationship( "Employee", back_populates="user", uselist=False )
    
    assigned_leaves = relationship( "Leave", foreign_keys="Leave.assigned_to_user_id", back_populates="assigned_approver")
    
    approved_leaves = relationship( "Leave", foreign_keys="Leave.approved_by", back_populates="approver")
    
    refresh_tokens = relationship( "RefreshToken", back_populates="user" )
    