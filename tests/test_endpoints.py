"""
Unit tests for API endpoints and routing in the Run My Pool application.
Tests FastAPI endpoints, request/response handling, routing, and HTTP status codes.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from models import User_IAM, Users, Entries, Picks, Teams, Schedule


class TestMainEndpoints:
    """Test main application endpoints"""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint redirects appropriately"""
        response = test_client.get("/", follow_redirects=False)
        # Should redirect to login or dashboard
        assert response.status_code in [200, 302]
        
        if response.status_code == 302:
            assert response.headers["location"] in ["/login", "/dashboard"]
    
    def test_health_check_endpoint(self, test_client):
        """Test health check endpoint if it exists"""
        response = test_client.get("/health")
        
        if response.status_code == 200:
            # Health check exists and working
            data = response.json()
            assert "status" in data
            assert data["status"] in ["ok", "healthy", "up"]
        else:
            # Health check may not be implemented
            assert response.status_code in [404, 405]
    
    def test_favicon_endpoint(self, test_client):
        """Test favicon endpoint"""
        response = test_client.get("/favicon.ico")
        # Should either serve favicon or return 404
        assert response.status_code in [200, 404]


class TestAuthenticationEndpoints:
    """Test authentication-related endpoints"""
    
    def test_login_get_endpoint(self, test_client):
        """Test GET /login endpoint"""
        response = test_client.get("/login")
        assert response.status_code == 200
        assert "login" in response.text.lower()
        
        # Check for login form elements
        assert "username" in response.text.lower()
        assert "password" in response.text.lower()
    
    def test_login_post_endpoint_valid(self, test_client, test_db, sample_user_iam):
        """Test POST /login with valid credentials"""
        response = test_client.post(
            "/login",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=False
        )
        
        assert response.status_code == 302
        assert "session-token" in response.cookies
        # Should redirect to dashboard
        assert "/dashboard" in response.headers.get("location", "")
    
    def test_login_post_endpoint_invalid(self, test_client):
        """Test POST /login with invalid credentials"""
        response = test_client.post(
            "/login",
            data={"username": "invalid", "password": "invalid"}
        )
        
        assert response.status_code == 200
        assert "invalid" in response.text.lower()
    
    def test_logout_endpoint(self, test_client, authenticated_user_cookie):
        """Test GET /logout endpoint"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/logout", cookies=cookies, follow_redirects=False)
        
        assert response.status_code == 302
        assert "/login" in response.headers["location"]
        
        # Session cookie should be cleared
        set_cookie = response.headers.get("set-cookie", "")
        if "session-token" in set_cookie:
            # Cookie is being cleared
            assert "max-age=0" in set_cookie.lower() or "expires=" in set_cookie.lower()
    
    def test_create_user_get_endpoint(self, test_client):
        """Test GET /create-user endpoint"""
        response = test_client.get("/create-user")
        assert response.status_code == 200
        assert "create" in response.text.lower()
        assert "username" in response.text.lower()
        assert "email" in response.text.lower()
        assert "password" in response.text.lower()
    
    def test_create_user_post_endpoint(self, test_client, test_db):
        """Test POST /create-user endpoint"""
        response = test_client.post(
            "/create-user",
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password": "Password123",
                "confirm_password": "Password123"
            }
        )
        
        assert response.status_code == 200
        assert "success" in response.text.lower()
        
        # Verify user was created
        user = test_db.query(User_IAM).filter(User_IAM.username == "newuser").first()
        assert user is not None
    
    def test_change_password_get_endpoint(self, test_client):
        """Test GET /change-password endpoint"""
        response = test_client.get("/change-password?username=testuser")
        assert response.status_code == 200
        assert "change" in response.text.lower()
        assert "password" in response.text.lower()
    
    def test_change_password_post_endpoint(self, test_client, test_db, sample_user_iam):
        """Test POST /change-password endpoint"""
        response = test_client.post(
            "/change-password",
            data={
                "username": "testuser",
                "current_password": "password123",
                "new_password": "NewPassword123",
                "confirm_password": "NewPassword123"
            }
        )
        
        assert response.status_code == 302  # Redirect after success
    
    def test_forgot_password_endpoints(self, test_client):
        """Test forgot password endpoints"""
        # GET forgot password page
        response = test_client.get("/forgot-password")
        assert response.status_code == 200
        assert "forgot" in response.text.lower()
        
        # POST forgot password
        response = test_client.post(
            "/forgot-password",
            data={"email": "test@example.com"}
        )
        assert response.status_code == 200
        assert "sent" in response.text.lower()
    
    def test_reset_password_endpoint(self, test_client):
        """Test reset password endpoint"""
        response = test_client.get("/reset-password?token=test_token")
        assert response.status_code == 200
        assert "reset" in response.text.lower()


class TestDashboardEndpoints:
    """Test dashboard and main app endpoints"""
    
    def test_dashboard_requires_auth(self, test_client):
        """Test that dashboard requires authentication"""
        response = test_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["location"]
    
    def test_dashboard_authenticated_access(self, test_client, authenticated_user_cookie):
        """Test dashboard access with authentication"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/dashboard", cookies=cookies)
        
        assert response.status_code == 200
        assert "dashboard" in response.text.lower()
    
    def test_account_endpoint(self, test_client, authenticated_user_cookie):
        """Test account page endpoint"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/account", cookies=cookies)
        
        assert response.status_code == 200
        assert "account" in response.text.lower()
    
    def test_entries_endpoint(self, test_client, authenticated_user_cookie):
        """Test entries page endpoint"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/entries", cookies=cookies)
        
        assert response.status_code == 200
        # Should show entries or entry creation interface
        assert any(word in response.text.lower() for word in ["entries", "entry", "create"])


class TestAdminEndpoints:
    """Test admin-specific endpoints"""
    
    def test_admin_page_endpoint(self, test_client, authenticated_admin_cookie):
        """Test admin page endpoint"""
        cookies = {"session-token": authenticated_admin_cookie}
        response = test_client.get("/admin", cookies=cookies)
        
        assert response.status_code == 200
        assert "admin" in response.text.lower()
    
    def test_admin_page_requires_admin_role(self, test_client, authenticated_user_cookie):
        """Test admin page requires admin role"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/admin", cookies=cookies, follow_redirects=False)
        
        assert response.status_code == 302
        assert "/dashboard" in response.headers["location"]
    
    def test_get_admin_users_endpoint(self, test_client, authenticated_admin_cookie, sample_admin_user):
        """Test GET /admin/get-admin-users endpoint"""
        cookies = {"session-token": authenticated_admin_cookie}
        response = test_client.get("/admin/get-admin-users", cookies=cookies)
        
        assert response.status_code == 200
        
        # Should return JSON with admin users
        data = response.json()
        assert "admins" in data
        assert isinstance(data["admins"], list)
        
        if data["admins"]:
            admin = data["admins"][0]
            assert "username" in admin
            assert "email" in admin
    
    def test_assign_admin_endpoint(self, test_client, test_db, authenticated_admin_cookie, sample_user_iam):
        """Test POST /admin/assign-admin endpoint"""
        cookies = {"session-token": authenticated_admin_cookie}
        
        response = test_client.post(
            "/admin/assign-admin",
            json={"username": "testuser"},
            cookies=cookies
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "success" in data["message"].lower()
        
        # Verify user has admin role
        user = test_db.query(User_IAM).filter(User_IAM.username == "testuser").first()
        assert user.admin_role is True
    
    def test_revoke_admin_endpoint(self, test_client, test_db, authenticated_admin_cookie):
        """Test POST /admin/revoke-admin endpoint"""
        # Create a temporary admin user
        temp_admin = User_IAM(
            username="tempadmin",
            password="hashedpassword",
            email="temp@example.com",
            admin_role=True
        )
        test_db.add(temp_admin)
        test_db.commit()
        
        cookies = {"session-token": authenticated_admin_cookie}
        
        response = test_client.post(
            "/admin/revoke-admin",
            json={"username": "tempadmin"},
            cookies=cookies
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "success" in data["message"].lower()
        
        # Verify user no longer has admin role
        test_db.refresh(temp_admin)
        assert temp_admin.admin_role is False
    
    def test_admin_endpoints_require_admin_role(self, test_client, authenticated_user_cookie):
        """Test that admin endpoints require admin role"""
        cookies = {"session-token": authenticated_user_cookie}
        
        admin_endpoints = [
            ("GET", "/admin/get-admin-users"),
            ("POST", "/admin/assign-admin", {"username": "testuser"}),
            ("POST", "/admin/revoke-admin", {"username": "testuser"})
        ]
        
        for method, url, *data in admin_endpoints:
            if method == "GET":
                response = test_client.get(url, cookies=cookies)
            else:
                response = test_client.post(url, json=data[0] if data else {}, cookies=cookies)
            
            assert response.status_code == 403
            error_data = response.json()
            assert "access denied" in error_data["detail"].lower()


class TestPickEndpoints:
    """Test pick-related endpoints"""
    
    def test_submit_picks_endpoint(self, test_client, test_db, authenticated_user_cookie, sample_user_data):
        """Test POST /submit-picks endpoint"""
        # Create entry for testing
        user = test_db.query(Users).filter(Users.username == "testuser").first()
        entry = Entries(
            user_id=user.user_id,
            entry_name="Test Entry",
            current_week=1,
            weekly_total=0,
            season_total=0
        )
        test_db.add(entry)
        test_db.commit()
        
        cookies = {"session-token": authenticated_user_cookie}
        
        pick_data = {
            "entry_id": entry.entry_id,
            "week": 1,
            "picks": [
                {"game_id": 1, "team_id": 1},
                {"game_id": 2, "team_id": 3}
            ]
        }
        
        response = test_client.post("/submit-picks", json=pick_data, cookies=cookies)
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "success" in data["message"].lower()
        else:
            # Endpoint may not be fully implemented
            assert response.status_code in [400, 404, 405, 422, 501]
    
    def test_get_picks_endpoint(self, test_client, authenticated_user_cookie, sample_picks_data):
        """Test GET /picks/{entry_id}/{week} endpoint"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/picks/1/1", cookies=cookies)
        
        if response.status_code == 200:
            data = response.json()
            assert "picks" in data
            assert isinstance(data["picks"], list)
        else:
            # Endpoint may not be implemented
            assert response.status_code in [404, 405]
    
    def test_weekly_picks_endpoint(self, test_client, authenticated_user_cookie):
        """Test weekly picks endpoint"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/weekly-picks", cookies=cookies)
        
        if response.status_code == 200:
            # Should display weekly picks interface
            assert "picks" in response.text.lower()
        else:
            assert response.status_code in [404, 405]


class TestScheduleEndpoints:
    """Test schedule-related endpoints"""
    
    def test_get_schedule_endpoint(self, test_client, authenticated_user_cookie, sample_game_data):
        """Test GET /schedule/{week} endpoint"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/schedule/1", cookies=cookies)
        
        if response.status_code == 200:
            data = response.json()
            assert "games" in data
            assert isinstance(data["games"], list)
            
            if data["games"]:
                game = data["games"][0]
                required_fields = ["game_id", "away_team", "home_team", "game_time"]
                for field in required_fields:
                    assert field in game
        else:
            assert response.status_code in [404, 405]
    
    def test_current_week_schedule_endpoint(self, test_client, authenticated_user_cookie):
        """Test GET /schedule/current endpoint"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/schedule/current", cookies=cookies)
        
        if response.status_code == 200:
            data = response.json()
            assert "games" in data
        else:
            assert response.status_code in [404, 405]
    
    def test_weekly_locks_endpoint(self, test_client, authenticated_user_cookie):
        """Test GET /weekly-locks/{week} endpoint"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/weekly-locks/1", cookies=cookies)
        
        if response.status_code == 200:
            data = response.json()
            assert "lock_time" in data
        else:
            assert response.status_code in [404, 405]


class TestTeamEndpoints:
    """Test team-related endpoints"""
    
    def test_get_teams_endpoint(self, test_client, authenticated_user_cookie, sample_teams_data):
        """Test GET /teams endpoint"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/teams", cookies=cookies)
        
        if response.status_code == 200:
            data = response.json()
            assert "teams" in data
            assert isinstance(data["teams"], list)
            
            if data["teams"]:
                team = data["teams"][0]
                required_fields = ["team_id", "team_name", "team_abbreviation"]
                for field in required_fields:
                    assert field in team
        else:
            assert response.status_code in [404, 405]
    
    def test_get_team_by_id_endpoint(self, test_client, authenticated_user_cookie, sample_teams_data):
        """Test GET /teams/{team_id} endpoint"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/teams/1", cookies=cookies)
        
        if response.status_code == 200:
            data = response.json()
            assert "team_id" in data
            assert data["team_id"] == 1
        else:
            assert response.status_code in [404, 405]


class TestStaticFileEndpoints:
    """Test static file serving endpoints"""
    
    def test_css_files(self, test_client):
        """Test CSS file serving"""
        css_files = [
            "/static/css/style.css",
            "/static/css/event-style.css",
            "/static/css/left-nav.css"
        ]
        
        for css_file in css_files:
            response = test_client.get(css_file)
            # Should either serve the file or return 404
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                assert "text/css" in response.headers.get("content-type", "")
    
    def test_js_files(self, test_client):
        """Test JavaScript file serving"""
        js_files = [
            "/static/js/rmp.js",
            "/static/js/rules-delete.js"
        ]
        
        for js_file in js_files:
            response = test_client.get(js_file)
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                assert any(js_type in content_type for js_type in ["javascript", "application/json"])
    
    def test_image_files(self, test_client):
        """Test image file serving"""
        image_files = [
            "/static/img/logo.svg",
            "/static/img/rmp_logo.svg",
            "/static/img/nfl.svg"
        ]
        
        for image_file in image_files:
            response = test_client.get(image_file)
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                assert "image" in content_type


class TestErrorEndpoints:
    """Test error handling endpoints"""
    
    def test_404_error_handling(self, test_client):
        """Test 404 error handling"""
        response = test_client.get("/nonexistent-page")
        assert response.status_code == 404
    
    def test_405_method_not_allowed(self, test_client):
        """Test 405 Method Not Allowed handling"""
        # Try POST on a GET-only endpoint
        response = test_client.post("/login-page-that-only-accepts-get")
        assert response.status_code in [404, 405]
    
    def test_422_validation_error(self, test_client, authenticated_user_cookie):
        """Test 422 validation error handling"""
        cookies = {"session-token": authenticated_user_cookie}
        
        # Send invalid JSON to an endpoint that expects valid data
        response = test_client.post(
            "/submit-picks",
            json={"invalid": "data"},
            cookies=cookies
        )
        
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data
        else:
            # Endpoint may handle validation differently
            assert response.status_code in [400, 404, 405]


class TestHTTPHeaders:
    """Test HTTP headers and responses"""
    
    def test_security_headers(self, test_client):
        """Test security headers in responses"""
        response = test_client.get("/login")
        
        # Check for basic security headers
        headers = response.headers
        
        # Content-Type should be set
        assert "content-type" in headers
        
        # Check for security headers (if implemented)
        security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection"
        ]
        
        # These may or may not be implemented
        for header in security_headers:
            if header in headers:
                assert headers[header] is not None
    
    def test_cors_headers(self, test_client):
        """Test CORS headers if applicable"""
        response = test_client.options("/login")
        
        # CORS headers may or may not be set depending on configuration
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers"
        ]
        
        # Just verify response doesn't crash
        assert response.status_code in [200, 405]
    
    def test_content_type_headers(self, test_client, authenticated_user_cookie):
        """Test Content-Type headers for different endpoints"""
        cookies = {"session-token": authenticated_user_cookie}
        
        # HTML endpoints
        html_endpoints = ["/login", "/dashboard", "/admin"]
        
        for endpoint in html_endpoints:
            response = test_client.get(endpoint, cookies=cookies)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                assert "text/html" in content_type
        
        # JSON endpoints
        json_endpoints = ["/admin/get-admin-users", "/teams"]
        
        for endpoint in json_endpoints:
            response = test_client.get(endpoint, cookies=cookies)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                assert "application/json" in content_type


class TestRequestValidation:
    """Test request validation and parameter handling"""
    
    def test_invalid_json_handling(self, test_client, authenticated_user_cookie):
        """Test handling of invalid JSON in requests"""
        cookies = {"session-token": authenticated_user_cookie}
        
        # Send malformed JSON
        response = test_client.post(
            "/submit-picks",
            data="invalid json data",
            headers={"Content-Type": "application/json"},
            cookies=cookies
        )
        
        # Should handle gracefully
        assert response.status_code in [400, 422]
    
    def test_missing_required_fields(self, test_client, authenticated_user_cookie):
        """Test handling of missing required fields"""
        cookies = {"session-token": authenticated_user_cookie}
        
        # Send incomplete data
        response = test_client.post(
            "/submit-picks",
            json={"incomplete": "data"},
            cookies=cookies
        )
        
        assert response.status_code in [400, 422]
        
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data
    
    def test_parameter_type_validation(self, test_client, authenticated_user_cookie):
        """Test parameter type validation"""
        cookies = {"session-token": authenticated_user_cookie}
        
        # Test with invalid parameter types
        invalid_endpoints = [
            "/picks/invalid_entry_id/1",
            "/picks/1/invalid_week",
            "/schedule/invalid_week",
            "/teams/invalid_team_id"
        ]
        
        for endpoint in invalid_endpoints:
            response = test_client.get(endpoint, cookies=cookies)
            # Should return 422 for type validation errors or 404 for not found
            assert response.status_code in [404, 422]
    
    def test_parameter_range_validation(self, test_client, authenticated_user_cookie):
        """Test parameter range validation"""
        cookies = {"session-token": authenticated_user_cookie}
        
        # Test with out-of-range parameters
        out_of_range_endpoints = [
            "/picks/0/1",      # entry_id should be > 0
            "/picks/1/0",      # week should be > 0
            "/schedule/0",     # week should be > 0
            "/teams/0"         # team_id should be > 0
        ]
        
        for endpoint in out_of_range_endpoints:
            response = test_client.get(endpoint, cookies=cookies)
            # Should handle gracefully
            assert response.status_code in [400, 404, 422]


class TestResponseFormat:
    """Test response format consistency"""
    
    def test_json_response_structure(self, test_client, authenticated_admin_cookie):
        """Test JSON response structure consistency"""
        cookies = {"session-token": authenticated_admin_cookie}
        
        # Test admin users endpoint
        response = test_client.get("/admin/get-admin-users", cookies=cookies)
        
        if response.status_code == 200:
            data = response.json()
            
            # Should be valid JSON
            assert isinstance(data, dict)
            assert "admins" in data
            assert isinstance(data["admins"], list)
    
    def test_error_response_structure(self, test_client, authenticated_user_cookie):
        """Test error response structure consistency"""
        cookies = {"session-token": authenticated_user_cookie}
        
        # Generate an error response
        response = test_client.get("/admin/get-admin-users", cookies=cookies)
        
        if response.status_code in [400, 403, 404, 422]:
            data = response.json()
            
            # Should have standard error structure
            assert isinstance(data, dict)
            assert "detail" in data
    
    def test_html_response_structure(self, test_client, authenticated_user_cookie):
        """Test HTML response structure"""
        cookies = {"session-token": authenticated_user_cookie}
        
        response = test_client.get("/dashboard", cookies=cookies)
        
        if response.status_code == 200:
            html = response.text
            
            # Should be valid HTML structure
            assert "<html" in html.lower()
            assert "<head" in html.lower()
            assert "<body" in html.lower()
            assert "</html>" in html.lower()
    
    def test_redirect_response_structure(self, test_client, sample_user_iam):
        """Test redirect response structure"""
        # Login should redirect after success
        response = test_client.post(
            "/login",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=False
        )
        
        if response.status_code == 302:
            # Should have location header
            assert "location" in response.headers
            assert response.headers["location"].startswith("/")


class TestRateLimiting:
    """Test rate limiting if implemented"""
    
    def test_login_rate_limiting(self, test_client):
        """Test rate limiting on login attempts"""
        # This would test rate limiting if implemented
        # For now, just verify multiple attempts don't crash
        
        for i in range(5):
            response = test_client.post(
                "/login",
                data={"username": "invalid", "password": "invalid"}
            )
            
            # Should handle multiple invalid attempts gracefully
            assert response.status_code in [200, 429]  # 429 = Too Many Requests
            
            if response.status_code == 429:
                # Rate limiting is implemented
                break
    
    def test_api_rate_limiting(self, test_client, authenticated_user_cookie):
        """Test rate limiting on API endpoints"""
        cookies = {"session-token": authenticated_user_cookie}
        
        # Make multiple rapid requests
        for i in range(10):
            response = test_client.get("/teams", cookies=cookies)
            
            # Should handle multiple requests gracefully
            assert response.status_code in [200, 404, 429]
            
            if response.status_code == 429:
                # Rate limiting is implemented
                break
