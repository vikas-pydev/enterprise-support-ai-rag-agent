from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalContextConfig:
    """Configuration for retrieval, hybrid fusion, reranking, and context selection."""

    # Stage 1: Candidate Generation
    dense_k: int = 10
    sparse_k: int = 10

    # Stage 2: Hybrid Fusion (RRF)
    rrf_k: int = 60
    reranker_candidates_k: int = 10

    # Stage 3 & 4: Reranking & Threshold
    reranker_score_threshold: float | None = 5.0
    max_distance: float = 0.7

    # Stage 5 & 6: Context Selection, Deduplication & Budget Enforcement
    final_context_k: int = 3
    max_context_chars: int = 1500
    redundancy_similarity_threshold: float = 0.70

    # Operational Mode
    mode: str = "hybrid"  # "hybrid" | "dense" | "sparse"
    use_reranker: bool = True


# Predefined configurations for benchmarking & deployment
SMALL_CONFIG = RetrievalContextConfig(
    dense_k=3,
    sparse_k=3,
    reranker_candidates_k=5,
    final_context_k=2,
    max_context_chars=800,
    redundancy_similarity_threshold=0.65,
)

MEDIUM_CONFIG = RetrievalContextConfig(
    dense_k=10,
    sparse_k=10,
    reranker_candidates_k=10,
    final_context_k=3,
    max_context_chars=1500,
    redundancy_similarity_threshold=0.70,
)

LARGE_CONFIG = RetrievalContextConfig(
    dense_k=20,
    sparse_k=20,
    reranker_candidates_k=20,
    final_context_k=5,
    max_context_chars=3000,
    redundancy_similarity_threshold=0.75,
)

# Showcase V1 Default Configuration
DEFAULT_CONFIG = MEDIUM_CONFIG
