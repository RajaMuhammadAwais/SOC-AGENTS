import pytest

from app.rag.chunking import Document, chunk_document, normalize_text


def test_normalize_text_removes_blank_lines_and_extra_space() -> None:
    assert normalize_text(" one \n\n two \r\n three ") == "one\ntwo\nthree"


def test_chunk_document_creates_stable_chunks_with_overlap() -> None:
    document = Document(
        source_id="nist-csf",
        title="NIST CSF",
        text="a" * 120,
        metadata={"source": "nist"},
    )

    chunks = chunk_document(document, max_chars=50, overlap_chars=10)

    assert len(chunks) == 3
    assert chunks[0].metadata["offset_start"] == "0"
    assert chunks[1].metadata["offset_start"] == "40"


def test_chunk_document_rejects_invalid_overlap() -> None:
    document = Document(source_id="x", title="x", text="abc", metadata={})

    with pytest.raises(ValueError):
        chunk_document(document, max_chars=100, overlap_chars=100)
