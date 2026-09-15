from sentence_transformers import CrossEncoder

# Load cross-encoder reranker model
# cross-encoder/ms-marco-MiniLM-L-6-v2 takes (query, document) pairs
# and outputs a logit representing passage relevance.
model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def score_pairs(query: str, documents: list[str]) -> list[float]:
    """Score query-document pairs using the cross-encoder model.

    Returns a list of raw relevance scores (logits).
    """
    if not documents:
        return []

    pairs = [(query, doc) for doc in documents]
    scores = model.predict(pairs)
    return [float(score) for score in scores]


def rerank_candidates(
    query: str,
    candidates: list[tuple[str, float, dict]],
    top_k: int = 3,
    score_threshold: float | None = None,
) -> list[tuple[str, float, dict]]:
    """Rerank first-stage candidate documents using cross-encoder.

    Args:
        query: The user search query.
        candidates: List of (document, vector_distance, metadata) from first stage.
        top_k: Maximum number of reranked documents to return.
        score_threshold: Minimum cross-encoder score to keep. If None, no filtering by score.

    Returns:
        List of (document, rerank_score, metadata) sorted by rerank_score descending.
    """
    if not candidates:
        return []

    documents = [doc for doc, _, _ in candidates]
    scores = score_pairs(query, documents)

    # Attach score to candidate
    scored_candidates = [
        (
            doc,
            score,
            {
                **metadata,
                "vector_distance": orig_distance,
                "rerank_score": score,
            },
        )
        for (doc, orig_distance, metadata), score in zip(candidates, scores)
    ]

    # Sort descending by reranker score
    scored_candidates.sort(key=lambda item: item[1], reverse=True)

    # Apply score threshold if configured
    if score_threshold is not None:
        scored_candidates = [
            item for item in scored_candidates if item[1] >= score_threshold
        ]

    return scored_candidates[:top_k]
