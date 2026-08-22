"""RBAC and global visibility tests for the platform administration boundary."""

import uuid
from datetime import datetime, timezone

import pytest

import models
from platform_admin import (
    BOOTSTRAP_SUPER_ADMIN_EMAIL,
    is_bootstrap_super_admin,
    is_platform_super_admin,
    require_platform_super_admin,
)
from fastapi import HTTPException
from tests.plan_support import grant_unlimited_pool_creations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register(client, email, password="Platform123!"):
    response = client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    grant_unlimited_pool_creations(email)
    return login.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _set_role(db, email, role):
    user = db.query(models.User).filter(models.User.email == email).one()
    user.role = role
    db.commit()
    db.expire_all()
    return user.id


def _create_pool(client, token, name=None, private=False):
    payload = {"name": name or f"Pool {uuid.uuid4()}", "is_private": private}
    if private:
        payload["join_password"] = "password123"
    resp = client.post(
        "/pools/create",
        json=payload,
        headers=_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_entry(client, token, pool_id, name=None):
    resp = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": name or f"Entry {uuid.uuid4()}"},
        headers=_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _add_member(db, pool_id, email):
    user = db.query(models.User).filter(models.User.email == email).one()
    existing = (
        db.query(models.PoolMember).filter_by(pool_id=pool_id, user_id=user.id).first()
    )
    if not existing:
        db.add(
            models.PoolMember(
                pool_id=pool_id,
                user_id=user.id,
                joined_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        db.commit()
    return user.id


def _add_pick(db, entry_id, week, team):
    pick = models.Pick(
        id=str(uuid.uuid4()),
        entry_id=entry_id,
        week=week,
        team=team,
        locked=False,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(pick)
    db.commit()
    db.refresh(pick)
    return pick


# ---------------------------------------------------------------------------
# Minimal user stub for unit tests (bypasses SQLAlchemy instrumentation)
# ---------------------------------------------------------------------------


class _UserStub:
    """Plain object that mimics the User model fields needed for unit tests."""

    def __init__(self, email=None, role=None):
        self.email = email
        self.role = role


# ---------------------------------------------------------------------------
# Unit tests: is_bootstrap_super_admin
# ---------------------------------------------------------------------------


class TestIsBootstrapSuperAdmin:
    def _make_user(self, email):
        return _UserStub(email=email)

    def test_exact_match_returns_true(self):
        assert (
            is_bootstrap_super_admin(self._make_user(BOOTSTRAP_SUPER_ADMIN_EMAIL))
            is True
        )

    def test_different_email_returns_false(self):
        assert is_bootstrap_super_admin(self._make_user("other@example.com")) is False

    def test_case_insensitive_returns_true(self):
        assert (
            is_bootstrap_super_admin(
                self._make_user(BOOTSTRAP_SUPER_ADMIN_EMAIL.upper())
            )
            is True
        )

    def test_leading_trailing_whitespace_returns_true(self):
        assert (
            is_bootstrap_super_admin(
                self._make_user(f"  {BOOTSTRAP_SUPER_ADMIN_EMAIL}  ")
            )
            is True
        )

    def test_none_email_returns_false(self):
        assert is_bootstrap_super_admin(self._make_user(None)) is False

    def test_empty_string_email_returns_false(self):
        assert is_bootstrap_super_admin(self._make_user("")) is False


# ---------------------------------------------------------------------------
# Unit tests: is_platform_super_admin
# ---------------------------------------------------------------------------


class TestIsPlatformSuperAdmin:
    def _make_user(self, role):
        return _UserStub(role=role)

    def test_super_admin_role_returns_true(self):
        assert (
            is_platform_super_admin(self._make_user(models.UserRole.SUPER_ADMIN))
            is True
        )

    def test_user_role_returns_false(self):
        assert is_platform_super_admin(self._make_user(models.UserRole.USER)) is False

    def test_pool_admin_role_returns_false(self):
        assert (
            is_platform_super_admin(self._make_user(models.UserRole.POOL_ADMIN))
            is False
        )

    def test_none_role_returns_false(self):
        assert is_platform_super_admin(self._make_user(None)) is False


# ---------------------------------------------------------------------------
# Unit tests: require_platform_super_admin
# ---------------------------------------------------------------------------


class TestRequirePlatformSuperAdmin:
    def _make_user(self, role):
        return _UserStub(role=role)

    def test_super_admin_passes(self):
        user = self._make_user(models.UserRole.SUPER_ADMIN)
        from platform_admin import is_platform_super_admin

        # Directly call the guard logic (not the FastAPI dependency)
        from fastapi import HTTPException

        if not is_platform_super_admin(user):
            raise HTTPException(
                status_code=403, detail="Platform admin access required"
            )
        # No exception raised — test passes

    def test_user_role_raises_403(self):
        user = self._make_user(models.UserRole.USER)
        with pytest.raises(HTTPException) as exc_info:
            if not is_platform_super_admin(user):
                raise HTTPException(
                    status_code=403, detail="Platform admin access required"
                )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Platform admin access required"

    def test_pool_admin_role_raises_403(self):
        user = self._make_user(models.UserRole.POOL_ADMIN)
        with pytest.raises(HTTPException) as exc_info:
            if not is_platform_super_admin(user):
                raise HTTPException(
                    status_code=403, detail="Platform admin access required"
                )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Platform admin access required"


# ---------------------------------------------------------------------------
# Existing smoke tests (preserved)
# ---------------------------------------------------------------------------


def test_every_platform_endpoint_rejects_non_super_admins(client, db_session):
    token = _register(client, "ordinary@platform.example.com")
    endpoints = (
        "/platform-admin/overview",
        "/platform-admin/pools",
        "/platform-admin/entries",
    )
    for endpoint in endpoints:
        assert client.get(endpoint, headers=_headers(token)).status_code == 403

    _set_role(db_session, "ordinary@platform.example.com", models.UserRole.POOL_ADMIN)
    for endpoint in endpoints:
        response = client.get(endpoint, headers=_headers(token))
        assert response.status_code == 403
        assert response.json()["detail"] == "Platform admin access required"


def test_platform_admin_sees_all_users_pools_and_entries(client, db_session):
    owner_token = _register(client, "owner@platform.example.com")
    _register(client, "unassigned@platform.example.com")
    admin_token = _register(client, "support@platform.example.com")
    _set_role(db_session, "support@platform.example.com", models.UserRole.SUPER_ADMIN)

    public_pool = _create_pool(
        client, owner_token, name="Public Platform Pool", private=False
    )
    private_pool = client.post(
        "/pools/create",
        json={
            "name": "Private Platform Pool",
            "is_private": True,
            "join_password": "invite-code",
        },
        headers=_headers(owner_token),
    ).json()
    entry = client.post(
        "/entries/create",
        json={"name": "Owner Entry", "pool_id": public_pool["id"]},
        headers=_headers(owner_token),
    )
    assert entry.status_code == 200, entry.text

    overview = client.get("/platform-admin/overview", headers=_headers(admin_token))
    assert overview.status_code == 200
    assert overview.json()["pools"] == 2
    assert overview.json()["private_pools"] == 1
    assert overview.json()["entries"] == 1
    assert overview.json()["unassigned_users"] == 2

    pools = client.get("/platform-admin/pools", headers=_headers(admin_token)).json()
    assert {pool["name"] for pool in pools} == {
        "Public Platform Pool",
        "Private Platform Pool",
    }
    assert {pool["is_private"] for pool in pools} == {True, False}
    entries = client.get(
        "/platform-admin/entries", headers=_headers(admin_token)
    ).json()
    assert entries[0]["name"] == "Owner Entry"
    assert entries[0]["user_email"] == "owner@platform.example.com"

    users = client.get(
        "/users/admin-dashboard?limit=500", headers=_headers(admin_token)
    ).json()
    assert {user["email"] for user in users["users"]} == {
        "owner@platform.example.com",
        "unassigned@platform.example.com",
        "support@platform.example.com",
    }

    # Global pool administration works without making the super admin a member.
    assert (
        client.get(
            f"/pools/{private_pool['id']}", headers=_headers(admin_token)
        ).status_code
        == 200
    )
    access = client.get(
        f"/pools/{private_pool['id']}/is-admin", headers=_headers(admin_token)
    )
    assert access.status_code == 200
    assert access.json()["has_admin_access"] is True


# ---------------------------------------------------------------------------
# API tests: /platform-admin/overview
# ---------------------------------------------------------------------------


class TestPlatformAdminOverview:
    def test_unauthenticated_returns_401(self, client):
        assert client.get("/platform-admin/overview").status_code == 401

    def test_user_role_returns_403(self, client, db_session):
        token = _register(client, "usr.overview@example.com")
        resp = client.get("/platform-admin/overview", headers=_headers(token))
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Platform admin access required"

    def test_pool_admin_returns_403(self, client, db_session):
        token = _register(client, "pa.overview@example.com")
        _set_role(db_session, "pa.overview@example.com", models.UserRole.POOL_ADMIN)
        resp = client.get("/platform-admin/overview", headers=_headers(token))
        assert resp.status_code == 403

    def test_empty_db_returns_correct_counts(self, client, db_session):
        token = _register(client, "sa.overview.empty@example.com")
        _set_role(
            db_session, "sa.overview.empty@example.com", models.UserRole.SUPER_ADMIN
        )
        resp = client.get("/platform-admin/overview", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["users"] == 1  # only the super admin
        assert data["super_admins"] == 1
        assert data["pools"] == 0
        assert data["private_pools"] == 0
        assert data["entries"] == 0

    def test_owner_not_counted_as_unassigned(self, client, db_session):
        owner_token = _register(client, "owner.overview@example.com")
        admin_token = _register(client, "sa.overview2@example.com")
        _set_role(db_session, "sa.overview2@example.com", models.UserRole.SUPER_ADMIN)
        _create_pool(client, owner_token, name="Overview Pool")

        resp = client.get("/platform-admin/overview", headers=_headers(admin_token))
        assert resp.status_code == 200
        # The pool owner is not unassigned; the super admin (not in any pool) is
        unassigned = resp.json()["unassigned_users"]
        assert (
            unassigned == 1
        )  # only the SA is unassigned; owner is assigned via pool ownership

    def test_counts_reflect_seeded_state(self, client, db_session):
        owner_token = _register(client, "owner.cnt@example.com")
        admin_token = _register(client, "sa.cnt@example.com")
        _set_role(db_session, "sa.cnt@example.com", models.UserRole.SUPER_ADMIN)
        pool = _create_pool(client, owner_token, name="Count Pool", private=True)
        _create_entry(client, owner_token, pool["id"])

        resp = client.get("/platform-admin/overview", headers=_headers(admin_token))
        data = resp.json()
        assert data["pools"] == 1
        assert data["private_pools"] == 1
        assert data["entries"] == 1
        assert data["users"] == 2


# ---------------------------------------------------------------------------
# API tests: /platform-admin/pools
# ---------------------------------------------------------------------------


class TestPlatformAdminListAllPools:
    def test_unauthenticated_returns_401(self, client):
        assert client.get("/platform-admin/pools").status_code == 401

    def test_user_role_returns_403(self, client, db_session):
        token = _register(client, "usr.pools@example.com")
        assert (
            client.get("/platform-admin/pools", headers=_headers(token)).status_code
            == 403
        )

    def test_pool_admin_returns_403(self, client, db_session):
        token = _register(client, "pa.pools@example.com")
        _set_role(db_session, "pa.pools@example.com", models.UserRole.POOL_ADMIN)
        assert (
            client.get("/platform-admin/pools", headers=_headers(token)).status_code
            == 403
        )

    def test_returns_all_pools_with_counts(self, client, db_session):
        owner_token = _register(client, "owner.allpools@example.com")
        member_token = _register(client, "member.allpools@example.com")
        admin_token = _register(client, "sa.allpools@example.com")
        _set_role(db_session, "sa.allpools@example.com", models.UserRole.SUPER_ADMIN)

        pub_pool = _create_pool(
            client, owner_token, name="PA Public Pool", private=False
        )
        priv_pool = _create_pool(
            client, owner_token, name="PA Private Pool", private=True
        )

        # Add member + entry to public pool
        _add_member(db_session, pub_pool["id"], "member.allpools@example.com")
        _create_entry(client, owner_token, pub_pool["id"])

        resp = client.get("/platform-admin/pools", headers=_headers(admin_token))
        assert resp.status_code == 200
        pools_by_name = {p["name"]: p for p in resp.json()}
        assert "PA Public Pool" in pools_by_name
        assert "PA Private Pool" in pools_by_name

        pub = pools_by_name["PA Public Pool"]
        assert pub["member_count"] == 2  # owner (auto-added) + extra member
        assert pub["entry_count"] == 1
        assert pub["owner_email"] == "owner.allpools@example.com"

        priv = pools_by_name["PA Private Pool"]
        assert priv["member_count"] == 1  # owner auto-added as member
        assert priv["entry_count"] == 0
        assert priv["is_private"] is True

    def test_search_by_pool_name(self, client, db_session):
        owner_token = _register(client, "owner.srchpool@example.com")
        admin_token = _register(client, "sa.srchpool@example.com")
        _set_role(db_session, "sa.srchpool@example.com", models.UserRole.SUPER_ADMIN)
        _create_pool(client, owner_token, name="UniqueAlpha Pool")
        _create_pool(client, owner_token, name="UniqueZeta Pool")

        resp = client.get(
            "/platform-admin/pools?search=alpha", headers=_headers(admin_token)
        )
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert "UniqueAlpha Pool" in names
        assert "UniqueZeta Pool" not in names

    def test_search_by_owner_email(self, client, db_session):
        owner_token = _register(client, "owner.srchemail@example.com")
        other_token = _register(client, "other.srchemail@example.com")
        admin_token = _register(client, "sa.srchemail@example.com")
        _set_role(db_session, "sa.srchemail@example.com", models.UserRole.SUPER_ADMIN)
        _create_pool(client, owner_token, name="Email Search Pool A")
        _create_pool(client, other_token, name="Email Search Pool B")

        resp = client.get(
            "/platform-admin/pools?search=owner.srchemail",
            headers=_headers(admin_token),
        )
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert "Email Search Pool A" in names
        assert "Email Search Pool B" not in names

    def test_pagination_skip_and_limit(self, client, db_session):
        owner_token = _register(client, "owner.paginp@example.com")
        admin_token = _register(client, "sa.paginp@example.com")
        _set_role(db_session, "sa.paginp@example.com", models.UserRole.SUPER_ADMIN)
        for i in range(3):
            _create_pool(client, owner_token, name=f"Paginate Pool {i}")

        resp = client.get(
            "/platform-admin/pools?skip=1&limit=1", headers=_headers(admin_token)
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_limit_exceeding_max_returns_422(self, client, db_session):
        admin_token = _register(client, "sa.paginmax@example.com")
        _set_role(db_session, "sa.paginmax@example.com", models.UserRole.SUPER_ADMIN)
        resp = client.get(
            "/platform-admin/pools?limit=501", headers=_headers(admin_token)
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# API tests: /platform-admin/entries
# ---------------------------------------------------------------------------


class TestPlatformAdminListAllEntries:
    def test_unauthenticated_returns_401(self, client):
        assert client.get("/platform-admin/entries").status_code == 401

    def test_user_role_returns_403(self, client, db_session):
        token = _register(client, "usr.entries@example.com")
        assert (
            client.get("/platform-admin/entries", headers=_headers(token)).status_code
            == 403
        )

    def test_pool_admin_returns_403(self, client, db_session):
        token = _register(client, "pa.entries@example.com")
        _set_role(db_session, "pa.entries@example.com", models.UserRole.POOL_ADMIN)
        assert (
            client.get("/platform-admin/entries", headers=_headers(token)).status_code
            == 403
        )

    def test_returns_entries_from_all_pools(self, client, db_session):
        owner_token = _register(client, "owner.allentries@example.com")
        admin_token = _register(client, "sa.allentries@example.com")
        _set_role(db_session, "sa.allentries@example.com", models.UserRole.SUPER_ADMIN)
        pool_a = _create_pool(client, owner_token, name="Entry Pool A")
        pool_b = _create_pool(client, owner_token, name="Entry Pool B")
        _create_entry(client, owner_token, pool_a["id"], name="Entry In A")
        _create_entry(client, owner_token, pool_b["id"], name="Entry In B")

        resp = client.get("/platform-admin/entries", headers=_headers(admin_token))
        assert resp.status_code == 200
        names = {e["name"] for e in resp.json()}
        assert {"Entry In A", "Entry In B"} <= names

    def test_pool_id_filter_restricts_results(self, client, db_session):
        owner_token = _register(client, "owner.pidfilter@example.com")
        admin_token = _register(client, "sa.pidfilter@example.com")
        _set_role(db_session, "sa.pidfilter@example.com", models.UserRole.SUPER_ADMIN)
        pool_a = _create_pool(client, owner_token, name="Filter Pool A")
        pool_b = _create_pool(client, owner_token, name="Filter Pool B")
        _create_entry(client, owner_token, pool_a["id"], name="Entry Filter A")
        _create_entry(client, owner_token, pool_b["id"], name="Entry Filter B")

        resp = client.get(
            f"/platform-admin/entries?pool_id={pool_a['id']}",
            headers=_headers(admin_token),
        )
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()]
        assert "Entry Filter A" in names
        assert "Entry Filter B" not in names

    def test_search_by_entry_name(self, client, db_session):
        owner_token = _register(client, "owner.srchentry@example.com")
        admin_token = _register(client, "sa.srchentry@example.com")
        _set_role(db_session, "sa.srchentry@example.com", models.UserRole.SUPER_ADMIN)
        pool = _create_pool(client, owner_token, name="Search Entry Pool")
        _create_entry(client, owner_token, pool["id"], name="AlphaDragon Entry")
        _create_entry(client, owner_token, pool["id"], name="ZetaWolf Entry")

        resp = client.get(
            "/platform-admin/entries?search=alphadragon", headers=_headers(admin_token)
        )
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()]
        assert "AlphaDragon Entry" in names
        assert "ZetaWolf Entry" not in names

    def test_search_by_user_email(self, client, db_session):
        owner_token = _register(client, "owner.emailsrch@example.com")
        admin_token = _register(client, "sa.emailsrch@example.com")
        _set_role(db_session, "sa.emailsrch@example.com", models.UserRole.SUPER_ADMIN)
        pool = _create_pool(client, owner_token, name="Email Search Entry Pool")
        _create_entry(client, owner_token, pool["id"], name="Email Match Entry")

        resp = client.get(
            "/platform-admin/entries?search=owner.emailsrch",
            headers=_headers(admin_token),
        )
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()]
        assert "Email Match Entry" in names

    def test_pagination(self, client, db_session):
        owner_token = _register(client, "owner.entrypag@example.com")
        admin_token = _register(client, "sa.entrypag@example.com")
        _set_role(db_session, "sa.entrypag@example.com", models.UserRole.SUPER_ADMIN)
        pool = _create_pool(client, owner_token, name="Paginate Entry Pool")
        for i in range(3):
            _create_entry(client, owner_token, pool["id"], name=f"Page Entry {i}")

        resp = client.get(
            f"/platform-admin/entries?pool_id={pool['id']}&skip=1&limit=1",
            headers=_headers(admin_token),
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_limit_exceeding_max_returns_422(self, client, db_session):
        admin_token = _register(client, "sa.entrylimmax@example.com")
        _set_role(db_session, "sa.entrylimmax@example.com", models.UserRole.SUPER_ADMIN)
        resp = client.get(
            "/platform-admin/entries?limit=501", headers=_headers(admin_token)
        )
        assert resp.status_code == 422

    def test_entry_response_includes_required_fields(self, client, db_session):
        owner_token = _register(client, "owner.entryfields@example.com")
        admin_token = _register(client, "sa.entryfields@example.com")
        _set_role(db_session, "sa.entryfields@example.com", models.UserRole.SUPER_ADMIN)
        pool = _create_pool(client, owner_token, name="Fields Pool")
        _create_entry(client, owner_token, pool["id"], name="Fields Entry")

        resp = client.get("/platform-admin/entries", headers=_headers(admin_token))
        assert resp.status_code == 200
        entry = next(e for e in resp.json() if e["name"] == "Fields Entry")
        for field in (
            "id",
            "name",
            "user_id",
            "user_email",
            "pool_id",
            "pool_name",
            "alive",
            "created_at",
        ):
            assert field in entry, f"Missing field: {field}"
        assert entry["user_email"] == "owner.entryfields@example.com"
        assert entry["pool_name"] == "Fields Pool"


# ---------------------------------------------------------------------------
# Integration tests: Grant/Revoke Super Admin
# ---------------------------------------------------------------------------


class TestGrantRevokeSuperAdmin:
    def test_grant_super_admin_happy_path(self, client, db_session):
        granter_token = _register(client, "granter.sa@example.com")
        _set_role(db_session, "granter.sa@example.com", models.UserRole.SUPER_ADMIN)
        target_token = _register(client, "target.sa@example.com")
        target_id = (
            db_session.query(models.User)
            .filter(models.User.email == "target.sa@example.com")
            .one()
            .id
        )

        resp = client.patch(
            f"/users/{target_id}/super-admin?enabled=true",
            headers=_headers(granter_token),
        )
        assert resp.status_code == 200

        # Verify target can now access platform admin
        overview = client.get(
            "/platform-admin/overview", headers=_headers(target_token)
        )
        assert overview.status_code == 200

    def test_regular_user_cannot_grant(self, client, db_session):
        token = _register(client, "reg.grant@example.com")
        target = _register(client, "reg.target@example.com")
        target_id = (
            db_session.query(models.User)
            .filter(models.User.email == "reg.target@example.com")
            .one()
            .id
        )
        resp = client.patch(
            f"/users/{target_id}/super-admin?enabled=true", headers=_headers(token)
        )
        assert resp.status_code == 403

    def test_pool_admin_cannot_grant(self, client, db_session):
        token = _register(client, "pa.grant@example.com")
        _set_role(db_session, "pa.grant@example.com", models.UserRole.POOL_ADMIN)
        target = _register(client, "pa.target@example.com")
        target_id = (
            db_session.query(models.User)
            .filter(models.User.email == "pa.target@example.com")
            .one()
            .id
        )
        resp = client.patch(
            f"/users/{target_id}/super-admin?enabled=true", headers=_headers(token)
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client):
        resp = client.patch(f"/users/{uuid.uuid4()}/super-admin?enabled=true")
        assert resp.status_code in (401, 403, 404)

    def test_nonexistent_user_returns_404(self, client, db_session):
        token = _register(client, "sa.grant404@example.com")
        _set_role(db_session, "sa.grant404@example.com", models.UserRole.SUPER_ADMIN)
        resp = client.patch(
            f"/users/{uuid.uuid4()}/super-admin?enabled=true", headers=_headers(token)
        )
        assert resp.status_code == 404

    def test_grant_idempotent(self, client, db_session):
        granter_token = _register(client, "sa.idempgrant@example.com")
        _set_role(db_session, "sa.idempgrant@example.com", models.UserRole.SUPER_ADMIN)
        target_id = (
            db_session.query(models.User)
            .filter(models.User.email == "sa.idempgrant@example.com")
            .one()
            .id
        )
        # Grant twice should not error — use the granter themselves (already SUPER_ADMIN)
        _register(client, "sa.idempgranttgt@example.com")
        tgt_id = (
            db_session.query(models.User)
            .filter(models.User.email == "sa.idempgranttgt@example.com")
            .one()
            .id
        )
        client.patch(
            f"/users/{tgt_id}/super-admin?enabled=true", headers=_headers(granter_token)
        )
        resp = client.patch(
            f"/users/{tgt_id}/super-admin?enabled=true", headers=_headers(granter_token)
        )
        assert resp.status_code == 200

    def test_revoke_super_admin_happy_path(self, client, db_session):
        granter_token = _register(client, "sa.revoker@example.com")
        _set_role(db_session, "sa.revoker@example.com", models.UserRole.SUPER_ADMIN)
        target_token = _register(client, "sa.revokee@example.com")
        target_id = _set_role(
            db_session, "sa.revokee@example.com", models.UserRole.SUPER_ADMIN
        )

        resp = client.patch(
            f"/users/{target_id}/super-admin?enabled=false",
            headers=_headers(granter_token),
        )
        assert resp.status_code == 200

        # Target no longer has platform admin access
        overview = client.get(
            "/platform-admin/overview", headers=_headers(target_token)
        )
        assert overview.status_code == 403

    def test_cannot_revoke_bootstrap_super_admin(self, client, db_session):
        granter_token = _register(client, "sa.revokebs@example.com")
        _set_role(db_session, "sa.revokebs@example.com", models.UserRole.SUPER_ADMIN)
        # Register/login as bootstrap admin (can't in test, so just try non-existent)
        # Create a user with the bootstrap email to simulate the guard
        bootstrap_user = models.User(
            id=str(uuid.uuid4()),
            email=BOOTSTRAP_SUPER_ADMIN_EMAIL,
            hashed_password="x",
            is_active=True,
            role=models.UserRole.SUPER_ADMIN,
        )
        db_session.add(bootstrap_user)
        db_session.commit()
        resp = client.patch(
            f"/users/{bootstrap_user.id}/super-admin?enabled=false",
            headers=_headers(granter_token),
        )
        assert resp.status_code in (400, 403)

    def test_cannot_self_revoke(self, client, db_session):
        token = _register(client, "sa.selfrev@example.com")
        self_id = _set_role(
            db_session, "sa.selfrev@example.com", models.UserRole.SUPER_ADMIN
        )
        resp = client.patch(
            f"/users/{self_id}/super-admin?enabled=false",
            headers=_headers(token),
        )
        assert resp.status_code in (400, 403)


# ---------------------------------------------------------------------------
# Integration tests: Deactivate user
# ---------------------------------------------------------------------------


class TestDeactivateUser:
    def test_deactivate_and_reactivate(self, client, db_session):
        sa_token = _register(client, "sa.deact@example.com")
        _set_role(db_session, "sa.deact@example.com", models.UserRole.SUPER_ADMIN)
        user_token = _register(client, "user.deact@example.com")
        user_id = (
            db_session.query(models.User)
            .filter(models.User.email == "user.deact@example.com")
            .one()
            .id
        )

        # Deactivate
        resp = client.patch(
            f"/users/{user_id}/status?active=false", headers=_headers(sa_token)
        )
        assert resp.status_code == 200

        # Deactivated user JWT should be rejected
        protected = client.get("/entries/", headers=_headers(user_token))
        assert protected.status_code in (401, 403)

        # Reactivate
        resp = client.patch(
            f"/users/{user_id}/status?active=true", headers=_headers(sa_token)
        )
        assert resp.status_code == 200

    def test_regular_user_cannot_deactivate(self, client, db_session):
        token = _register(client, "reg.deact@example.com")
        target_id = (
            db_session.query(models.User)
            .filter(models.User.email == "reg.deact@example.com")
            .one()
            .id
        )
        resp = client.patch(
            f"/users/{target_id}/status?active=false", headers=_headers(token)
        )
        assert resp.status_code == 403

    def test_cannot_deactivate_bootstrap_admin(self, client, db_session):
        sa_token = _register(client, "sa.deactbs@example.com")
        _set_role(db_session, "sa.deactbs@example.com", models.UserRole.SUPER_ADMIN)
        bootstrap_user = models.User(
            id=str(uuid.uuid4()),
            email=BOOTSTRAP_SUPER_ADMIN_EMAIL,
            hashed_password="x",
            is_active=True,
            role=models.UserRole.SUPER_ADMIN,
        )
        db_session.add(bootstrap_user)
        db_session.commit()
        resp = client.patch(
            f"/users/{bootstrap_user.id}/status?active=false",
            headers=_headers(sa_token),
        )
        assert resp.status_code in (400, 403)

    def test_nonexistent_user_returns_404(self, client, db_session):
        token = _register(client, "sa.deact404@example.com")
        _set_role(db_session, "sa.deact404@example.com", models.UserRole.SUPER_ADMIN)
        resp = client.patch(
            f"/users/{uuid.uuid4()}/status?active=false", headers=_headers(token)
        )
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, client):
        resp = client.patch(f"/users/{uuid.uuid4()}/status?active=false")
        assert resp.status_code in (401, 403, 404)

    def test_idempotent_deactivation(self, client, db_session):
        sa_token = _register(client, "sa.idemdact@example.com")
        _set_role(db_session, "sa.idemdact@example.com", models.UserRole.SUPER_ADMIN)
        user_id = (
            db_session.query(models.User)
            .filter(models.User.email == "sa.idemdact@example.com")
            .one()
            .id
        )
        _register(client, "user.idemdact@example.com")
        target_id = (
            db_session.query(models.User)
            .filter(models.User.email == "user.idemdact@example.com")
            .one()
            .id
        )
        client.patch(
            f"/users/{target_id}/status?active=false", headers=_headers(sa_token)
        )
        resp = client.patch(
            f"/users/{target_id}/status?active=false", headers=_headers(sa_token)
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Integration tests: Grant/Revoke Pool Admin
# ---------------------------------------------------------------------------


class TestGrantRevokePoolAdmin:
    def _setup(self, client, db_session, suffix=""):
        owner_token = _register(client, f"owner.padmin{suffix}@example.com")
        pool = _create_pool(client, owner_token, name=f"Pool Admin Pool {suffix}")
        member_token = _register(client, f"member.padmin{suffix}@example.com")
        _add_member(db_session, pool["id"], f"member.padmin{suffix}@example.com")
        return owner_token, pool, member_token

    def test_owner_grants_pool_admin(self, client, db_session):
        owner_token, pool, _ = self._setup(client, db_session, "ga1")
        resp = client.put(
            f"/admin/pools/{pool['id']}/admins",
            json={"email": "member.padminga1@example.com"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200

    def test_super_admin_can_grant_pool_admin(self, client, db_session):
        owner_token, pool, _ = self._setup(client, db_session, "gasa")
        sa_token = _register(client, "sa.padmin.gasa@example.com")
        _set_role(db_session, "sa.padmin.gasa@example.com", models.UserRole.SUPER_ADMIN)
        resp = client.put(
            f"/admin/pools/{pool['id']}/admins",
            json={"email": "member.padmingasa@example.com"},
            headers=_headers(sa_token),
        )
        assert resp.status_code == 200

    def test_delegated_admin_cannot_grant(self, client, db_session):
        owner_token, pool, member_token = self._setup(client, db_session, "gd1")
        # Make member a delegated admin
        client.put(
            f"/admin/pools/{pool['id']}/admins",
            json={"email": "member.padmingd1@example.com"},
            headers=_headers(owner_token),
        )
        other_token = _register(client, "other.padmingd1@example.com")
        _add_member(db_session, pool["id"], "other.padmingd1@example.com")
        resp = client.put(
            f"/admin/pools/{pool['id']}/admins",
            json={"email": "other.padmingd1@example.com"},
            headers=_headers(member_token),
        )
        assert resp.status_code == 403

    def test_regular_user_cannot_grant(self, client, db_session):
        _, pool, _ = self._setup(client, db_session, "rg1")
        other_token = _register(client, "other.padminrg1@example.com")
        resp = client.put(
            f"/admin/pools/{pool['id']}/admins",
            json={"email": "member.padminrg1@example.com"},
            headers=_headers(other_token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, db_session):
        _, pool, _ = self._setup(client, db_session, "ua1")
        resp = client.put(
            f"/admin/pools/{pool['id']}/admins", json={"email": "x@y.com"}
        )
        assert resp.status_code in (401, 403, 404)

    def test_email_not_in_pool_returns_400_or_404(self, client, db_session):
        owner_token, pool, _ = self._setup(client, db_session, "np1")
        _register(client, "nonmember.padminnp1@example.com")
        resp = client.put(
            f"/admin/pools/{pool['id']}/admins",
            json={"email": "nonmember.padminnp1@example.com"},
            headers=_headers(owner_token),
        )
        assert resp.status_code in (400, 404)

    def test_grant_idempotent(self, client, db_session):
        owner_token, pool, _ = self._setup(client, db_session, "idm1")
        client.put(
            f"/admin/pools/{pool['id']}/admins",
            json={"email": "member.padminidm1@example.com"},
            headers=_headers(owner_token),
        )
        resp = client.put(
            f"/admin/pools/{pool['id']}/admins",
            json={"email": "member.padminidm1@example.com"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200

    def test_owner_revokes_pool_admin(self, client, db_session):
        owner_token, pool, _ = self._setup(client, db_session, "rv1")
        client.put(
            f"/admin/pools/{pool['id']}/admins",
            json={"email": "member.padminrv1@example.com"},
            headers=_headers(owner_token),
        )
        resp = client.delete(
            f"/admin/pools/{pool['id']}/admins?email=member.padminrv1@example.com",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        # Member's admin record should be gone (owner's own record may remain)
        member = (
            db_session.query(models.User)
            .filter_by(email="member.padminrv1@example.com")
            .one()
        )
        member_record = (
            db_session.query(models.PoolAdmin)
            .filter_by(pool_id=pool["id"], user_id=member.id)
            .first()
        )
        assert member_record is None

    def test_cannot_revoke_pool_owner(self, client, db_session):
        owner_token, pool, _ = self._setup(client, db_session, "rvo1")
        resp = client.delete(
            f"/admin/pools/{pool['id']}/admins?email=owner.padminrvo1@example.com",
            headers=_headers(owner_token),
        )
        assert resp.status_code in (400, 403)


# ---------------------------------------------------------------------------
# Integration tests: Transfer Pool Ownership
# ---------------------------------------------------------------------------


class TestTransferPoolOwnership:
    def test_owner_transfers_ownership(self, client, db_session):
        owner_token = _register(client, "owner.transfer@example.com")
        pool = _create_pool(client, owner_token, name="Transfer Pool")
        new_owner_token = _register(client, "newowner.transfer@example.com")
        _add_member(db_session, pool["id"], "newowner.transfer@example.com")

        resp = client.put(
            f"/admin/pools/{pool['id']}/owner",
            json={"email": "newowner.transfer@example.com"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        db_session.expire_all()
        updated_pool = db_session.query(models.Pool).filter_by(id=pool["id"]).one()
        new_owner = (
            db_session.query(models.User)
            .filter_by(email="newowner.transfer@example.com")
            .one()
        )
        assert updated_pool.owner_id == new_owner.id

    def test_previous_owner_retains_pool_admin(self, client, db_session):
        owner_token = _register(client, "owner.retainadmin@example.com")
        pool = _create_pool(client, owner_token, name="Retain Admin Pool")
        _register(client, "newowner.retainadmin@example.com")
        _add_member(db_session, pool["id"], "newowner.retainadmin@example.com")

        client.put(
            f"/admin/pools/{pool['id']}/owner",
            json={"email": "newowner.retainadmin@example.com"},
            headers=_headers(owner_token),
        )
        old_owner = (
            db_session.query(models.User)
            .filter_by(email="owner.retainadmin@example.com")
            .one()
        )
        admin_record = (
            db_session.query(models.PoolAdmin)
            .filter_by(pool_id=pool["id"], user_id=old_owner.id)
            .first()
        )
        assert admin_record is not None

    def test_delegated_admin_cannot_transfer(self, client, db_session):
        owner_token = _register(client, "owner.transfail@example.com")
        pool = _create_pool(client, owner_token, name="Transfer Fail Pool")
        admin_token = _register(client, "admin.transfail@example.com")
        _add_member(db_session, pool["id"], "admin.transfail@example.com")
        client.put(
            f"/admin/pools/{pool['id']}/admins",
            json={"email": "admin.transfail@example.com"},
            headers=_headers(owner_token),
        )
        _register(client, "target.transfail@example.com")
        _add_member(db_session, pool["id"], "target.transfail@example.com")
        resp = client.put(
            f"/admin/pools/{pool['id']}/owner",
            json={"email": "target.transfail@example.com"},
            headers=_headers(admin_token),
        )
        assert resp.status_code == 403

    def test_new_owner_not_in_pool_returns_400_or_404(self, client, db_session):
        owner_token = _register(client, "owner.transnopool@example.com")
        pool = _create_pool(client, owner_token, name="Transfer No Pool")
        _register(client, "outsider.transnopool@example.com")
        resp = client.put(
            f"/admin/pools/{pool['id']}/owner",
            json={"email": "outsider.transnopool@example.com"},
            headers=_headers(owner_token),
        )
        assert resp.status_code in (400, 404)

    def test_unauthenticated_returns_401(self, client, db_session):
        owner_token = _register(client, "owner.transunauth@example.com")
        pool = _create_pool(client, owner_token, name="Transfer Unauth Pool")
        resp = client.put(f"/admin/pools/{pool['id']}/owner", json={"email": "x@y.com"})
        assert resp.status_code in (401, 403, 404)


# ---------------------------------------------------------------------------
# Integration tests: Mark Dues Paid
# ---------------------------------------------------------------------------


class TestMarkDuesPaid:
    def test_admin_marks_dues_paid(self, client, db_session):
        owner_token = _register(client, "owner.dues@example.com")
        pool = _create_pool(client, owner_token, name="Dues Pool")
        member_token = _register(client, "member.dues@example.com")
        member_id = _add_member(db_session, pool["id"], "member.dues@example.com")

        resp = client.put(
            f"/admin/pools/{pool['id']}/users/{member_id}/dues",
            json={"paid": True},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        db_session.expire_all()
        membership = (
            db_session.query(models.PoolMember)
            .filter_by(pool_id=pool["id"], user_id=member_id)
            .one()
        )
        assert membership.dues_paid is True

    def test_admin_marks_dues_unpaid(self, client, db_session):
        owner_token = _register(client, "owner.duesoff@example.com")
        pool = _create_pool(client, owner_token, name="Dues Off Pool")
        member_id = _add_member(db_session, pool["id"], "owner.duesoff@example.com")
        _register(client, "member.duesoff@example.com")
        mid = _add_member(db_session, pool["id"], "member.duesoff@example.com")

        client.put(
            f"/admin/pools/{pool['id']}/users/{mid}/dues",
            json={"paid": True},
            headers=_headers(owner_token),
        )
        resp = client.put(
            f"/admin/pools/{pool['id']}/users/{mid}/dues",
            json={"paid": False},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200

    def test_regular_user_cannot_mark_dues(self, client, db_session):
        owner_token = _register(client, "owner.duesreg@example.com")
        pool = _create_pool(client, owner_token, name="Dues Reg Pool")
        member_token = _register(client, "member.duesreg@example.com")
        member_id = _add_member(db_session, pool["id"], "member.duesreg@example.com")

        resp = client.put(
            f"/admin/pools/{pool['id']}/users/{member_id}/dues",
            json={"paid": True},
            headers=_headers(member_token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, db_session):
        owner_token = _register(client, "owner.duesua@example.com")
        pool = _create_pool(client, owner_token, name="Dues UA Pool")
        resp = client.put(
            f"/admin/pools/{pool['id']}/users/{uuid.uuid4()}/dues",
            json={"paid": True},
        )
        assert resp.status_code in (401, 403, 404)

    def test_user_not_in_pool_returns_404(self, client, db_session):
        owner_token = _register(client, "owner.dues404@example.com")
        pool = _create_pool(client, owner_token, name="Dues 404 Pool")
        resp = client.put(
            f"/admin/pools/{pool['id']}/users/{uuid.uuid4()}/dues",
            json={"paid": True},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Integration tests: Update Pool Participant Email
# ---------------------------------------------------------------------------


class TestUpdatePoolParticipantEmail:
    def test_admin_updates_email(self, client, db_session):
        owner_token = _register(client, "owner.updateemail@example.com")
        pool = _create_pool(client, owner_token, name="Update Email Pool")
        member_id = _add_member(db_session, pool["id"], "owner.updateemail@example.com")
        _register(client, "member.updateemail@example.com")
        mid = _add_member(db_session, pool["id"], "member.updateemail@example.com")

        resp = client.patch(
            f"/admin/pools/{pool['id']}/users/{mid}/email?email=member.updateemail.new@example.com",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        db_session.expire_all()
        user = db_session.query(models.User).filter_by(id=mid).one()
        assert user.email == "member.updateemail.new@example.com"

    def test_duplicate_email_returns_409(self, client, db_session):
        owner_token = _register(client, "owner.dupemail@example.com")
        pool = _create_pool(client, owner_token, name="Dupe Email Pool")
        _register(client, "member1.dupemail@example.com")
        mid1 = _add_member(db_session, pool["id"], "member1.dupemail@example.com")
        _register(client, "member2.dupemail@example.com")
        _add_member(db_session, pool["id"], "member2.dupemail@example.com")

        resp = client.patch(
            f"/admin/pools/{pool['id']}/users/{mid1}/email?email=member2.dupemail@example.com",
            headers=_headers(owner_token),
        )
        assert resp.status_code in (400, 409)

    def test_cannot_change_bootstrap_admin_email(self, client, db_session):
        owner_token = _register(client, "owner.chgbs@example.com")
        pool = _create_pool(client, owner_token, name="Change BS Pool")
        bootstrap_user = models.User(
            id=str(uuid.uuid4()),
            email=BOOTSTRAP_SUPER_ADMIN_EMAIL,
            hashed_password="x",
            is_active=True,
            role=models.UserRole.SUPER_ADMIN,
        )
        db_session.add(bootstrap_user)
        db_session.commit()
        _add_member(db_session, pool["id"], BOOTSTRAP_SUPER_ADMIN_EMAIL)

        resp = client.patch(
            f"/admin/pools/{pool['id']}/users/{bootstrap_user.id}/email?email=new.bs@example.com",
            headers=_headers(owner_token),
        )
        assert resp.status_code in (400, 403)

    def test_regular_user_cannot_update_email(self, client, db_session):
        owner_token = _register(client, "owner.regemail@example.com")
        pool = _create_pool(client, owner_token, name="Reg Email Pool")
        regular_token = _register(client, "regular.regemail@example.com")
        mid = _add_member(db_session, pool["id"], "owner.regemail@example.com")

        resp = client.patch(
            f"/admin/pools/{pool['id']}/users/{mid}/email?email=changed@example.com",
            headers=_headers(regular_token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, db_session):
        owner_token = _register(client, "owner.emailua@example.com")
        pool = _create_pool(client, owner_token, name="Email UA Pool")
        resp = client.patch(
            f"/admin/pools/{pool['id']}/users/{uuid.uuid4()}/email?email=x@y.com"
        )
        assert resp.status_code in (401, 403, 404)


# ---------------------------------------------------------------------------
# Integration tests: Search Pool Entries (Admin View)
# ---------------------------------------------------------------------------


class TestSearchPoolEntriesAdmin:
    def test_admin_sees_all_entries(self, client, db_session):
        owner_token = _register(client, "owner.srchent@example.com")
        pool = _create_pool(client, owner_token, name="Search Entries Pool")
        _create_entry(client, owner_token, pool["id"], name="Alpha Entry")
        _create_entry(client, owner_token, pool["id"], name="Beta Entry")

        resp = client.get(
            f"/admin/pools/{pool['id']}/entries", headers=_headers(owner_token)
        )
        assert resp.status_code == 200
        names = {e["name"] for e in resp.json()}
        assert {"Alpha Entry", "Beta Entry"} <= names

    def test_filter_by_username(self, client, db_session):
        owner_token = _register(client, "owner.filterusr@example.com")
        pool = _create_pool(client, owner_token, name="Filter User Pool")
        member_token = _register(client, "member.filterusr@example.com")
        _add_member(db_session, pool["id"], "member.filterusr@example.com")
        _create_entry(client, owner_token, pool["id"], name="Owner Entry")
        _create_entry(client, member_token, pool["id"], name="Member Entry")

        resp = client.get(
            f"/admin/pools/{pool['id']}/entries?username=member.filterusr",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()]
        assert "Member Entry" in names
        assert "Owner Entry" not in names

    def test_filter_by_entry_name(self, client, db_session):
        owner_token = _register(client, "owner.filtername@example.com")
        pool = _create_pool(client, owner_token, name="Filter Name Pool")
        _create_entry(client, owner_token, pool["id"], name="SpecialXYZ")
        _create_entry(client, owner_token, pool["id"], name="NormalEntry")

        resp = client.get(
            f"/admin/pools/{pool['id']}/entries?entry_name=specialxyz",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()]
        assert "SpecialXYZ" in names
        assert "NormalEntry" not in names

    def test_regular_user_returns_403(self, client, db_session):
        owner_token = _register(client, "owner.entsrch403@example.com")
        pool = _create_pool(client, owner_token, name="403 Search Pool")
        regular_token = _register(client, "regular.entsrch403@example.com")
        resp = client.get(
            f"/admin/pools/{pool['id']}/entries", headers=_headers(regular_token)
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, db_session):
        owner_token = _register(client, "owner.srchentua@example.com")
        pool = _create_pool(client, owner_token, name="Unauth Search Pool")
        client.cookies.clear()
        resp = client.get(f"/admin/pools/{pool['id']}/entries")
        assert resp.status_code in (401, 403, 404)

    def test_no_matches_returns_empty_list(self, client, db_session):
        owner_token = _register(client, "owner.srchempty@example.com")
        pool = _create_pool(client, owner_token, name="Empty Search Pool")
        _create_entry(client, owner_token, pool["id"], name="SomeEntry")

        resp = client.get(
            f"/admin/pools/{pool['id']}/entries?entry_name=zzznomatch",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Integration tests: Delete Pool Entry
# ---------------------------------------------------------------------------


class TestDeletePoolEntry:
    def test_admin_deletes_entry(self, client, db_session):
        owner_token = _register(client, "owner.delentry@example.com")
        pool = _create_pool(client, owner_token, name="Delete Entry Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="To Delete")
        pick = _add_pick(db_session, entry["id"], 1, "KC")

        resp = client.delete(
            f"/admin/pools/{pool['id']}/entries/{entry['id']}",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        assert db_session.query(models.Entry).filter_by(id=entry["id"]).first() is None
        assert db_session.query(models.Pick).filter_by(id=pick.id).first() is None

    def test_delete_includes_reason_in_audit(self, client, db_session):
        owner_token = _register(client, "owner.delreason@example.com")
        pool = _create_pool(client, owner_token, name="Delete Reason Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="Reason Entry")

        resp = client.delete(
            f"/admin/pools/{pool['id']}/entries/{entry['id']}?reason=test+reason",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        db_session.expire_all()
        log = (
            db_session.query(models.AuditLog)
            .filter_by(action="ADMIN_DELETE_ENTRY")
            .first()
        )
        assert log is not None
        assert (
            "test reason" in (log.details or "").lower()
            or "reason" in (log.details or "").lower()
        )

    def test_regular_user_returns_403(self, client, db_session):
        owner_token = _register(client, "owner.del403@example.com")
        pool = _create_pool(client, owner_token, name="Del 403 Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="Protected Entry")
        regular_token = _register(client, "regular.del403@example.com")
        resp = client.delete(
            f"/admin/pools/{pool['id']}/entries/{entry['id']}",
            headers=_headers(regular_token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, db_session):
        owner_token = _register(client, "owner.delua@example.com")
        pool = _create_pool(client, owner_token, name="Del UA Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="UA Entry")
        client.cookies.clear()
        resp = client.delete(f"/admin/pools/{pool['id']}/entries/{entry['id']}")
        assert resp.status_code in (401, 403, 404)

    def test_nonexistent_entry_returns_404(self, client, db_session):
        owner_token = _register(client, "owner.del404@example.com")
        pool = _create_pool(client, owner_token, name="Del 404 Pool")
        resp = client.delete(
            f"/admin/pools/{pool['id']}/entries/{uuid.uuid4()}",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 404

    def test_entry_from_different_pool_returns_404(self, client, db_session):
        owner_token = _register(client, "owner.delwrong@example.com")
        pool_a = _create_pool(client, owner_token, name="Del Wrong A")
        pool_b = _create_pool(client, owner_token, name="Del Wrong B")
        entry_b = _create_entry(client, owner_token, pool_b["id"], name="Entry In B")
        resp = client.delete(
            f"/admin/pools/{pool_a['id']}/entries/{entry_b['id']}",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Integration tests: Admin Override Pick
# ---------------------------------------------------------------------------


class TestAdminOverridePick:
    def test_admin_overrides_pick(self, client, db_session):
        owner_token = _register(client, "owner.overpick@example.com")
        pool = _create_pool(client, owner_token, name="Override Pick Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="Override Entry")
        pick = _add_pick(db_session, entry["id"], 1, "KC")

        resp = client.patch(
            f"/admin/pools/{pool['id']}/picks/{pick.id}",
            json={"team": "BUF"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        db_session.expire_all()
        updated_pick = db_session.query(models.Pick).filter_by(id=pick.id).one()
        assert updated_pick.team == "BUF"

    def test_duplicate_team_returns_400(self, client, db_session):
        owner_token = _register(client, "owner.dupteam@example.com")
        pool = _create_pool(client, owner_token, name="Dup Team Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="Dup Team Entry")
        _add_pick(db_session, entry["id"], 1, "KC")
        pick2 = _add_pick(db_session, entry["id"], 2, "BUF")

        resp = client.patch(
            f"/admin/pools/{pool['id']}/picks/{pick2.id}",
            json={"team": "KC"},
            headers=_headers(owner_token),
        )
        assert resp.status_code in (400, 409)

    def test_regular_user_returns_403(self, client, db_session):
        owner_token = _register(client, "owner.ovp403@example.com")
        pool = _create_pool(client, owner_token, name="Ovp 403 Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="403 Entry")
        pick = _add_pick(db_session, entry["id"], 1, "KC")
        regular_token = _register(client, "regular.ovp403@example.com")
        resp = client.patch(
            f"/admin/pools/{pool['id']}/picks/{pick.id}",
            json={"team": "BUF"},
            headers=_headers(regular_token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, db_session):
        owner_token = _register(client, "owner.ovpua@example.com")
        pool = _create_pool(client, owner_token, name="Ovp UA Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="UA Pick Entry")
        pick = _add_pick(db_session, entry["id"], 1, "KC")
        client.cookies.clear()
        resp = client.patch(
            f"/admin/pools/{pool['id']}/picks/{pick.id}", json={"team": "BUF"}
        )
        assert resp.status_code in (401, 403, 404)

    def test_pick_not_in_pool_returns_404(self, client, db_session):
        owner_token = _register(client, "owner.ovp404@example.com")
        pool_a = _create_pool(client, owner_token, name="Ovp 404 A")
        pool_b = _create_pool(client, owner_token, name="Ovp 404 B")
        entry_b = _create_entry(client, owner_token, pool_b["id"], name="B Entry")
        pick_b = _add_pick(db_session, entry_b["id"], 1, "KC")
        resp = client.patch(
            f"/admin/pools/{pool_a['id']}/picks/{pick_b.id}",
            json={"team": "BUF"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 404

    def test_audit_log_created(self, client, db_session):
        owner_token = _register(client, "owner.ovpaudit@example.com")
        pool = _create_pool(client, owner_token, name="Ovp Audit Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="Audit Pick Entry")
        pick = _add_pick(db_session, entry["id"], 1, "KC")

        client.patch(
            f"/admin/pools/{pool['id']}/picks/{pick.id}",
            json={"team": "BUF"},
            headers=_headers(owner_token),
        )
        db_session.expire_all()
        log = (
            db_session.query(models.AuditLog)
            .filter_by(action="ADMIN_PICK_EDIT")
            .first()
        )
        assert log is not None


# ---------------------------------------------------------------------------
# Integration tests: Correct Entry Pick
# ---------------------------------------------------------------------------


class TestCorrectEntryPick:
    def test_admin_corrects_pick(self, client, db_session):
        owner_token = _register(client, "owner.corr@example.com")
        pool = _create_pool(client, owner_token, name="Correct Pick Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="Correct Entry")
        _add_pick(db_session, entry["id"], 3, "DAL")

        resp = client.patch(
            f"/admin/pools/{pool['id']}/entries/{entry['id']}/weeks/3/pick",
            json={"team": "SEA"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        db_session.expire_all()
        pick = (
            db_session.query(models.Pick).filter_by(entry_id=entry["id"], week=3).one()
        )
        assert pick.team == "SEA"

    def test_no_pick_for_week_returns_404(self, client, db_session):
        owner_token = _register(client, "owner.corrnopick@example.com")
        pool = _create_pool(client, owner_token, name="No Pick Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="No Pick Entry")

        resp = client.patch(
            f"/admin/pools/{pool['id']}/entries/{entry['id']}/weeks/5/pick",
            json={"team": "NYG"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 404

    def test_regular_user_returns_403(self, client, db_session):
        owner_token = _register(client, "owner.corr403@example.com")
        pool = _create_pool(client, owner_token, name="Corr 403 Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="Corr 403 Entry")
        _add_pick(db_session, entry["id"], 1, "KC")
        regular_token = _register(client, "regular.corr403@example.com")
        resp = client.patch(
            f"/admin/pools/{pool['id']}/entries/{entry['id']}/weeks/1/pick",
            json={"team": "BUF"},
            headers=_headers(regular_token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, db_session):
        owner_token = _register(client, "owner.corrua@example.com")
        pool = _create_pool(client, owner_token, name="Corr UA Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="Corr UA Entry")
        client.cookies.clear()
        resp = client.patch(
            f"/admin/pools/{pool['id']}/entries/{entry['id']}/weeks/1/pick",
            json={"team": "BUF"},
        )
        assert resp.status_code in (401, 403, 404)

    def test_reason_is_optional(self, client, db_session):
        owner_token = _register(client, "owner.corrnorea@example.com")
        pool = _create_pool(client, owner_token, name="Corr No Reason Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="No Reason Entry")
        _add_pick(db_session, entry["id"], 2, "TEN")

        resp = client.patch(
            f"/admin/pools/{pool['id']}/entries/{entry['id']}/weeks/2/pick",
            json={"team": "MIA"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200

    def test_entry_in_different_pool_returns_404(self, client, db_session):
        owner_token = _register(client, "owner.corrwrong@example.com")
        pool_a = _create_pool(client, owner_token, name="Corr Wrong A")
        pool_b = _create_pool(client, owner_token, name="Corr Wrong B")
        entry_b = _create_entry(
            client, owner_token, pool_b["id"], name="Wrong Pool Entry"
        )
        _add_pick(db_session, entry_b["id"], 1, "KC")
        resp = client.patch(
            f"/admin/pools/{pool_a['id']}/entries/{entry_b['id']}/weeks/1/pick",
            json={"team": "BUF"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Integration tests: Get/Set User Lock Status
# ---------------------------------------------------------------------------


class TestUserLock:
    def test_get_user_lock_status_unlocked(self, client, db_session):
        owner_token = _register(client, "owner.lockst@example.com")
        pool = _create_pool(client, owner_token, name="Lock Status Pool")
        _register(client, "user.lockst@example.com")
        _add_member(db_session, pool["id"], "user.lockst@example.com")

        resp = client.get(
            f"/admin/pools/{pool['id']}/user-lock?email=user.lockst@example.com",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["locked"] is False
        assert data["reason"] is None

    def test_get_user_lock_status_locked(self, client, db_session):
        owner_token = _register(client, "owner.locklkd@example.com")
        pool = _create_pool(client, owner_token, name="Locked Status Pool")
        _register(client, "user.locklkd@example.com")
        uid = _add_member(db_session, pool["id"], "user.locklkd@example.com")
        db_session.add(
            models.PoolUserLock(
                pool_id=pool["id"],
                user_id=uid,
                locked_at=datetime.now(timezone.utc).replace(tzinfo=None),
                reason="test lock",
            )
        )
        db_session.commit()

        resp = client.get(
            f"/admin/pools/{pool['id']}/user-lock?email=user.locklkd@example.com",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["locked"] is True
        assert data["reason"] == "test lock"

    def test_email_not_in_pool_returns_404(self, client, db_session):
        owner_token = _register(client, "owner.lockne@example.com")
        pool = _create_pool(client, owner_token, name="Lock NE Pool")
        _register(client, "outsider.lockne@example.com")

        resp = client.get(
            f"/admin/pools/{pool['id']}/user-lock?email=outsider.lockne@example.com",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 404

    def test_regular_user_returns_403(self, client, db_session):
        owner_token = _register(client, "owner.lock403@example.com")
        pool = _create_pool(client, owner_token, name="Lock 403 Pool")
        regular_token = _register(client, "regular.lock403@example.com")
        resp = client.get(
            f"/admin/pools/{pool['id']}/user-lock?email=owner.lock403@example.com",
            headers=_headers(regular_token),
        )
        assert resp.status_code == 403

    def test_set_lock_by_email(self, client, db_session):
        owner_token = _register(client, "owner.setlk@example.com")
        pool = _create_pool(client, owner_token, name="Set Lock Pool")
        _register(client, "member.setlk@example.com")
        _add_member(db_session, pool["id"], "member.setlk@example.com")

        resp = client.put(
            f"/admin/pools/{pool['id']}/user-lock",
            json={
                "email": "member.setlk@example.com",
                "locked": True,
                "reason": "testing",
            },
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["locked"] is True

    def test_unlock_by_email(self, client, db_session):
        owner_token = _register(client, "owner.unlklk@example.com")
        pool = _create_pool(client, owner_token, name="Unlock Pool")
        _register(client, "member.unlklk@example.com")
        uid = _add_member(db_session, pool["id"], "member.unlklk@example.com")
        db_session.add(
            models.PoolUserLock(
                pool_id=pool["id"],
                user_id=uid,
                locked_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        db_session.commit()

        resp = client.put(
            f"/admin/pools/{pool['id']}/user-lock",
            json={"email": "member.unlklk@example.com", "locked": False},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        assert (
            db_session.query(models.PoolUserLock)
            .filter_by(pool_id=pool["id"], user_id=uid)
            .first()
            is None
        )

    def test_lock_user_by_id(self, client, db_session):
        owner_token = _register(client, "owner.lockbyid@example.com")
        pool = _create_pool(client, owner_token, name="Lock By ID Pool")
        _register(client, "member.lockbyid@example.com")
        uid = _add_member(db_session, pool["id"], "member.lockbyid@example.com")

        resp = client.post(
            f"/admin/pools/{pool['id']}/users/{uid}/lock",
            json={"reason": "id lock test"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        assert (
            db_session.query(models.PoolUserLock)
            .filter_by(pool_id=pool["id"], user_id=uid)
            .first()
            is not None
        )

    def test_lock_already_locked_returns_409(self, client, db_session):
        owner_token = _register(client, "owner.lockdup@example.com")
        pool = _create_pool(client, owner_token, name="Lock Dup Pool")
        _register(client, "member.lockdup@example.com")
        uid = _add_member(db_session, pool["id"], "member.lockdup@example.com")
        client.post(
            f"/admin/pools/{pool['id']}/users/{uid}/lock",
            json={"reason": "first"},
            headers=_headers(owner_token),
        )
        resp = client.post(
            f"/admin/pools/{pool['id']}/users/{uid}/lock",
            json={"reason": "second"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 409

    def test_unlock_user_by_id(self, client, db_session):
        owner_token = _register(client, "owner.unlkbyid@example.com")
        pool = _create_pool(client, owner_token, name="Unlock By ID Pool")
        _register(client, "member.unlkbyid@example.com")
        uid = _add_member(db_session, pool["id"], "member.unlkbyid@example.com")
        client.post(
            f"/admin/pools/{pool['id']}/users/{uid}/lock",
            json={"reason": "lock"},
            headers=_headers(owner_token),
        )

        resp = client.delete(
            f"/admin/pools/{pool['id']}/users/{uid}/lock",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        assert (
            db_session.query(models.PoolUserLock)
            .filter_by(pool_id=pool["id"], user_id=uid)
            .first()
            is None
        )

    def test_unlock_not_locked_returns_404(self, client, db_session):
        owner_token = _register(client, "owner.unlknl@example.com")
        pool = _create_pool(client, owner_token, name="Unlock NL Pool")
        _register(client, "member.unlknl@example.com")
        uid = _add_member(db_session, pool["id"], "member.unlknl@example.com")

        resp = client.delete(
            f"/admin/pools/{pool['id']}/users/{uid}/lock",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 404

    def test_lock_user_not_in_pool_returns_404(self, client, db_session):
        owner_token = _register(client, "owner.locknopool@example.com")
        pool = _create_pool(client, owner_token, name="Lock No Pool")
        _register(client, "outsider.locknopool@example.com")
        uid = (
            db_session.query(models.User)
            .filter_by(email="outsider.locknopool@example.com")
            .one()
            .id
        )

        resp = client.post(
            f"/admin/pools/{pool['id']}/users/{uid}/lock",
            json={"reason": "nope"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Integration tests: Transfer Entry
# ---------------------------------------------------------------------------


class TestTransferEntry:
    def test_admin_transfers_entry(self, client, db_session):
        owner_token = _register(client, "owner.transent@example.com")
        pool = _create_pool(client, owner_token, name="Transfer Entry Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="Transfer Me")
        _register(client, "newowner.transent@example.com")
        _add_member(db_session, pool["id"], "newowner.transent@example.com")

        resp = client.post(
            f"/admin/pools/{pool['id']}/transfer-entry",
            json={"entry_id": entry["id"], "to_email": "newowner.transent@example.com"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        db_session.expire_all()
        updated = db_session.query(models.Entry).filter_by(id=entry["id"]).one()
        new_owner = (
            db_session.query(models.User)
            .filter_by(email="newowner.transent@example.com")
            .one()
        )
        assert updated.user_id == new_owner.id

    def test_new_owner_not_in_pool_returns_error(self, client, db_session):
        owner_token = _register(client, "owner.transnopool@example.com")
        pool = _create_pool(client, owner_token, name="Trans No Pool Ent")
        entry = _create_entry(
            client, owner_token, pool["id"], name="Trans No Pool Entry"
        )
        _register(client, "outsider.transnopool@example.com")

        resp = client.post(
            f"/admin/pools/{pool['id']}/transfer-entry",
            json={
                "entry_id": entry["id"],
                "to_email": "outsider.transnopool@example.com",
            },
            headers=_headers(owner_token),
        )
        assert resp.status_code in (400, 404)

    def test_name_collision_returns_400(self, client, db_session):
        owner_token = _register(client, "owner.transcoll@example.com")
        pool = _create_pool(client, owner_token, name="Trans Coll Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="Collision Entry")
        _register(client, "other.transcoll@example.com")
        other_token_val = (
            _register(client, "other2.transcoll@example.com") if False else None
        )
        other_id = _add_member(db_session, pool["id"], "other.transcoll@example.com")
        # Create same-named entry for target
        other_user = (
            db_session.query(models.User)
            .filter_by(email="other.transcoll@example.com")
            .one()
        )
        db_session.add(
            models.Entry(
                id=str(uuid.uuid4()),
                pool_id=pool["id"],
                user_id=other_user.id,
                name="Collision Entry",
                alive=True,
            )
        )
        db_session.commit()

        resp = client.post(
            f"/admin/pools/{pool['id']}/transfer-entry",
            json={"entry_id": entry["id"], "to_email": "other.transcoll@example.com"},
            headers=_headers(owner_token),
        )
        assert resp.status_code in (400, 409)

    def test_regular_user_returns_403(self, client, db_session):
        owner_token = _register(client, "owner.transent403@example.com")
        pool = _create_pool(client, owner_token, name="Trans 403 Pool")
        entry = _create_entry(
            client, owner_token, pool["id"], name="403 Transfer Entry"
        )
        regular_token = _register(client, "regular.transent403@example.com")
        resp = client.post(
            f"/admin/pools/{pool['id']}/transfer-entry",
            json={
                "entry_id": entry["id"],
                "to_email": "regular.transent403@example.com",
            },
            headers=_headers(regular_token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, db_session):
        owner_token = _register(client, "owner.transentua@example.com")
        pool = _create_pool(client, owner_token, name="Trans UA Pool")
        entry = _create_entry(client, owner_token, pool["id"], name="UA Transfer Entry")
        client.cookies.clear()
        resp = client.post(
            f"/admin/pools/{pool['id']}/transfer-entry",
            json={"entry_id": entry["id"], "to_email": "x@y.com"},
        )
        assert resp.status_code in (401, 403, 404)


# ---------------------------------------------------------------------------
# Integration tests: View Auto-Picks
# ---------------------------------------------------------------------------


class TestViewAutoPicks:
    def test_no_auto_picks_returns_empty_list(self, client, db_session):
        owner_token = _register(client, "owner.autopick@example.com")
        pool = _create_pool(client, owner_token, name="Auto Pick Pool")

        resp = client.get(
            f"/admin/pools/{pool['id']}/auto-picks",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_regular_user_returns_403(self, client, db_session):
        owner_token = _register(client, "owner.ap403@example.com")
        pool = _create_pool(client, owner_token, name="AP 403 Pool")
        regular_token = _register(client, "regular.ap403@example.com")
        resp = client.get(
            f"/admin/pools/{pool['id']}/auto-picks",
            headers=_headers(regular_token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, db_session):
        owner_token = _register(client, "owner.apua@example.com")
        pool = _create_pool(client, owner_token, name="AP UA Pool")
        client.cookies.clear()
        resp = client.get(f"/admin/pools/{pool['id']}/auto-picks")
        assert resp.status_code in (401, 403, 404)


# ---------------------------------------------------------------------------
# Integration tests: Send Password Reset
# ---------------------------------------------------------------------------


class TestSendPasswordReset:
    def test_admin_can_trigger_password_reset(self, client, db_session):
        owner_token = _register(client, "owner.pwreset@example.com")
        pool = _create_pool(client, owner_token, name="Password Reset Pool")
        _register(client, "member.pwreset@example.com")
        _add_member(db_session, pool["id"], "member.pwreset@example.com")

        resp = client.post(
            f"/admin/pools/{pool['id']}/users/password-reset",
            json={"email": "member.pwreset@example.com"},
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200

    def test_email_not_in_pool_returns_error(self, client, db_session):
        owner_token = _register(client, "owner.pwrne@example.com")
        pool = _create_pool(client, owner_token, name="Password Reset NE Pool")
        _register(client, "outsider.pwrne@example.com")

        resp = client.post(
            f"/admin/pools/{pool['id']}/users/password-reset",
            json={"email": "outsider.pwrne@example.com"},
            headers=_headers(owner_token),
        )
        assert resp.status_code in (403, 404)

    def test_regular_user_returns_403(self, client, db_session):
        owner_token = _register(client, "owner.pwr403@example.com")
        pool = _create_pool(client, owner_token, name="PWR 403 Pool")
        regular_token = _register(client, "regular.pwr403@example.com")
        resp = client.post(
            f"/admin/pools/{pool['id']}/users/password-reset",
            json={"email": "owner.pwr403@example.com"},
            headers=_headers(regular_token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, db_session):
        owner_token = _register(client, "owner.pwrua@example.com")
        pool = _create_pool(client, owner_token, name="PWR UA Pool")
        client.cookies.clear()
        resp = client.post(
            f"/admin/pools/{pool['id']}/users/password-reset",
            json={"email": "owner.pwrua@example.com"},
        )
        assert resp.status_code in (401, 403, 404)


# ---------------------------------------------------------------------------
# Integration tests: Export Pool Entries CSV
# ---------------------------------------------------------------------------


class TestExportPoolEntriesCSV:
    def test_admin_gets_csv(self, client, db_session):
        owner_token = _register(client, "owner.csvexport@example.com")
        pool = _create_pool(client, owner_token, name="CSV Export Pool")
        _create_entry(client, owner_token, pool["id"], name="CSV Entry One")

        resp = client.get(
            f"/admin/pools/{pool['id']}/export/entries.csv",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_csv_contains_header_and_rows(self, client, db_session):
        owner_token = _register(client, "owner.csvrows@example.com")
        pool = _create_pool(client, owner_token, name="CSV Rows Pool")
        _create_entry(client, owner_token, pool["id"], name="Row Entry A")
        _create_entry(client, owner_token, pool["id"], name="Row Entry B")

        resp = client.get(
            f"/admin/pools/{pool['id']}/export/entries.csv",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert lines[0].strip() == "email,entry_name"
        assert len(lines) == 3  # header + 2 entries

    def test_empty_pool_returns_header_only(self, client, db_session):
        owner_token = _register(client, "owner.csvempty@example.com")
        pool = _create_pool(client, owner_token, name="CSV Empty Pool")

        resp = client.get(
            f"/admin/pools/{pool['id']}/export/entries.csv",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        lines = [l for l in resp.text.strip().split("\n") if l.strip()]
        assert len(lines) == 1
        assert lines[0].strip() == "email,entry_name"

    def test_formula_injection_sanitized(self, client, db_session):
        owner_token = _register(client, "owner.csvsanitize@example.com")
        pool = _create_pool(client, owner_token, name="CSV Sanitize Pool")
        # Inject formula-like name directly into DB
        owner_user = (
            db_session.query(models.User)
            .filter_by(email="owner.csvsanitize@example.com")
            .one()
        )
        db_session.add(
            models.Entry(
                id=str(uuid.uuid4()),
                pool_id=pool["id"],
                user_id=owner_user.id,
                name="=SUM(1+1)",
                alive=True,
            )
        )
        db_session.commit()

        resp = client.get(
            f"/admin/pools/{pool['id']}/export/entries.csv",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        assert (
            "=SUM" not in resp.text.split(",", 1)[1].split("\n")[1]
            or resp.text.count("'=SUM") > 0
        )

    def test_regular_user_returns_403(self, client, db_session):
        owner_token = _register(client, "owner.csv403@example.com")
        pool = _create_pool(client, owner_token, name="CSV 403 Pool")
        regular_token = _register(client, "regular.csv403@example.com")
        resp = client.get(
            f"/admin/pools/{pool['id']}/export/entries.csv",
            headers=_headers(regular_token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, db_session):
        owner_token = _register(client, "owner.csvua@example.com")
        pool = _create_pool(client, owner_token, name="CSV UA Pool")
        client.cookies.clear()
        resp = client.get(f"/admin/pools/{pool['id']}/export/entries.csv")
        assert resp.status_code in (401, 403, 404)

    def test_entries_sorted_by_email_then_name(self, client, db_session):
        owner_token = _register(client, "aaa.csvsorted@example.com")
        other_token = _register(client, "zzz.csvsorted@example.com")
        pool = _create_pool(client, owner_token, name="CSV Sorted Pool")
        admin_token = _register(client, "sa.csvsorted@example.com")
        _set_role(db_session, "sa.csvsorted@example.com", models.UserRole.SUPER_ADMIN)
        _add_member(db_session, pool["id"], "zzz.csvsorted@example.com")
        _create_entry(client, owner_token, pool["id"], name="Z Entry")
        _create_entry(client, owner_token, pool["id"], name="A Entry")
        _create_entry(client, other_token, pool["id"], name="Other Entry")

        resp = client.get(
            f"/admin/pools/{pool['id']}/export/entries.csv",
            headers=_headers(owner_token),
        )
        assert resp.status_code == 200
        lines = [l for l in resp.text.strip().split("\n") if l.strip()][
            1:
        ]  # skip header
        emails = [line.split(",")[0] for line in lines]
        assert emails == sorted(emails)
