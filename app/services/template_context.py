import os
from fastapi import Request
from app.models.session import SessionData


def template_context(panel: str, request: Request, session: SessionData, ** kwargs):
    context = {
        "active_section": panel,
        "username": session.display_name,
        "role": session.role,
        "request": request,
        "environment": os.getenv("ENV", "-"),
        "version": os.getenv("VERSION", "-"),
        "git_commit": os.getenv("GIT_COMMIT", "-")[:7],
    }

    context.update(kwargs)
    return context
