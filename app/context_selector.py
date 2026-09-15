import hashlib
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextSelectionStats:
    """Statistics on context selection, deduplication, and budget enforcement."""
    initial_chunks: int = 0
    final_chunks: int = 0
    exact_duplicates_removed: int = 0
    redundant_chunks_removed: int = 0
    budget_exceeded_chunks_removed: int = 0
    initial_chars: int = 0
    final_chars: int = 0

    @property
    def char_reduction_pct(self) -> float:
        if self.initial_chars == 0:
            return 0.0
        return ((self.initial_chars - self.final_chars) / self.initial_chars) * 100.0


def _tokenize_for_similarity(text: str) -> set[str]:
    """Extract lowercased word tokens for Jaccard similarity calculation."""
    return set(re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower()))


def calculate_jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Computes Jaccard similarity coefficient between two token sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return float(intersection) / float(union) if union > 0 else 0.0


def select_and_compress_context(
    candidates: list[tuple[str, float, dict[str, Any]]],
    max_chunks: int = 3,
    max_chars: int = 1500,
    redundancy_threshold: float = 0.70,
) -> tuple[list[tuple[str, float, dict[str, Any]]], ContextSelectionStats]:
    """Deterministic context selection, deduplication, redundancy elimination, and budget enforcement.

    Args:
        candidates: List of (document_text, score, metadata) sorted by relevance descending.
        max_chunks: Maximum number of final chunks to return.
        max_chars: Maximum cumulative character budget for context.
        redundancy_threshold: Maximum allowed Jaccard token overlap with an already accepted chunk.

    Returns:
        tuple of (selected_candidates, selection_stats)
    """
    stats = ContextSelectionStats()
    stats.initial_chunks = len(candidates)
    stats.initial_chars = sum(len(doc) for doc, _, _ in candidates)

    if not candidates:
        return [], stats

    selected: list[tuple[str, float, dict[str, Any]]] = []
    seen_chunk_uids: set[str] = set()
    seen_content_hashes: set[str] = set()
    accepted_token_sets: list[set[str]] = []
    current_chars = 0

    for doc, score, meta in candidates:
        if len(selected) >= max_chunks:
            break

        doc_clean = doc.strip()
        chunk_uid = meta.get("chunk_uid") or meta.get("id") or f"{meta.get('document_id', 'doc')}_{meta.get('chunk_id', '0')}"
        # Prefer the stored per-chunk content hash; fall back to a deterministic
        # SHA-256 of the chunk text (never Python's process-randomized hash()).
        content_sig = meta.get("content_hash") or hashlib.sha256(doc_clean.encode("utf-8")).hexdigest()

        # 1. Exact Duplicate Elimination
        if chunk_uid in seen_chunk_uids or content_sig in seen_content_hashes:
            stats.exact_duplicates_removed += 1
            continue

        doc_tokens = _tokenize_for_similarity(doc_clean)

        # 2. Redundancy / Near-Duplicate Elimination
        is_redundant = False
        for prior_tokens in accepted_token_sets:
            similarity = calculate_jaccard_similarity(doc_tokens, prior_tokens)
            if similarity >= redundancy_threshold:
                is_redundant = True
                break

        if is_redundant:
            stats.redundant_chunks_removed += 1
            continue

        # 3. Context Budget Enforcement
        doc_len = len(doc_clean)
        if selected and (current_chars + doc_len > max_chars):
            # Budget exceeded and we already have at least one top relevant chunk
            stats.budget_exceeded_chunks_removed += 1
            continue

        # Accept chunk
        selected.append((doc, score, meta))
        seen_chunk_uids.add(chunk_uid)
        seen_content_hashes.add(content_sig)
        accepted_token_sets.append(doc_tokens)
        current_chars += doc_len

    stats.final_chunks = len(selected)
    stats.final_chars = current_chars
    return selected, stats
