"""
Security middleware for the Run My Pool application
Implements security headers, rate limiting, input validation, and CSRF protection
"""

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
import time
import logging
import os
from typing import Dict, Optional
from datetime import datetime, timedelta
import hashlib
import secrets
import re
from security_config import SecurityConfig, SecurityHeaders, AuditLogger, rate_limiter

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        security_headers = SecurityHeaders.get_security_headers()
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # Add CORS headers if needed
        if SecurityConfig.is_production():
            response.headers["Access-Control-Allow-Origin"] = "https://yourdomain.com"
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.login_endpoints = ["/login", "/create-user", "/change-password"]
        self.api_endpoints = ["/api/", "/admin/"]
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers first (if behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return "unknown"
    
    async def dispatch(self, request: Request, call_next):
        client_ip = self.get_client_ip(request)
        path = request.url.path
        
        # Check if rate limiting is enabled
        rate_limit_enabled = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
        
        # Check for login endpoint rate limiting
        if rate_limit_enabled and any(endpoint in path for endpoint in self.login_endpoints):
            rate_key = f"login:{client_ip}"
            
            if rate_limiter.is_locked_out(rate_key):
                AuditLogger.log_security_event("RATE_LIMIT_LOCKOUT", None, client_ip, f"path={path}")
                raise HTTPException(
                    status_code=429,
                    detail="Too many failed attempts. Please try again later."
                )
            
            if rate_limiter.is_rate_limited(rate_key, SecurityConfig.LOGIN_RATE_LIMIT, 1):
                rate_limiter.lockout(rate_key)
                AuditLogger.log_security_event("RATE_LIMIT_EXCEEDED", None, client_ip, f"path={path}")
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later."
                )
            
            rate_limiter.record_attempt(rate_key)
        
        # Check for API endpoint rate limiting
        elif rate_limit_enabled and any(endpoint in path for endpoint in self.api_endpoints):
            rate_key = f"api:{client_ip}"
            
            if rate_limiter.is_rate_limited(rate_key, SecurityConfig.API_RATE_LIMIT, 1):
                AuditLogger.log_security_event("API_RATE_LIMIT_EXCEEDED", None, client_ip, f"path={path}")
                raise HTTPException(
                    status_code=429,
                    detail="API rate limit exceeded."
                )
            
            rate_limiter.record_attempt(rate_key)
        
        response = await call_next(request)
        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Input validation and sanitization middleware"""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.dangerous_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'eval\s*\(',
            r'expression\s*\(',
            r'url\s*\(',
            r'<iframe',
            r'<object',
            r'<embed',
            r'<link',
            r'<meta',
            r'<style',
        ]
    
    def detect_xss(self, text: str) -> bool:
        """Detect potential XSS attacks"""
        if not text:
            return False
        
        text_lower = text.lower()
        for pattern in self.dangerous_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def detect_sql_injection(self, text: str) -> bool:
        """Detect potential SQL injection attacks"""
        if not text:
            return False
        
        sql_patterns = [
            r"'\s*or\s*'",
            r"'\s*and\s*'",
            r"'\s*union\s*",
            r"'\s*select\s*",
            r"'\s*insert\s*",
            r"'\s*update\s*",
            r"'\s*delete\s*",
            r"'\s*drop\s*",
            r"--",
            r"/\*",
            r"\*/",
            r"xp_",
            r"sp_",
        ]
        
        text_lower = text.lower()
        for pattern in sql_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        client_ip = self.get_client_ip(request)
        
        # Check query parameters
        for param, value in request.query_params.items():
            if isinstance(value, str):
                if self.detect_xss(value):
                    AuditLogger.log_security_event("XSS_ATTEMPT", None, client_ip, f"param={param}, value={value}")
                    raise HTTPException(status_code=400, detail="Invalid input detected")
                
                if self.detect_sql_injection(value):
                    AuditLogger.log_security_event("SQL_INJECTION_ATTEMPT", None, client_ip, f"param={param}, value={value}")
                    raise HTTPException(status_code=400, detail="Invalid input detected")
        
        # Check form data for POST requests
        if request.method == "POST":
            try:
                content_type = request.headers.get("content-type", "")
                
                if "application/x-www-form-urlencoded" in content_type:
                    # This is a simplified check - in production you'd want more sophisticated validation
                    body = await request.body()
                    body_str = body.decode('utf-8')
                    
                    if self.detect_xss(body_str):
                        AuditLogger.log_security_event("XSS_ATTEMPT", None, client_ip, f"body={body_str[:100]}")
                        raise HTTPException(status_code=400, detail="Invalid input detected")
                    
                    if self.detect_sql_injection(body_str):
                        AuditLogger.log_security_event("SQL_INJECTION_ATTEMPT", None, client_ip, f"body={body_str[:100]}")
                        raise HTTPException(status_code=400, detail="Invalid input detected")
                    
                    # Re-create request with body for next middleware
                    async def receive():
                        return {"type": "http.request", "body": body}
                    request._receive = receive
                    
            except Exception as e:
                logger.error(f"Error validating input: {e}")
        
        response = await call_next(request)
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return "unknown"


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware"""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.csrf_tokens = {}  # In production, use Redis or database
        self.protected_methods = ["POST", "PUT", "DELETE"]
        self.excluded_paths = ["/api/", "/login", "/logout"]  # API endpoints might use different CSRF protection
    
    def generate_csrf_token(self, session_id: str) -> str:
        """Generate CSRF token for session"""
        token = secrets.token_urlsafe(32)
        self.csrf_tokens[session_id] = {
            "token": token,
            "created": datetime.utcnow()
        }
        return token
    
    def validate_csrf_token(self, session_id: str, token: str) -> bool:
        """Validate CSRF token"""
        if session_id not in self.csrf_tokens:
            return False
        
        stored_data = self.csrf_tokens[session_id]
        
        # Check if token is expired (1 hour)
        if datetime.utcnow() - stored_data["created"] > timedelta(hours=1):
            del self.csrf_tokens[session_id]
            return False
        
        return stored_data["token"] == token
    
    async def dispatch(self, request: Request, call_next):
        client_ip = self.get_client_ip(request)
        path = request.url.path
        
        # Skip CSRF protection for excluded paths and safe methods
        if (request.method not in self.protected_methods or 
            any(excluded in path for excluded in self.excluded_paths)):
            response = await call_next(request)
            return response
        
        # Get session ID from cookie
        session_cookie = request.cookies.get("session-token")
        if not session_cookie:
            response = await call_next(request)
            return response
        
        # Check for CSRF token in form data or headers
        csrf_token = None
        
        # Check header first
        csrf_token = request.headers.get("X-CSRF-Token")
        
        # If not in header, check form data
        if not csrf_token and request.method == "POST":
            try:
                content_type = request.headers.get("content-type", "")
                if "application/x-www-form-urlencoded" in content_type:
                    form_data = await request.form()
                    csrf_token = form_data.get("csrf_token")
            except:
                pass
        
        # Validate CSRF token
        if not csrf_token or not self.validate_csrf_token(session_cookie, csrf_token):
            AuditLogger.log_security_event("CSRF_ATTACK_ATTEMPT", None, client_ip, f"path={path}")
            raise HTTPException(status_code=403, detail="CSRF token validation failed")
        
        response = await call_next(request)
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return "unknown"


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """Security logging middleware"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = self.get_client_ip(request)
        
        # Log request
        logger.info(f"REQUEST: {request.method} {request.url.path} from {client_ip}")
        
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(f"RESPONSE: {response.status_code} in {process_time:.3f}s")
            
            # Log security events
            if response.status_code in [401, 403, 429]:
                AuditLogger.log_security_event(
                    f"HTTP_{response.status_code}",
                    None,
                    client_ip,
                    f"path={request.url.path}, method={request.method}"
                )
            
            return response
            
        except Exception as e:
            # Log exceptions
            process_time = time.time() - start_time
            logger.error(f"EXCEPTION: {str(e)} in {process_time:.3f}s from {client_ip}")
            
            AuditLogger.log_security_event(
                "EXCEPTION",
                None,
                client_ip,
                f"path={request.url.path}, error={str(e)}"
            )
            
            raise
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return "unknown"


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP to HTTPS in production"""
    
    async def dispatch(self, request: Request, call_next):
        # Only redirect in production
        if SecurityConfig.is_production():
            if request.url.scheme != "https":
                https_url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(https_url), status_code=301)
        
        response = await call_next(request)
        return response


def setup_security_middleware(app: FastAPI):
    """Setup all security middleware"""
    
    # Add security middleware in order of execution
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(SecurityLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(InputValidationMiddleware)
    # Note: CSRF middleware disabled by default as it requires frontend integration
    # app.add_middleware(CSRFProtectionMiddleware)
    
    logger.info("Security middleware configured successfully")


class SecurityUtils:
    """Security utility functions"""
    
    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Get client IP address from request"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return "unknown"
    
    @staticmethod
    def is_safe_redirect_url(url: str, allowed_hosts: list = None) -> bool:
        """Check if redirect URL is safe"""
        if not url:
            return False
        
        # Prevent open redirects
        if url.startswith("http://") or url.startswith("https://"):
            if allowed_hosts:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                return parsed.netloc in allowed_hosts
            return False
        
        # Allow relative URLs that don't start with //
        if url.startswith("//"):
            return False
        
        # Allow relative paths
        if url.startswith("/"):
            return True
        
        return False
    
    @staticmethod
    def generate_nonce() -> str:
        """Generate cryptographic nonce"""
        return secrets.token_urlsafe(16)
    
    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """Hash sensitive data for logging"""
        return hashlib.sha256(data.encode()).hexdigest()[:8] + "..."
