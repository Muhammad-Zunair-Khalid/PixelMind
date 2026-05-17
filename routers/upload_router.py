import json
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from auth import get_current_user_id
from database import get_db_connection
from models import ObjectDetection, UploadResponse
from services.blip_service import generate_caption
from services.embedding_service import encode
from services.quota_service import check_and_increment_uploads
from services.qdrant_service import store_vector
from services.yolo_service import detect_objects

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png"}


@router.post("/upload", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user_id),
) -> UploadResponse:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only JPEG and PNG images are allowed",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Empty file")
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="File exceeds 10MB limit")

    try:
        image = Image.open(BytesIO(file_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=422, detail="Invalid image file") from exc

    # --- Quota check (before expensive processing) ---
    with get_db_connection() as conn:
        check_and_increment_uploads(current_user_id, conn)
        conn.commit()

    image_uuid = str(uuid4())
    user_dir = Path("uploads") / str(current_user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    original_path = user_dir / f"{image_uuid}.jpg"
    annotated_path = user_dir / f"{image_uuid}_annotated.jpg"

    image.save(original_path, format="JPEG", quality=95)

    caption = generate_caption(image)
    annotated_bytes, objects = detect_objects(image)

    annotated_path.write_bytes(annotated_bytes)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO images (user_id, file_path, annotated_path, caption, objects_detected)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                current_user_id,
                str(original_path),
                str(annotated_path),
                caption,
                json.dumps(objects),
            ),
        )
        image_id = cursor.lastrowid
        conn.commit()
        cursor.close()

    vector = encode(caption)
    store_vector(image_id=image_id, user_id=current_user_id, caption=caption, vector=vector)

    return UploadResponse(
        image_id=image_id,
        caption=caption,
        objects=[ObjectDetection(**obj) for obj in objects],
    )
