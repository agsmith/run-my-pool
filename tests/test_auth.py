"""
Unit tests for authentication and session management in the Run My Pool application.
Tests login, logout, session handling, password management, and user authentication.
"""

import pytest
import hashlib
import secrets
import base64
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from main import get_current_user
from models import User_IAM


class TestAuthentication:
    """Test authentication functionality"""
    
    def test_login_page_accessible(self, test_client):
        """Test that login page is accessible"""
        response = test_client.get("/login")
        assert response.status_code == 200
        assert "login" in response.text.lower()
    
    def test_valid_login(self, test_client, test_db, sample_user_iam):
        """Test successful login with valid credentials"""
        response = test_client.post(
            "/login",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=False
        )
        
        assert response.status_code == 302  # Redirect after successful login
        assert "session-token" in response.cookies
        
        # Verify session token was set in database
        user = test_db.query(User_IAM).filter(User_IAM.username == "testuser").first()
        assert user.session_token is not None
    
    def test_invalid_username_login(self, test_client, test_db, sample_user_iam):
        """Test login with invalid username"""
        response = test_client.post(
            "/login",
            data={"username": "nonexistent", "password": "password123"}
        )
        
        assert response.status_code == 200
        assert "Invalid username or password" in response.text
    
    def test_invalid_password_login(self, test_client, test_db, sample_user_iam):
        """Test login with invalid password"""
        response = test_client.post(
            "/login",
            data={"username": "testuser", "password": "wrongpassword"}
        )
        
        assert response.status_code == 200
        assert "Invalid username or password" in response.text
    
    def test_username_format_validation(self, test_client):
        """Test username format validation during login"""
        # Test invalid characters
        response = test_client.post(
            "/login",
            data={"username": "user@invalid", "password": "password123"}
        )
        assert response.status_code == 200
        assert "Invalid username format" in response.text
        
        # Test too short username
        response = test_client.post(
            "/login",
            data={"username": "ab", "password": "password123"}
        )
        assert response.status_code == 200
        assert "Invalid username format" in response.text
    
    def test_password_length_validation(self, test_client):
        """Test password length validation during login"""
        long_password = "a" * 300
        response = test_client.post(
            "/login",
            data={"username": "testuser", "password": long_password}
        )
        assert response.status_code == 200
        assert "Password too long" in response.text
    
    def test_force_password_change_redirect(self, test_client, test_db):
        """Test redirect to password change when force_password_change is True"""
        from security_config import PasswordSecurity
        
        # Create user with forced password change using secure bcrypt
        hashed_password, salt = PasswordSecurity.hash_password("password123")
        user = User_IAM(
            username="forcechange",
            password=hashed_password,
            salt=salt,
            email="force@example.com",
            force_password_change=True,
            failed_login_attempts=0,
            account_locked=False
        )
        test_db.add(user)
        test_db.commit()
        
        response = test_client.post(
            "/login",
            data={"username": "forcechange", "password": "password123"},
            follow_redirects=False
        )
        
        assert response.status_code == 302
        assert "/change-password" in response.headers["location"]


class TestSessionManagement:
    """Test session token management"""
    
    def test_get_current_user_valid_session(self, test_db, sample_user_iam):
        """Test getting current user with valid session"""
        from unittest.mock import Mock
        from datetime import datetime
        
        # Set session token
        session_token = secrets.token_urlsafe(32)
        sample_user_iam.session_token = session_token
        test_db.commit()
        
        # Create mock request with session cookie using new format
        timestamp = datetime.utcnow().isoformat()
        session_data = f"{sample_user_iam.username}|{session_token}|{timestamp}"
        encoded_session = base64.b64encode(session_data.encode()).decode()
        
        mock_request = Mock()
        mock_request.cookies = {"session-token": encoded_session}
        
        user = get_current_user(mock_request, test_db)
        
        assert user is not None
        assert user["username"] == "testuser"
        assert user["admin_role"] is False
    
    def test_get_current_user_invalid_session(self, test_db):
        """Test getting current user with invalid session"""
        from unittest.mock import Mock
        
        mock_request = Mock()
        mock_request.cookies = {"session-token": "invalid_token"}
        
        user = get_current_user(mock_request, test_db)
        assert user is None
    
    def test_get_current_user_no_session(self, test_db):
        """Test getting current user with no session cookie"""
        from unittest.mock import Mock
        
        mock_request = Mock()
        mock_request.cookies = {}
        
        user = get_current_user(mock_request, test_db)
        assert user is None
    
    def test_logout_clears_session(self, test_client, test_db, authenticated_user_cookie):
        """Test that logout clears session token"""
        # Login first
        cookies = {"session-token": authenticated_user_cookie}
        
        response = test_client.get("/logout", cookies=cookies, follow_redirects=False)
        
        assert response.status_code == 302
        assert response.headers["location"] == "/login"
        
        # Verify session token was cleared in database
        user = test_db.query(User_IAM).filter(User_IAM.username == "testuser").first()
        assert user.session_token is None


class TestPasswordManagement:
    """Test password change and reset functionality"""
    
    def test_change_password_page(self, test_client):
        """Test password change page accessibility"""
        response = test_client.get("/change-password?username=testuser")
        assert response.status_code == 200
        assert "change" in response.text.lower()
        assert "password" in response.text.lower()
    
    def test_change_password_success(self, test_client, test_db, sample_user_iam):
        """Test successful password change"""
        response = test_client.post(
            "/change-password",
            data={
                "username": "testuser",
                "current_password": "password123",
                "new_password": "NewPassword123",
                "confirm_password": "NewPassword123"
            }
        )
        
        assert response.status_code == 302  # Redirect after success
        
        # Verify password was changed in database using bcrypt verification
        from security_config import PasswordSecurity
        user = test_db.query(User_IAM).filter(User_IAM.username == "testuser").first()
        # Verify the new password works with bcrypt
        assert PasswordSecurity.verify_password("NewPassword123", user.password, user.salt)
    
    def test_change_password_validation(self, test_client, test_db, sample_user_iam):
        """Test password change validation rules"""
        # Test password mismatch
        response = test_client.post(
            "/change-password",
            data={
                "username": "testuser",
                "current_password": "password123",
                "new_password": "NewPassword123",
                "confirm_password": "DifferentPassword123"
            }
        )
        assert response.status_code == 200
        assert "Passwords do not match" in response.text
        
        # Test password too short
        response = test_client.post(
            "/change-password",
            data={
                "username": "testuser",
                "current_password": "password123",
                "new_password": "short",
                "confirm_password": "short"
            }
        )
        assert response.status_code == 200
        assert "at least 8 characters" in response.text
        
        # Test password missing number
        response = test_client.post(
            "/change-password",
            data={
                "username": "testuser",
                "current_password": "password123",
                "new_password": "NoNumbers",
                "confirm_password": "NoNumbers"
            }
        )
        assert response.status_code == 200
        assert "at least one number" in response.text
        
        # Test password missing uppercase
        response = test_client.post(
            "/change-password",
            data={
                "username": "testuser",
                "current_password": "password123",
                "new_password": "nouppercase123",
                "confirm_password": "nouppercase123"
            }
        )
        assert response.status_code == 200
        assert "at least one uppercase" in response.text
    
    def test_change_password_wrong_current(self, test_client, test_db, sample_user_iam):
        """Test password change with wrong current password"""
        response = test_client.post(
            "/change-password",
            data={
                "username": "testuser",
                "current_password": "wrongpassword",
                "new_password": "NewPassword123",
                "confirm_password": "NewPassword123"
            }
        )
        
        assert response.status_code == 200
        assert "Current password is incorrect" in response.text
    
    def test_forgot_password_page(self, test_client):
        """Test forgot password page"""
        response = test_client.get("/forgot-password")
        assert response.status_code == 200
        assert "forgot" in response.text.lower()
        assert "password" in response.text.lower()
    
    def test_forgot_password_submission(self, test_client, test_db, sample_user_iam):
        """Test forgot password form submission"""
        response = test_client.post(
            "/forgot-password",
            data={"email": "test@example.com"}
        )
        
        assert response.status_code == 200
        assert "password reset link has been sent" in response.text
    
    def test_forgot_password_nonexistent_email(self, test_client, test_db):
        """Test forgot password with non-existent email"""
        response = test_client.post(
            "/forgot-password",
            data={"email": "nonexistent@example.com"}
        )
        
        # Should still show success message for security
        assert response.status_code == 200
        assert "password reset link has been sent" in response.text
    
    def test_reset_password_page(self, test_client):
        """Test reset password page"""
        response = test_client.get("/reset-password?token=test_token")
        assert response.status_code == 200
        assert "reset" in response.text.lower()
        assert "password" in response.text.lower()


class TestUserCreation:
    """Test user creation functionality"""
    
    def test_create_user_page(self, test_client):
        """Test create user page accessibility"""
        response = test_client.get("/create-user")
        assert response.status_code == 200
        assert "create" in response.text.lower()
        assert "user" in response.text.lower()
    
    def test_create_user_success(self, test_client, test_db):
        """Test successful user creation"""
        response = test_client.post(
            "/create-user",
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password": "Password123",
                "confirm_password": "Password123"
            }
        )
        
        assert response.status_code == 200
        assert "User created successfully" in response.text
        
        # Verify user was created in database
        user = test_db.query(User_IAM).filter(User_IAM.username == "newuser").first()
        assert user is not None
        assert user.email == "new@example.com"
        assert user.admin_role is False
    
    def test_create_user_validation(self, test_client, test_db):
        """Test user creation validation"""
        # Test invalid username format
        response = test_client.post(
            "/create-user",
            data={
                "username": "in@valid",
                "email": "test@example.com",
                "password": "Password123",
                "confirm_password": "Password123"
            }
        )
        assert response.status_code == 200
        assert "Invalid username format" in response.text
        
        # Test password mismatch
        response = test_client.post(
            "/create-user",
            data={
                "username": "validuser",
                "email": "test@example.com",
                "password": "Password123",
                "confirm_password": "Different123"
            }
        )
        assert response.status_code == 200
        assert "Passwords do not match" in response.text
    
    def test_create_user_duplicate(self, test_client, test_db, sample_user_iam):
        """Test creating user with duplicate username/email"""
        response = test_client.post(
            "/create-user",
            data={
                "username": "testuser",  # Already exists
                "email": "different@example.com",
                "password": "Password123",
                "confirm_password": "Password123"
            }
        )
        
        assert response.status_code == 200
        assert "already exists" in response.text


class TestAccessControl:
    """Test access control and authorization"""
    
    def test_admin_page_requires_auth(self, test_client):
        """Test that admin page requires authentication"""
        response = test_client.get("/admin", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["location"]
    
    def test_admin_page_requires_admin_role(self, test_client, authenticated_user_cookie):
        """Test that admin page requires admin role"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/admin", cookies=cookies, follow_redirects=False)
        
        assert response.status_code == 302
        assert "/dashboard" in response.headers["location"]
    
    def test_admin_page_accessible_to_admin(self, test_client, authenticated_admin_cookie):
        """Test that admin page is accessible to admin users"""
        cookies = {"session-token": authenticated_admin_cookie}
        response = test_client.get("/admin", cookies=cookies)
        
        assert response.status_code == 200
        assert "admin" in response.text.lower()
    
    def test_account_page_requires_auth(self, test_client):
        """Test that account page requires authentication"""
        response = test_client.get("/account", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["location"]
    
    def test_entries_page_requires_auth(self, test_client):
        """Test that entries page requires authentication"""
        response = test_client.get("/entries", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["location"]


class TestSessionSecurity:
    """Test session security features"""
    
    def test_session_cookie_security(self, test_client, test_db, sample_user_iam):
        """Test session cookie security attributes"""
        response = test_client.post(
            "/login",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=False
        )
        
        # Check cookie attributes
        cookie_header = response.headers.get("set-cookie", "")
        assert "httponly" in cookie_header.lower()
        assert "session-token" in cookie_header
    
    def test_session_token_uniqueness(self, test_db):
        """Test that session tokens are unique and random"""
        tokens = set()
        
        for i in range(10):
            token = secrets.token_urlsafe(32)
            assert token not in tokens
            tokens.add(token)
            assert len(token) > 20  # Reasonable length
    
    def test_password_hashing(self):
        """Test bcrypt password hashing functionality"""
        from security_config import PasswordSecurity
        
        password = "testpassword123"
        hash1, salt1 = PasswordSecurity.hash_password(password)
        hash2, salt2 = PasswordSecurity.hash_password(password)
        
        # Same password should produce different hashes due to salt
        assert hash1 != hash2
        assert salt1 != salt2
        
        # But both should verify correctly
        assert PasswordSecurity.verify_password(password, hash1, salt1)
        assert PasswordSecurity.verify_password(password, hash2, salt2)
        
        # Different passwords should not verify
        assert not PasswordSecurity.verify_password("wrongpassword", hash1, salt1)
    
    def test_session_base64_encoding(self):
        """Test session data base64 encoding/decoding with new format"""
        from datetime import datetime
        
        username = "testuser"
        session_token = "test_token_123"
        timestamp = datetime.utcnow().isoformat()
        
        # Encode using new format
        session_data = f"{username}|{session_token}|{timestamp}"
        encoded = base64.b64encode(session_data.encode()).decode()
        
        # Decode
        decoded = base64.b64decode(encoded).decode()
        parts = decoded.split('|')
        
        assert len(parts) == 3
        assert parts[0] == username
        assert parts[1] == session_token
        assert parts[2] == timestamp
