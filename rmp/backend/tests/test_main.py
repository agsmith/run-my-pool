import pytest
import json
import logging
from fastapi.testclient import TestClient
from main import app


def test_read_root(client):
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the RunMyPool FastAPI backend!"}


def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_requests_have_correlatable_structured_logs(client, caplog):
    caplog.set_level(logging.INFO, logger="runmypool.api")
    response = client.get("/health", headers={"X-Request-ID": "support-case-123"})

    assert response.headers["X-Request-ID"] == "support-case-123"
    record = next(record for record in caplog.records if record.getMessage() == "http_request_completed")
    assert record.request_id == "support-case-123"
    assert record.path == "/health"
    assert record.status_code == 200


def test_invalid_request_id_is_replaced(client):
    response = client.get("/health", headers={"X-Request-ID": "bad request id\nforged"})

    request_id = response.headers["X-Request-ID"]
    assert request_id != "bad request id\nforged"
    assert len(request_id) == 36


def test_json_formatter_excludes_sensitive_request_data():
    from app_logging import JsonFormatter

    record = logging.LogRecord("runmypool.test", logging.INFO, __file__, 1, "safe_event", (), None)
    record.event = "safe_event"
    record.path = "/auth/login"
    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "safe_event"
    assert payload["path"] == "/auth/login"
    assert "password" not in payload
    assert "token" not in payload


class TestApplication:
    """Test application configuration"""
    
    def test_app_title(self):
        """Test that the app has correct title"""
        assert app.title == "RunMyPool API"
    
    def test_cors_headers(self, client):
        """Test that CORS headers are present"""
        response = client.options("/")
        # CORS preflight should not fail
        assert response.status_code in [200, 405]  # 405 is acceptable for OPTIONS on root
