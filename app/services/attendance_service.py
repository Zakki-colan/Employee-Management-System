from datetime import date, datetime, time, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.models.attendance import Attendance
from app.models.employee import Employee
from zoneinfo import ZoneInfo

INDIA_TZ = ZoneInfo("Asia/Kolkata")


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)

def local_now() -> datetime:
    return datetime.now(INDIA_TZ).replace(microsecond=0)

def as_utc(value: datetime | time, attendance_date: date | None = None) -> datetime:
    if isinstance(value, time):
        if attendance_date is None:
            raise ValueError("An attendance date is required for time values.")
        value = datetime.combine(attendance_date, value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_duration(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{hours}h {minutes:02d}m"


def session_seconds(attendance: Attendance, now: datetime | None = None) -> int:
    check_in = as_utc(attendance.check_in, attendance.date)
    if attendance.check_out is not None:
        check_out = as_utc(attendance.check_out, attendance.date)
    else:
        check_out = as_utc(now or utc_now())
    seconds = int((check_out - check_in).total_seconds())
    return max(0, seconds)

def check_in(employee_id: int, db: Session):
    employee = db.query(Employee).filter( Employee.id == employee_id ).first()

    if not employee:
        raise HTTPException( status_code=404, detail="Employee Not Found" )
    current_time = local_now()
    today = current_time.date()

    open_attendance = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.check_out.is_(None)
    ).with_for_update().first()

    if open_attendance:
        raise HTTPException( status_code=409, detail="Please complete your previous check-out first." )

    current_time = utc_now()
    attendance = Attendance( employee_id=employee_id, date=today, check_in=current_time, status="PRESENT")

    try:
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Please complete your previous check-out first.")

    return attendance

def check_out(employee_id: int, db: Session):
    attendance = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.check_out.is_(None)
    ).order_by(
        Attendance.id.desc()
    ).with_for_update().first()

    if not attendance:
        raise HTTPException(
            status_code=404,
            detail="No active check-in found."
        )

    # Use UTC consistently
    current_time = utc_now()

    check_in_time = as_utc(attendance.check_in, attendance.date)

    if current_time <= check_in_time:
        raise HTTPException(
            status_code=400,
            detail="Check-out must be after check-in."
        )

    attendance.check_out = current_time

    try:
        db.commit()
        db.refresh(attendance)
    except Exception:
        db.rollback()
        raise

    return attendance

def get_all_attendance(db: Session):

    return db.query(Attendance).order_by(
        Attendance.date.desc(),
        Attendance.id.desc() ).all()


def get_attendance_by_date(attendance_date: date, db: Session):

    return db.query(Attendance).filter( Attendance.date == attendance_date ).all()

def calculate_working_hours(attendance):
    total_seconds = session_seconds(attendance)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    return {
        "hours": hours,
        "minutes": minutes,
        "total_seconds": total_seconds,
        "total_hours": round(total_seconds / 3600, 2),
        "working_hours": format_duration(total_seconds),
    }


def get_daily_attendance_summary(employee_id: int, attendance_date: date, db: Session, now: datetime | None = None):
    attendances = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.date == attendance_date,
    ).order_by(Attendance.id.asc()).all()

    now = now or local_now()
    sessions = []
    total_seconds = 0
    completed_sessions = 0
    ongoing_sessions = 0

    for index, attendance in enumerate(attendances, start=1):
        seconds = session_seconds(attendance, now)
        total_seconds += seconds
        if attendance.check_out is None:
            status = "IN_PROGRESS"
            ongoing_sessions += 1
        else:
            status = "COMPLETED"
            completed_sessions += 1

        check_in_utc = as_utc(attendance.check_in, attendance.date)
        check_out_utc = as_utc(attendance.check_out, attendance.date) if attendance.check_out else None
        sessions.append({
            "session": index,
            "check_in": check_in_utc.strftime("%H:%M:%S"),
            "check_out": check_out_utc.strftime("%H:%M:%S") if check_out_utc else None,
            "working_hours": format_duration(seconds),
            "status": status,
        })

    return {
        "employee_id": employee_id,
        "date": attendance_date.isoformat(),
        "sessions": sessions,
        "total_sessions": len(attendances),
        "completed_sessions": completed_sessions,
        "ongoing_sessions": ongoing_sessions,
        "total_working_hours": format_duration(total_seconds),
        "total_working_minutes": total_seconds // 60,
        "total_hours_decimal": round(total_seconds / 3600, 2),
        "formatted_working_duration": format_duration(total_seconds),
        "attendance_status": "PRESENT" if attendances else "ABSENT",
    }


def get_today_attendance_summary(employee_id: int, db: Session, now: datetime | None = None):
    today = (now or local_now()).date()
    return get_daily_attendance_summary(employee_id, today, db, now)


def get_monthly_attendance_summary(
    employee_id: int,
    year: int,
    month: int,
    db: Session,
    now: datetime | None = None,
):

    if month < 1 or month > 12:
        raise HTTPException(
            status_code=400,
            detail="Month must be between 1 and 12."
        )

    start_date = date(year, month, 1)

    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    attendances = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.date >= start_date,
        Attendance.date < end_date
    ).order_by(Attendance.date.asc()).all()

    now = now or utc_now()
    daily_totals: dict[date, int] = {}
    daily_session_counts: dict[date, int] = {}
    open_sessions = 0
    completed_sessions = 0
    for attendance in attendances:
        daily_totals.setdefault(attendance.date, 0)
        daily_session_counts.setdefault(attendance.date, 0)
        daily_session_counts[attendance.date] += 1
        if attendance.check_out is None:
            open_sessions += 1
        else:
            completed_sessions += 1
        daily_totals[attendance.date] += session_seconds(attendance, now)

    total_seconds = sum(daily_totals.values())
    daily_attendance = [
        {
            "date": day.isoformat(),
            "sessions": daily_session_counts[day],
            "working_hours": format_duration(seconds),
            "total_minutes": seconds // 60,
        }
        for day, seconds in sorted(daily_totals.items())
    ]

    return {
        "employee_id": employee_id,
        "year": year,
        "month": month,
        "working_days": len(daily_totals),
        "total_sessions": len(attendances),
        "total_completed_sessions": completed_sessions,
        "completed_sessions": completed_sessions,
        "open_sessions": open_sessions,
        "ongoing_sessions": open_sessions,
        "total_working_hours": format_duration(total_seconds),
        "total_working_minutes": total_seconds // 60,
        "total_working_duration": format_duration(total_seconds),
        "total_hours_decimal": round(total_seconds / 3600, 2),
        "daily_attendance": daily_attendance,
    }