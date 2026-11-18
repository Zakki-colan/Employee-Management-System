from datetime import date, datetime, time
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.attendance import Attendance
from app.models.employee import Employee

def check_in(employee_id: int, db:Session):
    employee = db.query(Employee).filter(
        Employee.id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail= "Employee Not Found")
    today = date.today()
    
    attendance = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.date == today
    ).first()
    
    if attendance:
        raise HTTPException(status_code=409, detail="Todays Attendance is Already Recorded")
    
    current_time = datetime.now().time().replace(microsecond=0)
    attendance =  Attendance(employee_id=employee_id, date=today, check_in=current_time, status="PRESENT")
    
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    
    return attendance

def check_out(employee_id: int, db:Session):
    today = date.today()
    attendance = db.query(Attendance).filter(
        Attendance.employee_id == employee_id, Attendance.date == today
    ).first()
    
    if not attendance:
        raise HTTPException(status_code=404, detail= "Kindly complete the check-in first.")
    if attendance.check_out is not None:
        raise HTTPException(status_code=409, detail="Already Chech Out")
    
    attendance.check_out = datetime.now().time().replace(microsecond=0)
    
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
