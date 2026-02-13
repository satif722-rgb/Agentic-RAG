from langchain.tools import tool
import requests


@tool
def hr_policy_lookup(question: str) -> str:
    """
    Answer HR policy-related questions using the internal HR policy knowledge base.
    Use this tool only for questions about HR rules, leave policies, benefits, and guidelines.
    """
    from Rag.rag import ask_hr 
    return ask_hr(question)


@tool
def get_leave_balance(employee_id: str, leave_type: str) -> str:
    """
    Retrieve an employee's leave balance for a specific leave type
    from the HR leave management system.
    """
    try:
        url = f"http://localhost:8000/leave-balance/{employee_id}/{leave_type}"
        response = requests.get(url, timeout=3)
        response.raise_for_status()

        data = response.json()

        # ✅ Correct parsing for your API structure
        name = data.get("employee_name", "Employee")
        remaining = data.get("remaining")
        total = data.get("total_allowed")
        used = data.get("used")

        if remaining is not None:
            return (
                f"{name}, you have {remaining} {leave_type} leaves remaining "
                f"out of {total}. You have used {used} so far."
            )

        return "Leave balance information is unavailable."

    except requests.exceptions.HTTPError:
        return "No leave balance found for your account."

    except requests.exceptions.ConnectionError:
        return "HR system is temporarily unavailable."

    except requests.exceptions.Timeout:
        return "HR system took too long to respond."

    except Exception:
        return "Unexpected error while retrieving leave balance."

