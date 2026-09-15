def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float, dict]]],
    k: int = 60,
) -> list[tuple[str, float, dict]]:
    """Combines multiple ranked candidate lists using Reciprocal Rank Fusion (RRF).

    Formula for each document d across retrieval systems m:
        RRF_score(d) = SUM_m [ 1 / (k + rank_m(d)) ]

    Args:
        ranked_lists: List of candidate rankings, e.g. [dense_results, sparse_results].
        k: Smoothing constant preventing high ranks from dominating (default: 60).

    Returns:
        List of fused (document, rrf_score, metadata) ordered by rrf_score descending.
    """
    if not ranked_lists:
        return []

    fused_scores: dict[str, float] = {}
    fused_docs: dict[str, str] = {}
    fused_metadata: dict[str, dict] = {}
    source_ranks: dict[str, dict[str, int]] = {}

    list_names = ["dense", "sparse"] if len(ranked_lists) == 2 else [
        f"ranker_{i}" for i in range(len(ranked_lists))
    ]

    for list_idx, candidates in enumerate(ranked_lists):
        source_name = list_names[list_idx] if list_idx < len(list_names) else f"ranker_{list_idx}"

        for rank_1_based, (doc, score, meta) in enumerate(candidates, start=1):
            # Form unique document/chunk key
            key = meta.get("chunk_uid")
            if not key:
                doc_id = meta.get("document_id", "doc")
                chunk_id = meta.get("chunk_id", 0)
                key = f"{doc_id}_chunk_{chunk_id}"

            rrf_contribution = 1.0 / (k + rank_1_based)

            fused_scores[key] = fused_scores.get(key, 0.0) + rrf_contribution
            fused_docs[key] = doc

            if key not in fused_metadata:
                fused_metadata[key] = meta.copy()
            if key not in source_ranks:
                source_ranks[key] = {}

            source_ranks[key][f"{source_name}_rank"] = rank_1_based

    # Build fused output list
    fused_results = []
    for key, score in fused_scores.items():
        meta = fused_metadata[key].copy()
        meta["rrf_score"] = score
        meta.update(source_ranks[key])
        fused_results.append((fused_docs[key], score, meta))

    # Sort descending by RRF score
    fused_results.sort(key=lambda item: item[1], reverse=True)
    return fused_results
