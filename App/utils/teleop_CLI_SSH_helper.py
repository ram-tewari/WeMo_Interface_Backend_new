#utils/teleop_CLI_SSH_helper.py
import os
import subprocess
import time
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
ssh_logger = logging.getLogger("SSH")

class SSHClientError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)

class SSHClient:
    def __init__(self):
        self.WEMOIP = os.getenv("WEMOIP")
        self.WEMOPORT = os.getenv("WEMOPORT")
        self.active_sessions = {}  # Track active sessions

    def start_session(self, bot_id: int) -> str:
        ssh_logger.info(f"Starting session for bot {bot_id}")
        try:
            if bot_id in self.active_sessions:
                return "Session already active"

            # Build the SSH command
            ssh_command = f"ssh.hive@{self.WEMOIP}{bot_id}:{self.WEMOPORT}"

            # Start the process
            process = subprocess.Popen(
                ssh_command,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Store the process
            self.active_sessions[bot_id] = process

            # Step 2: Enter password
            process.stdin.write("robohive\n")
            process.stdin.flush()
            time.sleep(1)  # Allow time for response

            # Step 3: Start teleop console
            process.stdin.write("robohive_keyboard_teleop_console\n")
            process.stdin.flush()
            time.sleep(1)

            # Step 4: Press ENTER to select robot
            process.stdin.write("\n")
            process.stdin.flush()
            time.sleep(1)

            # Step 5: Grab the bot
            process.stdin.write("g\n")
            process.stdin.flush()
            time.sleep(1)

            ssh_logger.info(f"Session started for bot {bot_id}")
            return "Session started successfully"
        except Exception as e:
            ssh_logger.error(f"Failed to start session for bot {bot_id}: {str(e)}")
            raise SSHClientError(f"Failed to start session: {str(e)}")

    def end_session(self, bot_id: int) -> str:
        ssh_logger.info(f"Ending session for bot {bot_id}")
        try:
            if bot_id not in self.active_sessions:
                return "No active session"

            process = self.active_sessions[bot_id]

            # Ungrab the bot
            process.stdin.write("g\n")
            process.stdin.flush()
            time.sleep(0.5)

            # Exit the session
            process.stdin.write("exit\n")
            process.stdin.flush()
            time.sleep(0.5)

            # Terminate the process
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()

            del self.active_sessions[bot_id]
            ssh_logger.info(f"Session ended for bot {bot_id}")
            return "Session ended successfully"
        except Exception as e:
            ssh_logger.error(f"Failed to end session for bot {bot_id}: {str(e)}")
            raise SSHClientError(f"Failed to end session: {str(e)}")

    def send_command(self, bot_id: int, command: str) -> str:
        try:
            if bot_id not in self.active_sessions:
                raise SSHClientError("No active session for this bot")

            process = self.active_sessions[bot_id]
            process.stdin.write(command + "\n")
            process.stdin.flush()
            time.sleep(0.1)  # Short delay for command processing

            return f"Command '{command}' sent"
        except Exception as e:
            ssh_logger.error(f"Failed to send command to bot {bot_id}: {str(e)}")
            raise SSHClientError(f"Failed to send command: {str(e)}")

    def change_speed(self, bot_id: int, action: str) -> str:
        keymap = {"increase": "+", "decrease": "-"}
        try:
            key = keymap[action]
            return self.send_command(bot_id, key)
        except KeyError:
            raise SSHClientError(f"Invalid speed action '{action}'")

    def move(self, bot_id: int, direction: str) -> str:
        keymap = {
            "up": "\x1b[A",    # Up arrow
            "down": "\x1b[B",  # Down arrow
            "left": "\x1b[D",  # Left arrow
            "right": "\x1b[C", # Right arrow
        }
        try:
            key = keymap[direction]
            return self.send_command(bot_id, key)
        except KeyError:
            raise SSHClientError(f"Invalid direction '{direction}'")

    def rotate(self, bot_id: int, direction: str) -> str:
        keymap = {"left": "<", "right": ">"}
        try:
            key = keymap[direction]
            return self.send_command(bot_id, key)
        except KeyError:
            raise SSHClientError(f"Invalid rotation '{direction}'")