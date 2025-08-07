"""(prototype) SSH helper built on wexpect.

It starts an SSH connection, types the password, launches the tele-op
console, grabs control, and lets other parts of the app send single-
character commands to move / rotate / change speed.

Uses wexpect for proper interactive terminal handling on Windows.
"""

from __future__ import annotations

import logging
import time
from typing import Dict
import wexpect


try:
    from App.core.config import WEMOIP, WEMOPORT  # type: ignore
except ImportError as exc:
    raise RuntimeError("Failed to import WEMOIP / WEMOPORT from App.core.config") from exc

logger = logging.getLogger("SSH")


class SSHClientError(Exception):
    """Errors raised by SSHClient."""


class SSHClient:
    """SSH client wrapper using wexpect for interactive sessions."""

    def __init__(self) -> None:
        if not WEMOIP or not WEMOPORT:
            raise SSHClientError("WEMOIP / WEMOPORT not configured")

        # bot_id -> wexpect spawn object
        self._sessions: Dict[int, wexpect.spawn] = {}

    # --------------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------------
    @staticmethod
    def _is_alive(child: wexpect.spawn) -> bool:
        """Check if the wexpect session is still running."""
        return child.isalive()

    @staticmethod
    def _safe_write(child: wexpect.spawn, data: str) -> None:
        """Write data to the session."""
        try:
            child.send(data)
        except Exception as exc:
            raise SSHClientError(f"Failed to send data: {exc}")

    # --------------------------------------------------------------
    # Public API
    # --------------------------------------------------------------
    def start_session(self, bot_id: int) -> str:
        if bot_id in self._sessions and self._is_alive(self._sessions[bot_id]):
            return "Session already active"

        ssh_cmd = f"ssh -tt hive@{WEMOIP}.{bot_id + 100}"
        logger.info("Starting SSH for bot %s: %s", bot_id, ssh_cmd)

        try:
            child = wexpect.spawn(ssh_cmd, timeout=30)
            logger.debug(f"SSH session spawned for bot {bot_id}")

            # Wait for password prompt
            patterns = [
                f"hive@{WEMOIP}.{bot_id + 100}'s password: ",
                "Permission denied",
                wexpect.TIMEOUT
            ]
            index = child.expect(patterns, timeout=30)
            if index == 1:
                raise SSHClientError("SSH connection rejected - permission denied before password")
            elif index == 2:
                logger.error(f"Timeout waiting for password prompt for bot {bot_id}")
                if child.isalive():
                    child.terminate()
                raise SSHClientError(f"BOT {bot_id} is currently not active.")

            # Send password
            child.sendline("robohive")

            # Wait for authentication result
            index = child.expect([
                "Permission denied, please try again.",
                "Welcome to Ubuntu",
                f"hive@wemo{bot_id:04d}:~"
            ], timeout=10)

            if index == 0:
                raise SSHClientError("Authentication failed - incorrect password")
            elif index == 1:
                # Got welcome message, now wait for shell prompt
                child.expect(f"hive@wemo{bot_id:04d}:~", timeout=10)

            # Launch teleop console
            child.sendline("robohive_keyboard_teleop_console")

            # Wait for teleop interface
            child.expect("Available teleoperables", timeout=15)

            # Wait for robots to load before selecting
            time.sleep(10)

            # Select default robot (press ENTER)
            child.sendline("")

            # Wait for platform to be ready
            time.sleep(5)

            # Grab control
            child.send("g")

            # Wait for control to be grabbed and final warning
            try:
                child.expect(r"| WARNING - WATCH OUT FOR MOVING ROBOT", timeout=10)
            except wexpect.TIMEOUT:
                logger.error("Grabbing failed: Another operator is probably using the bot")
                if child.isalive():
                    child.terminate()
                raise SSHClientError("Grabbing failed: Another operator is probably using the bot")

        except wexpect.TIMEOUT as e:
            logger.error(f"Timeout during SSH setup: {e}")
            if 'child' in locals() and child.isalive():
                child.terminate()
            raise SSHClientError(f"Timeout during session setup for bot {bot_id}: {e}")
        except wexpect.EOF as e:
            logger.error(f"SSH connection closed unexpectedly: {e}")
            raise SSHClientError(f"SSH connection failed for bot {bot_id}: {e}")
        except Exception as e:
            logger.error(f"Error during session setup: {e}")
            if 'child' in locals() and child.isalive():
                child.terminate()
            raise SSHClientError(f"Failed to start session for bot {bot_id}: {e}")

        self._sessions[bot_id] = child
        logger.info("Session successfully started for bot %s", bot_id)
        return "Session started successfully"

    # --------------------------------------------------------------
    def end_session(self, bot_id: int) -> str:
        child = self._sessions.get(bot_id)
        if not child:
            return "No active session"

        try:
            # Release control, Ctrl+C, exit
            child.send("g")  # Release control
            time.sleep(0.3)
            child.send("\x03")  # Ctrl+C
            time.sleep(0.3)
            child.sendline("exit")
            time.sleep(0.3)
        finally:
            if child.isalive():
                child.terminate()
            self._sessions.pop(bot_id, None)
            logger.info("Session ended for bot %s", bot_id)

        return "Session ended successfully"

    # --------------------------------------------------------------
    def send_command(self, bot_id: int, command: str) -> str:
        child = self._sessions.get(bot_id)
        if not child or not self._is_alive(child):
            raise SSHClientError("No active session for this bot")

        logger.info(f"Sending command {repr(command)} to bot {bot_id}")
        try:
            self._safe_write(child, command)
            return "Command sent successfully"
        except Exception as e:
            if not self._is_alive(child):
                self._sessions.pop(bot_id, None)
                raise SSHClientError(f"Session for bot {bot_id} is no longer active") from e
            raise SSHClientError(f"Failed to send command: {e}") from e


    _ROTATE_KEYS = {"left": "<" * 5, "right": ">" * 5}
    _SPEED_KEYS = {"increase": "+", "decrease": "-"}

    _NUMPAD_KEYS = {
        "up":    "\x1bOA" * 5,    # Numpad 8
        "down":  "\x1bOB" * 5,    # Numpad 2
        "right": "\x1bOC" * 5,    # Numpad 6
        "left":  "\x1bOD" * 5,    # Numpad 4
    }


    def move(self, bot_id: int, direction: str) -> str:
        if direction not in self._NUMPAD_KEYS:
            raise SSHClientError(f"Invalid move direction: {direction}. Valid directions: {list(self._NUMPAD_KEYS.keys())}")

        command = self._NUMPAD_KEYS[direction]
        return self.send_command(bot_id, command)


    def rotate(self, bot_id: int, direction: str) -> str:
        if direction not in self._ROTATE_KEYS:
            raise SSHClientError(f"Invalid rotation direction: {direction}. Valid directions: {list(self._ROTATE_KEYS.keys())}")

        command = self._ROTATE_KEYS[direction]
        return self.send_command(bot_id, command)

    def change_speed(self, bot_id: int, action: str) -> str:
        if action not in self._SPEED_KEYS:
            raise SSHClientError(f"Invalid speed action: {action}. Valid actions: {list(self._SPEED_KEYS.keys())}")

        command = self._SPEED_KEYS[action]
        return self.send_command(bot_id, command)

    def get_speed(self, bot_id: int) -> str:
        """Get current linear speed limit value from the teleop console display."""
        child = self._sessions.get(bot_id)
        if not child or not self._is_alive(child):
            raise SSHClientError("No active session for this bot")

        # TODO: Implement proper speed detection from teleop console
        # For now, return a reasonable default value
        return "0.125"

    # --------------------------------------------------------------
    def get_session_status(self, bot_id: int) -> str:
        child = self._sessions.get(bot_id)
        if not child:
            return "No session"
        if self._is_alive(child):
            return "Active"
        else:
            self._sessions.pop(bot_id, None)
            return "Session terminated"

    def list_active_sessions(self):
        return {bid: ("Active" if self._is_alive(p) else "Terminated") for bid, p in list(self._sessions.items())}
