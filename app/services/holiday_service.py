from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.holiday import Holiday
from app.schemas.holiday import HolidayCreate, HolidayUpdate

def create_holiday(data: HolidayCreate, db: Session):
    existing = db.query(Holiday).filter(Holiday.holiday_date == data.holiday_date).first()
    if existing:
        raise HTTPException(status_code= 400, detail="A Holiday is Already exists on this Date")
    holiday = Holiday(holiday_name=data.holiday_name.strip(), holiday_date=data.holiday_date)
    
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    
    return holiday

def get_all_holidays(db: Session, year: int |None = None):
    query = db.query(Holiday)
    
    if year is not None:
        query = query.filter(
            Holiday.holiday_date >= date(year, 1, 1),
            Holiday.holiday_date < date(year + 1, 1, 1),
        )
    return query.order_by(Holiday.holiday_date.asc()).all()
    
def get_holiday_by_id(holiday_id: int, db: Session):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    
    if not holiday:
        raise HTTPException(status_code=404 , detail="Holiday is not Found ")
    return holiday

def update_holiday(holiday_id: int, data: HolidayUpdate, db: Session):
    holiday = get_holiday_by_id(holiday_id, db)
    
    updates = data.model_dump(exclude_unset=True)
    
    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update"
        )
    
    new_date = updates.get("holiday_date")
    
    existing = None
    if new_date is not None:
        existing = db.query(Holiday).filter(
            Holiday.holiday_date == new_date, Holiday.id != holiday_id
        ).first()
        
    if existing:
        raise HTTPException(status_code=400, detail=" A Holiday is Already exists on this Date")
    
    if any(value is None for value in updates.values()):
        raise HTTPException(
            status_code=400,
            detail="Holiday fields cannot be null"
        )
    
    if "holiday_name" in updates:
        updates["holiday_name"] = updates["holiday_name"].strip()

    for field, value in updates.items():
        setattr(holiday, field, value)

    db.commit()
    db.refresh(holiday)

    return holiday
        
def delete_holiday(holiday_id: int, db: Session):
    holiday = get_holiday_by_id(holiday_id, db)
    
    db.delete(holiday)
    db.commit()
    
    return True

