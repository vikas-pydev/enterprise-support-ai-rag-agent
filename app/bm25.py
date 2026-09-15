import math
import re
from collections import Counter
from app.vector_store import collection


def tokenize(text: str) -> list[str]:
    """Tokenizes text preserving alphanumeric codes, abbreviations, and hyphenated terms."""
    if not text:
        return []
    # Matches words, numbers, and hyphenated policy codes like 'POL-101', '401k'
    return [
        token.lower()
        for token in re.findall(r"[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*", text)
        if len(token) > 0
    ]


class BM25Index:
    """Lightweight, in-memory BM25Okapi sparse search index."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: list[tuple[str, dict]] = []
        self.doc_len: list[int] = []
        self.avg_doc_len: float = 0.0
        self.doc_freqs: dict[str, int] = Counter()
        self.idf: dict[str, float] = {}
        self.tokenized_corpus: list[list[str]] = []

    def build_from_chunks(self, chunks: list[str], metadatas: list[dict]):
        """Builds index from raw text chunks and their metadata dictionaries."""
        self.corpus = list(zip(chunks, metadatas))
        self.tokenized_corpus = [tokenize(doc) for doc in chunks]
        self.doc_len = [len(tokens) for tokens in self.tokenized_corpus]
        total_tokens = sum(self.doc_len)
        self.avg_doc_len = (
            total_tokens / len(self.doc_len) if self.doc_len else 0.0
        )

        # Compute document frequencies
        self.doc_freqs = Counter()
        for tokens in self.tokenized_corpus:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] += 1

        # Compute Robertson-Spärck Jones IDF with additive smoothing
        num_docs = len(self.corpus)
        self.idf = {}
        for token, df in self.doc_freqs.items():
            self.idf[token] = math.log(
                ((num_docs - df + 0.5) / (df + 0.5)) + 1.0
            )

    def build_from_vector_store(self):
        """Pulls all stored chunks and metadata directly from ChromaDB."""
        data = collection.get(include=["documents", "metadatas"])
        docs = data.get("documents") or []
        metas = data.get("metadatas") or []
        self.build_from_chunks(docs, metas)

    def search(
        self,
        query: str,
        top_k: int = 10,
        where: dict | None = None,
    ) -> list[tuple[str, float, dict]]:
        """Scores documents against query using BM25Okapi formula."""
        query_tokens = tokenize(query)
        if not query_tokens or not self.corpus:
            return []

        scores = []
        for idx, (doc, meta) in enumerate(self.corpus):
            # Apply metadata pre-filtering if specified
            if where:
                match = True
                for k, v in where.items():
                    if meta.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            # Calculate BM25 score
            doc_tokens = self.tokenized_corpus[idx]
            doc_len = self.doc_len[idx]
            token_counts = Counter(doc_tokens)

            score = 0.0
            for q_term in query_tokens:
                if q_term not in token_counts:
                    continue
                tf = token_counts[q_term]
                idf = self.idf.get(q_term, 0.0)
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (
                    1.0 - self.b + self.b * (doc_len / (self.avg_doc_len or 1.0))
                )
                score += idf * (numerator / denominator)

            if score > 0.0:
                scores.append((doc, score, meta))

        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:top_k]


# Global singleton instance
_bm25_instance: BM25Index | None = None


def get_bm25_index(force_refresh: bool = False) -> BM25Index:
    """Returns singleton BM25 index, building from ChromaDB if not initialized."""
    global _bm25_instance
    if _bm25_instance is None or force_refresh:
        _bm25_instance = BM25Index()
        _bm25_instance.build_from_vector_store()
    return _bm25_instance
