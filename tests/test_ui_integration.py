import unittest
import ast
from pathlib import Path
from app.retriever import retrieve
from app.rag import generate_answer
from app.context_config import DEFAULT_CONFIG


class TestUIIntegration(unittest.TestCase):
    """Integration tests verifying the RAG pipeline backend powering the Showcase UI."""

    def test_ui_script_syntax_and_imports(self):
        """Verify app/ui.py has valid Python AST and clean syntax."""
        ui_path = Path("app/ui.py")
        self.assertTrue(ui_path.exists(), "app/ui.py does not exist")
        content = ui_path.read_text(encoding="utf-8")
        parsed = ast.parse(content)
        self.assertIsNotNone(parsed, "app/ui.py failed to parse AST")

    def test_answerable_query_travel_policy(self):
        """Scenario 1: Ask travel policy question, verify answer and citations."""
        query = "What is the meal per diem allowance for domestic travel?"
        results, stats = retrieve(query, config=DEFAULT_CONFIG, return_stats=True)

        self.assertGreater(len(results), 0, "Expected at least 1 retrieved result")
        contexts = [doc for doc, score, meta in results]
        answer = generate_answer(query, contexts)

        self.assertIn("75", answer, "Expected domestic per diem $75 in answer")
        self.assertNotIn("not available in the provided documents", answer.lower())

        # Verify source citations
        source_files = [meta["source"] for doc, score, meta in results]
        self.assertTrue(
            any("travel_policy.md" in src for src in source_files),
            "Expected travel_policy.md in retrieved sources",
        )
        self.assertGreater(stats.initial_chunks, 0)
        self.assertGreater(stats.final_chunks, 0)

    def test_answerable_query_attendance_policy(self):
        """Scenario 2: Ask attendance policy question, verify answer and citations."""
        query = "What are the core collaboration hours for remote employees?"
        results, stats = retrieve(query, config=DEFAULT_CONFIG, return_stats=True)

        self.assertGreater(len(results), 0, "Expected at least 1 retrieved result")
        contexts = [doc for doc, score, meta in results]
        answer = generate_answer(query, contexts)

        self.assertTrue(
            "10" in answer or "core" in answer.lower(),
            "Expected core hours information in answer",
        )
        source_files = [meta["source"] for doc, score, meta in results]
        self.assertTrue(
            any("attendance_policy.txt" in src for src in source_files),
            "Expected attendance_policy.txt in retrieved sources",
        )

    def test_unanswerable_query_refusal(self):
        """Scenario 3: Ask out-of-domain question, verify strict refusal."""
        query = "What is the company pet insurance reimbursement policy?"
        results, stats = retrieve(query, config=DEFAULT_CONFIG, return_stats=True)

        self.assertEqual(len(results), 0, "Expected 0 results for unanswerable query")
        contexts = [doc for doc, score, meta in results]
        answer = generate_answer(query, contexts)

        self.assertIn(
            "not available in the provided documents",
            answer.lower(),
            "Expected standard refusal message",
        )

    def test_empty_query_handling(self):
        """Scenario 4: Empty input handled gracefully."""
        query = "   "
        results, stats = retrieve(query, config=DEFAULT_CONFIG, return_stats=True)
        self.assertEqual(len(results), 0)
        contexts = [doc for doc, score, meta in results]
        answer = generate_answer(query, contexts)
        self.assertIn("not available in the provided documents", answer.lower())


if __name__ == "__main__":
    unittest.main()
