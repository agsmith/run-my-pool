#!/usr/bin/env python3
"""
Simple test runner to validate security updates
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_password_security():
    """Test password security functionality"""
    print("🔐 Testing Password Security...")
    
    from security_config import PasswordSecurity
    
    # Test password hashing
    password = "TestPassword123!"
    hashed_password, salt = PasswordSecurity.hash_password(password)
    
    assert len(hashed_password) > 0, "Password hash should not be empty"
    assert len(salt) > 0, "Salt should not be empty"
    assert hashed_password != password, "Password should be hashed"
    
    # Test password verification
    is_valid = PasswordSecurity.verify_password(password, hashed_password, salt)
    assert is_valid, "Valid password should verify"
    
    is_invalid = PasswordSecurity.verify_password("WrongPassword", hashed_password, salt)
    assert not is_invalid, "Invalid password should not verify"
    
    # Test token generation
    token = PasswordSecurity.generate_secure_token()
    assert len(token) >= 32, "Token should be at least 32 characters"
    
    print("✅ Password Security tests passed")


def test_input_validation():
    """Test input validation functionality"""
    print("🔍 Testing Input Validation...")
    
    from security_config import SecurityValidators
    
    # Test username validation
    valid_usernames = ["testuser", "user123", "test_user"]
    for username in valid_usernames:
        is_valid, message = SecurityValidators.validate_username(username)
        assert is_valid, f"Username '{username}' should be valid, got: {message}"
    
    invalid_usernames = ["", "ab", "user@domain", "a" * 100]
    for username in invalid_usernames:
        is_valid, message = SecurityValidators.validate_username(username)
        assert not is_valid, f"Username '{username}' should be invalid"
    
    # Test email validation
    valid_emails = ["test@example.com", "user.name@domain.co.uk"]
    for email in valid_emails:
        is_valid, message = SecurityValidators.validate_email(email)
        assert is_valid, f"Email '{email}' should be valid, got: {message}"
    
    invalid_emails = ["", "notanemail", "@domain.com", "user@"]
    for email in invalid_emails:
        is_valid, message = SecurityValidators.validate_email(email)
        assert not is_valid, f"Email '{email}' should be invalid"
    
    # Test password validation
    valid_passwords = ["ComplexPass123!", "MyVerySecure@Pass99", "Strong$Passwd1"]
    for password in valid_passwords:
        is_valid, message = SecurityValidators.validate_password(password)
        assert is_valid, f"Password '{password}' should be valid, got: {message}"
    
    invalid_passwords = ["", "short", "password123", "PASSWORD123"]
    for password in invalid_passwords:
        is_valid, message = SecurityValidators.validate_password(password)
        assert not is_valid, f"Password should be invalid"
    
    print("✅ Input Validation tests passed")


def test_session_security():
    """Test session security functionality"""
    print("🔒 Testing Session Security...")
    
    from security_config import SessionSecurity
    import base64
    
    # Test session token creation
    user_id = 123
    username = "testuser"
    token = SessionSecurity.create_session_token(user_id, username)
    assert len(token) >= 32, "Session token should be at least 32 characters"
    
    # Test session cookie creation
    session_token = "test_token_123"
    cookie = SessionSecurity.create_session_cookie(username, session_token)
    assert len(cookie) > 0, "Session cookie should not be empty"
    
    # Test session cookie validation
    result = SessionSecurity.validate_session_cookie(cookie)
    assert result is not None, "Valid cookie should parse successfully"
    assert result["username"] == username, "Username should match"
    assert result["session_token"] == session_token, "Session token should match"
    
    # Test invalid cookie
    invalid_result = SessionSecurity.validate_session_cookie("invalid_cookie")
    assert invalid_result is None, "Invalid cookie should return None"
    
    print("✅ Session Security tests passed")


def test_rate_limiting():
    """Test rate limiting functionality"""
    print("🚦 Testing Rate Limiting...")
    
    from security_config import RateLimiter
    
    rate_limiter = RateLimiter()
    key = "test_key"
    limit = 3
    
    # Test within limit
    for i in range(limit - 1):
        rate_limiter.record_attempt(key)
        is_limited = rate_limiter.is_rate_limited(key, limit, 1)
        assert not is_limited, f"Should not be rate limited at attempt {i+1}"
    
    # Test over limit
    rate_limiter.record_attempt(key)
    is_limited = rate_limiter.is_rate_limited(key, limit, 1)
    assert is_limited, "Should be rate limited after exceeding limit"
    
    # Test lockout
    lockout_key = "lockout_test"
    assert not rate_limiter.is_locked_out(lockout_key), "Should not be locked out initially"
    
    rate_limiter.lockout(lockout_key)
    assert rate_limiter.is_locked_out(lockout_key), "Should be locked out after lockout()"
    
    # Test clearing rate limits
    rate_limiter.clear_rate_limit(key)
    is_limited = rate_limiter.is_rate_limited(key, limit, 1)
    assert not is_limited, "Should not be rate limited after clearing"
    
    print("✅ Rate Limiting tests passed")


def test_database_integration():
    """Test database integration with security features"""
    print("🗄️ Testing Database Integration...")
    
    from database import SessionLocal
    from models import User_IAM
    from security_config import PasswordSecurity
    
    db = SessionLocal()
    try:
        # Test creating user with secure password
        from datetime import datetime
        hashed_password, salt = PasswordSecurity.hash_password("TestPassword123!")
        
        test_user = User_IAM(
            username="test_security_user",
            password=hashed_password,
            salt=salt,
            email="test@security.com",
            admin_role=False,
            failed_login_attempts=0,
            account_locked=False,
            account_created_time=datetime.utcnow(),  # Required field
            force_password_change=False
        )
        
        # Clean up any existing test user
        existing = db.query(User_IAM).filter(User_IAM.username == "test_security_user").first()
        if existing:
            db.delete(existing)
            db.commit()
        
        # Add new test user
        db.add(test_user)
        db.commit()
        
        # Verify user was created with security fields
        created_user = db.query(User_IAM).filter(User_IAM.username == "test_security_user").first()
        assert created_user is not None, "User should be created"
        assert created_user.password == hashed_password, "Password hash should match"
        assert created_user.salt == salt, "Salt should match"
        assert created_user.failed_login_attempts == 0, "Failed attempts should be 0"
        assert created_user.account_locked == False, "Account should not be locked"
        
        # Test password verification
        is_valid = PasswordSecurity.verify_password("TestPassword123!", created_user.password, created_user.salt)
        assert is_valid, "Password should verify correctly"
        
        # Clean up
        db.delete(created_user)
        db.commit()
        
        print("✅ Database Integration tests passed")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()
    
    return True


def main():
    """Run all tests"""
    print("🚀 Running Security Tests")
    print("=" * 50)
    
    tests = [
        test_password_security,
        test_input_validation,
        test_session_security,
        test_rate_limiting,
        test_database_integration,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
