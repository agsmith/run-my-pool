"""
Secure database operations to prevent SQL injection and other database-related vulnerabilities
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timedelta, timezone
from security_config import SecurityValidators, InputSanitizer, AuditLogger

logger = logging.getLogger(__name__)


class SecureDBOperations:
    """Secure database operations using parameterized queries"""
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[Dict[str, Any]]:
        """Securely get user by username using parameterized query"""
        try:
            # Validate input
            is_valid, _ = SecurityValidators.validate_username(username)
            if not is_valid:
                return None
            
            # Use parameterized query to prevent SQL injection
            result = db.execute(
                text("SELECT user_id, username, email, password, salt, admin_role, force_password_change, failed_login_attempts, last_login_attempt, created_time FROM User_IAM WHERE username = :username"),
                {"username": username}
            ).fetchone()
            
            if result:
                return {
                    "user_id": result[0],
                    "username": result[1],
                    "email": result[2],
                    "password": result[3],
                    "salt": result[4],
                    "admin_role": result[5],
                    "force_password_change": result[6],
                    "failed_login_attempts": result[7],
                    "last_login_attempt": result[8],
                    "created_time": result[9]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    @staticmethod
    def get_user_by_session_token(db: Session, username: str, session_token: str) -> Optional[Dict[str, Any]]:
        """Securely get user by session token"""
        try:
            # Validate inputs
            is_valid, _ = SecurityValidators.validate_username(username)
            if not is_valid or not session_token:
                return None
            
            result = db.execute(
                text("SELECT user_id, username, admin_role, session_token_expiry FROM User_IAM WHERE username = :username AND session_token = :session_token"),
                {"username": username, "session_token": session_token}
            ).fetchone()
            
            if result:
                # Check if session is expired
                if result[3] and result[3] < datetime.utcnow():
                    # Session expired, clear it
                    SecureDBOperations.clear_session_token(db, username)
                    return None
                
                return {
                    "user_id": result[0],
                    "username": result[1],
                    "admin_role": result[2],
                    "session_token_expiry": result[3]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by session token: {e}")
            return None
    
    @staticmethod
    def create_user(db: Session, username: str, email: str, password_hash: str, salt: str) -> bool:
        """Securely create a new user"""
        try:
            # Validate inputs
            username_valid, username_msg = SecurityValidators.validate_username(username)
            if not username_valid:
                logger.warning(f"Invalid username during user creation: {username_msg}")
                return False
            
            email_valid, email_msg = SecurityValidators.validate_email(email)
            if not email_valid:
                logger.warning(f"Invalid email during user creation: {email_msg}")
                return False
            
            # Check if user already exists
            existing_user = db.execute(
                text("SELECT username FROM User_IAM WHERE username = :username OR email = :email"),
                {"username": username, "email": email}
            ).fetchone()
            
            if existing_user:
                logger.warning(f"Attempt to create duplicate user: {username}")
                return False
            
            # Create user with parameterized query
            db.execute(
                text("""
                    INSERT INTO User_IAM 
                    (username, email, password, salt, admin_role, force_password_change, failed_login_attempts, created_time) 
                    VALUES (:username, :email, :password, :salt, 0, 0, 0, NOW())
                """),
                {
                    "username": username,
                    "email": email,
                    "password": password_hash,
                    "salt": salt
                }
            )
            db.commit()
            
            logger.info(f"User created successfully: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def update_password(db: Session, username: str, password_hash: str, salt: str) -> bool:
        """Securely update user password"""
        try:
            # Validate username
            is_valid, _ = SecurityValidators.validate_username(username)
            if not is_valid:
                return False
            
            db.execute(
                text("""
                    UPDATE User_IAM 
                    SET password = :password, salt = :salt, force_password_change = 0, password_changed_time = NOW()
                    WHERE username = :username
                """),
                {
                    "password": password_hash,
                    "salt": salt,
                    "username": username
                }
            )
            db.commit()
            
            logger.info(f"Password updated for user: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def set_session_token(db: Session, username: str, session_token: str, expiry_time: datetime) -> bool:
        """Securely set session token"""
        try:
            db.execute(
                text("""
                    UPDATE User_IAM 
                    SET session_token = :session_token, session_token_expiry = :expiry_time, last_login_time = NOW()
                    WHERE username = :username
                """),
                {
                    "session_token": session_token,
                    "expiry_time": expiry_time,
                    "username": username
                }
            )
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error setting session token: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def clear_session_token(db: Session, username: str) -> bool:
        """Securely clear session token"""
        try:
            db.execute(
                text("UPDATE User_IAM SET session_token = NULL, session_token_expiry = NULL WHERE username = :username"),
                {"username": username}
            )
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error clearing session token: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def record_failed_login(db: Session, username: str) -> bool:
        """Record failed login attempt"""
        try:
            db.execute(
                text("""
                    UPDATE User_IAM 
                    SET failed_login_attempts = failed_login_attempts + 1, last_login_attempt = NOW()
                    WHERE username = :username
                """),
                {"username": username}
            )
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error recording failed login: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def reset_failed_login_attempts(db: Session, username: str) -> bool:
        """Reset failed login attempts after successful login"""
        try:
            db.execute(
                text("UPDATE User_IAM SET failed_login_attempts = 0 WHERE username = :username"),
                {"username": username}
            )
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error resetting failed login attempts: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def assign_admin_role(db: Session, username: str) -> bool:
        """Securely assign admin role"""
        try:
            # Validate username
            is_valid, _ = SecurityValidators.validate_username(username)
            if not is_valid:
                return False
            
            # Check if user exists
            user = SecureDBOperations.get_user_by_username(db, username)
            if not user:
                return False
            
            # Update admin role
            db.execute(
                text("UPDATE User_IAM SET admin_role = 1 WHERE username = :username"),
                {"username": username}
            )
            db.commit()
            
            logger.info(f"Admin role assigned to user: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning admin role: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def revoke_admin_role(db: Session, username: str) -> bool:
        """Securely revoke admin role"""
        try:
            # Validate username
            is_valid, _ = SecurityValidators.validate_username(username)
            if not is_valid:
                return False
            
            # Check if user exists
            user = SecureDBOperations.get_user_by_username(db, username)
            if not user:
                return False
            
            # Check if this is the last admin
            admin_count = db.execute(
                text("SELECT COUNT(*) FROM User_IAM WHERE admin_role = 1")
            ).fetchone()[0]
            
            if admin_count <= 1:
                logger.warning("Cannot revoke admin role from last admin user")
                return False
            
            # Update admin role
            db.execute(
                text("UPDATE User_IAM SET admin_role = 0 WHERE username = :username"),
                {"username": username}
            )
            db.commit()
            
            logger.info(f"Admin role revoked from user: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking admin role: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def get_admin_users(db: Session) -> List[Dict[str, Any]]:
        """Get list of admin users"""
        try:
            results = db.execute(
                text("SELECT user_id, username, email, created_time FROM User_IAM WHERE admin_role = 1 ORDER BY username")
            ).fetchall()
            
            return [
                {
                    "user_id": result[0],
                    "username": result[1],
                    "email": result[2],
                    "created_time": result[3]
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting admin users: {e}")
            return []
    
    @staticmethod
    def get_user_entries(db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Get user entries securely"""
        try:
            # Validate user_id
            if not isinstance(user_id, int) or user_id <= 0:
                return []
            
            results = db.execute(
                text("""
                    SELECT e.entry_id, e.entry_name, e.active_status, e.current_week, e.weekly_total, e.season_total
                    FROM Entries e
                    WHERE e.user_id = :user_id
                    ORDER BY e.entry_name
                """),
                {"user_id": user_id}
            ).fetchall()
            
            return [
                {
                    "entry_id": result[0],
                    "entry_name": result[1],
                    "active_status": result[2],
                    "current_week": result[3],
                    "weekly_total": result[4],
                    "season_total": result[5]
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting user entries: {e}")
            return []
    
    @staticmethod
    def get_user_picks(db: Session, entry_id: int, week: int, user_id: int) -> List[Dict[str, Any]]:
        """Get user picks securely with authorization check"""
        try:
            # Validate inputs
            week_valid, week_num = InputSanitizer.validate_week_number(str(week))
            if not week_valid or not isinstance(entry_id, int) or entry_id <= 0:
                return []
            
            # Verify entry belongs to user (authorization check)
            entry_check = db.execute(
                text("SELECT user_id FROM Entries WHERE entry_id = :entry_id"),
                {"entry_id": entry_id}
            ).fetchone()
            
            if not entry_check or entry_check[0] != user_id:
                logger.warning(f"Unauthorized access attempt to entry {entry_id} by user {user_id}")
                return []
            
            # Get picks
            results = db.execute(
                text("""
                    SELECT p.pick_id, p.game_id, p.team_id, p.result, t.team_name, t.team_abbreviation
                    FROM Picks p
                    LEFT JOIN Teams t ON p.team_id = t.team_id
                    WHERE p.entry_id = :entry_id AND p.week_num = :week
                    ORDER BY p.game_id
                """),
                {"entry_id": entry_id, "week": week_num}
            ).fetchall()
            
            return [
                {
                    "pick_id": result[0],
                    "game_id": result[1],
                    "team_id": result[2],
                    "result": result[3],
                    "team_name": result[4],
                    "team_abbreviation": result[5]
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting user picks: {e}")
            return []
    
    @staticmethod
    def create_entry(db: Session, user_id: int, entry_name: str) -> Optional[int]:
        """Securely create new entry"""
        try:
            # Validate inputs
            if not isinstance(user_id, int) or user_id <= 0:
                return None
            
            # Sanitize entry name
            entry_name = SecurityValidators.sanitize_input(entry_name)
            if not entry_name or len(entry_name) > 100:
                return None
            
            # Check if user already has an entry with this name
            existing = db.execute(
                text("SELECT entry_id FROM Entries WHERE user_id = :user_id AND entry_name = :entry_name"),
                {"user_id": user_id, "entry_name": entry_name}
            ).fetchone()
            
            if existing:
                logger.warning(f"User {user_id} attempted to create duplicate entry: {entry_name}")
                return None
            
            # Create entry
            result = db.execute(
                text("""
                    INSERT INTO Entries (user_id, entry_name, active_status, current_week, weekly_total, season_total)
                    VALUES (:user_id, :entry_name, 1, 1, 0, 0)
                """),
                {"user_id": user_id, "entry_name": entry_name}
            )
            
            entry_id = result.lastrowid
            db.commit()
            
            logger.info(f"Entry created: {entry_name} for user {user_id}")
            return entry_id
            
        except Exception as e:
            logger.error(f"Error creating entry: {e}")
            db.rollback()
            return None
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address securely"""
        try:
            result = db.execute(
                text("SELECT user_id, username, email, password, salt, admin_role, force_password_change, failed_login_attempts, last_login_attempt, created_time FROM User_IAM WHERE email = :email"),
                {"email": email}
            ).fetchone()
            
            if result:
                return {
                    "user_id": result[0],
                    "username": result[1],
                    "email": result[2],
                    "password": result[3],
                    "salt": result[4],
                    "admin_role": result[5],
                    "force_password_change": result[6],
                    "failed_login_attempts": result[7],
                    "last_login_attempt": result[8],
                    "created_time": result[9]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user with username and password"""
        from security_config import PasswordSecurity
        
        try:
            # Get user data
            user_data = SecureDBOperations.get_user_by_username(db, username)
            if not user_data:
                return {"success": False, "reason": "user_not_found"}
            
            # Check if account is locked
            if user_data.get("failed_login_attempts", 0) >= 5:
                return {"success": False, "reason": "account_locked"}
            
            # Verify password
            stored_password = user_data.get("password")
            stored_salt = user_data.get("salt")
            
            if stored_password and stored_salt and PasswordSecurity.verify_password(password, stored_password, stored_salt):
                # Reset failed login attempts on successful login
                SecureDBOperations.reset_failed_login_attempts(db, username)
                return {"success": True, "user": user_data}
            else:
                # Record failed login attempt
                SecureDBOperations.record_failed_login(db, username)
                return {"success": False, "reason": "invalid_password"}
                
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return {"success": False, "reason": "authentication_error"}
    
    @staticmethod
    def update_user_session(db: Session, username: str, session_token: str) -> bool:
        """Update user session token"""
        from datetime import datetime, timedelta
        from security_config import SecurityConfig
        
        try:
            # Calculate expiry time
            expiry_time = datetime.now(timezone.utc) + timedelta(hours=SecurityConfig.SESSION_TIMEOUT_HOURS)
            
            db.execute(
                text("UPDATE User_IAM SET session_token = :session_token, session_token_expiry = :expiry_time, last_logged_in_time = NOW() WHERE username = :username"),
                {
                    "session_token": session_token,
                    "expiry_time": expiry_time,
                    "username": username
                }
            )
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating user session: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def clear_user_session(db: Session, username: str) -> bool:
        """Clear user session token"""
        try:
            db.execute(
                text("UPDATE User_IAM SET session_token = NULL, session_token_expiry = NULL WHERE username = :username"),
                {"username": username}
            )
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error clearing user session: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def update_user_password(db: Session, username: str, new_password: str) -> bool:
        """Update user password securely"""
        from security_config import PasswordSecurity
        
        try:
            # Hash the new password with salt
            hashed_password = PasswordSecurity.hash_password(new_password)
            
            db.execute(
                text("UPDATE User_IAM SET password = :password, force_password_change = 0, password_changed_time = NOW() WHERE username = :username"),
                {
                    "password": hashed_password,
                    "username": username
                }
            )
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating user password: {e}")
            db.rollback()
            return False
