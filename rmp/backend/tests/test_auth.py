import pytest
from unittest.mock import Mock, patch


class TestAuthFunctions:
    """Test authentication utility functions"""

    def test_verify_password_success(self):
        """Test password verification with correct password"""
        from auth import verify_password, get_password_hash
        
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self):
        """Test password verification with incorrect password"""
        from auth import verify_password, get_password_hash
        
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False

    def test_get_password_hash(self):
        """Test password hashing"""
        from auth import get_password_hash
        
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash format

    def test_create_access_token(self):
        """Test JWT token creation"""
        from auth import create_access_token
        from jose import jwt
        import os
        
        test_data = {"sub": "test@example.com"}
        token = create_access_token(test_data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode token to verify it's valid
        secret_key = os.getenv("SECRET_KEY", "supersecretkey")
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert decoded["sub"] == "test@example.com"
        assert "exp" in decoded


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_register_success(self, client, test_user_data):
        """Test successful user registration"""
        response = client.post("/auth/register", json=test_user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert "id" in data
        assert "hashed_password" not in data  # Password should not be returned

    def test_register_duplicate_email(self, client, test_user_data):
        """Test registration with duplicate email"""
        # Register first user
        client.post("/auth/register", json=test_user_data)
        
        # Try to register again with same email
        response = client.post("/auth/register", json=test_user_data)
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        invalid_data = {
            "email": "invalid-email",
            "password": "testpassword123"
        }
        
        response = client.post("/auth/register", json=invalid_data)
        assert response.status_code == 422  # Validation error

    def test_login_success(self, client, test_user_data):
        """Test successful login"""
        # Register user first
        client.post("/auth/register", json=test_user_data)
        
        # Login
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        response = client.post("/auth/login", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client, test_user_data):
        """Test login with invalid credentials"""
        # Register user first
        client.post("/auth/register", json=test_user_data)
        
        # Try login with wrong password
        login_data = {
            "username": test_user_data["email"],
            "password": "wrongpassword"
        }
        response = client.post("/auth/login", data=login_data)
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "somepassword"
        }
        response = client.post("/auth/login", data=login_data)
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    @patch('auth.log_authentication_event')
    def test_login_audit_logging(self, mock_audit, client, test_user_data):
        """Test that authentication events are logged"""
        # Register user first
        client.post("/auth/register", json=test_user_data)
        
        # Login
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        client.post("/auth/login", data=login_data)
        
        # Verify audit logging was called
        mock_audit.assert_called()
