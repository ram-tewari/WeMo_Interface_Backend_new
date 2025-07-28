#FORMER FILE FOR SSH
from contextlib import contextmanager
from datetime import time

from dotenv import load_dotenv
import os
import paramiko


#get SSH connection properties
load_dotenv()

#facilitates direct SSH/CLI interactions via paramiko shells

# Custom error for consistent handling
class SSHClientError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)

class SSHClient:
    def __init__(self): #host, port, username, password, injected from the .env file
        self.WEMOIP = os.getenv("WEMOIP")
        self.WEMOPORT = os.getenv("WEMOPORT")
        self.host = os.getenv("SSH_HOST")
        self.port = os.getenv("SSH_PORT")
        self.username = os.getenv("SSH_USERNAME")
        self.password = os.getenv("SSH_PASSWORD")
        self.active_channels = {} #tracks open channels

    @contextmanager
    def connection(self):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.host, self.port, self.username, self.password)
            yield client
        except paramiko.AuthenticationException as e:
            raise SSHClientError("SSH authentication failed: " + str(e))
        except paramiko.SSHException as e:
            raise SSHClientError("SSH session error: " + str(e))
        except Exception as e:
            raise SSHClientError("SSH connection error: " + str(e))
        finally:
            try:
                client.close()
            except Exception:
                pass

    #send CLI commands to connect and grab the robot
    def start_session(self, bot_id: int) -> str:
        try:
            if bot_id in self.active_channels:
                return "Session already active"

            with self.connection() as client:
                channel = client.invoke_shell() #opens the shell to send CLI commands for grabbing teleop control
                self.active_channels[bot_id] = channel #stores channel for future commands

                #send commands
                commands = [
                    f"ssh.hive@{self.WEMOIP}{bot_id}:{self.WEMOPORT}", #CLI connects to robot
                    "robohive", #password
                    "robohive_keyboard_teleop_console",  #CLI opens console
                    "g" # 'g' to grab the robot
                ]

                for cmd in commands:
                    channel.send(cmd + "\n")
                    time.sleep(0.5) #time for command processing

                return "session started"
        except Exception as e:
            raise SSHClientError("Failed to start session: " + str(e))

    #sends CLI commands to ungrab the robot and end the session
    def end_session(self, bot_id:int) -> str:
        try:
            if bot_id not in self.active_channels:
                return "no active session"

            channel = self.active_channels[bot_id]
            channel.send(f"g\n") #press 'g' once again to ungrab the robot
            return channel.close()
            del self.active_channels[bot_id] #remove from active channels
            return "session ended"

        except Exception as e:
            raise SSHClientError("Failed to end session: " + str(e))

    #sends CLI commands to increase/decrease speed
    def change_speed(self, bot_id: int, action: str) -> str:
        """
        Sends '+' to increase speed or '-' to decrease speed via the CLI.
        """
        keymap = {
            "increase": "+",
            "decrease": "-"
        }
        try:
            if bot_id not in self.active_channels:
                raise SSHClientError("No active session for this bot")

            key = keymap[action]
            channel = self.active_channels[bot_id]
            channel.send(key)
            return f"Speed {action}d"
        except KeyError:
            raise SSHClientError(f"Invalid speed action '{action}'. Must be 'increase' or 'decrease'.")
        except Exception as e:
            raise SSHClientError("Failed to change speed: " + str(e))

    #sends CLI commands to move robot in specified direction at set speed
    def move(self, bot_id: int, direction: str, speed: float) -> str:
        """
        sends the correct arrow key for robot movement
        """

        keymap = {
            "up": "xlb[A", #Up arrow
            "down": "xlb[B", #Down arrow
            "left": "xlb[D", #Left arrow
            "right": "xlb[E", #Right arrow
        }
        try:
            if bot_id not in self.active_channels:
                raise SSHClientError("No active session for this bot")

            arrow_key = keymap[direction]

            channel = self.active_channels[bot_id]
            channel.send(arrow_key)
            return f"Moved {direction}"

        except KeyError:
            raise SSHClientError(f"Invalid move direction '{direction}'. Must be one of {list(keymap.keys())}.")
        except Exception as e:
            raise SSHClientError("Failed to move robot: " + str(e))

    #sends CLI commands to rotate robot in a given direction(left or right)
    def rotate(self, bot_id: int, direction: str) -> str:
        """
        Sends '<' to rotate to the left and '>' to rotate to the right
        """

        keymap = {
            "left": "<",
            "right": ">",
        }

        try:
            if bot_id not in self.active_channels:
                raise SSHClientError("No active session for this bot")

            key = keymap[direction]
            channel = self.active_channels[bot_id]
            channel.send(key)
            return f"Rotated {direction}"
        except KeyError:
            raise SSHClientError(f"Invalid rotation '{direction}'")
        except Exception as e:
            raise SSHClientError("Failed to rotate: " + str(e))

