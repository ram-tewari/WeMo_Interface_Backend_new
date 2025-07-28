# main.py
import uvicorn
from App.routers import teleop_CLI_endpoints

def run():
    uvicorn.run(
        "App.routers.teleop_CLI_endpoints:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    run()
