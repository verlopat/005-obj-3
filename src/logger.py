"""Structured logging setup with rich formatting."""
import logging
import sys
from rich.logging import RichHandler
from src.config import config

def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    return logging.getLogger(name)
