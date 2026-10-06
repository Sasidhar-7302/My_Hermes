# -*- coding: utf-8 -*-
"""
Hermes Companion Logging System
Provides structured, rotating, and redacted persistent logging for companion devices.
Writes to ~/.hermes/logs/companions.log and maintains an in-memory ring buffer for dashboard inspection.
"""

from __future__ import annotations

import collections
import logging
import os
import re
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional

_TOKEN_RE = re.compile(r"(pair_[A-Za-z0-9_-]{8,}|tok_[A-Za-z0-9_-]{8,}|[A-Za-z0-9_-]{24,})")
_LOG_DIR = Path.home() / ".hermes" / "logs"
_LOG_FILE = _LOG_DIR / "companions.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 5
_RECENT_BUFFER_SIZE = 100

_recent_logs: collections.deque = collections.deque(maxlen=_RECENT_BUFFER_SIZE)


def sanitize_log_text(text: str) -> str:
    """Masks secret tokens and shortens long payload previews for privacy and security."""
    if not isinstance(text, str):
        text = str(text)

    # Redact obvious auth tokens while keeping short prefix
    def _mask_match(m: re.Match) -> str:
        s = m.group(0)
        if len(s) > 12:
            return s[:4] + "..." + s[-4:]
        return "***"

    return _TOKEN_RE.sub(_mask_match, text)


class _RingBufferHandler(logging.Handler):
    """Stores recent log records in memory for instant retrieval by the dashboard."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created)),
                "level": record.levelname,
                "message": record.getMessage(),
                "name": record.name,
                "created": record.created,
                "device_id": getattr(record, "device_id", None),
                "event": getattr(record, "event", None),
            }
            _recent_logs.append(entry)
        except Exception:
            self.handleError(record)


_logger_initialized = False


def get_companion_logger() -> logging.Logger:
    """Returns the dedicated logger for companion ecosystem operations."""
    global _logger_initialized
    logger = logging.getLogger("hermes.companions")

    if not _logger_initialized:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        try:
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            rf_handler = RotatingFileHandler(
                filename=str(_LOG_FILE),
                maxBytes=_MAX_BYTES,
                backupCount=_BACKUP_COUNT,
                encoding="utf-8",
            )
            rf_handler.setFormatter(formatter)
            rf_handler.setLevel(logging.INFO)
            logger.addHandler(rf_handler)
        except Exception as exc:
            # Fallback if ~/.hermes is read-only
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            logger.addHandler(console)
            logger.warning(f"Failed to create companions.log file handler: {exc}")

        # Always add ring buffer handler for web UI
        ring_handler = _RingBufferHandler()
        ring_handler.setLevel(logging.INFO)
        logger.addHandler(ring_handler)

        logger.propagate = False
        _logger_initialized = True

    return logger


def log_companion_event(
    event: str,
    message: str,
    level: str = "INFO",
    device_id: Optional[str] = None,
    device_kind: Optional[str] = None,
    **extra: Any,
) -> None:
    """Logs a companion event with structured context and token sanitization."""
    logger = get_companion_logger()
    safe_msg = sanitize_log_text(message)
    prefix_parts = []
    if device_id:
        prefix_parts.append(f"[{device_id}]")
    if device_kind:
        prefix_parts.append(f"[{device_kind}]")
    prefix_parts.append(f"[{event}]")

    full_message = f"{' '.join(prefix_parts)} {safe_msg}"
    if extra:
        safe_extra = {k: sanitize_log_text(str(v)) for k, v in extra.items()}
        full_message += f" | {safe_extra}"

    lvl = getattr(logging, level.upper(), logging.INFO)
    logger.log(
        lvl,
        full_message,
        extra={"device_id": device_id, "event": event, "device_kind": device_kind},
    )


def get_recent_companion_logs(limit: int = 50, min_level: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns the most recent companion log entries for dashboard display."""
    logs = list(_recent_logs)
    if min_level:
        target_lvl = getattr(logging, min_level.upper(), logging.INFO)
        filtered = []
        for l in logs:
            l_val = getattr(logging, l.get("level", "INFO"), logging.INFO)
            if l_val >= target_lvl:
                filtered.append(l)
        logs = filtered

    return logs[-limit:]
