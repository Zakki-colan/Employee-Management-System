from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.leave import Leave
from app.models.user import User
from app.schemas.auth import UserAccountUpdate, UserRegister, UserLogin
from app.utils.security import (hash_password, verify_password, create_access_token)
from datetime import datetime, timezone
from app.models.refresh_token import RefreshToken
from app.utils.security import ( hash_password, verify_password, create_access_token, create_refresh_token, hash_refresh_token, get_refresh_token_expiry)


def register_user(data: UserRegister, db: Session):
    exister_user = db.query(User).filter(
        (User.email == data.email ) | (User.username == data.username)
    ).first()
    if exister_user: raise HTTPException(status_code=409, detail="The Username or email already exists")
    user = User(username=data.username, email=data.email, hashed_password=hash_password(data.password), role="EMPLOYEE")
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_admin_account(data: UserRegister, db: Session):
    existing_user = db.query(User).filter(
        (User.email == data.email) | (User.username == data.username)
    ).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="The Username or email already exists")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role="ADMIN",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_account(
    user_id: int,
    data: UserAccountUpdate,
    db: Session,
    actor: User,
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role.upper() == "SUPER_ADMIN" and actor.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A Super Admin account cannot be modified by another account",
        )

    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("is_active") is False and actor.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot deactivate your own account",
        )

    if "username" in update_data:
        existing_user = db.query(User).filter(
            User.username == update_data["username"],
            User.id != user_id,
        ).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    if "email" in update_data:
        existing_user = db.query(User).filter(
            User.email == update_data["email"],
            User.id != user_id,
        ).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    password = update_data.pop("password", None)
    if password is not None:
        user.hashed_password = hash_password(password)

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user_account(user_id: int, db: Session, actor: User):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if actor.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot delete your own account",
        )

    if user.role.upper() == "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A Super Admin account cannot be deleted",
        )

    if user.employee:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delete the linked employee profile before deleting this user",
        )

    has_approved_leaves = db.query(Leave.id).filter(
        Leave.approved_by == user_id
    ).first()
    if has_approved_leaves:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user is the approver for leave requests and cannot be deleted",
        )

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


def update_user_role(user_id: int, new_role: str, db: Session, actor: User):
    if actor.role.upper() != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admin can manage user roles")

    valid_roles = {"EMPLOYEE", "ADMIN", "SUPER_ADMIN"}
    normalized_role = new_role.strip().upper()
    if normalized_role not in valid_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user role")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if normalized_role == "SUPER_ADMIN" and actor.id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the Super Admin can hold the SUPER_ADMIN role")

    if user.role.upper() == "SUPER_ADMIN" and actor.id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Another Super Admin cannot be modified by this account")
    if user.id == actor.id and normalized_role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot change your own Super Admin role",
        )

    user.role = normalized_role
    db.commit()
    db.refresh(user)
    return user


def login_user(data: UserLogin, db: Session):
    
    identifier = data.email.casefold()
    user = db.query(User).filter(
        or_(
            func.lower(User.email) == identifier,
            func.lower(User.username) == identifier
        ) ).first()

    if not user or not verify_password(
        data.password,
        user.hashed_password ):
        raise HTTPException( status_code=401, detail="Invalid email or password" )

    if not user.is_active:
        raise HTTPException( status_code=403, detail="Your Account is InActive" )

    try:
        tokens = generate_token_pair(user, db)

        db.commit()

        return {
            "user": { "id": user.id, "username": user.username, "email": user.email, "role": user.role }, **tokens }

    except Exception:
        db.rollback()
        raise
    
def save_refresh_token(user_id: int, token: str, db: Session):
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(token),
        expires_at=get_refresh_token_expiry() )

    db.add(refresh_token)
    db.flush()

    return refresh_token

def generate_token_pair(user: User, db: Session):

    access_token = create_access_token( data={"sub": str(user.id)} )
    refresh_token = create_refresh_token()
    save_refresh_token( user_id=user.id, token=refresh_token, db=db )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
 }

def refresh_access_token(token: str, db: Session):

    token_hash = hash_refresh_token(token)
    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .with_for_update()
        .first() )

    if not stored_token:
        raise HTTPException( status_code=401, detail="Invalid refresh token" )
    now = datetime.now(timezone.utc)

    if stored_token.revoked_at is not None:
        raise HTTPException( status_code=401, detail="Refresh token has been revoked" )
    if stored_token.expires_at <= now:
        raise HTTPException( status_code=401, detail="Refresh token has expired" )
    user = db.query(User).filter( User.id == stored_token.user_id ).first()

    if not user or not user.is_active:
        raise HTTPException( status_code=401, detail="User account is unavailable" )

    stored_token.revoked_at = now

    new_tokens = generate_token_pair(user, db)

    db.commit()

    return new_tokens


def logout_user(token: str, db: Session):
    token_hash = hash_refresh_token(token)
    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .with_for_update()
        .first() )

    if not stored_token:
        raise HTTPException( status_code=401, detail="Invalid refresh token" )

    if stored_token.revoked_at is not None:
        raise HTTPException( status_code=401, detail="Refresh token already revoked" )
    stored_token.revoked_at = datetime.now(timezone.utc)

    db.commit()

    return { "message": "Logout successful" }
