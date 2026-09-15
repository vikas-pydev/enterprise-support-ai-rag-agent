import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path


class Document(str):
    """Rich document string container holding document identity and version metadata.

    Inherits from str for seamless backward compatibility with existing chunking,
    embedding, and string operations.
    """

    document_id: str
    filename: str
    title: str
    source: str
    file_extension: str
    content_hash: str
    version: str
    created_at: str

    def __new__(
        cls,
        content: str,
        document_id: str,
        filename: str,
        title: str,
        source: str,
        file_extension: str,
        content_hash: str,
        version: str,
        created_at: str | None = None,
    ):
        obj = super().__new__(cls, content)
        obj.document_id = document_id
        obj.filename = filename
        obj.title = title
        obj.source = source
        obj.file_extension = file_extension
        obj.content_hash = content_hash
        obj.version = version
        obj.created_at = (
            created_at
            or datetime.now(timezone.utc).isoformat()
        )
        return obj

    @property
    def metadata(self) -> dict:
        """Returns document-level metadata dictionary."""
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "title": self.title,
            "source": self.source,
            "file_extension": self.file_extension,
            "content_hash": self.content_hash,
            "version": self.version,
            "created_at": self.created_at,
        }


def _extract_title(content: str, filename: str) -> str:
    """Extract human-readable title from document content or fallback to filename."""
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return Path(filename).stem.replace("_", " ").title()

    first_line = lines[0]
    # Check for markdown header (e.g. '# Title')
    if first_line.startswith("#"):
        return re.sub(r"^#+\s*", "", first_line).strip()

    # If first line is a short heading without punctuation, use it
    if len(first_line) <= 80 and not first_line.endswith((".", "?", "!")):
        return first_line.rstrip(":")

    # Fallback to sanitized filename
    return Path(filename).stem.replace("_", " ").title()


def _generate_document_id(file_path: Path) -> str:
    """Generates a stable, deterministic document ID from filename slug."""
    clean_stem = re.sub(r"[^a-zA-Z0-9_]+", "_", file_path.stem.lower()).strip("_")
    return clean_stem or "doc_unknown"


def _compute_sha256(content: str) -> str:
    """Computes SHA-256 hex digest for document versioning and change detection."""
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


# =====================================================================
# Extensible Format Loaders
# =====================================================================

def _load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_markdown_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


LOADER_REGISTRY = {
    ".txt": _load_text_file,
    ".md": _load_markdown_file,
}


def register_loader(extension: str, loader_fn):
    """Allows registering future document formats (e.g., .pdf, .docx)."""
    LOADER_REGISTRY[extension.lower()] = loader_fn


def load_document(file_path: str | Path) -> Document:
    """Load a single document from disk with identity and version metadata.

    Args:
        file_path: Path to the target file.

    Returns:
        Document: String-compatible document object with metadata.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Document file not found: {file_path}")

    ext = path.suffix.lower()
    if ext not in LOADER_REGISTRY:
        raise ValueError(
            f"Unsupported file format '{ext}' for file '{path.name}'. "
            f"Supported formats: {list(LOADER_REGISTRY.keys())}"
        )

    content = LOADER_REGISTRY[ext](path)
    content_hash = _compute_sha256(content)
    document_id = _generate_document_id(path)
    title = _extract_title(content, path.name)

    # Normalize source path with forward slashes for cross-platform consistency
    normalized_source = str(path).replace("\\", "/")

    return Document(
        content=content,
        document_id=document_id,
        filename=path.name,
        title=title,
        source=normalized_source,
        file_extension=ext,
        content_hash=content_hash,
        version=content_hash[:8],
    )


def load_directory(
    directory_path: str | Path = "data/documents",
    supported_extensions: tuple = (".txt", ".md"),
) -> list[Document]:
    """Scans and loads all supported documents from a directory.

    Args:
        directory_path: Path to documents directory.
        supported_extensions: Tuple of file suffixes to load.

    Returns:
        List of loaded Document objects sorted by document_id.
    """
    dir_path = Path(directory_path)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Directory not found: {directory_path}")

    documents = []
    for file_path in sorted(dir_path.iterdir()):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            try:
                doc = load_document(file_path)
                documents.append(doc)
            except Exception as e:
                print(f"[Warning] Failed to load '{file_path.name}': {e}")

    return documents