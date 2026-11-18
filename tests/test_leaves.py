from datetime import date
from uuid import uuid4

from app.models import Department, Employee, Leave, User
from app.utils.security import create_access_token


def test_apply_leave(client, db_session):
    unique = uuid4().hex
    user = User(
        username=f"leave-{unique}",
        email=f"leave-{unique}@example.com",
        hashed_password="test-hash",
        role="EMPLOYEE",
        is_active=True,
    )
    department = Department(name=f"Leave Test {unique}")
    db_session.add_all([user, department])
    db_session.commit()

    employee = Employee(
        full_name="Leave Test Employee",
        phone=f"+1{uuid4().int % 10**10:010d}",
        hire_date=date(2026, 1, 1),
        position="Developer",
        salary=50000,
        department_id=department.id,
        user_id=user.id,
    )
    db_session.add(employee)
    db_session.commit()

    token = create_access_token({"sub": str(user.id)})
    try:
        response = client.post(
            "/leaves/",
            json={
                "leave_type": "Casual",
                "start_date": "2026-11-18",
                "end_date": "2026-11-19",
                "reason": "Personal work",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        assert response.json()["employee_id"] == employee.id
        assert response.json()["status"] == "Pending"
    finally:
        db_session.rollback()
        db_session.query(Leave).filter(
            Leave.employee_id == employee.id
        ).delete(synchronize_session=False)
        db_session.delete(employee)
        db_session.delete(user)
        db_session.delete(department)
        db_session.commit()