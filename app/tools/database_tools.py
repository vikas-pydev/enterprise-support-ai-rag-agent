"""LangChain Tool wrappers for PostgreSQL Enterprise Database.

Exposes structured, typed, and parameterized repository queries to LangChain agents.
No raw SQL or arbitrary queries are permitted or executed in this layer.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.database import (
    get_employee_summary,
    get_employee_leave_summary,
    get_employee_travel_summary,
    list_employees_by_department,
    DatabaseError,
)


def _serialize(obj: Any) -> Any:
    """Recursively convert dates, datetimes, and decimals to JSON-serializable types."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    return obj


class EmployeeIdInput(BaseModel):
    """Input schema for tools requiring an employee business identifier."""

    employee_id: str = Field(
        ...,
        description="The unique employee identifier (e.g., 'E1001', 'E1002').",
    )


class DepartmentInput(BaseModel):
    """Input schema for department queries."""

    department: str = Field(
        ...,
        description="The department name (e.g., 'Engineering', 'Human Resources', 'Finance', 'Sales').",
    )


@tool(args_schema=EmployeeIdInput)
def get_employee(employee_id: str) -> dict[str, Any]:
    """Retrieves an employee's official profile and manager details from PostgreSQL.

    USE THIS TOOL WHEN:
    - Looking up an employee's name, email, department, job title, or hire details.
    - Identifying who manages an employee or who reports to whom.

    DO NOT USE THIS TOOL FOR:
    - Looking up general company policy rules or expense limits (use `ask_policy` instead).
    - Querying leave balance numbers (use `get_leave_balance` instead).
    - Querying travel reimbursement amounts (use `get_travel_summary` instead).

    RETURNS:
    A dictionary with employee attributes and direct manager info, or `found: False` if missing.
    """
    clean_id = str(employee_id).strip()
    if not clean_id:
        return {"error": "Invalid employee_id provided.", "found": False}

    try:
        data = get_employee_summary(clean_id)
        if data is None:
            return {
                "employee_id": clean_id,
                "found": False,
                "message": f"Employee with ID '{clean_id}' was not found in the database.",
            }
        return {
            "found": True,
            "data": _serialize(data),
        }
    except DatabaseError:
        return {
            "employee_id": clean_id,
            "found": False,
            "status": "error",
            "error": "A database error occurred while fetching the employee profile.",
        }
    except Exception:
        return {
            "employee_id": clean_id,
            "found": False,
            "status": "error",
            "error": "An unexpected error occurred while querying employee records.",
        }


@tool(args_schema=EmployeeIdInput)
def get_leave_balance(employee_id: str) -> dict[str, Any]:
    """Retrieves current leave balance allocations, usage, and remaining days for an employee.

    USE THIS TOOL WHEN:
    - An employee asks how many vacation, sick, or personal days they have left.
    - Checking if an employee has sufficient balance for taking time off.

    DO NOT USE THIS TOOL FOR:
    - General corporate leave rules, rollover policies, or holiday calendars (use `ask_policy` instead).
    - Non-leave employee data (use `get_employee` instead).

    RETURNS:
    A dictionary with total allocated days, used days, remaining days, and category breakdowns.
    """
    clean_id = str(employee_id).strip()
    if not clean_id:
        return {"error": "Invalid employee_id provided.", "found": False}

    try:
        data = get_employee_leave_summary(clean_id)
        if data is None:
            return {
                "employee_id": clean_id,
                "found": False,
                "message": f"Leave records for employee '{clean_id}' were not found.",
            }
        return {
            "found": True,
            "data": _serialize(data),
        }
    except DatabaseError:
        return {
            "employee_id": clean_id,
            "found": False,
            "status": "error",
            "error": "A database error occurred while fetching leave balances.",
        }
    except Exception:
        return {
            "employee_id": clean_id,
            "found": False,
            "status": "error",
            "error": "An unexpected error occurred while querying leave records.",
        }


@tool(args_schema=EmployeeIdInput)
def get_travel_summary(employee_id: str) -> dict[str, Any]:
    """Retrieves travel expense summaries, aggregate claims, and status breakdowns for an employee.

    USE THIS TOOL WHEN:
    - Checking total travel spending, submitted expenses, approved claims, or reimbursed amounts for a specific person.
    - Inspecting expense category breakdowns (e.g., flight, hotel, meals).

    DO NOT USE THIS TOOL FOR:
    - Travel policy rules, per diem limits, or receipt requirements (use `ask_policy` instead).
    - Querying leave balance numbers (use `get_leave_balance` instead).

    RETURNS:
    A dictionary containing total claims, total amount, amounts by status, and category breakdowns.
    """
    clean_id = str(employee_id).strip()
    if not clean_id:
        return {"error": "Invalid employee_id provided.", "found": False}

    try:
        data = get_employee_travel_summary(clean_id)
        if data is None:
            return {
                "employee_id": clean_id,
                "found": False,
                "message": f"Travel records for employee '{clean_id}' were not found.",
            }
        return {
            "found": True,
            "data": _serialize(data),
        }
    except DatabaseError:
        return {
            "employee_id": clean_id,
            "found": False,
            "status": "error",
            "error": "A database error occurred while fetching travel summaries.",
        }
    except Exception:
        return {
            "employee_id": clean_id,
            "found": False,
            "status": "error",
            "error": "An unexpected error occurred while querying travel records.",
        }


@tool(args_schema=DepartmentInput)
def list_department_employees(department: str) -> dict[str, Any]:
    """Lists all active employees and their job titles in a specific department.

    USE THIS TOOL WHEN:
    - Looking up team members in a department (e.g., 'Engineering', 'Finance', 'Human Resources').
    - Counting or listing staff assigned to a department.

    DO NOT USE THIS TOOL FOR:
    - Querying company wide policies (use `ask_policy` instead).
    - Querying leave balances (use `get_leave_balance` instead).

    RETURNS:
    A dictionary with the department name, count, and list of employee records.
    """
    clean_dept = str(department).strip()
    if not clean_dept:
        return {"error": "Invalid department name provided.", "found": False}

    try:
        employees = list_employees_by_department(clean_dept)
        return {
            "department": clean_dept,
            "found": True,
            "count": len(employees),
            "employees": _serialize(employees),
        }
    except DatabaseError:
        return {
            "department": clean_dept,
            "found": False,
            "status": "error",
            "error": "A database error occurred while fetching department members.",
        }
    except Exception:
        return {
            "department": clean_dept,
            "found": False,
            "status": "error",
            "error": "An unexpected error occurred while querying department records.",
        }
