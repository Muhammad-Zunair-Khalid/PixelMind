from fastapi import APIRouter, Depends

from auth import get_current_user_id
from database import get_db_connection
from services.quota_service import get_quota

router = APIRouter()


@router.get("/quota")
def quota_status(current_user_id: int = Depends(get_current_user_id)) -> dict:
    """Return today's quota usage for the authenticated user."""
    with get_db_connection() as conn:
        data = get_quota(current_user_id, conn)
        conn.commit()  # commit the INSERT if a new row was created
    return data
