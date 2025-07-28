#routers/teleop_CLI_endpoints.py
import logging
import json
from datetime import datetime
from fastapi import FastAPI, APIRouter, status, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from App.schemas.teleop_CLI_models import BotId, SpeedChangeReq, MoveReq, RotateReq
from App.services.teleop_CLI_services import TeleopService
from App.utils.teleop_CLI_SSH_helper import SSHClient, SSHClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler("api_requests.log")  # Log to file
    ]
)
logger = logging.getLogger("API")

app = FastAPI(title="WeMo Controller routers")
router = APIRouter(prefix="/api", tags=["teleop"])

# Add root endpoint
@app.get("/", include_in_schema=False)
def root():
    return PlainTextResponse("WeMo Teleoperation API is running")

# Add favicon endpoint to prevent 404 errors
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

# Enhanced logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    path = request.url.path

    # Skip logging for favicon and root
    if path in ["/favicon.ico", "/"]:
        return await call_next(request)

    try:
        response = await call_next(request)
    except Exception as e:
        process_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.error(f"Request failed: {request.method} {path} - {str(e)} - {process_time:.2f}ms")
        raise e

    process_time = (datetime.now() - start_time).total_seconds() * 1000

    log_data = {
        "method": request.method,
        "path": path,
        "status_code": response.status_code,
        "process_time": f"{process_time:.2f}ms",
        "client": request.client.host if request.client else "unknown"
    }

    try:
        # Log request body for POST requests
        if request.method == "POST":
            body = await request.body()
            if body:
                try:
                    log_data["body"] = json.loads(body)
                except json.JSONDecodeError:
                    log_data["body"] = body.decode('utf-8', 'ignore')
    except Exception as e:
        logger.warning(f"Failed to log request body: {str(e)}")

    # Log differently based on status code
    if response.status_code >= 500:
        logger.error(f"API Request: {json.dumps(log_data)}")
    elif response.status_code >= 400:
        logger.warning(f"API Request: {json.dumps(log_data)}")
    else:
        logger.info(f"API Request: {json.dumps(log_data)}")

    return response

# Register a global exception handler for SSHClientError
@app.exception_handler(SSHClientError)
async def sshclient_exception_handler(request: Request, exc: SSHClientError):
    logger.error(f"SSH Client Error: {exc.message}")
    return JSONResponse(
        status_code=500,
        content={"error": exc.message}
    )

# Generic exception handler
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# Dependency to create the service and inject SSH client
def get_teleop_service():
    return TeleopService(SSHClient())

@router.post("/startsession", status_code=status.HTTP_200_OK)
def start_session(
        req: BotId,
        teleop_service: TeleopService = Depends(get_teleop_service)):
    logger.info(f"Starting session for bot {req.bot_id}")
    try:
        result = teleop_service.start_session(req.bot_id)
        logger.info(f"Session started for bot {req.bot_id}: {result}")
        return result
    except SSHClientError as e:
        logger.error(f"Failed to start session for bot {req.bot_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unknown error starting session for bot {req.bot_id}")
        raise HTTPException(status_code=500, detail=f"Unknown error: {str(e)}")

@router.post("/endsession", status_code=status.HTTP_200_OK)
def end_session(
        req: BotId,
        teleop_service: TeleopService = Depends(get_teleop_service)):
    logger.info(f"Ending session for bot {req.bot_id}")
    try:
        result = teleop_service.end_session(req.bot_id)
        logger.info(f"Session ended for bot {req.bot_id}: {result}")
        return result
    except SSHClientError as e:
        logger.error(f"Failed to end session for bot {req.bot_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unknown error ending session for bot {req.bot_id}")
        raise HTTPException(status_code=500, detail=f"Unknown error: {str(e)}")

@router.post("/speed", status_code=status.HTTP_200_OK)
def change_speed(
        req: SpeedChangeReq,
        teleop_service: TeleopService = Depends(get_teleop_service)
):
    logger.info(f"Changing speed for bot {req.bot_id}: {req.action}")
    try:
        result = teleop_service.change_speed(req.bot_id, req.action)
        logger.info(f"Speed changed for bot {req.bot_id}: {result}")
        return result
    except SSHClientError as e:
        logger.error(f"Speed change failed for bot {req.bot_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unknown error changing speed for bot {req.bot_id}")
        raise HTTPException(status_code=500, detail=f"Unknown error: {str(e)}")

@router.post("/move", status_code=status.HTTP_200_OK)
def move_bot(
        req: MoveReq,
        teleop_service = Depends(get_teleop_service)):
    logger.info(f"Moving bot {req.bot_id}: {req.direction}")
    try:
        result = teleop_service.move(req.bot_id, req.direction)
        logger.info(f"Moved bot {req.bot_id}: {result}")
        return result
    except SSHClientError as e:
        logger.error(f"Move failed for bot {req.bot_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unknown error moving bot {req.bot_id}")
        raise HTTPException(status_code=500, detail=f"Unknown error: {str(e)}")

@router.post("/rotate", status_code=status.HTTP_200_OK)
def rotate_bot(
        req: RotateReq,
        teleop_service = Depends(get_teleop_service)):
    logger.info(f"Rotating bot {req.bot_id}: {req.direction}")
    try:
        result = teleop_service.rotate(req.bot_id, req.direction)
        logger.info(f"Rotated bot {req.bot_id}: {result}")
        return result
    except SSHClientError as e:
        logger.error(f"Rotation failed for bot {req.bot_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unknown error rotating bot {req.bot_id}")
        raise HTTPException(status_code=500, detail=f"Unknown error: {str(e)}")

@router.get("/getspeed", status_code=status.HTTP_200_OK)
def get_speed(bot_id: int):
    logger.info(f"Getting speed for bot {bot_id}")
    try:
        speed = 0.2
        logger.info(f"Returning speed for bot {bot_id}: {speed}")
        return {"bot_id": bot_id, "speed": speed}
    except Exception as e:
        logger.exception(f"Unknown error getting speed for bot {bot_id}")
        raise HTTPException(status_code=500, detail=f"Unknown error: {str(e)}")

app.include_router(router)