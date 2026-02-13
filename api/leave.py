from fastapi import APIRouter, HTTPException
from api.database import get_db


router = APIRouter()

# --------------------------------------------------
# API 1: Get leave balance for a specific leave type
# --------------------------------------------------
@router.get("/leave-balance/{employee_id}/{leave_type}")
def get_leave_balance(employee_id: str, leave_type: str):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                e.employee_id,
                e.name AS employee_name,
                lb.leave_type,
                lb.total_allowed,
                lb.used,
                lb.remaining
            FROM leave_balances lb
            JOIN employees e
                ON lb.employee_id = e.employee_id
            WHERE lb.employee_id = ?
              AND lb.leave_type = ?
        """, (employee_id, leave_type))

        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Leave record not found")

        return {
            "employee_id": row["employee_id"],
            "employee_name": row["employee_name"],
            "leave_type": row["leave_type"],
            "total_allowed": row["total_allowed"],
            "used": row["used"],
            "remaining": row["remaining"]
        }

