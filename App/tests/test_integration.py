import pytest
from fastapi.testclient import TestClient
from App.routers.teleop_CLI_endpoints import app, get_teleop_service
from App.services.teleop_CLI_services import TeleopService
from App.utils.teleop_CLI_SSH_helper import SSHClient, SSHClientError

client = TestClient(app)


# Fixture to override dependencies for all tests
@pytest.fixture(autouse=True)
def override_dependencies():
    # Create mock SSH client with proper method signatures
    class MockSSHClient(SSHClient):
        def start_session(self, bot_id: int) -> str:
            if bot_id == 999:
                raise SSHClientError("SSH connection failed")
            return f"Session started for bot {bot_id}"

        def end_session(self, bot_id: int) -> str:
            if bot_id == 999:
                raise SSHClientError("SSH session error")
            return f"Session ended for bot {bot_id}"

        def change_speed(self, bot_id: int, action: str) -> str:
            if bot_id == 999:
                raise SSHClientError("Speed change failed")
            return f"Speed {action}d for bot {bot_id}"

        def move(self, bot_id: int, direction: str) -> str:
            if bot_id == 999:
                raise SSHClientError("Move command failed")
            return f"Moved {direction} for bot {bot_id}"

        def rotate(self, bot_id: int, direction: str) -> str:
            if bot_id == 999:
                raise SSHClientError("Rotate command failed")
            return f"Rotated {direction} for bot {bot_id}"

    # Create service with mock SSH client
    mock_service = TeleopService(MockSSHClient())

    # Override dependency
    app.dependency_overrides[get_teleop_service] = lambda: mock_service
    yield
    # Clean up after tests
    app.dependency_overrides = {}


# Test cases
def test_start_session_success():
    response = client.post("/api/startsession", json={"bot_id": 1})
    assert response.status_code == 200
    assert response.json() == {"Status": "Session started for bot 1"}


def test_start_session_invalid_bot_id():
    response = client.post("/api/startsession", json={"bot_id": 0})
    assert response.status_code == 422
    assert "greater than 0" in response.text


def test_start_session_error():
    response = client.post("/api/startsession", json={"bot_id": 999})
    assert response.status_code == 500
    assert "SSH connection failed" in response.text


def test_end_session_success():
    response = client.post("/api/endsession", json={"bot_id": 1})
    assert response.status_code == 200
    assert response.json() == {"Status": "Session ended for bot 1"}


def test_end_session_invalid_bot_id():
    response = client.post("/api/endsession", json={"bot_id": -1})
    assert response.status_code == 422
    assert "greater than 0" in response.text


def test_end_session_error():
    response = client.post("/api/endsession", json={"bot_id": 999})
    assert response.status_code == 500
    assert "SSH session error" in response.text


def test_change_speed_increase_success():
    response = client.post("/api/speed", json={"bot_id": 1, "action": "increase"})
    assert response.status_code == 200
    assert response.json() == {"status": "Speed increased for bot 1"}


def test_change_speed_decrease_success():
    response = client.post("/api/speed", json={"bot_id": 1, "action": "decrease"})
    assert response.status_code == 200
    assert response.json() == {"status": "Speed decreased for bot 1"}


def test_change_speed_invalid_action():
    response = client.post("/api/speed", json={"bot_id": 1, "action": "invalid"})
    assert response.status_code == 422
    error_detail = response.json()["detail"][0]
    assert error_detail["type"] == "string_pattern_mismatch"
    assert error_detail["loc"] == ["body", "action"]
    assert "pattern" in error_detail["msg"]


def test_change_speed_error():
    response = client.post("/api/speed", json={"bot_id": 999, "action": "increase"})
    assert response.status_code == 500
    assert "Speed change failed" in response.text


def test_move_success():
    for direction in ["up", "down", "left", "right"]:
        response = client.post("/api/move", json={"bot_id": 1, "direction": direction})
        assert response.status_code == 200
        assert response.json() == {"status": f"Moved {direction} for bot 1"}


def test_move_invalid_direction():
    response = client.post("/api/move", json={"bot_id": 1, "direction": "invalid"})
    assert response.status_code == 422
    error_detail = response.json()["detail"][0]
    assert error_detail["type"] == "string_pattern_mismatch"
    assert error_detail["loc"] == ["body", "direction"]
    assert "pattern" in error_detail["msg"]


def test_move_error():
    response = client.post("/api/move", json={"bot_id": 999, "direction": "up"})
    assert response.status_code == 500
    assert "Move command failed" in response.text


def test_rotate_success():
    for direction in ["left", "right"]:
        response = client.post("/api/rotate", json={"bot_id": 1, "direction": direction})
        assert response.status_code == 200
        assert response.json() == {"status": f"Rotated {direction} for bot 1"}


def test_rotate_invalid_direction():
    response = client.post("/api/rotate", json={"bot_id": 1, "direction": "invalid"})
    assert response.status_code == 422
    error_detail = response.json()["detail"][0]
    assert error_detail["type"] == "string_pattern_mismatch"
    assert error_detail["loc"] == ["body", "direction"]
    assert "pattern" in error_detail["msg"]


def test_rotate_error():
    response = client.post("/api/rotate", json={"bot_id": 999, "direction": "left"})
    assert response.status_code == 500
    assert "Rotate command failed" in response.text


def test_get_speed_success():
    response = client.get("/api/getspeed", params={"bot_id": 1})
    assert response.status_code == 200
    assert response.json() == {"bot_id": 1, "speed": 0.2}


def test_get_speed_missing_bot_id():
    response = client.get("/api/getspeed")
    assert response.status_code == 422
    assert "missing" in response.text