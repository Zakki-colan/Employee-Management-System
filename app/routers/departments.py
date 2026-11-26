from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.databased import get_db
from app.models.user import User
from app.schemas.department import (
    DepartmentCreate,
    DepartmentPatch,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.services import department_service
from app.dependencies.auth import get_current_user_optional
from app.dependencies.permissions import get_current_admin
from app.utils.response import success_response

router = APIRouter()


@router.get("/")
def get_all_departments( db: Annotated[Session, Depends(get_db)], current_user: Annotated[ User | None, Depends(get_current_user_optional) ] = None,):
    departments = department_service.get_all_departments(db)

    department_data = [
 DepartmentResponse.model_validate(department).model_dump(
            mode="json")
        for department in departments
    ]

    return success_response( message="Departments retrieved successfully", data=department_data, status_code=status.HTTP_200_OK )


@router.get("/{department_id}")
def get_department( department_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[ User | None, Depends(get_current_user_optional) ] = None,):
    department = department_service.get_department_by_id(
        department_id,
        db
    )

    department_data = DepartmentResponse.model_validate( department ).model_dump(mode="json")

    return success_response( message="Department retrieved successfully", data=department_data, status_code=status.HTTP_200_OK )

@router.post("/")
def create_department( data: DepartmentCreate, db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    department = department_service.create_department(data, db)

    department_data = DepartmentResponse.model_validate( department ).model_dump(mode="json")

    return success_response( message="Department created successfully", data=department_data, status_code=status.HTTP_201_CREATED )


@router.put("/{department_id}")
def update_department(
    department_id: int,
    data: DepartmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
):
    department = department_service.update_department(department_id, data, db)
    return success_response(
        message="Department updated successfully",
        data=DepartmentResponse.model_validate(department).model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )


@router.patch("/{department_id}")
def patch_department(
    department_id: int,
    data: DepartmentPatch,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
):
    department = department_service.update_department(department_id, data, db)
    return success_response(
        message="Department updated successfully",
        data=DepartmentResponse.model_validate(department).model_dump(mode="json"),
    )


@router.delete("/{department_id}")
def delete_department( department_id: int, db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    department_service.delete_department(department_id, db)

    return success_response( message="Department deleted successfully", data={}, status_code=status.HTTP_200_OK )