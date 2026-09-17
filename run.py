"""
Master One-Click Launcher for the ChatGPT Modular Engine.
Checks authentication profile, validates configuration, and starts the FastAPI server.
"""

import os
import sys
import uvicorn
from config.settings import settings

def check_login():
    """Checks if the persistent user_data directory contains session files."""
    user_data = settings.USER_DATA_DIR
    if not os.path.exists(user_data) or not os.listdir(user_data):
        print("\n" + "!" * 60)
        print(" [!] No active ChatGPT session found in ./user_data")
        print("     Please run the login helper first:")
        print("     python login_helper.py")
        print("!" * 60 + "\n")
        return False
    return True

def main():
    print("=" * 65)
    print("  ChatGPT Web-to-API Modular Engine v2.0")
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
