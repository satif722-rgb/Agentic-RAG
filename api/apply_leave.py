from fastapi import APIRouter
from pydantic import BaseModel
import sqlite3
from datetime import datetime


router = APIRouter()

DB_PATH = "db/hr.db"


class LeaveRequest(BaseModel):
    employee_id: str
    leave_type: str
    days: int


@router.post("/apply-leave")
def apply_leave(data: LeaveRequest):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get current remaining leave
    cursor.execute(
        """
        SELECT remaining, used 
        FROM leave_balances 
        WHERE employee_id=? AND leave_type=?
        """,
        (data.employee_id, data.leave_type),
    )

    result = cursor.fetchone()

    if not result:
        conn.close()
        return {"status": "error", "message": "Employee or leave type not found"}

    remaining, used = result

    if remaining < data.days:
        conn.close()
        return {
            "status": "error",
            "message": f"Insufficient balance. Available: {remaining}",
        }

    new_remaining = remaining - data.days
    new_used = used + data.days

    # Update leave balance properly
    cursor.execute(
        """
        UPDATE leave_balances 
        SET remaining=?, used=? 
        WHERE employee_id=? AND leave_type=?
        """,
        (new_remaining, new_used, data.employee_id, data.leave_type),
    )

    # Insert leave application record
    cursor.execute(
        """
        INSERT INTO leave_applications 
        (employee_id, leave_type, days, status, applied_on)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data.employee_id,
            data.leave_type,
            data.days,
            "approved",
            datetime.now().date()
        ),
    )

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": f"Leave applied successfully. Remaining balance: {new_remaining}",
    }
