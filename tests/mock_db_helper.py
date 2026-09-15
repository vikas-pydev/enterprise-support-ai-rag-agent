"""Deterministic mock database fixtures for unit and integration testing without live PostgreSQL."""

from unittest.mock import patch
from app.database.connection import test_connection
from app.database.config import DEFAULT_DB_CONFIG

MOCK_EMPLOYEES = {
    "E1001": {
        "employee_id": "E1001",
        "name": "Alice Chen",
        "email": "alice.chen@enterprise.internal",
        "department": "Engineering",
        "job_title": "Senior Software Engineer",
        "manager_employee_id": "E1004",
        "manager": {"employee_id": "E1004", "name": "David Kim", "job_title": "VP of Operations"},
    },
    "E1002": {
        "employee_id": "E1002",
        "name": "Bob Martinez",
        "email": "bob.martinez@enterprise.internal",
        "department": "Marketing",
        "job_title": "Growth Marketing Manager",
        "manager_employee_id": "E1004",
        "manager": {"employee_id": "E1004", "name": "David Kim", "job_title": "VP of Operations"},
    },
    "E1003": {
        "employee_id": "E1003",
        "name": "Carol Taylor",
        "email": "carol.taylor@enterprise.internal",
        "department": "Human Resources",
        "job_title": "People Operations Lead",
        "manager_employee_id": "E1004",
        "manager": {"employee_id": "E1004", "name": "David Kim", "job_title": "VP of Operations"},
    },
    "E1004": {
        "employee_id": "E1004",
        "name": "David Kim",
        "email": "david.kim@enterprise.internal",
        "department": "Executive",
        "job_title": "VP of Operations",
        "manager_employee_id": None,
        "manager": None,
    },
}

MOCK_LEAVE = {
    "E1001": {
        "employee_id": "E1001",
        "name": "Alice Chen",
        "department": "Engineering",
        "total_allocated_days": 34.0,
        "total_used_days": 10.0,
        "total_remaining_days": 24.0,
        "balances": [
            {"leave_type": "annual", "total_days": 24.0, "used_days": 8.0, "remaining_days": 16.0},
            {"leave_type": "sick", "total_days": 10.0, "used_days": 2.0, "remaining_days": 8.0},
        ],
    },
    "E1002": {
        "employee_id": "E1002",
        "name": "Bob Martinez",
        "department": "Marketing",
        "total_allocated_days": 34.0,
        "total_used_days": 14.0,
        "total_remaining_days": 20.0,
        "balances": [
            {"leave_type": "annual", "total_days": 24.0, "used_days": 14.0, "remaining_days": 10.0},
            {"leave_type": "sick", "total_days": 10.0, "used_days": 0.0, "remaining_days": 10.0},
        ],
    },
}

MOCK_TRAVEL = {
    "E1001": {
        "employee_id": "E1001",
        "name": "Alice Chen",
        "department": "Engineering",
        "total_claims": 2,
        "total_amount": 425.0,
        "approved_amount": 425.0,
        "submitted_amount": 0.0,
        "by_category": {"flights": 350.0, "meals": 75.0},
        "expenses": [
            {"expense_id": 1, "expense_date": "2026-02-14", "category": "flights", "amount": 350.0, "status": "approved", "description": "Domestic flight to Seattle for architecture review"},
            {"expense_id": 2, "expense_date": "2026-02-15", "category": "meals", "amount": 75.0, "status": "approved", "description": "Client working dinner in Seattle"},
        ],
    },
    "E1002": {
        "employee_id": "E1002",
        "name": "Bob Martinez",
        "department": "Marketing",
        "total_claims": 1,
        "total_amount": 195.0,
        "approved_amount": 0.0,
        "submitted_amount": 195.0,
        "by_category": {"lodging": 195.0},
        "expenses": [
            {"expense_id": 3, "expense_date": "2026-03-01", "category": "lodging", "amount": 195.0, "status": "submitted", "description": "Hotel stay for annual growth marketing expo"},
        ],
    },
}


def mock_get_employee_summary(employee_id: str, config=None):
    clean = str(employee_id).strip()
    return MOCK_EMPLOYEES.get(clean)


def mock_get_employee_leave_summary(employee_id: str, config=None):
    clean = str(employee_id).strip()
    return MOCK_LEAVE.get(clean)


def mock_get_employee_travel_summary(employee_id: str, config=None):
    clean = str(employee_id).strip()
    return MOCK_TRAVEL.get(clean)


def mock_list_employees_by_department(department: str, config=None):
    clean = str(department).strip().lower()
    return [
        {"employee_id": emp["employee_id"], "name": emp["name"], "job_title": emp["job_title"], "department": emp["department"]}
        for emp in MOCK_EMPLOYEES.values()
        if emp["department"].lower() == clean
    ]


def setup_mock_db_if_offline(test_case_or_cls):
    """If Postgres server is not running on localhost:5432, patch database tools with mock functions."""
    if not test_connection(DEFAULT_DB_CONFIG):
        p1 = patch("app.tools.database_tools.get_employee_summary", side_effect=mock_get_employee_summary)
        p2 = patch("app.tools.database_tools.get_employee_leave_summary", side_effect=mock_get_employee_leave_summary)
        p3 = patch("app.tools.database_tools.get_employee_travel_summary", side_effect=mock_get_employee_travel_summary)
        p4 = patch("app.tools.database_tools.list_employees_by_department", side_effect=mock_list_employees_by_department)
        p1.start()
        p2.start()
        p3.start()
        p4.start()
        return [p1, p2, p3, p4]
    return []
