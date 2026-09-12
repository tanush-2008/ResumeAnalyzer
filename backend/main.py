"""Optional FastAPI backend: user login + saved analysis reports.

The Streamlit app (app.py) works standalone without this backend. When this
service is reachable (BACKEND_URL, default http://localhost:8000), the
dashboard additionally offers account registration/login and lets users
save and revisit past analysis reports, backed by SQLite/PostgreSQL.

Run directly with: uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import base64
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import crud
import models
import schemas
from auth import create_access_token, decode_access_token, verify_password
from database import Base, SessionLocal, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Resume Analyzer - Backend API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing credentials"
    )
    if not token:
        raise unauthorized
    email = decode_access_token(token)
    if not email:
        raise unauthorized
    user = crud.get_user_by_email(db, email)
    if not user:
        raise unauthorized
    return user


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/register", response_model=schemas.UserOut, status_code=201)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user_in)


@app.post("/auth/login", response_model=schemas.Token)
def login(user_in: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, user_in.email)
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return schemas.Token(access_token=create_access_token(user.email))


@app.get("/auth/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.post("/reports", response_model=schemas.SavedReportOut, status_code=201)
def save_report(
    report_in: schemas.SavedReportCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    report = crud.create_report(db, current_user.id, report_in)
    return crud.report_to_out(report)


@app.get("/reports", response_model=list[schemas.SavedReportOut])
def get_reports(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    reports = crud.list_reports(db, current_user.id)
    return [crud.report_to_out(r) for r in reports]


@app.get("/reports/{report_id}/pdf")
def get_report_pdf(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    report = crud.get_report(db, current_user.id, report_id)
    if not report or not report.pdf_bytes:
        raise HTTPException(status_code=404, detail="Report or PDF not found")
    return {"pdf_base64": base64.b64encode(report.pdf_bytes).decode()}
