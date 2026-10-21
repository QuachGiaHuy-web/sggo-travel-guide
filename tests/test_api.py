# -*- coding: utf-8 -*-
"""
test_api.py - Integration test suite for REST API endpoints
"""
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_places():
    response = client.get("/api/places")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "places" in data
    assert isinstance(data["places"], list)

def test_get_place_detail_404():
    response = client.get("/api/places/999999")
    assert response.status_code == 404
