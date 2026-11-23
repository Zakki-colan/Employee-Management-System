from datetime import date, datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.databased import Base, get_db
from app.main import app
from app.models.attendance import Attendance
from app.models.department import Department
from app.models.employee import Employee
from app.models.user import User
from app.services import employee_service
from app.utils.security import create_access_token, hash_password


def test_register_and_login_with_email():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)
    with test_session() as session:
        admin = User(
            username="registration-admin",
            email="registration-admin@example.com",
            hashed_password="test-hash",
            role="ADMIN",
        )
        employee = User(
            username="registration-employee",
            email="registration-employee@example.com",
            hashed_password="test-hash",
            role="EMPLOYEE",
        )
        session.add_all([admin, employee])
        session.commit()
        admin_token = create_access_token({"sub": str(admin.id)})
        employee_token = create_access_token({"sub": str(employee.id)})

    def override_get_db():
        with test_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            registration_data = {
                "username": "Registration Check",
                "email": "registration-check@example.com",
                "password": "valid-test-password",
            }
            registration = client.post(
                "/auth/register",
                json=registration_data,
            )
            assert registration.status_code == 401

            registration = client.post(
                "/auth/register",
                json=registration_data,
                headers={"Authorization": f"Bearer {employee_token}"},
            )
            assert registration.status_code == 403

            registration = client.post(
                "/auth/register",
                json=registration_data,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert registration.status_code == 201

            login = client.post(
                "/auth/login",
                json={
                    "email": "registration-check@example.com",
                    "password": "valid-test-password",
                },
            )
            assert login.status_code == 200
            assert login.json()["data"]["token_type"] == "bearer"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_admin_can_login_with_email_or_username():
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        test_session = sessionmaker(bind=engine)
        with test_session() as session:
            admin = User(
                username="login-admin",
                email="login-admin@example.com",
                hashed_password=hash_password("valid-test-password"),
                role="ADMIN",
            )
            session.add(admin)
            session.commit()

        def override_get_db():
            with test_session() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app) as client:
                for identifier in ("login-admin@example.com", "LOGIN-ADMIN@EXAMPLE.COM", "login-admin"):
                    response = client.post(
                        "/auth/login",
                        json={
                            "email": identifier,
                            "password": "valid-test-password",
                        },
                    )
                    assert response.status_code == 200
                    assert response.json()["data"]["token_type"] == "bearer"

        finally:
            app.dependency_overrides.clear()
            engine.dispose()


def test_delete_employee_removes_related_attendance():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        user = User(
            username="delete-user",
            email="delete-user@example.com",
            hashed_password="hashed",
            role="EMPLOYEE",
            is_active=True,
        )
        department = Department(name="Engineering", description="Tech")
        db.add_all([user, department])
        db.commit()
        db.refresh(user)
        db.refresh(department)

        employee = Employee(
            full_name="Delete Me",
            phone="1234567890",
            hire_date=date(2024, 1, 1),
            position="Developer",
            salary=Decimal("50000.00"),
            department_id=department.id,
            user_id=user.id,
        )
        db.add(employee)
        db.commit()
        db.refresh(employee)

        attendance = Attendance(
            employee_id=employee.id,
            date=date(2026, 11, 13),
            check_in=datetime(2026, 11, 13, 9, 0),
            check_out=datetime(2026, 11, 13, 10, 0),
            status="PRESENT",
        )
        db.add(attendance)
        db.commit()

        response = employee_service.delete_employee(employee.id, db)

        assert response == {"message": "This Employee Deleted Successfully"}
        assert db.query(Employee).filter(Employee.id == employee.id).first() is None
        assert db.query(Attendance).filter(Attendance.id == attendance.id).first() is None

    engine.dispose()


def test_admin_cannot_assign_admin_role_during_registration():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        admin_user = User(
            username="admin-role",
            email="admin-role@example.com",
            hashed_password="hashed",
            role="ADMIN",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        token = create_access_token({"sub": str(admin_user.id)})

        def override_get_db():
            with session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/auth/register",
                    json={
                        "username": "Should Not Be Created",
                        "email": "should-not-be-created@example.com",
                        "password": "demo-password",
                        "role": "ADMIN",
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    engine.dispose()


def test_super_admin_can_register_employee_user():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        super_admin = User(
            username="super-admin-role",
            email="super-admin-role@example.com",
            hashed_password="hashed",
            role="SUPER_ADMIN",
            is_active=True,
        )
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)

        token = create_access_token({"sub": str(super_admin.id)})

        def override_get_db():
            with session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/auth/register",
                    json={
                        "username": "New Admin User",
                        "email": "new-admin-user@example.com",
                        "password": "demo-password",
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 201
                assert response.json()["data"]["role"] == "EMPLOYEE"
        finally:
            app.dependency_overrides.clear()

    engine.dispose()
