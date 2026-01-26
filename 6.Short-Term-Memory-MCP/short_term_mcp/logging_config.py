"""Structured logging configuration for Short-Term Memory MCP Server"""

import json
import logging
import time
from datetime import datetime
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable

from .config import LOG_DIR


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields from extra
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with colors"""

    # Color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        # Base format
        log_msg = f"{color}[{record.levelname}]{reset} {record.name} - {record.getMessage()}"

        # Add timing info if present
        if hasattr(record, "extra_data") and "duration_ms" in record.extra_data:
            duration = record.extra_data["duration_ms"]
            log_msg += f" ({duration:.2f}ms)"

        # Add exception if present
        if record.exc_info:
            log_msg += f"\n{self.formatException(record.exc_info)}"

        return log_msg


def setup_logging(
    log_level: str = "INFO", enable_file_logging: bool = True, enable_console_logging: bool = True
) -> None:
    """
    Setup logging configuration for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Enable logging to rotating files
        enable_console_logging: Enable logging to console
    """
    # Ensure log directory exists
    LOG_DIR.mkdir(exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (human-readable)
    if enable_console_logging:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ConsoleFormatter())
        root_logger.addHandler(console_handler)

    # File handler (JSON structured)
    if enable_file_logging:
        # Main application log
        app_log_path = LOG_DIR / "short_term_mcp.log"
        app_handler = RotatingFileHandler(
            app_log_path, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        app_handler.setLevel(logging.DEBUG)
        app_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(app_handler)

        # Error log (errors only)
        error_log_path = LOG_DIR / "errors.log"
        error_handler = RotatingFileHandler(
            error_log_path, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(error_handler)

    # Set levels for specific loggers
    logging.getLogger("short_term_mcp.database").setLevel(logging.DEBUG)
    logging.getLogger("short_term_mcp.tools_impl").setLevel(logging.INFO)
    logging.getLogger("short_term_mcp.utils").setLevel(logging.INFO)


def log_performance(operation_name: str):
    """
    Decorator to log function execution time and parameters.

    Args:
        operation_name: Name of the operation for logging
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(func.__module__)
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                logger.info(
                    f"{operation_name} completed",
                    extra={
                        "extra_data": {
                            "operation": operation_name,
                            "duration_ms": duration_ms,
                            "success": True,
                            "args_count": len(args),
                            "kwargs_count": len(kwargs),
                        }
                    },
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                logger.error(
                    f"{operation_name} failed: {str(e)}",
                    exc_info=True,
                    extra={
                        "extra_data": {
                            "operation": operation_name,
                            "duration_ms": duration_ms,
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    },
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(func.__module__)
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                logger.info(
                    f"{operation_name} completed",
                    extra={
                        "extra_data": {
                            "operation": operation_name,
                            "duration_ms": duration_ms,
                            "success": True,
                        }
                    },
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                logger.error(
                    f"{operation_name} failed: {str(e)}",
                    exc_info=True,
                    extra={
                        "extra_data": {
                            "operation": operation_name,
                            "duration_ms": duration_ms,
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    },
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Initialize logging on module import
setup_logging()
