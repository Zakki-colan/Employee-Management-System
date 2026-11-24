from datetime import datetime
from sqlalchemy import ( Integer, String, DateTime, ForeignKey, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.databased import Base

class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id: Mapped[int] = mapped_column( Integer, primary_key=True, index=True )
    user_id: Mapped[int] = mapped_column( Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False )
    token_hash: Mapped[str] = mapped_column( String(64), unique=True, nullable=False, index=True )
    expires_at: Mapped[datetime] = mapped_column( "ecpires_at", DateTime(timezone=True), nullable=False )
    revoked_at: Mapped[datetime | None] = mapped_column( DateTime(timezone=True), nullable=True )
    created_at: Mapped[datetime] = mapped_column( DateTime(timezone=True), server_default=func.now() )
    
    user = relationship( "User", back_populates="refresh_tokens" )