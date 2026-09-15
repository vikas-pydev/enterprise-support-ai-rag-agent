import json
import unittest
from unittest.mock import patch, MagicMock

from app.tools import (
    ALL_TOOLS,
    ask_policy,
    get_employee,
    get_leave_balance,
    get_travel_summary,
    list_department_employees,
    PolicyQuestionInput,
    EmployeeIdInput,
    DepartmentInput,
)
from app.database.exceptions import DatabaseError
from app.rag import STANDARD_REFUSAL
from tests.mock_db_helper import setup_mock_db_if_offline


class TestLangChainTools(unittest.TestCase):
    """Unit and integration test suite for LangChain Tool Wrappers."""

    @classmethod
    def setUpClass(cls):
        cls._db_patches = setup_mock_db_if_offline(cls)

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "_db_patches", []):
            p.stop()

    def test_01_rag_tool_exists_and_has_schema(self):
        """1. Verify RAG tool exists, has proper metadata, and uses PolicyQuestionInput schema."""
        self.assertEqual(ask_policy.name, "ask_policy")
        self.assertIsNotNone(ask_policy.description)
        self.assertIn("authoritative documentation", ask_policy.description)
        self.assertIn("DO NOT USE THIS TOOL FOR", ask_policy.description)
        self.assertEqual(ask_policy.args_schema, PolicyQuestionInput)

        schema = ask_policy.args_schema.model_json_schema()
        self.assertIn("question", schema["properties"])
        self.assertEqual(schema["properties"]["question"]["type"], "string")

    @patch("app.tools.rag_tools.retrieve")
    @patch("app.tools.rag_tools.generate_answer")
    def test_02_rag_tool_calls_existing_rag_boundary(self, mock_generate, mock_retrieve):
        """2. Verify RAG tool delegates directly to existing retrieve() and generate_answer()."""
        mock_doc = "Standard domestic per diem is $75 for meals."
        mock_meta = {
            "title": "Travel Policy",
            "source": "data/travel_policy.md",
            "chunk_uid": "travel_chunk_1",
            "rerank_score": 8.5,
        }
        mock_retrieve.return_value = ([(mock_doc, 8.5, mock_meta)], MagicMock())
        mock_generate.return_value = "The per diem rate is $75 for meals."

        result = ask_policy.invoke({"question": "What is the per diem meal rate?"})

        mock_retrieve.assert_called_once()
        mock_generate.assert_called_once_with("What is the per diem meal rate?", [mock_doc])

        self.assertIsInstance(result, dict)
        self.assertEqual(result["question"], "What is the per diem meal rate?")
        self.assertEqual(result["answer"], "The per diem rate is $75 for meals.")
        self.assertFalse(result["is_refusal"])
        self.assertEqual(len(result["sources"]), 1)

    @patch("app.tools.rag_tools.retrieve")
    @patch("app.tools.rag_tools.generate_answer")
    def test_03_rag_refusal_is_preserved(self, mock_generate, mock_retrieve):
        """3. Verify RAG refusal is preserved when no relevant context exists or LLM refuses."""
        # Case A: Empty retrieval
        mock_retrieve.return_value = ([], MagicMock())
        mock_generate.return_value = STANDARD_REFUSAL

        result = ask_policy.invoke({"question": "What is the company policy on pet care?"})
        self.assertTrue(result["is_refusal"])
        self.assertEqual(result["answer"], STANDARD_REFUSAL)
        self.assertEqual(result["sources"], [])

        # Case B: Context retrieved but refusal answer generated
        mock_retrieve.return_value = ([("Unrelated text", 5.1, {"title": "Doc", "source": "f.md"})], MagicMock())
        mock_generate.return_value = "I am sorry, but the requested information is not available in the provided documents."

        result2 = ask_policy.invoke({"question": "What is the stock grant formula?"})
        self.assertTrue(result2["is_refusal"])
        self.assertEqual(result2["sources"], [])

    @patch("app.tools.rag_tools.retrieve")
    @patch("app.tools.rag_tools.generate_answer")
    def test_04_rag_citations_and_provenance_preserved(self, mock_generate, mock_retrieve):
        """4. Verify structured citations include ranks, titles, file paths, and scores."""
        mock_retrieve.return_value = (
            [
                ("Chunk 1 text", 9.2, {"title": "Leave Policy", "source": "leave.md", "chunk_uid": "c1", "rerank_score": 9.2}),
                ("Chunk 2 text", 7.8, {"title": "Leave FAQ", "source": "faq.md", "chunk_uid": "c2", "rerank_score": 7.8}),
            ],
            MagicMock(),
        )
        mock_generate.return_value = "Employees receive 20 days of annual leave."

        result = ask_policy.invoke({"question": "How many days of annual leave do employees get?"})

        self.assertFalse(result["is_refusal"])
        self.assertEqual(len(result["sources"]), 2)
        self.assertEqual(result["sources"][0]["rank"], 1)
        self.assertEqual(result["sources"][0]["title"], "Leave Policy")
        self.assertEqual(result["sources"][0]["source_file"], "leave.md")
        self.assertEqual(result["sources"][0]["chunk_uid"], "c1")
        self.assertEqual(result["sources"][0]["rerank_score"], 9.2)
        self.assertEqual(result["sources"][0]["snippet"], "Chunk 1 text")

        self.assertEqual(result["sources"][1]["rank"], 2)
        self.assertEqual(result["sources"][1]["title"], "Leave FAQ")

    def test_05_employee_tool_works(self):
        """5. Verify employee tool fetches summary with manager hierarchy from PostgreSQL."""
        result = get_employee.invoke({"employee_id": "E1001"})
        self.assertTrue(result["found"])
        self.assertIn("data", result)
        data = result["data"]
        self.assertEqual(data["employee_id"], "E1001")
        self.assertEqual(data["name"], "Alice Chen")
        self.assertEqual(data["department"], "Engineering")
        self.assertIn("manager", data)
        if data["manager"]:
            self.assertIn("name", data["manager"])

    def test_06_leave_balance_tool_works(self):
        """6. Verify leave balance tool fetches allocations, used, and remaining days."""
        result = get_leave_balance.invoke({"employee_id": "E1001"})
        self.assertTrue(result["found"])
        self.assertIn("data", result)
        data = result["data"]
        self.assertEqual(data["employee_id"], "E1001")
        self.assertIn("total_allocated_days", data)
        self.assertIn("total_used_days", data)
        self.assertIn("total_remaining_days", data)
        self.assertIn("balances", data)
        self.assertGreaterEqual(len(data["balances"]), 1)

    def test_07_travel_summary_tool_works(self):
        """7. Verify travel summary tool fetches claims, status rollups, and category totals."""
        result = get_travel_summary.invoke({"employee_id": "E1001"})
        self.assertTrue(result["found"])
        self.assertIn("data", result)
        data = result["data"]
        self.assertEqual(data["employee_id"], "E1001")
        self.assertIn("total_claims", data)
        self.assertIn("total_amount", data)
        self.assertIn("approved_amount", data)
        self.assertIn("submitted_amount", data)
        self.assertIn("by_category", data)

    def test_08_unknown_employee_handled_cleanly(self):
        """8. Verify querying a non-existent employee returns structured found: False."""
        emp_res = get_employee.invoke({"employee_id": "NON_EXISTENT_9999"})
        self.assertFalse(emp_res["found"])
        self.assertIn("not found", emp_res.get("message", "").lower())

        leave_res = get_leave_balance.invoke({"employee_id": "NON_EXISTENT_9999"})
        self.assertFalse(leave_res["found"])

        travel_res = get_travel_summary.invoke({"employee_id": "NON_EXISTENT_9999"})
        self.assertFalse(travel_res["found"])

    @patch("app.tools.database_tools.get_employee_summary")
    def test_09_database_errors_sanitized(self, mock_summary):
        """9. Verify internal DB failures do not leak connection strings, passwords, or traces."""
        mock_summary.side_effect = DatabaseError("psycopg2.OperationalError: password authentication failed for user 'postgres'")

        result = get_employee.invoke({"employee_id": "E1001"})
        self.assertFalse(result["found"])
        self.assertEqual(result.get("status"), "error")
        # Ensure sensitive database credentials or raw exceptions are NOT exposed
        self.assertNotIn("password", result.get("error", "").lower())
        self.assertNotIn("postgres", result.get("error", "").lower())
        self.assertIn("database error occurred", result.get("error", "").lower())

    def test_10_tool_inputs_validated(self):
        """10. Verify Pydantic schema validation handles empty or missing inputs."""
        empty_emp = get_employee.invoke({"employee_id": "   "})
        self.assertFalse(empty_emp["found"])
        self.assertIn("error", empty_emp)

        empty_rag = ask_policy.invoke({"question": ""})
        self.assertTrue(empty_rag["is_refusal"])

        dept_res = list_department_employees.invoke({"department": "Engineering"})
        self.assertTrue(dept_res["found"])
        self.assertGreaterEqual(dept_res["count"], 1)

    def test_11_security_boundary_no_arbitrary_sql_tool(self):
        """11. Verify no arbitrary SQL execution tools exist and tool registry is strictly safe."""
        tool_names = [t.name for t in ALL_TOOLS]
        forbidden_keywords = ["sql", "query_raw", "execute", "command", "exec", "eval", "table_scan"]

        for name in tool_names:
            for kw in forbidden_keywords:
                self.assertNotIn(
                    kw,
                    name.lower(),
                    f"Forbidden arbitrary database execution keyword '{kw}' found in tool '{name}'",
                )

        # Ensure all registered tools have explicit Pydantic args_schemas
        for t in ALL_TOOLS:
            self.assertIsNotNone(t.args_schema, f"Tool {t.name} must have a typed args_schema.")

    def test_12_tools_return_json_serializable_results(self):
        """12. Verify all tool return values can be serialized directly with json.dumps."""
        emp_res = get_employee.invoke({"employee_id": "E1001"})
        leave_res = get_leave_balance.invoke({"employee_id": "E1001"})
        travel_res = get_travel_summary.invoke({"employee_id": "E1001"})
        dept_res = list_department_employees.invoke({"department": "Engineering"})

        # Must not raise TypeError: Object of type datetime / Decimal is not JSON serializable
        json.dumps(emp_res)
        json.dumps(leave_res)
        json.dumps(travel_res)
        json.dumps(dept_res)


if __name__ == "__main__":
    unittest.main()
