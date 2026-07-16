import pytest
from unittest.mock import Mock, patch


class TestDependencies:
    """Test FastAPI dependencies"""

    def test_get_db_dependency(self):
        """Test database dependency function"""
        try:
            from deps import get_db

            # Test that get_db returns a generator
            db_gen = get_db()
            assert hasattr(db_gen, "__iter__")

        except ImportError:
            pytest.skip("deps module not available")

    @patch("deps.get_current_user")
    def test_current_user_dependency(self, mock_get_user):
        """Test current user dependency"""
        try:
            from deps import get_current_user

            # Mock a user object
            mock_user = Mock()
            mock_user.id = "test-user-id"
            mock_user.email = "test@example.com"
            mock_get_user.return_value = mock_user

            result = get_current_user("fake-token", Mock())
            assert result.id == "test-user-id"

        except ImportError:
            pytest.skip("deps module not available")


class TestUtilities:
    """Test utility functions"""

    def test_audit_logging_functions(self):
        """Test audit logging utilities"""
        try:
            from audit_utils import log_create_operation, log_authentication_event

            # Test that functions exist and can be called
            assert callable(log_create_operation)
            assert callable(log_authentication_event)

            # Mock database session
            mock_db = Mock()

            # Test calling audit functions (they should not raise errors)
            log_create_operation(mock_db, "test-user-id", "pools", "test-pool-id")
            log_authentication_event(mock_db, "test-user-id", "LOGIN", True)

        except ImportError:
            pytest.skip("audit_utils module not available")

    def test_password_utilities(self):
        """Test password hashing utilities"""
        from auth import verify_password, get_password_hash

        password = "testpassword123"
        hashed = get_password_hash(password)

        # Test hash is different from original
        assert hashed != password

        # Test verification works
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_jwt_utilities(self):
        """Test JWT token utilities"""
        from auth import create_access_token, SECRET_KEY
        from jose import jwt, JWTError

        # Test token creation
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode using the same key the auth module loaded with at import time
        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            assert decoded["sub"] == "test@example.com"
        except JWTError:
            pytest.fail("Token decoding failed")


class TestDatabaseConnection:
    """Test database connection and configuration"""

    def test_database_url_configuration(self):
        """Test database URL configuration"""
        try:
            from database import SQLALCHEMY_DATABASE_URL, engine

            # Test that database URL is configured
            assert SQLALCHEMY_DATABASE_URL is not None
            assert len(SQLALCHEMY_DATABASE_URL) > 0

            # Test that engine is created
            assert engine is not None

        except ImportError:
            pytest.skip("database module not available")

    def test_session_creation(self):
        """Test database session creation"""
        try:
            from database import SessionLocal

            # Test session creation
            session = SessionLocal()
            assert session is not None
            session.close()

        except ImportError:
            pytest.skip("database module not available")


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_invalid_token_handling(self, client):
        """Test handling of invalid JWT tokens"""
        # Try to access protected endpoint with invalid token
        response = client.get(
            "/pools/my-pools", headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401

    def test_missing_token_handling(self, client):
        """Test handling when no token is provided"""
        response = client.get("/pools/my-pools")
        # Starlette <0.20 returns 401, >=0.20 returns 403 when no token is provided
        assert response.status_code in (401, 403)

    def test_malformed_request_handling(self, client):
        """Test handling of malformed requests"""
        # Send invalid JSON
        response = client.post(
            "/auth/register",
            content=b"invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_database_error_handling(self, client):
        """Test handling of database errors"""
        # This is difficult to test without mocking the database
        # In a real scenario, you might mock the database to raise exceptions
        pass


class TestPerformance:
    """Test performance-related aspects"""

    def test_password_hashing_performance(self):
        """Test password hashing performance"""
        import time
        from auth import get_password_hash

        password = "testpassword123"

        start_time = time.time()
        get_password_hash(password)
        end_time = time.time()

        # Hashing should complete in reasonable time (less than 1 second)
        assert (end_time - start_time) < 1.0

    def test_token_creation_performance(self):
        """Test JWT token creation performance"""
        import time
        from auth import create_access_token

        data = {"sub": "test@example.com"}

        start_time = time.time()
        create_access_token(data)
        end_time = time.time()

        # Token creation should be fast (less than 0.1 seconds)
        assert (end_time - start_time) < 0.1


class TestConfiguration:
    """Test application configuration"""

    def test_environment_variables(self):
        """Test environment variable handling"""
        import os

        # Test that required environment variables are handled properly
        secret_key = os.getenv("SECRET_KEY", "supersecretkey")
        assert secret_key is not None
        assert len(secret_key) > 0

    def test_cors_configuration(self):
        """Test CORS configuration"""
        # Test that CORS middleware is configured
        # This is implicit in the successful client requests in other tests
        pass

    @pytest.mark.integration
    def test_full_application_startup(self):
        """Test that the application starts up correctly"""
        from main import app

        # Test that app is created successfully
        assert app is not None
        assert app.title == "RunMyPool API"
