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


def test_auth_refuses_default_secret_in_production(monkeypatch):
    import importlib

    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    sys.modules.pop("auth", None)
    with pytest.raises(RuntimeError, match="Refusing to start"):
        importlib.import_module("auth")

    # Re-import cleanly (dev env) so later tests get a working auth module.
    sys.modules.pop("auth", None)
    monkeypatch.delenv("APP_ENV", raising=False)
    importlib.import_module("auth")


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


def test_root_and_get_single_report(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "service" in r.json()

    client.post("/auth/register", json={"email": "b@example.com", "password": "password123"})
    token = client.post(
        "/auth/login", json={"email": "b@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/reports",
        json={"target_role": "AI Engineer", "match_score": 55.0, "matched_skills": ["python"]},
        headers=headers,
    ).json()

    r = client.get(f"/reports/{created['id']}", headers=headers)
    assert r.status_code == 200
    assert r.json()["target_role"] == "AI Engineer"

    r = client.get("/reports/99999", headers=headers)
    assert r.status_code == 404


def test_login_is_rate_limited(client):
    client.post("/auth/register", json={"email": "d@example.com", "password": "password123"})
    responses = [
        client.post("/auth/login", json={"email": "d@example.com", "password": "wrong"})
        for _ in range(15)
    ]
    statuses = [r.status_code for r in responses]
    assert 429 in statuses, "expected the login endpoint to start rate-limiting repeated attempts"


def test_delete_report(client):
    client.post("/auth/register", json={"email": "c@example.com", "password": "password123"})
    token = client.post(
        "/auth/login", json={"email": "c@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/reports",
        json={"target_role": "Data Scientist", "match_score": 60.0},
        headers=headers,
    ).json()

    r = client.delete(f"/reports/{created['id']}", headers=headers)
    assert r.status_code == 204

    r = client.get(f"/reports/{created['id']}", headers=headers)
    assert r.status_code == 404

    r = client.delete("/reports/99999", headers=headers)
    assert r.status_code == 404
