import re
from datetime import date
from decimal import Decimal

ALLOWED_ROLES = {
    "SUPER_ADMIN",
    "ADMIN",
    "EMPLOYEE"
}


def validate_phone(phone: str) -> bool:
    """
    Allows an optional + followed by 10 to 15 digits.
    """
    return bool(re.fullmatch(r"\+?[0-9]{10,15}", phone))


def validate_salary(salary: Decimal) -> bool:
    return salary > 0


def validate_date_range(start_date: date, end_date: date) -> bool:
    return end_date >= start_date


def validate_role(role: str) -> bool:
    return role.upper() in ALLOWED_ROLES


def normalize_role(role: str) -> str:
    normalized = role.strip().upper()

    if normalized not in ALLOWED_ROLES:
        raise ValueError("Invalid user role")

    return normalized