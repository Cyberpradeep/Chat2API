"""
Prompt and Tool Calling Compiler.
Compiles System Instructions, Tool Schemas, and Conversation History into
effective prompts, and parses tool-call responses into standard OpenAI format.
"""

import re
import json
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple, Union

logger = logging.getLogger("prompt_compiler")

def compile_messages(
    messages: List[Dict[str, Any]],
    system_prompt: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None
) -> Tuple[str, List[str]]:
    """
    Compiles an array of OpenAI messages, system prompts, and tool definitions
    into an optimized ChatGPT prompt string and a list of image/file paths.
    """
    system_instructions: List[str] = []
    if system_prompt:
        system_instructions.append(system_prompt.strip())

    history_parts: List[str] = []
    latest_user_prompt = ""
    files: List[str] = []

    # Process all messages
    for i, msg in enumerate(messages):
        role = msg.get("role", "user")
        raw_content = msg.get("content", "")

        # Extract text and multimodal files
        text_content = ""
        if isinstance(raw_content, str):
            text_content = raw_content
        elif isinstance(raw_content, list):
            parts = []
            for item in raw_content:
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif item.get("type") == "image_url":
                    url = item.get("image_url", {}).get("url", "")
                    if url:
                        files.append(url)
            text_content = "\n".join(parts)

        # Handle roles
        if role == "system":
            system_instructions.append(text_content.strip())
        elif role == "tool":
            tool_call_id = msg.get("tool_call_id", "unknown")
            history_parts.append(f"[TOOL RESULT for {tool_call_id}]:\n{text_content}")
        elif role == "assistant":
            # Check if assistant message had tool calls
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                history_parts.append(f"Assistant [Tool Call]: {json.dumps(tool_calls)}")
            else:
                history_parts.append(f"Assistant: {text_content}")
        elif role == "user":
            if i == len(messages) - 1:
                latest_user_prompt = text_content
            else:
                history_parts.append(f"User: {text_content}")

    if not latest_user_prompt:
        # If the last message was a tool execution result, instruct the model to synthesize the final answer
        latest_user_prompt = "Using the tool results above, provide the final complete answer to the user's request."

    # Build final composite prompt
    composite_sections: List[str] = []

    # 1. System Instructions Block
    if system_instructions:
        joined_system = "\n\n".join(system_instructions)
        composite_sections.append(
            f"[SYSTEM INSTRUCTION]\n{joined_system}\n[/SYSTEM_INSTRUCTION]"
        )

    # 2. Tool Definitions Block (Function Calling)
    if tools:
        tools_str = json.dumps(tools, indent=2)
        composite_sections.append(
            "[AVAILABLE TOOLS]\n"
            "You are connected to an external execution client with the following tool definitions:\n"
            f"{tools_str}\n\n"
            "MANDATORY TOOL INSTRUCTIONS:\n"
            "1. When the user requests information that can be obtained from the tools above, you MUST generate a tool call so the client can execute it on your behalf.\n"
            "2. NEVER claim you cannot access tools or don't have real-time capabilities. Always emit the tool call request.\n"
            "3. When calling a tool, your entire response MUST be ONLY this JSON block:\n"
            "```json\n"
            "{\n"
            '  "tool_calls": [\n'
            '    {\n'
            '      "name": "<exact_tool_name>",\n'
            '      "arguments": { "<param_name>": "<value>" }\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "```\n"
            "4. Do not include any conversational explanation before or after the JSON.\n"
            "5. If a [TOOL RESULT] is provided in the conversation, use that data to answer the user directly.\n"
            "[/AVAILABLE TOOLS]"
        )

    # 3. Conversation History (if multi-turn)
    if history_parts:
        history_str = "\n\n".join(history_parts)
        composite_sections.append(
            f"[PREVIOUS CONVERSATION]\n{history_str}\n[/PREVIOUS CONVERSATION]"
        )

    # 4. User Prompt
    composite_sections.append(latest_user_prompt)

    final_prompt = "\n\n".join(composite_sections)
    return final_prompt, files


def extract_json_object(text: str) -> Optional[dict]:
    """Extracts a valid JSON object containing tool_calls even if markdown escaped or nested."""
    clean_text = text.replace(r"\_", "_").replace("\\_", "_").replace(r"\*", "*").replace("\r", "")
    idx = clean_text.find('"tool_calls"')
    if idx == -1:
        return None

    # Walk backward to find the outer '{'
    start = clean_text.rfind('{', 0, idx)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(clean_text)):
        ch = clean_text[i]
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    candidate = clean_text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        pass
    return None


def parse_tool_calls(response_text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Inspects response text to see if ChatGPT emitted a structured tool_calls JSON block.
    Returns standard OpenAI tool_calls list if detected, else None.
    """
    if not response_text:
        return None

    data = extract_json_object(response_text)
    if data and isinstance(data.get("tool_calls"), list):
        raw_calls = data["tool_calls"]
        standardized_calls = []
        for call in raw_calls:
            fn_name = call.get("name") or call.get("function", {}).get("name")
            fn_args = call.get("arguments") or call.get("function", {}).get("arguments", {})
            args_str = json.dumps(fn_args) if isinstance(fn_args, (dict, list)) else str(fn_args)

            if fn_name:
                call_id = f"call_{uuid.uuid4().hex[:12]}"
                standardized_calls.append({
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": fn_name,
                        "arguments": args_str
                    }
                })

        if standardized_calls:
            logger.info(f"Successfully parsed {len(standardized_calls)} tool call(s) from ChatGPT response!")
            return standardized_calls

    return None
