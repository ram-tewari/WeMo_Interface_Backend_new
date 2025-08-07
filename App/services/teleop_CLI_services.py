#services/teleop_CLI_services.py
"""
Teleop CLI Services Module

This module provides teleoperation services for robot control via SSH.
Handles session management, movement commands, and status monitoring.
"""

import logging
from functools import wraps
from typing import Dict, List

from App.utils.teleop_CLI_SSH_helper import SSHClient, SSHClientError

logger = logging.getLogger(__name__)


def handle_ssh_errors(operation_name: str):
    """
    Decorator to handle SSH errors consistently across all methods.

    Args:
        operation_name: Name of the operation for logging purposes
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except SSHClientError as e:
                logger.error(f"SSH error during {operation_name}: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error during {operation_name}: {e}")
                raise SSHClientError(f"Failed to {operation_name}: {str(e)}")
        return wrapper
    return decorator


class TeleopService:
    """
    Service class for handling robot teleoperation commands.

    Provides methods for session management, movement control, and status monitoring
    through SSH connections to robot controllers.
    """

    # Valid command parameters
    VALID_SPEED_ACTIONS = ["increase", "decrease"]
    VALID_MOVE_DIRECTIONS = ["up", "down", "left", "right"]
    VALID_ROTATION_DIRECTIONS = ["left", "right"]

    def __init__(self, ssh_client: SSHClient = None):
        """
        Initialize the teleop service.

        Args:
            ssh_client: Optional SSH client instance. Creates new one if not provided.
        """
        self.ssh_client = ssh_client if ssh_client else SSHClient()

    def _validate_parameter(self, parameter: str, valid_options: List[str],
                            parameter_name: str) -> None:
        """
        Validate command parameters against allowed values.

        Args:
            parameter: The parameter value to validate
            valid_options: List of valid parameter values
            parameter_name: Name of the parameter for error messages

        Raises:
            SSHClientError: If parameter is not in valid options
        """
        if parameter not in valid_options:
            raise SSHClientError(
                f"Invalid {parameter_name}: {parameter}. "
                f"Valid options: {valid_options}"
            )

    @handle_ssh_errors("start session")
    def start_session(self, bot_id: int) -> Dict[str, str]:
        """
        Start a teleop session for the specified bot.

        Args:
            bot_id: Unique identifier for the robot

        Returns:
            Dictionary containing operation status
        """
        logger.info(f"Starting teleop session for bot {bot_id}")
        result = self.ssh_client.start_session(bot_id)
        logger.info(f"Successfully started session for bot {bot_id}")
        return {"status": result}

    @handle_ssh_errors("end session")
    def end_session(self, bot_id: int) -> Dict[str, str]:
        """
        End the teleop session for the specified bot.

        Args:
            bot_id: Unique identifier for the robot

        Returns:
            Dictionary containing operation status
        """
        logger.info(f"Ending teleop session for bot {bot_id}")
        result = self.ssh_client.end_session(bot_id)
        logger.info(f"Successfully ended session for bot {bot_id}")
        return {"status": result}

    @handle_ssh_errors("change speed")
    def change_speed(self, bot_id: int, action: str) -> Dict[str, str]:
        """
        Change the speed of the robot (increase/decrease).

        Args:
            bot_id: Unique identifier for the robot
            action: Speed change action ('increase' or 'decrease')

        Returns:
            Dictionary containing operation status
        """
        logger.info(f"Changing speed for bot {bot_id}: {action}")

        # Validate action parameter
        self._validate_parameter(action, self.VALID_SPEED_ACTIONS, "speed action")

        result = self.ssh_client.change_speed(bot_id, action)
        logger.info(f"Successfully changed speed for bot {bot_id}: {action}")
        return {"status": result}

    @handle_ssh_errors("move robot")
    def move(self, bot_id: int, direction: str) -> Dict[str, str]:
        """
        Move the robot in the specified direction.

        Args:
            bot_id: Unique identifier for the robot
            direction: Movement direction ('up', 'down', 'left', 'right')

        Returns:
            Dictionary containing operation status
        """
        logger.info(f"Moving bot {bot_id} in direction: {direction}")

        # Validate direction parameter
        self._validate_parameter(direction, self.VALID_MOVE_DIRECTIONS, "move direction")

        result = self.ssh_client.move(bot_id, direction)
        logger.info(f"Successfully moved bot {bot_id} {direction}")
        return {"status": result}

    @handle_ssh_errors("rotate robot")
    def rotate(self, bot_id: int, direction: str) -> Dict[str, str]:
        """
        Rotate the robot in the specified direction.

        Args:
            bot_id: Unique identifier for the robot
            direction: Rotation direction ('left' or 'right')

        Returns:
            Dictionary containing operation status
        """
        logger.info(f"Rotating bot {bot_id} in direction: {direction}")

        # Validate direction parameter
        self._validate_parameter(direction, self.VALID_ROTATION_DIRECTIONS, "rotation direction")

        result = self.ssh_client.rotate(bot_id, direction)
        logger.info(f"Successfully rotated bot {bot_id} {direction}")
        return {"status": result}

    @handle_ssh_errors("get speed information")
    def get_speed(self, bot_id: int) -> Dict[str, str]:
        """
        Get current speed information for the robot.

        Args:
            bot_id: Unique identifier for the robot

        Returns:
            Dictionary containing status and speed information
        """
        logger.info(f"Getting speed information for bot {bot_id}")
        result = self.ssh_client.get_speed(bot_id)
        logger.info(f"Successfully retrieved speed for bot {bot_id}")
        
        # Return speed info as a dictionary to match API expectations
        if result == "Speed information not available":
            return {"status": "success", "speed_info": {"error": result}}
        else:
            return {"status": "success", "speed_info": {"linear_speed": result}}

    @handle_ssh_errors("get session status")
    def get_session_status(self, bot_id: int) -> Dict[str, str]:
        """
        Get the status of a session for the specified bot.

        Args:
            bot_id: Unique identifier for the robot

        Returns:
            Dictionary containing status and session information
        """
        logger.info(f"Getting session status for bot {bot_id}")
        result = self.ssh_client.get_session_status(bot_id)
        logger.info(f"Session status for bot {bot_id}: {result}")
        return {"status": "success", "session_status": result}

    @handle_ssh_errors("list active sessions")
    def list_active_sessions(self) -> Dict[str, str]:
        """
        List all active sessions.

        Returns:
            Dictionary containing status and list of active sessions
        """
        logger.info("Listing active sessions")
        result = self.ssh_client.list_active_sessions()
        logger.info(f"Active sessions: {result}")
        return {"status": "success", "active_sessions": result}
