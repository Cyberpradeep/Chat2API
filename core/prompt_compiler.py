"""
Prompt and Tool Calling Compiler.
Compiles System Instructions, Tool Schemas, and Conversation History into
effective prompts, and parses tool-call responses into standard OpenAI format.
"""

import re
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple, Union
from config.logger import get_logger

logger = get_logger("prompt_compiler")

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
            "[API FUNCTION CALLING MODE]\n"
            "You are acting as an automated API function calling router. "
            "You have access to the following tool specifications:\n"
            f"{tools_str}\n\n"
            "OPERATIONAL RULES:\n"
            "1. When the user's inquiry requires external data or an action provided by any tool above, "
            "you MUST output a function call. Do not decline or state that you lack real-time data or tools; "
            "your output will be intercepted and executed by our backend system.\n"
            "2. When invoking tools, your response MUST be ONLY a JSON code block in this exact structure with no surrounding conversational prose:\n"
            "```json\n"
            "{\n"
            '  "tool_calls": [\n'
            '    {\n'
            '      "name": "function_name",\n'
            '      "arguments": {\n'
            '        "param": "value"\n'
            "      }\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "```\n"
            "3. If previous [TOOL RESULT] messages are already present in the conversation history, use them to formulate your natural language response to the user.\n"
            "[/API FUNCTION CALLING MODE]"
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
            if fn_args is None or fn_args == "" or fn_args == "None":
                args_str = "{}"
            elif isinstance(fn_args, (dict, list)):
                args_str = json.dumps(fn_args)
            else:
                s = str(fn_args).strip()
                if not s or s == "None":
                    args_str = "{}"
                else:
                    try:
                        json.loads(s)
                        args_str = s
                    except Exception:
                        args_str = json.dumps({"raw_value": s})

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
            logger.info("Successfully parsed tool call(s) from ChatGPT response", count=len(standardized_calls))
            return standardized_calls

    # Fallback: detect inline function calls e.g. `tool_name({"arg": "val"})`
    inline_pattern = r'`?([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*(\{.*?\})\s*\)`?'
    inline_matches = re.findall(inline_pattern, response_text)
    if inline_matches:
        fallback_calls = []
        for fn_name, args_str in inline_matches:
            try:
                json.loads(args_str)
                call_id = f"call_{uuid.uuid4().hex[:12]}"
                fallback_calls.append({
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": fn_name,
                        "arguments": args_str
                    }
                })
            except Exception:
                continue
        if fallback_calls:
            logger.info("Successfully parsed inline function call(s) from ChatGPT response", count=len(fallback_calls))
            return fallback_calls

    return None
