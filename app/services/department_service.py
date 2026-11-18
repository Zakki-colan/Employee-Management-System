from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate

def get_all_departments(db:Session):
    return db.query(Department).all()

def get_department_by_id(department_id:int, db: Session):
    department = db.query(Department).filter(
        Department.id == department_id
    ).first()
    
    if not department:
        raise HTTPException(status_code=404, detail= "This Department is Not Found")
    return department

def create_department(data: DepartmentCreate, db: Session):

    existing = db.query(Department).filter(
        Department.name == data.name
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Department Already exists"
        )

    department = Department(**data.model_dump())
    
    db.add(department)
    db.commit()
    db.refresh(department)
    
    return department

def update_department(department_id: int, data: DepartmentUpdate, db: Session):
    department = get_department_by_id(department_id, db)
    
    existing = db.query(Department).filter(
            Department.name == data.name,
            Department.id != department_id
        ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail= " This Department Name is Already exists")
    
    department.name = data.name
    department.description = data.description
    db.commit()
    db.refresh(department)
    
    return department

def delete_department(department_id: int, db: Session):
    department = get_department_by_id(department_id, db)
    if department.employees:
        raise HTTPException(status_code=409, detail= "We Cannot Delete This Department with Employees")
    
    db.delete(department)
    db.commit()
    
    return { "message": "This Department is Deleted Successfully"}