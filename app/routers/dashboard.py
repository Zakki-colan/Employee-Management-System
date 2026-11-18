from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Annotated
from app.databased import get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.department import Department
from app.models.leave import Leave
from app.models.attendance import Attendance
from app.dependencies.permissions import get_current_admin

router = APIRouter()

@router.get("/")
def get_dashboard(db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    total_employees = db.query(Employee).count()
    total_departments = db.query(Department).count()
    total_leaves = db.query(Leave).count()
    pending_leaves = db.query(Leave).filter( Leave.status == "Pending" ).count()
    total_attendance = db.query(Attendance).count()

    return { "total_employees": total_employees, "total_departments": total_departments, "total_leaves": total_leaves, "pending_leaves": pending_leaves, "total_attendance_records": total_attendance}