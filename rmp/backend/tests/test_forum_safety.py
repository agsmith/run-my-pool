import pytest
import models
from forum_safety import objectionable
from tests.test_message_board import _reg, _h, _create_pool, _create_entry, _post_msg


@pytest.fixture
def forum(client):
    owner = _reg(client, "mod@example.com")
    member = _reg(client, "member@example.com")
    other = _reg(client, "other@example.com")
    pool = _create_pool(client, owner, "Safety pool")
    for token in (member, other):
        _create_entry(client, token, pool)
    author = client.get("/auth/me", headers=_h(member)).json()["id"]
    return owner, member, other, pool, author


@pytest.mark.parametrize(
    "value",
    [
        "fuck you",
        "f.u.c.k you",
        "f u c k you",
        "f\u200buck you",
        "ＦＵＣＫ you",
        "sh1t",
        "kill yourself",
        "child porn",
    ],
)
def test_filter_rejects_obfuscated_abuse(value):
    assert objectionable(value)


@pytest.mark.parametrize(
    "value",
    ["Great pick!", "Scunthorpe won", "Class assignment", "Seattle 13 New England 10"],
)
def test_filter_preserves_normal_text(value):
    assert not objectionable(value)


def test_native_payload_and_filter(client, forum):
    owner, member, other, pool, author = forum
    assert (
        client.post(
            f"/messages/pool/{pool}",
            headers=_h(member),
            json={"message": "Hello from native"},
        ).status_code
        == 200
    )
    assert _post_msg(client, member, pool, "f.u.c.k you").status_code == 400
    assert (
        client.post(
            f"/messages/pool/{pool}",
            headers=_h(member),
            json={"pool_id": "wrong", "message": "Hello"},
        ).status_code
        == 200
    )


def test_reports_are_private_deduplicated_and_survive_deletion(
    client, forum, db_session
):
    owner, member, other, pool, author = forum
    mid = _post_msg(client, member, pool).json()["id"]
    for _ in range(2):
        assert (
            client.post(
                f"/messages/{mid}/report",
                headers=_h(other),
                json={"reason": "Spam or scam"},
            ).status_code
            == 200
        )
    assert db_session.query(models.ForumReport).count() == 1
    assert client.get(f"/messages/pool/{pool}", headers=_h(other)).json() == []
    state = client.get(f"/messages/pool/{pool}/safety", headers=_h(other)).json()
    assert state["reports"] == [] and not state["can_moderate"]
    state = client.get(f"/messages/pool/{pool}/safety", headers=_h(owner)).json()
    assert len(state["reports"]) == 1 and "reporter_id" not in state["reports"][0]
    assert client.delete(f"/messages/{mid}", headers=_h(member)).status_code == 200
    db_session.expire_all()
    report = db_session.query(models.ForumReport).one()
    assert report.message_snapshot == "Hello world" and report.status == "removed"


def test_personal_block_and_unblock(client, forum):
    owner, member, other, pool, author = forum
    _post_msg(client, member, pool)
    assert (
        client.put(
            f"/messages/pool/{pool}/blocks/{author}", headers=_h(other)
        ).status_code
        == 200
    )
    assert client.get(f"/messages/pool/{pool}", headers=_h(other)).json() == []
    assert len(client.get(f"/messages/pool/{pool}", headers=_h(owner)).json()) == 1
    assert (
        client.delete(f"/messages/blocks/{author}", headers=_h(other)).status_code
        == 200
    )
    assert len(client.get(f"/messages/pool/{pool}", headers=_h(other)).json()) == 1


def test_suspend_enforced_and_restore(client, forum):
    owner, member, other, pool, author = forum
    mid = _post_msg(client, member, pool).json()["id"]
    client.post(
        f"/messages/{mid}/report",
        headers=_h(other),
        json={"reason": "Harassment or hate"},
    )
    report = client.get(f"/messages/pool/{pool}/safety", headers=_h(owner)).json()[
        "reports"
    ][0]["id"]
    url = f"/messages/pool/{pool}/reports/{report}/review"
    assert (
        client.post(url, headers=_h(other), json={"action": "suspend"}).status_code
        == 403
    )
    assert (
        client.post(url, headers=_h(owner), json={"action": "suspend"}).status_code
        == 200
    )
    assert _post_msg(client, member, pool).status_code == 403
    assert client.get(f"/messages/pool/{pool}/safety", headers=_h(member)).json()[
        "suspended"
    ]
    assert (
        client.delete(
            f"/messages/pool/{pool}/suspensions/{author}", headers=_h(other)
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/messages/pool/{pool}/suspensions/{author}", headers=_h(owner)
        ).status_code
        == 200
    )
    assert _post_msg(client, member, pool).status_code == 200


def test_cross_pool_access_and_self_protection(client, forum):
    owner, member, other, pool, author = forum
    outsider = _reg(client, "outsider@example.com")
    other_pool = _create_pool(client, outsider, "Other safety pool")
    mid = _post_msg(client, member, pool).json()["id"]
    assert (
        client.post(
            f"/messages/{mid}/report", headers=_h(outsider), json={"reason": "Other"}
        ).status_code
        == 403
    )
    assert (
        client.get(f"/messages/pool/{pool}/safety", headers=_h(outsider)).status_code
        == 403
    )
    assert (
        client.put(
            f"/messages/pool/{pool}/blocks/{author}", headers=_h(member)
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/messages/{mid}/report", headers=_h(member), json={"reason": "Other"}
        ).status_code
        == 400
    )
    client.post(f"/messages/{mid}/report", headers=_h(other), json={"reason": "Other"})
    report = client.get(f"/messages/pool/{pool}/safety", headers=_h(owner)).json()[
        "reports"
    ][0]["id"]
    assert (
        client.post(
            f"/messages/pool/{other_pool}/reports/{report}/review",
            headers=_h(outsider),
            json={"action": "remove"},
        ).status_code
        == 404
    )


def test_moderator_removal_without_entry(client, forum):
    owner, member, other, pool, author = forum
    mid = _post_msg(client, member, pool).json()["id"]
    assert client.delete(f"/messages/{mid}", headers=_h(owner)).status_code == 200


def test_dismiss_keeps_message_for_others(client, forum):
    owner, member, other, pool, author = forum
    mid = _post_msg(client, member, pool).json()["id"]
    client.post(f"/messages/{mid}/report", headers=_h(other), json={"reason": "Other"})
    rid = client.get(f"/messages/pool/{pool}/safety", headers=_h(owner)).json()[
        "reports"
    ][0]["id"]
    assert (
        client.post(
            f"/messages/pool/{pool}/reports/{rid}/review",
            headers=_h(owner),
            json={"action": "dismiss"},
        ).status_code
        == 200
    )
    assert (
        client.get(f"/messages/pool/{pool}/safety", headers=_h(owner)).json()["reports"]
        == []
    )
    assert len(client.get(f"/messages/pool/{pool}", headers=_h(owner)).json()) == 1


def test_block_is_global_but_suspension_is_pool_scoped(client, forum, db_session):
    from datetime import datetime

    owner, member, other, pool, author = forum
    second_owner = _reg(client, "second-owner@example.com")
    second = _create_pool(client, second_owner, "Second safety pool")
    for token in (member, other):
        _create_entry(client, token, second)
    _post_msg(client, member, second)
    client.put(f"/messages/pool/{pool}/blocks/{author}", headers=_h(other))
    assert client.get(f"/messages/pool/{second}", headers=_h(other)).json() == []
    db_session.add(
        models.ForumBan(pool_id=pool, user_id=author, created_at=datetime.now())
    )
    db_session.commit()
    assert _post_msg(client, member, pool).status_code == 403
    assert _post_msg(client, member, second).status_code == 200
