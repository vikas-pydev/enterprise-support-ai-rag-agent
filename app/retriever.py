from typing import Any
from app.embeddings import create_embedding
from app.vector_store import search
from app.reranker import rerank_candidates
from app.bm25 import get_bm25_index
from app.fusion import reciprocal_rank_fusion
from app.context_config import RetrievalContextConfig, DEFAULT_CONFIG
from app.context_selector import select_and_compress_context, ContextSelectionStats


def retrieve_from_vector_store(
    query: str,
    top_k: int = 3,
    max_distance: float = 0.7,
    where: dict | None = None,
) -> list[tuple[str, float, dict]]:
    """Stage 1: Bi-encoder dense vector retrieval from ChromaDB."""
    if not query or not query.strip():
        return []

    query_embedding = create_embedding(query.strip())

    results = search(
        query_embedding,
        top_k=top_k,
        where=where,
    )

    if not results or not results.get("documents") or not results["documents"][0]:
        return []

    documents = results["documents"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    paired = list(zip(documents, distances, metadatas))
    return [item for item in paired if item[1] <= max_distance]


def retrieve_from_bm25(
    query: str,
    top_k: int = 3,
    where: dict | None = None,
) -> list[tuple[str, float, dict]]:
    """Stage 1 (Sparse): BM25Okapi keyword retrieval."""
    if not query or not query.strip():
        return []

    bm25_index = get_bm25_index()
    return bm25_index.search(query=query, top_k=top_k, where=where)


def retrieve_hybrid_candidates(
    query: str,
    initial_top_k: int = 10,
    dense_k: int | None = None,
    sparse_k: int | None = None,
    max_distance: float = 0.7,
    rrf_k: int = 60,
    where: dict | None = None,
) -> list[tuple[str, float, dict]]:
    """Retrieves candidates from both Dense and Sparse systems and fuses via RRF."""
    dk = dense_k if dense_k is not None else initial_top_k
    sk = sparse_k if sparse_k is not None else initial_top_k

    dense_candidates = retrieve_from_vector_store(
        query=query,
        top_k=dk,
        max_distance=max_distance,
        where=where,
    )
    sparse_candidates = retrieve_from_bm25(
        query=query,
        top_k=sk,
        where=where,
    )

    return reciprocal_rank_fusion(
        ranked_lists=[dense_candidates, sparse_candidates],
        k=rrf_k,
    )


def retrieve_with_rerank(
    query: str,
    initial_top_k: int = 10,
    final_top_k: int = 3,
    max_distance: float = 0.7,
    score_threshold: float | None = 5.0,
    where: dict | None = None,
    mode: str = "hybrid",
    config: RetrievalContextConfig | None = None,
    return_stats: bool = False,
) -> list[tuple[str, float, dict]] | tuple[list[tuple[str, float, dict]], ContextSelectionStats]:
    """Multi-stage retrieval: candidate generation (dense, sparse, or hybrid),
    Cross-Encoder reranking, threshold filtering, and deterministic context selection/compression.
    """
    if not query or not query.strip():
        empty_stats = ContextSelectionStats()
        return ([], empty_stats) if return_stats else []

    # Resolve parameters from config or explicit arguments
    if config is not None:
        c_dense_k = config.dense_k
        c_sparse_k = config.sparse_k
        c_rrf_k = config.rrf_k
        c_rerank_cand = config.reranker_candidates_k
        c_final_k = config.final_context_k
        c_threshold = config.reranker_score_threshold
        c_max_dist = config.max_distance
        c_mode = config.mode
        c_max_chars = config.max_context_chars
        c_redundancy = config.redundancy_similarity_threshold
    else:
        c_dense_k = initial_top_k
        c_sparse_k = initial_top_k
        c_rrf_k = 60
        c_rerank_cand = initial_top_k
        c_final_k = final_top_k
        c_threshold = score_threshold
        c_max_dist = max_distance
        c_mode = mode
        c_max_chars = 1500
        c_redundancy = 0.70

    # 1. Candidate Retrieval
    if c_mode == "sparse":
        candidates = retrieve_from_bm25(
            query=query,
            top_k=c_sparse_k,
            where=where,
        )
    elif c_mode == "dense":
        candidates = retrieve_from_vector_store(
            query=query,
            top_k=c_dense_k,
            max_distance=c_max_dist,
            where=where,
        )
    else:  # hybrid
        candidates = retrieve_hybrid_candidates(
            query=query,
            initial_top_k=c_dense_k,
            dense_k=c_dense_k,
            sparse_k=c_sparse_k,
            max_distance=c_max_dist,
            rrf_k=c_rrf_k,
            where=where,
        )

    # 2. Cross-Encoder Reranking & Score Filtering
    reranked = rerank_candidates(
        query=query,
        candidates=candidates,
        top_k=c_rerank_cand,
        score_threshold=c_threshold,
    )

    # 3. Deterministic Context Selection, Deduplication & Budget Enforcement
    selected, stats = select_and_compress_context(
        candidates=reranked,
        max_chunks=c_final_k,
        max_chars=c_max_chars,
        redundancy_threshold=c_redundancy,
    )

    return (selected, stats) if return_stats else selected


def retrieve(
    query: str,
    top_k: int = 3,
    mode: str = "hybrid",
    use_reranker: bool = True,
    score_threshold: float | None = 5.0,
    max_distance: float = 0.7,
    where: dict | None = None,
    config: RetrievalContextConfig | None = None,
    return_stats: bool = False,
) -> list[tuple[str, float, dict]] | tuple[list[tuple[str, float, dict]], ContextSelectionStats]:
    """Unified retrieval interface supporting dense, sparse, and hybrid modes,
    optional reranking, and deterministic context selection/compression.
    """
    if not query or not query.strip():
        empty_stats = ContextSelectionStats()
        return ([], empty_stats) if return_stats else []

    if config is not None:
        if config.use_reranker:
            return retrieve_with_rerank(
                query=query,
                where=where,
                config=config,
                return_stats=return_stats,
            )

        # Config-driven retrieval without reranking: generate candidates
        # (dense / sparse / hybrid) then apply deterministic context selection.
        if config.mode == "sparse":
            raw_candidates = retrieve_from_bm25(
                query=query,
                top_k=config.sparse_k,
                where=where,
            )
        elif config.mode == "dense":
            raw_candidates = retrieve_from_vector_store(
                query=query,
                top_k=config.dense_k,
                max_distance=config.max_distance,
                where=where,
            )
        else:  # hybrid
            raw_candidates = retrieve_hybrid_candidates(
                query=query,
                initial_top_k=config.dense_k,
                dense_k=config.dense_k,
                sparse_k=config.sparse_k,
                max_distance=config.max_distance,
                rrf_k=config.rrf_k,
                where=where,
            )

        selected, stats = select_and_compress_context(
            candidates=raw_candidates,
            max_chunks=config.final_context_k,
            max_chars=config.max_context_chars,
            redundancy_threshold=config.redundancy_similarity_threshold,
        )
        return (selected, stats) if return_stats else selected

    initial_candidates_count = max(10, top_k * 3)

    if use_reranker:
        return retrieve_with_rerank(
            query=query,
            initial_top_k=initial_candidates_count,
            final_top_k=top_k,
            max_distance=max_distance,
            score_threshold=score_threshold,
            where=where,
            mode=mode,
            return_stats=return_stats,
        )

    # Un-reranked path: still apply deduplication & budget enforcement
    if mode == "sparse":
        raw_candidates = retrieve_from_bm25(
            query=query,
            top_k=top_k * 2,
            where=where,
        )
    elif mode == "dense":
        raw_candidates = retrieve_from_vector_store(
            query=query,
            top_k=top_k * 2,
            max_distance=max_distance,
            where=where,
        )
    else:  # hybrid without reranker
        raw_candidates = retrieve_hybrid_candidates(
            query=query,
            initial_top_k=top_k * 2,
            max_distance=max_distance,
            where=where,
        )

    selected, stats = select_and_compress_context(
        candidates=raw_candidates,
        max_chunks=top_k,
        max_chars=1500,
        redundancy_threshold=0.70,
    )

    return (selected, stats) if return_stats else selected