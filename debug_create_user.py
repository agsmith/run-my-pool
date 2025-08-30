#!/usr/bin/env python3
"""
Debug script for /create-user endpoint 422 errors
"""

import requests
import json

# Test data with different scenarios
test_cases = [
    {
        "name": "Valid user",
        "data": {
            "username": "testuser123",
            "email": "test@example.com", 
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
    },
    {
        "name": "Short password",
        "data": {
            "username": "testuser2",
            "email": "test2@example.com",
            "password": "short",
            "confirm_password": "short"
        }
    },
    {
        "name": "Password missing special char",
        "data": {
            "username": "testuser3", 
            "email": "test3@example.com",
            "password": "SecurePass123",
            "confirm_password": "SecurePass123"
        }
    },
    {
        "name": "Invalid email",
        "data": {
            "username": "testuser4",
            "email": "invalid-email",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
    },
    {
        "name": "Reserved username",
        "data": {
            "username": "admin",
            "email": "admin@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
    }
]

def test_create_user(base_url="http://localhost:8000"):
    """Test the /create-user endpoint with various inputs"""
    
    print(f"Testing /create-user endpoint at {base_url}")
    print("=" * 60)
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"Data: {test_case['data']}")
        
        try:
            response = requests.post(
                f"{base_url}/create-user",
                data=test_case['data'],
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 422:
                print("❌ 422 Unprocessable Entity")
                try:
                    error_detail = response.json()
                    print(f"Error Details: {json.dumps(error_detail, indent=2)}")
                except:
                    print(f"Response Text: {response.text}")
            elif response.status_code == 200:
                print("✅ 200 OK")
                if "error" in response.text:
                    print("⚠️  Contains validation error in response")
                elif "success" in response.text:
                    print("✅ User created successfully")
            else:
                print(f"📋 Other status: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError:
            print("❌ Connection Error - Is the server running?")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 40)

def test_password_requirements():
    """Test password validation requirements"""
    print("\n🔒 Password Requirements:")
    print("- Minimum 12 characters")
    print("- At least 1 uppercase letter")
    print("- At least 1 lowercase letter") 
    print("- At least 1 number")
    print("- At least 1 special character (!@#$%^&*(),.?\":{}|<>)")
    print("- Cannot contain common weak patterns")
    print("- Cannot be a reserved username")

if __name__ == "__main__":
    import sys
    
    # Allow custom URL as command line argument
    base_url = sys.argv[1] if len(sys.argv) > 1 else "https://runmypool.net"
    
    test_password_requirements()
    test_create_user(base_url)
