from __future__ import annotations

from typing import Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.config import QDRANT_COLLECTION, QDRANT_URL, VECTOR_SIZE
from app.rag.embeddings import HashingEmbedder

embedder = HashingEmbedder(VECTOR_SIZE)


def get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_collection() -> None:
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


def index_chunks(chunks: list[dict[str, Any]]) -> int:
    ensure_collection()
    client = get_client()
    points: list[PointStruct] = []
    for i, chunk in enumerate(chunks):
        vector = embedder.embed(chunk["text"])
        payload = {**chunk["metadata"], "text": chunk["text"], "chunk_id": chunk["id"]}
        # stable numeric-ish id from hash is okay, but use incremental offset after current MVP simplicity
        points.append(PointStruct(id=abs(hash(chunk["id"])) % (2**63), vector=vector, payload=payload))
    if points:
        client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    return len(points)


def search_policy(query: str, product_type: str | None = None, top_k: int = 5) -> list[dict[str, Any]]:
    ensure_collection()
    client = get_client()
    query_vector = embedder.embed(query)
    q_filter = None
    if product_type:
        q_filter = Filter(must=[FieldCondition(key="product_type", match=MatchValue(value=product_type))])
    # Qdrant client versions differ: older versions expose `search`, newer versions
    # prefer `query_points`. Support both so this runs across local environments.
    if hasattr(client, "search"):
        results = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            query_filter=q_filter,
            limit=top_k,
            with_payload=True,
        )
    else:
        response = client.query_points(
            collection_name=QDRANT_COLLECTION,
            query=query_vector,
            query_filter=q_filter,
            limit=top_k,
            with_payload=True,
        )
        results = response.points
    return [
        {
            "score": r.score,
            "text": r.payload.get("text", ""),
            "chunk_id": r.payload.get("chunk_id"),
            "source_file": r.payload.get("source_file"),
            "section": r.payload.get("section"),
            "clause_type": r.payload.get("clause_type"),
            "product_type": r.payload.get("product_type"),
        }
        for r in results
    ]
