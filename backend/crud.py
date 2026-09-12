from __future__ import annotations

import base64

from sqlalchemy.orm import Session

import models
import schemas
from auth import hash_password


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    user = models.User(email=user_in.email, hashed_password=hash_password(user_in.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_report(db: Session, owner_id: int, report_in: schemas.SavedReportCreate) -> models.SavedReport:
    pdf_bytes = base64.b64decode(report_in.pdf_base64) if report_in.pdf_base64 else None
    report = models.SavedReport(
        owner_id=owner_id,
        target_role=report_in.target_role,
        match_score=report_in.match_score,
        matched_skills=",".join(report_in.matched_skills),
        missing_skills=",".join(report_in.missing_skills),
        pdf_bytes=pdf_bytes,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def list_reports(db: Session, owner_id: int) -> list[models.SavedReport]:
    return (
        db.query(models.SavedReport)
        .filter(models.SavedReport.owner_id == owner_id)
        .order_by(models.SavedReport.created_at.desc())
        .all()
    )


def get_report(db: Session, owner_id: int, report_id: int) -> models.SavedReport | None:
    return (
        db.query(models.SavedReport)
        .filter(models.SavedReport.owner_id == owner_id, models.SavedReport.id == report_id)
        .first()
    )


def report_to_out(report: models.SavedReport) -> schemas.SavedReportOut:
    return schemas.SavedReportOut(
        id=report.id,
        target_role=report.target_role,
        match_score=report.match_score,
        matched_skills=[s for s in report.matched_skills.split(",") if s],
        missing_skills=[s for s in report.missing_skills.split(",") if s],
        created_at=report.created_at,
        has_pdf=report.pdf_bytes is not None,
    )
