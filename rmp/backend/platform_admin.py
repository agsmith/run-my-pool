"""Platform-level administrator identity and authorization rules."""

import models


BOOTSTRAP_SUPER_ADMIN_EMAIL = "agsmith11@gmail.com"


def is_platform_super_admin(user: models.User) -> bool:
    """Return whether the account currently has platform support access."""
    return user.role == models.UserRole.SUPER_ADMIN


def is_bootstrap_super_admin(user: models.User) -> bool:
    """The initial account is protected so the platform cannot lose all access."""
    return (user.email or "").strip().lower() == BOOTSTRAP_SUPER_ADMIN_EMAIL
