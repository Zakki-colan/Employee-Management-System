from uuid import uuid4

from app.models import User
from app.utils.security import create_access_token


def test_only_admin_roles_can_register_users(client, db_session):
    unique = uuid4().hex
    employee = User(
        username=f"employee-{unique}",
        email=f"employee-{unique}@example.com",
        hashed_password="test-hash",
        role="EMPLOYEE",
        is_active=True,
    )
    admin = User(
        username=f"admin-{unique}",
        email=f"admin-{unique}@example.com",
        hashed_password="test-hash",
        role="ADMIN",
        is_active=True,
    )
    super_admin = User(
        username=f"super-admin-{unique}",
        email=f"super-admin-{unique}@example.com",
        hashed_password="test-hash",
        role="SUPER_ADMIN",
        is_active=True,
    )
    db_session.add_all([employee, admin, super_admin])
    db_session.commit()

    employee_token = create_access_token({"sub": str(employee.id)})
    admin_token = create_access_token({"sub": str(admin.id)})
    super_admin_token = create_access_token({"sub": str(super_admin.id)})

    try:
        registration_data = {
            "username": f"new-user-{unique}",
            "email": f"new-user-{unique}@example.com",
            "password": "valid-test-password",
        }

        unauthenticated = client.post("/auth/register", json=registration_data)
        assert unauthenticated.status_code == 401

        employee_registration = client.post(
            "/auth/register",
            json=registration_data,
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert employee_registration.status_code == 403

        admin_registration = client.post(
            "/auth/register",
            json=registration_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_registration.status_code == 201
        assert admin_registration.json()["role"] == "EMPLOYEE"

        super_admin_registration = client.post(
            "/auth/register",
            json={
                "username": f"super-created-{unique}",
                "email": f"super-created-{unique}@example.com",
                "password": "valid-test-password",
            },
            headers={"Authorization": f"Bearer {super_admin_token}"},
        )
        assert super_admin_registration.status_code == 201
        assert super_admin_registration.json()["role"] == "EMPLOYEE"
    finally:
        db_session.rollback()
        db_session.query(User).filter(
            User.email.in_(
                [
                    employee.email,
                    admin.email,
                    super_admin.email,
                    registration_data["email"],
                    f"super-created-{unique}@example.com",
                ]
            )
        ).delete(synchronize_session=False)
        db_session.commit()
