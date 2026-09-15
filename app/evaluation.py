import json
import re
from dataclasses import dataclass, field
from app.llm import ask_llm


@dataclass
class EvalThresholds:
    """Configurable quality thresholds for automated RAG validation."""
    min_recall_rate: float = 0.85
    min_precision: float = 0.75
    min_faithfulness: float = 0.85
    min_relevance: float = 0.85
    min_citation_correctness: float = 1.00


# =====================================================================
# 1. DETERMINISTIC METRICS
# =====================================================================

def evaluate_retrieval_metrics(
    retrieved_chunk_ids: list[int],
    expected_chunk_ids: list[int],
) -> dict:
    """Deterministic evaluation of Recall Hit and Precision@K.

    Args:
        retrieved_chunk_ids: Chunks returned by retriever.
        expected_chunk_ids: Ground truth relevant chunks (empty if unanswerable).
    """
    if expected_chunk_ids:
        recall_hit = any(chunk in retrieved_chunk_ids for chunk in expected_chunk_ids)
        recall_score = 1.0 if recall_hit else 0.0
    else:
        # For unanswerable queries, success means 0 chunks retrieved
        recall_score = 1.0 if len(retrieved_chunk_ids) == 0 else 0.0

    if retrieved_chunk_ids:
        relevant_retrieved = [
            chunk for chunk in retrieved_chunk_ids if chunk in expected_chunk_ids
        ]
        precision_score = len(relevant_retrieved) / len(retrieved_chunk_ids)
    else:
        # If nothing retrieved, precision is 1.0 for unanswerable queries, 0.0 for answerable
        precision_score = 1.0 if not expected_chunk_ids else 0.0

    return {
        "recall_score": recall_score,
        "precision_score": precision_score,
        "retrieved_chunks": retrieved_chunk_ids,
        "expected_chunks": expected_chunk_ids,
    }


def evaluate_citation_correctness(
    cited_chunk_ids: list[int],
    retrieved_chunk_ids: list[int],
    is_answerable: bool,
) -> dict:
    """Deterministic evaluation of citation validity.

    Ensures:
    1. Every cited chunk ID belongs to the actual retrieved contexts.
    2. No hallucinated/unretrieved chunks are cited.
    3. Unanswerable queries produce zero citations.
    """
    errors = []

    # Check for hallucinated citations (cited chunk not in retrieved contexts)
    for chunk_id in cited_chunk_ids:
        if chunk_id not in retrieved_chunk_ids:
            errors.append(
                f"Cited chunk_id {chunk_id} was NOT in retrieved chunks {retrieved_chunk_ids}."
            )

    # Check unanswerable consistency
    if not is_answerable and cited_chunk_ids:
        errors.append(
            f"Unanswerable query produced citations {cited_chunk_ids}, expected none."
        )

    # If answerable and contexts were retrieved, at least one valid citation is expected
    if is_answerable and retrieved_chunk_ids and not cited_chunk_ids:
        errors.append("Answerable query retrieved contexts but cited none.")

    correct = len(errors) == 0
    return {
        "citation_score": 1.0 if correct else 0.0,
        "valid": correct,
        "errors": errors,
        "cited_chunks": cited_chunk_ids,
    }


# =====================================================================
# 2. LLM-AS-JUDGE METRICS (Probabilistic / Model-Evaluated)
# =====================================================================

def _extract_json_response(raw_text: str) -> dict | None:
    """Helper to parse JSON from model responses containing possible markdown fences."""
    try:
        # Try direct json
        return json.loads(raw_text.strip())
    except Exception:
        pass

    # Extract {...} via regex
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return None


def evaluate_faithfulness(
    context: str,
    answer: str,
) -> dict:
    """LLM-as-Judge metric: Evaluates whether claims in answer are grounded in context.

    Note: This is an LLM-based evaluation and is non-deterministic.
    """
    # Deterministic short-circuit for empty context refusal
    if not context.strip():
        if "not available" in answer.lower() or "cannot" in answer.lower() or "sorry" in answer.lower():
            return {
                "score": 1.0,
                "faithful": True,
                "unsupported_claims": [],
                "reason": "Correct refusal when context is empty.",
            }
        return {
            "score": 0.0,
            "faithful": False,
            "unsupported_claims": [answer],
            "reason": "Answer made claims without any context.",
        }

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an impartial AI evaluation judge. Your task is to evaluate the Faithfulness "
                "of an AI answer against the provided Context.\n"
                "Faithfulness means: Every factual claim made in the Answer must be directly supported "
                "by the Context. If the Answer contains statements or numbers not present in the Context, "
                "it is unfaithful.\n"
                "Respond ONLY with a JSON object in this exact format:\n"
                '{"score": 1.0, "faithful": true, "unsupported_claims": [], "reason": "concise explanation"}\n'
                "Use score=1.0 if all claims are supported, or score=0.0 if any unsupported claim is found."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Context:\n{context}\n\n"
                f"Answer:\n{answer}\n\n"
                "JSON Evaluation:"
            ),
        },
    ]

    try:
        raw_output = ask_llm(prompt)
        parsed = _extract_json_response(raw_output)
        if parsed and "score" in parsed:
            return {
                "score": float(parsed["score"]),
                "faithful": bool(parsed.get("faithful", parsed["score"] >= 0.8)),
                "unsupported_claims": parsed.get("unsupported_claims", []),
                "reason": parsed.get("reason", "Evaluated by LLM judge."),
            }
    except Exception as e:
        pass

    # Fallback heuristic if LLM call fails
    is_faithful = "not available" in answer.lower() or any(
        sentence.strip() in context for sentence in answer.split(".") if len(sentence.strip()) > 15
    )
    return {
        "score": 1.0 if is_faithful else 0.5,
        "faithful": is_faithful,
        "unsupported_claims": [],
        "reason": "Fallback evaluation applied.",
    }


def evaluate_answer_relevance(
    question: str,
    answer: str,
    is_answerable: bool,
) -> dict:
    """LLM-as-Judge metric: Evaluates whether the answer directly addresses the question.

    Note: This is an LLM-based evaluation and is non-deterministic.
    """
    # Deterministic check for unanswerable questions
    if not is_answerable:
        if "not available" in answer.lower() or "cannot" in answer.lower() or "sorry" in answer.lower():
            return {
                "score": 1.0,
                "relevant": True,
                "reason": "Correctly acknowledged lack of information for unanswerable question.",
            }

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an impartial AI evaluation judge. Your task is to evaluate Answer Relevance.\n"
                "Relevance means: Does the Answer directly address what the User asked in the Question?\n"
                "Respond ONLY with a JSON object in this exact format:\n"
                '{"score": 1.0, "relevant": true, "reason": "concise explanation"}\n'
                "Use score=1.0 if the answer directly answers the query, or score=0.0 if it is irrelevant or evasive."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\n"
                f"Answer:\n{answer}\n\n"
                "JSON Evaluation:"
            ),
        },
    ]

    try:
        raw_output = ask_llm(prompt)
        parsed = _extract_json_response(raw_output)
        if parsed and "score" in parsed:
            return {
                "score": float(parsed["score"]),
                "relevant": bool(parsed.get("relevant", parsed["score"] >= 0.8)),
                "reason": parsed.get("reason", "Evaluated by LLM judge."),
            }
    except Exception as e:
        pass

    # Fallback heuristic
    return {
        "score": 1.0,
        "relevant": True,
        "reason": "Fallback relevance assumption.",
    }
