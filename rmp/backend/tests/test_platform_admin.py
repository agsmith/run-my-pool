"""RBAC and global visibility tests for the platform administration boundary."""

import models


def register(client, email):
    password = "Platform123!"
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def set_role(db, email, role):
    user = db.query(models.User).filter(models.User.email == email).one()
    user.role = role
    db.commit()
    db.expire_all()
    return user.id


def test_every_platform_endpoint_rejects_non_super_admins(client, db_session):
    token = register(client, "ordinary@platform.example.com")
    endpoints = (
        "/platform-admin/overview",
        "/platform-admin/pools",
        "/platform-admin/entries",
    )
    for endpoint in endpoints:
        assert client.get(endpoint, headers=headers(token)).status_code == 403

    set_role(db_session, "ordinary@platform.example.com", models.UserRole.POOL_ADMIN)
    for endpoint in endpoints:
        response = client.get(endpoint, headers=headers(token))
        assert response.status_code == 403
        assert response.json()["detail"] == "Platform admin access required"


def test_platform_admin_sees_all_users_pools_and_entries(client, db_session):
    owner_token = register(client, "owner@platform.example.com")
    register(client, "unassigned@platform.example.com")
    admin_token = register(client, "support@platform.example.com")
    set_role(db_session, "support@platform.example.com", models.UserRole.SUPER_ADMIN)

    public_pool = client.post(
        "/pools/create", json={"name": "Public Platform Pool", "is_private": False},
        headers=headers(owner_token),
    ).json()
    private_pool = client.post(
        "/pools/create", json={"name": "Private Platform Pool", "is_private": True, "join_password": "invite-code"},
        headers=headers(owner_token),
    ).json()
    entry = client.post(
        "/entries/create", json={"name": "Owner Entry", "pool_id": public_pool["id"]},
        headers=headers(owner_token),
    )
    assert entry.status_code == 200, entry.text

    overview = client.get("/platform-admin/overview", headers=headers(admin_token))
    assert overview.status_code == 200
    assert overview.json()["pools"] == 2
    assert overview.json()["private_pools"] == 1
    assert overview.json()["entries"] == 1
    assert overview.json()["unassigned_users"] == 2

    pools = client.get("/platform-admin/pools", headers=headers(admin_token)).json()
    assert {pool["name"] for pool in pools} == {"Public Platform Pool", "Private Platform Pool"}
    assert {pool["is_private"] for pool in pools} == {True, False}
    entries = client.get("/platform-admin/entries", headers=headers(admin_token)).json()
    assert entries[0]["name"] == "Owner Entry"
    assert entries[0]["user_email"] == "owner@platform.example.com"

    users = client.get("/users/admin-dashboard?limit=500", headers=headers(admin_token)).json()
    assert {user["email"] for user in users["users"]} == {
        "owner@platform.example.com", "unassigned@platform.example.com", "support@platform.example.com"
    }

    # Global pool administration works without making the super admin a member.
    assert client.get(f"/pools/{private_pool['id']}", headers=headers(admin_token)).status_code == 200
    access = client.get(f"/pools/{private_pool['id']}/is-admin", headers=headers(admin_token))
    assert access.status_code == 200
    assert access.json()["has_admin_access"] is True
