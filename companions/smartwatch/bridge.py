# -*- coding: utf-8 -*-
"""
Hermes Smartwatch Companion Bridge (WearOS, Galaxy Watch, Apple Watch)
Handles wearable state, wrist haptic vibration sequences, and voice streaming.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Standard Wrist Haptic Patterns (milliseconds on / off)
HAPTIC_PATTERNS = {
    "TASK_COMPLETE": [100, 50, 100],
    "PANIC_STOP": [300, 100, 300, 100, 500],
    "CLIPBOARD_SYNC": [60],
    "LOW_BATTERY": [200, 100, 200],
    "VOICE_LISTENING": [40],
}


class SmartwatchBridge:
    """Manages smartwatch wearable companion capabilities and events."""

    def __init__(self):
        self.active_watches: Dict[str, Dict[str, Any]] = {}

    def get_quick_actions(self) -> List[Dict[str, str]]:
        """Returns wearable 1-tap quick action buttons."""
        return [
            {"id": "voice", "label": "🎙️ Talk to Hermes", "color": "#10b981"},
            {"id": "clipboard", "label": "📋 Grab PC Clip", "color": "#38bdf8"},
            {"id": "status", "label": "⚡ PC Status", "color": "#f59e0b"},
            {"id": "panic", "label": "🚨 Emergency Stop", "color": "#ef4444"},
        ]

    def format_tile_data(
        self,
        telemetry: Optional[Union[Dict[str, Any], float]] = None,
        cpu_pct: float = 0.0,
        ram_pct: float = 0.0,
        active_agent: str = "CEO",
    ) -> Dict[str, Any]:
        """Formats wearable glanceable Tile / Complication telemetry."""
        if isinstance(telemetry, dict):
            c_pct = float(telemetry.get("cpu_pct", telemetry.get("cpu", cpu_pct)))
            r_pct = float(telemetry.get("ram_pct", telemetry.get("ram", ram_pct)))
            agent = str(telemetry.get("active_agent", telemetry.get("status", active_agent)))
            extra = {k: v for k, v in telemetry.items() if k not in ("cpu_pct", "ram_pct", "active_agent")}
            res = {
                "title": "Hermes Core",
                "active_agent": agent,
                "cpu": f"{c_pct:.0f}%",
                "ram": f"{r_pct:.0f}%",
                "updated_at": time.time(),
            }
            res.update(extra)
            return res

        val_cpu = float(telemetry) if isinstance(telemetry, (int, float)) else cpu_pct
        return {
            "title": "Hermes Core",
            "active_agent": active_agent,
            "cpu": f"{val_cpu:.0f}%",
            "ram": f"{ram_pct:.0f}%",
            "updated_at": time.time(),
        }

    def get_haptic_pattern(self, event_type: str) -> List[int]:
        """Resolves physical wrist vibration sequence for a given event."""
        return HAPTIC_PATTERNS.get(event_type.upper(), [80])


_watch_bridge_instance: Optional[SmartwatchBridge] = None


def get_smartwatch_bridge() -> SmartwatchBridge:
    global _watch_bridge_instance
    if _watch_bridge_instance is None:
        _watch_bridge_instance = SmartwatchBridge()
    return _watch_bridge_instance
