#utils/teleop_CLI_SSH_helper.py
import os
import subprocess
import time
import logging
import threading
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

    def _read_output(self, process, bot_id):
        """Background thread to read process output for debugging"""
        try:
            while process.poll() is None:
                output = process.stdout.readline()
                if output:
                    ssh_logger.debug(f"Bot {bot_id} output: {output.strip()}")
        except:
            pass

    def start_session(self, bot_id: int) -> str:
        ssh_logger.info(f"Starting session for bot {bot_id}")
        try:
            if bot_id in self.active_sessions:
                return "Session already active"

            # Build the correct SSH command with proper format
            # ssh username@hostname -p port
            ssh_command = ["ssh", f"hive@{self.WEMOIP}{bot_id}", "-p", str(self.WEMOPORT)]
            ssh_logger.info(f"Executing SSH command: {' '.join(ssh_command)}")

            # Start the SSH process
            process = subprocess.Popen(
                ssh_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0  # Unbuffered
            )

            # Store the process
            self.active_sessions[bot_id] = process

            # Start background thread to read output
            output_thread = threading.Thread(target=self._read_output, args=(process, bot_id))
            output_thread.daemon = True
            output_thread.start()

            # Give SSH time to establish connection and show password prompt
            time.sleep(2)

            # Step 2: Enter password
            ssh_logger.info("Sending password...")
            process.stdin.write("robohive\n")
            process.stdin.flush()
            time.sleep(3)  # Allow time for authentication and shell prompt

            # Step 3: Start teleop console
            ssh_logger.info("Starting robohive_keyboard_teleop_console...")
            process.stdin.write("robohive_keyboard_teleop_console\n")
            process.stdin.flush()
            time.sleep(3)  # Allow time for console to start

            # Step 4: Press ENTER to select robot
            ssh_logger.info("Pressing ENTER to select robot...")
            process.stdin.write("\n")
            process.stdin.flush()
            time.sleep(2)

            # Step 5: Grab the bot
            ssh_logger.info("Sending 'g' to grab the bot...")
            process.stdin.write("g\n")
            process.stdin.flush()
            time.sleep(1)

            ssh_logger.info(f"Session started successfully for bot {bot_id}")
            return "Session started successfully"
            
        except Exception as e:
            ssh_logger.error(f"Failed to start session for bot {bot_id}: {str(e)}")
            # Clean up if process was created
            if bot_id in self.active_sessions:
                try:
                    self.active_sessions[bot_id].terminate()
                    del self.active_sessions[bot_id]
                except:
                    pass
            raise SSHClientError(f"Failed to start session: {str(e)}")

    def end_session(self, bot_id: int) -> str:
        ssh_logger.info(f"Ending session for bot {bot_id}")
        try:
            if bot_id not in self.active_sessions:
                return "No active session"

            process = self.active_sessions[bot_id]

            # Ungrab the bot
            ssh_logger.info("Ungrapping the bot...")
            process.stdin.write("g\n")
            process.stdin.flush()
            time.sleep(0.5)

            # Exit the teleop console (Ctrl+C)
            ssh_logger.info("Exiting teleop console...")
            process.stdin.write("\x03")  # Send Ctrl+C
            process.stdin.flush()
            time.sleep(1)
            
            # Exit the SSH session
            ssh_logger.info("Exiting SSH session...")
            process.stdin.write("exit\n")
            process.stdin.flush()
            time.sleep(1)

            # Terminate the process if still running
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    ssh_logger.warning(f"Force killing SSH process for bot {bot_id}")
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
            
            # Check if process is still alive
            if process.poll() is not None:
                raise SSHClientError("SSH session has terminated")
                
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