# -*- coding: utf-8 -*-
"""
Smart Shutdown & Network-Idle Monitor for Hermes Agent
Monitors network throughput and system activity to safely put the PC to sleep,
hibernate, or shut down once long downloads, training jobs, or batch runs complete.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Ensure Windows UTF-8 stdout safety
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def get_user_idle_seconds() -> Optional[float]:
    """Returns elapsed seconds since the user last moved mouse or pressed a key."""
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("dwTime", ctypes.c_uint),
            ]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception:
        pass
    return None


@dataclass
class SmartShutdownConfig:
    idle_minutes: int = 2
    idle_kbps: float = 35.0
    active_kbps: float = 150.0
    sample_seconds: int = 3
    action: str = "shutdown"  # "shutdown", "sleep", "hibernate"
    countdown_seconds: int = 60
    require_user_idle_seconds: int = 120

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SmartShutdownConfig:
        return cls(
            idle_minutes=int(data.get("idle_minutes", 2)),
            idle_kbps=float(data.get("idle_kbps", 35.0)),
            active_kbps=float(data.get("active_kbps", 150.0)),
            sample_seconds=int(data.get("sample_seconds", 3)),
            action=str(data.get("action", "shutdown")).lower(),
            countdown_seconds=int(data.get("countdown_seconds", 60)),
            require_user_idle_seconds=int(data.get("require_user_idle_seconds", 120)),
        )


@dataclass
class MonitorSnapshot:
    running: bool = False
    status: str = "INACTIVE"  # "INACTIVE", "MONITORING", "ACTIVE_DOWNLOAD", "COUNTDOWN", "ABORTED"
    started_at: float = 0.0
    current_rate_kbps: float = 0.0
    seen_active: bool = False
    idle_seconds: int = 0
    idle_target_seconds: int = 120
    countdown_remaining: int = 0
    user_idle_seconds: float = 0.0
    action: str = "shutdown"
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SmartShutdownMonitor:
    """Threaded network-idle observer for automated power management."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._config = SmartShutdownConfig()
        self._snapshot = MonitorSnapshot()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._snapshot.running

    def start(self, config: Optional[SmartShutdownConfig] = None) -> Tuple[bool, str]:
        with self._lock:
            if self._snapshot.running:
                return False, "Smart shutdown monitor is already active."

            self._config = config or SmartShutdownConfig()
            self._stop_event.clear()
            self._snapshot = MonitorSnapshot(
                running=True,
                status="MONITORING",
                started_at=time.time(),
                current_rate_kbps=0.0,
                seen_active=False,
                idle_seconds=0,
                idle_target_seconds=self._config.idle_minutes * 60,
                countdown_remaining=0,
                action=self._config.action,
                message=f"Monitoring network activity. Will trigger {self._config.action} after download completes.",
            )
            self._thread = threading.Thread(target=self._run_loop, name="hermes-smart-shutdown", daemon=True)
            self._thread.start()

        logger.info(f"Smart shutdown monitor engaged: action={self._config.action}, target_idle={self._config.idle_minutes}m")
        return True, f"Smart shutdown monitor active ({self._config.action} mode)."

    def cancel(self) -> Tuple[bool, str]:
        with self._lock:
            if not self._snapshot.running:
                return False, "Smart shutdown monitor is not currently running."

            self._stop_event.set()
            self._snapshot.running = False
            self._snapshot.status = "ABORTED"
            self._snapshot.message = "Smart shutdown cancelled by user."

        # Abort any Windows scheduled shutdown if counting down
        try:
            subprocess.run(["shutdown", "/a"], capture_output=True, text=True, check=False)
        except Exception:
            pass

        logger.info("Smart shutdown monitor cancelled.")
        return True, "Smart shutdown cancelled and pending commands aborted."

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            snap = self._snapshot.to_dict()
            snap["user_idle_seconds"] = round(get_user_idle_seconds() or 0.0, 1)
            return snap

    def _execute_power_action(self, action: str):
        """Executes the final Windows power state command."""
        logger.warning(f"🚨 Executing Smart Power Action: {action.upper()}")
        action_clean = action.lower()
        try:
            if action_clean == "sleep":
                # Put system to sleep (S3 state)
                subprocess.run(
                    ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                    capture_output=True,
                    check=False
                )
            elif action_clean == "hibernate":
                subprocess.run(
                    ["shutdown", "/h"],
                    capture_output=True,
                    check=False
                )
            else:
                # Standard safe shutdown with 30s countdown
                subprocess.run(
                    ["shutdown", "/s", "/t", "30", "/c", "Hermes Smart Shutdown: Download complete & system idle."],
                    capture_output=True,
                    check=False
                )
        except Exception as exc:
            logger.error(f"Failed to execute {action}: {exc}")

    def _run_loop(self) -> None:
        cfg = self._config
        sample_time = max(1, cfg.sample_seconds)
        idle_target = cfg.idle_minutes * 60
        active_thresh = cfg.active_kbps
        idle_thresh = cfg.idle_kbps

        prev_net = psutil.net_io_counters() if HAS_PSUTIL else None
        prev_t = time.time()

        while not self._stop_event.is_set():
            time.sleep(sample_time)
            now = time.time()
            dt = max(0.1, now - prev_t)

            rate_kbps = 0.0
            if HAS_PSUTIL and prev_net:
                try:
                    cur_net = psutil.net_io_counters()
                    d_bytes = max(0, cur_net.bytes_recv - prev_net.bytes_recv)
                    rate_kbps = (d_bytes / 1024.0) / dt
                    prev_net = cur_net
                except Exception:
                    pass
            prev_t = now

            user_idle = get_user_idle_seconds() or 0.0

            with self._lock:
                self._snapshot.current_rate_kbps = round(rate_kbps, 1)
                self._snapshot.user_idle_seconds = round(user_idle, 1)

                if rate_kbps >= active_thresh:
                    self._snapshot.seen_active = True
                    self._snapshot.idle_seconds = 0
                    self._snapshot.status = "ACTIVE_DOWNLOAD"
                    self._snapshot.message = f"Active download detected: {rate_kbps:.0f} KB/s"
                elif self._snapshot.seen_active and rate_kbps <= idle_thresh:
                    # Check if user is actively using the computer
                    if cfg.require_user_idle_seconds > 0 and user_idle < cfg.require_user_idle_seconds:
                        self._snapshot.idle_seconds = 0
                        self._snapshot.status = "USER_ACTIVE"
                        self._snapshot.message = f"Download idle ({rate_kbps:.0f} KB/s), but user is actively working."
                    else:
                        self._snapshot.idle_seconds += sample_time
                        self._snapshot.status = "IDLE_ACCUMULATING"
                        remaining = max(0, idle_target - self._snapshot.idle_seconds)
                        self._snapshot.message = f"Download finished. Idle for {self._snapshot.idle_seconds}s (shutting down in {remaining}s)..."
                else:
                    self._snapshot.idle_seconds = 0
                    if not self._snapshot.seen_active:
                        self._snapshot.status = "MONITORING"
                        self._snapshot.message = f"Waiting for download activity to exceed {active_thresh} KB/s (current: {rate_kbps:.0f} KB/s)"

                # Check if trigger threshold reached
                if self._snapshot.seen_active and self._snapshot.idle_seconds >= idle_target:
                    self._snapshot.status = "COUNTDOWN"
                    self._snapshot.countdown_remaining = cfg.countdown_seconds
                    break

        # Countdown phase with abort possibility
        if not self._stop_event.is_set() and self._snapshot.status == "COUNTDOWN":
            cd_time = cfg.countdown_seconds
            while cd_time > 0 and not self._stop_event.is_set():
                with self._lock:
                    self._snapshot.countdown_remaining = cd_time
                    self._snapshot.message = f"Smart shutdown in {cd_time}s! Click Cancel or press Ctrl+Esc to abort."
                time.sleep(1.0)
                cd_time -= 1

            if not self._stop_event.is_set():
                with self._lock:
                    self._snapshot.running = False
                    self._snapshot.status = "EXECUTED"
                    self._snapshot.message = f"Executing {cfg.action} now."
                self._execute_power_action(cfg.action)
                return

        with self._lock:
            self._snapshot.running = False


# Global singleton monitor
_smart_shutdown_instance: Optional[SmartShutdownMonitor] = None


def get_smart_shutdown_monitor() -> SmartShutdownMonitor:
    """Returns singleton SmartShutdownMonitor instance."""
    global _smart_shutdown_instance
    if _smart_shutdown_instance is None:
        _smart_shutdown_instance = SmartShutdownMonitor()
    return _smart_shutdown_instance
