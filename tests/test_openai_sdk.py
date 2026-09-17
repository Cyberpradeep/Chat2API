"""
Official OpenAI SDK Verification Script.
Tests that the local ChatGPT Modular Engine works as a drop-in replacement for OpenAI.

Requirements:
    pip install openai
Usage:
    python tests/test_openai_sdk.py
"""

import sys
from pathlib import Path

# Ensure root workspace directory is in sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings

try:
    from openai import OpenAI
except ImportError:
    print("[!] 'openai' package not installed. Run: pip install openai")
    sys.exit(1)

def main():
    base_url = f"http://{settings.HOST}:{settings.PORT}/v1"
    print("=" * 65)
    print("  Testing Drop-In OpenAI SDK Compatibility")
    print(f"  Target: {base_url}")
    print("=" * 65)

    client = OpenAI(
        base_url=base_url,
        api_key="not-needed-local"
    )

    # 1. Test Models Endpoint
    print("\n1. Calling client.models.list() ...")
    try:
        models = client.models.list()
        print(f"   Available models: {[m.id for m in models.data]}")
    except Exception as e:
        print(f"   [X] Error listing models: {e}")

    # 2. Test Chat Completions
    print("\n2. Calling client.chat.completions.create() ...")
    try:
        response = client.chat.completions.create(
            model="chatgpt",
            messages=[
                {"role": "user", "content": "Explain gravity in exactly one sentence."}
            ]
        )
        print("\n" + "=" * 65)
        print("  OPENAI SDK RESPONSE:")
        print("=" * 65)
        print(response.choices[0].message.content)
        print("=" * 65)
        print("[+] OpenAI SDK compatibility verified successfully!")
    except Exception as e:
        print(f"\n[X] Error during completion: {e}")

if __name__ == "__main__":
    main()
