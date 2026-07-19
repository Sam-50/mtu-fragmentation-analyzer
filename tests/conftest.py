"""Shared test fixtures."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient
import pytest


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
