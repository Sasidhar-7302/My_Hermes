# -*- coding: utf-8 -*-
"""
Hermes Smartphone Companion Bridge (Android & iOS)
Handles camera photo ingestion for vision models, mobile sensor telemetry,
and clipboard synchronization.
"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SmartphoneBridge:
    """Manages smartphone companion photo streams, sensors, and clipboard history."""

    def __init__(self, photo_dir: Optional[Path] = None):
        self.photo_dir = photo_dir or (Path(__file__).resolve().parent.parent.parent / "local_model_lab" / "outputs" / "mesh_photos")
        self.photo_dir.mkdir(parents=True, exist_ok=True)
        self.clipboard_history: List[Dict[str, Any]] = []
        self.activity_log: List[Dict[str, Any]] = []

    def save_captured_photo(self, img_bytes: bytes, filename: str) -> Path:
        """Saves raw image bytes directly to outputs directory."""
        filepath = self.photo_dir / filename
        filepath.write_bytes(img_bytes)
        logger.info(f"📸 Saved smartphone photo {filename} ({len(img_bytes)} bytes)")
        return filepath

    def save_camera_photo(self, photo_b64: str, device_id: str) -> Dict[str, Any]:
        """Decodes and stores a high-resolution photo from the mobile camera."""
        filename = f"phone_{device_id[:6]}_{int(time.time())}.jpg"
        raw_b64 = photo_b64.split(",")[-1]
        img_bytes = base64.b64decode(raw_b64)
        filepath = self.save_captured_photo(img_bytes, filename)

        return {
            "filename": filename,
            "filepath": str(filepath),
            "size_bytes": len(img_bytes),
            "timestamp": time.time(),
        }

    def record_clipboard(self, content: str, source: str = "phone"):
        """Maintains rolling buffer of recent synchronized clipboard items."""
        if not content:
            return
        entry = {
            "content": content,
            "source": source,
            "length": len(content),
            "timestamp": time.time(),
        }
        self.clipboard_history.insert(0, entry)
        if len(self.clipboard_history) > 20:
            self.clipboard_history = self.clipboard_history[:20]

    def buffer_clipboard(self, content: str, source: str = "mesh"):
        """Alias for record_clipboard."""
        return self.record_clipboard(content=content, source=source)

    def log_activity(self, action: str, detail: str):
        """Records smartphone bridge interaction."""
        self.activity_log.append({
            "action": action,
            "detail": detail,
            "timestamp": time.time(),
        })
        if len(self.activity_log) > 50:
            self.activity_log = self.activity_log[-50:]

    def get_clipboard_history(self) -> List[Dict[str, Any]]:
        return list(self.clipboard_history)


_phone_bridge_instance: Optional[SmartphoneBridge] = None


def get_smartphone_bridge() -> SmartphoneBridge:
    global _phone_bridge_instance
    if _phone_bridge_instance is None:
        _phone_bridge_instance = SmartphoneBridge()
    return _phone_bridge_instance
