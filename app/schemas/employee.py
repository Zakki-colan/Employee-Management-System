from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

PhoneNumber = Annotated[ str, StringConstraints( min_length=10, max_length=10, pattern=r"^[6-9][0-9]{9}$")]

class EmployeePosition(str, Enum):
    JUNIOR = "Junior"
    SENIOR = "Senior"
    TEAM_LEADER = "Team Leader"
    PC = "PC"
    OTHER = "Other"
    
class EmployeeBase(BaseModel):
    full_name: str = Field( min_length=1, max_length=100, pattern=r"^[A-Za-z ]+$", json_schema_extra={"example": "Rahul Kumar"})
    phone: PhoneNumber = Field( validation_alias=AliasChoices("phone", "phone_number"), json_schema_extra={"example": "9876543210"} )
    hire_date: date
    position: EmployeePosition = Field( description="Allowed positions: 'Junior', 'Senior', 'Team Leader', 'PC', or 'Other'")
    salary: Decimal = Field(gt=0)
    department_id: int = Field(gt=0)

class EmployeeCreate(EmployeeBase):
    user_id: int = Field(gt=0)

class EmployeeUpdate(EmployeeBase):
    model_config = ConfigDict(extra="forbid")

class EmployeePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field( default=None, min_length=1, max_length=100, pattern=r"^[A-Za-z ]+$", json_schema_extra={"example": "Rahul Kumar"} )
    phone: PhoneNumber | None = Field( default=None, validation_alias=AliasChoices("phone", "phone_number"), json_schema_extra={"example": "9876543210"} )
    hire_date: date | None = None
    position: EmployeePosition | None = None
    salary: Decimal | None = Field(default=None, gt=0)
    department_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_patch_fields(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        if any( getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Fields cannot be null")

        return self
    

class EmployeeSelfUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field( default=None, min_length=1, max_length=100 )
    phone: PhoneNumber | None = Field( default=None, validation_alias=AliasChoices("phone", "phone_number"), json_schema_extra={"example": "9876543210"} )

    @model_validator(mode="after")
    def validate_update_fields(self):
        if not self.model_fields_set:
            raise ValueError(
                "At least one profile field must be provided"
            )

        if any(
            getattr(self, field) is None
            for field in self.model_fields_set
        ):
            raise ValueError("Profile fields cannot be null")

        return self

class EmployeeDepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str

class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone_number: str = Field(validation_alias="phone")
    hire_date: date
    position: EmployeePosition
    salary: Decimal
    department: EmployeeDepartmentResponse
    user_id: int