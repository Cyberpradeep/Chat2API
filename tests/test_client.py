"""
Interactive Test Client for ChatGPT Modular API
Supports testing prompt execution, Think mode, Web search, Deep research, and file attachments.

Usage:
    python tests/test_client.py "Your prompt here"
    python tests/test_client.py "Solve this math problem" --think
    python tests/test_client.py "Latest news about quantum computing" --search
    python tests/test_client.py "Describe this image" --file "path/to/image.png"
"""

import os
import sys
from pathlib import Path

# Ensure root workspace directory is in sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import httpx
from config.settings import settings

BASE_URL = f"http://{settings.HOST}:{settings.PORT}"

def test_api(
    prompt: str,
    think: bool = False,
    web_search: bool = False,
    deep_research: bool = False,
    files: list = None,
    new_chat: bool = False
):
    print("=" * 65)
    print("  ChatGPT Modular Engine - Test Client")
    print("=" * 65)

    # 1. Check Server Status
    print(f"\n1. Checking API status at {BASE_URL}/api/status ...")
    try:
        res = httpx.get(f"{BASE_URL}/api/status", timeout=10.0)
        status_data = res.json()
        print(f"   Status: {status_data}")
        if not status_data.get("browser_ready"):
            print("\n[!] WARNING: Browser does not report ready state.")
            print("    Make sure the server is initialized.")
    except Exception as e:
        print(f"\n[X] Could not connect to API server at {BASE_URL}: {e}")
        print("    Start the server with: python run.py")
        return

    # 2. Build Request Payload
    payload = {
        "prompt": prompt,
        "think": think,
        "web_search": web_search,
        "deep_research": deep_research,
        "files": files or [],
        "new_chat": new_chat,
        "timeout_seconds": 180
    }

    print(f"\n2. Sending Request:")
    print(f"   - Prompt:        \"{prompt}\"")
    print(f"   - Think Mode:    {think}")
    print(f"   - Web Search:    {web_search}")
    print(f"   - Deep Research: {deep_research}")
    if files:
        print(f"   - Attachments:   {files}")

    try:
        res = httpx.post(f"{BASE_URL}/api/chat", json=payload, timeout=200.0)
        if res.status_code == 200:
            data = res.json()
            
            if data.get("thought_process"):
                print("\n" + "-" * 65)
                print("  [THOUGHT PROCESS / REASONING]:")
                print("-" * 65)
                print(data["thought_process"])

            print("\n" + "=" * 65)
            print("  CHATGPT RESPONSE:")
            print("=" * 65)
            print(data.get("response"))
            print("=" * 65)

            if data.get("sources"):
                print("\n  [SOURCES / CITATIONS]:")
                for src in data["sources"]:
                    print(f"   • {src}")

            print("\n[+] Request completed successfully!")
        else:
            print(f"\n[X] Error ({res.status_code}): {res.text}")
    except httpx.TimeoutException:
        print("\n[X] Request timed out.")
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test client for ChatGPT Modular API")
    parser.add_argument("prompt", nargs="*", default=["Hello! Tell me in 10 words what you can do."], help="Prompt text")
    parser.add_argument("--think", action="store_true", help="Enable Think Mode (Reasoning)")
    parser.add_argument("--search", action="store_true", help="Enable Web search")
    parser.add_argument("--deep", action="store_true", help="Enable Deep research")
    parser.add_argument("--file", action="append", default=[], help="Attach local file or image")
    parser.add_argument("--new", action="store_true", help="Start a new chat session")

    args = parser.parse_args()
    prompt_str = " ".join(args.prompt)
    test_api(
        prompt=prompt_str,
        think=args.think,
        web_search=args.search,
        deep_research=args.deep,
        files=args.file,
        new_chat=args.new
    )
