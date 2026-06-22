from app.rag.hybrid import HybridQueryVector, SparseVector, normalize_hybrid_query


def test_normalize_hybrid_query_applies_alpha_weights() -> None:
    vector = HybridQueryVector(
        dense=[1.0, 2.0],
        sparse=SparseVector(indices=[3, 5], values=[10.0, 20.0]),
    )

    normalized = normalize_hybrid_query(vector, alpha=0.25)

    assert normalized.dense == [0.25, 0.5]
    assert normalized.sparse.values == [7.5, 15.0]
