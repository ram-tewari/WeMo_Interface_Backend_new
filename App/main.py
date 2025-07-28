# main.py
import uvicorn
import sys
import os

# Add the workspace root to Python path so imports work correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from App.routers.teleop_CLI_endpoints import app

def run():
    uvicorn.run(
        app,  # Use the imported app directly instead of module string
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    run()
