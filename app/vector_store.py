import os
import hashlib

import chromadb


try:
    chroma_path = os.getenv("CHROMA_PATH", "data/chroma")
    client = chromadb.PersistentClient(
        path=chroma_path
    )
    collection = client.get_or_create_collection(
        name="company_documents",
        metadata={"hnsw:space": "cosine"},
    )
except BaseException:
    try:
        client = chromadb.EphemeralClient()
        collection = client.get_or_create_collection(
            name="company_documents",
            metadata={"hnsw:space": "cosine"},
        )
    except BaseException:
        client = None
        collection = None


def reset_collection():
    global collection

    if client is None:
        return

    try:
        client.delete_collection("company_documents")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name="company_documents",
        metadata={"hnsw:space": "cosine"},
    )


def delete_document(document_id: str):
    """Deletes all chunks belonging to a specific document_id."""
    try:
        collection.delete(where={"document_id": document_id})
    except Exception:
        pass


def add_documents(
    chunks: list[str],
    embeddings: list[list[float]],
    metadata: dict | None = None,
):
    if metadata is None:
        metadata = {}

    doc_id = metadata.get("document_id")

    if doc_id:
        ids = [f"{doc_id}_chunk_{index}" for index in range(len(chunks))]
    else:
        ids = [f"chunk_{index}" for index in range(len(chunks))]

    metadatas = [
        {
            **metadata,
            "chunk_id": index,
            "chunk_uid": ids[index],
            # Per-chunk content hash so context selection can dedupe identical
            # chunk text without mistaking two different chunks of the same
            # document for exact duplicates (the document-level hash is
            # identical across all chunks of a document).
            "content_hash": hashlib.sha256(chunks[index].encode("utf-8")).hexdigest(),
        }
        for index in range(len(chunks))
    ]

    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )



def search(
    query_embedding: list[float],
    top_k: int = 3,
    where: dict | None = None,
):
    count = collection.count()
    if count == 0:
        return {
            "documents": [[]],
            "distances": [[]],
            "metadatas": [[]],
            "ids": [[]],
        }

    n_results = min(top_k, count)
    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
    }
    if where:
        query_kwargs["where"] = where

    return collection.query(**query_kwargs)