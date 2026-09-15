import re
from dataclasses import dataclass
from enum import Enum


class ChunkingStrategy(str, Enum):
    AUTO = "auto"
    PARAGRAPH = "paragraph"
    MARKDOWN = "markdown"


@dataclass
class ChunkerConfig:
    """Configurable settings for text and document chunking."""
    chunk_size: int = 350
    chunk_overlap: int = 50
    strategy: ChunkingStrategy = ChunkingStrategy.AUTO
    preserve_headers: bool = True


DEFAULT_CONFIG = ChunkerConfig()


def _split_into_sentences(text: str) -> list[str]:
    """Splits a block of text into sentences based on punctuation."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _split_into_paragraphs(text: str) -> list[str]:
    """Splits text on double newlines."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs


def _chunk_paragraphs_with_overlap(
    paragraphs: list[str],
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """Chunks paragraphs, preserving coherent boundaries and applying overlap on split."""
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        # If single paragraph is larger than chunk_size, split by sentences
        if len(paragraph) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            sentences = _split_into_sentences(paragraph)
            for sentence in sentences:
                candidate = (
                    current_chunk + " " + sentence if current_chunk else sentence
                )
                if len(candidate) <= chunk_size:
                    current_chunk = candidate
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                        # Carry over overlap from end of previous chunk snapped to whole words
                        if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                            raw_tail = current_chunk[-chunk_overlap:]
                            space_idx = raw_tail.find(" ")
                            overlap_prefix = (
                                raw_tail[space_idx:].strip()
                                if space_idx != -1
                                else ""
                            )
                            current_chunk = (
                                f"{overlap_prefix} {sentence}".strip()
                                if overlap_prefix
                                else sentence
                            )
                        else:
                            current_chunk = sentence
                    else:
                        chunks.append(sentence)
                        current_chunk = ""
            continue

        candidate = (
            current_chunk + "\n\n" + paragraph if current_chunk else paragraph
        )

        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)
                # If overlap requested and within the same block, carry forward overlap
                if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                    # Take up to chunk_overlap chars snapped to space
                    tail = current_chunk[-chunk_overlap:]
                    space_idx = tail.find(" ")
                    overlap_seed = tail[space_idx:].strip() if space_idx != -1 else tail.strip()
                    # Only carry forward if it doesn't already fill the budget
                    if len(overlap_seed) + len(paragraph) + 2 <= chunk_size:
                        current_chunk = overlap_seed + "\n\n" + paragraph
                    else:
                        current_chunk = paragraph
                else:
                    current_chunk = paragraph
            else:
                current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _chunk_markdown_sections(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    preserve_headers: bool = True,
) -> list[str]:
    """Splits Markdown by headers and groups sections without severing headers from content."""
    # Split text into sections by Markdown headers (# or ## or ###)
    header_pattern = re.compile(r"^(#{1,6}\s+.*)$", re.MULTILINE)
    splits = header_pattern.split(text)

    # Reconstruct (header, body) sections
    sections = []
    main_title = ""
    i = 0
    while i < len(splits):
        token = splits[i].strip()
        if not token:
            i += 1
            continue

        if header_pattern.match(token):
            header = token
            body = splits[i + 1].strip() if i + 1 < len(splits) else ""
            if header.startswith("# ") and not main_title:
                main_title = header
            sections.append((header, body))
            i += 2
        else:
            # Standalone leading text before first header
            sections.append(("", token))
            i += 1

    chunks = []
    current_chunk = ""
    current_header = ""

    for header, body in sections:
        section_text = f"{header}\n\n{body}".strip() if header else body
        if not section_text:
            continue

        # If the whole section fits, try combining with current_chunk
        if len(section_text) <= chunk_size:
            candidate = (
                current_chunk + "\n\n" + section_text if current_chunk else section_text
            )
            if len(candidate) <= chunk_size:
                current_chunk = candidate
                if header:
                    current_header = header
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = section_text
                current_header = header
        else:
            # Section itself is larger than chunk_size: chunk paragraphs within section
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            paragraphs = _split_into_paragraphs(body)
            section_chunks = _chunk_paragraphs_with_overlap(
                paragraphs,
                chunk_size=chunk_size - (len(header) + 2 if (preserve_headers and header) else 0),
                chunk_overlap=chunk_overlap,
            )
            for sc in section_chunks:
                if preserve_headers and header and not sc.startswith("#"):
                    chunks.append(f"{header}\n\n{sc}")
                else:
                    chunks.append(sc)

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [text]


def chunk_text(
    text: str,
    chunk_size: int = 300,
    chunk_overlap: int = 0,
    strategy: ChunkingStrategy | str = ChunkingStrategy.AUTO,
    preserve_headers: bool = True,
) -> list[str]:
    """Configurable text chunking preserving paragraph, sentence, and Markdown boundaries.

    Args:
        text: Raw document text to split.
        chunk_size: Target maximum characters per chunk (default 300 for backward compatibility).
        chunk_overlap: Number of characters to overlap between sequential chunks.
        strategy: 'auto', 'markdown', or 'paragraph'.
        preserve_headers: When True, keeps Markdown headers attached to their content.

    Returns:
        List of clean, coherent chunk strings.
    """
    if not text or not text.strip():
        return []

    strat_val = strategy.value if isinstance(strategy, ChunkingStrategy) else str(strategy).lower()

    is_markdown = bool(re.search(r"^#{1,6}\s+", text, re.MULTILINE))

    if strat_val == "markdown" or (strat_val == "auto" and is_markdown):
        return _chunk_markdown_sections(
            text=text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            preserve_headers=preserve_headers,
        )

    # Paragraph-based coherent chunking
    paragraphs = _split_into_paragraphs(text)
    return _chunk_paragraphs_with_overlap(
        paragraphs=paragraphs,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )