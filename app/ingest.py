import sys
from app.ingestion import ingest_directory, ingest_document


def main():
    args = sys.argv[1:]

    reset = "--reset" in args
    force = "--force" in args
    target = next((a for a in args if not a.startswith("--")), None)

    if target:
        print(f"Ingesting target file: {target}")
        res = ingest_document(target, reset=reset, force=force)
        print(
            f"Ingestion completed. "
            f"Document ID: {res.document_id}, "
            f"Status: {res.status}, "
            f"Chunks: {int(res)}, "
            f"Version: {res.version}"
        )
    else:
        print("Ingesting all documents from 'data/documents'...")
        summary = ingest_directory("data/documents", reset=reset, force=force)
        print("Ingestion Summary:")
        print(f"  Total Documents: {summary['total_documents']}")
        print(f"  Newly Ingested:  {summary['ingested_count']}")
        print(f"  Skipped (Cached):{summary['skipped_count']}")
        print(f"  Total Chunks:    {summary['total_chunks']}")
        for doc in summary["documents"]:
            print(
                f"    - {doc['document_id']} ({doc['version']}): "
                f"{doc['status']} ({doc['chunks_stored']} chunks)"
            )
        if reset:
            print(
                "\n[note] Collection was reset. Use --force next time "
                "to re-embed unchanged documents."
            )


if __name__ == "__main__":
    main()