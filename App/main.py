"""
Main Application Entry Point

This module initializes and configures the FastAPI application for the WeMo robot
teleoperation interface. It sets up routing and provides the main application instance.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from App.routers import teleop_CLI_endpoints, wemo_API_endpoints

# Get logger (configuration handled in router module)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    Returns:
        Configured FastAPI application
    """
    # Initialize FastAPI app with metadata
    app = FastAPI(
        title="WeMo Interface Backend API",
        description="REST API for WeMo robot teleoperation control",
        version="1.0.0"
    )

    #middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins(for dev only)
        allow_credentials=True,
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
    )

    # Register routers
    app.include_router(teleop_CLI_endpoints.router)
    #app.include_router(wemo_API_endpoints.router)
    logger.info("FastAPI application initialized successfully")
    return app


# Create application instance
app = create_app()


@app.get("/")
async def root() -> dict:
    """
    Root endpoint providing basic API information.

    Returns:
        Dictionary containing API status message
    """
    return {"message": "WeMo Interface Backend API", "status": "running"}
