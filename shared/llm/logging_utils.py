"""Small logging helper so every module gets a consistently formatted logger.

Log level is controlled by the ``LLM_LOG_LEVEL`` environment variable
(defaults to INFO). Logs go to stderr to keep stdout clean for program output.
"""

from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    level_name = os.getenv("LLM_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    root = logging.getLogger("bbi")
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under the ``bbi`` root."""
    _configure_root()
    short = name.split(".")[-1]
    return logging.getLogger(f"bbi.{short}")
