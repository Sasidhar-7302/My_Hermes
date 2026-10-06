# -*- coding: utf-8 -*-
"""
Hermes Laptop Remote Worker Agent
Run this standalone script on any secondary laptop (Windows / macOS / Linux) to connect
it to your primary Hermes Desktop PC.

Capabilities:
1. Bidirectional OS Clipboard Sync with Stale-Overwrite Protection
2. Hardware Resource Telemetry (CPU %, RAM %, Battery %)
3. Token-based Authentication
4. Remote Task Execution dispatched from Hermes Core
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


def get_system_telemetry() -> dict:
    """Collects CPU, RAM, and Battery statistics if psutil is available."""
    data = {"cpu": 0.0, "ram": 0.0, "battery": None, "is_charging": None}
    try:
        import psutil
        data["cpu"] = psutil.cpu_percent(interval=None)
        data["ram"] = psutil.virtual_memory().percent
        batt = psutil.sensors_battery()
        if batt:
            data["battery"] = int(batt.percent)
            data["is_charging"] = batt.power_plugged
    except Exception:
        pass
    return data


async def run_worker(hub_host: str, hub_port: int, token: str = "", pairing_code: str = ""):
    """Main worker event loop connecting to primary Hermes Desktop PC."""
    import websockets

    uri = f"ws://{hub_host}:{hub_port}/api/mesh/ws"
    node_id = f"laptop-{socket.gethostname().lower()}"
    last_clip = get_os_clipboard()  # Seed with current clipboard to prevent initial stale overwrite
    initial_sync_done = False

    while True:
        try:
            logger.info(f"Connecting to Hermes PC Core at {uri}...")
            async with websockets.connect(uri) as ws:
                logger.info("Connected to Hermes Omni-Mesh Hub!")

                # Register laptop with auth token
                reg_pkt = {
                    "type": "register",
                    "device_id": node_id,
                    "name": f"Laptop ({socket.gethostname()})",
                    "device_type": "laptop",
                    "user_agent": f"HermesLaptopWorker/2.0 ({platform.system()} {platform.release()})",
                    "token": token,
                    "pairing_code": pairing_code,
                }
                await ws.send(json.dumps(reg_pkt))

                # Periodic heartbeat & telemetry watcher
                async def telemetry_loop():
                    while True:
                        stats = get_system_telemetry()
                        await ws.send(json.dumps({
                            "type": "telemetry",
                            "cpu": stats["cpu"],
                            "ram": stats["ram"],
                            "battery": stats["battery"],
                            "is_charging": stats["is_charging"],
                        }))
                        await asyncio.sleep(5.0)

                # Periodic clipboard watcher
                async def clipboard_loop():
                    nonlocal last_clip, initial_sync_done
                    while True:
                        if initial_sync_done:
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
                    nonlocal last_clip, initial_sync_done
                    async for message in ws:
                        data = json.loads(message)
                        msg_type = data.get("type")

                        if msg_type == "welcome":
                            logger.info(f"Verified connection. Host IP: {data.get('host_ip')}")
                            if data.get("auth_token"):
                                logger.info(f"Received new device token: {data.get('auth_token')}")
                            # Initialize clipboard from PC
                            pc_clip = data.get("pc_clipboard", "")
                            if pc_clip:
                                last_clip = pc_clip
                                set_os_clipboard(pc_clip)
                                logger.info(f"📋 Seeded clipboard from PC ({len(pc_clip)} chars)")
                            initial_sync_done = True

                        elif msg_type == "auth_error":
                            logger.error(f"Authentication failed: {data.get('message')}")
                            await asyncio.sleep(10.0)
                            return

                        elif msg_type == "clipboard_update":
                            content = data.get("content", "")
                            if content and content != last_clip:
                                last_clip = content
                                set_os_clipboard(content)
                                logger.info(f"📋 Received & updated clipboard from PC ({len(content)} chars)")

                        elif msg_type == "notification":
                            logger.info(f"🔔 Notification: {data.get('title')} - {data.get('body')}")

                        elif msg_type == "panic_alert":
                            logger.warning(f"🚨 PANIC ALERT: {data.get('message')}")

                        elif msg_type == "remote_task":
                            # Execute dispatched command
                            cmd = data.get("command", "")
                            task_id = data.get("task_id", "")
                            logger.info(f"⚡ Executing remote task [{task_id}]: {cmd}")
                            try:
                                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                                out = proc.stdout or proc.stderr
                                code = proc.returncode
                            except Exception as exc:
                                out = str(exc)
                                code = 1

                            await ws.send(json.dumps({
                                "type": "task_result",
                                "task_id": task_id,
                                "returncode": code,
                                "output": out,
                            }))

                await asyncio.gather(telemetry_loop(), clipboard_loop(), incoming_loop())
        except Exception as exc:
            logger.warning(f"Connection lost ({exc}). Retrying in 5 seconds...")
            await asyncio.sleep(5.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hermes Laptop Worker Node")
    parser.add_argument("--host", default="127.0.0.1", help="Hermes PC LAN IP address")
    parser.add_argument("--port", type=int, default=8000, help="Hermes PC port (default: 8000)")
    parser.add_argument("--token", default="", help="Device authorization token")
    parser.add_argument("--pair", default="", help="One-time pairing code from PC QR code")
    args = parser.parse_args()

    try:
        asyncio.run(run_worker(args.host, args.port, token=args.token, pairing_code=args.pair))
    except KeyboardInterrupt:
        logger.info("Laptop worker stopped.")
