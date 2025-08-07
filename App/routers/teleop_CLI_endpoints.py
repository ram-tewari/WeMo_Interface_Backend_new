#routers/teleop_CLI_endpoints
"""
Teleop CLI Endpoints Module

This module provides REST API endpoints for robot teleoperation control.
Handles HTTP requests for session management, movement commands, and status monitoring.
"""

import json
import logging
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, APIRouter, status, Depends, HTTPException, Request, Response, Query, Path
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from App.schemas.teleop_CLI_models import BotId, SpeedChangeReq, MoveReq, RotateReq
from App.services.teleop_CLI_services import TeleopService
from App.utils.teleop_CLI_SSH_helper import SSHClient, SSHClientError


# Response Models for Documentation
class OperationResponse(BaseModel):
    """Standard response model for successful operations."""
    status: str = Field(..., description="Operation status indicator")

    class Config:
        schema_extra = {
            "example": {
                "status": "success"
            }
        }


class SpeedInfoResponse(BaseModel):
    """Response model for speed information."""
    status: str = Field(..., description="Operation status indicator")
    speed_info: Dict[str, Any] = Field(..., description="Current speed information")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "speed_info": {"current_speed": 5, "max_speed": 10}
            }
        }


class SessionStatusResponse(BaseModel):
    """Response model for session status information."""
    status: str = Field(..., description="Operation status indicator")
    session_status: str = Field(..., description="Current session status")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "session_status": "active"
            }
        }


class ActiveSessionsResponse(BaseModel):
    """Response model for active sessions list."""
    status: str = Field(..., description="Operation status indicator")
    active_sessions: List[int] = Field(..., description="List of active bot session IDs")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "active_sessions": [1, 2, 3]
            }
        }


class DebugInfoResponse(BaseModel):
    """Response model for debug information."""
    bot_id: int = Field(..., description="Bot ID being debugged")
    status: str = Field(..., description="Current session status")
    session_exists_in_sessions: bool = Field(..., description="Whether session exists in memory")
    all_active_sessions: List[int] = Field(..., description="All currently active sessions")
    process_alive: Optional[bool] = Field(None, description="Whether the process is alive (if session exists)")
    process_type: Optional[str] = Field(None, description="Type of process (if session exists)")

    class Config:
        schema_extra = {
            "example": {
                "bot_id": 123,
                "status": "active",
                "session_exists_in_sessions": True,
                "all_active_sessions": [123, 456],
                "process_alive": True,
                "process_type": "Process"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error message describing what went wrong")

    class Config:
        schema_extra = {
            "example": {
                "error": "SSH connection failed"
            }
        }


def setup_logging() -> logging.Logger:
    """
    Configure logging for the API module.

    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Log to console
            logging.FileHandler("api_requests.log")  # Log to file
        ]
    )
    return logging.getLogger("API")


def handle_endpoint_errors(operation_name: str):
    """
    Decorator to handle errors consistently across all endpoint functions.

    Args:
        operation_name: Name of the operation for logging purposes
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs) if hasattr(func, '__code__') and 'await' in func.__code__.co_names else func(*args, **kwargs)
                return result
            except SSHClientError as e:
                logger.error(f"{operation_name} failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
            except Exception as e:
                logger.exception(f"Unknown error during {operation_name}")
                raise HTTPException(status_code=500, detail=f"Unknown error: {str(e)}")
        return wrapper
    return decorator



logger = setup_logging()

app = FastAPI(
    title="WeMo Robot Teleoperation API",
    description="""
    ## WeMo Robot Teleoperation Control System

    This API provides comprehensive control over WeMo robots through teleoperation commands.
    It allows users to:

    * **Start and stop teleoperation sessions** for individual robots
    * **Control robot movement** in four directions (up, down, left, right)
    * **Control robot rotation** (left and right)
    * **Adjust robot speed** (increase and decrease)
    * **Monitor session status** and active sessions
    * **Debug robot connection** and session information

    All operations are performed through secure SSH connections to robot controllers.

    ### Authentication
    Currently, no authentication is required, but this may change in future versions.

    ### Rate Limiting
    No rate limiting is currently implemented, but users should avoid excessive requests.
    """,
    version="1.0.0",
    contact={
        "name": "WeMo Development Team",
        "url": "https://github.com/your-org/wemo-interface",
        "email": "support@wemo-robotics.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    tags_metadata=[
        {
            "name": "teleop",
            "description": "Robot teleoperation control endpoints for session management and movement commands.",
        },
        {
            "name": "status",
            "description": "Status monitoring and debugging endpoints for robot sessions.",
        },
    ]
)

router = APIRouter(prefix="/api", tags=["teleop"])

# Create singleton instances for dependency injection
ssh_client_singleton = SSHClient()
teleop_service_singleton = TeleopService(ssh_client_singleton)


def get_teleop_service() -> TeleopService:
    """
    Dependency function to retrieve the shared TeleopService instance.

    Returns:
        Singleton TeleopService instance
    """
    return teleop_service_singleton


@app.get("/", include_in_schema=False)
def root() -> PlainTextResponse:
    """Root endpoint to verify API is running."""
    return PlainTextResponse("WeMo Teleoperation API is running")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Favicon endpoint to prevent 404 errors."""
    return Response(status_code=204)


def _should_skip_logging(path: str) -> bool:
    """Check if request path should be skipped from logging."""
    return path in ["/favicon.ico", "/"]


def _extract_request_body(request: Request) -> Dict[str, Any]:
    """
    Extract and parse request body for logging.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary containing request body data or empty dict
    """
    try:
        if request.method == "POST":
            # Note: In real implementation, you'd need to handle this differently
            # as request.body() can only be called once. Consider using middleware
            # that stores the body or use a custom Request class.
            return {"body": "POST request body logged separately"}
    except Exception as e:
        logger.warning(f"Failed to extract request body: {str(e)}")
    return {}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all HTTP requests with timing and error information.

    Args:
        request: Incoming HTTP request
        call_next: Next middleware or endpoint function

    Returns:
        HTTP response
    """
    start_time = datetime.now()
    path = request.url.path

    # Skip logging for utility endpoints
    if _should_skip_logging(path):
        return await call_next(request)

    try:
        response = await call_next(request)
    except Exception as e:
        process_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.error(
            f"Request failed: {request.method} {path} - {str(e)} - {process_time:.2f}ms"
        )
        raise e

    # Calculate processing time
    process_time = (datetime.now() - start_time).total_seconds() * 1000

    # Prepare log data
    log_data = {
        "method": request.method,
        "path": path,
        "status_code": response.status_code,
        "process_time": f"{process_time:.2f}ms",
        "client": request.client.host if request.client else "unknown"
    }

    # Add request body for POST requests
    log_data.update(_extract_request_body(request))

    # Log based on status code severity
    log_message = f"API Request: {json.dumps(log_data)}"
    if response.status_code >= 500:
        logger.error(log_message)
    elif response.status_code >= 400:
        logger.warning(log_message)
    else:
        logger.info(log_message)

    return response


@app.exception_handler(SSHClientError)
async def ssh_client_exception_handler(request: Request, exc: SSHClientError) -> JSONResponse:
    """
    Global exception handler for SSH client errors.

    Args:
        request: The request that caused the exception
        exc: The SSH client exception

    Returns:
        JSON response with error details
    """
    logger.error(f"SSH Client Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled exceptions.

    Args:
        request: The request that caused the exception
        exc: The unhandled exception

    Returns:
        JSON response with generic error message
    """
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


@router.post(
    "/startsession",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Robot Teleoperation Session",
    description="""
    Initialize a new teleoperation session for the specified robot.

    This endpoint establishes an SSH connection to the robot controller and 
    prepares it for receiving movement commands. Each robot can only have 
    one active session at a time.

    **Example Usage:**
    ```
    {
        "bot_id": 123
    }
    ```

    **Success Response:**
    ```
    {
        "status": "session_started"
    }
    ```
    """,
    responses={
        200: {
            "description": "Session started successfully",
            "model": OperationResponse
        },
        500: {
            "description": "Internal server error or SSH connection failed",
            "model": ErrorResponse
        }
    }
)
@handle_endpoint_errors("start session")
def start_session(
        req: BotId,
        teleop_service: TeleopService = Depends(get_teleop_service)
) -> OperationResponse:
    """
    Start a teleoperation session for the specified bot.

    Args:
        req: Request containing bot ID
        teleop_service: Injected teleop service instance

    Returns:
        Dictionary containing operation status
    """
    logger.info(f"Starting session for bot {req.bot_id}")
    result = teleop_service.start_session(req.bot_id)
    logger.info(f"Session started for bot {req.bot_id}: {result}")
    return result


@router.post(
    "/endsession",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
    summary="End Robot Teleoperation Session",
    description="""
    Terminate the active teleoperation session for the specified robot.

    This endpoint closes the SSH connection and cleans up any associated 
    resources. The robot will stop responding to movement commands after 
    the session is ended.

    **Example Usage:**
    ```
    {
        "bot_id": 123
    }
    ```

    **Success Response:**
    ```
    {
        "status": "session_ended"
    }
    ```
    """,
    responses={
        200: {
            "description": "Session ended successfully",
            "model": OperationResponse
        },
        500: {
            "description": "Internal server error or session termination failed",
            "model": ErrorResponse
        }
    }
)
@handle_endpoint_errors("end session")
def end_session(
        req: BotId,
        teleop_service: TeleopService = Depends(get_teleop_service)
) -> OperationResponse:
    """
    End the teleoperation session for the specified bot.

    Args:
        req: Request containing bot ID
        teleop_service: Injected teleop service instance

    Returns:
        Dictionary containing operation status
    """
    logger.info(f"Ending session for bot {req.bot_id}")
    result = teleop_service.end_session(req.bot_id)
    logger.info(f"Session ended for bot {req.bot_id}: {result}")
    return result


@router.post(
    "/speed",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Change Robot Speed",
    description="""
    Modify the movement speed of the specified robot.

    This endpoint allows you to increase or decrease the robot's movement 
    speed. The robot must have an active teleoperation session for this 
    command to work.

    **Valid Actions:**
    - `increase`: Increase the robot's movement speed
    - `decrease`: Decrease the robot's movement speed

    **Example Usage:**
    ```
    {
        "bot_id": 123,
        "action": "increase"
    }
    ```

    **Success Response:**
    ```
    {
        "status": "speed_changed"
    }
    ```
    """,
    responses={
        200: {
            "description": "Speed changed successfully",
            "model": OperationResponse
        },
        500: {
            "description": "Internal server error or invalid speed action",
            "model": ErrorResponse
        }
    }
)
@handle_endpoint_errors("change speed")
def change_speed(
        req: SpeedChangeReq,
        teleop_service: TeleopService = Depends(get_teleop_service)
) -> OperationResponse:
    """
    Change the speed of the specified bot.

    Args:
        req: Request containing bot ID and speed action
        teleop_service: Injected teleop service instance

    Returns:
        Dictionary containing operation status
    """
    logger.info(f"Changing speed for bot {req.bot_id}: {req.action}")
    result = teleop_service.change_speed(req.bot_id, req.action)
    logger.info(f"Speed changed for bot {req.bot_id}: {result}")
    return result


@router.post(
    "/move",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Move Robot in Direction",
    description="""
    Command the robot to move in a specified direction.

    This endpoint sends movement commands to the robot. The robot must have 
    an active teleoperation session for this command to work.

    **Valid Directions:**
    - `up`: Move forward
    - `down`: Move backward
    - `left`: Move left
    - `right`: Move right

    **Example Usage:**
    ```
    {
        "bot_id": 123,
        "direction": "up"
    }
    ```

    **Success Response:**
    ```
    {
        "status": "moved"
    }
    ```
    """,
    responses={
        200: {
            "description": "Robot moved successfully",
            "model": OperationResponse
        },
        500: {
            "description": "Internal server error or invalid direction",
            "model": ErrorResponse
        }
    }
)
@handle_endpoint_errors("move bot")
def move_bot(
        req: MoveReq,
        teleop_service: TeleopService = Depends(get_teleop_service)
) -> OperationResponse:
    """
    Move the specified bot in a direction.

    Args:
        req: Request containing bot ID and movement direction
        teleop_service: Injected teleop service instance

    Returns:
        Dictionary containing operation status
    """
    logger.info(f"Moving bot {req.bot_id}: {req.direction}")
    result = teleop_service.move(req.bot_id, req.direction)
    logger.info(f"Moved bot {req.bot_id}: {result}")
    return result


@router.post(
    "/rotate",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate Robot",
    description="""
    Command the robot to rotate in a specified direction.

    This endpoint sends rotation commands to the robot. The robot must have 
    an active teleoperation session for this command to work.

    **Valid Directions:**
    - `left`: Rotate counterclockwise
    - `right`: Rotate clockwise

    **Example Usage:**
    ```
    {
        "bot_id": 123,
        "direction": "left"
    }
    ```

    **Success Response:**
    ```
    {
        "status": "rotated"
    }
    ```
    """,
    responses={
        200: {
            "description": "Robot rotated successfully",
            "model": OperationResponse
        },
        500: {
            "description": "Internal server error or invalid rotation direction",
            "model": ErrorResponse
        }
    }
)
@handle_endpoint_errors("rotate bot")
def rotate_bot(
        req: RotateReq,
        teleop_service: TeleopService = Depends(get_teleop_service)
) -> OperationResponse:
    """
    Rotate the specified bot in a direction.

    Args:
        req: Request containing bot ID and rotation direction
        teleop_service: Injected teleop service instance

    Returns:
        Dictionary containing operation status
    """
    logger.info(f"Rotating bot {req.bot_id}: {req.direction}")
    result = teleop_service.rotate(req.bot_id, req.direction)
    logger.info(f"Rotated bot {req.bot_id}: {result}")
    return result


@router.get(
    "/getspeed",
    response_model=SpeedInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Robot Speed Information",
    description="""
    Retrieve the current speed information for a robot.

    This endpoint returns detailed information about the robot's current 
    movement speed settings. The robot must have an active session.

    **Example Response:**
    ```
    {
        "status": "success",
        "speed_info": {
            "current_speed": 5,
            "max_speed": 10,
            "min_speed": 1
        }
    }
    ```
    """,
    responses={
        200: {
            "description": "Speed information retrieved successfully",
            "model": SpeedInfoResponse
        },
        500: {
            "description": "Internal server error or robot not accessible",
            "model": ErrorResponse
        }
    },
    tags=["status"]
)
@handle_endpoint_errors("get speed")
def get_speed(
        bot_id: int = Query(..., description="The ID of the robot to query for speed information", example=123),
        teleop_service: TeleopService = Depends(get_teleop_service)
) -> SpeedInfoResponse:
    """
    Get current speed information for the specified bot.

    Args:
        bot_id: ID of the bot to query
        teleop_service: Injected teleop service instance

    Returns:
        Dictionary containing speed information
    """
    logger.info(f"Getting speed for bot {bot_id}")
    result = teleop_service.get_speed(bot_id)
    logger.info(f"Speed retrieved for bot {bot_id}: {result}")
    return result


@router.get(
    "/session/status",
    response_model=SessionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Session Status",
    description="""
    Check the current status of a robot's teleoperation session.

    This endpoint returns information about whether a session is active, 
    inactive, or in an error state for the specified robot.

    **Possible Status Values:**
    - `active`: Session is running and ready for commands
    - `inactive`: No session is currently active
    - `error`: Session is in an error state
    - `connecting`: Session is being established

    **Example Response:**
    ```
    {
        "status": "success",
        "session_status": "active"
    }
    ```
    """,
    responses={
        200: {
            "description": "Session status retrieved successfully",
            "model": SessionStatusResponse
        },
        500: {
            "description": "Internal server error or status check failed",
            "model": ErrorResponse
        }
    },
    tags=["status"]
)
@handle_endpoint_errors("get session status")
def get_session_status(
        bot_id: int = Query(..., description="The ID of the robot to check session status for", example=123),
        teleop_service: TeleopService = Depends(get_teleop_service)
) -> SessionStatusResponse:
    """
    Get session status for the specified bot.

    Args:
        bot_id: ID of the bot to query
        teleop_service: Injected teleop service instance

    Returns:
        Dictionary containing session status information
    """
    logger.info(f"Getting session status for bot {bot_id}")
    result = teleop_service.get_session_status(bot_id)
    logger.info(f"Session status for bot {bot_id}: {result}")
    return result


@router.get(
    "/sessions",
    response_model=ActiveSessionsResponse,
    status_code=status.HTTP_200_OK,
    summary="List All Active Sessions",
    description="""
    Retrieve a list of all currently active teleoperation sessions.

    This endpoint returns the IDs of all robots that currently have 
    active teleoperation sessions running.

    **Example Response:**
    ```
    {
        "status": "success",
        "active_sessions": 
    }
    ```
    """,
    responses={
        200: {
            "description": "Active sessions list retrieved successfully",
            "model": ActiveSessionsResponse
        },
        500: {
            "description": "Internal server error or failed to retrieve sessions",
            "model": ErrorResponse
        }
    },
    tags=["status"]
)
@handle_endpoint_errors("list active sessions")
def list_active_sessions(
        teleop_service: TeleopService = Depends(get_teleop_service)
) -> ActiveSessionsResponse:
    """
    List all currently active teleoperation sessions.

    Args:
        teleop_service: Injected teleop service instance

    Returns:
        Dictionary containing list of active sessions
    """
    logger.info("Listing all active sessions")
    result = teleop_service.list_active_sessions()
    logger.info(f"Active sessions: {result}")
    return result


@router.get(
    "/debug",
    response_model=DebugInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Debug Information",
    description="""
    Retrieve comprehensive debugging information for a robot session.

    This endpoint provides detailed technical information about the state 
    of a robot's session, including process status, memory state, and 
    connection details. Primarily used for troubleshooting.

    **Example Response:**
    ```
    {
        "bot_id": 123,
        "status": "active",
        "session_exists_in_sessions": true,
        "all_active_sessions": ,
        "process_alive": true,
        "process_type": "Process"
    }
    ```
    """,
    responses={
        200: {
            "description": "Debug information retrieved successfully",
            "model": DebugInfoResponse
        },
        500: {
            "description": "Internal server error or debug check failed",
            "model": ErrorResponse
        }
    },
    tags=["status"]
)
@handle_endpoint_errors("debug session")
def debug_session(
        bot_id: int = Query(..., description="The ID of the robot to debug", example=123),
        teleop_service: TeleopService = Depends(get_teleop_service)
) -> DebugInfoResponse:
    """
    Get detailed debug information for a bot session.

    Args:
        bot_id: ID of the bot to debug
        teleop_service: Injected teleop service instance

    Returns:
        Dictionary containing detailed debug information
    """
    logger.info(f"Debug check for bot {bot_id}")

    ssh_client = teleop_service.ssh_client

    # Gather debug information
    session_status = ssh_client.get_session_status(bot_id)
    active_sessions = ssh_client.list_active_sessions()
    session_exists = bot_id in ssh_client._sessions

    debug_info = {
        "bot_id": bot_id,
        "status": session_status,
        "session_exists_in_sessions": session_exists,
        "all_active_sessions": active_sessions,
    }

    # Add process-specific debug info if session exists
    if session_exists:
        child_process = ssh_client._sessions[bot_id]
        debug_info.update({
            "process_alive": ssh_client._is_alive(child_process),
            "process_type": type(child_process).__name__
        })

    logger.info(f"Debug info for bot {bot_id}: {debug_info}")
    return debug_info


# Register router with app
app.include_router(router)
