from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from app.models.employee import Employee
from app.models.department import Department
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeePatch,
    EmployeeSelfUpdate,
    EmployeeUpdate,
)


def get_all_employees(db: Session):
    return db.query(Employee).options(
        joinedload(Employee.department)
    ).all()


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
            status_code=409,
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
            status_code=409,
            detail="This Phone number already exists"
        )

    employee = Employee(**data.model_dump())

    db.add(employee)
    db.commit()
    db.refresh(employee)

    return employee


def update_employee(employee_id: int, data: EmployeeUpdate, db: Session):

    employee = get_employee_by_id(employee_id, db)

    department = db.query(Department).filter(
        Department.id == data.department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="This Department is not Found"
        )

    existing_phone = db.query(Employee).filter(
        Employee.phone == data.phone,
        Employee.id != employee_id
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=409,
            detail="This Phone number already exists"
        )

    for key, value in data.model_dump().items():
        setattr(employee, key, value)

    db.commit()
    db.refresh(employee)

    return employee


def patch_employee(employee_id: int, data: EmployeePatch, db: Session):

    employee = get_employee_by_id(employee_id, db)

    update_data = data.model_dump(exclude_unset=True)

    if "department_id" in update_data:

        department = db.query(Department).filter(
            Department.id == update_data["department_id"]
        ).first()

        if not department:
            raise HTTPException(
                status_code=404,
                detail="This Department is not Found"
            )

    if "phone" in update_data:
        existing_phone = db.query(Employee).filter(
            Employee.phone == update_data["phone"],
            Employee.id != employee_id
        ).first()
        if existing_phone:
            raise HTTPException(
                status_code=409,
                detail="This Phone number already exists"
            )

    for key, value in update_data.items():
        setattr(employee, key, value)

    db.commit()
    db.refresh(employee)

    return employee


def update_own_profile(employee_id: int, data: EmployeeSelfUpdate, db: Session):
    employee = get_employee_by_id(employee_id, db)
    update_data = data.model_dump(exclude_unset=True)

    if "phone" in update_data:
        existing_phone = db.query(Employee).filter(
            Employee.phone == update_data["phone"],
            Employee.id != employee_id,
        ).first()
        if existing_phone:
            raise HTTPException(
                status_code=409,
                detail="This Phone number already exists"
            )

    for key, value in update_data.items():
        setattr(employee, key, value)

    db.commit()
    db.refresh(employee)

    return employee


def delete_employee(employee_id: int, db: Session):

    employee = get_employee_by_id(employee_id, db)

    for attendance in list(employee.attendances):
        db.delete(attendance)

    for leave in list(employee.leaves):
        db.delete(leave)

    db.delete(employee)
    db.commit()

    return {"message": "This Employee Deleted Successfully"}
