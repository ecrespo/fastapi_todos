import sys
import os
from datetime import datetime
from loguru import logger

from app.shared.config import get_settings

class LoggerSingleton:
    _instance = None

    def __new__(cls, app_name=get_settings.app_name):
        if cls._instance is None:
            # Remove any existing handlers
            logger.remove()

            # Create logs directory if it doesn't exist
            logs_dir = "logs"
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)

            # Generate log filename with date
            log_filename = os.path.join(
                logs_dir,
                f"{datetime.now().strftime('%Y-%m-%d')}.log"
            )

            # Add handler for console output (real-time logs)
            logger.add(
                sys.stdout,
                colorize=True,
                format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                       f"<blue>{app_name}</blue> | "
                       "{level} | "
                       "<level>{message}</level>",
            )

            # Add handler for file output
            logger.add(
                log_filename,
                rotation="12:00",  # Create new file at midnight
                retention="30 days",  # Keep logs for 30 days
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                       f"{app_name} | "
                       "{level} | "
                       "{message}",
            )

            cls._instance = logger

        return cls._instance

# Create a logger instance
logger = LoggerSingleton(app_name=get_settings.app_name)  # noqa: F811
