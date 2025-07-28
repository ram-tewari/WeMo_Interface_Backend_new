#services/teleop_CLI_services.py
from fastapi import BackgroundTasks
from starlette import status
from App.utils.teleop_CLI_SSH_helper import SSHClient, SSHClientError


class TeleopService:
    def __init__(self, ssh_client=None):
        self.sshclient = ssh_client if ssh_client else SSHClient()

    def start_session(self, bot_id: int) -> dict:
        try:
            result = self.sshclient.start_session(bot_id)
            return {"Status": result}
        except Exception as e:
            raise SSHClientError(f"Failed to start session: {str(e)}")

    def end_session(self, bot_id: int) -> dict:
        try:
            result = self.sshclient.end_session(bot_id)
            return {"Status": result}
        except Exception as e:
            raise SSHClientError(f"Failed to end session: {str(e)}")


    def change_speed(self, bot_id: int, action: str) -> dict:
        try:
            result = self.sshclient.change_speed(bot_id, action)
            return {"status": result}
        except Exception as e:
            raise SSHClientError(f"Failed to change speed: {str(e)}")

    def move(self, bot_id: int, direction: str) -> dict:
        try:
            result = self.sshclient.move(bot_id, direction)
            return {"status": result}
        except Exception as e:
            raise SSHClientError(f"Failed to move: {str(e)}")

    def rotate(self, bot_id: int, direction: str) -> dict:
        try:
            result = self.sshclient.rotate(bot_id, direction)
            return {"status": result}
        except Exception as e:
            raise SSHClientError(f"Failed to rotate: {str(e)}")