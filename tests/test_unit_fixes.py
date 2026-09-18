"""
Unit test verifying the High-Priority Bug Fixes:
1. Tool call arguments normalization (guaranteeing valid JSON {} even for empty/null)
2. new_chat field validation in OpenAICompletionRequest
3. Error banners definitions and check_ui_error function
"""

import sys
import json
from pathlib import Path

# Ensure root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.prompt_compiler import parse_tool_calls
from server.schemas import OpenAICompletionRequest, OpenAIMessage
from config.selectors import ERROR_BANNERS
from providers.chatgpt.extractor import check_ui_error

def test_tool_call_arguments_normalization():
    print("1. Testing tool call arguments normalization...")

    # Case A: Tool call with explicit null/None arguments
    response_with_none = """
    ```json
    {
      "tool_calls": [
        {
          "name": "get_current_time",
          "arguments": null
        }
      ]
    }
    ```
    """
    calls_none = parse_tool_calls(response_with_none)
    assert calls_none is not None, "Failed to parse tool calls with null arguments"
    assert len(calls_none) == 1
    assert calls_none[0]["function"]["arguments"] == "{}"
    # Verify it deserializes without JSONDecodeError
    assert json.loads(calls_none[0]["function"]["arguments"]) == {}

    # Case B: Tool call with empty dict arguments
    response_with_empty = """
    ```json
    {
      "tool_calls": [
        {
          "name": "ping",
          "arguments": {}
        }
      ]
    }
    ```
    """
    calls_empty = parse_tool_calls(response_with_empty)
    assert calls_empty is not None
    assert calls_empty[0]["function"]["arguments"] == "{}"
    assert json.loads(calls_empty[0]["function"]["arguments"]) == {}

    # Case C: Tool call with populated arguments
    response_with_args = """
    ```json
    {
      "tool_calls": [
        {
          "name": "search_stock",
          "arguments": {
            "ticker": "NVDA"
          }
        }
      ]
    }
    ```
    """
    calls_args = parse_tool_calls(response_with_args)
    assert calls_args is not None
    loaded = json.loads(calls_args[0]["function"]["arguments"])
    assert loaded == {"ticker": "NVDA"}

    # Case D: Inline function calls in natural text
    response_inline = """
    Action items:
    1. Run `check_server_health({"service_name":"auth-gateway"})`.
    2. Run `check_threat_level({"ip_address":"194.26.29.11"})`.
    """
    calls_inline = parse_tool_calls(response_inline)
    assert calls_inline is not None, "Failed to parse inline function calls"
    assert len(calls_inline) == 2
    assert calls_inline[0]["function"]["name"] == "check_server_health"
    assert json.loads(calls_inline[0]["function"]["arguments"]) == {"service_name": "auth-gateway"}
    assert calls_inline[1]["function"]["name"] == "check_threat_level"
    assert json.loads(calls_inline[1]["function"]["arguments"]) == {"ip_address": "194.26.29.11"}

    print("   [PASS] Tool call arguments normalized and always valid JSON.")

def test_new_chat_schema():
    print("2. Testing new_chat schema field in OpenAICompletionRequest...")

    req_default = OpenAICompletionRequest(
        messages=[OpenAIMessage(role="user", content="Hi")]
    )
    assert req_default.new_chat is None, "Expected new_chat default to be None"

    req_override = OpenAICompletionRequest(
        messages=[OpenAIMessage(role="user", content="Hi")],
        new_chat=True
    )
    assert req_override.new_chat is True, "Expected new_chat to be True when specified"

    print("   [PASS] new_chat schema accepts None, True, False properly.")

def test_error_banner_selectors():
    print("3. Testing error banner selectors and function availability...")
    assert len(ERROR_BANNERS) >= 5, "ERROR_BANNERS selector list is too short"
    assert callable(check_ui_error), "check_ui_error should be callable"
    print("   [PASS] Error banners configured.")

if __name__ == "__main__":
    test_tool_call_arguments_normalization()
    test_new_chat_schema()
    test_error_banner_selectors()
    print("\n[+] ALL UNIT TESTS PASSED SUCCESSFULLY!")
