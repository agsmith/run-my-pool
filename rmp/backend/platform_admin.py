"""Platform-level administrator identity and authorization rules."""

from fastapi import Depends, HTTPException, status

import deps
import models


BOOTSTRAP_SUPER_ADMIN_EMAIL = "agsmith11@gmail.com"


def is_platform_super_admin(user: models.User) -> bool:
    """Return whether the account currently has platform support access."""
    return user.role == models.UserRole.SUPER_ADMIN


def is_bootstrap_super_admin(user: models.User) -> bool:
    """The initial account is protected so the platform cannot lose all access."""
    return (user.email or "").strip().lower() == BOOTSTRAP_SUPER_ADMIN_EMAIL


def require_platform_super_admin(
    current_user: models.User = Depends(deps.get_current_user),
) -> models.User:
    """Authorize platform-wide operations at the API boundary."""
    if not is_platform_super_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )
    return current_user
