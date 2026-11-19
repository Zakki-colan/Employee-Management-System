from datetime import date, datetime, time
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.attendance import Attendance
from app.models.employee import Employee


def check_in(employee_id: int, db: Session):
    employee = db.query(Employee).filter(
        Employee.id == employee_id
    ).first()
    if not employee:
        raise HTTPException( status_code=404, detail="Employee Not Found" )
    today = date.today()
     
    attendance = db.query(Attendance).filter( Attendance.employee_id == employee_id, Attendance.date == today, Attendance.check_out.is_(None) ).first()

    if attendance:
        raise HTTPException( status_code=409, detail="Please complete your previous check-out first." )

    current_time = datetime.now().time().replace(microsecond=0)

    attendance = Attendance( employee_id=employee_id, date=today, check_in=current_time, status="PRESENT" )

    db.add(attendance)
    db.commit()
    db.refresh(attendance)

    return attendance

def check_out(employee_id: int, db: Session):

    today = date.today()

    attendance = db.query(Attendance).filter( Attendance.employee_id == employee_id, Attendance.date == today, Attendance.check_out.is_(None) ).order_by(Attendance.id.desc()).first()

    if not attendance:
        raise HTTPException( status_code=404, detail="No active check-in found." )

    attendance.check_out = datetime.now().time().replace( microsecond=0 )

    db.commit()
    db.refresh(attendance)

    return attendance

def get_all_attendance(db:Session):
    
    return db.query(Attendance).order_by(
            Attendance.date.desc()
        ).all()
    
def get_attendance_by_date( attendance_date: date, db:Session):
    return db.query(Attendance).filter(
        Attendance.date == attendance_date
    ).all()
