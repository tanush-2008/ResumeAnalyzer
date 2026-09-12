from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SavedReportCreate(BaseModel):
    target_role: str
    match_score: float
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    pdf_base64: str | None = None


class SavedReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_role: str
    match_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    created_at: datetime
    has_pdf: bool
