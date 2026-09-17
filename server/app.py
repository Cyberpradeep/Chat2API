"""
FastAPI application setup with lifecycle management and CORS.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from providers import get_provider
from server.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("app")

provider = get_provider("chatgpt")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up ChatGPT Modular Engine...")
    try:
        await provider.initialize()
    except Exception as e:
        logger.error(f"Startup initialization note: {e}")
        logger.info("Browser will initialize automatically on the first request.")
    yield
    logger.info("Shutting down ChatGPT Modular Engine...")
    await provider.close()

def create_app() -> FastAPI:
    app = FastAPI(
        title="ChatGPT Modular Web-to-API Engine",
        description="Local, private API bridge supporting Think Mode, Web Search, Deep Research, and Attachments",
        version="2.0.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app

app = create_app()
