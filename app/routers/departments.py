from fastapi import APIRouter, Depends, status, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from app.databased import get_db
from app.models.user import User
from app.schemas.department import (DepartmentUpdate, DepartmentCreate, DepartmentResponse)
from app.services import department_service
from app.dependencies.auth import get_current_user_optional
from app.dependencies.permissions import get_current_admin

router = APIRouter()

@router.get("/", response_model=list[DepartmentResponse])
def get_all_departments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
):
    return department_service.get_all_departments(db)


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
):
    return department_service.get_department_by_id(department_id, db)

@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(data:DepartmentCreate, db:Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    return department_service.create_department(data, db)

@router.put("/{department_id}", response_model=DepartmentResponse)
def update_dapartment(department_id: int, data:DepartmentUpdate, db:Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    return department_service.update_department(department_id, data, db)

@router.delete("/{department_id}")
def delete_department(department_id: int, db:Annotated[Session,Depends(get_db)], admin: Annotated[User,Depends(get_current_admin)]):
    return department_service.delete_department(department_id,db)