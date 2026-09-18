"""
Application configuration loaded from environment variables and .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8088"))
    HEADLESS: bool = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")
    BROWSER_CHANNEL: str = os.getenv("BROWSER_CHANNEL", "chrome")
    TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "180"))
    USER_DATA_DIR: str = os.getenv("USER_DATA_DIR", str(BASE_DIR / "user_data"))
    TEMP_UPLOADS_DIR: str = str(BASE_DIR / "temp_uploads")
    LOGS_DIR: str = os.getenv("LOGS_DIR", str(BASE_DIR / "logs"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

settings = Settings()
