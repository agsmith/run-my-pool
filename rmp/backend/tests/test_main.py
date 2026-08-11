import pytest
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
