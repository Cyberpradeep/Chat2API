"""
Master One-Click Launcher for the ChatGPT Modular Engine.
Checks authentication profile, validates configuration, and starts the FastAPI server.
"""

import os
import sys
import uvicorn
from config.settings import settings
from config.logger import setup_logging, get_logger

# Initialize modular structured logging
setup_logging()
logger = get_logger("launcher")

def check_login():
    """Checks if the persistent user_data directory contains session files."""
    user_data = settings.USER_DATA_DIR
    if not os.path.exists(user_data) or not os.listdir(user_data):
        logger.warning("No active ChatGPT session found in user_data", user_data_dir=user_data)
        print("\n" + "!" * 60)
        print(" [!] No active ChatGPT session found in ./user_data")
        print("     Please run the login helper first:")
        print("     python login_helper.py")
        print("!" * 60 + "\n")
        return False
    logger.info("Active session verified", user_data_dir=user_data)
    return True

def main():
    logger.info(
        "Launching ZeroKey Web-to-API Engine",
        host=settings.HOST,
        port=settings.PORT,
        headless=settings.HEADLESS,
        profile_dir=settings.USER_DATA_DIR
    )
    print("=" * 65)
    print("  ZeroKey Web-to-API Modular Engine v2.0")
    print("=" * 65)
    print(f" * Host:            {settings.HOST}")
    print(f" * Port:            {settings.PORT}")
    print(f" * Headless:        {settings.HEADLESS}")
    print(f" * Profile Dir:     {settings.USER_DATA_DIR}")
    print(f" * API Docs:        http://{settings.HOST}:{settings.PORT}/docs")
    print(f" * OpenAI Base URL: http://{settings.HOST}:{settings.PORT}/v1")
    print("=" * 65)

    check_login()

    uvicorn.run(
        "server.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )

if __name__ == "__main__":
    main()
