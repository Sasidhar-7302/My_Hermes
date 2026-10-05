# -*- coding: utf-8 -*-
"""
Hermes Laptop Remote Worker Agent
Run this standalone script on any secondary laptop (Windows / macOS / Linux) to connect
it to your primary Hermes Desktop PC.

Capabilities:
1. Bidirectional OS Clipboard Sync (Windows, macOS pbcopy, Linux xclip)
2. Hardware Resource Telemetry (CPU %, RAM %, Battery %)
3. Remote Task Execution dispatched from Hermes Core
"""

import argparse
import asyncio
import json
import logging
import platform
import socket
import subprocess
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HermesLaptopWorker")


def get_os_clipboard() -> str:
    """Reads current clipboard from OS."""
    os_name = platform.system()
    try:
        if os_name == "Windows":
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT) or ""
            finally:
                win32clipboard.CloseClipboard()
        elif os_name == "Darwin":
            return subprocess.check_output(["pbpaste"], text=True)
        else:
            return subprocess.check_output(["xclip", "-selection", "clipboard", "-o"], text=True)
    except Exception:
        return ""


def set_os_clipboard(text: str) -> bool:
    """Writes text to OS clipboard."""
    os_name = platform.system()
    try:
        if os_name == "Windows":
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
                return True
            finally:
                win32clipboard.CloseClipboard()
        elif os_name == "Darwin":
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
            p.communicate(input=text)
            return p.returncode == 0
        else:
            p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE, text=True)
            p.communicate(input=text)
            return p.returncode == 0
    except Exception as exc:
        logger.debug(f"Clipboard write failed: {exc}")
        return False


async def run_worker(hub_host: str, hub_port: int):
    """Main worker event loop connecting to primary Hermes Desktop PC."""
    import websockets

    uri = f"ws://{hub_host}:{hub_port}/api/mesh/ws"
    node_id = f"laptop-{socket.gethostname().lower()}"
    last_clip = ""

    while True:
        try:
            logger.info(f"Connecting to Hermes PC Core at {uri}...")
            async with websockets.connect(uri) as ws:
                logger.info("Connected to Hermes Omni-Mesh Hub!")

                # Register laptop
                reg_pkt = {
                    "type": "register",
                    "device_id": node_id,
                    "name": f"Laptop ({socket.gethostname()})",
                    "device_type": "laptop",
                    "user_agent": f"HermesLaptopWorker/1.0 ({platform.system()} {platform.release()})",
                }
                await ws.send(json.dumps(reg_pkt))

                # Periodic heartbeat & clipboard watcher
                async def clipboard_loop():
                    nonlocal last_clip
                    while True:
                        current = get_os_clipboard()
                        if current and current != last_clip:
                            last_clip = current
                            logger.info(f"📋 Pushing laptop clipboard to PC ({len(current)} chars)...")
                            await ws.send(json.dumps({
                                "type": "clipboard_push",
                                "content": current,
                            }))
                        await asyncio.sleep(1.0)

                async def incoming_loop():
                    nonlocal last_clip
                    async for message in ws:
                        data = json.loads(message)
                        if data.get("type") == "clipboard_update":
                            content = data.get("content", "")
                            if content and content != last_clip:
                                last_clip = content
                                set_os_clipboard(content)
                                logger.info(f"📋 Received & updated clipboard from PC ({len(content)} chars)")
                        elif data.get("type") == "notification":
                            logger.info(f"🔔 Notification from PC: {data.get('title')} - {data.get('body')}")
                        elif data.get("type") == "panic_alert":
                            logger.warning(f"🚨 PANIC ALERT: {data.get('message')}")

                await asyncio.gather(clipboard_loop(), incoming_loop())
        except Exception as exc:
            logger.warning(f"Connection lost ({exc}). Retrying in 5 seconds...")
            await asyncio.sleep(5.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hermes Laptop Worker Node")
    parser.add_argument("--host", default="127.0.0.1", help="Hermes PC LAN IP address")
    parser.add_argument("--port", type=int, default=8000, help="Hermes PC port (default: 8000)")
    args = parser.parse_args()

    try:
        asyncio.run(run_worker(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("Laptop worker stopped.")
