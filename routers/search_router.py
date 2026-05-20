from fastapi import APIRouter, Depends

from auth import get_current_user_id
from database import get_db_connection
from models import SearchRequest, SearchResult
from services.embedding_service import encode
from services.qdrant_service import search_vectors

router = APIRouter()


@router.post("/search", response_model=list[SearchResult])
def semantic_search(
    payload: SearchRequest,
    current_user_id: int = Depends(get_current_user_id),
) -> list[SearchResult]:
    query_vector = encode(payload.query)
    qdrant_hits = search_vectors(query_vector=query_vector, user_id=current_user_id)

    if not qdrant_hits:
        return []

    image_ids = [hit["image_id"] for hit in qdrant_hits]
    placeholders = ",".join(["%s"] * len(image_ids))

    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f"SELECT id, caption FROM images WHERE user_id = %s AND id IN ({placeholders})",
            (current_user_id, *image_ids),
        )
        rows = cursor.fetchall()
        cursor.close()

    image_map = {int(row["id"]): row for row in rows}

    results: list[SearchResult] = []
    for hit in qdrant_hits:
        image_id = hit["image_id"]
        image_row = image_map.get(image_id)
        if not image_row:
            continue

        results.append(
            SearchResult(
                image_id=image_id,
                caption=image_row.get("caption"),
                score=float(hit["score"]),
                thumbnail_url=f"/api/images/{image_id}?type=annotated",
            )
        )

    return results
