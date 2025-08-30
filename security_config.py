"""
OWASP Top 10 Security Configuration for Run My Pool Application
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import hmac
import re
from dataclasses import dataclass


@dataclass
class SecurityConfig:
    """Security configuration settings"""
    
    # Session Security
    SESSION_TIMEOUT_HOURS: int = 24
    SESSION_TOKEN_LENGTH: int = 32
    SECURE_COOKIES: bool = True
    HTTPONLY_COOKIES: bool = True
    SAMESITE_COOKIES: str = "strict"
    
    # Password Security
    MIN_PASSWORD_LENGTH: int = 12
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_LOWERCASE: bool = True
    REQUIRE_NUMBERS: bool = True
    REQUIRE_SPECIAL_CHARS: bool = True
    PASSWORD_HISTORY_COUNT: int = 5
    PASSWORD_EXPIRY_DAYS: int = 90
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30
    
    # Rate Limiting
    LOGIN_RATE_LIMIT: int = 5  # attempts per minute
    API_RATE_LIMIT: int = 100  # requests per minute
    
    # Input Validation
    MAX_USERNAME_LENGTH: int = 50
    MAX_EMAIL_LENGTH: int = 255
    MAX_ENTRY_NAME_LENGTH: int = 100
    
    # Security Headers
    ENABLE_HSTS: bool = True
    ENABLE_CSP: bool = True
    ENABLE_X_FRAME_OPTIONS: bool = True
    ENABLE_X_CONTENT_TYPE_OPTIONS: bool = True
    
    # Encryption
    BCRYPT_ROUNDS: int = 12
    
    @classmethod
    def get_secret_key(cls) -> str:
        """Get or generate secret key"""
        secret_key = os.getenv("SECRET_KEY")
        if not secret_key:
            # Generate a secure random key
            secret_key = secrets.token_urlsafe(32)
            print(f"WARNING: Generated new secret key. Set SECRET_KEY environment variable to: {secret_key}")
        return secret_key
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL with security validation"""
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Validate database URL format
        if not any(db_type in db_url for db_type in ["mysql://", "postgresql://", "sqlite:///"]):
            raise ValueError("Invalid database URL format")
        
        return db_url
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production"""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"


class SecurityValidators:
    """Security validation utilities"""
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """Validate password strength"""
        config = SecurityConfig()
        
        if len(password) < config.MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters long"
        
        if config.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if config.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if config.REQUIRE_NUMBERS and not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        if config.REQUIRE_SPECIAL_CHARS and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        # Check for common weak passwords
        weak_patterns = [
            r'password', r'123456', r'qwerty', r'admin', r'letmein',
            r'welcome', r'monkey', r'dragon', r'master', r'login'
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, password.lower()):
                return False, "Password contains common weak patterns"
        
        return True, "Password is valid"
    
    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """Validate username format"""
        config = SecurityConfig()
        
        if not username:
            return False, "Username cannot be empty"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > config.MAX_USERNAME_LENGTH:
            return False, f"Username cannot exceed {config.MAX_USERNAME_LENGTH} characters"
        
        # Allow alphanumeric and underscores only
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        # Prevent reserved usernames
        reserved = ['admin', 'root', 'system', 'guest', 'user', 'test', 'demo']
        if username.lower() in reserved:
            return False, "Username is reserved"
        
        return True, "Username is valid"
    
    @staticmethod
    def validate_email(email: str) -> tuple[bool, str]:
        """Validate email format"""
        config = SecurityConfig()
        
        if not email:
            return False, "Email cannot be empty"
        
        if len(email) > config.MAX_EMAIL_LENGTH:
            return False, f"Email cannot exceed {config.MAX_EMAIL_LENGTH} characters"
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "Invalid email format"
        
        return True, "Email is valid"
    
    @staticmethod
    def validate_login_input(username: str, password: str) -> Optional[str]:
        """Validate login input parameters"""
        # Validate username
        is_valid, error = SecurityValidators.validate_username(username)
        if not is_valid:
            return error
        
        # Basic password validation
        if not password:
            return "Password cannot be empty"
        
        if len(password) > 256:
            return "Password too long"
        
        return None
    
    @staticmethod
    def validate_password_input(username: str, current_password: str, new_password: str, confirm_password: str) -> Optional[str]:
        """Validate password change input parameters"""
        # Validate username
        is_valid, error = SecurityValidators.validate_username(username)
        if not is_valid:
            return error
        
        # Validate current password
        if not current_password:
            return "Current password cannot be empty"
        
        # Validate new password
        is_valid, error = SecurityValidators.validate_password(new_password)
        if not is_valid:
            return error
        
        # Check password confirmation
        if new_password != confirm_password:
            return "Passwords do not match"
        
        return None
    
    @staticmethod
    def validate_user_creation_input(username: str, email: str, password: str, confirm_password: str) -> Optional[str]:
        """Validate user creation input parameters"""
        # Validate username
        is_valid, error = SecurityValidators.validate_username(username)
        if not is_valid:
            return error
        
        # Validate email
        is_valid, error = SecurityValidators.validate_email(email)
        if not is_valid:
            return error
        
        # Validate password
        is_valid, error = SecurityValidators.validate_password(password)
        if not is_valid:
            return error
        
        # Check password confirmation
        if password != confirm_password:
            return "Passwords do not match"
        
        return None
    
    @staticmethod
    def validate_password_reset_input(username: str, token: str, new_password: str) -> Optional[str]:
        """Validate password reset input parameters"""
        # Validate username
        is_valid, error = SecurityValidators.validate_username(username)
        if not is_valid:
            return error
        
        # Validate token
        if not token or len(token) < 32:
            return "Invalid reset token"
        
        # Validate new password
        is_valid, error = SecurityValidators.validate_password(new_password)
        if not is_valid:
            return error
        
        return None
    
    @staticmethod
    def sanitize_search_input(query: str) -> str:
        """Sanitize search input to prevent injection"""
        if not query:
            return ""
        
        # Remove special characters that could be used for injection
        sanitized = re.sub(r'[<>"\';\\]', '', query)
        
        # Limit length
        sanitized = sanitized[:100]
        
        return sanitized.strip()
    
    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """Sanitize user input to prevent XSS"""
        if not input_str:
            return ""
        
        # Remove potential XSS characters
        sanitized = re.sub(r'[<>"\']', '', input_str)
        
        # Limit length
        sanitized = sanitized[:1000]
        
        return sanitized.strip()


class PasswordSecurity:
    """Password hashing and validation utilities"""
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash password with salt using PBKDF2"""
        import hashlib
        
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Use PBKDF2 with SHA-256
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100,000 iterations
        )
        
        return password_hash.hex(), salt
    
    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """Verify password against hash"""
        computed_hash, _ = PasswordSecurity.hash_password(password, salt)
        return hmac.compare_digest(computed_hash, hashed_password)
    
    @staticmethod
    def generate_secure_token() -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(32)


class SessionSecurity:
    """Session management utilities"""
    
    @staticmethod
    def create_session_token(user_id: int, username: str) -> str:
        """Create secure session token"""
        timestamp = datetime.utcnow().isoformat()
        data = f"{user_id}:{username}:{timestamp}"
        
        # Sign the session data
        secret_key = SecurityConfig.get_secret_key()
        signature = hmac.new(
            secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        session_data = f"{data}:{signature}"
        return secrets.token_urlsafe(32)  # Return random token for database lookup
    
    @staticmethod
    def validate_session_token(token: str, expected_user_id: int) -> bool:
        """Validate session token"""
        if not token or len(token) < 32:
            return False
        
        # Additional validation logic would go here
        # For now, just check token format
        return True
    
    @staticmethod
    def is_session_expired(created_time: datetime) -> bool:
        """Check if session is expired"""
        if not created_time:
            return True
        
        expiry_time = created_time + timedelta(hours=SecurityConfig.SESSION_TIMEOUT_HOURS)
        return datetime.utcnow() > expiry_time
    
    @staticmethod
    def create_session_cookie(username: str, session_token: str) -> str:
        """Create a secure session cookie value"""
        if not username or not session_token:
            raise ValueError("Username and session_token are required")
        
        # Create session data with timestamp for additional security
        # Use | as separator to avoid conflicts with : in timestamps
        timestamp = datetime.utcnow().isoformat()
        session_data = f"{username}|{session_token}|{timestamp}"
        
        # Encode the session data
        import base64
        return base64.b64encode(session_data.encode()).decode()
    
    @staticmethod
    def validate_session_cookie(session_cookie: str) -> dict:
        """Validate and decode session cookie"""
        if not session_cookie:
            return None
        
        try:
            import base64
            # Decode the base64 session cookie
            decoded_session = base64.b64decode(session_cookie).decode()
            # Session format: username|session_token|timestamp
            parts = decoded_session.split('|')
            if len(parts) != 3:
                return None
            
            username, session_token, timestamp = parts
            
            # Return the session data
            return {
                "username": username,
                "session_token": session_token,
                "timestamp": timestamp
            }
        except (ValueError, UnicodeDecodeError):
            return None


class SecurityHeaders:
    """Security headers configuration"""
    
    @staticmethod
    def get_security_headers() -> dict:
        """Get security headers"""
        config = SecurityConfig()
        headers = {}
        
        if config.ENABLE_HSTS:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        if config.ENABLE_CSP:
            headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
        
        if config.ENABLE_X_FRAME_OPTIONS:
            headers["X-Frame-Options"] = "DENY"
        
        if config.ENABLE_X_CONTENT_TYPE_OPTIONS:
            headers["X-Content-Type-Options"] = "nosniff"
        
        headers["X-XSS-Protection"] = "1; mode=block"
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return headers


class InputSanitizer:
    """Input sanitization and validation"""
    
    @staticmethod
    def sanitize_sql_input(value: str) -> str:
        """Sanitize input to prevent SQL injection"""
        if not value:
            return ""
        
        # Remove common SQL injection characters
        dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]
        sanitized = value
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")
        
        return sanitized.strip()
    
    @staticmethod
    def validate_integer(value: str, min_val: int = None, max_val: int = None) -> tuple[bool, Optional[int]]:
        """Validate and convert integer input"""
        try:
            int_val = int(value)
            
            if min_val is not None and int_val < min_val:
                return False, None
            
            if max_val is not None and int_val > max_val:
                return False, None
            
            return True, int_val
        except (ValueError, TypeError):
            return False, None
    
    @staticmethod
    def validate_week_number(week: str) -> tuple[bool, Optional[int]]:
        """Validate NFL week number"""
        is_valid, week_num = InputSanitizer.validate_integer(week, 1, 18)
        return is_valid, week_num


class AuditLogger:
    """Security audit logging"""
    
    @staticmethod
    def log_security_event(event_type: str, user_id: Optional[int], ip_address: str, details: str = ""):
        """Log security events"""
        import logging
        
        security_logger = logging.getLogger("security")
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details
        }
        
        security_logger.warning(f"SECURITY_EVENT: {log_data}")
    
    @staticmethod
    def log_login_attempt(username: str, ip_address: str, success: bool, reason: str = ""):
        """Log login attempts"""
        event_type = "LOGIN_SUCCESS" if success else "LOGIN_FAILURE"
        details = f"username={username}, reason={reason}"
        
        AuditLogger.log_security_event(event_type, None, ip_address, details)
    
    @staticmethod
    def log_admin_action(user_id: int, action: str, target: str, ip_address: str):
        """Log admin actions"""
        details = f"action={action}, target={target}"
        AuditLogger.log_security_event("ADMIN_ACTION", user_id, ip_address, details)


class RateLimiter:
    """Rate limiting implementation"""
    
    def __init__(self):
        self.attempts = {}
        self.lockouts = {}
    
    def is_rate_limited(self, key: str, limit: int, window_minutes: int = 1) -> bool:
        """Check if key is rate limited"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        
        # Clean old attempts
        if key in self.attempts:
            self.attempts[key] = [
                attempt for attempt in self.attempts[key]
                if attempt > window_start
            ]
        else:
            self.attempts[key] = []
        
        # Check if over limit
        return len(self.attempts[key]) >= limit
    
    def record_attempt(self, key: str):
        """Record an attempt"""
        if key not in self.attempts:
            self.attempts[key] = []
        
        self.attempts[key].append(datetime.utcnow())
    
    def is_locked_out(self, key: str) -> bool:
        """Check if key is locked out"""
        if key not in self.lockouts:
            return False
        
        lockout_end = self.lockouts[key] + timedelta(minutes=SecurityConfig.LOCKOUT_DURATION_MINUTES)
        return datetime.utcnow() < lockout_end
    
    def lockout(self, key: str):
        """Lock out a key"""
        self.lockouts[key] = datetime.utcnow()
    
    def clear_all(self):
        """Clear all rate limiting data - for development use only"""
        self.attempts.clear()
        self.lockouts.clear()
    
    def _record_failed_attempt_internal(self, key: str, action: str):
        """Record a failed attempt for rate limiting"""
        rate_limit_key = f"{key}:{action}"
        self.record_attempt(rate_limit_key)
        
        # Check if we should lock out after too many attempts
        if self.is_rate_limited(rate_limit_key, SecurityConfig.MAX_LOGIN_ATTEMPTS, SecurityConfig.LOCKOUT_DURATION_MINUTES):
            self.lockout(rate_limit_key)
    
    @classmethod
    def is_user_rate_limited(cls, key: str, action: str) -> bool:
        """Class method wrapper for user rate limiting check"""
        rate_limit_key = f"{key}:{action}"
        return rate_limiter.is_rate_limited(rate_limit_key, SecurityConfig.MAX_LOGIN_ATTEMPTS, SecurityConfig.LOCKOUT_DURATION_MINUTES)
    
    @classmethod
    def record_user_failed_attempt(cls, key: str, action: str):
        """Class method wrapper for recording failed attempts"""
        rate_limiter._record_failed_attempt_internal(key, action)
    
    def clear_rate_limit(self, key: str):
        """Clear rate limiting for a specific key"""
        if key in self.attempts:
            del self.attempts[key]
        if key in self.lockouts:
            del self.lockouts[key]
    
    def clear_all_rate_limits(self):
        """Clear all rate limits and lockouts"""
        self.attempts.clear()
        self.lockouts.clear()


# Global rate limiter instance
rate_limiter = RateLimiter()
