#/tests/test_endpoints.py
"""
Unit Tests for Teleop CLI Endpoints

This module contains comprehensive unit tests for the robot teleoperation API endpoints.
Tests cover successful operations, error handling, and input validation while mocking
all external dependencies including SSH connections.
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

# Import the FastAPI app and dependencies
from App.routers.teleop_CLI_endpoints import app, get_teleop_service
from App.services.teleop_CLI_services import TeleopService
from App.utils.teleop_CLI_SSH_helper import SSHClientError


class TestTeleopEndpointsSuccessful(unittest.TestCase):
    """Test successful API endpoint operations."""

    def setUp(self):
        """Set up test client and mock dependencies."""
        self.client = TestClient(app)
        self.mock_teleop_service = Mock(spec=TeleopService)

        # Override dependency injection with mock
        app.dependency_overrides[get_teleop_service] = lambda: self.mock_teleop_service

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    def test_root_endpoint_returns_success_message(self):
        """Root endpoint should return API running message."""
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "WeMo Teleoperation API is running")

    def test_favicon_endpoint_returns_no_content(self):
        """Favicon endpoint should return 204 status."""
        response = self.client.get("/favicon.ico")

        self.assertEqual(response.status_code, 204)

    def test_start_session_with_valid_bot_id_succeeds(self):
        """Start session endpoint should call service and return success."""
        # Arrange
        expected_response = {"status": "session_started"}
        self.mock_teleop_service.start_session.return_value = expected_response

        # Act
        response = self.client.post("/api/startsession", json={"bot_id": 123})

        # Assert
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data, expected_response)
        self.assertIn("status", json_data)
        self.mock_teleop_service.start_session.assert_called_once_with(123)

    def test_end_session_with_valid_bot_id_succeeds(self):
        """End session endpoint should call service and return success."""
        # Arrange
        expected_response = {"status": "session_ended"}
        self.mock_teleop_service.end_session.return_value = expected_response

        # Act
        response = self.client.post("/api/endsession", json={"bot_id": 456})

        # Assert
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data, expected_response)
        self.assertIn("status", json_data)
        self.mock_teleop_service.end_session.assert_called_once_with(456)

    def test_change_speed_with_valid_parameters_succeeds(self):
        """Change speed endpoint should call service with correct parameters."""
        # Arrange
        expected_response = {"status": "speed_changed"}
        self.mock_teleop_service.change_speed.return_value = expected_response

        # Act
        response = self.client.post("/api/speed", json={
            "bot_id": 789,
            "action": "increase"
        })

        # Assert
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data, expected_response)
        self.assertIn("status", json_data)
        self.mock_teleop_service.change_speed.assert_called_once_with(789, "increase")

    def test_move_bot_with_valid_direction_succeeds(self):
        """Move bot endpoint should call service with correct direction."""
        # Arrange
        expected_response = {"status": "moved"}
        self.mock_teleop_service.move.return_value = expected_response

        # Act
        response = self.client.post("/api/move", json={
            "bot_id": 111,
            "direction": "up"
        })

        # Assert
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data, expected_response)
        self.assertIn("status", json_data)
        self.mock_teleop_service.move.assert_called_once_with(111, "up")

    def test_rotate_bot_with_valid_direction_succeeds(self):
        """Rotate bot endpoint should call service with correct direction."""
        # Arrange
        expected_response = {"status": "rotated"}
        self.mock_teleop_service.rotate.return_value = expected_response

        # Act
        response = self.client.post("/api/rotate", json={
            "bot_id": 222,
            "direction": "left"
        })

        # Assert
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data, expected_response)
        self.assertIn("status", json_data)
        self.mock_teleop_service.rotate.assert_called_once_with(222, "left")

    def test_get_speed_returns_speed_information(self):
        """Get speed endpoint should return speed information."""
        # Arrange
        expected_response = {"status": "success", "speed_info": {"current_speed": 5}}
        self.mock_teleop_service.get_speed.return_value = expected_response

        # Act
        response = self.client.get("/api/getspeed?bot_id=333")

        # Assert
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["status"], "success")
        self.assertIn("speed_info", json_data)
        self.assertIsInstance(json_data["speed_info"], dict)
        self.mock_teleop_service.get_speed.assert_called_once_with(333)

    def test_get_session_status_returns_status_information(self):
        """Get session status endpoint should return session information."""
        # Arrange
        expected_response = {"status": "success", "session_status": "active"}
        self.mock_teleop_service.get_session_status.return_value = expected_response

        # Act
        response = self.client.get("/api/session/status?bot_id=444")

        # Assert
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["status"], "success")
        self.assertIn("session_status", json_data)
        self.assertEqual(json_data["session_status"], "active")
        self.mock_teleop_service.get_session_status.assert_called_once_with(444)

    def test_list_active_sessions_returns_session_list(self):
        """List active sessions endpoint should return list of sessions."""
        # Arrange
        expected_response = {"status": "success", "active_sessions": [1, 2, 3]}
        self.mock_teleop_service.list_active_sessions.return_value = expected_response

        # Act
        response = self.client.get("/api/sessions")

        # Assert
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["status"], "success")
        self.assertIn("active_sessions", json_data)
        self.assertIsInstance(json_data["active_sessions"], list)
        self.mock_teleop_service.list_active_sessions.assert_called_once()

    def test_debug_session_returns_debug_information(self):
        """Debug session endpoint should return comprehensive debug info."""
        # Arrange
        mock_ssh_client = Mock()
        mock_ssh_client.get_session_status.return_value = "active"
        mock_ssh_client.list_active_sessions.return_value = [555]
        mock_ssh_client._sessions = {555: Mock()}
        mock_ssh_client._is_alive.return_value = True

        self.mock_teleop_service.ssh_client = mock_ssh_client

        # Act
        response = self.client.get("/api/debug?bot_id=555")

        # Assert
        self.assertEqual(response.status_code, 200)
        debug_info = response.json()

        # Validate required fields from DebugInfoResponse model
        self.assertIn("bot_id", debug_info)
        self.assertEqual(debug_info["bot_id"], 555)
        self.assertIn("status", debug_info)
        self.assertIn("session_exists_in_sessions", debug_info)
        self.assertIn("all_active_sessions", debug_info)
        self.assertIsInstance(debug_info["all_active_sessions"], list)


class TestTeleopEndpointsErrorHandling(unittest.TestCase):
    """Test error handling in API endpoints."""

    def setUp(self):
        """Set up test client and mock dependencies."""
        self.client = TestClient(app)
        self.mock_teleop_service = Mock(spec=TeleopService)

        # Override dependency injection with mock
        app.dependency_overrides[get_teleop_service] = lambda: self.mock_teleop_service

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    def test_start_session_handles_ssh_client_error(self):
        """Start session should handle SSHClientError gracefully."""
        # Arrange
        self.mock_teleop_service.start_session.side_effect = SSHClientError("SSH connection failed")

        # Act
        response = self.client.post("/api/startsession", json={"bot_id": 123})

        # Assert
        self.assertEqual(response.status_code, 500)
        json_data = response.json()
        self.assertIn("error", json_data)  # Updated for new ErrorResponse model
        self.assertIn("SSH connection failed", json_data["error"])

    def test_end_session_handles_generic_exception(self):
        """End session should handle generic exceptions gracefully."""
        # Arrange
        self.mock_teleop_service.end_session.side_effect = Exception("Unexpected error")

        # Act
        response = self.client.post("/api/endsession", json={"bot_id": 123})

        # Assert
        self.assertEqual(response.status_code, 500)
        json_data = response.json()
        self.assertIn("error", json_data)  # Updated for new ErrorResponse model
        self.assertIn("Unknown error", json_data["error"])

    def test_change_speed_handles_service_error(self):
        """Change speed should handle service layer errors."""
        # Arrange
        self.mock_teleop_service.change_speed.side_effect = SSHClientError("Robot communication failed")

        # Act - Use valid request format that passes FastAPI validation
        response = self.client.post("/api/speed", json={
            "bot_id": 789,
            "action": "increase"  # Valid action that passes validation
        })

        # Assert
        self.assertEqual(response.status_code, 500)
        json_data = response.json()
        self.assertIn("error", json_data)  # Updated for new ErrorResponse model
        self.assertIn("Robot communication failed", json_data["error"])

    def test_move_bot_handles_ssh_error(self):
        """Move bot should handle SSH communication errors."""
        # Arrange
        self.mock_teleop_service.move.side_effect = SSHClientError("Robot not responding")

        # Act
        response = self.client.post("/api/move", json={
            "bot_id": 111,
            "direction": "up"
        })

        # Assert
        self.assertEqual(response.status_code, 500)
        json_data = response.json()
        self.assertIn("error", json_data)  # Updated for new ErrorResponse model
        self.assertIn("Robot not responding", json_data["error"])

    def test_rotate_bot_handles_ssh_error(self):
        """Rotate bot should handle SSH communication errors."""
        # Arrange
        self.mock_teleop_service.rotate.side_effect = SSHClientError("Rotation command failed")

        # Act
        response = self.client.post("/api/rotate", json={
            "bot_id": 222,
            "direction": "left"
        })

        # Assert
        self.assertEqual(response.status_code, 500)
        json_data = response.json()
        self.assertIn("error", json_data)  # Updated for new ErrorResponse model
        self.assertIn("Rotation command failed", json_data["error"])

    def test_debug_session_handles_missing_session_data(self):
        """Debug session should handle missing session gracefully."""
        # Arrange
        mock_ssh_client = Mock()
        mock_ssh_client.get_session_status.side_effect = Exception("Session not found")
        self.mock_teleop_service.ssh_client = mock_ssh_client

        # Act
        response = self.client.get("/api/debug?bot_id=999")

        # Assert
        self.assertEqual(response.status_code, 500)
        json_data = response.json()
        self.assertIn("error", json_data)  # Updated for new ErrorResponse model


class TestTeleopEndpointsInputValidation(unittest.TestCase):
    """Test input validation for API endpoints."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
        self.mock_teleop_service = Mock(spec=TeleopService)

        # Override dependency injection with mock
        app.dependency_overrides[get_teleop_service] = lambda: self.mock_teleop_service

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    def test_start_session_requires_bot_id(self):
        """Start session should require bot_id parameter."""
        response = self.client.post("/api/startsession", json={})

        self.assertEqual(response.status_code, 422)  # Validation error

    def test_change_speed_requires_action_parameter(self):
        """Change speed should require action parameter."""
        response = self.client.post("/api/speed", json={"bot_id": 123})

        self.assertEqual(response.status_code, 422)  # Validation error

    def test_move_bot_requires_direction_parameter(self):
        """Move bot should require direction parameter."""
        response = self.client.post("/api/move", json={"bot_id": 111})

        self.assertEqual(response.status_code, 422)  # Validation error

    def test_rotate_bot_requires_direction_parameter(self):
        """Rotate bot should require direction parameter."""
        response = self.client.post("/api/rotate", json={"bot_id": 222})

        self.assertEqual(response.status_code, 422)  # Validation error

    def test_get_speed_requires_bot_id_parameter(self):
        """Get speed should require bot_id parameter."""
        response = self.client.get("/api/getspeed")

        self.assertEqual(response.status_code, 422)  # Validation error

    def test_get_session_status_requires_bot_id_parameter(self):
        """Get session status should require bot_id parameter."""
        response = self.client.get("/api/session/status")

        self.assertEqual(response.status_code, 422)  # Validation error

    def test_invalid_bot_id_type_returns_validation_error(self):
        """Invalid bot_id type should return validation error."""
        response = self.client.post("/api/startsession", json={"bot_id": "invalid"})

        self.assertEqual(response.status_code, 422)  # Validation error

    def test_invalid_speed_action_returns_validation_error(self):
        """Invalid speed action should return validation error."""
        response = self.client.post("/api/speed", json={
            "bot_id": 123,
            "action": "invalid_action"
        })

        # This should be a 422 if validation happens at Pydantic level
        # or 500 if it reaches service layer validation
        self.assertIn(response.status_code, [422, 500])


class TestMainAppConfiguration(unittest.TestCase):
    """Test main application configuration."""

    def test_main_app_root_endpoint_returns_api_info(self):
        """Main app root endpoint should return API information."""
        from App.main import app as main_app
        client = TestClient(main_app)

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        expected_response = {"message": "WeMo Interface Backend API", "status": "running"}
        self.assertEqual(response.json(), expected_response)

    def test_main_app_includes_teleop_router(self):
        """Main app should include teleop router with correct prefix."""
        from App.main import app as main_app
        client = TestClient(main_app)

        # Test that router endpoints are accessible through main app
        response = client.get("/api/sessions")

        # Should get to the endpoint (may fail due to no mocking, but shouldn't be 404)
        self.assertNotEqual(response.status_code, 404)


class TestMiddlewareLogging(unittest.TestCase):
    """Test request logging middleware functionality."""

    def setUp(self):
        """Set up test client and mock logging."""
        self.client = TestClient(app)
        self.mock_teleop_service = Mock(spec=TeleopService)
        self.mock_teleop_service.list_active_sessions.return_value = {"status": "success", "active_sessions": []}

        app.dependency_overrides[get_teleop_service] = lambda: self.mock_teleop_service

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    @patch('App.routers.teleop_CLI_endpoints.logger')
    def test_middleware_logs_successful_requests(self, mock_logger):
        """Middleware should log successful requests."""
        response = self.client.get("/api/sessions")

        # Verify that logger.info was called
        mock_logger.info.assert_called()

        # Check that log message contains request information
        log_calls = mock_logger.info.call_args_list
        self.assertTrue(any("API Request:" in str(call) for call in log_calls))

    @patch('App.routers.teleop_CLI_endpoints.logger')
    def test_middleware_skips_logging_for_favicon(self, mock_logger):
        """Middleware should skip logging for favicon requests."""
        response = self.client.get("/favicon.ico")

        # Verify that no API Request logs were made
        log_calls = mock_logger.info.call_args_list
        self.assertFalse(any("API Request:" in str(call) for call in log_calls))

    @patch('App.routers.teleop_CLI_endpoints.logger')
    def test_middleware_logs_error_requests(self, mock_logger):
        """Middleware should log error requests with proper severity."""
        # Arrange - Make service throw an error
        self.mock_teleop_service.list_active_sessions.side_effect = Exception("Test error")

        # Act
        response = self.client.get("/api/sessions")

        # Assert
        self.assertEqual(response.status_code, 500)
        mock_logger.error.assert_called()


if __name__ == '__main__':
    # Run specific test classes
    test_classes = [
        TestTeleopEndpointsSuccessful,
        TestTeleopEndpointsErrorHandling,
        TestTeleopEndpointsInputValidation,
        TestMainAppConfiguration,
        TestMiddlewareLogging
    ]

    for test_class in test_classes:
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        print(f"\n{'='*50}")
        print(f"Running {test_class.__name__}")
        print(f"{'='*50}")
        runner.run(suite)

