# -*- coding: utf-8 -*-
"""
Desktop Shell & System Tray Daemon for Hermes Agent
Provides always-on system tray presence, Win32 global hotkeys, selected-text assist,
and emergency panic stop across the entire Windows desktop.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import json
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Ensure Windows UTF-8 stdout safety
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Win32 Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001

VK_CODES: Dict[str, int] = {
    "SPACE": 0x20,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "ENTER": 0x0D,
    "TAB": 0x09,
    "C": ord("C"),
    "H": ord("H"),
    "S": ord("S"),
    "A": ord("A"),
    "Z": ord("Z"),
}
for i in range(1, 13):
    VK_CODES[f"F{i}"] = 0x70 + i - 1

EMERGENCY_LOCK_FILE = Path(__file__).resolve().parent / "emergency_stop.lock"


@dataclass
class HotkeyBinding:
    id: int
    action: str
    name: str
    modifiers: int
    vk: int
    description: str


def trigger_emergency_stop() -> str:
    """Sets the emergency stop lock file and signals all running agents to abort."""
    EMERGENCY_LOCK_FILE.write_text(json.dumps({
        "timestamp": time.time(),
        "reason": "Emergency Panic Stop triggered by user hotkey (Ctrl+Esc)",
        "source": "desktop_shell"
    }), encoding="utf-8")
    logger.warning("🚨 EMERGENCY PANIC STOP ENGAGED!")
    return "EMERGENCY_STOP_ENGAGED"


def clear_emergency_stop():
    """Clears emergency stop lock file."""
    if EMERGENCY_LOCK_FILE.exists():
        try:
            EMERGENCY_LOCK_FILE.unlink()
        except Exception:
            pass


def is_emergency_stopped() -> bool:
    """Checks whether the emergency stop flag is active."""
    return EMERGENCY_LOCK_FILE.exists()


def get_clipboard_text() -> str:
    """Safely extracts current text from the Windows clipboard."""
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(0):
            return ""
        try:
            h_data = user32.GetClipboardData(13)  # CF_UNICODETEXT = 13
            if not h_data:
                return ""
            p_data = kernel32.GlobalLock(h_data)
            if not p_data:
                return ""
            try:
                return ctypes.c_wchar_p(p_data).value or ""
            finally:
                kernel32.GlobalUnlock(h_data)
        finally:
            user32.CloseClipboard()
    except Exception:
        return ""


def set_clipboard_text(text: str):
    """Sets text on Windows clipboard."""
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(0):
            return
        try:
            user32.EmptyClipboard()
            # GMEM_MOVEABLE = 0x0002
            data_bytes = (text + "\0").encode("utf-16le")
            h_glob = kernel32.GlobalAlloc(0x0002, len(data_bytes))
            if h_glob:
                p_glob = kernel32.GlobalLock(h_glob)
                ctypes.memmove(p_glob, data_bytes, len(data_bytes))
                kernel32.GlobalUnlock(h_glob)
                user32.SetClipboardData(13, h_glob)
        finally:
            user32.CloseClipboard()
    except Exception:
        pass


def grab_selected_text() -> str:
    """
    Sends simulated Ctrl+C to copy highlighted text anywhere in Windows,
    reads the clipboard, and restores original clipboard text.
    """
    prev = get_clipboard_text()
    user32 = ctypes.windll.user32

    # Simulate Ctrl+C
    user32.keybd_event(0x11, 0, 0, 0)          # Ctrl down
    user32.keybd_event(ord("C"), 0, 0, 0)       # C down
    user32.keybd_event(ord("C"), 0, 2, 0)       # C up
    user32.keybd_event(0x11, 0, 2, 0)          # Ctrl up
    time.sleep(0.15)

    selected = get_clipboard_text()
    # Restore previous clipboard if different
    if prev and prev != selected:
        set_clipboard_text(prev)

    return selected.strip()


def summon_hermes_dashboard():
    """Summons or focuses Hermes Dashboard in the default web browser."""
    url = "http://127.0.0.1:9119"
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception as exc:
        logger.warning(f"Could not open dashboard URL: {exc}")


def handle_selected_text_assist():
    """Handles Selected-Text Assist hotkey (Ctrl+Alt+C)."""
    text = grab_selected_text()
    if not text:
        logger.info("Selected-text assist triggered, but no text was selected.")
        return

    logger.info(f"Selected-text assist captured ({len(text)} chars): {text[:60]}...")
    # Send to Hermes company dashboard or log
    log_file = Path(__file__).resolve().parent / "employee_logs" / "OPERATOR.json"
    if log_file.parent.exists():
        try:
            entry = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "task": f"Selected-Text Assist: '{text[:120]}'",
                "response": f"Captured {len(text)} characters for assist.",
                "model": "desktop_shell",
                "latency_ms": 12
            }
            # Append entry to log safely
            existing = []
            if log_file.exists():
                try:
                    existing = json.loads(log_file.read_text(encoding="utf-8"))
                except Exception:
                    existing = []
            existing.insert(0, entry)
            log_file.write_text(json.dumps(existing[:100], indent=2), encoding="utf-8")
        except Exception:
            pass

    # Open dashboard with query if appropriate
    summon_hermes_dashboard()


class HermesTrayApp:
    """System Tray Icon and Win32 Global Hotkey Daemon."""

    def __init__(self):
        self._running = False
        self._tray_icon = None
        self._hotkey_thread: Optional[threading.Thread] = None

        # Configured Hotkey Bindings
        self.bindings = [
            HotkeyBinding(
                id=101,
                action="summon",
                name="Global Summon",
                modifiers=MOD_CONTROL | MOD_ALT,
                vk=VK_CODES["SPACE"],
                description="Ctrl+Alt+Space: Summon Hermes Dashboard"
            ),
            HotkeyBinding(
                id=102,
                action="assist_selection",
                name="Selected-Text Assist",
                modifiers=MOD_CONTROL | MOD_ALT,
                vk=VK_CODES["C"],
                description="Ctrl+Alt+C: Analyze highlighted text"
            ),
            HotkeyBinding(
                id=103,
                action="emergency_stop",
                name="Emergency Panic Stop",
                modifiers=MOD_CONTROL,
                vk=VK_CODES["ESC"],
                description="Ctrl+Esc: Instantly abort all running agent actions"
            ),
        ]

    def _create_tray_image(self):
        """Generates a clean 64x64 Hermes emblem icon using PIL."""
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Circular base with indigo/purple gradient tone
            draw.ellipse((4, 4, 60, 60), fill=(99, 102, 241, 255), outline=(129, 140, 248, 255), width=2)
            # Hermes winged stylized "H"
            draw.line((22, 20, 22, 44), fill=(255, 255, 255, 255), width=4)
            draw.line((42, 20, 42, 44), fill=(255, 255, 255, 255), width=4)
            draw.line((22, 32, 42, 32), fill=(255, 255, 255, 255), width=4)
            # Wing accent
            draw.polygon([(42, 20), (52, 14), (46, 26)], fill=(244, 114, 182, 255))
            return img
        except Exception:
            from PIL import Image
            return Image.new("RGB", (64, 64), color=(99, 102, 241))

    def _run_hotkey_loop(self):
        """Win32 RegisterHotKey message pump thread."""
        user32 = ctypes.windll.user32
        registered: List[int] = []

        for b in self.bindings:
            res = user32.RegisterHotKey(0, b.id, b.modifiers, b.vk)
            if res != 0:
                registered.append(b.id)
                logger.info(f"Registered global hotkey {b.description}")
            else:
                logger.warning(f"Could not register hotkey {b.description} (may be reserved)")

        msg = ctypes.wintypes.MSG()
        while self._running:
            # Peek and dispatch messages
            if user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, PM_REMOVE):
                if msg.message == WM_HOTKEY:
                    hotkey_id = msg.wParam
                    self._dispatch_hotkey(hotkey_id)
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(0.02)

        # Unregister upon exit
        for hid in registered:
            user32.UnregisterHotKey(0, hid)

    def _dispatch_hotkey(self, hotkey_id: int):
        """Dispatches an action when a hotkey is pressed."""
        for b in self.bindings:
            if b.id == hotkey_id:
                logger.info(f"Hotkey fired: {b.name} ({b.action})")
                if b.action == "summon":
                    summon_hermes_dashboard()
                elif b.action == "assist_selection":
                    handle_selected_text_assist()
                elif b.action == "emergency_stop":
                    trigger_emergency_stop()
                break

    def start(self, with_tray: bool = True):
        """Starts the hotkey message loop and optional system tray icon."""
        self._running = True
        self._hotkey_thread = threading.Thread(target=self._run_hotkey_loop, daemon=True, name="hermes-hotkeys")
        self._hotkey_thread.start()

        if with_tray:
            try:
                import pystray
                from window_services import get_display_monitors

                monitors = get_display_monitors()
                mon_count = len(monitors)

                def on_open_dashboard(icon, item):
                    summon_hermes_dashboard()

                def on_open_roster(icon, item):
                    import webbrowser
                    webbrowser.open("http://localhost:8000")

                def on_assist(icon, item):
                    handle_selected_text_assist()

                def on_stop(icon, item):
                    trigger_emergency_stop()

                def on_exit(icon, item):
                    self.stop()
                    icon.stop()

                menu = pystray.Menu(
                    pystray.MenuItem("⚡ Open Hermes Dashboard (9119)", on_open_dashboard, default=True),
                    pystray.MenuItem("👥 Open Company Roster (8000)", on_open_roster),
                    pystray.MenuItem("📋 Selected-Text Assist (Ctrl+Alt+C)", on_assist),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("🚨 EMERGENCY PANIC STOP (Ctrl+Esc)", on_stop),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem(f"🖥️ Displays: {mon_count} Active", None, enabled=False),
                    pystray.MenuItem("❌ Exit Hermes Shell", on_exit)
                )

                self._tray_icon = pystray.Icon(
                    "hermes_shell",
                    self._create_tray_image(),
                    "Hermes Agent - Autonomous Assistant",
                    menu=menu
                )
                logger.info("Starting Hermes System Tray icon...")
                self._tray_icon.run()
            except Exception as exc:
                logger.warning(f"pystray unavailable or failed: {exc}. Running headless hotkey daemon.")
                while self._running:
                    time.sleep(0.5)
        else:
            while self._running:
                time.sleep(0.5)

    def stop(self):
        """Stops tray icon and message loop."""
        self._running = False
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Hermes Desktop Shell & Tray Daemon")
    parser.add_argument("--start", action="store_true", help="Start the desktop shell daemon and tray")
    parser.add_argument("--no-tray", action="store_true", help="Start hotkeys without tray icon")
    parser.add_argument("--emergency-stop", action="store_true", help="Trigger emergency panic stop")
    parser.add_argument("--clear-stop", action="store_true", help="Clear emergency panic stop")
    parser.add_argument("--status", action="store_true", help="Check emergency stop status")

    args = parser.parse_args()

    if args.emergency_stop:
        trigger_emergency_stop()
        print("Emergency stop triggered.")
        sys.exit(0)

    if args.clear_stop:
        clear_emergency_stop()
        print("Emergency stop cleared.")
        sys.exit(0)

    if args.status:
        stopped = is_emergency_stopped()
        print(f"Emergency stop active: {stopped}")
        sys.exit(0)

    app = HermesTrayApp()
    try:
        app.start(with_tray=not args.no_tray)
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()
