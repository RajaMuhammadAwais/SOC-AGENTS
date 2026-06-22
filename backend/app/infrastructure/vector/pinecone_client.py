from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from app.core.config import Settings
from app.rag.indexing import PineconeVector


@asynccontextmanager
async def pinecone_client(settings: Settings) -> AsyncGenerator[object]:
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is required for vector operations")

    from pinecone import PineconeAsyncio

    async with PineconeAsyncio(api_key=settings.pinecone_api_key) as client:
        yield client


async def ensure_hybrid_index(settings: Settings) -> None:
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is required for vector operations")

    from pinecone import PineconeAsyncio, ServerlessSpec

    async with PineconeAsyncio(api_key=settings.pinecone_api_key) as client:
        if await client.has_index(settings.pinecone_index):
            return
        await client.create_index(
            name=settings.pinecone_index,
            vector_type="dense",
            dimension=settings.embedding_dimension,
            metric="dotproduct",
            spec=ServerlessSpec(
                cloud=settings.pinecone_cloud,
                region=settings.pinecone_region,
            ),
        )


@dataclass(frozen=True)
class PineconeVectorSink:
    index: object

    async def upsert(self, vectors: list[PineconeVector], *, namespace: str) -> None:
        await self.index.upsert(
            vectors=[
                {
                    "id": vector.id,
                    "values": vector.values,
                    "sparse_values": vector.sparse_values,
                    "metadata": vector.metadata,
                }
                for vector in vectors
            ],
            namespace=namespace,
        )
