# -*- coding: utf-8 -*-
"""
Hermes Omni-Mesh Central Hub
Coordinates real-time WebSocket communication, state presence, and cross-device routing
across Smartwatch, Smartphone, Laptop, and Host PC.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import socket
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Native Win32 Clipboard integration
try:
    import win32clipboard
    import win32con
    HAS_WIN32_CLIP = True
except ImportError:
    HAS_WIN32_CLIP = False


def get_local_lan_ip() -> str:
    """Detects primary LAN IPv4 address of this host PC."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def read_pc_clipboard() -> str:
    """Reads plaintext content from the Windows system clipboard."""
    if not HAS_WIN32_CLIP:
        return ""
    try:
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                return str(data or "")
        finally:
            win32clipboard.CloseClipboard()
    except Exception as exc:
        logger.debug(f"Win32 clipboard read error: {exc}")
    return ""


def write_pc_clipboard(text: str) -> bool:
    """Writes plaintext content to the Windows system clipboard."""
    if not HAS_WIN32_CLIP:
        return False
    try:
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, str(text or ""))
            return True
        finally:
            win32clipboard.CloseClipboard()
    except Exception as exc:
        logger.warning(f"Win32 clipboard write error: {exc}")
        return False


def generate_qr_code_png_base64(url: str) -> str:
    """Generates high-contrast QR code PNG formatted as base64 data URI."""
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#10b981", back_color="#0a0d0e")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception as exc:
        logger.warning(f"QR code generation failed: {exc}")
        return ""


@dataclass
class MeshDevice:
    """Represents a connected or paired ecosystem device."""
    device_id: str
    name: str
    device_type: str  # "smartwatch", "smartphone", "laptop", "desktop"
    ip_address: str = ""
    user_agent: str = ""
    battery_level: Optional[int] = None
    is_charging: Optional[bool] = None
    last_seen: float = field(default_factory=time.time)
    connected: bool = True
    paired_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OmniMeshHub:
    """Central WebSocket routing bus and device state coordinator."""

    def __init__(self, port: int = 8000):
        self.devices: Dict[str, MeshDevice] = {}
        self.active_sockets: Dict[str, WebSocket] = {}
        self.last_synced_clipboard: str = ""
        self._lock = asyncio.Lock()
        self.port: int = port
        self.lan_ip: str = get_local_lan_ip()

        # Seed host desktop node
        self.devices["desktop-host"] = MeshDevice(
            device_id="desktop-host",
            name="Hermes Host PC",
            device_type="desktop",
            ip_address=self.lan_ip,
            connected=True,
            metadata={"os": sys.platform, "role": "Primary AI Core"},
        )

    def get_companion_url(self, device_type: Optional[str] = None) -> str:
        """Returns the local network companion URL for mobile/watch/laptop."""
        base = f"http://{self.lan_ip}:{self.port}"
        if device_type == "smartwatch":
            return f"{base}/companions/smartwatch"
        elif device_type == "smartphone":
            return f"{base}/companions/smartphone"
        elif device_type == "laptop":
            return f"{base}/companions/laptop"
        return f"{base}/companions/smartphone"

    def get_pairing_qr(self, device_type: Optional[str] = None) -> str:
        """Generates pairing QR code base64 PNG data URI."""
        return generate_qr_code_png_base64(self.get_companion_url(device_type))

    async def register_connection(
        self,
        websocket: WebSocket,
        device_id: str,
        name: str,
        device_type: str,
        client_ip: str,
        user_agent: str = "",
        battery: Optional[int] = None,
        is_charging: Optional[bool] = None,
        skip_accept: bool = False,
    ) -> MeshDevice:
        """Registers a newly connected companion device."""
        if not skip_accept:
            try:
                await websocket.accept()
            except Exception:
                pass

        normalized_type = device_type.lower()
        if normalized_type in ("watch", "smartwatch"):
            normalized_type = "smartwatch"
        elif normalized_type in ("phone", "smartphone", "mobile"):
            normalized_type = "smartphone"
        elif normalized_type in ("laptop", "tablet", "worker"):
            normalized_type = "laptop"
        else:
            normalized_type = "smartphone"

        dev = MeshDevice(
            device_id=device_id,
            name=name or f"Device-{device_id[:6]}",
            device_type=normalized_type,
            ip_address=client_ip,
            user_agent=user_agent,
            battery_level=battery,
            is_charging=is_charging,
            last_seen=time.time(),
            connected=True,
        )

        async with self._lock:
            self.devices[device_id] = dev
            self.active_sockets[device_id] = websocket

        logger.info(f"📱 OmniMesh: Connected {dev.device_type} '{dev.name}' ({device_id}) from {client_ip}")

        # Send welcome state packet
        welcome_pkt = {
            "type": "welcome",
            "device_id": device_id,
            "device_type": normalized_type,
            "host_ip": self.lan_ip,
            "pc_clipboard": read_pc_clipboard(),
            "timestamp": time.time(),
        }
        await websocket.send_text(json.dumps(welcome_pkt))

        # Broadcast presence change to other devices
        await self.broadcast_event({
            "type": "device_joined",
            "device": dev.to_dict(),
        }, exclude_device_id=device_id)

        return dev

    async def unregister_connection(self, device_id: str):
        """Marks a device as disconnected."""
        async with self._lock:
            if device_id in self.active_sockets:
                del self.active_sockets[device_id]
            if device_id in self.devices:
                self.devices[device_id].connected = False
                self.devices[device_id].last_seen = time.time()

        logger.info(f"📱 OmniMesh: Device {device_id} disconnected.")
        await self.broadcast_event({
            "type": "device_left",
            "device_id": device_id,
        })

    async def broadcast_event(self, message: Dict[str, Any], exclude_device_id: Optional[str] = None):
        """Broadcasts a JSON message to all active companion sockets."""
        payload = json.dumps(message)
        dead_ids: Set[str] = set()

        for dev_id, ws in list(self.active_sockets.items()):
            if exclude_device_id and dev_id == exclude_device_id:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                dead_ids.add(dev_id)

        for d_id in dead_ids:
            await self.unregister_connection(d_id)

    async def send_to_device(self, device_id: str, message: Dict[str, Any]) -> bool:
        """Sends a JSON packet directly to a specific companion device."""
        ws = self.active_sockets.get(device_id)
        if not ws:
            return False
        try:
            await ws.send_text(json.dumps(message))
            return True
        except Exception:
            await self.unregister_connection(device_id)
            return False

    async def handle_inbound_message(self, device_id: str, data: Dict[str, Any]):
        """Processes an incoming message from a companion device."""
        msg_type = data.get("type", "")

        # 1. Heartbeat / Telemetry update (Battery, Location, Status)
        if msg_type in ("heartbeat", "telemetry"):
            if device_id in self.devices:
                dev = self.devices[device_id]
                dev.last_seen = time.time()
                if "battery" in data:
                    dev.battery_level = data["battery"]
                if "is_charging" in data:
                    dev.is_charging = data["is_charging"]
                if "metadata" in data and isinstance(data["metadata"], dict):
                    dev.metadata.update(data["metadata"])

        # 2. Clipboard Synchronization (Device -> PC & other devices)
        elif msg_type == "clipboard_push":
            content = str(data.get("content", ""))
            if content and content != self.last_synced_clipboard:
                self.last_synced_clipboard = content
                # Write to Windows system clipboard
                write_pc_clipboard(content)
                logger.info(f"📋 OmniMesh: Synced clipboard from {device_id} ({len(content)} chars)")
                # Relay to all other companion devices
                await self.broadcast_event({
                    "type": "clipboard_update",
                    "content": content,
                    "from_device": device_id,
                }, exclude_device_id=device_id)

        # 3. Request PC Clipboard (Device -> PC)
        elif msg_type == "clipboard_pull":
            current_clip = read_pc_clipboard()
            await self.send_to_device(device_id, {
                "type": "clipboard_update",
                "content": current_clip,
                "from_device": "desktop-host",
            })

        # 4. Emergency Panic Stop Trigger (Watch or Phone -> PC)
        elif msg_type == "panic_stop":
            logger.warning(f"🚨 OmniMesh: Emergency panic stop triggered by device {device_id}!")
            try:
                from local_model_lab.shell_daemon import trigger_emergency_stop
                trigger_emergency_stop()
            except Exception:
                pass
            # Broadcast alert to all devices with physical vibration pattern
            await self.broadcast_event({
                "type": "panic_alert",
                "triggered_by": device_id,
                "message": "EMERGENCY PANIC STOP ENGAGED",
                "vibrate_pattern": [300, 100, 300, 100, 500],
            })

        # 5. Remote Voice Prompt / Dispatch (Watch or Phone -> Hermes Agents)
        elif msg_type == "voice_prompt":
            prompt = str(data.get("prompt", "")).strip()
            if prompt:
                logger.info(f"🎙️ OmniMesh: Inbound voice prompt from {device_id}: '{prompt[:60]}...'")
                asyncio.create_task(self._dispatch_voice_request(device_id, prompt))

        # 6. Camera Photo Captured (Phone -> Vision Agent)
        elif msg_type == "camera_photo":
            photo_b64 = data.get("photo_data", "")
            if photo_b64:
                logger.info(f"📸 OmniMesh: Received camera photo from {device_id} ({len(photo_b64)} b64 chars)")
                asyncio.create_task(self._process_camera_photo(device_id, photo_b64, data.get("prompt", "")))

    async def _dispatch_voice_request(self, device_id: str, prompt: str):
        """Asynchronously dispatches companion prompt to Hermes Agent dispatcher."""
        try:
            from channels import default_channel_dispatcher
            response = await default_channel_dispatcher(prompt, channel="mesh", user_id=device_id)
        except Exception as exc:
            response = f"Hermes Agent error: {str(exc)}"

        await self.send_to_device(device_id, {
            "type": "agent_response",
            "prompt": prompt,
            "response": response,
            "timestamp": time.time(),
        })

    async def _process_camera_photo(self, device_id: str, photo_b64: str, user_prompt: str = ""):
        """Saves photo and provides analysis response."""
        temp_dir = Path(__file__).resolve().parent.parent / "local_model_lab" / "outputs" / "mesh_photos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        filename = f"mesh_cam_{int(time.time())}.jpg"
        filepath = temp_dir / filename

        try:
            raw_b64 = photo_b64.split(",")[-1]
            img_bytes = base64.b64decode(raw_b64)
            filepath.write_bytes(img_bytes)

            await self.send_to_device(device_id, {
                "type": "photo_saved",
                "filename": filename,
                "size_bytes": len(img_bytes),
                "message": f"Photo saved to Hermes PC ({len(img_bytes) // 1024} KB). Ready for multimodal inspection.",
            })
        except Exception as exc:
            logger.error(f"Failed to save camera photo: {exc}")

    def notify_all(self, title: str, body: str, vibrate: bool = True):
        """Sends notification and optional vibration pattern to all companion devices."""
        asyncio.create_task(self.broadcast_event({
            "type": "notification",
            "title": title,
            "body": body,
            "vibrate": [150, 80, 150] if vibrate else [],
            "timestamp": time.time(),
        }))

    def get_status_overview(self) -> Dict[str, Any]:
        """Returns serializable overview of the mesh ecosystem."""
        return {
            "hub_ip": self.lan_ip,
            "hub_port": self.port,
            "companion_url": self.get_companion_url(),
            "smartwatch_url": self.get_companion_url("smartwatch"),
            "smartphone_url": self.get_companion_url("smartphone"),
            "laptop_url": self.get_companion_url("laptop"),
            "pairing_qr": self.get_pairing_qr(),
            "total_devices": len(self.devices),
            "connected_devices": len(self.active_sockets),
            "devices": [d.to_dict() for d in self.devices.values()],
        }


# Global Singleton Hub Instance
_global_hub: Optional[OmniMeshHub] = None


def get_omni_mesh_hub(port: int = 8000) -> OmniMeshHub:
    global _global_hub
    if _global_hub is None:
        _global_hub = OmniMeshHub(port=port)
    return _global_hub
