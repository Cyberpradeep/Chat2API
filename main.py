"""
FastAPI Server for ChatGPT Web-to-API Bridge
Exposes REST endpoints to interact with ChatGPT via Playwright browser automation.
"""

import sys
import logging
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from chatgpt_service import ChatGPTService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("api_server")

# Instantiate service singleton
service = ChatGPTService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize Playwright and launch browser
    logger.info("Starting up ChatGPT API Service...")
    try:
        await service.initialize()
    except Exception as e:
        logger.error(f"Failed to auto-initialize ChatGPT on startup: {e}")
        logger.info("You can still initialize it on the first request or run python login_helper.py first.")
    yield
    # Shutdown: close browser cleanly
    logger.info("Shutting down ChatGPT API Service...")
    await service.close()

app = FastAPI(
    title="ChatGPT Web-to-API Bridge",
    description="Unofficial local REST API wrapping the ChatGPT web client via Playwright automation",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local web applications or frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    prompt: str = Field(..., description="Prompt message to send to ChatGPT", min_length=1)
    new_chat: bool = Field(False, description="Whether to start a fresh conversation session before sending")
    timeout_seconds: int = Field(120, description="Max seconds to wait for generation", ge=10, le=300)


class ChatResponse(BaseModel):
    prompt: str
    response: str
    status: str


class StatusResponse(BaseModel):
    initialized: bool
    browser_ready: bool
    current_url: str | None = None
    input_ready: bool
    profile_dir: str


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "ChatGPT Web-to-API Bridge",
        "status": "online",
        "documentation": "/docs"
    }


@app.get("/api/status", response_model=StatusResponse, tags=["Health"])
async def get_status():
    """Returns browser and ChatGPT interface readiness."""
    return await service.get_status()


@app.post("/api/new-chat", tags=["Chat"])
async def reset_chat():
    """Resets the conversation by navigating to a fresh chat window."""
    try:
        await service.new_chat()
        return {"status": "success", "message": "Started a new conversation session"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset chat: {str(e)}"
        )


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Sends a prompt to ChatGPT, waits for response generation to complete,
    and returns the assistant's reply.
    """
    try:
        result = await service.send_prompt(
            prompt=request.prompt,
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
        logger.exception("Error processing chat prompt")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Automation error: {str(e)}"
        )


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.getenv("PORT", "8088"))
    # Run server on port 8088 (or PORT environment variable)
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=False)
