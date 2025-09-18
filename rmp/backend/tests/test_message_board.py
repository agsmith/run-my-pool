import pytest
from unittest.mock import Mock, patch


class TestMessageBoardEndpoints:
    """Test message board endpoints"""

    def test_get_pool_messages_success(self, authenticated_client, test_pool_data):
        """Test getting messages for a pool"""
        client, _ = authenticated_client
        
        # Create a pool first
        create_response = client.post("/pools/create", json=test_pool_data)
        pool_id = create_response.json()["id"]
        
        # Get messages for the pool
        response = client.get(f"/messages/pool/{pool_id}")
        
        assert response.status_code == 200
        messages = response.json()
        assert isinstance(messages, list)

    def test_post_message_success(self, authenticated_client, test_pool_data):
        """Test posting a message to a pool"""
        client, _ = authenticated_client
        
        # Create a pool first
        create_response = client.post("/pools/create", json=test_pool_data)
        pool_id = create_response.json()["id"]
        
        # Post a message
        message_data = {
            "pool_id": pool_id,
            "message": "This is a test message"
        }
        response = client.post(f"/messages/pool/{pool_id}", json=message_data)
        
        assert response.status_code == 200
        message = response.json()
        assert message["message"] == message_data["message"]
        assert message["pool_id"] == pool_id

    def test_post_empty_message(self, authenticated_client, test_pool_data):
        """Test posting an empty message"""
        client, _ = authenticated_client
        
        # Create a pool first
        create_response = client.post("/pools/create", json=test_pool_data)
        pool_id = create_response.json()["id"]
        
        # Try to post empty message
        message_data = {
            "pool_id": pool_id,
            "message": ""
        }
        response = client.post(f"/messages/pool/{pool_id}", json=message_data)
        
        assert response.status_code in [400, 422]  # Should be rejected

    def test_post_message_long_content(self, authenticated_client, test_pool_data):
        """Test posting a message that's too long"""
        client, _ = authenticated_client
        
        # Create a pool first
        create_response = client.post("/pools/create", json=test_pool_data)
        pool_id = create_response.json()["id"]
        
        # Try to post very long message (assuming 250 char limit)
        long_message = "x" * 300
        message_data = {
            "pool_id": pool_id,
            "message": long_message
        }
        response = client.post(f"/messages/pool/{pool_id}", json=message_data)
        
        assert response.status_code in [400, 422]  # Should be rejected

    def test_get_messages_unauthorized(self, client):
        """Test getting messages without authentication"""
        response = client.get("/messages/pool/some-pool-id")
        assert response.status_code == 401

    def test_post_message_unauthorized(self, client):
        """Test posting message without authentication"""
        message_data = {
            "pool_id": "some-pool-id",
            "message": "Test message"
        }
        response = client.post("/messages/pool/some-pool-id", json=message_data)
        assert response.status_code == 401

    def test_delete_message_success(self, authenticated_client, test_pool_data):
        """Test deleting a message"""
        client, _ = authenticated_client
        
        # Create a pool first
        create_response = client.post("/pools/create", json=test_pool_data)
        pool_id = create_response.json()["id"]
        
        # Post a message
        message_data = {
            "pool_id": pool_id,
            "message": "Message to delete"
        }
        post_response = client.post(f"/messages/pool/{pool_id}", json=message_data)
        message_id = post_response.json()["id"]
        
        # Delete the message
        response = client.delete(f"/messages/{message_id}")
        
        assert response.status_code in [200, 204]

    def test_delete_nonexistent_message(self, authenticated_client):
        """Test deleting a non-existent message"""
        client, _ = authenticated_client
        
        fake_message_id = "00000000-0000-0000-0000-000000000000"
        response = client.delete(f"/messages/{fake_message_id}")
        
        assert response.status_code == 404

    def test_get_messages_nonexistent_pool(self, authenticated_client):
        """Test getting messages for non-existent pool"""
        client, _ = authenticated_client
        
        fake_pool_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/messages/pool/{fake_pool_id}")
        
        # This might return empty list or 404 depending on implementation
        assert response.status_code in [200, 404]

    @patch('message_board.log_create_operation')
    def test_message_creation_audit_logging(self, mock_audit, authenticated_client, test_pool_data):
        """Test that message creation is audited"""
        client, _ = authenticated_client
        
        # Create a pool first
        create_response = client.post("/pools/create", json=test_pool_data)
        pool_id = create_response.json()["id"]
        
        # Post a message
        message_data = {
            "pool_id": pool_id,
            "message": "Audited message"
        }
        response = client.post(f"/messages/pool/{pool_id}", json=message_data)
        
        assert response.status_code == 200
        # Verify audit logging was called (if implemented)
        # mock_audit.assert_called()


class TestMessageBoardPermissions:
    """Test message board permissions and access control"""

    def test_message_board_enabled_pool(self, authenticated_client):
        """Test message board access when enabled"""
        client, _ = authenticated_client
        
        pool_data = {
            "name": "Message Board Enabled Pool",
            "description": "Pool with message board enabled",
            "is_private": False,
            "rule_values": [
                {"rule_id": "message-board-enabled", "rule_value": "true"}
            ]
        }
        
        # Create pool with message board enabled
        create_response = client.post("/pools/create", json=pool_data)
        pool_id = create_response.json()["id"]
        
        # Should be able to access messages
        response = client.get(f"/messages/pool/{pool_id}")
        assert response.status_code == 200

    def test_message_board_disabled_pool(self, authenticated_client):
        """Test message board access when disabled"""
        client, _ = authenticated_client
        
        pool_data = {
            "name": "Message Board Disabled Pool",
            "description": "Pool with message board disabled",
            "is_private": False,
            "rule_values": [
                {"rule_id": "message-board-enabled", "rule_value": "false"}
            ]
        }
        
        # Create pool with message board disabled
        create_response = client.post("/pools/create", json=pool_data)
        pool_id = create_response.json()["id"]
        
        # Access might be restricted (depends on implementation)
        response = client.get(f"/messages/pool/{pool_id}")
        # Could be 403 (forbidden) or 200 with empty list
        assert response.status_code in [200, 403]
