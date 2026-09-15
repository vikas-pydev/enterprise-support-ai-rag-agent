from datetime import date
from decimal import Decimal
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    _Psycopg2Error = psycopg2.Error
except ImportError:
    psycopg2 = None
    RealDictCursor = None
    _Psycopg2Error = Exception

from app.database.config import DatabaseConfig, DEFAULT_DB_CONFIG
from app.database.connection import get_db_connection
from app.database.exceptions import DatabaseError


# =====================================================================
# 1. EMPLOYEE REPOSITORY OPERATIONS
# =====================================================================

def get_employee_by_id(
    employee_id: str,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> dict | None:
    """Fetch employee by unique business identifier (e.g. 'E1001').

    Returns None if employee is not found.
    Uses parameterized SQL to prevent injection.
    """
    query = """
    SELECT id, employee_id, name, email, department, job_title, manager_employee_id, created_at
    FROM employees
    WHERE employee_id = %s;
    """
    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(employee_id),))
                res = cur.fetchone()
                return dict(res) if res else None
    except psycopg2.Error as e:
        raise DatabaseError(f"Failed to fetch employee '{employee_id}'", original_error=e)


# Alias for backward compatibility
get_employee = get_employee_by_id


def get_employee_by_email(
    email: str,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> dict | None:
    """Fetch employee by unique email address."""
    query = """
    SELECT id, employee_id, name, email, department, job_title, manager_employee_id, created_at
    FROM employees
    WHERE LOWER(email) = LOWER(%s);
    """
    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(email).strip(),))
                res = cur.fetchone()
                return dict(res) if res else None
    except psycopg2.Error as e:
        raise DatabaseError(f"Failed to fetch employee by email '{email}'", original_error=e)


def list_employees_by_department(
    department: str,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> list[dict]:
    """Fetch all employees working in a given department."""
    query = """
    SELECT employee_id, name, email, department, job_title, manager_employee_id, created_at
    FROM employees
    WHERE LOWER(department) = LOWER(%s)
    ORDER BY name;
    """
    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(department).strip(),))
                return [dict(row) for row in cur.fetchall()]
    except psycopg2.Error as e:
        raise DatabaseError(f"Failed to fetch department '{department}' employees", original_error=e)


# Alias for backward compatibility
get_department_employees = list_employees_by_department


def get_employee_manager(
    employee_id: str,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> dict | None:
    """Fetch the direct manager's employee record for a given employee.

    Returns None if the employee has no manager or does not exist.
    """
    query = """
    SELECT m.id, m.employee_id, m.name, m.email, m.department, m.job_title, m.created_at
    FROM employees e
    JOIN employees m ON e.manager_employee_id = m.employee_id
    WHERE e.employee_id = %s;
    """
    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(employee_id),))
                res = cur.fetchone()
                return dict(res) if res else None
    except psycopg2.Error as e:
        raise DatabaseError(f"Failed to fetch manager for employee '{employee_id}'", original_error=e)


# =====================================================================
# 2. LEAVE BALANCE REPOSITORY OPERATIONS
# =====================================================================

def get_leave_balances(
    employee_id: str,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> list[dict]:
    """Fetch all leave balances for an employee."""
    query = """
    SELECT id, employee_id, leave_type, total_days, used_days, remaining_days, updated_at
    FROM leave_balances
    WHERE employee_id = %s
    ORDER BY leave_type;
    """
    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(employee_id),))
                return [dict(row) for row in cur.fetchall()]
    except psycopg2.Error as e:
        raise DatabaseError(f"Failed to fetch leave balances for '{employee_id}'", original_error=e)


def get_leave_balance_by_type(
    employee_id: str,
    leave_type: str,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> dict | None:
    """Fetch a specific leave balance record (e.g. 'annual', 'sick') for an employee."""
    query = """
    SELECT id, employee_id, leave_type, total_days, used_days, remaining_days, updated_at
    FROM leave_balances
    WHERE employee_id = %s AND LOWER(leave_type) = LOWER(%s);
    """
    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(employee_id), str(leave_type).strip()))
                res = cur.fetchone()
                return dict(res) if res else None
    except psycopg2.Error as e:
        raise DatabaseError(
            f"Failed to fetch '{leave_type}' leave balance for '{employee_id}'",
            original_error=e,
        )


# =====================================================================
# 3. TRAVEL EXPENSE REPOSITORY OPERATIONS
# =====================================================================

def get_travel_expenses(
    employee_id: str,
    status: str | None = None,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> list[dict]:
    """Fetch travel expenses for an employee, optionally filtered by status."""
    if status is not None:
        query = """
        SELECT id, employee_id, expense_date, category, amount, currency, status, description, created_at
        FROM travel_expenses
        WHERE employee_id = %s AND LOWER(status) = LOWER(%s)
        ORDER BY expense_date DESC;
        """
        params = (str(employee_id), str(status).strip())
    else:
        query = """
        SELECT id, employee_id, expense_date, category, amount, currency, status, description, created_at
        FROM travel_expenses
        WHERE employee_id = %s
        ORDER BY expense_date DESC;
        """
        params = (str(employee_id),)

    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
    except psycopg2.Error as e:
        raise DatabaseError(f"Failed to fetch travel expenses for '{employee_id}'", original_error=e)


def get_travel_expenses_by_status(
    employee_id: str,
    status: str,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> list[dict]:
    """Fetch travel expenses for an employee filtered by a specific status ('submitted', 'approved', 'reimbursed')."""
    return get_travel_expenses(employee_id=employee_id, status=status, config=config)


def get_total_travel_expenses(
    employee_id: str,
    status: str | None = None,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> float:
    """Calculate the sum total of travel expenses for an employee.

    If status is provided, sums only expenses matching that status (e.g., 'approved').
    Returns 0.0 if no expenses match.
    """
    if status is not None:
        query = """
        SELECT COALESCE(SUM(amount), 0.0) AS total
        FROM travel_expenses
        WHERE employee_id = %s AND LOWER(status) = LOWER(%s);
        """
        params = (str(employee_id), str(status).strip())
    else:
        query = """
        SELECT COALESCE(SUM(amount), 0.0) AS total
        FROM travel_expenses
        WHERE employee_id = %s;
        """
        params = (str(employee_id),)

    try:
        with get_db_connection(config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                res = cur.fetchone()
                return float(res[0]) if res and res[0] is not None else 0.0
    except psycopg2.Error as e:
        raise DatabaseError(f"Failed to calculate total expenses for '{employee_id}'", original_error=e)


# Alias for backward compatibility
get_employee_total_expense = get_total_travel_expenses


def get_travel_expenses_in_date_range(
    employee_id: str,
    start_date: str | date,
    end_date: str | date,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> list[dict]:
    """Fetch travel expenses for an employee within an inclusive date range [start_date, end_date]."""
    query = """
    SELECT id, employee_id, expense_date, category, amount, currency, status, description, created_at
    FROM travel_expenses
    WHERE employee_id = %s AND expense_date >= %s AND expense_date <= %s
    ORDER BY expense_date ASC;
    """
    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(employee_id), start_date, end_date))
                return [dict(row) for row in cur.fetchall()]
    except psycopg2.Error as e:
        raise DatabaseError(
            f"Failed to fetch date-range expenses for '{employee_id}' between {start_date} and {end_date}",
            original_error=e,
        )


# =====================================================================
# 4. BUSINESS-LEVEL ANALYTICAL QUERY OPERATIONS
# =====================================================================

def get_employee_summary(
    employee_id: str,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> dict | None:
    """Fetch a consolidated employee profile including direct manager details via relational self-JOIN."""
    query = """
    SELECT
        e.id,
        e.employee_id,
        e.name,
        e.email,
        e.department,
        e.job_title,
        e.created_at,
        m.employee_id AS manager_employee_id,
        m.name AS manager_name,
        m.email AS manager_email,
        m.job_title AS manager_job_title
    FROM employees e
    LEFT JOIN employees m ON e.manager_employee_id = m.employee_id
    WHERE e.employee_id = %s;
    """
    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(employee_id),))
                row = cur.fetchone()
                if not row:
                    return None

                manager_info = None
                if row["manager_employee_id"]:
                    manager_info = {
                        "employee_id": row["manager_employee_id"],
                        "name": row["manager_name"],
                        "email": row["manager_email"],
                        "job_title": row["manager_job_title"],
                    }

                return {
                    "employee_id": row["employee_id"],
                    "name": row["name"],
                    "email": row["email"],
                    "department": row["department"],
                    "job_title": row["job_title"],
                    "created_at": row["created_at"],
                    "manager": manager_info,
                }
    except psycopg2.Error as e:
        raise DatabaseError(f"Failed to fetch employee summary for '{employee_id}'", original_error=e)


def get_employee_leave_summary(
    employee_id: str,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> dict | None:
    """Fetch employee leave overview with totals and individual leave categories via relational JOIN."""
    emp = get_employee_by_id(employee_id, config=config)
    if not emp:
        return None

    query = """
    SELECT
        leave_type,
        total_days,
        used_days,
        remaining_days,
        updated_at
    FROM leave_balances
    WHERE employee_id = %s
    ORDER BY leave_type;
    """
    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(employee_id),))
                balances = [dict(row) for row in cur.fetchall()]

                total_allocated = sum(float(b["total_days"]) for b in balances)
                total_used = sum(float(b["used_days"]) for b in balances)
                total_remaining = sum(float(b["remaining_days"]) for b in balances)

                return {
                    "employee_id": emp["employee_id"],
                    "name": emp["name"],
                    "department": emp["department"],
                    "total_allocated_days": total_allocated,
                    "total_used_days": total_used,
                    "total_remaining_days": total_remaining,
                    "balances": balances,
                }
    except psycopg2.Error as e:
        raise DatabaseError(f"Failed to fetch leave summary for '{employee_id}'", original_error=e)


def get_employee_travel_summary(
    employee_id: str,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> dict | None:
    """Fetch a comprehensive travel expense summary including status and category rollups via aggregations."""
    emp = get_employee_by_id(employee_id, config=config)
    if not emp:
        return None

    # Aggregations by status and category
    query_aggregates = """
    SELECT
        COUNT(*) AS total_claims,
        COALESCE(SUM(amount), 0.0) AS total_amount,
        COALESCE(SUM(CASE WHEN LOWER(status) = 'approved' THEN amount ELSE 0.0 END), 0.0) AS approved_amount,
        COALESCE(SUM(CASE WHEN LOWER(status) = 'submitted' THEN amount ELSE 0.0 END), 0.0) AS submitted_amount,
        COALESCE(SUM(CASE WHEN LOWER(status) = 'reimbursed' THEN amount ELSE 0.0 END), 0.0) AS reimbursed_amount
    FROM travel_expenses
    WHERE employee_id = %s;
    """

    query_categories = """
    SELECT category, COALESCE(SUM(amount), 0.0) AS category_total
    FROM travel_expenses
    WHERE employee_id = %s
    GROUP BY category
    ORDER BY category_total DESC;
    """

    expenses = get_travel_expenses(employee_id, config=config)

    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query_aggregates, (str(employee_id),))
                agg = cur.fetchone()

                cur.execute(query_categories, (str(employee_id),))
                cat_rows = cur.fetchall()
                by_category = {row["category"]: float(row["category_total"]) for row in cat_rows}

                return {
                    "employee_id": emp["employee_id"],
                    "name": emp["name"],
                    "department": emp["department"],
                    "total_claims": int(agg["total_claims"]) if agg else 0,
                    "total_amount": float(agg["total_amount"]) if agg else 0.0,
                    "approved_amount": float(agg["approved_amount"]) if agg else 0.0,
                    "submitted_amount": float(agg["submitted_amount"]) if agg else 0.0,
                    "reimbursed_amount": float(agg["reimbursed_amount"]) if agg else 0.0,
                    "by_category": by_category,
                    "expenses": expenses,
                }
    except psycopg2.Error as e:
        raise DatabaseError(f"Failed to fetch travel summary for '{employee_id}'", original_error=e)


def get_department_employee_summary(
    department: str,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> dict:
    """Fetch department overview including headcount, employee roster, and departmental travel spend via JOIN."""
    query = """
    SELECT
        e.employee_id,
        e.name,
        e.email,
        e.job_title,
        COALESCE(SUM(te.amount), 0.0) AS employee_travel_spend
    FROM employees e
    LEFT JOIN travel_expenses te ON e.employee_id = te.employee_id
    WHERE LOWER(e.department) = LOWER(%s)
    GROUP BY e.employee_id, e.name, e.email, e.job_title
    ORDER BY e.name;
    """
    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (str(department).strip(),))
                rows = [dict(r) for r in cur.fetchall()]

                total_dept_spend = sum(float(r["employee_travel_spend"]) for r in rows)

                return {
                    "department": department,
                    "employee_count": len(rows),
                    "total_travel_spend": total_dept_spend,
                    "employees": rows,
                }
    except psycopg2.Error as e:
        raise DatabaseError(f"Failed to fetch summary for department '{department}'", original_error=e)


def get_pending_travel_expenses(
    employee_id: str | None = None,
    config: DatabaseConfig = DEFAULT_DB_CONFIG,
) -> list[dict]:
    """Fetch all pending ('submitted') travel expenses joined with employee name and department.

    If employee_id is specified, filters by that employee.
    If employee_id is None, returns all pending expenses across the company.
    """
    if employee_id:
        query = """
        SELECT
            te.id,
            te.employee_id,
            e.name AS employee_name,
            e.department,
            te.expense_date,
            te.category,
            te.amount,
            te.currency,
            te.status,
            te.description,
            te.created_at
        FROM travel_expenses te
        JOIN employees e ON te.employee_id = e.employee_id
        WHERE LOWER(te.status) = 'submitted' AND te.employee_id = %s
        ORDER BY te.expense_date ASC;
        """
        params = (str(employee_id),)
    else:
        query = """
        SELECT
            te.id,
            te.employee_id,
            e.name AS employee_name,
            e.department,
            te.expense_date,
            te.category,
            te.amount,
            te.currency,
            te.status,
            te.description,
            te.created_at
        FROM travel_expenses te
        JOIN employees e ON te.employee_id = e.employee_id
        WHERE LOWER(te.status) = 'submitted'
        ORDER BY te.expense_date ASC;
        """
        params = ()

    try:
        with get_db_connection(config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
    except psycopg2.Error as e:
        raise DatabaseError("Failed to fetch pending travel expenses", original_error=e)

