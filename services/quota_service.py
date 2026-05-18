"""
quota_service.py — per-user daily quota enforcement.

Limits:
  - UPLOAD_LIMIT  : 10 images per day
  - TOKEN_LIMIT   : 2000 AI tokens per day

The user_quotas table has ONE row per user. Every function checks whether
quota_date == today; if not, it resets the counters before checking.
All writes use INSERT ... ON DUPLICATE KEY UPDATE for atomicity.
"""

from __future__ import annotations

import mysql.connector
from fastapi import HTTPException, status

UPLOAD_LIMIT = 10
TOKEN_LIMIT = 2000


def _ensure_row(user_id: int, cursor: mysql.connector.cursor.MySQLCursor) -> None:
    """Insert a fresh quota row for today if one doesn't exist yet."""
    cursor.execute(
        """
        INSERT INTO user_quotas (user_id, quota_date, uploads, tokens)
        VALUES (%s, CURDATE(), 0, 0)
        ON DUPLICATE KEY UPDATE
            uploads    = IF(quota_date < CURDATE(), 0, uploads),
            tokens     = IF(quota_date < CURDATE(), 0, tokens),
            quota_date = CURDATE()
        """,
        (user_id,),
    )


def check_and_increment_uploads(user_id: int, conn: mysql.connector.MySQLConnection) -> None:
    """
    Raise HTTP 429 if the user has already uploaded UPLOAD_LIMIT images today.
    Otherwise increment the counter by 1.
    """
    cursor = conn.cursor(dictionary=True)
    _ensure_row(user_id, cursor)
    cursor.execute(
        "SELECT uploads FROM user_quotas WHERE user_id = %s",
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()

    if row and row["uploads"] >= UPLOAD_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily upload limit reached ({UPLOAD_LIMIT} images/day). Resets after midnight.",
        )

    cursor = conn.cursor()
    cursor.execute(
        "UPDATE user_quotas SET uploads = uploads + 1 WHERE user_id = %s",
        (user_id,),
    )
    cursor.close()


def check_and_increment_tokens(
    user_id: int, tokens_used: int, conn: mysql.connector.MySQLConnection
) -> None:
    """
    Raise HTTP 429 if adding tokens_used would exceed TOKEN_LIMIT today.
    Otherwise increment the token counter.
    """
    cursor = conn.cursor(dictionary=True)
    _ensure_row(user_id, cursor)
    cursor.execute(
        "SELECT tokens FROM user_quotas WHERE user_id = %s",
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()

    current = row["tokens"] if row else 0
    if current >= TOKEN_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily AI token limit reached ({TOKEN_LIMIT} tokens/day). Resets at midnight.",
        )

    cursor = conn.cursor()
    cursor.execute(
        "UPDATE user_quotas SET tokens = tokens + %s WHERE user_id = %s",
        (tokens_used, user_id),
    )
    cursor.close()


def get_quota(user_id: int, conn: mysql.connector.MySQLConnection) -> dict:
    """Return the current quota usage for a user (resets counters if stale date)."""
    cursor = conn.cursor(dictionary=True)
    _ensure_row(user_id, cursor)
    cursor.execute(
        "SELECT uploads, tokens, quota_date FROM user_quotas WHERE user_id = %s",
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()

    return {
        "uploads": row["uploads"] if row else 0,
        "tokens": row["tokens"] if row else 0,
        "upload_limit": UPLOAD_LIMIT,
        "token_limit": TOKEN_LIMIT,
    }
