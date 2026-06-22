from uuid import uuid4

import pytest

from app.domain.rag import RetrievalQuery


def test_retrieval_query_rejects_invalid_alpha() -> None:
    with pytest.raises(ValueError):
        RetrievalQuery(tenant_id=uuid4(), query="CVE-2026-0001", alpha=1.5)


def test_retrieval_query_rejects_invalid_top_k() -> None:
    with pytest.raises(ValueError):
        RetrievalQuery(tenant_id=uuid4(), query="powershell encoded command", top_k=0)
