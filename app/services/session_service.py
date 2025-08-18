import time
import secrets
from typing import Dict, Any
import logging
from app.models.session import SessionData
logger = logging.getLogger(__name__)


class SessionStore:

    def __init__(self, session_timeout: int = 86400):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = session_timeout  # Session timeout in seconds (default 24 hours)
        logger.info("Initialized session store")

    def create_session(self, session: SessionData) -> str:
        session_id = secrets.token_urlsafe(32)
        timestamp = int(time.time())
        self.sessions[session_id] = {
            "session_data": session,
            "created_at": timestamp,
            "last_accessed": timestamp
        }
        logger.info(f"Created new session for user: {session.display_name}")
        return session_id

    def get_session(self, session_id: str) -> SessionData:
        if not session_id or session_id not in self.sessions:
            return None
        session = self.sessions[session_id]
        current_time = int(time.time())

        if current_time - session["last_accessed"] > self.session_timeout:
            logger.info(f"Session {session_id[:8]}... expired")
            self.delete_session(session_id)
            return None

        session["last_accessed"] = current_time
        return session["session_data"]

    def update_session(self, session_id: str, key: str, value: Any) -> bool:
        session = self.get_session(session_id)
        if session:
            session[key] = value
            return True
        return False

    def delete_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            self.sessions.pop(session_id)
            logger.info(f"Deleted session {session_id[:8]}...")


session_store = SessionStore()
