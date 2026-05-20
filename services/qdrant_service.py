import os

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models

load_dotenv()

COLLECTION_NAME = "gallery"
VECTOR_SIZE = 384

qdrant_client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", "6333")),
)


def ensure_collection() -> None:
    collections = qdrant_client.get_collections().collections
    existing = {collection.name for collection in collections}
    if COLLECTION_NAME in existing:
        return

    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )


def store_vector(image_id: int, user_id: int, caption: str, vector: list[float]) -> None:
    point = models.PointStruct(
        id=image_id,
        vector=vector,
        payload={"user_id": user_id, "image_id": image_id, "caption": caption},
    )
    qdrant_client.upsert(collection_name=COLLECTION_NAME, points=[point])


def search_vectors(query_vector: list[float], user_id: int, limit: int = 50, score_threshold: float = 0.5) -> list[dict]:
    response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                )
            ]
        ),
        limit=limit,
        score_threshold=score_threshold,
        with_payload=True,
    )

    return [
        {
            "image_id": int(hit.payload.get("image_id", hit.id)),
            "caption": hit.payload.get("caption"),
            "score": float(hit.score),
        }
        for hit in response.points
    ]


def delete_vector(image_id: int) -> None:
    qdrant_client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.PointIdsList(points=[image_id]),
    )

