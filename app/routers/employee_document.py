import os
from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, UploadFile, status, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.databased import get_db
from app.models.user import User
from app.schemas.employee_document import EmployeeDocumentResponse
from app.services import employee_document_service
from app.dependencies.auth import get_current_user
from app.utils.response import success_response

router = APIRouter()

def check_document_access(employee_id: int, current_user:User):
    role = current_user.role.upper()
    
    if role in ["ADMIN", "SUPER_ADMIN"]:
        return
    
    if role == "EMPLOYEE":
        if not current_user.employee:
            raise HTTPException(status_code=404, detail="Employee Profile is not found", )
        if current_user.employee.id != employee_id:
            raise HTTPException(status_code=403, detail= "Your Not Authorized to access this Employee's Documents")
        return
    raise HTTPException(status_code=403, detail="You don't have Permission to Access Documents")

@router.post("/employees/{employee_id}/documents")
def upload_document(
    employee_id: int,
    document_name: Annotated[str, Form()],
    document_type: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    check_document_access(employee_id, current_user)
    
    document = employee_document_service.upload_employee_document( employee_id=employee_id, document_name=document_name, document_type=document_type, file=file, db=db)
   
    document_date = EmployeeDocumentResponse.model_validate(document).model_dump(mode="json")
    
    return success_response(message="Employee Document Uploded Successfully", data=document_date, status_code=status.HTTP_201_CREATED)

@router.get("/employees,{employee_id}/documents")
def get_documents(
    employee_id: int, db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)] 
):
    check_document_access(employee_id, current_user)
    
    documents = employee_document_service.get_employee_documents(employee_id, db)
    
    document_data = [EmployeeDocumentResponse.model_validate(document).model_dump(mode="json") for document in documents]
    
    return success_response(message="Employee document retrieved successfully", data=document_data, status_code=status.HTTP_200_OK)

@router.get("documents/{document_id}")
def get_document(document_id: int,db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    document = employee_document_service.get_document_by_id(
        document_id, db
    )
    check_document_access(document.employee_id, current_user)
    
    document_data = EmployeeDocumentResponse.model_validate(document).model_dump(mode="json")
    
    return success_response( message="Document Details retrieved successfully", data=document_data, status_code=status.HTTP_200_OK)
    
@router.get("/documents/{document_id}/download")
def download_document(
    document_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User,Depends(get_current_user)]
):
    document = employee_document_service.get_document_by_id(document_id, db)
    check_document_access(document.employee_id, current_user)
    
    if not os.path.isfile(document.file_path):
        raise HTTPException(status_code=404, detail=" Document File is Not Found")
    return FileResponse(path=document.file_path, filename=os.path.basename(document.file_path))

@router.delete("/document/{document_id}")
def delete_document(
    document_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User,Depends(get_current_user)]
):
    document = employee_document_service.get_document_by_id(
        document_id, db
    )
    check_document_access(document.employee_id, current_user)
    employee_document_service.delete_employee_document(document_id, db)
    
    return success_response(
        message=" Employee Document Deleted Successfully", data={}, status_code=status.HTTP_200_OK
    )
    