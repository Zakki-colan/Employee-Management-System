from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.leave import Leave
from app.models.employee import Employee
from app.schemas.leave import LeaveCreate, LeaveDecision

def apply_leave(employee_id: int, data: LeaveCreate, db: Session):

    employee = db.query(Employee).filter( Employee.id == employee_id ).first()

    if not employee:
        raise HTTPException( status_code=404, detail="This Employee is not found" )

    existing = db.query(Leave).filter( Leave.employee_id == employee_id, Leave.start_date <= data.end_date, Leave.end_date >= data.start_date, Leave.status.in_(["PENDING", "ACCEPTED"]) ).first()

    if existing:
        raise HTTPException( status_code=409, detail="You already have a leave request for these dates" )

    leave = Leave( employee_id=employee_id, **data.model_dump() )

    db.add(leave)
    db.commit()
    db.refresh(leave)

    return leave

def get_employee_leaves(employee_id: int, db: Session):
    return db.query(Leave).filter( Leave.employee_id == employee_id ).all()

def get_all_leaves(db: Session):
    return db.query(Leave).all()


def review_leave( leave_id: int, data: LeaveDecision, approver_user_id: int, db: Session):

    leave = db.query(Leave).filter( Leave.id == leave_id ).first()

    if not leave:
        raise HTTPException( status_code=404, detail="Your Leave Request is not found" )

    if leave.status != "PENDING":
        raise HTTPException( status_code=409, detail="Your Leave Request has already been reviewed" )

    leave.status = data.status
    leave.approved_by = approver_user_id

    db.commit()
    db.refresh(leave)

    return leave


def delete_leave(leave_id: int, db: Session):
    leave = db.query(Leave).filter( Leave.id == leave_id ).first()

    if not leave:
        raise HTTPException( status_code=404, detail="Your Leave Request is not found" )
    if leave.status.strip().upper() != "PENDING":
        raise HTTPException( status_code=409, detail="Only pending leave requests can be deleted" )

    db.delete(leave)
    db.commit()

    return { "message": "Your Leave Request Deleted Successfully" }