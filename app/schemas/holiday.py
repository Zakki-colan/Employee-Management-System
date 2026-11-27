from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_holiday_name(value: object) -> object:
    if not isinstance(value, str):
        return value

    value = value.strip()
    if not value or any(not character.isalpha() and character != " " for character in value):
        raise ValueError("Holiday name must contain only letters and spaces")
    return value


class HolidayCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    holiday_name: str = Field( min_length=2, max_length=100)
    holiday_date: date

    @field_validator("holiday_name", mode="before")
    @classmethod
    def validate_holiday_name(cls, value: object) -> object:
        return validate_holiday_name(value)
    
class HolidayUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    holiday_name: str | None = Field(default=None, min_length=2, max_length=100)
    holiday_date: date | None = None 

    @field_validator("holiday_name", mode="before")
    @classmethod
    def validate_holiday_name(cls, value: object) -> object:
        return validate_holiday_name(value)
    
class HolidayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int 
    holiday_name: str
    holiday_date: date