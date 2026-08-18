"""Privacy-safe labels for identities shown to other pool members."""

from typing import Optional


def display_name_from_email(email: Optional[str]) -> str:
    """Use the local part of an email without exposing its domain."""
    normalized = (email or "").strip()
    local_part, separator, _ = normalized.partition("@")
    if separator and local_part:
        return local_part
    return normalized or "Member"


def public_display_name(user) -> str:
    return display_name_from_email(getattr(user, "email", None))
