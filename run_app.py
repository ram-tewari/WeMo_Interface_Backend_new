#!/usr/bin/env python3
"""
Simple startup script for the WeMo Teleoperation API
Run this from the workspace root directory
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

if __name__ == "__main__":
    import uvicorn
    
    # Run uvicorn with the correct module path
    uvicorn.run(
        "App.routers.teleop_CLI_endpoints:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["./App"]  # Only watch App directory for changes
    )