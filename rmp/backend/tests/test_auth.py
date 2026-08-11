import pytest
from unittest.mock import Mock, patch
from auth import SECRET_KEY


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
        import jwt

        test_data = {"sub": "test@example.com"}
        token = create_access_token(test_data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode using the same key the module loaded with
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
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
        invalid_data = {"email": "invalid-email", "password": "testpassword123"}

        response = client.post("/auth/register", json=invalid_data)
        assert response.status_code == 422  # Validation error

    def test_login_success(self, client, test_user_data):
        """Test successful login"""
        # Register user first
        client.post("/auth/register", json=test_user_data)

        # Login
        response = client.post(
            "/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client, test_user_data):
        """Test login with invalid credentials"""
        # Register user first
        client.post("/auth/register", json=test_user_data)

        # Try login with wrong password
        response = client.post(
            "/auth/login",
            json={"email": test_user_data["email"], "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            "/auth/login",
            json={"email": "nonexistent@example.com", "password": "somepassword"},
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    @patch("auth.log_authentication_event")
    def test_login_audit_logging(self, mock_audit, client, test_user_data):
        """Test that authentication events are logged"""
        # Register user first
        client.post("/auth/register", json=test_user_data)

        # Login
        client.post(
            "/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )

        # Verify audit logging was called
        mock_audit.assert_called()


# ---------------------------------------------------------------------------
# Module-level token helpers (used by new test classes below)
# ---------------------------------------------------------------------------

from datetime import timedelta
from auth import create_access_token  # SECRET_KEY already imported at top


def _make_reset_token(email: str, **kwargs) -> str:
    data = {"sub": email, "type": "password_reset"}
    data.update(kwargs)
    return create_access_token(data, expires_delta=timedelta(hours=1))


def _make_expired_reset_token(email: str) -> str:
    return create_access_token(
        {"sub": email, "type": "password_reset"},
        expires_delta=timedelta(seconds=-1),
    )


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client, email: str, password: str) -> str:
    """Register a user and return a valid access token."""
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# T-01 through T-06: GET /auth/me
# ---------------------------------------------------------------------------


class TestGetMe:
    """Tests for GET /auth/me (T-01 to T-06)"""

    def test_get_me_success(self, client, test_user_data):
        """T-01: Valid token returns user profile"""
        token = _register_and_login(
            client, test_user_data["email"], test_user_data["password"]
        )
        response = client.get("/auth/me", headers=_auth_header(token))

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert "hashed_password" not in data

    def test_get_me_no_token(self, client, test_user_data):
        """T-02: No Authorization header returns 401 or 403"""
        client.post("/auth/register", json=test_user_data)
        response = client.get("/auth/me")

        assert response.status_code in (401, 403)

    def test_get_me_expired_token(self, client, test_user_data):
        """T-03: Expired token returns 401"""
        client.post("/auth/register", json=test_user_data)
        expired_token = create_access_token(
            {"sub": test_user_data["email"]},
            expires_delta=timedelta(seconds=-1),
        )
        response = client.get("/auth/me", headers=_auth_header(expired_token))

        assert response.status_code == 401

    def test_get_me_tampered_token(self, client, test_user_data):
        """T-04: Token with payload modified but original signature returns 401"""
        import jwt

        client.post("/auth/register", json=test_user_data)
        token = _register_and_login(
            client, test_user_data["email"], test_user_data["password"]
        )
        # Re-encode with a different key to simulate tampering
        tampered = jwt.encode(
            {"sub": "attacker@evil.com"},
            "wrong-secret",
            algorithm="HS256",
        )
        response = client.get("/auth/me", headers=_auth_header(tampered))

        assert response.status_code == 401

    def test_get_me_malformed_token(self, client):
        """T-05: Malformed token string returns 401 or 403"""
        response = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})

        assert response.status_code in (401, 403)

    def test_get_me_reset_token_rejected(self, client, test_user_data):
        """T-06: Reset tokens cannot be used as API bearer tokens."""
        client.post("/auth/register", json=test_user_data)
        reset_token = _make_reset_token(test_user_data["email"])
        response = client.get("/auth/me", headers=_auth_header(reset_token))

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# T-07 through T-10: POST /auth/forgot-password
# ---------------------------------------------------------------------------


class TestForgotPassword:
    """Tests for POST /auth/forgot-password (T-07 to T-10)"""

    def test_forgot_password_registered_email(self, client, test_user_data):
        """T-07: Registered email returns 200 with generic message"""
        client.post("/auth/register", json=test_user_data)
        response = client.post(
            "/auth/forgot-password", json={"email": test_user_data["email"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"]  # non-empty

    def test_forgot_password_unregistered_email(self, client):
        """T-08: Unregistered email returns same generic 200 — no email leakage"""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "noone@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "If an account with that email exists" in data["message"]

    def test_forgot_password_invalid_email_format(self, client):
        """T-09: Invalid email format returns 422"""
        response = client.post("/auth/forgot-password", json={"email": "not-an-email"})

        assert response.status_code == 422

    def test_forgot_password_missing_body(self, client):
        """T-10: Missing body returns 422"""
        response = client.post("/auth/forgot-password", json={})

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# T-11 through T-18: POST /auth/reset-password
# ---------------------------------------------------------------------------


class TestResetPassword:
    """Tests for POST /auth/reset-password (T-11 to T-18)"""

    def test_reset_password_success(self, client, test_user_data):
        """T-11: Valid reset token returns 200"""
        client.post("/auth/register", json=test_user_data)
        reset_token = _make_reset_token(test_user_data["email"])
        response = client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": "NewPass456!"},
        )

        assert response.status_code == 200
        assert response.json().get("message") == "Password reset successfully"

    def test_reset_password_allows_login_with_new_password(
        self, client, test_user_data
    ):
        """T-12: Login works after reset with new password"""
        client.post("/auth/register", json=test_user_data)
        reset_token = _make_reset_token(test_user_data["email"])
        client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": "NewPass456!"},
        )

        login_resp = client.post(
            "/auth/login",
            json={"email": test_user_data["email"], "password": "NewPass456!"},
        )

        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()

    def test_reset_password_old_password_rejected(self, client, test_user_data):
        """T-13: Old password is rejected after reset"""
        client.post("/auth/register", json=test_user_data)
        reset_token = _make_reset_token(test_user_data["email"])
        client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": "NewPass456!"},
        )

        login_resp = client.post(
            "/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )

        assert login_resp.status_code == 401

    def test_reset_password_expired_token(self, client, test_user_data):
        """T-14: Expired reset token returns 400"""
        client.post("/auth/register", json=test_user_data)
        expired_token = _make_expired_reset_token(test_user_data["email"])
        response = client.post(
            "/auth/reset-password",
            json={"token": expired_token, "new_password": "NewPass456!"},
        )

        assert response.status_code == 400
        assert (
            "expired" in response.json()["detail"].lower()
            or "invalid" in response.json()["detail"].lower()
        )

    def test_reset_password_wrong_type(self, client, test_user_data):
        """T-15: Regular access token is rejected as a reset token."""
        client.post("/auth/register", json=test_user_data)
        access_token = create_access_token(
            {"sub": test_user_data["email"]},
            expires_delta=timedelta(hours=1),
        )
        response = client.post(
            "/auth/reset-password",
            json={"token": access_token, "new_password": "NewPass456!"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid reset token"

    def test_reset_password_invalid_token_string(self, client):
        """T-16: Garbage token string returns 400"""
        response = client.post(
            "/auth/reset-password",
            json={"token": "garbage", "new_password": "NewPass456!"},
        )

        assert response.status_code == 400

    def test_reset_password_unknown_email(self, client):
        """T-17: A reset token for an unknown user is rejected cleanly."""
        reset_token = _make_reset_token("unknown@example.com")
        response = client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": "NewPass456!"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "User not found"

    def test_reset_password_missing_fields(self, client):
        """T-18: Empty body returns 422"""
        response = client.post("/auth/reset-password", json={})

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# T-19 through T-23: POST /auth/register (extended)
# ---------------------------------------------------------------------------


class TestRegisterExtended:
    """Additional POST /auth/register edge cases (T-19 to T-23)"""

    def test_register_missing_password(self, client):
        """T-19: Body with only email returns 422"""
        response = client.post("/auth/register", json={"email": "a@b.com"})

        assert response.status_code == 422

    def test_register_missing_email(self, client):
        """T-20: Body with only password returns 422"""
        response = client.post("/auth/register", json={"password": "pw"})

        assert response.status_code == 422

    def test_register_empty_body(self, client):
        """T-21: Empty body returns 422"""
        response = client.post("/auth/register", json={})

        assert response.status_code == 422

    def test_register_role_field_rejected(self, client):
        """T-22: Registration rejects a client-controlled role."""
        response = client.post(
            "/auth/register",
            json={
                "email": "admin@example.com",
                "password": "Pass1234!",
                "role": "POOL_ADMIN",
            },
        )

        assert response.status_code == 422

    def test_register_response_has_no_hashed_password(self, client, test_user_data):
        """T-23: Registration response must not expose hashed_password"""
        response = client.post("/auth/register", json=test_user_data)

        assert response.status_code == 200
        assert "hashed_password" not in response.json()


# ---------------------------------------------------------------------------
# T-24 through T-28: POST /auth/login (extended)
# ---------------------------------------------------------------------------


class TestLoginExtended:
    """Additional POST /auth/login edge cases (T-24 to T-28)"""

    def test_login_missing_password(self, client):
        """T-24: Body with only email returns 422"""
        response = client.post("/auth/login", json={"email": "a@b.com"})

        assert response.status_code == 422

    def test_login_missing_email(self, client):
        """T-25: Body with only password returns 422"""
        response = client.post("/auth/login", json={"password": "pw"})

        assert response.status_code == 422

    def test_login_empty_body(self, client):
        """T-26: Empty body returns 422"""
        response = client.post("/auth/login", json={})

        assert response.status_code == 422

    def test_login_token_is_decodable(self, client, test_user_data):
        """T-27: Returned JWT is decodable; sub == email; exp present; HS256"""
        import jwt

        client.post("/auth/register", json=test_user_data)
        response = client.post(
            "/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )

        assert response.status_code == 200
        token = response.json()["access_token"]
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        assert decoded["sub"] == test_user_data["email"]
        assert "exp" in decoded

    @patch("auth.log_authentication_event")
    def test_login_failed_audit_logging(self, mock_audit, client, test_user_data):
        """T-28: Failed login triggers audit log event"""
        client.post("/auth/register", json=test_user_data)
        client.post(
            "/auth/login",
            json={"email": test_user_data["email"], "password": "wrongpassword"},
        )

        mock_audit.assert_called()


# ---------------------------------------------------------------------------
# G-01 through G-06: Known behavior gap documentation
# ---------------------------------------------------------------------------


class TestKnownBehaviorGaps:
    """Tests documenting known gaps and bugs (G-01 to G-06)"""

    def test_inactive_user_login_is_blocked(self, client, db_session, test_user_data):
        """G-01: Inactive users are blocked at login."""
        from models import User

        client.post("/auth/register", json=test_user_data)

        # Deactivate user directly via DB
        user = (
            db_session.query(User).filter(User.email == test_user_data["email"]).first()
        )
        user.is_active = False
        db_session.commit()
        db_session.expire_all()

        response = client.post(
            "/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )

        assert response.status_code == 401

    def test_inactive_user_me_is_blocked(self, client, db_session, test_user_data):
        """G-02: Existing tokens stop working when a user is deactivated."""
        from models import User

        token = _register_and_login(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Deactivate user directly via DB
        user = (
            db_session.query(User).filter(User.email == test_user_data["email"]).first()
        )
        user.is_active = False
        db_session.commit()
        db_session.expire_all()

        response = client.get("/auth/me", headers=_auth_header(token))

        assert response.status_code == 401

    def test_deleted_user_token_rejected(self, client, db_session, test_user_data):
        """G-03: Deleted user's valid token returns 401 — asserts correct behavior stays correct"""
        from models import User

        token = _register_and_login(
            client, test_user_data["email"], test_user_data["password"]
        )

        # Delete user directly via DB
        user = (
            db_session.query(User).filter(User.email == test_user_data["email"]).first()
        )
        db_session.delete(user)
        db_session.commit()

        response = client.get("/auth/me", headers=_auth_header(token))

        assert response.status_code == 401
        assert "unavailable" in response.json()["detail"].lower()

    def test_reset_password_rejects_too_short_password(
        self, client, test_user_data
    ):
        """G-04: Password reset enforces the account password policy."""
        client.post("/auth/register", json=test_user_data)
        reset_token = _make_reset_token(test_user_data["email"])
        response = client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": "a"},
        )

        assert response.status_code == 422

    @patch("auth.log_create_operation")
    def test_register_audit_event_fired(self, mock_create, client, test_user_data):
        """G-05: Registration triggers a create audit log event"""
        client.post("/auth/register", json=test_user_data)

        mock_create.assert_called()

    @patch("auth.log_update_operation")
    def test_reset_password_audit_event_fired(
        self, mock_update, client, test_user_data
    ):
        """G-06: Successful password reset triggers an update audit log event"""
        client.post("/auth/register", json=test_user_data)
        reset_token = _make_reset_token(test_user_data["email"])
        client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": "NewPass456!"},
        )

        mock_update.assert_called()
