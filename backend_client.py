"""Thin client the Streamlit app uses to talk to the optional FastAPI backend.

Every function fails soft (returns None / False / []) instead of raising, so
the dashboard can offer login and saved-report features when the backend is
reachable and silently degrade to standalone mode when it isn't.
"""

from __future__ import annotations

import base64
import os

import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
_TIMEOUT = 3


def backend_available() -> bool:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=_TIMEOUT)
        return r.status_code == 200
    except requests.RequestException:
        return False


def register(email: str, password: str) -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{BACKEND_URL}/auth/register",
            json={"email": email, "password": password},
            timeout=_TIMEOUT,
        )
        if r.status_code == 201:
            return True, "Account created. You can now log in."
        return False, r.json().get("detail", "Registration failed.")
    except requests.RequestException as exc:
        return False, f"Backend unreachable: {exc}"


def login(email: str, password: str) -> tuple[str | None, str]:
    try:
        r = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()["access_token"], "Logged in."
        return None, r.json().get("detail", "Login failed.")
    except requests.RequestException as exc:
        return None, f"Backend unreachable: {exc}"


def save_report(
    token: str,
    target_role: str,
    match_score: float,
    matched_skills: list[str],
    missing_skills: list[str],
    pdf_bytes: bytes | None = None,
) -> tuple[bool, str]:
    payload = {
        "target_role": target_role,
        "match_score": match_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "pdf_base64": base64.b64encode(pdf_bytes).decode() if pdf_bytes else None,
    }
    try:
        r = requests.post(
            f"{BACKEND_URL}/reports",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )
        if r.status_code == 201:
            return True, "Report saved."
        return False, r.json().get("detail", "Could not save report.")
    except requests.RequestException as exc:
        return False, f"Backend unreachable: {exc}"


def list_reports(token: str) -> list[dict]:
    try:
        r = requests.get(
            f"{BACKEND_URL}/reports",
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()
        return []
    except requests.RequestException:
        return []


def delete_report(token: str, report_id: int) -> tuple[bool, str]:
    try:
        r = requests.delete(
            f"{BACKEND_URL}/reports/{report_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )
        if r.status_code == 204:
            return True, "Report deleted."
        return False, "Could not delete report."
    except requests.RequestException as exc:
        return False, f"Backend unreachable: {exc}"


def get_report_pdf(token: str, report_id: int) -> bytes | None:
    try:
        r = requests.get(
            f"{BACKEND_URL}/reports/{report_id}/pdf",
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            return base64.b64decode(r.json()["pdf_base64"])
        return None
    except requests.RequestException:
        return None
