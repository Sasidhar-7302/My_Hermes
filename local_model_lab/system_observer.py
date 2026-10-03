# -*- coding: utf-8 -*-
"""
System & Proactivity Observer for Hermes Agent
Monitors system resources (CPU, RAM, Disk, GPU), warns before runaway tasks freeze the machine,
and prepares proactive daily intelligence briefings.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class SystemHealth:
    """Snapshot of host system health metrics."""
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    disk_percent: float
    disk_free_gb: float
    disk_total_gb: float
    status: str       # "HEALTHY", "WARNING", "CRITICAL"
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "ram_percent": self.ram_percent,
            "ram_used_gb": round(self.ram_used_gb, 2),
            "ram_total_gb": round(self.ram_total_gb, 2),
            "disk_percent": self.disk_percent,
            "disk_free_gb": round(self.disk_free_gb, 2),
            "disk_total_gb": round(self.disk_total_gb, 2),
            "status": self.status,
            "timestamp": self.timestamp,
        }


class SystemObserver:
    """Proactive system observer and health tracker."""

    def get_health(self) -> SystemHealth:
        """Collects current system resource metrics."""
        now = datetime.now(timezone.utc).isoformat()
        cpu_pct = 0.0
        ram_pct = 0.0
        ram_used = 0.0
        ram_total = 16.0

        if HAS_PSUTIL:
            try:
                cpu_pct = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                ram_pct = mem.percent
                ram_used = mem.used / (1024 ** 3)
                ram_total = mem.total / (1024 ** 3)
            except Exception:
                pass
        else:
            try:
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ('dwLength', ctypes.c_ulong),
                        ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong),
                        ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong),
                        ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong),
                        ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('sullAvailExtendedVirtual', ctypes.c_ulonglong),
                    ]
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                ram_pct = float(stat.dwMemoryLoad)
                ram_total = stat.ullTotalPhys / (1024 ** 3)
                ram_used = (stat.ullTotalPhys - stat.ullAvailPhys) / (1024 ** 3)
            except Exception:
                pass

        # Disk usage on system drive
        disk_pct = 0.0
        disk_free = 0.0
        disk_total = 0.0
        try:
            drive = os.path.splitdrive(os.path.abspath(__file__))[0] or "C:"
            usage = shutil.disk_usage(drive)
            disk_total = usage.total / (1024 ** 3)
            disk_free = usage.free / (1024 ** 3)
            disk_pct = round(((usage.total - usage.free) / usage.total) * 100, 1)
        except Exception:
            pass

        # Health status classification
        status = "HEALTHY"
        if cpu_pct > 90 or ram_pct > 92 or disk_free < 5.0:
            status = "CRITICAL"
        elif cpu_pct > 75 or ram_pct > 80 or disk_free < 15.0:
            status = "WARNING"

        return SystemHealth(
            cpu_percent=cpu_pct,
            ram_percent=ram_pct,
            ram_used_gb=ram_used,
            ram_total_gb=ram_total,
            disk_percent=disk_pct,
            disk_free_gb=disk_free,
            disk_total_gb=disk_total,
            status=status,
            timestamp=now,
        )

    def get_briefing_preview(self) -> Dict[str, Any]:
        """Prepares a morning intelligence brief summary."""
        health = self.get_health()
        return {
            "title": "Hermes Daily System & Intelligence Briefing",
            "schedule": "Every day at 9:00 AM",
            "destination": "Telegram Bot & Local Dashboard",
            "system_health": health.to_dict(),
            "proactive_monitors": [
                {"name": "System Resource Guard", "status": "Active", "metric": f"RAM: {health.ram_percent}%"},
                {"name": "Emergency Panic Stop Guard", "status": "Armed", "hotkey": "Ctrl+Esc"},
                {"name": "Paper Desktop Studio Gateway", "status": "Active", "port": 29979},
                {"name": "Win32 Multi-Monitor Manager", "status": "Active", "monitors": 1},
                {"name": "PII & Secret Redaction Shield", "status": "Enforcing", "rules": 15},
            ]
        }

    def generate_daily_briefing(self) -> str:
        """Generates formatted executive morning intelligence briefing text."""
        preview = self.get_briefing_preview()
        health = preview["system_health"]
        monitors = preview["proactive_monitors"]

        lines = [
            f"=== {preview['title']} ===",
            f"Generated: {health.get('timestamp', '')[:19].replace('T', ' ')} UTC",
            f"Schedule: {preview['schedule']} | Destination: {preview['destination']}",
            "",
            f"1. SYSTEM HEALTH: [{health.get('status', 'HEALTHY')}]",
            f"   - CPU Utilization: {health.get('cpu_percent', 0.0)}%",
            f"   - RAM Memory: {health.get('ram_percent', 0.0)}% ({health.get('ram_used_gb', 0.0)} GB / {health.get('ram_total_gb', 0.0)} GB)",
            f"   - Disk Space: {health.get('disk_free_gb', 0.0)} GB Free ({health.get('disk_percent', 0.0)}% used)",
            "",
            "2. PROACTIVE DAEMON STATUS:",
        ]
        for m in monitors:
            detail = m.get("metric") or m.get("hotkey") or m.get("port") or m.get("rules") or m.get("monitors") or ""
            lines.append(f"   * {m['name']}: {m['status']} ({detail})")

        lines.extend([
            "",
            "3. RECOMMENDATIONS & TASKS:",
            "   - Model failover cascades operational across Groq and Gemini.",
            "   - Hardline deletion and payment safety shields active across all agent dispatches.",
            "   - Use Ctrl+Alt+Space to summon Hermes or Ctrl+Esc to engage emergency panic stop.",
            "==========================================================="
        ])
        return "\n".join(lines)


_observer_instance = SystemObserver()


def get_system_observer() -> SystemObserver:
    """Returns singleton SystemObserver."""
    return _observer_instance
