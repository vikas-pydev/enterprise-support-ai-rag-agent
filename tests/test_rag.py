"""Deterministic unit tests for RAG pipeline generation, prompt assembly, and refusal guardrails."""

import unittest
from unittest.mock import patch, MagicMock

from app.retriever import retrieve
from app.rag import generate_answer, STANDARD_REFUSAL, SYSTEM_PROMPT


class TestRAGPipeline(unittest.TestCase):
    """Automated unit test suite validating RAG answer synthesis, prompt formatting, and refusal logic."""

    def test_01_empty_context_returns_standard_refusal_without_llm_call(self):
        """Verify generate_answer returns standard refusal immediately when context list is empty."""
        with patch("app.rag.ask_llm") as mock_llm:
            answer = generate_answer("What is the company stock purchase plan?", contexts=[])
            self.assertEqual(answer, STANDARD_REFUSAL)
            mock_llm.assert_not_called()

    def test_02_prompt_structure_and_context_chunk_formatting(self):
        """Verify generate_answer formats context chunks with XML tags and includes SYSTEM_PROMPT."""
        question = "How many annual leave days do employees receive?"
        contexts = [
            "Employees receive 24 days of annual leave per calendar year.",
            "Leave must be approved by the reporting manager.",
        ]

        with patch("app.rag.ask_llm", return_value="Employees receive 24 days of annual leave.") as mock_llm:
            answer = generate_answer(question, contexts)

            self.assertEqual(answer, "Employees receive 24 days of annual leave.")
            mock_llm.assert_called_once()

            # Inspect payload sent to ask_llm
            call_args = mock_llm.call_args[0][0]
            self.assertIsInstance(call_args, list)
            self.assertEqual(len(call_args), 2)

            # System prompt verification
            self.assertEqual(call_args[0]["role"], "system")
            self.assertEqual(call_args[0]["content"], SYSTEM_PROMPT)

            # User prompt context wrapping verification
            self.assertEqual(call_args[1]["role"], "user")
            user_content = call_args[1]["content"]
            self.assertIn("<retrieved_context>", user_content)
            self.assertIn('</retrieved_context>', user_content)
            self.assertIn('<context_chunk id="1">', user_content)
            self.assertIn('<context_chunk id="2">', user_content)
            self.assertIn("Question: How many annual leave days do employees receive?", user_content)

    def test_03_rag_pipeline_end_to_end_with_mocked_llm(self):
        """Verify full RAG pipeline (retrieve -> format -> generate_answer -> citations) without live LLM."""
        question = "How many annual leave days do employees receive?"
        results = retrieve(question, top_k=3, score_threshold=0.0)
        self.assertGreaterEqual(len(results), 1)

        contexts = [doc for doc, score, metadata in results]

        mocked_answer = "Employees receive 24 annual leave days per calendar year according to enterprise policy."
        with patch("app.rag.ask_llm", return_value=mocked_answer):
            answer = generate_answer(question, contexts)
            self.assertEqual(answer, mocked_answer)

        # Verify sources format
        sources = [
            f"[{i}] {meta.get('title', 'Document')} (chunk {meta.get('chunk_id', 0)})"
            for i, (doc, score, meta) in enumerate(results, start=1)
        ]
        self.assertGreaterEqual(len(sources), 1)
        self.assertTrue(any("leave" in s.lower() for s in sources))

    def test_04_refusal_when_retrieval_finds_no_matching_context(self):
        """Verify that when retrieve finds no contexts above threshold, standard refusal is generated."""
        unanswerable_query = "What is the corporate quantum encryption algorithm?"
        results = retrieve(unanswerable_query, top_k=3, score_threshold=999.0)

        contexts = [doc for doc, score, metadata in results]
        with patch("app.rag.ask_llm") as mock_llm:
            answer = generate_answer(unanswerable_query, contexts)
            self.assertEqual(answer, STANDARD_REFUSAL)
            mock_llm.assert_not_called()


if __name__ == "__main__":
    unittest.main()