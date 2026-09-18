"""
FastAPI application setup with lifecycle management, structured logging, and CORS.
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from config.logger import get_logger
from providers import get_provider
from server.routes import router

logger = get_logger("server.app")
provider = get_provider("chatgpt")

class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs all incoming HTTP requests and response metrics using structlog."""
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_host = request.client.host if request.client else "unknown"
        
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        logger.info(
            "HTTP request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            client_ip=client_host,
            latency_ms=duration_ms
        )
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up ZeroKey Web-to-API Engine...")
    try:
        await provider.initialize()
    except Exception as e:
        logger.warning("Startup browser initialization deferred", error=str(e))
        logger.info("Browser will initialize automatically on the first request.")
    yield
    logger.info("Shutting down ZeroKey Web-to-API Engine...")
    await provider.close()

def create_app() -> FastAPI:
    app = FastAPI(
        title="ZeroKey: Free ChatGPT-to-OpenAI API Bridge",
        description="Local, private API bridge supporting Think Mode, Web Search, Deep Research, and Attachments",
        version="2.0.0",
        lifespan=lifespan
    )

    # Standard W3C compliant CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Structured request logger middleware
    app.add_middleware(LoggingMiddleware)

    app.include_router(router)
    return app

app = create_app()
