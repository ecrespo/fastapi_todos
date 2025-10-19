import sys
import os
import json
import logging
from datetime import datetime
from typing import Any, Dict
from rich.logging import RichHandler

from app.shared.config import get_settings


class JSONFormatter(logging.Formatter):
    """Simple JSON formatter for logging records."""

    def format(self, record: logging.LogRecord) -> str:
        log: Dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include optional attributes if present
        if record.exc_info:
            log["exc_info"] = self.formatException(record.exc_info)
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log.update(record.extra)
        return json.dumps(log, ensure_ascii=False)


class LoggerSingleton:
    _instance = None

    def __new__(cls, app_name=None):
        if cls._instance is None:
            # Create logs directory if it doesn't exist
            logs_dir = "logs"
            os.makedirs(logs_dir, exist_ok=True)

            # Generate log filename with date
            log_filename = os.path.join(
                logs_dir,
                f"{datetime.now().strftime('%Y-%m-%d')}.log",
            )

            # Determine app name
            if not app_name:
                try:
                    app_name = get_settings().app_name
                except Exception:
                    app_name = "app"

            # Set up base logger
            base_logger = logging.getLogger(app_name)
            base_logger.setLevel(logging.INFO)
            base_logger.propagate = False  # avoid duplicate logs

            # Clean previous handlers if any
            for h in base_logger.handlers:
                base_logger.removeHandler(h)

            # Console handler with Rich
            rich_handler = RichHandler(rich_tracebacks=True, markup=True)
            rich_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                "%(message)s"
            )  # Rich formats the rest
            rich_handler.setFormatter(console_formatter)
            base_logger.addHandler(rich_handler)

            # File handler with JSON formatting
            file_handler = logging.FileHandler(log_filename, encoding="utf-8")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(JSONFormatter())
            base_logger.addHandler(file_handler)

            cls._instance = base_logger

        return cls._instance

# Create a logger instance
logger = LoggerSingleton(app_name=get_settings().app_name)  # noqa: F811
