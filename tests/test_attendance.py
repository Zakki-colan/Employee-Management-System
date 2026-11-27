from datetime import date, datetime, timezone

from app.models.attendance import Attendance
from app.models.department import Department
from app.models.employee import Employee
from app.models.user import User
from app.services.attendance_service import get_all_attendance


def test_attendance_check_in(client):
    response = client.post("/attendance/check-in")

    assert response.status_code in [200, 201, 401, 403]


def test_get_my_attendance(client):
    response = client.get("/attendance/my-attendance")

    assert response.status_code in [200, 401, 403]


def test_get_all_attendance_can_filter_by_employee(db_session):
    department = Department(name="Engineering")
    first_user = User(
        username="first-employee",
        email="first-employee@example.com",
        hashed_password="test-hash",
        role="EMPLOYEE",
    )
    second_user = User(
        username="second-employee",
        email="second-employee@example.com",
        hashed_password="test-hash",
        role="EMPLOYEE",
    )
    db_session.add_all([department, first_user, second_user])
    db_session.flush()

    first_employee = Employee(
        full_name="First Employee",
        phone="9876543210",
        hire_date=date(2026, 1, 1),
        position="Developer",
        salary=50000,
        department_id=department.id,
        user_id=first_user.id,
    )
    second_employee = Employee(
        full_name="Second Employee",
        phone="9876543211",
        hire_date=date(2026, 1, 1),
        position="Developer",
        salary=50000,
        department_id=department.id,
        user_id=second_user.id,
    )
    db_session.add_all([first_employee, second_employee])
    db_session.flush()

    db_session.add_all(
        [
            Attendance(
                employee_id=first_employee.id,
                date=date(2026, 1, 2),
                check_in=datetime(2026, 1, 2, 9, tzinfo=timezone.utc),
                status="PRESENT",
            ),
            Attendance(
                employee_id=second_employee.id,
                date=date(2026, 1, 2),
                check_in=datetime(2026, 1, 2, 9, tzinfo=timezone.utc),
                status="PRESENT",
            ),
        ]
    )
    db_session.commit()

    attendances = get_all_attendance(db_session, employee_id=first_employee.id)

    assert len(attendances) == 1
    assert attendances[0].employee_id == first_employee.id


def test_format_duration_uses_exact_seconds():
    from app.services.attendance_service import format_duration

    assert format_duration(80 * 60) == "1h 20m"
    assert format_duration(70 * 60) == "1h 10m"
    assert format_duration(8 * 3600) == "8h 00m"


def test_session_seconds_are_added_as_integer_seconds():
    from datetime import datetime, timezone
    from app.models.attendance import Attendance
    from app.services.attendance_service import session_seconds

    attendance = Attendance(
        employee_id=1,
        date=datetime(2026, 11, 23).date(),
        check_in=datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc),
        check_out=datetime(2026, 11, 23, 12, 20, tzinfo=timezone.utc),
    )

    assert session_seconds(attendance) == 3 * 3600 + 20 * 60
