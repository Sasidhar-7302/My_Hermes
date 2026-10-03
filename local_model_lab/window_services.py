# -*- coding: utf-8 -*-
"""
Window Services & Multi-Monitor Management for Hermes Agent
Provides display monitor enumeration, clean window filtering, snapping, and cross-monitor movement.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Ensure Windows UTF-8 stdout safety
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import win32api
    import win32con
    import win32gui
    import win32process
    import win32service
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logger.warning("pywin32 not available. Multi-monitor and window services will be limited.")


# System windows to filter out (invisible background windows, system overlays, shells)
SYSTEM_WINDOWS_TO_HIDE = {
    "default ime",
    "msctfime ui",
    "nvidia geforce overlay",
    "program manager",
    "windows input experience",
    "windows shell experience host",
    "microsoft text input application",
    "systray",
    "start",
    "taskbar",
    "battery flyout",
    "volume control",
    "network flyout",
    "action center",
    "windows setup",
    "",  # Empty titles
}


@dataclass
class MonitorInfo:
    """Information about a physical display monitor."""
    id: int
    device: str
    rect: Tuple[int, int, int, int]        # left, top, right, bottom
    work_area: Tuple[int, int, int, int]   # left, top, right, bottom (excluding taskbar)
    is_primary: bool

    @property
    def x(self) -> int:
        return self.work_area[0]

    @property
    def y(self) -> int:
        return self.work_area[1]

    @property
    def width(self) -> int:
        return self.work_area[2] - self.work_area[0]

    @property
    def height(self) -> int:
        return self.work_area[3] - self.work_area[1]

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def contains_point(self, px: int, py: int) -> bool:
        return (self.rect[0] <= px < self.rect[2] and self.rect[1] <= py < self.rect[3])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "device": self.device,
            "width": self.width,
            "height": self.height,
            "work_area": list(self.work_area),
            "is_primary": self.is_primary,
            "center": list(self.center),
        }


def ensure_interactive_desktop():
    """Attaches process to interactive desktop WinSta0\\default."""
    if not HAS_WIN32:
        return
    try:
        hwinsta = win32service.OpenWindowStation('WinSta0', False, win32con.GENERIC_ALL)
        hwinsta.SetProcessWindowStation()
        hdesk = win32service.OpenDesktop('default', 0, False, win32con.GENERIC_ALL)
        hdesk.SetThreadDesktop()
    except Exception:
        pass


def get_display_monitors() -> List[MonitorInfo]:
    """Enumerates all active physical and virtual display monitors."""
    ensure_interactive_desktop()
    monitors: List[MonitorInfo] = []

    if not HAS_WIN32:
        try:
            import ctypes
            sw = ctypes.windll.user32.GetSystemMetrics(0) or 1920
            sh = ctypes.windll.user32.GetSystemMetrics(1) or 1080
            return [MonitorInfo(id=1, device="Primary", rect=(0, 0, sw, sh), work_area=(0, 0, sw, sh - 40), is_primary=True)]
        except Exception:
            return []

    try:
        raw_monitors = win32api.EnumDisplayMonitors()
        for idx, (hmon, _, _) in enumerate(raw_monitors, start=1):
            info = win32api.GetMonitorInfo(hmon)
            is_pri = bool(info.get("Flags", 0) & win32con.MONITORINFOF_PRIMARY)
            monitors.append(MonitorInfo(
                id=idx,
                device=str(info.get("Device", f"Display{idx}")),
                rect=tuple(info.get("Monitor", (0, 0, 1920, 1080))),
                work_area=tuple(info.get("Work", (0, 0, 1920, 1040))),
                is_primary=is_pri
            ))
    except Exception as exc:
        logger.warning(f"Error enumerating monitors: {exc}")

    if not monitors:
        # Fallback to single primary monitor
        sw = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        sh = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        monitors.append(MonitorInfo(id=1, device="Default", rect=(0, 0, sw, sh), work_area=(0, 0, sw, sh - 40), is_primary=True))

    return monitors


def get_monitor_for_window(hwnd: int) -> Optional[MonitorInfo]:
    """Determines which monitor contains the given window."""
    monitors = get_display_monitors()
    if not HAS_WIN32:
        return monitors[0] if monitors else None

    try:
        rect = win32gui.GetWindowRect(hwnd)
        center_x = (rect[0] + rect[2]) // 2
        center_y = (rect[1] + rect[3]) // 2

        for m in monitors:
            if m.contains_point(center_x, center_y):
                return m
    except Exception:
        pass

    return monitors[0] if monitors else None


def list_active_windows() -> List[Dict[str, Any]]:
    """
    Returns a clean list of real, visible application windows with their titles,
    handles, bounding rectangles, and assigned monitor IDs.
    Filters out background system noise and invisible windows.
    """
    ensure_interactive_desktop()
    results: List[Dict[str, Any]] = []
    if not HAS_WIN32:
        return []

    def _process_hwnd(hwnd):
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return

        title_lower = title.lower()
        if title_lower in SYSTEM_WINDOWS_TO_HIDE:
            return
        if len(title) < 2:
            return

        try:
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]

            # Filter out zero-size or off-screen minimized windows
            if w <= 50 or h <= 50:
                return
            if rect[0] <= -30000 or rect[1] <= -30000:
                return

            # Check style: must not be tool windows without taskbar presence
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

            # Skip child windows
            if style & win32con.WS_CHILD:
                return
            # Skip ToolWindow unless AppWindow is explicitly set
            if (ex_style & win32con.WS_EX_TOOLWINDOW) and not (ex_style & win32con.WS_EX_APPWINDOW):
                return

            mon = get_monitor_for_window(hwnd)
            results.append({
                "hwnd": hwnd,
                "title": title,
                "rect": (rect[0], rect[1], w, h),
                "monitor_id": mon.id if mon else 1,
                "is_active": (win32gui.GetForegroundWindow() == hwnd),
            })
        except Exception:
            pass

    try:
        hdesk = win32service.OpenDesktop('default', 0, False, win32con.GENERIC_ALL)
        def _desk_cb(hwnd, _):
            _process_hwnd(hwnd)
        win32gui.EnumDesktopWindows(hdesk, _desk_cb, None)
    except Exception:
        pass

    if not results:
        try:
            def _enum_cb(hwnd, _):
                _process_hwnd(hwnd)
            win32gui.EnumWindows(_enum_cb, None)
        except Exception:
            pass

    return results


def resolve_window_hwnd(target: Union[str, int]) -> Optional[int]:
    """Resolves a window title query, partial string, or HWND into an integer HWND."""
    if isinstance(target, int):
        return target

    windows = list_active_windows()
    query = str(target).strip().lower()

    # 1. Exact match
    for w in windows:
        if w["title"].lower() == query:
            return w["hwnd"]

    # 2. Substring match
    for w in windows:
        if query in w["title"].lower():
            return w["hwnd"]

    # 3. Word-level match
    words = [wd for wd in query.split() if len(wd) > 2]
    if words:
        for w in windows:
            t_low = w["title"].lower()
            if any(wd in t_low for wd in words):
                return w["hwnd"]

    return None


def focus_window(target: Union[str, int]) -> bool:
    """Brings the target window to the foreground and focuses it."""
    hwnd = resolve_window_hwnd(target)
    if not hwnd or not HAS_WIN32:
        return False
    try:
        ensure_interactive_desktop()
        # Restore if minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception as exc:
        logger.debug(f"Failed to focus window: {exc}")
        return False


def snap_window(target: Union[str, int], position: str) -> Dict[str, Any]:
    """
    Snaps window to a specific region on its current monitor.
    Positions: 'left', 'right', 'top', 'bottom', 'maximize', 'minimize', 'center'.
    """
    hwnd = resolve_window_hwnd(target)
    if not hwnd or not HAS_WIN32:
        return {"status": "error", "message": f"Window not found: {target}"}

    if not win32gui.IsWindow(hwnd):
        return {"status": "error", "message": f"Window handle invalid or closed: {hwnd}"}

    mon = get_monitor_for_window(hwnd) or get_display_monitors()[0]
    pos = position.strip().lower()

    wx, wy, ww, wh = mon.x, mon.y, mon.width, mon.height

    try:
        ensure_interactive_desktop()
        # Restore first if maximized or iconic
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        if pos in ("maximize", "max"):
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return {"status": "success", "action": "maximize", "hwnd": hwnd, "monitor": mon.id}

        if pos in ("minimize", "min"):
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return {"status": "success", "action": "minimize", "hwnd": hwnd, "monitor": mon.id}

        if pos in ("left", "left_half"):
            target_rect = (wx, wy, ww // 2, wh)
        elif pos in ("right", "right_half"):
            target_rect = (wx + ww // 2, wy, ww // 2, wh)
        elif pos in ("top", "top_half"):
            target_rect = (wx, wy, ww, wh // 2)
        elif pos in ("bottom", "bottom_half"):
            target_rect = (wx, wy + wh // 2, ww, wh // 2)
        elif pos in ("center", "centered"):
            cw = int(ww * 0.75)
            ch = int(wh * 0.75)
            target_rect = (wx + (ww - cw) // 2, wy + (wh - ch) // 2, cw, ch)
        else:
            return {"status": "error", "message": f"Unknown snap position: {position}"}

        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            target_rect[0], target_rect[1], target_rect[2], target_rect[3],
            win32con.SWP_SHOWWINDOW
        )
        win32gui.SetForegroundWindow(hwnd)

        return {
            "status": "success",
            "action": f"snap_{pos}",
            "hwnd": hwnd,
            "monitor": mon.id,
            "target_rect": list(target_rect)
        }
    except Exception as exc:
        return {"status": "error", "message": f"Snap window failed: {exc}"}


def move_window_to_monitor(target: Union[str, int], monitor_id: int) -> Dict[str, Any]:
    """
    Moves the target window to another display monitor (e.g. Monitor 1 or Monitor 2).
    """
    hwnd = resolve_window_hwnd(target)
    if not hwnd or not HAS_WIN32:
        return {"status": "error", "message": f"Window not found: {target}"}

    if not win32gui.IsWindow(hwnd):
        return {"status": "error", "message": f"Window handle invalid or closed: {hwnd}"}

    monitors = get_display_monitors()
    target_mon = None
    for m in monitors:
        if m.id == monitor_id:
            target_mon = m
            break

    if not target_mon:
        return {
            "status": "error",
            "message": f"Monitor {monitor_id} not found. Available monitors: {[m.id for m in monitors]}"
        }

    try:
        ensure_interactive_desktop()
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # Retrieve current window size
        rect = win32gui.GetWindowRect(hwnd)
        curr_w = min(rect[2] - rect[0], target_mon.width)
        curr_h = min(rect[3] - rect[1], target_mon.height)

        # Place centered in the target monitor work area
        new_x = target_mon.x + (target_mon.width - curr_w) // 2
        new_y = target_mon.y + (target_mon.height - curr_h) // 2

        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            new_x, new_y, curr_w, curr_h,
            win32con.SWP_SHOWWINDOW
        )
        win32gui.SetForegroundWindow(hwnd)

        return {
            "status": "success",
            "action": f"move_to_monitor_{monitor_id}",
            "hwnd": hwnd,
            "monitor": monitor_id,
            "target_rect": [new_x, new_y, curr_w, curr_h]
        }
    except Exception as exc:
        return {"status": "error", "message": f"Move to monitor failed: {exc}"}
