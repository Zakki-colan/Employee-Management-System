from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Annotated
from app.models.leave import Leave
from app.models.user import User
from app.databased import get_db
from app.schemas.leave import ( LeaveCreate, LeaveDecision, LeaveResponse)
from app.services import leave_service
from app.dependencies.auth import ( get_current_user, get_current_user_optional)
from app.dependencies.permissions import get_current_admin
from app.utils.response import success_response

router = APIRouter()


@router.post("/")
def apply_for_leave( data: LeaveCreate, db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User | None,
        Depends(get_current_user_optional)
    ] = None,):
    if current_user is None:
        raise HTTPException( status_code=401, detail="Authentication required" )

    if not current_user.employee:
        raise HTTPException( status_code=400, detail="Employee profile not found" )

    leave = leave_service.apply_leave( current_user.employee.id, data, db )

    leave_data = LeaveResponse.model_validate( leave ).model_dump(mode="json")

    return success_response( message="Leave application submitted successfully", data=leave_data, status_code=status.HTTP_201_CREATED )


@router.get("/my-leaves")
def get_my_leaves( db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    if not current_user.employee:
        raise HTTPException( status_code=400, detail="Employee profile not found" )

    leaves = leave_service.get_employee_leaves( current_user.employee.id, db )

    leave_data = [ LeaveResponse.model_validate(leave).model_dump(mode="json") for leave in leaves ]

    return success_response( message="Your leave records retrieved successfully", data=leave_data, status_code=status.HTTP_200_OK )


@router.get("/")
def get_all_leaves( db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    leaves = leave_service.get_all_leaves(db)

    leave_data = [ LeaveResponse.model_validate(leave).model_dump(mode="json") for leave in leaves ]

    return success_response( message="All leave records retrieved successfully", data=leave_data, status_code=status.HTTP_200_OK )


@router.patch("/{leave_id}/review")
def review_leave( leave_id: int, data: LeaveDecision, db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):

    leave = leave_service.review_leave( leave_id, data, admin.id, db )

    leave_data = LeaveResponse.model_validate( leave ).model_dump(mode="json")

    return success_response( message="Leave request reviewed successfully", data=leave_data, status_code=status.HTTP_200_OK )


@router.delete("/{leave_id}")
def delete_leave( leave_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    
    leave = db.query(Leave).filter( Leave.id == leave_id ).first()

    if not leave:
        raise HTTPException( status_code=404, detail="Leave request not found" )

    is_admin = current_user.role.upper() in { "ADMIN", "SUPER_ADMIN" }

    is_owner = ( current_user.employee is not None and current_user.employee.id == leave.employee_id )

    if not is_admin and not is_owner:
        raise HTTPException( status_code=403, detail="Permission denied" )

    leave_service.delete_leave(leave_id, db)

    return success_response( message="Leave request deleted successfully", data={}, status_code=status.HTTP_200_OK )