
def test_attendance_check_in(client):
    response = client.post("/attendance/check-in")

    assert response.status_code in [200, 201, 401, 403]


def test_get_my_attendance(client):
    response = client.get("/attendance/my-attendance")

    assert response.status_code in [200, 401, 403]


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
