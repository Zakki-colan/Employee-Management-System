from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from app.models.employee import Employee
from app.models.department import Department
from app.models.leave_balance import LeaveBalance
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeePatch,
    EmployeeSelfUpdate,
    EmployeeUpdate,
)


def get_all_employees(db: Session, page: int = 1, page_size: int = 10):
    employee_query = (
        db.query(Employee)
        .options(joinedload(Employee.department))
        .order_by(Employee.id)
    )
    total = db.query(Employee).count()
    total_pages = (total + page_size - 1) // page_size

    employees = (
        employee_query
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "next_page": page + 1 if page < total_pages else None,
        "previous_page": (
            min(page - 1, total_pages) if page > 1 and total_pages else None
        ),
        "items": employees,
    }


def get_employee_by_id(employee_id: int, db: Session):
    employee = db.query(Employee).options(
        joinedload(Employee.department)
    ).filter(Employee.id == employee_id).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee is not Found"
        )

    return employee


def create_employee(data: EmployeeCreate, db: Session):

    user = db.query(User).filter(
        User.id == data.user_id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User is not Found")

    if user.employee:
        raise HTTPException(
            status_code=400,
            detail="This User is Already in Employee Profile"
        )

    department = db.query(Department).filter(
        Department.id == data.department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="This Department is not Found"
        )

    existing_phone = db.query(Employee).filter(
        Employee.phone == data.phone
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="This Phone number already exists"
        )

    employee = Employee(**data.model_dump())
    try:
        db.add(employee)
        db.commit()
        db.refresh(employee)

    except Exception:
        db.rollback()
        raise

    return employee



def update_employee(employee_id: int, data: EmployeeUpdate, db: Session):
    return _apply_employee_update(employee_id, data.model_dump(), db)


def patch_employee(employee_id: int, data: EmployeePatch, db: Session):
    return _apply_employee_update(employee_id, data.model_dump(exclude_unset=True), db)


def update_own_profile(employee_id: int, data: EmployeeSelfUpdate, db: Session):
    return _apply_employee_update(employee_id, data.model_dump(exclude_unset=True), db)


def _apply_employee_update(employee_id: int, fields: dict, db: Session):
    employee = get_employee_by_id(employee_id, db)

    if "department_id" in fields and db.get(Department, fields["department_id"]) is None:
        raise HTTPException(status_code=404, detail="Department not found")

    if "phone" in fields:
        existing_phone = db.query(Employee.id).filter(
            Employee.phone == fields["phone"],
            Employee.id != employee_id,
        ).first()
        if existing_phone:
            raise HTTPException(status_code=400, detail="Phone number already exists")

    try:
        for key, value in fields.items():
            setattr(employee, key, value)
        db.commit()
        db.refresh(employee)
    except Exception:
        db.rollback()
        raise
    return employee


def delete_employee(employee_id: int, db: Session):

    employee = get_employee_by_id(employee_id, db)

    try:
        for attendance in employee.attendances:
            db.delete(attendance)

        for leave in employee.leaves:
            db.delete(leave)

        db.query(LeaveBalance).filter_by(employee_id=employee_id).delete()
        db.delete(employee)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"message": "This Employee Deleted Successfully"}
