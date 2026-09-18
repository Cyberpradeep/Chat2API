"""
Structured Logging Architecture for ZeroKey using structlog.
Provides unified, high-performance structured logging for console and file output.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
import structlog
from config.settings import settings

_LOGGING_CONFIGURED = False

def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None
) -> None:
    """
    Configures structlog and standard library logging handlers.
    Outputs rich colored logs to stdout and structured JSON records to logs/zerokey.log.
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    level_name = (log_level or settings.LOG_LEVEL or "INFO").upper()
    numeric_level = getattr(logging, level_name, logging.INFO)

    logs_dir = Path(settings.LOGS_DIR)
    logs_dir.mkdir(exist_ok=True)
    target_file = Path(log_file) if log_file else (logs_dir / "zerokey.log")

    # Common structlog processor chain
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handlers = []

    # 1. Console Handler (Colored, readable key-value formatting)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processor=structlog.dev.ConsoleRenderer(colors=True, pad_event_to=30)
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(numeric_level)
    handlers.append(console_handler)

    # 2. File Handler (Persistent JSON log lines for full auditability)
    try:
        file_handler = logging.FileHandler(str(target_file), encoding="utf-8")
        file_formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processor=structlog.processors.JSONRenderer()
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(numeric_level)
        handlers.append(file_handler)
    except Exception as e:
        sys.stderr.write(f"[Warning] Failed to initialize file logger at {target_file}: {e}\n")

    # Intercept standard library logging
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers = handlers

    # Quiet overly chatty third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    _LOGGING_CONFIGURED = True

def get_logger(name: str = "zerokey"):
    """
    Returns a structlog bound logger configured with the given module name.
    """
    if not _LOGGING_CONFIGURED:
        setup_logging()
    return structlog.get_logger(name)

# Ensure logging is initialized on import
setup_logging()
