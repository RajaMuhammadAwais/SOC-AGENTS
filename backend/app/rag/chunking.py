from dataclasses import dataclass
from hashlib import sha256
from textwrap import shorten


@dataclass(frozen=True)
class Document:
    source_id: str
    title: str
    text: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_id: str
    title: str
    text: str
    metadata: dict[str, str]


def normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    compact_lines = [line for line in lines if line]
    return "\n".join(compact_lines)


def chunk_document(document: Document, *, max_chars: int = 1800, overlap_chars: int = 200) -> list[Chunk]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be non-negative and smaller than max_chars")

    text = normalize_text(document.text)
    if not text:
        return []

    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk_text = text[start:end].strip()
        digest = sha256(f"{document.source_id}:{start}:{chunk_text}".encode("utf-8")).hexdigest()
        chunks.append(
            Chunk(
                chunk_id=digest[:32],
                source_id=document.source_id,
                title=document.title,
                text=chunk_text,
                metadata={
                    **document.metadata,
                    "offset_start": str(start),
                    "offset_end": str(end),
                    "preview": shorten(chunk_text, width=160, placeholder="..."),
                },
            )
        )
        if end == len(text):
            break
        start = end - overlap_chars
    return chunks
