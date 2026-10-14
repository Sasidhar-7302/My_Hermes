# -*- coding: utf-8 -*-
"""
Hermes Desktop & Personal Agent MCP Server
Provides standard Model Context Protocol (MCP) stdio access to native Windows automation:
Window Management, Computer Control, Media Volume, Smart Shutdown, Deal Finder,
RPA Macro Studio, Screen Vision, Emergency Stop, and Multi-Device OmniMesh Companion.
"""

from __future__ import annotations

import os
import sys
import json
import logging
from typing import Any, Dict, List, Optional

# Ensure local_model_lab is importable
_cur_dir = os.path.dirname(os.path.abspath(__file__))
if _cur_dir not in sys.path:
    sys.path.insert(0, _cur_dir)

_app_dir = os.path.dirname(_cur_dir)
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("hermes_desktop_mcp")

mcp = FastMCP("hermes-desktop")


# ── 1. Computer Control & Window Services ───────────────────────────────────

@mcp.tool()
def execute_computer_task(task: str) -> str:
    """Executes a natural language desktop or computer control task with hardline security guardrails."""
    try:
        from computer_control import execute_computer_task as _exec
        res = _exec(task)
        return json.dumps(res, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool()
def list_desktop_windows() -> str:
    """Lists all active, visible top-level windows with title, HWND, geometry, and monitor index."""
    try:
        from window_services import list_active_windows
        windows = list_active_windows()
        return json.dumps({"status": "success", "count": len(windows), "windows": windows[:30]}, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool()
def focus_window(title_or_hwnd: str) -> str:
    """Brings a window matching title_or_hwnd to the foreground."""
    try:
        from window_services import focus_window as _focus
        ok = _focus(title_or_hwnd)
        return json.dumps({"status": "success" if ok else "not_found", "target": title_or_hwnd})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool()
def snap_window(title_or_hwnd: str, position: str) -> str:
    """Snaps a target window to 'left', 'right', 'top', 'bottom', 'maximize', 'restore', or 'center'."""
    try:
        from window_services import snap_window as _snap
        res = _snap(title_or_hwnd, position)
        return json.dumps(res, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool()
def move_window_to_monitor(title_or_hwnd: str, monitor_id: int) -> str:
    """Moves a window to monitor 0, 1, etc."""
    try:
        from window_services import move_window_to_monitor as _move
        res = _move(title_or_hwnd, monitor_id)
        return json.dumps(res, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


# ── 2. Media & Volume Control ───────────────────────────────────────────────

@mcp.tool()
def control_media_and_volume(action: str, steps: int = 4) -> str:
    """
    Controls Windows system volume and media playback.
    Actions: 'mute', 'volume_up', 'volume_down', 'play_pause', 'next', 'previous', 'stop'.
    """
    try:
        from media_control import (
            toggle_mute, volume_up, volume_down, media_play_pause,
            media_next, media_previous, media_stop
        )
        act = action.lower().strip()
        if "mute" in act:
            res = toggle_mute()
        elif "up" in act or "loud" in act:
            res = volume_up(steps=steps)
        elif "down" in act or "quiet" in act:
            res = volume_down(steps=steps)
        elif "play" in act or "pause" in act:
            res = media_play_pause()
        elif "next" in act or "skip" in act:
            res = media_next()
        elif "prev" in act:
            res = media_previous()
        elif "stop" in act:
            res = media_stop()
        else:
            res = {"status": "error", "message": f"Unknown media action: {action}"}
        return json.dumps(res, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


# ── 3. Smart Shutdown & Power Management ───────────────────────────────────

@mcp.tool()
def manage_smart_shutdown(action: str = "status", timer_minutes: int = 30, power_action: str = "shutdown") -> str:
    """
    Manages intelligent network-idle and timer power actions.
    Actions: 'status', 'start_timer', 'start_idle', 'cancel'.
    power_action: 'shutdown', 'sleep', 'hibernate'.
    """
    try:
        from smart_shutdown import get_smart_shutdown_monitor, SmartShutdownConfig
        mon = get_smart_shutdown_monitor()
        act = action.lower().strip()
        if act == "status":
            return json.dumps(mon.snapshot(), indent=2)
        elif act in ("start_timer", "timer"):
            cfg = SmartShutdownConfig(action=power_action, max_wait_seconds=timer_minutes * 60)
            ok, msg = mon.start(cfg)
            return json.dumps({"status": "success" if ok else "error", "message": msg}, indent=2)
        elif act in ("start_idle", "idle"):
            cfg = SmartShutdownConfig(action=power_action, network_threshold_kbps=50.0, idle_duration_seconds=120)
            ok, msg = mon.start(cfg)
            return json.dumps({"status": "success" if ok else "error", "message": msg}, indent=2)
        elif act == "cancel":
            ok, msg = mon.cancel()
            return json.dumps({"status": "success" if ok else "error", "message": msg}, indent=2)
        return json.dumps({"status": "error", "message": f"Unknown action: {action}"})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


# ── 4. Deal Finder & Price Watchlist ───────────────────────────────────────

@mcp.tool()
def search_product_deals(query: str, max_results: int = 5) -> str:
    """Searches top product deals across Amazon, BestBuy, Newegg, Walmart, B&H, and Micro Center."""
    try:
        from deal_finder import search_deals
        listings = search_deals(query, max_per_retailer=max_results)
        return json.dumps({
            "status": "success",
            "query": query,
            "count": len(listings),
            "deals": [d.to_dict() for d in listings[:15]]
        }, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool()
def manage_deal_watchlist(action: str = "list", title: str = "", target_price: float = 0.0, retailer: str = "any") -> str:
    """
    Manages Hermes price watches.
    Actions: 'list', 'add', 'check'.
    """
    try:
        from deal_finder import get_deal_watch_store
        store = get_deal_watch_store()
        act = action.lower().strip()
        if act == "list":
            watches = [w.to_dict() for w in store.list_watches()]
            return json.dumps({"status": "success", "watches": watches}, indent=2)
        elif act == "add":
            if not title or target_price <= 0:
                return json.dumps({"status": "error", "message": "title and target_price > 0 required"})
            w = store.add_watch(title, target_price, retailer=retailer)
            return json.dumps({"status": "success", "watch": w.to_dict()}, indent=2)
        return json.dumps({"status": "error", "message": f"Unknown action: {action}"})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


# ── 5. RPA Macro Studio ─────────────────────────────────────────────────────

@mcp.tool()
def manage_rpa_macro(action: str = "list", name: str = "default_macro", speed: float = 1.0) -> str:
    """
    Manages desktop RPA macro recording and replay.
    Actions: 'record_start', 'record_stop', 'replay', 'list'.
    """
    try:
        from rpa_recorder import get_rpa_recorder
        rpa = get_rpa_recorder()
        act = action.lower().strip()
        if act == "list":
            return json.dumps({"status": "success", "recordings": rpa.list_recordings()}, indent=2)
        elif act in ("record_start", "start"):
            res = rpa.start_recording(name)
            return json.dumps(res, indent=2)
        elif act in ("record_stop", "stop"):
            res = rpa.stop_recording(name)
            return json.dumps(res, indent=2)
        elif act == "replay":
            res = rpa.replay(name, speed=speed)
            return json.dumps(res, indent=2)
        return json.dumps({"status": "error", "message": f"Unknown action: {action}"})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


# ── 6. Screen Vision & UI Grounding ─────────────────────────────────────────

@mcp.tool()
def inspect_screen_vision(prompt: str = "Describe what is currently visible on my screen in 2-3 concise sentences.") -> str:
    """Captures the active desktop monitor and provides visual understanding using local or cloud vision."""
    try:
        from screen_vision import get_screen_vision
        desc = get_screen_vision().describe_screen(prompt)
        return json.dumps({"status": "success", "description": desc}, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


# ── 7. Global Emergency Stop ────────────────────────────────────────────────

@mcp.tool()
def emergency_stop(action: str = "status") -> str:
    """
    Global hardline emergency kill switch.
    Actions: 'trigger' (immediately halts all running agent desktop actions), 'clear', 'status'.
    """
    try:
        from shell_daemon import trigger_emergency_stop, clear_emergency_stop, is_emergency_stopped
        act = action.lower().strip()
        if act in ("trigger", "halt", "stop", "abort"):
            msg = trigger_emergency_stop()
            return json.dumps({"status": "EMERGENCY_STOP_ENGAGED", "message": msg}, indent=2)
        elif act == "clear":
            clear_emergency_stop()
            return json.dumps({"status": "EMERGENCY_STOP_CLEARED"})
        else:
            return json.dumps({"status": "success", "is_emergency_stopped": is_emergency_stopped()})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


# ── 8. Multi-Device Companion Relay ─────────────────────────────────────────

@mcp.tool()
def send_companion_notification(title: str, body: str, target: str = "all", priority: str = "normal") -> str:
    """
    Sends an instantaneous push notification and haptic pulse to companion devices.
    target: 'smartwatch', 'smartphone', 'laptop', 'all'.
    priority: 'low', 'normal', 'urgent'.
    """
    try:
        import urllib.request
        payload = json.dumps({
            "title": title,
            "body": body,
            "target": target,
            "priority": priority
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/mesh/notify",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return json.dumps({"status": "success", "relay": data}, indent=2)
    except Exception as exc:
        return json.dumps({"status": "local_logged", "message": f"Broadcast logged locally: {title} - {body}"})


if __name__ == "__main__":
    mcp.run()
