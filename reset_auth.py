#!/usr/bin/env python3
"""
Rate Limit Reset Script - Clear rate limiting and reset user login attempts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import User_IAM
from security_config import rate_limiter, PasswordSecurity

def reset_user_auth(username):
    """Reset user authentication state and clear rate limits"""
    db = SessionLocal()
    try:
        # Find the user
        user = db.query(User_IAM).filter(User_IAM.username == username).first()
        if not user:
            print(f"❌ User '{username}' not found!")
            return False
        
        print(f"🔄 Resetting authentication state for user: {username}")
        
        # Reset failed login attempts
        user.failed_login_attempts = 0
        user.account_locked = False
        user.account_locked_until = None
        user.last_login_attempt = None
        
        # Commit changes
        db.commit()
        
        print(f"✅ Reset user database state:")
        print(f"   - Failed login attempts: {user.failed_login_attempts}")
        print(f"   - Account locked: {user.account_locked}")
        
        # Clear rate limiting for all possible keys related to this user/IP
        print(f"🔄 Clearing rate limits...")
        
        # Clear common rate limiting keys
        rate_limit_keys = [
            f"login:127.0.0.1",
            f"login:localhost", 
            f"api:127.0.0.1",
            f"api:localhost",
            f"{username}:login",
            f"127.0.0.1:login"
        ]
        
        for key in rate_limit_keys:
            rate_limiter.clear_rate_limit(key)
            print(f"   - Cleared rate limit for: {key}")
        
        # Also clear all rate limits as a safety measure
        rate_limiter.clear_all_rate_limits()
        print(f"✅ Cleared all rate limits")
        
        return True
        
    except Exception as e:
        print(f"❌ Error resetting user auth: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def set_user_password(username, password):
    """Set a new password for the user"""
    db = SessionLocal()
    try:
        # Find the user
        user = db.query(User_IAM).filter(User_IAM.username == username).first()
        if not user:
            print(f"❌ User '{username}' not found!")
            return False
        
        print(f"🔐 Setting new password for user: {username}")
        
        # Generate new bcrypt hash with salt
        hashed_password, salt = PasswordSecurity.hash_password(password)
        
        # Update user record
        user.password = hashed_password
        user.salt = salt
        user.failed_login_attempts = 0
        user.account_locked = False
        
        db.commit()
        
        print(f"✅ Password updated successfully")
        print(f"   - New password hash: {hashed_password[:20]}...")
        print(f"   - New salt: {salt[:20]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting password: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🔐 Authentication Reset Tool")
    print("============================")
    
    username = input("Enter username to reset (default: agsmith11): ").strip() or "agsmith11"
    
    print(f"\nOptions for user '{username}':")
    print("1. Reset authentication state and clear rate limits")
    print("2. Set new password")
    print("3. Both (reset + new password)")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        reset_user_auth(username)
    
    elif choice == "2":
        password = input("Enter new password: ").strip()
        if password:
            set_user_password(username, password)
        else:
            print("❌ Password cannot be empty")
    
    elif choice == "3":
        password = input("Enter new password: ").strip()
        if password:
            reset_user_auth(username)
            set_user_password(username, password)
        else:
            print("❌ Password cannot be empty")
    
    elif choice == "4":
        print("Goodbye!")
    
    else:
        print("❌ Invalid choice")
