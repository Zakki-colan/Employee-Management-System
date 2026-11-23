from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.leave import Leave
from app.models.leave_balance import LeaveBalance
from app.models.employee import Employee
from app.schemas.leave import LeaveBalanceAllocation, LeaveCreate, LeaveDecision
from datetime import timedelta
from app.models.holiday import Holiday


def allocate_leave_balance(data: LeaveBalanceAllocation, db: Session):
    employee = db.query(Employee).filter(Employee.id == data.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="This Employee is not found")

    balance = LeaveBalance(
        employee_id=data.employee_id,
        leave_type=data.leave_type,
        year=data.year,
        total_days=data.total_days,
        used_days=0,
    )
    db.add(balance)

    try:
        db.commit()
        db.refresh(balance)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A leave balance is already allocated for this employee, leave type, and year",
        )

    return balance


def apply_leave(employee_id: int, data: LeaveCreate, db: Session):

    employee = db.query(Employee).filter( Employee.id == employee_id ).first()

    if not employee:
        raise HTTPException( status_code=404, detail="This Employee is not found" )

    existing = db.query(Leave).filter( Leave.employee_id == employee_id, Leave.start_date <= data.end_date, Leave.end_date >= data.start_date, Leave.status.in_(["PENDING", "ACCEPTED"]) ).first()

    if existing:
        raise HTTPException( status_code=409, detail="You already have a leave request for these dates" )

    leave_days = calculate_leave_days( data.start_date, data.end_date, db )

    if leave_days == 0:
        raise HTTPException(
            status_code=400,
            detail="Selected dates do not contain any working days"
        )

    if data.start_date.year != data.end_date.year:
        raise HTTPException(
            status_code=400,
            detail="Leave requests across different years are not supported"
        )

    balance = db.query(LeaveBalance).filter(
    LeaveBalance.employee_id == employee_id,
    LeaveBalance.leave_type == data.leave_type,
    LeaveBalance.year == data.start_date.year
        ).first()

    if not balance:
        raise HTTPException(
            status_code=400,
            detail="Leave balance is not allocated for this leave type"
        )
        
    available_days = balance.total_days - balance.used_days

    if leave_days > available_days:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient leave balance. Available days: {available_days}"
        )

    leave = Leave(
        employee_id=employee_id,
        leave_days=leave_days,
        **data.model_dump()
    )

    db.add(leave)
    db.commit()
    db.refresh(leave)

    return leave

def get_employee_leaves(employee_id: int, db: Session):
    return db.query(Leave).filter( Leave.employee_id == employee_id ).all()

def get_all_leaves(db: Session):
    return db.query(Leave).all()


def review_leave( leave_id: int, data: LeaveDecision, approver_user_id: int, db: Session):

    leave = db.query(Leave).filter( Leave.id == leave_id ).first()

    if not leave:
        raise HTTPException( status_code=404, detail="Your Leave Request is not found" )
    if leave.status != "PENDING":
        raise HTTPException( status_code=409, detail="Your Leave Request has already been reviewed" )
    if data.status.strip().upper() == "ACCEPTED":
        balance = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == leave.employee_id,
            LeaveBalance.leave_type == leave.leave_type,
            LeaveBalance.year == leave.start_date.year
        ).with_for_update().first()
        if not balance:
            raise HTTPException( status_code=404, detail="Leave balance not found" )
        available_days = balance.total_days - balance.used_days
        if leave.leave_days > available_days:
            raise HTTPException( status_code=400, detail=f"Insufficient leave balance. Available days: {available_days}"  )
        balance.used_days += leave.leave_days
    leave.status = data.status
    leave.approved_by = approver_user_id

    try:
        db.commit()
        db.refresh(leave)

    except Exception:
        db.rollback()
        raise

    return leave


def delete_leave(leave_id: int, db: Session):
    leave = db.query(Leave).filter( Leave.id == leave_id ).first()

    if not leave:
        raise HTTPException( status_code=404, detail="Your Leave Request is not found" )
    if leave.status.strip().upper() != "PENDING":
        raise HTTPException( status_code=409, detail="Only pending leave requests can be deleted" )

    db.delete(leave)
    db.commit()

    return { "message": "Your Leave Request Deleted Successfully" }

def get_available_leave(db, employee_id, leave_type, year):
    balance = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee_id,
        LeaveBalance.leave_type == leave_type,
        LeaveBalance.year == year ).first()
    if not balance:
        raise HTTPException( status_code=404, detail="Leave balance not found" )
    return balance.total_days - balance.used_days

def calculate_leave_days(start_date, end_date, db: Session):
    holidays = db.query(Holiday.holiday_date).filter(
        Holiday.holiday_date >= start_date,
        Holiday.holiday_date <= end_date
    ).all()
    holiday_dates = {holiday[0] for holiday in holidays}
    total_days = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5 and current_date not in holiday_dates:
            total_days += 1
        current_date += timedelta(days=1)

    return total_days