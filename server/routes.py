"""
FastAPI route definitions for native endpoints and OpenAI SDK compatibility.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from core import prompt_compiler
from providers import get_provider
from server.schemas import (
    ChatRequest, ChatResponse, StatusResponse,
    OpenAICompletionRequest, OpenAICompletionResponse, OpenAIChoice
)

logger = logging.getLogger("routes")
router = APIRouter()
provider = get_provider("chatgpt")

@router.get("/", tags=["Health"])
async def root():
    return {
        "service": "ChatGPT Web-to-API Modular Engine",
        "status": "online",
        "features": [
            "system_instructions",
            "tool_calls",
            "think_mode",
            "web_search",
            "deep_research",
            "attachments",
            "openai_v1_compatible"
        ],
        "documentation": "/docs"
    }


@router.get("/api/status", response_model=StatusResponse, tags=["Health"])
async def get_status():
    """Returns browser and ChatGPT interface readiness."""
    return await provider.is_ready()


@router.post("/api/new-chat", tags=["Chat"])
async def reset_chat():
    """Starts a fresh conversation."""
    try:
        await provider.new_chat()
        return {"status": "success", "message": "Conversation session reset."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset chat: {str(e)}"
        )


@router.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Primary endpoint: sends prompt with optional System Instructions,
    Tools (Function Calling), Think mode, Web search, Deep research, and attachments.
    """
    try:
        result = await provider.send_prompt(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            tools=request.tools,
            think=request.think,
            web_search=request.web_search,
            deep_research=request.deep_research,
            files=request.files,
            new_chat=request.new_chat,
            timeout_seconds=request.timeout_seconds
        )
        return result
    except TimeoutError as te:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Generation timed out: {str(te)}"
        )
    except Exception as e:
        logger.exception("Error processing prompt")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Automation error: {str(e)}"
        )


# --- OpenAI SDK Compatibility Endpoints (/v1) ---

@router.get("/v1/models", tags=["OpenAI Compatibility"])
async def list_models():
    """Returns unified model descriptor for OpenAI SDK compatibility."""
    return {
        "object": "list",
        "data": [
            {
                "id": "chatgpt",
                "object": "model",
                "created": 1700000000,
                "owned_by": "openai"
            }
        ]
    }


@router.post("/v1/chat/completions", response_model=OpenAICompletionResponse, tags=["OpenAI Compatibility"])
async def openai_chat_completions(request: OpenAICompletionRequest):
    """
    Drop-in endpoint for the official OpenAI SDK and agent tools (LangChain, AutoGen, CrewAI).
    Supports messages with role='system', role='tool', and function calling via 'tools'.
    """
    try:
        # 1. Compile messages and tool definitions into unified prompt & files
        raw_msgs = [m.model_dump() for m in request.messages]
        compiled_prompt, files = prompt_compiler.compile_messages(
            messages=raw_msgs,
            tools=request.tools
        )

        if not compiled_prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No usable message content found in 'messages' array."
            )

        # 2. Call provider
        result = await provider.send_prompt(
            prompt=compiled_prompt,
            think=bool(request.think),
            web_search=bool(request.web_search),
            deep_research=bool(request.deep_research),
            files=files if files else None
        )

        # 3. Format OpenAI response
        message_payload: Dict[str, Any] = {
            "role": "assistant"
        }

        if result.get("tool_calls"):
            message_payload["content"] = None
            message_payload["tool_calls"] = result["tool_calls"]
            finish_reason = "tool_calls"
        else:
            message_payload["content"] = result["response"]
            finish_reason = "stop"

        if result.get("thought_process"):
            message_payload["reasoning_content"] = result["thought_process"]

        return OpenAICompletionResponse(
            model=request.model or "chatgpt",
            choices=[
                OpenAIChoice(
                    index=0,
                    message=message_payload,
                    finish_reason=finish_reason
                )
            ]
        )
    except Exception as e:
        logger.exception("Error in OpenAI chat completions endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
