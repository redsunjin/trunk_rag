from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app_api


@pytest.fixture()
def client():
    with TestClient(app_api.app, raise_server_exceptions=False) as test_client:
        yield test_client
