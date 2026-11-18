from datetime import date, datetime

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import pytest

from app.databased import Base
from app.models import Department, Employee, Leave, User
from app.schemas.leave import LeaveDecision
from app.services.leave_service import review_leave


@pytest.mark.parametrize("decision_status", ["ACCEPTED", "REJECTED"])
def test_super_admin_without_employee_can_review_leave(decision_status):
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)

    try:
        with test_session() as db:
            super_admin = User(
                username="super-admin",
                email="super-admin@example.com",
                hashed_password="test-hash",
                role="SUPER_ADMIN",
            )
            employee_user = User(
                username="leave-owner",
                email="leave-owner@example.com",
                hashed_password="test-hash",
                role="EMPLOYEE",
            )
            department = Department(name="Engineering")
            db.add_all([super_admin, employee_user, department])
            db.flush()

            employee = Employee(
                id=50,
                full_name="Leave Owner",
                phone="+12345678901",
                hire_date=date(2026, 1, 1),
                position="Developer",
                salary=50000,
                department_id=department.id,
                user_id=employee_user.id,
            )
            leave = Leave(
                employee=employee,
                leave_type="Casual",
                start_date=datetime(2026, 11, 16),
                end_date=datetime(2026, 11, 17),
                reason="Personal work",
            )
            db.add(leave)
            db.commit()
            db.refresh(super_admin)
            db.refresh(leave)

            reviewed_leave = review_leave(
                leave.id,
                LeaveDecision(status=decision_status),
                super_admin.id,
                db,
            )

            assert reviewed_leave.status == decision_status
            assert reviewed_leave.approved_by == super_admin.id
            assert reviewed_leave.approver.id == super_admin.id
    finally:
        engine.dispose()
