import json

from fastapi import APIRouter, Depends, HTTPException, status

from auth import get_current_user_id
from database import get_db_connection
from models import ChatRequest, ChatResponse
from services.grok_service import chat_about_image
from services.quota_service import check_and_increment_tokens

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user_id: int = Depends(get_current_user_id),
) -> ChatResponse:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, caption, objects_detected FROM images WHERE id = %s",
            (payload.image_id,),
        )
        row = cursor.fetchone()
        cursor.close()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    if int(row["user_id"]) != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    objects_raw = row.get("objects_detected")
    if isinstance(objects_raw, str):
        objects = json.loads(objects_raw)
    elif isinstance(objects_raw, list):
        objects = objects_raw
    else:
        objects = []

    reply, tokens_used = chat_about_image(
        caption=row.get("caption") or "",
        objects=objects,
        history=[message.model_dump() for message in payload.history],
        user_message=payload.message,
    )

    # Record token usage and enforce quota (after the call so we count real tokens)
    with get_db_connection() as conn:
        check_and_increment_tokens(current_user_id, tokens_used, conn)
        conn.commit()

    return ChatResponse(reply=reply)
