from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.employee import Employee
from app.models.holiday import Holiday
from app.models.leave import Leave
from app.models.leave_balance import LeaveBalance
from app.models.leave_type import LeaveType
from app.models.user import User
from app.schemas.leave import LeaveCreate, LeaveDecision, LeaveStatus
from app.services.attendance_service import local_now


LEAVE_APPROVER_ROLES = {
    "ADMIN",
    "SUPER_ADMIN",
    "MANAGER",
    "HR",
    "PROJECT_COORDINATOR",
}

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


def get_leave_approvers(requester_id: int, db: Session):
    return (
        db.query(User.id, User.username, User.role)
        .filter(
            User.id != requester_id,
            User.is_active.is_(True),
            func.upper(func.trim(User.role)).in_(LEAVE_APPROVER_ROLES),
        )
        .order_by(User.username, User.id)
        .all()
    )


def validate_leave_approver(approver_id: int, requester_id: int, db: Session):
    approver = db.get(User, approver_id)
    if approver is None:
        raise HTTPException(status_code=404, detail="Approver not found")
    if approver.id == requester_id:
        raise HTTPException(status_code=400, detail="You cannot approve your own leave")
    if not approver.is_active:
        raise HTTPException(status_code=400, detail="Selected approver account is inactive")
    if approver.role.strip().upper() not in LEAVE_APPROVER_ROLES:
        raise HTTPException(
            status_code=400, detail="Selected user is not an authorized leave approver"
        )


class InvalidLeaveType(HTTPException):
    def __init__(self, available_types: dict[int, str]):
        super().__init__(status_code=400, detail="Invalid or inactive leave type ID")
        self.available_types = [
            {"id": type_id, "name": name} for type_id, name in available_types.items()
        ]


def get_available_leave_types(db: Session) -> dict[int, str]:
    active_types = db.query(LeaveType.id, LeaveType.name).filter(
        LeaveType.is_active.is_(True)
    ).order_by(LeaveType.id)
    return {
        type_id: name
        for type_id, name in active_types
        if leave_type_for_balance(name) in DEFAULT_LEAVE_DAYS
    }


def apply_leave(employee_id: int, data: LeaveCreate, db: Session):
    employee = db.query(Employee).filter(
        Employee.id == employee_id
    ).with_for_update().first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="This Employee is not found",
        )

    available_types = get_available_leave_types(db)
    leave_type_name = available_types.get(data.leave_type_id)
    if leave_type_name is None:
        raise InvalidLeaveType(available_types)

    overlapping_leaves = db.query(Leave.id).filter(
        Leave.employee_id == employee_id,
        Leave.start_date <= data.end_date,
        Leave.end_date >= data.start_date,
        Leave.status.in_(["PENDING", "ACCEPTED"]),
    )
    if data.half_day_session is not None:
        overlapping_leaves = overlapping_leaves.filter(
            or_(
                Leave.half_day_session.is_(None),
                Leave.half_day_session == data.half_day_session,
            )
        )

    if overlapping_leaves.first():
        raise HTTPException(
            status_code=400, detail="You already have a leave request for these dates"
        )

    if data.start_date.year != data.end_date.year:
        raise HTTPException(
            status_code=400, detail="Leave requests across different years are not supported"
        )

    leave_days = calculate_leave_days(data.start_date, data.end_date, db)

    if leave_days == 0:
        raise HTTPException(
            status_code=400, detail="Selected dates do not contain any working days"
        )

    if data.half_day_session is not None:
        leave_days = 0.5

    balance_type = leave_type_for_balance(leave_type_name)
    balance = get_leave_balance(employee_id, balance_type, data.start_date.year, db)

    available_days = balance.total_days - balance.used_days

    if leave_days > available_days:
        raise HTTPException(
            status_code=400, detail=f"Insufficient leave balance. Available days: {available_days}"
        )

    validate_leave_approver(data.assigned_to_user_id, employee.user_id, db)

    leave = Leave(
        employee_id=employee_id,
        leave_type_id=data.leave_type_id,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason,
        leave_days=leave_days,
        half_day_session=data.half_day_session,
        status="PENDING",
        assigned_to_user_id=data.assigned_to_user_id,
        approved_by=None,
    )

    db.add(leave)
    db.commit()
    db.refresh(leave)

    return leave


def get_employee_leaves(
    employee_id: int, db: Session, *, status: LeaveStatus | None = None
):
    query = db.query(Leave).options(joinedload(Leave.leave_type_detail)).filter(
        Leave.employee_id == employee_id
    )
    if status is not None:
        query = query.filter(Leave.status == status)
    return query.order_by(Leave.created_at.desc(), Leave.id.desc()).all()


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


def lock_leave_for_balance_change(leave_id: int, db: Session) -> Leave:
    employee_id = db.query(Leave.employee_id).filter(
        Leave.id == leave_id
    ).scalar()
    if employee_id is None:
        raise HTTPException(
            status_code=404,
            detail="Leave request not found",
        )

    db.query(Employee.id).filter(
        Employee.id == employee_id
    ).with_for_update().one()
    leave = db.query(Leave).filter(
        Leave.id == leave_id
    ).with_for_update().first()
    if leave is None:
        raise HTTPException(
            status_code=404,
            detail="Leave request not found",
        )
    return leave


def review_leave(leave_id: int, data: LeaveDecision, approver_user_id: int, db: Session):
    leave = lock_leave_for_balance_change(leave_id, db)
    if leave.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="Leave request has already been reviewed",
        )

    if leave.assigned_to_user_id is None:
        raise HTTPException(
            status_code=400,
            detail="No approver has been assigned to this leave",
        )
    if leave.assigned_to_user_id != approver_user_id:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to review this leave",
        )
    validate_leave_approver(approver_user_id, leave.employee.user_id, db)
    if data.status == "ACCEPTED":
        leave_type = leave_type_for_balance(leave.leave_type)
        if leave_type not in DEFAULT_LEAVE_DAYS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported leave type",
            )
        balance = get_leave_balance(
            leave.employee_id,
            leave_type,
            leave.start_date.year,
            db,
        )
        leave_days = (
            leave.leave_days
            or calculate_leave_days(
                leave.start_date,
                leave.end_date,
                db,
            )
        )

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


def withdraw_leave(leave_id: int, employee_id: int, db: Session) -> Leave:
    leave = lock_leave_for_balance_change(leave_id, db)
    if leave.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="You can only withdraw your own leave")
    if leave.status == "WITHDRAWN":
        return leave
    if leave.status != "ACCEPTED":
        raise HTTPException(status_code=400, detail="Only approved leave can be withdrawn")
    if leave.start_date < local_now().date():
        raise HTTPException(
            status_code=400,
            detail="Approved leave can only be withdrawn on or before its start date",
        )

    balance = db.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_type=leave_type_for_balance(leave.leave_type),
        year=leave.start_date.year,
    ).first()
    if balance is not None:
        days = leave.leave_days or calculate_leave_days(leave.start_date, leave.end_date, db)
        balance.used_days = max(0, balance.used_days - days)

    leave.status = "WITHDRAWN"
    db.commit()
    return leave


def delete_leave(leave_id: int, db: Session):
    leave = db.query(Leave).filter(Leave.id == leave_id).populate_existing().with_for_update().first()

    if not leave:
        raise HTTPException( status_code=404, detail="Your Leave Request is not found" )
    if leave.status.strip().upper() != "PENDING":
        raise HTTPException( status_code=400, detail="Only pending leave requests can be deleted" )

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