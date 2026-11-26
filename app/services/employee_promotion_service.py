from decimal import Decimal
from typing import cast
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from app.models.employee import Employee
from app.models.employee_promotion import EmployeePromotion
from app.schemas.employee_promotion import PromotionCreate
from app.services.employee_service import get_employee_by_id


def promote_employee(
    employee_id: int, data: PromotionCreate, admin_id: int, db: Session
) -> EmployeePromotion:
    employee = get_employee_by_id(employee_id, db)
    new_position = data.new_position.value
    new_salary = employee.salary if data.new_salary is None else data.new_salary

    if employee.position == new_position:
        raise HTTPException(400, "Choose a position different from the employee's current position")
    if Decimal(str(new_salary)) < Decimal(str(employee.salary)):
        raise HTTPException(400, "A promotion cannot reduce the employee's salary")

    promotion = EmployeePromotion(
        employee_id=employee.id,
        promoted_by_user_id=admin_id,
        previous_position=employee.position,
        new_position=new_position,
        previous_salary=employee.salary,
        new_salary=new_salary,
        reason=data.reason,
    )

    try:
        # Apply the promotion only if its starting position and salary still match.
        result = cast(
            CursorResult,
            db.execute(
                update(Employee)
                .where(
                    Employee.id == employee_id,
                    Employee.position == promotion.previous_position,
                    Employee.salary == promotion.previous_salary,
                )
                .values(position=new_position, salary=new_salary)
            ),
        )
        if result.rowcount != 1:
            raise HTTPException(409, "The employee record changed. Refresh it and try again.")

        db.add(promotion)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return promotion


def get_promotion_history(
    employee_id: int, db: Session, *, page: int, page_size: int
) -> tuple[list[EmployeePromotion], bool]:
    get_employee_by_id(employee_id, db)
    promotions = db.scalars(
        select(EmployeePromotion)
        .where(EmployeePromotion.employee_id == employee_id)
        .order_by(EmployeePromotion.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size + 1)
    ).all()
    return list(promotions[:page_size]), len(promotions) > page_size
