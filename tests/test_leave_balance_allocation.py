from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.databased import Base, get_db
from app.main import app
from app.models.department import Department
from app.models.employee import Employee
from app.models.holiday import Holiday
from app.models.leave_type import LeaveType
from app.models.user import User
from app.services import leave_service
from app.utils.security import create_access_token


def test_employee_receives_automatic_annual_leave_allowances(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)

    with test_session() as db:
        admin = User(
            username="leave-balance-admin",
            email="leave-balance-admin@example.com",
            hashed_password="unused",
            role="ADMIN",
            is_active=True,
        )
        employee_user = User(
            username="leave-balance-employee",
            email="leave-balance-employee@example.com",
            hashed_password="unused",
            role="EMPLOYEE",
            is_active=True,
        )
        department = Department(name="Leave Balance Test")
        db.add_all([
            admin, employee_user, department,
            LeaveType(id=2, name="Casual Leave"),
            LeaveType(id=10, name="Historical Leave", is_active=False),
            LeaveType(id=11, name="Unsupported Leave"),
        ])
        db.commit()
        db.refresh(admin)
        db.refresh(employee_user)
        db.refresh(department)

        employee = Employee(
            full_name="Leave Balance Employee",
            phone="5550100100",
            hire_date=date(2024, 1, 1),
            position="Developer",
            salary=50000,
            department_id=department.id,
            user_id=employee_user.id,
        )
        db.add(employee)
        db.commit()
        db.refresh(employee)
        admin_id = admin.id
        token = create_access_token({"sub": str(admin_id)})
        employee_token = create_access_token({"sub": str(employee_user.id)})

    def override_get_db():
        with test_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            leave_date = date.today() + timedelta(days=1)
            while leave_date.weekday() != 4 or leave_date.year != (leave_date + timedelta(days=3)).year:
                leave_date += timedelta(days=1)
            holiday_date = leave_date + timedelta(days=3)
            headers = {"Authorization": f"Bearer {token}"}
            with test_session() as db:
                db.add(Holiday(holiday_date=holiday_date, holiday_name="Test holiday"))
                db.commit()
            employee_headers = {"Authorization": f"Bearer {employee_token}"}
            initial = client.get("/leaves/my-leaves", headers=employee_headers)
            assert initial.status_code == 200
            assert initial.json()["data"] == []
            assert len(initial.json()["meta"]["leave_balances"]) == 4
            paths = client.get("/openapi.json").json()["paths"]
            assert "/leaves/balances" not in paths
            assert "/leaves/balances/bulk" not in paths

            types = client.get("/leaves/types", headers=employee_headers)
            assert types.status_code == 200
            assert types.json()["data"] == [{"id": 2, "name": "Casual Leave"}]
            history_endpoint = "/leaves/history"
            status_parameter = next(
                parameter for parameter in paths[history_endpoint]["get"]["parameters"]
                if parameter["name"] == "status"
            )
            assert status_parameter["schema"]["enum"] == [
                "ALL", "PENDING", "ACCEPTED", "REJECTED", "WITHDRAWN"
            ]
            assert client.get(history_endpoint).status_code == 401
            assert client.get(
                history_endpoint, params={"status": "UNKNOWN"}, headers=employee_headers
            ).status_code == 400

            application = {
                "start_date": leave_date.isoformat(),
                "end_date": holiday_date.isoformat(),
                "reason": "Personal appointment",
            }
            for invalid_id in (0, 10, 11, 99):
                invalid = client.post(
                    "/leaves/",
                    json={**application, "leave_type_id": invalid_id},
                    headers=employee_headers,
                )
                assert invalid.status_code == 400
                assert invalid.json()["data"]["available_leave_types"] == types.json()["data"]

            leave_response = client.post(
                "/leaves/",
                json={**application, "leave_type_id": 2},
                headers=employee_headers,
            )
            assert leave_response.status_code == 201

            for endpoint, auth_headers in (
                ("/leaves/my-leaves", employee_headers),
                ("/leaves/", headers),
            ):
                response = client.get(endpoint, headers=auth_headers)
                assert response.status_code == 200
                (record,) = response.json()["data"]
                assert record["leave_days"] == 1

            my_leaves = client.get("/leaves/my-leaves", headers=employee_headers)
            (balance,) = [
                row for row in my_leaves.json()["meta"]["leave_balances"]
                if row["year"] == leave_date.year and row["leave_type"] == "Casual Leave"
            ]
            assert balance["total_days"] == 12
            assert balance["used_days"] == 0
            assert balance["remaining_days"] == 12

            leave_id = leave_response.json()["data"]["id"]
            pending = client.get(history_endpoint, params={"status": "PENDING"}, headers=employee_headers)
            assert pending.status_code == 200
            assert [record["id"] for record in pending.json()["data"]] == [leave_id]

            assignment = client.patch(
                f"/leaves/{leave_id}/assign",
                json={"assigned_to_user_id": admin_id},
                headers=headers,
            )
            assert assignment.status_code == 200
            review = client.patch(
                f"/leaves/{leave_id}/review",
                json={"status": "ACCEPTED"},
                headers=headers,
            )
            assert review.status_code == 200
            for status_filter, expected_ids in (
                (None, [leave_id]),
                ("ALL", [leave_id]),
                ("ACCEPTED", [leave_id]),
                ("PENDING", []),
                ("REJECTED", []),
            ):
                params = {} if status_filter is None else {"status": status_filter}
                history = client.get(history_endpoint, params=params, headers=employee_headers)
                assert history.status_code == 200
                assert [record["id"] for record in history.json()["data"]] == expected_ids

            my_leaves = client.get("/leaves/my-leaves", headers=employee_headers)
            (balance,) = [
                row for row in my_leaves.json()["meta"]["leave_balances"]
                if row["year"] == leave_date.year and row["leave_type"] == "Casual Leave"
            ]
            assert balance["used_days"] == 1
            assert balance["remaining_days"] == 11

            withdrawal_endpoint = f"/leaves/{leave_id}/withdraw"
            monkeypatch.setattr(
                leave_service, "local_now",
                lambda: datetime.combine(leave_date + timedelta(days=1), datetime.min.time()),
            )
            assert client.patch(withdrawal_endpoint, headers=employee_headers).status_code == 400

            monkeypatch.setattr(
                leave_service, "local_now",
                lambda: datetime.combine(leave_date, datetime.min.time()),
            )
            for _ in range(2):
                withdrawal = client.patch(withdrawal_endpoint, headers=employee_headers)
                assert withdrawal.status_code == 200
                assert withdrawal.json()["data"]["status"] == "WITHDRAWN"

            history = client.get(
                history_endpoint, params={"status": "WITHDRAWN"}, headers=employee_headers
            )
            assert [record["id"] for record in history.json()["data"]] == [leave_id]
            my_leaves = client.get("/leaves/my-leaves", headers=employee_headers)
            (balance,) = [
                row for row in my_leaves.json()["meta"]["leave_balances"]
                if row["year"] == leave_date.year and row["leave_type"] == "Casual Leave"
            ]
            assert balance["used_days"] == 0
            assert balance["remaining_days"] == 12

            reapplication = client.post(
                "/leaves/", json={**application, "leave_type_id": 2}, headers=employee_headers
            )
            assert reapplication.status_code == 201
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
