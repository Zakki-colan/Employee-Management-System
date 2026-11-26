from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentPatch, DepartmentUpdate


def get_all_departments(db: Session):
    return db.query(Department).all()


def get_department_by_id(department_id: int, db: Session):
    department = db.get(Department, department_id)

    if not department:
        raise HTTPException(status_code=404, detail="This Department is Not Found")
    return department


def create_department(data: DepartmentCreate, db: Session):
    department_data = data.model_dump()
    existing = db.query(Department).filter(
        Department.name == department_data["name"]
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Department Already exists")

    department = Department(**department_data)

    db.add(department)
    db.commit()
    db.refresh(department)

    return department


def update_department(
    department_id: int,
    data: DepartmentUpdate | DepartmentPatch,
    db: Session,
):
    department = get_department_by_id(department_id, db)

    update_data = data.model_dump(exclude_unset=isinstance(data, DepartmentPatch))

    if "name" in update_data:
        existing = db.query(Department).filter(
            Department.name == update_data["name"],
            Department.id != department_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Department name already exists")

    for field, value in update_data.items():
        setattr(department, field, value)

    try:
        db.commit()
        db.refresh(department)
    except Exception:
        db.rollback()
        raise

    return department


def delete_department(department_id: int, db: Session):
    department = get_department_by_id(department_id, db)
    if department.employees:
        raise HTTPException(
            status_code=400, detail="We Cannot Delete This Department with Employees"
        )

    db.delete(department)
    db.commit()

    return {"message": "This Department is Deleted Successfully"}