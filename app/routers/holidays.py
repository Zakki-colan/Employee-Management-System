from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session 
from typing import Annotated
from app.databased import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import get_current_admin
from app.models.user import User
from app.schemas.holiday import HolidayUpdate, HolidayCreate, HolidayResponse
from app.services import holiday_service
from app.utils.response import success_response

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_holiday(data: HolidayCreate, db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    holiday = holiday_service.create_holiday(data, db)
    
    return success_response(message=" New Holiday Created Successfully", data= HolidayResponse.model_validate(holiday).model_dump(mode="json"), status_code=201)

@router.get("/")
def get_holidays(
    db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)], year: int |None = Query(default=None, ge=2000, le=2100)
):
    holidays = holiday_service.get_all_holidays(db, year)
    return success_response( message= "Your Holiday's Retrieved Successfully", data=[HolidayResponse.model_validate(h).model_dump(mode="json") for h in holidays ])

@router.get("/{holiday_id}")
def get_holifday(holiday_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    holiday = holiday_service.get_holiday_by_id(holiday_id, db)
    
    return success_response( message="Holiday's Retrieved Successfully", data= HolidayResponse.model_validate(holiday).model_dump(mode="json"))

@router.put("/{holiday_id}")
def update_holiday(holiday_id: int, data: HolidayUpdate, db: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    holiday = holiday_service.update_holiday(holiday_id, data, db)
    
    return success_response( message="Holiday Updated Successfully", data=HolidayResponse.model_validate(holiday).model_dump(mode="json"), )

@router.delete("/{holiday_id}")
def delete_holiday(holiday_id: int, db: Annotated[Session,Depends(get_db)], admin: Annotated[User, Depends(get_current_admin)]):
    holiday = holiday_service.delete_holiday(holiday_id, db)
    
    return success_response(message=" Holiday deleted sucessfully ")