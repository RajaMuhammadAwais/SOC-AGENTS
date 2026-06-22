from dataclasses import dataclass


@dataclass(frozen=True)
class SparseVector:
    indices: list[int]
    values: list[float]


@dataclass(frozen=True)
class HybridQueryVector:
    dense: list[float]
    sparse: SparseVector


def normalize_hybrid_query(vector: HybridQueryVector, *, alpha: float) -> HybridQueryVector:
    if not 0 <= alpha <= 1:
        raise ValueError("alpha must be between 0 and 1")

    dense_weight = alpha
    sparse_weight = 1 - alpha
    return HybridQueryVector(
        dense=[value * dense_weight for value in vector.dense],
        sparse=SparseVector(
            indices=vector.sparse.indices,
            values=[value * sparse_weight for value in vector.sparse.values],
        ),
    )
