from langchain.tools import tool
import requests
import sqlite3

@tool
def hr_policy_lookup(question: str) -> str:
    """
    Answer HR policy-related questions using the internal HR policy knowledge base.
    Use this tool only for questions about HR rules, leave policies, benefits, and guidelines.
    """
    from Rag.rag import ask_hr 
    return ask_hr(question)


@tool
def get_leave_balance(employee_id: str, leave_type: str):
    """
    Get leave balance for an employee.
    """

    conn = sqlite3.connect("db/hr.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT total_allowed, used, remaining
        FROM leave_balances
        WHERE employee_id=? AND leave_type=?
        """,
        (employee_id, leave_type),
    )

    result = cursor.fetchone()
    conn.close()

    if not result:
        return "Employee or leave type not found."

    total, used, remaining = result

    return (
        f"You have {remaining} {leave_type} leaves remaining "
        f"out of {total}. You have used {used} so far."
    )

    
@tool
def apply_leave_tool(employee_id: str, leave_type: str, days: int):
    """
    Apply leave for an employee.

    Args:
        employee_id: Employee ID (e.g., EMP101)
        leave_type: Type of leave (medical, casual, earned)
        days: Number of leave days to apply

    Returns:
        JSON response from leave application API
    """

    response = requests.post(
        "http://localhost:8000/apply-leave",
        json={
            "employee_id": employee_id,
            "leave_type": leave_type,
            "days": days
        }
    )

    return response.json()

