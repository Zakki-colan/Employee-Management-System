from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.databased import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import get_current_admin
from app.models.user import User
from app.schemas.employee_promotion import PromotionCreate, PromotionResponse
from app.services import employee_promotion_service
from app.utils.response import success_response


router = APIRouter()
EmployeeId = Annotated[int, Path(gt=0)]


@router.post("/{employee_id}/promotions", status_code=status.HTTP_201_CREATED)
def promote_employee(
    employee_id: EmployeeId,
    data: PromotionCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
):
    """Apply a promotion immediately and record the previous position and salary."""
    promotion = employee_promotion_service.promote_employee(employee_id, data, admin.id, db)
    return success_response(
        message="Employee promoted successfully",
        data=PromotionResponse.model_validate(promotion).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/{employee_id}/promotions")
def get_promotion_history(
    employee_id: EmployeeId,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """List an employee's promotions, most recent first."""
    role = current_user.role.upper()
    if role not in {"ADMIN", "SUPER_ADMIN"} and (
        role != "EMPLOYEE" or current_user.employee is None or current_user.employee.id != employee_id
    ):
        raise HTTPException(403, "You are not authorized to view this promotion history")

    promotions, has_next_page = employee_promotion_service.get_promotion_history(
        employee_id, db, page=page, page_size=page_size
    )
    return success_response(
        message="Promotion history retrieved successfully",
        data=[
            PromotionResponse.model_validate(promotion).model_dump(mode="json")
            for promotion in promotions
        ],
        meta={
            "page": page,
            "page_size": page_size,
            "next_page": page + 1 if has_next_page else None,
        },
    )
