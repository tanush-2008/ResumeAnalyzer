"""Optional FastAPI backend: user login + saved analysis reports.

The Streamlit app (app.py) works standalone without this backend. When this
service is reachable (BACKEND_URL, default http://localhost:8000), the
dashboard additionally offers account registration/login and lets users
save and revisit past analysis reports, backed by SQLite/PostgreSQL.

Run directly with: uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import base64
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

import crud
import models
import schemas
from auth import create_access_token, decode_access_token, verify_password
from database import Base, engine, get_db

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("resume_analyzer.api")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Resume Analyzer - Backend API",
    description="Optional auth + saved-reports service for the AI Resume Analyzer dashboard.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting protects the auth endpoints from credential-stuffing / brute
# force attempts - the only endpoints that don't already require a valid JWT.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    return response


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


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "service": "AI Resume Analyzer - Backend API",
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/register", response_model=schemas.UserOut, status_code=201, tags=["auth"])
@limiter.limit("5/minute")
def register(request: Request, user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user_in)


@app.post("/auth/login", response_model=schemas.Token, tags=["auth"])
@limiter.limit("10/minute")
def login(request: Request, user_in: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, user_in.email)
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return schemas.Token(access_token=create_access_token(user.email))


@app.get("/auth/me", response_model=schemas.UserOut, tags=["auth"])
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.post("/reports", response_model=schemas.SavedReportOut, status_code=201, tags=["reports"])
def save_report(
    report_in: schemas.SavedReportCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    report = crud.create_report(db, current_user.id, report_in)
    return crud.report_to_out(report)


@app.get("/reports", response_model=list[schemas.SavedReportOut], tags=["reports"])
def get_reports(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    reports = crud.list_reports(db, current_user.id)
    return [crud.report_to_out(r) for r in reports]


@app.get("/reports/{report_id}", response_model=schemas.SavedReportOut, tags=["reports"])
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    report = crud.get_report(db, current_user.id, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return crud.report_to_out(report)


@app.get("/reports/{report_id}/pdf", tags=["reports"])
def get_report_pdf(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    report = crud.get_report(db, current_user.id, report_id)
    if not report or not report.pdf_bytes:
        raise HTTPException(status_code=404, detail="Report or PDF not found")
    return {"pdf_base64": base64.b64encode(report.pdf_bytes).decode()}


@app.delete("/reports/{report_id}", status_code=204, tags=["reports"])
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    report = crud.get_report(db, current_user.id, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    crud.delete_report(db, report)
    return None
