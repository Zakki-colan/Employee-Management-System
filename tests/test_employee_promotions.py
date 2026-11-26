from datetime import date
from decimal import Decimal

import pytest

from app.dependencies.auth import get_current_user
from app.main import app
from app.models import Department, Employee, User


@pytest.fixture
def promotion_employee(db_session, monkeypatch):
    department = Department(name="Engineering")
    admin = User(
        username="admin", email="admin@example.com", hashed_password="test", role="ADMIN"
    )
    owner = User(
        username="owner", email="owner@example.com", hashed_password="test", role="EMPLOYEE"
    )
    db_session.add_all([department, admin, owner])
    db_session.flush()

    employee = Employee(
        full_name="Sam Patel",
        phone="9876543210",
        hire_date=date(2025, 1, 1),
        position="Junior",
        salary=Decimal("50000.00"),
        department_id=department.id,
        user_id=owner.id,
    )
    db_session.add(employee)
    db_session.commit()

    monkeypatch.setitem(app.dependency_overrides, get_current_user, lambda: admin)
    return employee, owner


def test_promotion_updates_profile_and_records_history(client, promotion_employee):
    employee, _ = promotion_employee
    url = f"/employees/{employee.id}/promotions"

    response = client.post(
        url, json={"new_position": "Senior", "new_salary": "60000.25", "reason": "  Led onboarding  "}
    )
    assert response.status_code == 201
    promotion = response.json()["data"]
    assert promotion["previous_position"] == "Junior"
    assert promotion["previous_salary"] == "50000.00"
    assert promotion["new_salary"] == "60000.25"
    assert promotion["reason"] == "Led onboarding"

    response = client.post(url, json={"new_position": "Team Leader", "reason": "Leads the team"})
    assert response.status_code == 201
    assert response.json()["data"]["new_salary"] == "60000.25"

    profile = client.get(f"/employees/{employee.id}").json()["data"]
    assert profile["position"] == "Team Leader"
    assert profile["salary"] == "60000.25"

    history = client.get(url, params={"page_size": 1}).json()
    assert history["data"][0]["new_position"] == "Team Leader"
    assert history["meta"]["next_page"] == 2
    history = client.get(url, params={"page_size": 1, "page": 2}).json()
    assert history["data"] == [promotion]
    assert history["meta"]["next_page"] is None

    assert client.delete(f"/employees/{employee.id}").status_code == 200
    assert client.get(url).status_code == 404


@pytest.mark.parametrize(
    "data",
    [
        {"new_position": "Junior", "reason": "Same role"},
        {"new_position": "Senior", "new_salary": "1000", "reason": "Lower salary"},
        {"new_position": "Senior", "reason": " "},
    ],
)
def test_invalid_promotion_leaves_history_and_profile_unchanged(client, promotion_employee, data):
    employee, _ = promotion_employee
    url = f"/employees/{employee.id}/promotions"

    assert client.post(url, json=data).status_code == 400
    assert client.get(url).json()["data"] == []
    assert employee.position == "Junior"
    assert employee.salary == Decimal("50000.00")


def test_employee_can_only_read_own_promotions(client, promotion_employee, monkeypatch):
    employee, owner = promotion_employee
    url = f"/employees/{employee.id}/promotions"
    data = {"new_position": "Senior", "reason": "Expanded responsibilities"}
    assert client.post(url, json=data).status_code == 201

    monkeypatch.setitem(app.dependency_overrides, get_current_user, lambda: owner)
    response = client.get(url)
    assert response.status_code == 200
    assert response.json()["data"][0]["new_position"] == "Senior"
    assert client.get(f"/employees/{employee.id + 1}/promotions").status_code == 403
    assert client.post(url, json=data).status_code == 403
