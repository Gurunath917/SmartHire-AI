"""
Structured logging setup using loguru.
Import `logger` from here throughout the app.
Never log passwords, API keys, or sensitive PII.
"""
import sys
from loguru import logger


def setup_logging(debug: bool = False) -> None:
    """Configure loguru for the application."""
    logger.remove()  # Remove default handler

    log_level = "DEBUG" if debug else "INFO"
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Console output
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True,
    )

    # File output — rotates daily, keeps 7 days
    logger.add(
        "logs/smarthire_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="INFO",
        rotation="00:00",       # rotate at midnight
        retention="7 days",
        compression="zip",
        enqueue=True,           # thread-safe
    )


__all__ = ["logger", "setup_logging"]
