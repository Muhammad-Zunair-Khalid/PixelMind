from pathlib import Path

import mysql.connector
from fastapi import APIRouter, HTTPException, status

from auth import create_access_token, hash_password, verify_password
from database import get_db_connection
from models import LoginRequest, SignupRequest, TokenResponse

router = APIRouter()


@router.post("/signup", response_model=TokenResponse)
def signup(payload: SignupRequest) -> TokenResponse:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "INSERT INTO users (email, username, password_hash) VALUES (%s, %s, %s)",
                (payload.email, payload.username, hash_password(payload.password)),
            )
            user_id = cursor.lastrowid
            conn.commit()
        except mysql.connector.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Email already exists",
            ) from exc
        finally:
            cursor.close()

    Path("uploads").mkdir(exist_ok=True)
    Path("uploads").joinpath(str(user_id)).mkdir(parents=True, exist_ok=True)
    token = create_access_token(user_id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, password_hash FROM users WHERE email = %s", (payload.email,))
        user = cursor.fetchone()
        cursor.close()

    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(int(user["id"]))
    return TokenResponse(access_token=token)
