from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


DepartmentName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100, pattern=r"^[A-Za-z]")
]
DepartmentDescription = Annotated[str, Field(max_length=255)]


class DepartmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: DepartmentName
    description: DepartmentDescription | None = None


class DepartmentUpdate(DepartmentCreate):
    pass


class DepartmentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: DepartmentName | None = None
    description: DepartmentDescription | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None