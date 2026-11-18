from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.databased import Base, get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models import Department, Employee, User


def test_employee_can_only_update_own_contact_profile():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)
    db = test_session()

    user = User(
        username="profile-owner",
        email="profile-owner@example.com",
        hashed_password="test-hash",
        role="EMPLOYEE",
    )
    department = Department(name="Engineering")
    db.add_all([user, department])
    db.flush()
    employee = Employee(
        full_name="Original Name",
        phone="+12345678901",
        hire_date=date(2026, 1, 1),
        position="Developer",
        salary=50000,
        department_id=department.id,
        user_id=user.id,
    )
    db.add(employee)
    other_user = User(
        username="other-profile-owner",
        email="other-profile-owner@example.com",
        hashed_password="test-hash",
        role="EMPLOYEE",
    )
    db.add(other_user)
    db.flush()
    other_employee = Employee(
        full_name="Other Employee",
        phone="+12345678903",
        hire_date=date(2026, 1, 1),
        position="Designer",
        salary=50000,
        department_id=department.id,
        user_id=other_user.id,
    )
    db.add(other_employee)
    db.commit()

    def override_get_db():
        yield db

    def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            own_profile = client.get(f"/employees/{employee.id}")
            assert own_profile.status_code == 200
            own_profile_data = own_profile.json()
            assert own_profile_data["id"] == employee.id
            assert own_profile_data["full_name"] == "Original Name"
            assert own_profile_data["phone_number"] == "+12345678901"
            assert own_profile_data["hire_date"] == "2026-01-01"
            assert own_profile_data["position"] == "Developer"
            assert own_profile_data["salary"] == "50000.00"
            assert own_profile_data["department"] == {
                "id": department.id,
                "name": "Engineering",
            }
            assert own_profile_data["user_id"] == user.id

            other_profile = client.get(f"/employees/{other_employee.id}")
            assert other_profile.status_code == 403

            updated = client.patch(
                "/employees/me",
                json={"full_name": "Updated Name", "phone": "+10987654321"},
            )
            assert updated.status_code == 200
            assert updated.json()["full_name"] == "Updated Name"
            assert updated.json()["phone_number"] == "+10987654321"

            forbidden_field = client.patch(
                "/employees/me",
                json={"salary": 1},
            )
            assert forbidden_field.status_code == 422

            create_employee = client.post(
                "/employees/",
                json={
                    "full_name": "Unauthorized Employee",
                    "phone": "+12345678902",
                    "hire_date": "2026-01-01",
                    "position": "Developer",
                    "salary": 50000,
                    "department_id": employee.department_id,
                    "user_id": user.id,
                },
            )
            assert create_employee.status_code == 403

            register_user = client.post(
                "/auth/register",
                json={
                    "username": "unauthorized-user",
                    "email": "unauthorized-user@example.com",
                    "password": "valid-test-password",
                },
            )
            assert register_user.status_code == 403

            other_employee = client.patch(
                f"/employees/{employee.id}",
                json={"full_name": "Not Allowed"},
            )
            assert other_employee.status_code == 403

            employee_list = client.get("/employees/")
            assert employee_list.status_code == 403
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def test_admin_can_list_employees_with_existing_custom_positions():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)
    db = test_session()

    admin = User(
        username="employee-list-admin",
        email="employee-list-admin@example.com",
        hashed_password="test-hash",
        role="ADMIN",
    )
    employee_user = User(
        username="employee-list-user",
        email="employee-list-user@example.com",
        hashed_password="test-hash",
        role="EMPLOYEE",
    )
    department = Department(name="Operations")
    db.add_all([admin, employee_user, department])
    db.flush()
    employee = Employee(
        full_name="Custom Position Employee",
        phone="+12345678904",
        hire_date=date(2026, 1, 1),
        position="Team Leader",
        salary=50000,
        department_id=department.id,
        user_id=employee_user.id,
    )
    db.add(employee)
    db.commit()

    def override_get_db():
        yield db

    def override_current_user():
        return admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    try:
        with TestClient(app) as client:
            response = client.get("/employees/")

            assert response.status_code == 200
            assert response.json()[0]["position"] == "Team Leader"
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()
