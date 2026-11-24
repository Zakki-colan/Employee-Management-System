from datetime import datetime
from pydantic import BaseModel, ConfigDict

class EmployeeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    document_name: str
    document_type: str
    uploaded_at: datetime