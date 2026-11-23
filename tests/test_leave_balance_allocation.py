from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.databased import Base, get_db
from app.main import app
from app.models.department import Department
from app.models.employee import Employee
from app.models.user import User
from app.utils.security import create_access_token


def test_admin_can_allocate_leave_balance_once():
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
        db.add_all([admin, employee_user, department])
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
        employee_id = employee.id
        token = create_access_token({"sub": str(admin.id)})
        employee_token = create_access_token({"sub": str(employee_user.id)})

    def override_get_db():
        with test_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            payload = {
                "employee_id": employee_id,
                "leave_type": "Casual Leave",
                "year": 2026,
                "total_days": 12,
            }
            headers = {"Authorization": f"Bearer {token}"}

            response = client.post("/leaves/balances", json=payload, headers=headers)
            assert response.status_code == 201
            assert response.json()["data"]["total_days"] == 12
            assert response.json()["data"]["used_days"] == 0

            leave_date = date.today() + timedelta(days=1)
            while leave_date.weekday() >= 5:
                leave_date += timedelta(days=1)
            leave_response = client.post(
                "/leaves/",
                json={
                    "leave_type": "Casual Leave",
                    "start_date": leave_date.isoformat(),
                    "end_date": leave_date.isoformat(),
                    "reason": "Personal appointment",
                },
                headers={"Authorization": f"Bearer {employee_token}"},
            )
            assert leave_response.status_code == 201

            duplicate = client.post("/leaves/balances", json=payload, headers=headers)
            assert duplicate.status_code == 409
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
