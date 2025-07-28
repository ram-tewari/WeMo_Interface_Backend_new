import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from App.routers.teleop_CLI_endpoints import app, get_teleop_service

client = TestClient(app)

@pytest.fixture
def mock_ssh_client():
    return MagicMock()

@pytest.fixture
def mock_teleop_service(mock_ssh_client):
    service = MagicMock()
    service.start_session.return_value = {"Status": "Session started"}
    service.end_session.return_value = {"Status": "Session ended"}
    service.change_speed.return_value = {"status": "Speed changed"}
    service.move.return_value = {"status": "Moved"}
    service.rotate.return_value = {"status": "Rotated"}
    return service

def override_dependency():
    return mock_teleop_service

def test_start_session_success(mock_teleop_service):
    with patch.object(app, 'dependency_overrides', {get_teleop_service: lambda: mock_teleop_service}):
        resp = client.post("/api/startsession", json={"bot_id": 1})
        assert resp.status_code == 200
        assert resp.json() == {"Status": "Session started"}

def test_end_session_success(mock_teleop_service):
    with patch.object(app, 'dependency_overrides', {get_teleop_service: lambda: mock_teleop_service}):
        resp = client.post("/api/endsession", json={"bot_id": 1})
        assert resp.status_code == 200
        assert resp.json() == {"Status": "Session ended"}

def test_speed_increase_success(mock_teleop_service):
    with patch.object(app, 'dependency_overrides', {get_teleop_service: lambda: mock_teleop_service}):
        resp = client.post("/api/speed", json={"bot_id": 1, "action": "increase"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "Speed changed"}

def test_speed_decrease_success(mock_teleop_service):
    with patch.object(app, 'dependency_overrides', {get_teleop_service: lambda: mock_teleop_service}):
        resp = client.post("/api/speed", json={"bot_id": 1, "action": "decrease"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "Speed changed"}

def test_move_up_success(mock_teleop_service):
    with patch.object(app, 'dependency_overrides', {get_teleop_service: lambda: mock_teleop_service}):
        resp = client.post("/api/move", json={"bot_id": 1, "direction": "up"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "Moved"}

def test_rotate_left_success(mock_teleop_service):
    with patch.object(app, 'dependency_overrides', {get_teleop_service: lambda: mock_teleop_service}):
        resp = client.post("/api/rotate", json={"bot_id": 1, "direction": "left"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "Rotated"}


def test_get_speed_success():
    resp = client.get("/api/getspeed", params={"bot_id": 1})
    assert resp.status_code == 200
    assert resp.json() == {"bot_id": 1, "speed": 0.2}

def test_get_speed_missing_botid():
    resp = client.get("/api/getspeed")
    assert resp.status_code == 422