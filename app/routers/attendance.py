from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import Annotated
from app.databased import get_db
from app.models.user import User
from app.schemas.attendance import AttendanceResponse
from app.services import attendance_service
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import get_current_admin

router = APIRouter()

def get_employee_id(current_user: User) -> int:
    if not current_user.employee:
        raise HTTPException( status_code=400, detail="Employee profile not found" )

    return current_user.employee.id

@router.post("/check-in", response_model=AttendanceResponse)
def check_in( db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    employee_id = get_employee_id(current_user)

    return attendance_service.check_in(employee_id, db)

@router.post("/check-out", response_model=AttendanceResponse)
def check_out( db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    employee_id = get_employee_id(current_user)

    return attendance_service.check_out(employee_id, db)

@router.get("/my-attendance", response_model=list[AttendanceResponse])
def get_my_attendance( db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    employee_id = get_employee_id(current_user)

    return [
        attendance
        for attendance in attendance_service.get_all_attendance(db)
        if attendance.employee_id == employee_id
    ]

@router.get("/", response_model=list[AttendanceResponse])
def get_all_attendance( db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    return attendance_service.get_all_attendance(db)

@router.get("/date/{attendance_date}", response_model=list[AttendanceResponse])
def get_attendance_by_date( attendance_date: date, db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    return attendance_service.get_attendance_by_date( attendance_date, db )