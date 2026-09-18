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
from config.logger import get_logger

logger = get_logger("test_openai_sdk")

try:
    from openai import OpenAI
except ImportError:
    print("[!] 'openai' package not installed. Run: pip install openai")
    sys.exit(1)

def main():
    base_url = f"http://{settings.HOST}:{settings.PORT}/v1"
    logger.info("Starting OpenAI SDK compatibility test", base_url=base_url)
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
        model_ids = [m.id for m in models.data]
        logger.info("Models endpoint succeeded", models=model_ids)
        print(f"   Available models: {model_ids}")
    except Exception as e:
        logger.error("Error listing models", error=str(e), exc_info=True)
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
        content = response.choices[0].message.content
        logger.info("Completions endpoint succeeded", content=content)
        print("\n" + "=" * 65)
        print("  OPENAI SDK RESPONSE:")
        print("=" * 65)
        print(content)
        print("=" * 65)
        print("[+] OpenAI SDK compatibility verified successfully!")
    except Exception as e:
        logger.error("Chat completions failed", error=str(e), exc_info=True)
        print(f"[X] Chat completions failed: {e}")

if __name__ == "__main__":
    main()
