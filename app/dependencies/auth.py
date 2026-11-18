from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated
from jose import JWTError
from sqlalchemy.orm import Session
from app.databased import get_db
from app.models import User
from app.utils.security import decode_access_token

security = HTTPBearer(auto_error=False)


def _decode_user_from_token(token: str | None, db: Session) -> User | None:
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            return None

        user = db.query(User).filter(User.id == int(user_id)).first()

        if user is None or not user.is_active:
            return None

        return user

    except (ValueError, TypeError, JWTError):
        return None


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security)
    ],
    db: Annotated[Session, Depends(get_db)]
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    token = credentials.credentials if credentials else None

    user = _decode_user_from_token(token, db)

    if user is None:
        raise credentials_exception

    return user


def get_current_user_optional(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security)
    ],
    db: Annotated[Session, Depends(get_db)]
) -> User | None:

    token = credentials.credentials if credentials else None

    return _decode_user_from_token(token, db)
