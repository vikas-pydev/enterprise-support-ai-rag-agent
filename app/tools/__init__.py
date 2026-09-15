"""LangChain Tool Integration Layer.

Standardized, agent-ready tool wrappers for Enterprise RAG knowledge base
and PostgreSQL structured operational database queries.
"""

from app.tools.rag_tools import ask_policy, PolicyQuestionInput
from app.tools.database_tools import (
    get_employee,
    get_leave_balance,
    get_travel_summary,
    list_department_employees,
    EmployeeIdInput,
    DepartmentInput,
)

ALL_TOOLS = [
    ask_policy,
    get_employee,
    get_leave_balance,
    get_travel_summary,
    list_department_employees,
]

__all__ = [
    "ask_policy",
    "PolicyQuestionInput",
    "get_employee",
    "get_leave_balance",
    "get_travel_summary",
    "list_department_employees",
    "EmployeeIdInput",
    "DepartmentInput",
    "ALL_TOOLS",
]
