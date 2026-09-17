"""
Verification Script for System Instructions & Tool Calling (Function Calling).
Verifies that our ChatGPT Web-to-API engine correctly follows system instructions
and returns structured OpenAI tool_calls.

Usage:
    python tests/test_system_and_tools.py
"""

import sys
import json
from pathlib import Path

# Ensure root workspace directory is in sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import OpenAI
from config.settings import settings

def main():
    base_url = f"http://{settings.HOST}:{settings.PORT}/v1"
    print("=" * 65)
    print("  Testing System Instructions & Tool Calls via OpenAI SDK")
    print(f"  Base URL: {base_url}")
    print("=" * 65)

    client = OpenAI(
        base_url=base_url,
        api_key="not-needed-local"
    )

    # -------------------------------------------------------------
    # TEST 1: System Instructions
    # -------------------------------------------------------------
    print("\n[TEST 1] Verifying System Instructions...")
    system_instruction = "You are a 17th century pirate. Speak in full pirate slang and end every sentence with 'Arrr!'."
    user_question = "What is the capital of France? Answer in one short sentence."

    print(f" * System Prompt: \"{system_instruction}\"")
    print(f" * User Prompt:   \"{user_question}\"")

    try:
        response = client.chat.completions.create(
            model="chatgpt",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_question}
            ]
        )
        print("\n  Assistant Response:")
        print("  " + "-" * 50)
        print("  " + response.choices[0].message.content)
        print("  " + "-" * 50)
        print("  [+] System Instructions test completed!")
    except Exception as e:
        print(f"  [X] Test 1 failed: {e}")

    # -------------------------------------------------------------
    # TEST 2: Tool / Function Calling
    # -------------------------------------------------------------
    print("\n[TEST 2] Verifying Tool / Function Calling...")
    tools = [
        {
            "type": "function",
            "function": {
              "name": "get_stock_price",
              "description": "Get the current stock price for a given ticker symbol",
              "parameters": {
                "type": "object",
                "properties": {
                  "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol, e.g. AAPL, TSLA"
                  }
                },
                "required": ["ticker"]
              }
            }
        }
    ]
    tool_user_prompt = "What is the stock price of Apple (AAPL)?"
    print(f" * Tools defined: {[t['function']['name'] for t in tools]}")
    print(f" * User Prompt:   \"{tool_user_prompt}\"")

    try:
        response2 = client.chat.completions.create(
            model="chatgpt",
            messages=[
                {"role": "user", "content": tool_user_prompt}
            ],
            tools=tools
        )
        choice = response2.choices[0]
        print(f"\n  Finish Reason: {choice.finish_reason}")
        if choice.message.tool_calls:
            print("  [+] SUCCESS! Tool calls returned by ChatGPT:")
            for tc in choice.message.tool_calls:
                print(f"      Function:  {tc.function.name}")
                print(f"      Arguments: {tc.function.arguments}")
        else:
            print(f"  Message Content: {choice.message.content}")
        print("  [+] Tool Calling test completed!")
    except Exception as e:
        print(f"  [X] Test 2 failed: {e}")

if __name__ == "__main__":
    main()
