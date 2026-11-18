from typing import Annotated
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.databased import get_db
from app.dependencies.permissions import get_current_admin, get_current_super_admin
from app.models.user import User
from app.schemas.auth import (
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import (
    create_admin_account,
    login_user,
    register_user,
)

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: UserRegister,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
):
    return register_user(data, db)


@router.post("/login",response_model=Token)
def login(data:UserLogin, db:Annotated[Session, Depends(get_db)]):
    return login_user(data, db)

# @router.post("/token", response_model=Token)
# def token(
#     form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
#     db: Annotated[Session, Depends(get_db)],
# ):
#     return login_user(
#         UserLogin(email=form_data.username, password=form_data.password),
#         db,
#     )