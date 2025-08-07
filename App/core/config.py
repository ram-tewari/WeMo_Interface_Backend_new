import os
from pathlib import Path
from dotenv import load_dotenv

# Get the project root directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env file from project root
env_path = ROOT_DIR / '.env'
load_dotenv(env_path)

# Get environment variables with defaults
WEMOIP = os.getenv('WEMOIP')
WEMOPORT = os.getenv('WEMOPORT')

# Validate required environment variables
if not WEMOIP:
    raise ValueError("WEMOIP environment variable is not set")
if not WEMOPORT:
    raise ValueError("WEMOPORT environment variable is not set")