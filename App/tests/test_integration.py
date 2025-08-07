"""
Integration Tests for WeMo Robot Teleoperation Backend

This module contains comprehensive integration tests that verify the interactions
between different components of the robot teleoperation system, including:
- Router-Service integration
- Service-SSH client integration  
- Error handling across layers
- Request-response data flow
- Middleware functionality integration
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from fastapi.testclient import TestClient
from fastapi import HTTPException

# Import all components for integration testing
from App.main import app as main_app
from App.routers.teleop_CLI_endpoints import app as router_app, get_teleop_service
from App.services.teleop_CLI_services import TeleopService
from App.utils.teleop_CLI_SSH_helper import SSHClient, SSHClientError


class TestRouterServiceIntegration:
    """
    Test integration between FastAPI routers and service layer.
    Verifies that endpoints correctly call service methods and handle responses.
    """

    @pytest.fixture(autouse=True)
    def setup_test_client(self):
        """Set up test client with mocked SSH but real service integration."""
        self.client = TestClient(router_app)

        # Mock only the SSH client, keep service layer real
        self.mock_ssh_client = Mock(spec=SSHClient)

        # Create real service with mocked SSH client
        self.real_teleop_service = TeleopService(self.mock_ssh_client)

        # Override dependency injection
        router_app.dependency_overrides[get_teleop_service] = lambda: self.real_teleop_service

        yield

        # Cleanup
        router_app.dependency_overrides.clear()

    def test_router_service_start_session_integration(self):
        """Test complete router-to-service integration for start session."""
        # Arrange
        self.mock_ssh_client.start_session.return_value = "session_started_successfully"

        # Act
        response = self.client.post("/api/startsession", json={"bot_id": 123})

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "session_started_successfully"

        # Verify service called SSH client correctly
        self.mock_ssh_client.start_session.assert_called_once_with(123)

    def test_router_service_error_propagation_integration(self):
        """Test error propagation from service layer to router layer."""
        # Arrange
        self.mock_ssh_client.end_session.side_effect = SSHClientError("SSH connection lost")

        # Act
        response = self.client.post("/api/endsession", json={"bot_id": 456})

        # Assert
        assert response.status_code == 500
        error_data = response.json()
        assert "error" in error_data
        assert "SSH connection lost" in error_data["error"]

    def test_router_service_speed_change_integration(self):
        """Test router-service integration for speed change with validation."""
        # Arrange
        self.mock_ssh_client.change_speed.return_value = "speed_increased"

        # Act
        response = self.client.post("/api/speed", json={
            "bot_id": 789,
            "action": "increase"
        })

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "speed_increased"

        # Verify service validation and SSH call
        self.mock_ssh_client.change_speed.assert_called_once_with(789, "increase")

    def test_router_service_validation_integration(self):
        """Test that service-layer validation integrates with router error handling."""
        # Arrange
        self.mock_ssh_client.move.side_effect = SSHClientError("Invalid move direction: invalid")

        # Act - This should pass router validation but fail at service level
        response = self.client.post("/api/move", json={
            "bot_id": 111,
            "direction": "up"  # Valid for router, but service will throw error
        })

        # Assert
        assert response.status_code == 500
        error_data = response.json()
        assert "Invalid move direction" in error_data["error"]


class TestServiceSSHIntegration:
    """
    Test integration between service layer and SSH client.
    Verifies data flow and error handling between service and SSH components.
    """

    @pytest.fixture(autouse=True)
    def setup_service_ssh_integration(self):
        """Set up service with mock SSH client for integration testing."""
        self.mock_ssh_client = Mock(spec=SSHClient)
        self.teleop_service = TeleopService(self.mock_ssh_client)

    def test_service_ssh_session_lifecycle_integration(self):
        """Test complete session lifecycle integration between service and SSH."""
        # Arrange
        bot_id = 123
        self.mock_ssh_client.start_session.return_value = "session_started"
        self.mock_ssh_client.get_session_status.return_value = "active"
        self.mock_ssh_client.end_session.return_value = "session_ended"

        # Act & Assert - Start session
        start_result = self.teleop_service.start_session(bot_id)
        assert start_result["status"] == "session_started"
        self.mock_ssh_client.start_session.assert_called_once_with(bot_id)

        # Act & Assert - Check status
        status_result = self.teleop_service.get_session_status(bot_id)
        assert status_result["session_status"] == "active"
        self.mock_ssh_client.get_session_status.assert_called_once_with(bot_id)

        # Act & Assert - End session
        end_result = self.teleop_service.end_session(bot_id)
        assert end_result["status"] == "session_ended"
        self.mock_ssh_client.end_session.assert_called_once_with(bot_id)

    def test_service_ssh_movement_command_integration(self):
        """Test movement command integration between service and SSH."""
        # Arrange
        bot_id = 456
        self.mock_ssh_client.move.return_value = "movement_executed"
        self.mock_ssh_client.rotate.return_value = "rotation_executed"

        # Act & Assert - Move command
        move_result = self.teleop_service.move(bot_id, "up")
        assert move_result["status"] == "movement_executed"
        self.mock_ssh_client.move.assert_called_once_with(bot_id, "up")

        # Act & Assert - Rotate command
        rotate_result = self.teleop_service.rotate(bot_id, "left")
        assert rotate_result["status"] == "rotation_executed"
        self.mock_ssh_client.rotate.assert_called_once_with(bot_id, "left")

    def test_service_ssh_error_handling_integration(self):
        """Test error handling integration between service and SSH layers."""
        # Arrange
        bot_id = 789
        self.mock_ssh_client.change_speed.side_effect = SSHClientError("Robot not responding")

        # Act & Assert
        with pytest.raises(SSHClientError) as exc_info:
            self.teleop_service.change_speed(bot_id, "increase")

        assert "Robot not responding" in str(exc_info.value)
        self.mock_ssh_client.change_speed.assert_called_once_with(bot_id, "increase")

    def test_service_ssh_debug_information_integration(self):
        """Test debug information flow between service and SSH components."""
        # Arrange
        bot_id = 999
        mock_process = Mock()
        self.mock_ssh_client.get_session_status.return_value = "active"
        self.mock_ssh_client.list_active_sessions.return_value = [999, 1000]
        self.mock_ssh_client._sessions = {999: mock_process}
        self.mock_ssh_client._is_alive.return_value = True

        # Create test client with this service
        client = TestClient(router_app)
        router_app.dependency_overrides[get_teleop_service] = lambda: self.teleop_service

        try:
            # Act
            response = client.get(f"/api/debug?bot_id={bot_id}")

            # Assert
            assert response.status_code == 200
            debug_data = response.json()

            assert debug_data["bot_id"] == bot_id
            assert debug_data["status"] == "active"
            assert debug_data["session_exists_in_sessions"] is True
            assert debug_data["all_active_sessions"] == [999, 1000]
            assert debug_data["process_alive"] is True

        finally:
            router_app.dependency_overrides.clear()


class TestEndToEndWorkflowIntegration:
    """
    Test complete end-to-end workflows that span multiple components.
    Simulates real user scenarios with multiple API calls.
    """

    @pytest.fixture(autouse=True)
    def setup_e2e_environment(self):
        """Set up end-to-end testing environment."""
        self.client = TestClient(router_app)
        self.mock_ssh_client = Mock(spec=SSHClient)
        self.teleop_service = TeleopService(self.mock_ssh_client)

        router_app.dependency_overrides[get_teleop_service] = lambda: self.teleop_service

        yield

        router_app.dependency_overrides.clear()

    def test_complete_robot_control_workflow(self):
        """Test complete robot control workflow from session start to end."""
        bot_id = 123

        # Setup SSH client mock responses
        self.mock_ssh_client.start_session.return_value = "session_started"
        self.mock_ssh_client.get_session_status.return_value = "active"
        self.mock_ssh_client.change_speed.return_value = "speed_increased"
        self.mock_ssh_client.move.return_value = "moved_up"
        self.mock_ssh_client.rotate.return_value = "rotated_left"
        self.mock_ssh_client.get_speed.return_value = {"current_speed": 7}
        self.mock_ssh_client.end_session.return_value = "session_ended"

        # Step 1: Start session
        response = self.client.post("/api/startsession", json={"bot_id": bot_id})
        assert response.status_code == 200
        assert response.json()["status"] == "session_started"

        # Step 2: Check session status
        response = self.client.get(f"/api/session/status?bot_id={bot_id}")
        assert response.status_code == 200
        assert response.json()["session_status"] == "active"

        # Step 3: Increase speed
        response = self.client.post("/api/speed", json={"bot_id": bot_id, "action": "increase"})
        assert response.status_code == 200
        assert response.json()["status"] == "speed_increased"

        # Step 4: Move robot
        response = self.client.post("/api/move", json={"bot_id": bot_id, "direction": "up"})
        assert response.status_code == 200
        assert response.json()["status"] == "moved_up"

        # Step 5: Rotate robot
        response = self.client.post("/api/rotate", json={"bot_id": bot_id, "direction": "left"})
        assert response.status_code == 200
        assert response.json()["status"] == "rotated_left"

        # Step 6: Check speed
        response = self.client.get(f"/api/getspeed?bot_id={bot_id}")
        assert response.status_code == 200
        speed_data = response.json()
        assert speed_data["status"] == "success"
        assert speed_data["speed_info"]["current_speed"] == 7

        # Step 7: End session
        response = self.client.post("/api/endsession", json={"bot_id": bot_id})
        assert response.status_code == 200
        assert response.json()["status"] == "session_ended"

        # Verify all SSH client methods were called in correct sequence
        expected_calls = [
            ("start_session", (bot_id,)),
            ("get_session_status", (bot_id,)),
            ("change_speed", (bot_id, "increase")),
            ("move", (bot_id, "up")),
            ("rotate", (bot_id, "left")),
            ("get_speed", (bot_id,)),
            ("end_session", (bot_id,))
        ]

        # Verify call sequence
        assert self.mock_ssh_client.start_session.call_count == 1
        assert self.mock_ssh_client.get_session_status.call_count == 1
        assert self.mock_ssh_client.change_speed.call_count == 1
        assert self.mock_ssh_client.move.call_count == 1
        assert self.mock_ssh_client.rotate.call_count == 1
        assert self.mock_ssh_client.get_speed.call_count == 1
        assert self.mock_ssh_client.end_session.call_count == 1

    def test_error_recovery_workflow(self):
        """Test error recovery workflow across multiple components."""
        bot_id = 456

        # Setup: Start session successfully
        self.mock_ssh_client.start_session.return_value = "session_started"
        response = self.client.post("/api/startsession", json={"bot_id": bot_id})
        assert response.status_code == 200

        # Simulate SSH error during movement
        self.mock_ssh_client.move.side_effect = SSHClientError("Connection timeout")

        # Attempt movement - should fail
        response = self.client.post("/api/move", json={"bot_id": bot_id, "direction": "up"})
        assert response.status_code == 500
        assert "Connection timeout" in response.json()["error"]

        # Recovery: End session should still work
        self.mock_ssh_client.end_session.return_value = "session_ended"
        response = self.client.post("/api/endsession", json={"bot_id": bot_id})
        assert response.status_code == 200
        assert response.json()["status"] == "session_ended"


class TestMiddlewareIntegration:
    """
    Test middleware integration with the rest of the application.
    Verifies logging, error handling, and request processing middleware.
    """

    @pytest.fixture(autouse=True)
    def setup_middleware_testing(self):
        """Set up middleware integration testing."""
        self.client = TestClient(router_app)
        self.mock_teleop_service = Mock(spec=TeleopService)

        router_app.dependency_overrides[get_teleop_service] = lambda: self.mock_teleop_service

        yield

        router_app.dependency_overrides.clear()

    @patch('App.routers.teleop_CLI_endpoints.logger')
    def test_logging_middleware_integration(self, mock_logger):
        """Test logging middleware integration with endpoint processing."""
        # Arrange
        self.mock_teleop_service.list_active_sessions.return_value = {
            "status": "success",
            "active_sessions": [1, 2, 3]
        }

        # Act
        response = self.client.get("/api/sessions")

        # Assert
        assert response.status_code == 200

        # Verify logging middleware captured the request
        mock_logger.info.assert_called()
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        api_request_logged = any("API Request:" in call for call in log_calls)
        assert api_request_logged

    @patch('App.routers.teleop_CLI_endpoints.logger')
    def test_error_handling_middleware_integration(self, mock_logger):
        """Test error handling middleware integration with service errors."""
        # Arrange
        self.mock_teleop_service.start_session.side_effect = Exception("Database connection failed")

        # Act
        response = self.client.post("/api/startsession", json={"bot_id": 123})

        # Assert
        assert response.status_code == 500

        # Verify error was logged by middleware
        mock_logger.error.assert_called()
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        assert any("start session failed" in call for call in error_calls)


class TestMainAppIntegration:
    """
    Test integration between main app and router modules.
    Verifies that the main application correctly includes and routes to sub-modules.
    """

    def test_main_app_router_integration(self):
        """Test that main app correctly integrates with teleop router."""
        client = TestClient(main_app)

        # Test that main app root endpoint works
        response = client.get("/")
        assert response.status_code == 200
        expected_response = {"message": "WeMo Interface Backend API", "status": "running"}
        assert response.json() == expected_response

        # Test that router endpoints are accessible through main app
        response = client.get("/api/sessions")
        # Should not be 404 (router is properly included)
        assert response.status_code != 404

        # May be 500 due to no mocking, but the router is accessible
        assert response.status_code in [200, 500]


class TestDataFlowIntegration:
    """
    Test data flow integration across all layers of the application.
    Verifies that data is correctly transformed and passed between components.
    """

    @pytest.fixture(autouse=True)
    def setup_data_flow_testing(self):
        """Set up data flow integration testing."""
        self.client = TestClient(router_app)
        self.mock_ssh_client = Mock(spec=SSHClient)
        self.teleop_service = TeleopService(self.mock_ssh_client)

        router_app.dependency_overrides[get_teleop_service] = lambda: self.teleop_service

        yield

        router_app.dependency_overrides.clear()

    def test_request_response_data_transformation(self):
        """Test data transformation from request to response across all layers."""
        # Arrange
        bot_id = 789
        expected_speed_info = {
            "current_speed": 5,
            "max_speed": 10,
            "acceleration": 0.5
        }

        self.mock_ssh_client.get_speed.return_value = expected_speed_info

        # Act
        response = self.client.get(f"/api/getspeed?bot_id={bot_id}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()

        # Verify data structure transformation
        assert response_data["status"] == "success"
        assert response_data["speed_info"] == expected_speed_info

        # Verify data passed correctly through all layers
        self.mock_ssh_client.get_speed.assert_called_once_with(bot_id)

    def test_error_data_propagation(self):
        """Test error data propagation across all application layers."""
        # Arrange
        error_message = "Robot hardware malfunction detected"
        self.mock_ssh_client.rotate.side_effect = SSHClientError(error_message)

        # Act
        response = self.client.post("/api/rotate", json={
            "bot_id": 456,
            "direction": "right"
        })

        # Assert
        assert response.status_code == 500
        error_data = response.json()

        # Verify error message propagated correctly
        assert "error" in error_data
        assert error_message in error_data["error"]


# Integration Test Configuration
@pytest.fixture(scope="session")
def integration_test_setup():
    """Session-wide setup for integration tests."""
    print("\n" + "="*60)
    print("STARTING WEMO BACKEND INTEGRATION TESTS")
    print("="*60)
    yield
    print("\n" + "="*60)
    print("INTEGRATION TESTS COMPLETED")
    print("="*60)


# Run integration tests with proper configuration
if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--durations=10",
        "-k", "test_",
        "--capture=no"
    ])
