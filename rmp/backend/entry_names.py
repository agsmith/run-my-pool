"""Automatic entry names generated from CoolName's default vocabulary."""

from coolname import generate_slug
from sqlalchemy.orm import Session

import models

MAX_RANDOM_ATTEMPTS = 20


def _candidate() -> str:
    return generate_slug(2)


def generate_unique_entry_name(db: Session, user_id: str, pool_id: str) -> str:
    """Return an unused automatic name for one user's entries in a pool."""
    used_names = {
        name.casefold()
        for (name,) in db.query(models.Entry.name)
        .filter(
            models.Entry.user_id == user_id,
            models.Entry.pool_id == pool_id,
        )
        .all()
        if name
    }
    for _ in range(MAX_RANDOM_ATTEMPTS):
        candidate = _candidate()
        if candidate.casefold() not in used_names:
            return candidate

    # An extremely unlikely fallback keeps creation deterministic even when a
    # test generator or a future small vocabulary repeatedly collides.
    base = _candidate()
    suffix = 2
    candidate = base
    while candidate.casefold() in used_names:
        candidate = f"{base} {suffix}"
        suffix += 1
    return candidate
