from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.leave import Leave
from app.models.leave_balance import LeaveBalance
from app.models.employee import Employee
from app.schemas.leave import LeaveCreate, LeaveDecision
from datetime import date, timedelta
from app.models.holiday import Holiday


# Annual allowances in working days, used when an employee has no saved balance.
DEFAULT_LEAVE_DAYS = {
    "Annual Leave": 20,
    "Casual Leave": 12,
    "Emergency Leave": 5,
    "Sick Leave": 10,
}


def leave_type_for_balance(leave_type: str) -> str:
    legacy_types = {name.removesuffix(" Leave"): name for name in DEFAULT_LEAVE_DAYS}
    return legacy_types.get(leave_type, leave_type)


def default_leave_balance(
    employee_id: int, leave_type: str, year: int, leaves: list[Leave], db: Session
) -> LeaveBalance:
    used_days = sum(
        leave.leave_days or calculate_leave_days(leave.start_date, leave.end_date, db)
        for leave in leaves
        if leave.status == "ACCEPTED"
        and leave.start_date.year == year
        and leave_type_for_balance(leave.leave_type) == leave_type
    )
    return LeaveBalance(
        employee_id=employee_id,
        leave_type=leave_type,
        year=year,
        total_days=DEFAULT_LEAVE_DAYS[leave_type],
        used_days=used_days,
    )


def get_leave_balance(
    employee_id: int, leave_type: str, year: int, db: Session
) -> LeaveBalance:
    balance = db.query(LeaveBalance).filter_by(
        employee_id=employee_id, leave_type=leave_type, year=year
    ).first()
    if balance is not None:
        return balance

    accepted_leaves = db.query(Leave).filter(
        Leave.employee_id == employee_id,
        Leave.status == "ACCEPTED",
        Leave.start_date >= date(year, 1, 1),
        Leave.start_date <= date(year, 12, 31),
    ).all()
    return default_leave_balance(employee_id, leave_type, year, accepted_leaves, db)

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

    balance = get_leave_balance(employee_id, data.leave_type, data.start_date.year, db)

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

def get_employee_leave_balances(
    employee_id: int, leaves: list[Leave], db: Session
) -> list[LeaveBalance]:
    balances = {
        (balance.year, balance.leave_type): balance
        for balance in db.query(LeaveBalance).filter_by(employee_id=employee_id)
    }
    years = {date.today().year, *(leave.start_date.year for leave in leaves)}
    for year in years:
        for leave_type in DEFAULT_LEAVE_DAYS:
            if (year, leave_type) not in balances:
                balances[year, leave_type] = default_leave_balance(
                    employee_id, leave_type, year, leaves, db
                )
    return sorted(balances.values(), key=lambda balance: (-balance.year, balance.leave_type))

def get_all_leaves(db: Session):
    return db.query(Leave).all()


def review_leave( leave_id: int, data: LeaveDecision, approver_user_id: int, db: Session):

    employee_id = db.query(Leave.employee_id).filter(Leave.id == leave_id).scalar()
    if employee_id is None:
        raise HTTPException(status_code=404, detail="Your Leave Request is not found")

    # Serialize approvals for the employee, including the first use of an allowance.
    db.query(Employee.id).filter(Employee.id == employee_id).with_for_update().one()
    leave = db.query(Leave).filter(Leave.id == leave_id).with_for_update().first()
    if leave is None:
        raise HTTPException(status_code=404, detail="Your Leave Request is not found")
    if leave.status != "PENDING":
        raise HTTPException(status_code=409, detail="Your Leave Request has already been reviewed")
    if data.status == "ACCEPTED":
        leave_type = leave_type_for_balance(leave.leave_type)
        if leave_type not in DEFAULT_LEAVE_DAYS:
            raise HTTPException(status_code=400, detail="Unsupported leave type")
        balance = get_leave_balance(employee_id, leave_type, leave.start_date.year, db)
        leave_days = leave.leave_days or calculate_leave_days(leave.start_date, leave.end_date, db)
        available_days = balance.total_days - balance.used_days
        if leave_days > available_days:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient leave balance. Available days: {available_days}",
            )
        balance.used_days += leave_days
        db.add(balance)
        leave.leave_days = leave_days
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