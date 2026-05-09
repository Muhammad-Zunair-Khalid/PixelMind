import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from auth import get_current_user_id, get_current_user_id_flexible
from database import get_db_connection
from models import GalleryItem, ObjectDetection

router = APIRouter()


@router.get("/gallery", response_model=list[GalleryItem])
def get_gallery(current_user_id: int = Depends(get_current_user_id)) -> list[GalleryItem]:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, caption, objects_detected, uploaded_at
            FROM images
            WHERE user_id = %s
            ORDER BY uploaded_at DESC
            """,
            (current_user_id,),
        )
        rows = cursor.fetchall()
        cursor.close()

    items: list[GalleryItem] = []
    for row in rows:
        objects_raw = row.get("objects_detected")
        if isinstance(objects_raw, str):
            objects = json.loads(objects_raw)
        elif isinstance(objects_raw, list):
            objects = objects_raw
        else:
            objects = []

        items.append(
            GalleryItem(
                image_id=row["id"],
                caption=row.get("caption"),
                objects_detected=[ObjectDetection(**obj) for obj in objects],
                uploaded_at=row["uploaded_at"],
                thumbnail_url=f"/api/images/{row['id']}?type=annotated",
            )
        )

    return items


@router.get("/images/{image_id}")
def get_image(
    image_id: int,
    type: Literal["original", "annotated"] = Query(default="original"),
    current_user_id: int = Depends(get_current_user_id_flexible),
):
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, file_path, annotated_path FROM images WHERE id = %s",
            (image_id,),
        )
        row = cursor.fetchone()
        cursor.close()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    if int(row["user_id"]) != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    selected_path = row["annotated_path"] if type == "annotated" else row["file_path"]
    fallback_path  = row["file_path"] if type == "annotated" else row["annotated_path"]

    # Use preferred path if it exists, otherwise fall back to the other variant
    chosen = None
    for candidate in (selected_path, fallback_path):
        if candidate and Path(candidate).exists():
            chosen = candidate
            break

    if not chosen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file not found on disk")

    return FileResponse(path=Path(chosen), media_type="image/jpeg")

