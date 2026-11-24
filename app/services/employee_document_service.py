import os
import time
from pathlib import Path
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.models.employee import Employee
from app.models.employee_document import EmployeeDocument


UPLOAD_FOLDER = "uploads/employee_documents"
ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx"]
MAX_FILE_SIZE = 5 * 1024 * 1024

def upload_employee_document(
    employee_id: int,
    document_name: str,
    document_type: str,
    file: UploadFile,
    db: Session
):
    employee = db.query(Employee).filter( Employee.id == employee_id ).first()

    if not employee:
        raise HTTPException( status_code=404, detail="Employee not found" )

    file_extension = Path(file.filename or "").suffix.lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException( status_code=400, detail="File type is not allowed" )

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException( status_code=400, detail="File size cannot exceed 5 MB" )

    original_filename = Path(file.filename or "document").name
    safe_filename = original_filename.replace(" ", "_")

    unique_filename = ( f"employee_{employee_id}_{time.time_ns()}_{safe_filename}" )

    file_path = os.path.join( UPLOAD_FOLDER, unique_filename )

    try:
        with open(file_path, "wb") as uploaded_file:
            uploaded_file.write(file.file.read())

        document = EmployeeDocument(
            employee_id=employee_id,
            document_name=document_name,
            document_type=document_type,
            file_path=file_path
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return document

    except Exception:
        db.rollback()

        if os.path.exists(file_path):
            os.remove(file_path)

        raise


def get_employee_documents(employee_id: int, db: Session):
    employee = db.query(Employee).filter( Employee.id == employee_id ).first()

    if not employee:
        raise HTTPException( status_code=404, detail="Employee not found" )

    return db.query(EmployeeDocument).filter( EmployeeDocument.employee_id == employee_id ).all()


def get_document_by_id(document_id: int, db: Session):
    document = db.query(EmployeeDocument).filter( EmployeeDocument.id == document_id ).first()

    if not document:
        raise HTTPException( status_code=404, detail="Document not found" )

    return document

def delete_employee_document(document_id: int, db: Session):
    document = get_document_by_id(document_id, db)

    try:
        db.delete(document)
        db.commit()

        if os.path.exists(document.file_path):
            os.remove(document.file_path)

        return { "message": "Employee document deleted successfully" }

    except Exception:
        db.rollback()
        raise