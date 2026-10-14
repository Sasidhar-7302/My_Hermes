# -*- coding: utf-8 -*-
"""
Media & System Volume Control Module for Hermes
Provides instant Windows system volume and media playback control via native Win32 API.
Zero external dependencies, sub-millisecond execution.
"""

from __future__ import annotations

import ctypes
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Windows Virtual Key Codes for Multimedia
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def _send_vk(vk_code: int) -> bool:
    """Sends a single virtual keypress down and up."""
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        return True
    except Exception as exc:
        logger.error(f"Failed to send VK {vk_code}: {exc}")
        return False


def toggle_mute() -> Dict[str, Any]:
    """Toggles master audio mute state."""
    success = _send_vk(VK_VOLUME_MUTE)
    return {"status": "success" if success else "error", "action": "toggle_mute"}


def volume_up(steps: int = 2) -> Dict[str, Any]:
    """Increases system volume by the specified number of steps (default 2 steps = ~4%)."""
    steps = max(1, min(steps, 50))
    for _ in range(steps):
        _send_vk(VK_VOLUME_UP)
    return {"status": "success", "action": "volume_up", "steps": steps}


def volume_down(steps: int = 2) -> Dict[str, Any]:
    """Decreases system volume by the specified number of steps (default 2 steps = ~4%)."""
    steps = max(1, min(steps, 50))
    for _ in range(steps):
        _send_vk(VK_VOLUME_DOWN)
    return {"status": "success", "action": "volume_down", "steps": steps}


def media_play_pause() -> Dict[str, Any]:
    """Toggles play/pause on the active media player (Spotify, YouTube, VLC, etc.)."""
    success = _send_vk(VK_MEDIA_PLAY_PAUSE)
    return {"status": "success" if success else "error", "action": "play_pause"}


def media_next() -> Dict[str, Any]:
    """Skips to the next track."""
    success = _send_vk(VK_MEDIA_NEXT_TRACK)
    return {"status": "success" if success else "error", "action": "next_track"}


def media_previous() -> Dict[str, Any]:
    """Returns to the previous track."""
    success = _send_vk(VK_MEDIA_PREV_TRACK)
    return {"status": "success" if success else "error", "action": "previous_track"}


def media_stop() -> Dict[str, Any]:
    """Stops media playback."""
    success = _send_vk(VK_MEDIA_STOP)
    return {"status": "success" if success else "error", "action": "stop"}


def execute_media_command(command: str) -> Dict[str, Any]:
    """Dispatches natural language media and volume commands."""
    cmd = command.lower().strip()
    if any(k in cmd for k in ["unmute", "mute"]):
        return toggle_mute()
    if any(k in cmd for k in ["volume up", "louder", "turn it up", "increase volume"]):
        return volume_up(steps=4)
    if any(k in cmd for k in ["volume down", "quieter", "lower volume", "decrease volume", "turn it down"]):
        return volume_down(steps=4)
    if any(k in cmd for k in ["next track", "next song", "skip song", "skip track"]):
        return media_next()
    if any(k in cmd for k in ["previous track", "previous song", "prev track", "prev song"]):
        return media_previous()
    if any(k in cmd for k in ["pause", "resume", "play", "play/pause"]):
        return media_play_pause()
    if "stop music" in cmd or "stop playback" in cmd:
        return media_stop()

    return {"status": "unrecognized", "message": f"Unrecognized media command: {command}"}
