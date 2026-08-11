"""Executable OWASP Top 10 security assessment for the RunMyPool API.

Passing tests verify controls that exist today.  ``xfail`` tests are security
requirements for confirmed gaps; they remain visible in every test report and
will XPASS as soon as the associated control is implemented.
"""

import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import models
from auth import create_access_token


pytestmark = [pytest.mark.security, pytest.mark.owasp]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _register(client, email, password="Pass1234!"):
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _pool(client, token, name):
    response = client.post(
        "/pools/create",
        json={"name": name, "description": "OWASP test", "is_private": False},
        headers=_headers(token),
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _entry(client, token, pool_id, name="OWASP entry"):
    response = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": name},
        headers=_headers(token),
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


class TestA01BrokenAccessControl:
    def test_outsider_cannot_read_private_pool_details(self, client):
        owner = _register(client, "a01.owner@example.com")
        outsider = _register(client, "a01.outsider@example.com")
        pool_id = _pool(client, owner, "A01 private details")

        response = client.get(f"/pools/{pool_id}", headers=_headers(outsider))

        assert response.status_code == 403

    def test_message_body_cannot_redirect_post_to_another_pool(self, client):
        token = _register(client, "a01.message@example.com")
        allowed_pool = _pool(client, token, "A01 allowed message pool")
        other_pool = _pool(client, token, "A01 target message pool")
        _entry(client, token, allowed_pool)

        response = client.post(
            f"/messages/pool/{allowed_pool}",
            json={"pool_id": other_pool, "message": "boundary probe"},
            headers=_headers(token),
        )

        assert response.status_code == 200
        assert response.json()["pool_id"] == allowed_pool

    def test_player_cannot_set_pick_result_or_lock_state(self, client):
        token = _register(client, "a01.pick-integrity@example.com")
        pool_id = _pool(client, token, "A01 pick integrity")
        entry_id = _entry(client, token, pool_id)
        created = client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "NE"},
            headers=_headers(token),
        )
        assert created.status_code == 200, created.text

        response = client.put(
            f"/picks/{created.json()['id']}",
            json={"result": "WIN", "locked": True},
            headers=_headers(token),
        )

        assert response.status_code in (400, 403, 422)


class TestA02CryptographicFailures:
    def test_password_is_hashed_and_never_serialized(self, client, db_session):
        password = "NeverStoreThis123!"
        response = client.post(
            "/auth/register",
            json={"email": "a02.hash@example.com", "password": password},
        )
        assert response.status_code == 200
        user = db_session.query(models.User).filter_by(email="a02.hash@example.com").one()
        assert user.hashed_password != password
        assert password not in response.text
        assert "hashed_password" not in response.json()

    def test_no_hard_coded_jwt_secret_fallback(self):
        backend = Path(__file__).resolve().parents[1]
        assert "supersecretkey" not in (backend / "auth.py").read_text()
        assert "supersecretkey" not in (backend / "deps.py").read_text()


class TestA03Injection:
    def test_sql_injection_is_treated_as_data(self, client):
        token = _register(client, "a03.sql@example.com")
        payload = "'; DROP TABLE users; --"
        pool_id = _pool(client, token, payload)

        response = client.get(f"/pools/{pool_id}", headers=_headers(token))

        assert response.status_code == 200
        assert response.json()["name"] == payload
        assert client.get("/pools/").status_code == 200

    def test_xss_payload_is_returned_only_as_json_data(self, client):
        token = _register(client, "a03.xss@example.com")
        payload = '<img src=x onerror="alert(1)">'
        pool_id = _pool(client, token, payload)

        response = client.get(f"/pools/{pool_id}", headers=_headers(token))

        assert response.headers["content-type"].startswith("application/json")
        assert response.json()["name"] == payload


class TestA04InsecureDesign:
    def test_trivial_password_is_rejected(self, client):
        response = client.post(
            "/auth/register", json={"email": "a04.weak@example.com", "password": "x"}
        )
        assert response.status_code == 422

    def test_password_reset_token_is_single_use(self, client):
        email = "a04.reset@example.com"
        _register(client, email)
        token = create_access_token(
            {"sub": email, "type": "password_reset"}, expires_delta=timedelta(hours=1)
        )
        payload = {"token": token, "new_password": "Replacement123!"}
        assert client.post("/auth/reset-password", json=payload).status_code == 200

        replay = client.post("/auth/reset-password", json=payload)

        assert replay.status_code in (400, 401)


class TestA05SecurityMisconfiguration:
    def test_untrusted_origin_is_not_allowed_by_cors(self, client):
        response = client.options(
            "/auth/me",
            headers={
                "Origin": "https://attacker.invalid",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") != "https://attacker.invalid"

    def test_browser_security_headers_are_present(self, client):
        response = client.get("/")
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "content-security-policy" in response.headers
        assert "referrer-policy" in response.headers
        assert response.headers.get("x-frame-options") in ("DENY", "SAMEORIGIN")

    def test_api_documentation_is_not_public(self, client):
        assert client.get("/docs").status_code in (401, 403, 404)


class TestA06VulnerableAndOutdatedComponents:
    @pytest.mark.xfail(reason="Python requirements and frontend dependencies are not pinned")
    def test_direct_dependencies_are_exactly_pinned(self):
        root = Path(__file__).resolve().parents[2]
        requirements = (root / "backend" / "requirements.txt").read_text().splitlines()
        package = (root / "frontend" / "package.json").read_text()
        active = [line.strip() for line in requirements if line.strip() and not line.startswith("#")]
        assert all("==" in line for line in active)
        assert '"latest"' not in package
        assert '"^' not in package


class TestA07IdentificationAndAuthenticationFailures:
    def test_inactive_user_token_is_rejected(self, client, db_session):
        email = "a07.inactive@example.com"
        token = _register(client, email)
        user = db_session.query(models.User).filter_by(email=email).one()
        user.is_active = False
        db_session.commit()

        assert client.get("/auth/me", headers=_headers(token)).status_code in (401, 403)

    def test_repeated_failed_logins_are_rate_limited(self, client):
        email = "a07.bruteforce@example.com"
        _register(client, email)
        responses = [
            client.post("/auth/login", json={"email": email, "password": "wrong"})
            for _ in range(10)
        ]
        assert any(response.status_code == 429 for response in responses)


class TestA08SoftwareAndDataIntegrityFailures:
    def test_unsigned_jwt_is_rejected(self, client):
        encode = lambda value: base64.urlsafe_b64encode(
            json.dumps(value, separators=(",", ":")).encode()
        ).decode().rstrip("=")
        token = ".".join(
            (
                encode({"alg": "none", "typ": "JWT"}),
                encode({"sub": "a08@example.com", "exp": 4102444800}),
                "",
            )
        )
        assert client.get("/auth/me", headers=_headers(token)).status_code == 401


class TestA09SecurityLoggingAndMonitoringFailures:
    def test_failed_login_is_audited(self, client, db_session):
        client.post(
            "/auth/login", json={"email": "a09.unknown@example.com", "password": "wrong"}
        )
        event = (
            db_session.query(models.AuditLog)
            .filter(models.AuditLog.action == "LOGIN_FAILED")
            .order_by(models.AuditLog.created_at.desc())
            .first()
        )
        assert event is not None

    def test_password_reset_token_is_not_logged(self, client, capsys):
        email = "a09.reset-log@example.com"
        _register(client, email)
        capsys.readouterr()

        client.post("/auth/forgot-password", json={"email": email})
        output = capsys.readouterr().out

        assert "password reset token" not in output.lower()
        assert "reset-password?token=" not in output.lower()


class TestA10ServerSideRequestForgery:
    def test_upstream_urls_are_fixed_https_endpoints(self):
        import odds_service
        import sync_schedule

        assert odds_service.ESPN_SUMMARY_URL.startswith("https://")
        assert sync_schedule.ESPN_SCOREBOARD_URL.startswith("https://")
        assert "{" not in odds_service.ESPN_SUMMARY_URL
        assert "{" not in sync_schedule.ESPN_SCOREBOARD_URL
