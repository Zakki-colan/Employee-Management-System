from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from typing import Annotated
from app.databased import get_db
from app.models.user import User
from app.schemas.attendance import AttendanceResponse
from app.services import attendance_service
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import get_current_admin
from app.utils.response import success_response

router = APIRouter()

def get_employee_id(current_user: User) -> int:
    if not current_user.employee:
        raise HTTPException( status_code=400, detail="Employee profile not found" )
    return current_user.employee.id


@router.post("/check-in")
def check_in(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]):
    employee_id = get_employee_id(current_user)

    attendance = attendance_service.check_in(employee_id, db)

    attendance_data = AttendanceResponse.model_validate( attendance ).model_dump(mode="json")

    return success_response( message="Check-in successful", data=attendance_data, status_code=status.HTTP_201_CREATED )

@router.post("/check-out")
def check_out(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]):
    employee_id = get_employee_id(current_user)

    attendance = attendance_service.check_out(employee_id, db)

    attendance_data = AttendanceResponse.model_validate( attendance ).model_dump(mode="json")

    return success_response( message="Check-out successful", data=attendance_data, status_code=status.HTTP_200_OK )


@router.get("/my-attendance")
def get_my_attendance(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]):
    employee_id = get_employee_id(current_user)

    attendances = [ attendance for attendance in attendance_service.get_all_attendance(db) if attendance.employee_id == employee_id ]

    attendance_data = [ AttendanceResponse.model_validate(attendance).model_dump( mode="json" ) for attendance in attendances ]

    return success_response( message="Your attendance records retrieved successfully", data=attendance_data, status_code=status.HTTP_200_OK )

@router.get("/")
def get_all_attendance( db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    attendances = attendance_service.get_all_attendance(db)

    attendance_data = [ AttendanceResponse.model_validate(attendance).model_dump( mode="json" ) for attendance in attendances ]

    return success_response( message="All attendance records retrieved successfully", data=attendance_data, status_code=status.HTTP_200_OK )


@router.get("/date/{attendance_date}")
def get_attendance_by_date( attendance_date: date, db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    attendances = attendance_service.get_attendance_by_date( attendance_date, db )

    attendance_data = [ AttendanceResponse.model_validate(attendance).model_dump( mode="json" ) for attendance in attendances ]
    
    return success_response( message="Attendance records retrieved successfully", data=attendance_data, status_code=status.HTTP_200_OK )
