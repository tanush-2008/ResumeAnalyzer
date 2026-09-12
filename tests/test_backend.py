"""Integration tests for the optional FastAPI backend (auth + saved reports).

Run with: python -m pytest tests/test_backend.py -v
Uses a temporary SQLite file so it never touches data/app.db.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_app.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    # Reload modules bound to the (possibly already-imported) DATABASE_URL.
    for mod_name in ["database", "models", "main"]:
        sys.modules.pop(mod_name, None)

    from fastapi.testclient import TestClient
    import main

    return TestClient(main.app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_register_login_and_saved_reports_flow(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 201

    r = client.post("/auth/register", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 400  # duplicate email

    r = client.post("/auth/login", json={"email": "a@example.com", "password": "wrong"})
    assert r.status_code == 401

    r = client.post("/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/reports", headers=headers)
    assert r.status_code == 200
    assert r.json() == []

    r = client.post(
        "/reports",
        json={
            "target_role": "Data Analyst",
            "match_score": 68.1,
            "matched_skills": ["python", "sql"],
            "missing_skills": ["excel"],
        },
        headers=headers,
    )
    assert r.status_code == 201

    r = client.get("/reports", headers=headers)
    assert len(r.json()) == 1
    assert r.json()[0]["target_role"] == "Data Analyst"


def test_reports_require_authentication(client):
    r = client.get("/reports")
    assert r.status_code == 401

    r = client.get("/reports", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
