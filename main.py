import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import initialize_database
from routers.auth_router import router as auth_router
from routers.chat_router import router as chat_router
from routers.gallery_router import router as gallery_router
from routers.search_router import router as search_router
from routers.upload_router import router as upload_router
from services.qdrant_service import ensure_collection

load_dotenv()

app = FastAPI(title="Smart Photo Gallery", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(gallery_router, prefix="/api", tags=["gallery"])
app.include_router(search_router, prefix="/api", tags=["search"])
app.include_router(chat_router, prefix="/api", tags=["chat"])


@app.on_event("startup")
def on_startup() -> None:
    Path("uploads").mkdir(parents=True, exist_ok=True)
    initialize_database()
    ensure_collection()


@app.get("/")
def root() -> dict:
    return {"message": "Smart Photo Gallery API is running"}
