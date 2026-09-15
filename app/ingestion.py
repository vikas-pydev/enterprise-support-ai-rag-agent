import json
from datetime import datetime, timezone
from pathlib import Path

from app.document_loader import Document, load_document, load_directory
from app.chunker import chunk_text
from app.embeddings import create_embedding
from app.vector_store import (
    reset_collection,
    add_documents,
    delete_document,
)

REGISTRY_PATH = Path("data/document_registry.json")


class IngestResult(int):
    """Integer subclass returning chunk count while providing detailed ingestion metadata."""
    status: str
    document_id: str
    version: str
    chunks_stored: int

    def __new__(cls, chunk_count: int, **kwargs):
        obj = super().__new__(cls, chunk_count)
        for key, value in kwargs.items():
            setattr(obj, key, value)
        return obj

    def to_dict(self) -> dict:
        return {
            "status": getattr(self, "status", "unknown"),
            "document_id": getattr(self, "document_id", ""),
            "version": getattr(self, "version", ""),
            "chunks_stored": int(self),
        }


def _load_registry() -> dict:
    if REGISTRY_PATH.is_file():
        try:
            return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_registry(registry: dict):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        json.dumps(registry, indent=2),
        encoding="utf-8",
    )


def get_document_registry() -> dict:
    """Returns current document version registry."""
    return _load_registry()


def ingest_document(
    document_input: str | Path | Document,
    reset: bool = False,
    force: bool = False,
) -> IngestResult:
    """Ingests a single document into the vector database with version tracking.

    Args:
        document_input: File path or already-loaded Document object.
        reset: If True, resets the entire vector collection before ingestion.
        force: If True, forces re-embedding even if the content hash has not changed.

    Returns:
        IngestResult: Integer chunk count with status and version metadata.
    """
    registry = _load_registry()

    if reset:
        reset_collection()
        registry = {}
        _save_registry(registry)

    if isinstance(document_input, Document):
        doc = document_input
    else:
        doc = load_document(document_input)

    doc_id = doc.document_id
    existing_entry = registry.get(doc_id)

    # Change Detection via Content Hashing
    if not force and existing_entry:
        if existing_entry.get("content_hash") == doc.content_hash:
            return IngestResult(
                existing_entry.get("chunk_count", 0),
                status="skipped",
                document_id=doc_id,
                version=doc.version,
                chunks_stored=existing_entry.get("chunk_count", 0),
            )

    # If updating an existing document, prune old chunks from vector store
    if existing_entry:
        delete_document(doc_id)

    chunks = chunk_text(doc)
    embeddings = [create_embedding(chunk) for chunk in chunks]

    add_documents(
        chunks=chunks,
        embeddings=embeddings,
        metadata=doc.metadata,
    )

    # Update Registry
    registry[doc_id] = {
        "filename": doc.filename,
        "title": doc.title,
        "source": doc.source,
        "content_hash": doc.content_hash,
        "version": doc.version,
        "chunk_count": len(chunks),
        "last_ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_registry(registry)

    return IngestResult(
        len(chunks),
        status="ingested",
        document_id=doc_id,
        version=doc.version,
        chunks_stored=len(chunks),
    )


def ingest_directory(
    directory_path: str | Path = "data/documents",
    reset: bool = False,
    force: bool = False,
) -> dict:
    """Ingests all supported documents from a directory incrementally.

    Args:
        directory_path: Path to directory containing documents.
        reset: If True, clears the vector collection and registry first.
        force: If True, re-embeds all documents regardless of content hash.

    Returns:
        Dict summarizing total documents, ingested, skipped, and total chunks.
    """
    if reset:
        reset_collection()
        _save_registry({})

    documents = load_directory(directory_path)

    ingested_count = 0
    skipped_count = 0
    total_chunks = 0
    details = []

    for doc in documents:
        res = ingest_document(doc, reset=False, force=force)
        details.append(res.to_dict())
        total_chunks += int(res)

        if res.status == "ingested":
            ingested_count += 1
        else:
            skipped_count += 1

    return {
        "total_documents": len(documents),
        "ingested_count": ingested_count,
        "skipped_count": skipped_count,
        "total_chunks": total_chunks,
        "documents": details,
    }