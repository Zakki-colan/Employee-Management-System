from fastapi import ( APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status,)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
from typing import Annotated
from app.databased import get_db
from app.models.employee_document import EmployeeDocument
from app.models.user import User
from app.schemas.employee_document import EmployeeDocumentResponse
from app.services import employee_document_service
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import get_current_admin
from app.utils.response import success_response

router = APIRouter()


def check_document_access(employee_id: int, current_user: User):
    role = current_user.role.upper()

    if role in {"ADMIN", "SUPER_ADMIN"}:
        return

    if role == "EMPLOYEE":
        if not current_user.employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found",
            )

        if current_user.employee.id != employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access these documents",
            )

        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access documents",
    )


def serialize_document(document: EmployeeDocument, request: Request) -> EmployeeDocumentResponse:
    return EmployeeDocumentResponse(
        id=document.id,
        employee_id=document.employee_id,
        document_name=document.document_name,
        document_type=document.document_type,
        document_url=str(request.url_for("download_document", document_id=document.id)),
        uploaded_at=document.uploaded_at,
    )


@router.post("/employees/{employee_id}/documents")
def upload_document(
    request: Request,
    employee_id: int,
    document_name: Annotated[str, Form()],
    document_type: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    check_document_access(employee_id, current_user)

    document = employee_document_service.upload_employee_document(
        employee_id=employee_id,
        document_name=document_name,
        document_type=document_type,
        file=file,
        db=db,
    )

    document_data = serialize_document(document, request)

    return success_response(
        message="Employee document uploaded successfully",
        data=document_data,
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/employees/{employee_id}/documents")
def get_documents(
    request: Request,
    employee_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    check_document_access(employee_id, current_user)

    documents = employee_document_service.get_employee_documents(
        employee_id,
        db,
    )

    document_data = [serialize_document(document, request) for document in documents]

    return success_response(
        message="Employee documents retrieved successfully",
        data=document_data,
        status_code=status.HTTP_200_OK,
    )


@router.get("/documents/{document_id}")
def get_document(
    request: Request,
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    document = employee_document_service.get_document_by_id(
        document_id,
        db,
    )

    check_document_access(document.employee_id, current_user)

    document_data = serialize_document(document, request)

    return success_response(
        message="Document details retrieved successfully",
        data=document_data,
        status_code=status.HTTP_200_OK,
    )


@router.get("/documents/{document_id}/download", name="download_document")
def download_document(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    document = employee_document_service.get_document_by_id(
        document_id,
        db,
    )

    check_document_access(document.employee_id, current_user)

    if not os.path.isfile(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found",
        )

    return FileResponse(
        path=document.file_path,
        filename=os.path.basename(document.file_path),
    )


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
):
    employee_document_service.delete_employee_document(
        document_id,
        db,
    )

    return success_response(
        message="Employee document deleted successfully",
        data={},
        status_code=status.HTTP_200_OK,
    )
