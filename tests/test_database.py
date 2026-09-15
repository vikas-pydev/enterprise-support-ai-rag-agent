import unittest
from datetime import date
from decimal import Decimal
import psycopg2

from app.database.config import DatabaseConfig
from app.database.connection import (
    test_connection,
    ensure_database_exists,
    get_db_connection,
)
from app.database.schema import init_db, drop_tables
from app.database.seed import seed_db
from app.database.exceptions import DatabaseError
from app.database.repository import (
    get_employee_by_id,
    get_employee_by_email,
    list_employees_by_department,
    get_employee_manager,
    get_leave_balances,
    get_leave_balance_by_type,
    get_travel_expenses,
    get_travel_expenses_by_status,
    get_total_travel_expenses,
    get_travel_expenses_in_date_range,
    get_employee_summary,
    get_employee_leave_summary,
    get_employee_travel_summary,
    get_department_employee_summary,
    get_pending_travel_expenses,
)

# Isolated test database to ensure developer database is never corrupted
TEST_DB_CONFIG = DatabaseConfig(name="enterprise_support_test")


class TestPostgreSQLDatabase(unittest.TestCase):
    """Automated test suite validating PostgreSQL database foundation and safe query layer (Phase 3)."""

    @classmethod
    def setUpClass(cls):
        """Prepare isolated test database with initialized schema and seed data."""
        if not test_connection(TEST_DB_CONFIG):
            raise unittest.SkipTest(f"PostgreSQL server is not running on {TEST_DB_CONFIG.host}:{TEST_DB_CONFIG.port}")
        ensure_database_exists(TEST_DB_CONFIG)
        drop_tables(TEST_DB_CONFIG)
        init_db(TEST_DB_CONFIG)

    @classmethod
    def tearDownClass(cls):
        """Clean up test tables after suite execution."""
        drop_tables(TEST_DB_CONFIG)

    def setUp(self):
        """Reset and re-seed tables before each test to guarantee deterministic state."""
        drop_tables(TEST_DB_CONFIG)
        init_db(TEST_DB_CONFIG)
        seed_db(TEST_DB_CONFIG)

    # -----------------------------------------------------------------
    # Foundation Tests
    # -----------------------------------------------------------------

    def test_01_database_connection_and_configuration(self):
        """Verify database configuration and active server connectivity."""
        self.assertTrue(
            test_connection(TEST_DB_CONFIG),
            f"Failed to connect to test database '{TEST_DB_CONFIG.name}' at {TEST_DB_CONFIG.host}:{TEST_DB_CONFIG.port}",
        )
        self.assertEqual(TEST_DB_CONFIG.port, 5432)
        self.assertEqual(TEST_DB_CONFIG.name, "enterprise_support_test")

    def test_02_schema_initialization(self):
        """Verify all three tables exist in PostgreSQL information_schema."""
        expected_tables = {"employees", "leave_balances", "travel_expenses"}
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """
        with get_db_connection(TEST_DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                found_tables = {row[0] for row in cur.fetchall()}

        self.assertTrue(
            expected_tables.issubset(found_tables),
            f"Expected tables {expected_tables}, but found {found_tables}",
        )

    def test_03_employee_insertion_and_retrieval(self):
        """Verify inserting and querying a new employee record."""
        new_emp_id = "E9999"
        with get_db_connection(TEST_DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO employees (employee_id, name, email, department, job_title, manager_employee_id)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (new_emp_id, "Jane Doe", "jane.doe@enterprise.internal", "Security", "Security Engineer", "E1004"),
                )
            conn.commit()

        emp = get_employee_by_id(new_emp_id, config=TEST_DB_CONFIG)
        self.assertIsNotNone(emp)
        self.assertEqual(emp["name"], "Jane Doe")
        self.assertEqual(emp["department"], "Security")
        self.assertEqual(emp["job_title"], "Security Engineer")
        self.assertEqual(emp["manager_employee_id"], "E1004")

    def test_04_leave_balance_insertion_and_calculation(self):
        """Verify leave balance record, remaining days calculation, and constraints."""
        balances = get_leave_balances("E1001", config=TEST_DB_CONFIG)
        self.assertGreater(len(balances), 0)

        annual_leave = next(b for b in balances if b["leave_type"] == "annual")
        self.assertEqual(annual_leave["total_days"], Decimal("24.0"))
        self.assertEqual(annual_leave["used_days"], Decimal("8.0"))
        # Verify generated column: remaining_days = total - used (24 - 8 = 16)
        self.assertEqual(annual_leave["remaining_days"], Decimal("16.0"))

    def test_05_travel_expense_insertion_and_retrieval(self):
        """Verify travel expenses insertion and retrieval."""
        expenses = get_travel_expenses("E1001", config=TEST_DB_CONFIG)
        self.assertEqual(len(expenses), 2)

        categories = {e["category"] for e in expenses}
        self.assertIn("flights", categories)
        self.assertIn("meals", categories)

    def test_06_foreign_key_integrity(self):
        """Verify foreign key rejects records referencing nonexistent employee."""
        with get_db_connection(TEST_DB_CONFIG) as conn:
            with conn.cursor() as cur:
                with self.assertRaises(psycopg2.IntegrityError):
                    cur.execute(
                        """
                        INSERT INTO travel_expenses (employee_id, expense_date, category, amount, description)
                        VALUES ('NON_EXISTENT_EMP', '2026-03-01', 'meals', 50.00, 'Invalid expense');
                        """
                    )
            conn.rollback()

    def test_07_unique_constraints(self):
        """Verify unique constraints on employee_id and composite (employee_id, leave_type)."""
        with get_db_connection(TEST_DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # 1. Duplicate employee_id
                with self.assertRaises(psycopg2.IntegrityError):
                    cur.execute(
                        """
                        INSERT INTO employees (employee_id, name, email, department, job_title)
                        VALUES ('E1001', 'Duplicate Alice', 'diff.email@enterprise.internal', 'Eng', 'Dev');
                        """
                    )
            conn.rollback()

            with conn.cursor() as cur:
                # 2. Duplicate leave_type for same employee
                with self.assertRaises(psycopg2.IntegrityError):
                    cur.execute(
                        """
                        INSERT INTO leave_balances (employee_id, leave_type, total_days, used_days)
                        VALUES ('E1001', 'annual', 10.0, 0.0);
                        """
                    )
            conn.rollback()

    # -----------------------------------------------------------------
    # Safe Query Layer Tests
    # -----------------------------------------------------------------

    def test_08_employee_lookup_by_id_and_email(self):
        """Verify fetching employees by ID and email."""
        # By ID
        emp_by_id = get_employee_by_id("E1001", config=TEST_DB_CONFIG)
        self.assertIsNotNone(emp_by_id)
        self.assertEqual(emp_by_id["name"], "Alice Chen")
        self.assertEqual(emp_by_id["email"], "alice.chen@enterprise.internal")

        # By Email (case-insensitive)
        emp_by_email = get_employee_by_email("ALICE.CHEN@enterprise.internal", config=TEST_DB_CONFIG)
        self.assertIsNotNone(emp_by_email)
        self.assertEqual(emp_by_email["employee_id"], "E1001")

    def test_09_department_filtering(self):
        """Verify listing employees filtered by department."""
        eng_employees = list_employees_by_department("Engineering", config=TEST_DB_CONFIG)
        self.assertEqual(len(eng_employees), 1)
        self.assertEqual(eng_employees[0]["name"], "Alice Chen")

        mkt_employees = list_employees_by_department("marketing", config=TEST_DB_CONFIG)
        self.assertEqual(len(mkt_employees), 1)
        self.assertEqual(mkt_employees[0]["name"], "Bob Martinez")

    def test_10_manager_lookup(self):
        """Verify fetching an employee's direct manager."""
        # Alice Chen (E1001) reports to David Kim (E1004)
        manager = get_employee_manager("E1001", config=TEST_DB_CONFIG)
        self.assertIsNotNone(manager)
        self.assertEqual(manager["employee_id"], "E1004")
        self.assertEqual(manager["name"], "David Kim")
        self.assertEqual(manager["job_title"], "VP of Operations")

        # David Kim (E1004) has no manager (top of hierarchy)
        top_manager = get_employee_manager("E1004", config=TEST_DB_CONFIG)
        self.assertIsNone(top_manager)

    def test_11_leave_balance_specific_type(self):
        """Verify querying specific leave type for an employee."""
        annual = get_leave_balance_by_type("E1001", "annual", config=TEST_DB_CONFIG)
        self.assertIsNotNone(annual)
        self.assertEqual(annual["total_days"], Decimal("24.0"))
        self.assertEqual(annual["used_days"], Decimal("8.0"))
        self.assertEqual(annual["remaining_days"], Decimal("16.0"))

        sick = get_leave_balance_by_type("E1001", "sick", config=TEST_DB_CONFIG)
        self.assertIsNotNone(sick)
        self.assertEqual(sick["remaining_days"], Decimal("8.0"))

        # Non-existent leave type returns None cleanly
        maternity = get_leave_balance_by_type("E1001", "maternity", config=TEST_DB_CONFIG)
        self.assertIsNone(maternity)

    def test_12_travel_expense_filtering_by_status(self):
        """Verify querying travel expenses filtered by status."""
        approved = get_travel_expenses_by_status("E1001", "approved", config=TEST_DB_CONFIG)
        self.assertEqual(len(approved), 2)

        submitted = get_travel_expenses_by_status("E1001", "submitted", config=TEST_DB_CONFIG)
        self.assertEqual(len(submitted), 0)

        bob_submitted = get_travel_expenses_by_status("E1002", "submitted", config=TEST_DB_CONFIG)
        self.assertEqual(len(bob_submitted), 1)
        self.assertEqual(bob_submitted[0]["amount"], Decimal("195.00"))

    def test_13_travel_expense_date_range_filtering(self):
        """Verify querying travel expenses within an inclusive date range."""
        # E1001 has expenses on 2026-02-14 and 2026-02-15
        range_expenses = get_travel_expenses_in_date_range(
            "E1001",
            start_date=date(2026, 2, 14),
            end_date=date(2026, 2, 14),
            config=TEST_DB_CONFIG,
        )
        self.assertEqual(len(range_expenses), 1)
        self.assertEqual(range_expenses[0]["category"], "flights")

        both = get_travel_expenses_in_date_range(
            "E1001",
            start_date="2026-02-01",
            end_date="2026-02-28",
            config=TEST_DB_CONFIG,
        )
        self.assertEqual(len(both), 2)

        outside_range = get_travel_expenses_in_date_range(
            "E1001",
            start_date="2026-03-01",
            end_date="2026-03-31",
            config=TEST_DB_CONFIG,
        )
        self.assertEqual(len(outside_range), 0)

    def test_14_travel_expense_aggregation(self):
        """Verify total expense summation overall and by status."""
        # E1001: $350 (flights) + $75 (meals) = $425.00
        total_all = get_total_travel_expenses("E1001", config=TEST_DB_CONFIG)
        self.assertEqual(total_all, 425.00)

        total_approved = get_total_travel_expenses("E1001", status="approved", config=TEST_DB_CONFIG)
        self.assertEqual(total_approved, 425.00)

        total_rejected = get_total_travel_expenses("E1001", status="rejected", config=TEST_DB_CONFIG)
        self.assertEqual(total_rejected, 0.0)

    def test_15_clean_empty_result_for_unknown_entities(self):
        """Verify unknown employee queries return clean empty values without raising exceptions."""
        unknown_id = "UNKNOWN_EMP_999"
        self.assertIsNone(get_employee_by_id(unknown_id, config=TEST_DB_CONFIG))
        self.assertIsNone(get_employee_by_email("nobody@enterprise.internal", config=TEST_DB_CONFIG))
        self.assertEqual(list_employees_by_department("NonExistentDept", config=TEST_DB_CONFIG), [])
        self.assertIsNone(get_employee_manager(unknown_id, config=TEST_DB_CONFIG))
        self.assertEqual(get_leave_balances(unknown_id, config=TEST_DB_CONFIG), [])
        self.assertIsNone(get_leave_balance_by_type(unknown_id, "annual", config=TEST_DB_CONFIG))
        self.assertEqual(get_travel_expenses(unknown_id, config=TEST_DB_CONFIG), [])
        self.assertEqual(get_total_travel_expenses(unknown_id, config=TEST_DB_CONFIG), 0.0)

    def test_16_sql_injection_defense(self):
        """Verify parameterized queries treat SQL injection payloads strictly as literal values."""
        # Attempted SQL injection to bypass employee_id filter and dump all employees
        injection_payload = "'E1001' OR '1'='1"
        result = get_employee_by_id(injection_payload, config=TEST_DB_CONFIG)
        # Must treat payload as literal employee_id string and return None (no employee with that ID)
        self.assertIsNone(
            result,
            "SQL injection payload should return None, but returned a record!",
        )

        # Destructive injection attempt
        drop_attempt = "E1001'; DROP TABLE employees CASCADE; --"
        drop_result = get_employee_by_id(drop_attempt, config=TEST_DB_CONFIG)
        self.assertIsNone(drop_result)

        # Verify employees table is still intact and not dropped
        alice = get_employee_by_id("E1001", config=TEST_DB_CONFIG)
        self.assertIsNotNone(alice)
        self.assertEqual(alice["name"], "Alice Chen")

    def test_17_sanitized_database_error_handling(self):
        """Verify database errors raise sanitized DatabaseError without exposing secrets."""
        # Misconfigured invalid port to induce a connection error
        broken_config = DatabaseConfig(name="enterprise_support_test", port=9999, connect_timeout=1)
        with self.assertRaises(DatabaseError) as ctx:
            get_employee_by_id("E1001", config=broken_config)

        err_msg = str(ctx.exception)
        # Must not expose the password in the exception message
        self.assertNotIn(broken_config.password, err_msg)
        self.assertIn("Failed to fetch employee", err_msg)

    # -----------------------------------------------------------------
    # Business SQL & Relational Analytics Tests (Task 3)
    # -----------------------------------------------------------------

    def test_18_employee_summary_with_manager_join(self):
        """Verify get_employee_summary performs relational self-JOIN for manager details."""
        summary = get_employee_summary("E1001", config=TEST_DB_CONFIG)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["employee_id"], "E1001")
        self.assertEqual(summary["name"], "Alice Chen")
        self.assertEqual(summary["department"], "Engineering")
        self.assertIsNotNone(summary["manager"])
        self.assertEqual(summary["manager"]["employee_id"], "E1004")
        self.assertEqual(summary["manager"]["name"], "David Kim")
        self.assertEqual(summary["manager"]["job_title"], "VP of Operations")

        # Top of hierarchy (David Kim has no manager)
        vp_summary = get_employee_summary("E1004", config=TEST_DB_CONFIG)
        self.assertIsNotNone(vp_summary)
        self.assertIsNone(vp_summary["manager"])

    def test_19_employee_leave_summary_aggregation(self):
        """Verify get_employee_leave_summary aggregates total, used, and remaining PTO."""
        # Alice Chen: annual (24 total, 8 used, 16 remaining) + sick (10 total, 2 used, 8 remaining)
        leave_summary = get_employee_leave_summary("E1001", config=TEST_DB_CONFIG)
        self.assertIsNotNone(leave_summary)
        self.assertEqual(leave_summary["name"], "Alice Chen")
        self.assertEqual(leave_summary["total_allocated_days"], 34.0)
        self.assertEqual(leave_summary["total_used_days"], 10.0)
        self.assertEqual(leave_summary["total_remaining_days"], 24.0)
        self.assertEqual(len(leave_summary["balances"]), 2)

    def test_20_employee_travel_summary_status_and_category_breakdown(self):
        """Verify get_employee_travel_summary aggregates amounts by approval status and expense category."""
        # E1001 has $350 (flights, approved) and $75 (meals, approved) = $425 approved
        travel_summary = get_employee_travel_summary("E1001", config=TEST_DB_CONFIG)
        self.assertIsNotNone(travel_summary)
        self.assertEqual(travel_summary["total_claims"], 2)
        self.assertEqual(travel_summary["total_amount"], 425.0)
        self.assertEqual(travel_summary["approved_amount"], 425.0)
        self.assertEqual(travel_summary["submitted_amount"], 0.0)
        self.assertIn("flights", travel_summary["by_category"])
        self.assertEqual(travel_summary["by_category"]["flights"], 350.0)
        self.assertEqual(travel_summary["by_category"]["meals"], 75.0)

    def test_21_department_summary_with_travel_spend_join(self):
        """Verify get_department_employee_summary aggregates headcount and departmental travel spend."""
        # Engineering: Alice Chen ($425 travel spend)
        eng_summary = get_department_employee_summary("Engineering", config=TEST_DB_CONFIG)
        self.assertEqual(eng_summary["employee_count"], 1)
        self.assertEqual(eng_summary["total_travel_spend"], 425.0)
        self.assertEqual(eng_summary["employees"][0]["name"], "Alice Chen")

        # Marketing: Bob Martinez ($195 travel spend)
        mkt_summary = get_department_employee_summary("Marketing", config=TEST_DB_CONFIG)
        self.assertEqual(mkt_summary["employee_count"], 1)
        self.assertEqual(mkt_summary["total_travel_spend"], 195.0)

    def test_22_pending_travel_expenses_lookup(self):
        """Verify get_pending_travel_expenses returns submitted claims with employee metadata."""
        # Company-wide pending claims: Bob Martinez ($195 lodging) is submitted
        pending_all = get_pending_travel_expenses(config=TEST_DB_CONFIG)
        self.assertEqual(len(pending_all), 1)
        self.assertEqual(pending_all[0]["employee_name"], "Bob Martinez")
        self.assertEqual(pending_all[0]["department"], "Marketing")
        self.assertEqual(pending_all[0]["amount"], Decimal("195.00"))
        self.assertEqual(pending_all[0]["status"], "submitted")

        # Filtered by E1002 (Bob)
        pending_bob = get_pending_travel_expenses("E1002", config=TEST_DB_CONFIG)
        self.assertEqual(len(pending_bob), 1)

        # Filtered by E1001 (Alice has 0 pending; both approved)
        pending_alice = get_pending_travel_expenses("E1001", config=TEST_DB_CONFIG)
        self.assertEqual(len(pending_alice), 0)

    def test_23_sql_injection_defense_on_business_queries(self):
        """Verify business query operations treat injection strings as literals and handle safely."""
        injection_payload = "'E1001' OR '1'='1"
        self.assertIsNone(get_employee_summary(injection_payload, config=TEST_DB_CONFIG))
        self.assertIsNone(get_employee_leave_summary(injection_payload, config=TEST_DB_CONFIG))
        self.assertIsNone(get_employee_travel_summary(injection_payload, config=TEST_DB_CONFIG))

        dept_injection = "Engineering'; DROP TABLE travel_expenses CASCADE; --"
        dept_res = get_department_employee_summary(dept_injection, config=TEST_DB_CONFIG)
        self.assertEqual(dept_res["employee_count"], 0)
        self.assertEqual(dept_res["total_travel_spend"], 0.0)

        # Ensure travel_expenses was not dropped
        self.assertGreater(len(get_travel_expenses("E1001", config=TEST_DB_CONFIG)), 0)

    def test_24_data_integrity_negative_days_constraint(self):
        """Verify check constraints prevent negative total days or used_days exceeding total_days."""
        with get_db_connection(TEST_DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # Negative total days
                with self.assertRaises(psycopg2.IntegrityError):
                    cur.execute(
                        """
                        INSERT INTO leave_balances (employee_id, leave_type, total_days, used_days)
                        VALUES ('E1001', 'sabbatical', -5.0, 0.0);
                        """
                    )
            conn.rollback()

            with conn.cursor() as cur:
                # used_days > total_days
                with self.assertRaises(psycopg2.IntegrityError):
                    cur.execute(
                        """
                        INSERT INTO leave_balances (employee_id, leave_type, total_days, used_days)
                        VALUES ('E1001', 'sabbatical', 10.0, 15.0);
                        """
                    )
            conn.rollback()

    def test_25_empty_result_behavior_on_business_queries(self):
        """Verify non-existent employee ID returns clean None without exceptions."""
        non_existent = "NON_EXISTENT_999"
        self.assertIsNone(get_employee_summary(non_existent, config=TEST_DB_CONFIG))
        self.assertIsNone(get_employee_leave_summary(non_existent, config=TEST_DB_CONFIG))
        self.assertIsNone(get_employee_travel_summary(non_existent, config=TEST_DB_CONFIG))
        self.assertEqual(get_pending_travel_expenses(non_existent, config=TEST_DB_CONFIG), [])


if __name__ == "__main__":
    unittest.main()

