# WeMo Teleoperation API

A FastAPI-based REST API for controlling WeMo robots via SSH teleoperation.

## Quick Start

### Prerequisites
- Python 3.7+
- SSH access to WeMo robots

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Application

#### Option 1: Using the startup script (Recommended)
```bash
python3 run_app.py
```

#### Option 2: Using uvicorn directly
```bash
export PATH="/home/ubuntu/.local/bin:$PATH"  # If using local installation
uvicorn App.routers.teleop_CLI_endpoints:app --host 0.0.0.0 --port 8000 --reload
```

#### Option 3: Using the main module
```bash
cd App
python3 main.py
```

### Accessing the API

- **API Root**: http://127.0.0.1:8000/
- **API Documentation**: http://127.0.0.1:8000/docs
- **API Schema**: http://127.0.0.1:8000/openapi.json

### Environment Variables

Create a `.env` file in the project root with:
```
WEMOIP=your_robot_ip_base
WEMOPORT=your_ssh_port
```

### API Endpoints

- `POST /api/startsession` - Start a teleoperation session
- `POST /api/endsession` - End a teleoperation session  
- `POST /api/move` - Move the robot (up, down, left, right)
- `POST /api/rotate` - Rotate the robot (left, right)
- `POST /api/speed` - Change robot speed (increase, decrease)
- `GET /api/getspeed` - Get current robot speed

### Troubleshooting

If you get "ModuleNotFoundError", make sure you're running the application from the workspace root directory and all dependencies are installed.

For SSH connection issues, verify your environment variables and network connectivity to the robots.