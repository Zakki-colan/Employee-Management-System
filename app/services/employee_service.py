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


def get_all_employees(db: Session, page: int = 1, page_size: int = 10):
    query = db.query(Employee)
    total = query.count()
    total_pages = (total + page_size - 1) // page_size

    employees = []
    if page <= total_pages:
        employees = ( query.options(joinedload(Employee.department)) .order_by(Employee.id) .offset((page - 1) * page_size) .limit(page_size) .all() )

    return { "total": total, "page": page, "page_size": page_size, "total_pages": total_pages, "next_page": page + 1 if page < total_pages else None, "previous_page": min(page - 1, total_pages) if page > 1 and total_pages else None, "items": employees, }


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



def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session
):
    employee = get_employee_by_id(employee_id, db)

    department = db.query(Department).filter(
        Department.id == data.department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # Check duplicate phone
    existing_phone = db.query(Employee).filter(
        Employee.phone == data.phone,
        Employee.id != employee_id
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Phone number already exists"
        )

    # Replace all updateable fields
    update_data = data.model_dump()

    try:
        for key, value in update_data.items():
            setattr(employee, key, value)

        db.commit()
        db.refresh(employee)

    except Exception:
        db.rollback()
        raise

    return employee



def patch_employee(
    employee_id: int,
    data: EmployeePatch,
    db: Session
):
    employee = get_employee_by_id(employee_id, db)

    # Get only the fields sent by frontend
    update_data = data.model_dump(exclude_unset=True)

    if "department_id" in update_data:
        department = db.query(Department).filter(
            Department.id == update_data["department_id"]
        ).first()

        if not department:
            raise HTTPException(
                status_code=404,
                detail="Department not found"
            )

    if "phone" in update_data:
        existing_phone = db.query(Employee).filter(
            Employee.phone == update_data["phone"],
            Employee.id != employee_id
        ).first()

        if existing_phone:
            raise HTTPException(
                status_code=400,
                detail="Phone number already exists"
            )

    try:
        for key, value in update_data.items():
            setattr(employee, key, value)

        db.commit()
        db.refresh(employee)

    except Exception:
        db.rollback()
        raise

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
                status_code=400,
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
