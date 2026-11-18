from typing import Annotated
from fastapi import Depends, HTTPException, status
from app.models.user import User
from app.dependencies.auth import get_current_user


def require_roles(*allowed_roles: str):
    allowed = {
        role.strip().upper()
        for role in allowed_roles
    }

    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:

        if current_user.role.upper() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )

        return current_user

    return role_checker


get_current_admin = require_roles("ADMIN", "SUPER_ADMIN")
get_current_super_admin = require_roles("SUPER_ADMIN")
get_current_employee = require_roles("EMPLOYEE")