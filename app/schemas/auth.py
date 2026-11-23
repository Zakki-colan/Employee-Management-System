from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z ]+$", json_schema_extra={"example": "Rahul Kumar"})
    email: EmailStr
    password: str = Field(min_length=8)


class UserAccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update_fields(self):
        if not self.model_fields_set:
            raise ValueError("At least one account field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Account fields cannot be null")
        return self

class UserLogin(BaseModel):
    email: str = Field(
        min_length=1,
        max_length=100,
        description="Email address or username",
    )
    password: str

    @field_validator("email")
    @classmethod
    def strip_login_identifier(cls, value: str) -> str:
        return value.strip()

class UserRoleUpdate(BaseModel):
    role: Literal["EMPLOYEE", "ADMIN", "SUPER_ADMIN"]

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: EmailStr
    role: str
    # is_active: bool

class Token(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: EmailStr | None = None