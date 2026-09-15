"""LangChain Tool wrapper for Enterprise Policy RAG.

Integrates the existing multi-stage hybrid retrieval (ChromaDB dense + BM25 sparse +
Cross-Encoder reranking) and strictly grounded LLM generation without duplicating
any retrieval, embedding, prompt engineering, or citation logic.
"""

from typing import Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.retriever import retrieve
from app.rag import generate_answer, STANDARD_REFUSAL
from app.context_config import DEFAULT_CONFIG


class PolicyQuestionInput(BaseModel):
    """Input schema for enterprise policy questions."""

    question: str = Field(
        ...,
        description=(
            "The specific enterprise policy, company guideline, compliance rule, "
            "travel expense limit, or leave policy question to look up."
        ),
    )


@tool(args_schema=PolicyQuestionInput)
def ask_policy(question: str) -> dict[str, Any]:
    """Answers enterprise policy and guideline questions using authoritative documentation.

    USE THIS TOOL WHEN:
    - The user asks about general company policies, standard rules, or guidelines.
    - Questions regarding travel policy allowances, expense limits, per diem rates, or receipt rules.
    - Questions regarding leave policies, accrual rules, standard holidays, or rollover limits.
    - Questions regarding IT security, equipment allowances, or remote work guidelines.

    DO NOT USE THIS TOOL FOR:
    - Querying an individual employee's personal data, specific leave balance, or submitted expense claims.
      (Use database tools like `get_employee`, `get_leave_balance`, or `get_travel_summary` instead).

    RETURNS:
    A structured dictionary containing:
    - `question`: The input question.
    - `answer`: The strictly grounded policy answer or standard refusal message.
    - `is_refusal`: Boolean indicating if the policy context was insufficient to answer.
    - `sources`: List of cited document snippets with ranks, titles, file paths, and reranker scores.
    """
    if not question or not str(question).strip():
        return {
            "question": question,
            "answer": STANDARD_REFUSAL,
            "is_refusal": True,
            "sources": [],
        }

    try:
        # 1. Execute hybrid retrieval pipeline
        results, _ = retrieve(
            query=str(question).strip(),
            config=DEFAULT_CONFIG,
            return_stats=True,
        )

        contexts = [doc for doc, score, meta in results]

        # 2. Generate grounded answer
        answer = generate_answer(str(question).strip(), contexts)

        # 3. Assess refusal state
        is_refusal = (
            not results
            or "not available in the provided documents" in answer.lower()
        )

        # 4. Extract structured citations
        sources = []
        if not is_refusal:
            for idx, (doc, score, meta) in enumerate(results, start=1):
                sources.append(
                    {
                        "rank": idx,
                        "title": meta.get("title", "Document"),
                        "source_file": meta.get("source", "Unknown file"),
                        "chunk_uid": meta.get("chunk_uid", f"chunk_{idx}"),
                        "rerank_score": round(float(meta.get("rerank_score", score)), 3),
                        "snippet": doc.strip(),
                    }
                )

        return {
            "question": str(question).strip(),
            "answer": answer,
            "is_refusal": is_refusal,
            "sources": sources,
        }

    except Exception:
        # Prevent stack trace or internal path leakage to agent
        return {
            "question": str(question).strip(),
            "answer": STANDARD_REFUSAL,
            "is_refusal": True,
            "sources": [],
            "error": "Failed to process policy question safely.",
        }
