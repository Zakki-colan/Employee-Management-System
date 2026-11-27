from datetime import date

import pytest
from fastapi import HTTPException

from app.models.holiday import Holiday
from app.schemas.holiday import HolidayCreate, HolidayResponse, HolidayUpdate
from app.services.holiday_service import create_holiday, get_all_holidays, get_holiday_by_id, update_holiday


def test_create_holiday_succeeds_for_new_date(db_session):
    holiday_date = date(2027, 8, 15)
    data = HolidayCreate(holiday_name="Independence Day", holiday_date=holiday_date)

    holiday = create_holiday(data, db_session)
    response = HolidayResponse.model_validate(holiday)

    assert response.holiday_name == "Independence Day"
    assert response.holiday_date == holiday_date


def test_holiday_name_rejects_numbers():
    with pytest.raises(ValueError, match="only letters and spaces"):
        HolidayCreate(holiday_name="Holiday 2027", holiday_date=date(2027, 8, 15))


def test_holiday_update_name_rejects_numbers():
    with pytest.raises(ValueError, match="only letters and spaces"):
        HolidayUpdate(holiday_name="Holiday 2027")


def test_create_holiday_rejects_existing_date(db_session):
    holiday_date = date(2027, 8, 15)
    db_session.add(Holiday(holiday_name="Existing Holiday", holiday_date=holiday_date))
    db_session.commit()
    data = HolidayCreate(holiday_name="Independence Day", holiday_date=holiday_date)

    with pytest.raises(HTTPException) as exc_info:
        create_holiday(data, db_session)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "A Holiday is Already exists on this Date"


def test_get_all_holidays_filters_by_year(db_session):
    db_session.add_all([
        Holiday(holiday_name="Before Holiday", holiday_date=date(2026, 12, 31)),
        Holiday(holiday_name="Current Holiday", holiday_date=date(2027, 1, 1)),
        Holiday(holiday_name="After Holiday", holiday_date=date(2028, 1, 1)),
    ])
    db_session.commit()

    holidays = get_all_holidays(db_session, year=2027)

    assert [holiday.holiday_name for holiday in holidays] == ["Current Holiday"]


def test_get_holiday_by_id_returns_holiday(db_session):
    holiday = Holiday(holiday_name="Existing Holiday", holiday_date=date(2027, 8, 15))
    db_session.add(holiday)
    db_session.commit()

    result = get_holiday_by_id(holiday.id, db_session)

    assert result.id == holiday.id
    assert result.holiday_name == "Existing Holiday"


def test_update_holiday_updates_all_provided_fields(db_session):
    holiday = Holiday(holiday_name="Existing Holiday", holiday_date=date(2027, 8, 15))
    db_session.add(holiday)
    db_session.commit()

    result = update_holiday(
        holiday.id,
        HolidayUpdate(holiday_name="Independence Day", holiday_date=date(2027, 8, 16)),
        db_session,
    )

    assert result.holiday_name == "Independence Day"
    assert result.holiday_date == date(2027, 8, 16)
