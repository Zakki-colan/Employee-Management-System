from datetime import date, datetime, timedelta, timezone

import pytest

from app.models import Attendance, Department, Employee, Leave, User
from app.models.leave_balance import LeaveBalance
from app.services import attendance_service
from app.utils.security import create_access_token, hash_password


def create_user(db, username, role="EMPLOYEE", password_hash="unused"):
    user = User(
        username=username,
        email=f"{username.lower()}@example.com",
        hashed_password=password_hash,
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def authorization(user):
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def employee_profile(db_session):
    department = Department(name="Engineering")
    user = create_user(db_session, "Employee")
    db_session.add(department)
    db_session.flush()
    employee = Employee(
        full_name="Test Employee",
        phone="9876543210",
        hire_date=date(2026, 1, 1),
        position="Junior",
        salary=50000,
        user_id=user.id,
        department_id=department.id,
    )
    db_session.add(employee)
    db_session.commit()
    return employee


def test_delete_employee_with_leave_balance(client, db_session, employee_profile):
    admin = create_user(db_session, "Admin", role="ADMIN")
    teammate = create_user(db_session, "Teammate")
    other_employee = Employee(
        full_name="Test Teammate",
        phone="9876543211",
        hire_date=employee_profile.hire_date,
        position="Junior",
        salary=50000,
        user_id=teammate.id,
        department_id=employee_profile.department_id,
    )
    db_session.add(other_employee)
    db_session.flush()

    employee_id = employee_profile.id
    other_id = other_employee.id
    day = date(2026, 1, 5)
    db_session.add_all([
        Attendance(
            employee_id=employee_id,
            date=day,
            check_in=datetime(2026, 1, 5, 9, tzinfo=timezone.utc),
            status="PRESENT",
        ),
        Leave(employee_id=employee_id, leave_type_id=2, start_date=day, end_date=day),
        LeaveBalance(employee_id=employee_id, leave_type="CASUAL", year=2026, total_days=12),
        LeaveBalance(employee_id=other_id, leave_type="CASUAL", year=2026, total_days=12),
    ])
    db_session.commit()

    response = client.delete(f"/employees/{employee_id}", headers=authorization(admin))

    assert response.status_code == 200, response.text
    assert db_session.get(Employee, employee_id) is None
    for model in (Attendance, Leave, LeaveBalance):
        assert db_session.query(model).filter_by(employee_id=employee_id).count() == 0
    assert db_session.get(Employee, other_id) is not None
    assert db_session.query(LeaveBalance).filter_by(employee_id=other_id).count() == 1


def test_refresh_token_rotation_and_logout(client, db_session):
    password = "valid-test-password"
    user = create_user(db_session, "Employee", password_hash=hash_password(password))
    db_session.commit()
    login = client.post("/auth/login", json={"email": user.email, "password": password})
    assert login.status_code == 200, login.text
    original = {"refresh_token": login.json()["data"]["refresh_token"]}

    refreshed = client.post("/auth/refresh", json=original)
    assert refreshed.status_code == 200, refreshed.text
    rotated = {"refresh_token": refreshed.json()["data"]["refresh_token"]}
    assert original != rotated
    assert client.post("/auth/refresh", json=original).status_code == 401
    assert client.post("/auth/logout", json=rotated).status_code == 200
    assert client.post("/auth/refresh", json=rotated).status_code == 401


def test_checkout_in_same_second(client, employee_profile, monkeypatch):
    class ControlledClock(datetime):
        current = datetime(2026, 1, 5, 9, 0, 0, 100_000, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls.current.astimezone(tz)

    monkeypatch.setattr(attendance_service, "datetime", ControlledClock)
    headers = authorization(employee_profile.user)

    assert client.post("/attendance/check-out", headers=headers).status_code == 404
    check_in = client.post("/attendance/check-in", headers=headers)
    assert check_in.status_code == 201, check_in.text
    assert client.post("/attendance/check-in", headers=headers).status_code == 400
    assert client.post("/attendance/check-out", headers=headers).status_code == 400

    ControlledClock.current += timedelta(milliseconds=200)
    check_out = client.post("/attendance/check-out", headers=headers)
    assert check_out.status_code == 200, check_out.text
    summary = client.get("/attendance/my-attendance/today", headers=headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["data"]["completed_sessions"] == 1
    assert summary.json()["data"]["ongoing_sessions"] == 0


def test_employee_updates_preserve_untouched_fields(client, db_session, employee_profile):
    headers = authorization(create_user(db_session, "Admin", role="ADMIN"))
    employee_profile.position = "Legacy Developer"
    db_session.commit()
    path = f"/employees/{employee_profile.id}"

    assert client.put(path, headers=headers, json={"salary": 55000}).status_code == 400
    assert client.patch(path, headers=headers, json={}).status_code == 400
    assert client.patch(path, headers=headers, json={"phone": None}).status_code == 400
    assert client.patch(path, headers=headers, json={"department_id": 999}).status_code == 404
    patched = client.patch(path, headers=headers, json={"salary": 55000})
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["salary"] == "55000.00"
    assert patched.json()["data"]["position"] == "Legacy Developer"
    assert patched.json()["data"]["phone_number"] == "9876543210"

    replacement = {
        "full_name": "Updated Employee",
        "phone": "9876543211",
        "hire_date": "2026-01-05",
        "position": "Senior",
        "salary": 60000,
        "department_id": employee_profile.department_id,
    }
    replaced = client.put(path, headers=headers, json=replacement)
    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["data"]["position"] == "Senior"


def test_department_put_replaces_and_patch_merges(client, db_session):
    headers = authorization(create_user(db_session, "Admin", role="ADMIN"))
    department = Department(name="Engineering", description="Original description")
    db_session.add_all([department, Department(name="Existing")])
    db_session.commit()
    path = f"/departments/{department.id}"

    assert client.put(path, headers=headers, json={"description": "Missing name"}).status_code == 400
    assert client.patch(path, headers=headers, json={}).status_code == 400
    assert client.patch(path, headers=headers, json={"name": None}).status_code == 400
    assert client.patch(path, headers=headers, json={"name": "Existing"}).status_code == 400
    assert client.patch(path, headers=headers, json={"description": "x" * 256}).status_code == 400
    assert client.patch(path, json={"name": "Support"}).status_code == 401

    patched = client.patch(path, headers=headers, json={"name": "Support"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["description"] == "Original description"

    cleared = client.patch(path, headers=headers, json={"description": None})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["data"]["name"] == "Support"
    assert cleared.json()["data"]["description"] is None

    assert client.patch(path, headers=headers, json={"description": "Temporary"}).status_code == 200
    replaced = client.put(path, headers=headers, json={"name": "Operations"})
    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["data"]["description"] is None


def test_half_day_leave_sessions_and_balances(client, db_session, employee_profile):
    employee = authorization(employee_profile.user)
    admin_user = create_user(db_session, "Approver", role="ADMIN")
    admin = authorization(admin_user)
    db_session.commit()

    options = client.get("/leaves/types", headers=employee).json()["meta"]["half_day_sessions"]
    assert options == [{"id": 1, "name": "Session 1"}, {"id": 2, "name": "Session 2"}]

    day = date.today() + timedelta(days=1)
    while day.weekday() != 0:
        day += timedelta(days=1)
    payload = {
        "leave_type_id": 2, "start_date": day.isoformat(), "end_date": day.isoformat(),
        "reason": "Personal work",
        "assigned_to_user_id": admin_user.id,
    }

    def apply(**fields):
        return client.post("/leaves/", headers=employee, json={**payload, **fields})

    def used_days():
        balances = client.get("/leaves/my-leaves", headers=employee).json()["meta"]["leave_balances"]
        return next(
            balance["used_days"] for balance in balances
            if balance["leave_type"] == "Casual Leave" and balance["year"] == day.year
        )

    assert apply(half_day_session=3).status_code == 400
    assert apply(half_day_session=1, end_date=(day + timedelta(days=1)).isoformat()).status_code == 400
    saturday = (day + timedelta(days=5)).isoformat()
    assert apply(half_day_session=2, start_date=saturday, end_date=saturday).status_code == 400

    leave_ids = []
    for session in (1, 2):
        response = apply(half_day_session=session)
        assert response.status_code == 201, response.text
        result = response.json()["data"]
        assert result["half_day_session"] == session
        assert result["leave_days"] == 0.5
        leave_ids.append(result["id"])
        assert apply(half_day_session=session).status_code == 400

    assert apply().status_code == 400
    assert used_days() == 0
    for index, leave_id in enumerate(leave_ids, start=1):
        path = f"/leaves/{leave_id}"
        assert client.patch(
            f"{path}/review", headers=admin, json={"status": "ACCEPTED", "leave_days": 2}
        ).status_code == 400
        assert client.patch(
            f"{path}/review", headers=admin, json={"status": "ACCEPTED"}
        ).status_code == 200
        assert used_days() == index * 0.5

    history = client.get("/leaves/history?status=ACCEPTED", headers=employee).json()["data"]
    assert {row["half_day_session"] for row in history} == {1, 2}

    withdraw = f"/leaves/{leave_ids[0]}/withdraw"
    assert client.patch(withdraw, headers=employee).status_code == 200
    assert client.patch(withdraw, headers=employee).status_code == 200
    assert used_days() == 0.5
    assert apply(half_day_session=1).status_code == 201

    full_day = (day + timedelta(days=1)).isoformat()
    assert apply(start_date=full_day, end_date=full_day).status_code == 201
    assert apply(half_day_session=2, start_date=full_day, end_date=full_day).status_code == 400


def test_leave_history_swagger_keeps_status_dropdown(client):
    operation = client.get("/openapi.json").json()["paths"]["/leaves/history"]["get"]
    assert "description" not in operation
    status_filter = operation["parameters"][0]
    assert status_filter["name"] == "status"
    assert status_filter["schema"]["default"] == "ALL"
    assert status_filter["schema"]["enum"] == [
        "ALL", "PENDING", "ACCEPTED", "REJECTED", "WITHDRAWN"
    ]

    docs = client.get("/docs")
    assert docs.status_code == 200
    assert f"#operations-Leaves-{operation['operationId']}" in docs.text
    assert client.get("/docs/oauth2-redirect").status_code == 200


def test_leave_application_swagger_example_shows_approver_id(client):
    operation = client.get("/openapi.json").json()["paths"]["/leaves/"]["post"]
    request = operation["requestBody"]["content"]["application/json"]
    assert request["example"]["assigned_to_user_id"] == 3
    assert request["example"]["half_day_session"] == 1
    assert "examples" not in request


@pytest.mark.parametrize(
    "approver_role",
    ["ADMIN", "SUPER_ADMIN", "MANAGER", "HR", "PROJECT_COORDINATOR"],
)
def test_employee_can_choose_approver_when_applying(
    client, db_session, employee_profile, approver_role
):
    applicant = employee_profile.user
    applicant.role = "MANAGER"
    approver = create_user(db_session, "Approver", role=approver_role)
    other_approver = create_user(db_session, "Other", role="ADMIN")
    inactive = create_user(db_session, "Inactive", role="HR")
    inactive.is_active = False
    employee_user = create_user(db_session, "Other Employee", role="EMPLOYEE")
    db_session.commit()
    headers = authorization(applicant)

    assert client.get("/leaves/approvers").status_code == 401
    options = client.get("/leaves/approvers", headers=headers)
    assert options.status_code == 200, options.text
    assert options.json()["data"] == [
        {"id": approver.id, "username": "Approver", "role": approver_role},
        {"id": other_approver.id, "username": "Other", "role": "ADMIN"},
    ]

    day = date.today() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    payload = {
        "leave_type_id": 2, "start_date": day.isoformat(), "end_date": day.isoformat(),
        "reason": "Personal work", "half_day_session": 1,
    }
    no_approver = client.post("/leaves/", headers=headers, json=payload)
    assert no_approver.status_code == 400
    assert no_approver.json()["data"]["errors"][0]["field"] == "body.assigned_to_user_id"

    for invalid_id, expected in ((None, 400), (0, 400), (applicant.id, 400), (inactive.id, 400), (employee_user.id, 400), (9999, 404)):
        response = client.post(
            "/leaves/", headers=headers, json={**payload, "assigned_to_user_id": invalid_id}
        )
        assert response.status_code == expected, response.text

    response = client.post(
        "/leaves/", headers=headers, json={**payload, "assigned_to_user_id": approver.id}
    )
    assert response.status_code == 201, response.text
    leave = response.json()["data"]
    assert leave["assigned_to_user_id"] == approver.id
    assert leave["status"] == "PENDING"
    paths = client.get("/openapi.json").json()["paths"]
    assert "/leaves/{leave_id}/assign" not in paths
    assert client.patch(
        f"/leaves/{leave['id']}/assign",
        headers=authorization(other_approver),
        json={"assigned_to_user_id": employee_user.id},
    ).status_code == 404

    review = f"/leaves/{leave['id']}/review"
    assert client.patch(
        review, headers=authorization(other_approver), json={"status": "ACCEPTED"}
    ).status_code == 403
    approver.role = "EMPLOYEE"
    db_session.commit()
    for decision in ("ACCEPTED", "REJECTED"):
        assert client.patch(
            review, headers=authorization(approver), json={"status": decision}
        ).status_code == 400

    approver.role = approver_role
    db_session.commit()
    accepted = client.patch(
        review, headers=authorization(approver), json={"status": "ACCEPTED"}
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["data"]["approved_by"] == approver.id


def test_authentication_role_patch_is_removed(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/auth/users/{user_id}/role" not in paths
    response = client.patch("/auth/users/1/role", json={"role": "HR"})
    assert response.status_code == 404


@pytest.mark.parametrize("role", ["ADMIN", "MANAGER", "HR", "PROJECT_COORDINATOR"])
def test_super_admin_can_register_an_approver(client, db_session, employee_profile, role):
    super_admin = create_user(db_session, "SuperAdmin", role="SUPER_ADMIN")
    admin = create_user(db_session, "Admin", role="ADMIN")
    db_session.commit()
    payload = {
        "username": "New Approver", "email": "new-approver@example.com",
        "password": "test-password", "role": role,
    }

    assert client.post("/auth/register", headers=authorization(admin), json=payload).status_code == 403
    forbidden = client.post(
        "/auth/register", headers=authorization(super_admin),
        json={**payload, "role": "SUPER_ADMIN"},
    )
    assert forbidden.status_code == 400

    registered = client.post("/auth/register", headers=authorization(super_admin), json=payload)
    assert registered.status_code == 201, registered.text
    user = registered.json()["data"]
    assert user["role"] == role

    approvers = client.get("/leaves/approvers", headers=authorization(employee_profile.user))
    assert {"id": user["id"], "username": "New Approver", "role": role} in approvers.json()["data"]


def test_swagger_registration_exposes_role_and_success_response(client):
    schema = client.get("/openapi.json").json()
    role = schema["components"]["schemas"]["UserRegister"]["properties"]["role"]
    assert role["default"] == "EMPLOYEE"
    assert role["enum"] == ["EMPLOYEE", "ADMIN", "MANAGER", "HR", "PROJECT_COORDINATOR"]
    assert "201" in schema["paths"]["/auth/register"]["post"]["responses"]


def test_leave_history_is_scoped_to_the_signed_in_employee(client, db_session, employee_profile):
    colleague_user = create_user(db_session, "Colleague")
    colleague = Employee(
        full_name="Test Colleague",
        phone="9876543211",
        hire_date=employee_profile.hire_date,
        position="Junior",
        salary=50000,
        user_id=colleague_user.id,
        department_id=employee_profile.department_id,
    )
    db_session.add(colleague)
    db_session.flush()

    day = date(2026, 1, 5)
    for employee in (employee_profile, colleague):
        db_session.add(Leave(
            employee_id=employee.id,
            leave_type_id=2,
            start_date=day,
            end_date=day,
            leave_days=1,
            status="PENDING",
        ))
    db_session.commit()

    for employee, other_employee in ((employee_profile, colleague), (colleague, employee_profile)):
        auth = authorization(employee.user)
        for status in ("ALL", "PENDING"):
            response = client.get(
                "/leaves/history",
                headers=auth,
                params={"status": status, "employee_id": other_employee.id},
            )
            assert response.status_code == 200, response.text
            assert [leave["employee_id"] for leave in response.json()["data"]] == [employee.id]
        my_leaves = client.get("/leaves/my-leaves", headers=auth)
        assert my_leaves.status_code == 200, my_leaves.text
        assert [leave["employee_id"] for leave in my_leaves.json()["data"]] == [employee.id]
        assert client.get("/leaves/", headers=auth).status_code == 403
