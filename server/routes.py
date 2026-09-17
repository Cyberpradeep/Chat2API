"""
FastAPI route definitions for native endpoints and OpenAI SDK compatibility.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
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
        "features": ["think_mode", "web_search", "deep_research", "attachments", "openai_v1_compatible"],
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
    Primary endpoint: sends prompt with optional Think mode, Web search,
    Deep research, and file/image attachments.
    """
    try:
        result = await provider.send_prompt(
            prompt=request.prompt,
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
    Drop-in endpoint for the official OpenAI SDK and tools like LangChain / Cursor.
    """
    try:
        # 1. Parse prompt and any multimodal image URLs from messages
        prompt_text = ""
        files: List[str] = []

        # Extract content from the last user message
        for msg in reversed(request.messages):
            if msg.role == "user":
                if isinstance(msg.content, str):
                    prompt_text = msg.content
                elif isinstance(msg.content, list):
                    # Multimodal content array
                    parts = []
                    for item in msg.content:
                        if item.get("type") == "text":
                            parts.append(item.get("text", ""))
                        elif item.get("type") == "image_url":
                            url_obj = item.get("image_url", {})
                            url = url_obj.get("url", "")
                            if url:
                                files.append(url)
                    prompt_text = "\n".join(parts)
                break

        if not prompt_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user message found in 'messages' array."
            )

        # 2. Call provider with requested toggles
        result = await provider.send_prompt(
            prompt=prompt_text,
            think=bool(request.think),
            web_search=bool(request.web_search),
            deep_research=bool(request.deep_research),
            files=files if files else None
        )

        message_payload: Dict[str, Any] = {
            "role": "assistant",
            "content": result["response"]
        }
        if result.get("thought_process"):
            message_payload["reasoning_content"] = result["thought_process"]

        return OpenAICompletionResponse(
            model=request.model or "chatgpt",
            choices=[
                OpenAIChoice(
                    index=0,
                    message=message_payload,
                    finish_reason="stop"
                )
            ]
        )
    except Exception as e:
        logger.exception("Error in OpenAI chat completions endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
