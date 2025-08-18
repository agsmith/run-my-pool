import logging
import datetime
from typing import Dict, Any, Optional
from app.models.session import SessionData

logger = logging.getLogger(__name__)


class AuditService:

    def __init__(self, db_service):
        self.db_service = db_service
        self.collection = "rule_audits"

    def log_add_audit(self, session_data: SessionData, new_rule: Dict[str, Any]) -> None:
        self._log_audit("ADD", session_data, new_rule["_id"], None, new_rule)

    def log_edit_audit(self, session_data: SessionData, new_rule: Dict[str, Any], old_rule: Dict[str, Any]) -> None:
        self._log_audit("EDIT", session_data, old_rule["_id"], old_rule, new_rule)

    def log_delete_audit(self, session_data: SessionData, old_rule: Dict[str, Any]) -> None:
        self._log_audit("DELETE", session_data, old_rule["_id"], old_rule, None)

    def _log_audit(self, operation: str, session_data: SessionData, rule_id: str,
                   old_rule: Optional[Dict[str, Any]], new_rule: Optional[Dict[str, Any]]) -> None:
        try:
            audit_log = {
                "operation": operation,
                "user_mail": session_data.mail,
                "rule_id": rule_id,
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
            }
            if old_rule:
                audit_log["old"] = old_rule
            if new_rule:
                audit_log["new"] = new_rule

            self.db_service.get_db()[self.collection].insert_one(audit_log)
            logger.info(f"Audit log created for {operation} operation on rule {rule_id}")
        except Exception as e:
            logger.exception(f"Failed to create audit log: {e}")
