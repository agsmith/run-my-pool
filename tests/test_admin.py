"""
Unit tests for admin functionality in the Run My Pool application.
Tests admin access management, user administration, and admin-only features.
"""

import pytest
import hashlib
import secrets
import base64
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from models import User_IAM


class TestAdminEndpoints:
    """Test admin-specific endpoints"""
    
    def test_get_admin_users_requires_auth(self, test_client):
        """Test that get admin users endpoint requires authentication"""
        response = test_client.get("/admin/get-admin-users")
        assert response.status_code == 401
        assert "Unauthorized" in response.text
    
    def test_get_admin_users_requires_admin_role(self, test_client, authenticated_user_cookie):
        """Test that get admin users requires admin role"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/admin/get-admin-users", cookies=cookies)
        assert response.status_code == 403
        assert "Access denied" in response.text
    
    def test_get_admin_users_success(self, test_client, test_db, authenticated_admin_cookie, sample_admin_user):
        """Test successful retrieval of admin users"""
        cookies = {"session-token": authenticated_admin_cookie}
        response = test_client.get("/admin/get-admin-users", cookies=cookies)
        
        assert response.status_code == 200
        data = response.json()
        assert "admins" in data
        assert len(data["admins"]) >= 1
        
        # Verify admin user is in the list
        admin_usernames = [user["username"] for user in data["admins"]]
        assert "adminuser" in admin_usernames
    
    def test_assign_admin_requires_auth(self, test_client):
        """Test that assign admin endpoint requires authentication"""
        response = test_client.post(
            "/admin/assign-admin",
            json={"username": "testuser"}
        )
        assert response.status_code == 401
        assert "Unauthorized" in response.text
    
    def test_assign_admin_requires_admin_role(self, test_client, authenticated_user_cookie):
        """Test that assign admin requires admin role"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.post(
            "/admin/assign-admin",
            json={"username": "testuser"},
            cookies=cookies
        )
        assert response.status_code == 403
        assert "Access denied" in response.text
    
    def test_assign_admin_success(self, test_client, test_db, authenticated_admin_cookie, sample_user_iam):
        """Test successful admin assignment"""
        cookies = {"session-token": authenticated_admin_cookie}
        response = test_client.post(
            "/admin/assign-admin",
            json={"username": "testuser"},
            cookies=cookies
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Admin role assigned successfully"
        
        # Verify user now has admin role in database
        user = test_db.query(User_IAM).filter(User_IAM.username == "testuser").first()
        assert user.admin_role is True
    
    def test_assign_admin_nonexistent_user(self, test_client, test_db, authenticated_admin_cookie):
        """Test assigning admin to non-existent user"""
        cookies = {"session-token": authenticated_admin_cookie}
        response = test_client.post(
            "/admin/assign-admin",
            json={"username": "nonexistent"},
            cookies=cookies
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "User not found" in data["detail"]
    
    def test_assign_admin_already_admin(self, test_client, test_db, authenticated_admin_cookie, sample_admin_user):
        """Test assigning admin to user who is already admin"""
        cookies = {"session-token": authenticated_admin_cookie}
        response = test_client.post(
            "/admin/assign-admin",
            json={"username": "adminuser"},
            cookies=cookies
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already has admin role" in data["detail"]
    
    def test_revoke_admin_requires_auth(self, test_client):
        """Test that revoke admin endpoint requires authentication"""
        response = test_client.post(
            "/admin/revoke-admin",
            json={"username": "adminuser"}
        )
        assert response.status_code == 401
        assert "Unauthorized" in response.text
    
    def test_revoke_admin_requires_admin_role(self, test_client, authenticated_user_cookie):
        """Test that revoke admin requires admin role"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.post(
            "/admin/revoke-admin",
            json={"username": "adminuser"},
            cookies=cookies
        )
        assert response.status_code == 403
        assert "Access denied" in response.text
    
    def test_revoke_admin_success(self, test_client, test_db, authenticated_admin_cookie):
        """Test successful admin revocation"""
        # Create a user with admin role
        admin_user = User_IAM(
            username="tempadmin",
            password=hashlib.sha256("password123".encode()).hexdigest(),
            email="temp@example.com",
            admin_role=True
        )
        test_db.add(admin_user)
        test_db.commit()
        
        cookies = {"session-token": authenticated_admin_cookie}
        response = test_client.post(
            "/admin/revoke-admin",
            json={"username": "tempadmin"},
            cookies=cookies
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Admin role revoked successfully"
        
        # Verify user no longer has admin role in database
        user = test_db.query(User_IAM).filter(User_IAM.username == "tempadmin").first()
        assert user.admin_role is False
    
    def test_revoke_admin_nonexistent_user(self, test_client, test_db, authenticated_admin_cookie):
        """Test revoking admin from non-existent user"""
        cookies = {"session-token": authenticated_admin_cookie}
        response = test_client.post(
            "/admin/revoke-admin",
            json={"username": "nonexistent"},
            cookies=cookies
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "User not found" in data["detail"]
    
    def test_revoke_admin_not_admin(self, test_client, test_db, authenticated_admin_cookie, sample_user_iam):
        """Test revoking admin from user who is not admin"""
        cookies = {"session-token": authenticated_admin_cookie}
        response = test_client.post(
            "/admin/revoke-admin",
            json={"username": "testuser"},
            cookies=cookies
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "does not have admin role" in data["detail"]


class TestAdminPageAccess:
    """Test admin page accessibility and functionality"""
    
    def test_admin_page_renders_for_admin(self, test_client, authenticated_admin_cookie):
        """Test that admin page renders correctly for admin users"""
        cookies = {"session-token": authenticated_admin_cookie}
        response = test_client.get("/admin", cookies=cookies)
        
        assert response.status_code == 200
        assert "admin" in response.text.lower()
        assert "users" in response.text.lower()
    
    def test_admin_page_redirects_non_admin(self, test_client, authenticated_user_cookie):
        """Test that admin page redirects non-admin users"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/admin", cookies=cookies, follow_redirects=False)
        
        assert response.status_code == 302
        assert "/dashboard" in response.headers["location"]
    
    def test_admin_page_redirects_unauthenticated(self, test_client):
        """Test that admin page redirects unauthenticated users"""
        response = test_client.get("/admin", follow_redirects=False)
        
        assert response.status_code == 302
        assert "/login" in response.headers["location"]


class TestAdminPrivileges:
    """Test admin-only privileges and restrictions"""
    
    def test_admin_can_view_all_users(self, test_client, test_db, authenticated_admin_cookie, sample_user_iam):
        """Test that admin can view all users"""
        cookies = {"session-token": authenticated_admin_cookie}
        
        # This would be an endpoint that lists all users (if it exists)
        # For now, we can test the admin user retrieval
        response = test_client.get("/admin/get-admin-users", cookies=cookies)
        assert response.status_code == 200
    
    def test_regular_user_cannot_access_admin_endpoints(self, test_client, authenticated_user_cookie):
        """Test that regular users cannot access admin endpoints"""
        cookies = {"session-token": authenticated_user_cookie}
        
        # Test all admin endpoints
        admin_endpoints = [
            "/admin/get-admin-users",
            ("/admin/assign-admin", {"username": "testuser"}),
            ("/admin/revoke-admin", {"username": "testuser"})
        ]
        
        for endpoint in admin_endpoints:
            if isinstance(endpoint, tuple):
                url, data = endpoint
                response = test_client.post(url, json=data, cookies=cookies)
            else:
                response = test_client.get(endpoint, cookies=cookies)
            
            assert response.status_code == 403
            assert "Access denied" in response.text or "Forbidden" in response.text
    
    def test_admin_role_inheritance(self, test_client, test_db, authenticated_admin_cookie):
        """Test that admin role provides access to regular user features"""
        cookies = {"session-token": authenticated_admin_cookie}
        
        # Admin should be able to access regular user pages
        user_endpoints = ["/dashboard", "/account"]
        
        for endpoint in user_endpoints:
            response = test_client.get(endpoint, cookies=cookies)
            # Should not redirect to login (status 200 or other non-401/403)
            assert response.status_code not in [401, 403]


class TestAdminSecurity:
    """Test security aspects of admin functionality"""
    
    def test_admin_assignment_requires_valid_json(self, test_client, authenticated_admin_cookie):
        """Test that admin assignment requires valid JSON"""
        cookies = {"session-token": authenticated_admin_cookie}
        
        # Test with invalid JSON
        response = test_client.post(
            "/admin/assign-admin",
            data="invalid json",
            cookies=cookies,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_admin_assignment_validates_username(self, test_client, authenticated_admin_cookie):
        """Test that admin assignment validates username format"""
        cookies = {"session-token": authenticated_admin_cookie}
        
        # Test with empty username
        response = test_client.post(
            "/admin/assign-admin",
            json={"username": ""},
            cookies=cookies
        )
        
        assert response.status_code == 422
    
    def test_admin_endpoints_prevent_sql_injection(self, test_client, authenticated_admin_cookie):
        """Test that admin endpoints prevent SQL injection"""
        cookies = {"session-token": authenticated_admin_cookie}
        
        # Test with SQL injection attempt
        malicious_username = "'; DROP TABLE User_IAM; --"
        
        response = test_client.post(
            "/admin/assign-admin",
            json={"username": malicious_username},
            cookies=cookies
        )
        
        # Should handle gracefully (not crash) and return 404 for non-existent user
        assert response.status_code in [404, 422]
    
    def test_admin_actions_are_logged(self, test_client, test_db, authenticated_admin_cookie, sample_user_iam):
        """Test that admin actions can be audited"""
        # This is a placeholder for audit logging functionality
        # In a real implementation, you would test that admin actions are logged
        
        cookies = {"session-token": authenticated_admin_cookie}
        
        # Perform admin action
        response = test_client.post(
            "/admin/assign-admin",
            json={"username": "testuser"},
            cookies=cookies
        )
        
        assert response.status_code == 200
        
        # In a real implementation, you would check audit logs here
        # For example:
        # audit_log = test_db.query(AuditLog).filter(
        #     AuditLog.action == "assign_admin",
        #     AuditLog.target_user == "testuser"
        # ).first()
        # assert audit_log is not None


class TestAdminDataIntegrity:
    """Test data integrity in admin operations"""
    
    def test_admin_assignment_is_atomic(self, test_client, test_db, authenticated_admin_cookie, sample_user_iam):
        """Test that admin assignment is atomic (all or nothing)"""
        cookies = {"session-token": authenticated_admin_cookie}
        
        # Get initial state
        user = test_db.query(User_IAM).filter(User_IAM.username == "testuser").first()
        initial_admin_status = user.admin_role
        
        # Attempt assignment
        response = test_client.post(
            "/admin/assign-admin",
            json={"username": "testuser"},
            cookies=cookies
        )
        
        # Verify final state is consistent
        test_db.refresh(user)
        if response.status_code == 200:
            assert user.admin_role is True
        else:
            assert user.admin_role == initial_admin_status
    
    def test_admin_revocation_is_atomic(self, test_client, test_db, authenticated_admin_cookie):
        """Test that admin revocation is atomic (all or nothing)"""
        # Create admin user
        admin_user = User_IAM(
            username="tempadmin2",
            password=hashlib.sha256("password123".encode()).hexdigest(),
            email="temp2@example.com",
            admin_role=True
        )
        test_db.add(admin_user)
        test_db.commit()
        
        cookies = {"session-token": authenticated_admin_cookie}
        
        # Get initial state
        initial_admin_status = admin_user.admin_role
        
        # Attempt revocation
        response = test_client.post(
            "/admin/revoke-admin",
            json={"username": "tempadmin2"},
            cookies=cookies
        )
        
        # Verify final state is consistent
        test_db.refresh(admin_user)
        if response.status_code == 200:
            assert admin_user.admin_role is False
        else:
            assert admin_user.admin_role == initial_admin_status
    
    def test_cannot_revoke_last_admin(self, test_client, test_db, authenticated_admin_cookie):
        """Test that the last admin cannot revoke their own admin status"""
        # This test assumes there should always be at least one admin
        # Implementation would need to check admin count before revocation
        
        cookies = {"session-token": authenticated_admin_cookie}
        
        # Try to revoke the only admin (adminuser from fixture)
        response = test_client.post(
            "/admin/revoke-admin",
            json={"username": "adminuser"},
            cookies=cookies
        )
        
        # Should either prevent the action or ensure another admin exists
        # This depends on business logic implementation
        if response.status_code == 400:
            assert "cannot revoke last admin" in response.json()["detail"].lower()
        else:
            # If allowed, verify there's still at least one admin
            admins = test_db.query(User_IAM).filter(User_IAM.admin_role == True).all()
            assert len(admins) >= 1


class TestAdminBulkOperations:
    """Test bulk operations for admin functionality"""
    
    def test_assign_multiple_admins(self, test_client, test_db, authenticated_admin_cookie):
        """Test assigning admin role to multiple users"""
        # Create multiple test users
        users = []
        for i in range(3):
            user = User_IAM(
                username=f"bulkuser{i}",
                password=hashlib.sha256("password123".encode()).hexdigest(),
                email=f"bulk{i}@example.com",
                admin_role=False
            )
            users.append(user)
            test_db.add(user)
        test_db.commit()
        
        cookies = {"session-token": authenticated_admin_cookie}
        
        # Assign admin to each user
        for user in users:
            response = test_client.post(
                "/admin/assign-admin",
                json={"username": user.username},
                cookies=cookies
            )
            assert response.status_code == 200
        
        # Verify all users now have admin role
        for user in users:
            test_db.refresh(user)
            assert user.admin_role is True
    
    def test_revoke_multiple_admins(self, test_client, test_db, authenticated_admin_cookie):
        """Test revoking admin role from multiple users"""
        # Create multiple admin users
        admin_users = []
        for i in range(3):
            user = User_IAM(
                username=f"bulkadmin{i}",
                password=hashlib.sha256("password123".encode()).hexdigest(),
                email=f"bulkadmin{i}@example.com",
                admin_role=True
            )
            admin_users.append(user)
            test_db.add(user)
        test_db.commit()
        
        cookies = {"session-token": authenticated_admin_cookie}
        
        # Revoke admin from each user
        for user in admin_users:
            response = test_client.post(
                "/admin/revoke-admin",
                json={"username": user.username},
                cookies=cookies
            )
            assert response.status_code == 200
        
        # Verify no users have admin role anymore
        for user in admin_users:
            test_db.refresh(user)
            assert user.admin_role is False
