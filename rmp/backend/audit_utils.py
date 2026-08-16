"""
Audit logging utility functions
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import models
import json


def create_audit_log(
    db: Session,
    action: str,
    details: str,
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None,
):
    """
    Create an audit log entry for database operations

    Args:
        db: Database session
        action: The action performed (e.g., "CREATE_USER", "UPDATE_PICK", "DELETE_ENTRY")
        details: Human-readable description of the action
        user_id: ID of the user performing the action
        entity_type: Type of entity affected (e.g., "user", "pick", "entry", "pool")
        entity_id: ID of the specific entity affected
        additional_data: Additional structured data about the action
    """
    try:
        # Build detailed information
        audit_details = {
            "description": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if entity_type:
            audit_details["entity_type"] = entity_type
        if entity_id:
            audit_details["entity_id"] = entity_id
        if additional_data:
            audit_details["additional_data"] = additional_data

        # Convert to JSON string
        details_json = json.dumps(audit_details, default=str, indent=2)

        audit_entry = models.AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action=action,
            details=details_json,
            created_at=datetime.now(timezone.utc),
        )

        db.add(audit_entry)
        db.commit()

    except Exception as e:
        # Don't let audit logging failures break the main operation
        print(f"Failed to create audit log: {e}")
        db.rollback()


def log_create_operation(
    db: Session,
    entity_type: str,
    entity_id: str,
    user_id: Optional[str] = None,
    entity_data: Optional[Dict[str, Any]] = None,
):
    """Log creation of a new entity"""
    create_audit_log(
        db=db,
        action=f"CREATE_{entity_type.upper()}",
        details=f"Created new {entity_type} with ID {entity_id}",
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        additional_data=entity_data,
    )


def log_update_operation(
    db: Session,
    entity_type: str,
    entity_id: str,
    user_id: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
):
    """Log update of an existing entity"""
    create_audit_log(
        db=db,
        action=f"UPDATE_{entity_type.upper()}",
        details=f"Updated {entity_type} with ID {entity_id}",
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        additional_data={"changes": changes} if changes else None,
    )


def log_delete_operation(
    db: Session,
    entity_type: str,
    entity_id: str,
    user_id: Optional[str] = None,
    entity_data: Optional[Dict[str, Any]] = None,
):
    """Log deletion of an entity"""
    create_audit_log(
        db=db,
        action=f"DELETE_{entity_type.upper()}",
        details=f"Deleted {entity_type} with ID {entity_id}",
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        additional_data=entity_data,
    )


def log_authentication_event(
    db: Session,
    action: str,
    user_email: str,
    user_id: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None,
):
    """Log authentication-related events"""
    create_audit_log(
        db=db,
        action=action,
        details=f"Authentication event for user {user_email}",
        user_id=user_id,
        entity_type="authentication",
        additional_data={"email": user_email, **additional_info}
        if additional_info
        else {"email": user_email},
    )


def log_admin_action(
    db: Session,
    action: str,
    admin_user_id: str,
    details: str,
    target_entity_type: Optional[str] = None,
    target_entity_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None,
):
    """Log administrative actions"""
    create_audit_log(
        db=db,
        action=f"ADMIN_{action}",
        details=f"Admin action: {details}",
        user_id=admin_user_id,
        entity_type=target_entity_type,
        entity_id=target_entity_id,
        additional_data=additional_data,
    )
