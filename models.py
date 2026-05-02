from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ObjectDetection(BaseModel):
    label: str
    confidence: float


class UploadResponse(BaseModel):
    image_id: int
    caption: str
    objects: list[ObjectDetection]


class GalleryItem(BaseModel):
    image_id: int
    caption: str | None
    objects_detected: list[ObjectDetection]
    uploaded_at: datetime
    thumbnail_url: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class SearchResult(BaseModel):
    image_id: int
    caption: str | None
    score: float
    thumbnail_url: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    image_id: int
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
