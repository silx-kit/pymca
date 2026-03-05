import logging
import argparse

_LOG_LEVELS_DICT = {
    # Explicit args
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    # int args sorted by increasing verbosity
    "0": logging.CRITICAL,
    "1": logging.ERROR,
    "2": logging.WARNING,
    "3": logging.INFO,
    "4": logging.DEBUG,
}


def parse_log_level(value: str) -> int:
    """Convert CLI logging argument to logging level."""
    key = value.lower()
    if key in _LOG_LEVELS_DICT:
        return _LOG_LEVELS_DICT[key]
    raise argparse.ArgumentTypeError(
        f"Invalid log level '{value}'. Use debug/info/warning/error/critical or verbosity 0-4."
    )
