from fastapi import APIRouter, Depends, status, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from app.databased import get_db
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeePatch,
    EmployeeResponse,
    EmployeeSelfUpdate,
    EmployeeUpdate,
    EmployeePosition,
)
from app.services import employee_service
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import get_current_admin, get_current_employee

router = APIRouter()

@router.get("/", response_model=list[EmployeeResponse])
def get_employees( db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)],):
    return employee_service.get_all_employees(db)


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee_by_id(employee_id: int,db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    employee = employee_service.get_employee_by_id(employee_id, db)

    if not employee:
        raise HTTPException( status_code=404, detail="Employee not found" )

    role = current_user.role.upper()
    if role == "EMPLOYEE":

        if not current_user.employee:
            raise HTTPException( status_code=404, detail="Employee profile not found")

        if current_user.employee.id != employee_id:
            raise HTTPException( status_code=403, detail="You are not authorized to view employee profiles" )
    elif role not in {"ADMIN", "SUPER_ADMIN"}:
        raise HTTPException( status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to view employee profiles" )

    return employee


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee( employee_id: int, data: EmployeeUpdate, db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    return employee_service.update_employee(employee_id, data, db)

@router.post( "/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee( data: EmployeeCreate, db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    return employee_service.create_employee(data, db)

@router.patch("/me", response_model=EmployeeResponse)
def update_my_profile( data: EmployeeSelfUpdate, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    
    if not current_user.employee:
        raise HTTPException( status_code=404, detail="Employee profile not found" )
    return employee_service.update_own_profile( current_user.employee.id, data, db )
@router.delete("/{employee_id}")
def delete_employee( employee_id: int, db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    return employee_service.delete_employee(employee_id, db)