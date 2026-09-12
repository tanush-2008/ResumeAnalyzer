from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import relationship

from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    reports = relationship("SavedReport", back_populates="owner", cascade="all, delete-orphan")


class SavedReport(Base):
    __tablename__ = "saved_reports"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_role = Column(String, nullable=False)
    match_score = Column(Float, nullable=False)
    matched_skills = Column(String, default="")  # comma-separated
    missing_skills = Column(String, default="")  # comma-separated
    pdf_bytes = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    owner = relationship("User", back_populates="reports")
