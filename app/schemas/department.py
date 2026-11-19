from pydantic import BaseModel, ConfigDict, Field

class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100,pattern=r"^[A-Za-z]", json_schema_extra={"example": "string"})
    description: str | None = Field(default=None, max_length=255, json_schema_extra={"example": "string"})

class DepartmentUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100,pattern=r"^[A-Za-z]", json_schema_extra={"example": "string"})
    description: str | None = None

class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str 
    description: str | None = None