"""
Logging configuration for the Financial Email Agent.

This module sets up structured logging using Loguru with support for
file rotation, console output, and different log levels.
"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger

from ..config.models import LoggingConfig


def setup_logger(config: LoggingConfig) -> logger:
    """
    Configure the application logger with Loguru.

    Args:
        config: Logging configuration

    Returns:
        Configured logger instance
    """
    # Remove default handler
    logger.remove()

    # Console handler with colored output
    logger.add(
        sys.stderr,
        level=config.level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Ensure log directory exists
    log_path = Path(config.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # File handler with rotation
    logger.add(
        config.file,
        level=config.level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation=f"{config.max_size_mb} MB",
        retention=config.backup_count,
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Thread-safe logging
    )

    logger.info("Logger initialized successfully")
    logger.debug(f"Log level: {config.level}")
    logger.debug(f"Log file: {config.file}")

    return logger


def get_logger(name: Optional[str] = None):
    """
    Get a logger instance with optional name binding.

    Args:
        name: Optional name to bind to the logger

    Returns:
        Logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""

    @property
    def logger(self):
        """Get a logger instance bound to the class name."""
        return get_logger(self.__class__.__name__)


# Convenience functions for common log patterns
def log_function_call(func_name: str, **kwargs):
    """Log a function call with its parameters."""
    params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.debug(f"Calling {func_name}({params})")


def log_error(error: Exception, context: str = ""):
    """Log an error with context."""
    if context:
        logger.error(f"{context}: {type(error).__name__}: {str(error)}")
    else:
        logger.error(f"{type(error).__name__}: {str(error)}")
    logger.exception(error)


def log_success(message: str, **details):
    """Log a success message with optional details."""
    if details:
        detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
        logger.success(f"{message} ({detail_str})")
    else:
        logger.success(message)


def log_performance(operation: str, duration_ms: float):
    """Log performance metrics."""
    logger.info(f"Performance: {operation} completed in {duration_ms:.2f}ms")

# Made with Bob
