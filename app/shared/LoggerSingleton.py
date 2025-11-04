"""Structured logging configuration using structlog with Rich console output and JSON file output."""

import logging
import os
from datetime import datetime
from pathlib import Path

import structlog
from rich.console import Console
from rich.logging import RichHandler

from app.shared.config import get_settings


def setup_structlog() -> structlog.stdlib.BoundLogger:
    """Configure structlog with Rich console output and JSON file output.

    Returns:
        Configured structlog logger instance
    """
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Generate log filename with date
    log_filename = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    # Get app name from settings
    try:
        app_name = get_settings().app_name
    except Exception:
        app_name = "app"

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        handlers=[],  # We'll add handlers manually
    )

    # Console output with Rich (colorized, human-readable)
    console = Console(stderr=True, force_terminal=True)
    rich_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
        markup=True,
        show_time=True,
        show_level=True,
        show_path=True,
    )
    rich_handler.setLevel(logging.INFO)

    # File output with JSON (structured, machine-readable)
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # Get root logger and configure handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []  # Clear existing handlers
    root_logger.addHandler(rich_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)

    # Configure structlog processors
    shared_processors = [
        # Add extra attributes of LogRecord objects to the event dictionary
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add stack info if available
        structlog.processors.StackInfoRenderer(),
        # Format exception info if present
        structlog.processors.format_exc_info,
        # Unicode decode errors
        structlog.processors.UnicodeDecoder(),
    ]

    # Configure structlog
    structlog.configure(
        processors=shared_processors
        + [
            # Prepare event dict for `ProcessorFormatter`
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        # Logger factory
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger instances for performance
        cache_logger_on_first_use=True,
    )

    # Configure processor formatter for standard logging
    # This makes standard logging calls (logging.info, etc.) also benefit from structlog
    formatter_processors = [
        # Remove _record & _from_structlog from event_dict
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
    ]

    # Rich console formatter (human-readable)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=formatter_processors
        + [
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.RichTracebackFormatter(),
            ),
        ],
    )

    # JSON file formatter (machine-readable)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=formatter_processors + [structlog.processors.JSONRenderer()],
    )

    # Apply formatters to handlers
    rich_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)

    # Get a structlog logger
    logger = structlog.get_logger(app_name)

    # Log initialization
    logger.info(
        "logger_initialized",
        app_name=app_name,
        log_file=str(log_filename),
        environment=os.getenv("APP_ENV", "develop"),
    )

    return logger


# Singleton instance
_logger_instance: structlog.stdlib.BoundLogger | None = None


def get_logger() -> structlog.stdlib.BoundLogger:
    """Get or create the singleton logger instance.

    Returns:
        Configured structlog logger
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = setup_structlog()
    return _logger_instance


# Create default logger instance for backward compatibility
logger = get_logger()
