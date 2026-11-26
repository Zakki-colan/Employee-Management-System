from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Annotated
from app.databased import get_db
from app.dependencies.permissions import get_current_admin
from app.models.user import User
from app.schemas.auth import ( UserLogin, UserRegister, UserResponse, RefreshTokenRequest, LogoutRequest)
from app.services.auth_service import ( register_user, login_user, refresh_access_token, logout_user)
from app.utils.response import success_response


router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    data: UserRegister,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
):
    user = register_user(data, db, admin)
    return success_response(
        message="User registered successfully",
        status_code=status.HTTP_201_CREATED,
        data=UserResponse.model_validate(user).model_dump(mode="json"),
    )


@router.post("/login")
def login( data: UserLogin, db: Annotated[Session, Depends(get_db)]):
    token_data = login_user(data, db)

    return success_response( message="Login successful", status_code=status.HTTP_200_OK, data=token_data )


@router.post("/refresh")
def refresh_token( data: RefreshTokenRequest, db: Annotated[Session, Depends(get_db)]):

    tokens = refresh_access_token( data.refresh_token, db )

    return success_response( message="Token refreshed successfully", status_code=status.HTTP_200_OK, data=tokens )


@router.post("/logout")
def logout( data: LogoutRequest, db: Annotated[Session, Depends(get_db)]):

    result = logout_user( data.refresh_token, db )

    return success_response( message=result["message"], status_code=status.HTTP_200_OK, data={} )