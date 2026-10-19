# -*- coding: utf-8 -*-
"""
Hermes Omni-Mesh Central Hub
Coordinates real-time WebSocket communication, state presence, authentication, and cross-device routing
across Smartwatch, Smartphone, Laptop, and Host PC.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import socket
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from fastapi import WebSocket

from .auth import get_pairing_manager
from .laptop import get_laptop_bridge
from .logger import get_companion_logger, get_recent_companion_logs, log_companion_event
from .smartphone import get_smartphone_bridge
from .smartwatch import get_smartwatch_bridge

logger = get_companion_logger()

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
    """Central WebSocket routing bus, authentication guard, and device state coordinator."""

    def __init__(self, port: int = 8000):
        self.devices: Dict[str, MeshDevice] = {}
        self.active_sockets: Dict[str, WebSocket] = {}
        self.last_synced_clipboard: str = ""
        self._lock = asyncio.Lock()
        self.port: int = port
        self.lan_ip: str = get_local_lan_ip()
        self._gateway_listener: Optional[Callable[[str, str, str, str], Awaitable[None]]] = None

        # Battery-Preserving Screen Wall & HUD State
        self.device_snapshots: Dict[str, Dict[str, Any]] = {}
        self.watch_hud_state: Dict[str, Any] = {
            "time": time.strftime("%H:%M"),
            "battery": None,
            "is_charging": False,
            "voice_state": "idle",
            "last_message": "Ready",
            "last_seen": time.time(),
        }
        self._battery_alert_state: Dict[str, Dict[str, Any]] = {}

        # Seed host desktop node
        self.devices["desktop-host"] = MeshDevice(
            device_id="desktop-host",
            name="Hermes Host PC",
            device_type="desktop",
            ip_address=self.lan_ip,
            connected=True,
            metadata={"os": sys.platform, "role": "Primary AI Core"},
        )

    def check_battery_guardian(self, dev: MeshDevice):
        """Monitors companion battery health and sends timely alerts without user distraction."""
        if dev.battery_level is None:
            return
        state = self._battery_alert_state.setdefault(dev.device_id, {"low_notified": False, "full_notified": False})

        # Low Battery Alert (< 20%)
        if dev.battery_level <= 20 and not dev.is_charging and not state["low_notified"]:
            state["low_notified"] = True
            self.notify_all(
                title=f"⚠️ Low Battery ({dev.name})",
                body=f"{dev.name} is at {dev.battery_level}%. Connect charger to stay connected to Hermes.",
                vibrate=True,
            )
            log_companion_event("BATTERY_LOW", f"{dev.name} battery critical ({dev.battery_level}%)", device_id=dev.device_id)
        elif dev.battery_level > 25:
            state["low_notified"] = False

        # Full Battery Alert (100% on charger)
        if dev.battery_level >= 100 and dev.is_charging and not state["full_notified"]:
            state["full_notified"] = True
            self.notify_all(
                title=f"🔋 Battery Full ({dev.name})",
                body=f"{dev.name} reached 100%. Unplug to protect battery longevity.",
                vibrate=False,
            )
            log_companion_event("BATTERY_FULL", f"{dev.name} is fully charged (100%)", device_id=dev.device_id)
        elif not dev.is_charging:
            state["full_notified"] = False

    async def request_screen_snapshot(self, device_id: str) -> bool:
        """Requests an on-demand, battery-preserving single screen snapshot from companion."""
        return await self.send_to_device(device_id, {
            "type": "request_screen_snapshot",
            "timestamp": time.time(),
        })

    async def ping_device(self, device_id: str, tone: str = "chime") -> bool:
        """Acoustically pings and vibrates companion device to find it in the room."""
        ok = await self.send_to_device(device_id, {
            "type": "ping_device",
            "tone": tone,
            "timestamp": time.time(),
        })
        if ok:
            log_companion_event("DEVICE_PINGED", f"Sent acoustic ping to {device_id}", device_id=device_id)
        return ok

    def set_gateway_listener(self, listener: Callable[[str, str, str, str], Awaitable[None]]) -> None:
        """Hooks the Hermes Gateway Companion Adapter to process inbound device prompts."""
        self._gateway_listener = listener
        log_companion_event("GATEWAY_LISTENER_BOUND", "Hermes Gateway platform adapter listener attached.")

    def get_companion_url(self, device_type: Optional[str] = None, pairing_code: Optional[str] = None) -> str:
        """Returns the local network companion URL for mobile/watch/laptop."""
        base = f"http://{self.lan_ip}:{self.port}"
        norm_type = (device_type or "").lower()
        if norm_type in ("watch", "smartwatch"):
            target = f"{base}/companions/smartwatch"
        elif norm_type in ("laptop", "workstation"):
            target = f"{base}/companions/laptop"
        else:
            target = f"{base}/companions/smartphone"

        if pairing_code:
            target += f"?pair={pairing_code}"
        return target

    def get_pairing_qr(self, device_type: Optional[str] = None) -> str:
        """Generates pairing QR code with a temporary pairing session code."""
        pm = get_pairing_manager()
        pair_code = pm.create_pairing_code(ttl_seconds=600)
        url = self.get_companion_url(device_type, pairing_code=pair_code)
        return generate_qr_code_png_base64(url)

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
        token: Optional[str] = None,
        pairing_code: Optional[str] = None,
        skip_accept: bool = False,
    ) -> Optional[MeshDevice]:
        """Registers a newly connected companion device after verifying authentication."""
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

        # Authenticate device
        pm = get_pairing_manager()
        is_auth, auth_status, issued_token = pm.authenticate_connection(
            device_id=device_id,
            token=token,
            pairing_code=pairing_code,
            name=name,
            device_type=normalized_type,
            user_agent=user_agent,
            client_ip=client_ip,
        )

        if not is_auth:
            reject_pkt = {
                "type": "auth_error",
                "status": "unauthorized",
                "message": "Authentication required. Please scan the pairing QR code from the Hermes PC dashboard.",
                "timestamp": time.time(),
            }
            try:
                await websocket.send_text(json.dumps(reject_pkt))
                await websocket.close(code=4001)
            except Exception:
                pass
            return None

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
            stale_ids = [
                old_id for old_id, old_dev in self.devices.items()
                if old_id != device_id
                and old_id != "desktop-host"
                and old_dev.ip_address == client_ip
                and old_dev.device_type == normalized_type
                and old_id not in self.active_sockets
            ]
            for old_id in stale_ids:
                self.devices.pop(old_id, None)
            self.devices[device_id] = dev
            self.active_sockets[device_id] = websocket

        log_companion_event(
            "DEVICE_CONNECTED",
            f"Connected {dev.device_type} '{dev.name}' from {client_ip}",
            device_id=device_id,
            device_kind=dev.device_type,
            auth_status=auth_status,
        )

        # Notify companion bridges
        if normalized_type == "laptop":
            get_laptop_bridge().register_node(device_id, dev.name, client_ip, user_agent)
        elif normalized_type == "smartphone":
            get_smartphone_bridge().log_activity("CONNECT", f"Connected {dev.name} ({client_ip})")

        # Send welcome state packet
        welcome_pkt: Dict[str, Any] = {
            "type": "welcome",
            "device_id": device_id,
            "device_type": normalized_type,
            "host_ip": self.lan_ip,
            "pc_clipboard": read_pc_clipboard(),
            "timestamp": time.time(),
        }
        if issued_token:
            welcome_pkt["auth_token"] = issued_token

        await websocket.send_text(json.dumps(welcome_pkt))

        # Broadcast presence change to other devices
        await self.broadcast_event({
            "type": "device_joined",
            "device": dev.to_dict(),
        }, exclude_device_id=device_id)

        return dev

    async def _delayed_offline_check(self, device_id: str, grace_seconds: float = 120.0):
        """Allows mobile/watch companions to survive brief app switches or screenshot pauses without flashing OFFLINE."""
        await asyncio.sleep(grace_seconds)
        async with self._lock:
            if device_id in self.active_sockets:
                return
            dev = self.devices.get(device_id)
            if not dev:
                return
            if (time.time() - dev.last_seen) < grace_seconds:
                return
            dev.connected = False

        log_companion_event("DEVICE_DISCONNECTED", f"Device {device_id} disconnected after standby grace.", device_id=device_id)
        await self.broadcast_event({
            "type": "device_left",
            "device_id": device_id,
        })

    async def unregister_connection(self, device_id: str, immediate: bool = False):
        """Marks a device as disconnected (with a 120s standby grace window for real LAN mobile/watch devices)."""
        is_lan_companion = False
        async with self._lock:
            if device_id in self.active_sockets:
                del self.active_sockets[device_id]
            if device_id in self.devices:
                dev = self.devices[device_id]
                dev.last_seen = time.time()
                if not immediate and dev.ip_address not in ("127.0.0.1", "::1", "testclient"):
                    is_lan_companion = True
                    dev.connected = True
                else:
                    dev.connected = False

        if is_lan_companion:
            asyncio.create_task(self._delayed_offline_check(device_id, grace_seconds=120.0))
            return

        log_companion_event("DEVICE_DISCONNECTED", f"Device {device_id} disconnected.", device_id=device_id)
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

    async def send_agent_reply(self, device_id: str, response_text: str, prompt_text: str = "") -> bool:
        """Sends an agent completion response packet to the target device."""
        return await self.send_to_device(device_id, {
            "type": "agent_response",
            "prompt": prompt_text,
            "response": response_text,
            "timestamp": time.time(),
        })

    async def handle_inbound_message(self, device_id: str, data: Dict[str, Any]):
        """Processes an incoming message from a companion device."""
        msg_type = data.get("type", "")

        # 1. Heartbeat / Telemetry update (Battery, Status)
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
                if dev.device_type == "laptop" and "cpu" in data:
                    get_laptop_bridge().update_telemetry(
                        device_id,
                        float(data.get("cpu", 0)),
                        float(data.get("ram", 0)),
                        dev.battery_level,
                    )
                self.check_battery_guardian(dev)

        # 2. Clipboard Synchronization (Device -> PC & other devices)
        elif msg_type == "clipboard_push":
            content = str(data.get("content", ""))
            if content and content != self.last_synced_clipboard:
                self.last_synced_clipboard = content
                write_pc_clipboard(content)
                log_companion_event(
                    "CLIPBOARD_SYNC",
                    f"Synced clipboard from {device_id} ({len(content)} chars)",
                    device_id=device_id,
                )
                # Store in smartphone bridge buffer if applicable
                get_smartphone_bridge().buffer_clipboard(content)
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
            stop_detail = "Engaged"
            stopped = True
            try:
                from local_model_lab.shell_daemon import trigger_emergency_stop, is_emergency_stopped
                stop_detail = trigger_emergency_stop()
                stopped = is_emergency_stopped()
            except Exception as exc:
                stop_detail = f"Exception: {exc}"
                stopped = False

            log_companion_event(
                "PANIC_STOP",
                f"Emergency panic stop triggered by device {device_id}! Status: {stop_detail}",
                level="CRITICAL",
                device_id=device_id,
            )

            # Broadcast alert to all devices with physical vibration pattern
            haptic_pattern = get_smartwatch_bridge().get_haptic_pattern("panic")
            await self.broadcast_event({
                "type": "panic_alert",
                "triggered_by": device_id,
                "status": "engaged" if stopped else "failed",
                "message": f"EMERGENCY PANIC STOP ENGAGED: {stop_detail}",
                "vibrate_pattern": haptic_pattern,
            })

        # 5. Remote Voice / Text Prompt (Watch, Phone, or Laptop -> Hermes Agents)
        elif msg_type in ("voice_prompt", "text_prompt"):
            prompt = str(data.get("prompt", "")).strip()
            if prompt:
                dev = self.devices.get(device_id)
                dev_name = dev.name if dev else "Companion"
                dev_type = dev.device_type if dev else "phone"
                log_companion_event(
                    "PROMPT_INBOUND",
                    f"Inbound prompt from {device_id} ({dev_type}): '{prompt[:80]}'",
                    device_id=device_id,
                    device_kind=dev_type,
                )
                asyncio.create_task(self._dispatch_prompt(device_id, dev_type, dev_name, prompt))

        # 5b. Streaming Realtime Voice / Typing Transcript (Jev / Laya System-1)
        elif msg_type in ("voice_partial", "stream_partial", "typing_partial"):
            partial = str(data.get("transcript") or data.get("text", "")).strip()
            if partial:
                try:
                    from local_model_lab.laya_real_bridge import evaluate_streaming_transcript
                    eval_res = evaluate_streaming_transcript(partial, session_id=device_id)
                    if eval_res.get("executed"):
                        await self.send_to_device(device_id, {
                            "type": "fast_action_executed",
                            "action": eval_res.get("action"),
                            "tool": eval_res.get("tool"),
                            "result": eval_res.get("result"),
                            "confidence": eval_res.get("confidence", 1.0),
                            "transcript": partial,
                            "timestamp": time.time(),
                        })
                except Exception as exc:
                    logger.debug(f"Streaming voice evaluation error: {exc}")

        # 6. Camera Photo or Mobile Screen Snap (Phone -> Vision Agent)
        elif msg_type in ("camera_photo", "mobile_screen_snap"):
            photo_b64 = data.get("photo_data") or data.get("image") or ""
            prompt_text = data.get("prompt") or ("Analyze what is currently visible on my mobile phone screen." if msg_type == "mobile_screen_snap" else "Analyze camera photo from companion")
            if photo_b64:
                asyncio.create_task(self._process_camera_photo(device_id, photo_b64, prompt_text))

        # 7. Low-Power Location Telemetry (Always-on Geofencing & Weather Context)
        elif msg_type == "location_telemetry":
            lat = data.get("latitude")
            lon = data.get("longitude")
            if lat is not None and lon is not None:
                try:
                    from local_model_lab.hermes_location import get_location_engine
                    loc_engine = get_location_engine()
                    dev = self.devices.get(device_id)
                    dev_type = dev.device_type if dev else data.get("source_type", "smartphone")
                    updated = loc_engine.update_location(
                        latitude=float(lat),
                        longitude=float(lon),
                        accuracy=float(data.get("accuracy", 0.0)),
                        altitude=data.get("altitude"),
                        speed=data.get("speed"),
                        heading=data.get("heading"),
                        source_device=device_id,
                        source_type=dev_type,
                    )
                    # Broadcast location update to PC dashboards
                    await self.broadcast_event({
                        "type": "location_updated",
                        "location": updated,
                    })
                except Exception as exc:
                    logger.debug(f"Location telemetry ingestion error: {exc}")

        # 8. Battery-Preserving Companion Screen Snapshot
        elif msg_type == "companion_screen_snapshot":
            img = data.get("image", "")
            if img:
                snap_entry = {
                    "image": img,
                    "width": data.get("width"),
                    "height": data.get("height"),
                    "battery": data.get("battery"),
                    "is_charging": data.get("is_charging"),
                    "device_type": data.get("device_type", "smartphone"),
                    "device_id": device_id,
                    "timestamp": time.time(),
                }
                self.device_snapshots[device_id] = snap_entry
                await self.broadcast_event({
                    "type": "screen_snapshot_received",
                    "device_id": device_id,
                    "snapshot": snap_entry,
                })

        # 9. Smartwatch Real-Time Wrist HUD Micro-Telemetry (Zero Battery Drain)
        elif msg_type == "watch_hud_telemetry":
            self.watch_hud_state.update({
                "time": data.get("time", time.strftime("%H:%M")),
                "battery": data.get("battery"),
                "is_charging": data.get("is_charging", False),
                "voice_state": data.get("voice_state", "idle"),
                "last_message": data.get("last_message", ""),
                "heart_rate": data.get("heart_rate"),
                "last_seen": time.time(),
            })
            await self.broadcast_event({
                "type": "watch_hud_updated",
                "hud": self.watch_hud_state,
            })

    async def _dispatch_prompt(self, device_id: str, device_type: str, device_name: str, prompt: str):
        """Dispatches companion prompt into Hermes Gateway or company dispatcher."""
        # Fast System 1 Gate: Check if deterministic tool can execute immediately
        try:
            from local_model_lab.laya_real_bridge import evaluate_streaming_transcript
            fast_res = evaluate_streaming_transcript(prompt, session_id=device_id, fire_threshold=0.80)
            if fast_res.get("executed"):
                result_content = fast_res.get("result", {})
                msg = result_content.get("message") or result_content.get("result") or str(result_content)
                await self.send_agent_reply(device_id, f"⚡ [System 1 Executed ({fast_res.get('tool')})]: {msg}", prompt)
                return
        except Exception as exc:
            logger.debug(f"System 1 bypass error: {exc}")

        # Location Intelligence Gate: Instant accurate answer for user location & weather queries
        lower_prompt = prompt.lower().strip()
        if any(q in lower_prompt for q in ["where am i", "what is my location", "what's my location", "am i home", "what is the weather", "what's the weather", "how far am i from home", "what city am i in"]):
            try:
                from local_model_lab.hermes_location import get_location_engine
                engine = get_location_engine()
                cur = engine.get_current()
                if "weather" in lower_prompt:
                    w = cur.get("weather", {})
                    if w:
                        cond = w.get("condition", "Clear")
                        temp_f = w.get("temperature_f", "70")
                        temp_c = w.get("temperature_c", "21")
                        hum = w.get("humidity", 50)
                        wind = w.get("wind_speed_kmh", 10)
                        ans = f"🌤️ Current Weather: {cond}, {temp_f}°F ({temp_c}°C) with {hum}% humidity and wind at {wind} km/h (at {cur.get('display_name', 'your location')})."
                    else:
                        ans = f"Weather lookup pending satellite telemetry for {cur.get('display_name', 'your location')}."
                    await self.send_agent_reply(device_id, ans, prompt)
                    return
                elif any(q in lower_prompt for q in ["where am i", "my location", "am i home", "how far", "what city"]):
                    zone = cur.get("zone", "Home Cockpit")
                    disp = cur.get("display_name", "Home Cockpit")
                    dist = cur.get("distance_to_home_meters", 0)
                    dist_str = f"({dist:.0f}m from Home Cockpit)" if dist and zone != "Home Cockpit" else "(At Home Cockpit)"
                    src = cur.get("source_type", "companion")
                    ans = f"📍 You are currently in **{zone}** {dist_str} at {disp}. [GPS Telemetry synced from your {src}]"
                    await self.send_agent_reply(device_id, ans, prompt)
                    return
            except Exception as exc:
                logger.debug(f"Location instant answer error: {exc}")

        # Enrich prompt with environmental context for all general queries
        try:
            from local_model_lab.hermes_location import get_location_engine
            ctx_snippet = get_location_engine().get_environmental_context_prompt()
            enriched_prompt = f"[{ctx_snippet}]\n{prompt}"
        except Exception:
            enriched_prompt = prompt

        # Check if gateway listener is hooked
        if self._gateway_listener:
            try:
                await self._gateway_listener(device_id, device_type, device_name, enriched_prompt)
                return
            except Exception as exc:
                log_companion_event("GATEWAY_DISPATCH_ERROR", f"Gateway listener failed: {exc}", level="WARNING", device_id=device_id)

        # Fallback to channel dispatcher
        try:
            from channels import default_channel_dispatcher
            response = await default_channel_dispatcher(enriched_prompt, channel="companion", user_id=device_id)
        except Exception as exc:
            response = f"Hermes Agent error: {str(exc)}"

        await self.send_agent_reply(device_id, response, prompt)

    async def _process_camera_photo(self, device_id: str, photo_b64: str, user_prompt: str = ""):
        """Validates photo, saves safely to outputs, and provides analysis response."""
        # Size limit: 15MB base64 string
        if len(photo_b64) > 15 * 1024 * 1024:
            await self.send_to_device(device_id, {
                "type": "error",
                "message": "Photo exceeds 15MB limit.",
            })
            return

        try:
            # Strip header if present
            raw_b64 = photo_b64.split(",")[-1]
            img_bytes = base64.b64decode(raw_b64)
            filename = f"mesh_cam_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"

            # Save via smartphone bridge
            saved_path = get_smartphone_bridge().save_captured_photo(img_bytes, filename)

            log_companion_event(
                "PHOTO_SAVED",
                f"Saved photo from {device_id} ({len(img_bytes)} bytes) -> {saved_path.name}",
                device_id=device_id,
            )

            await self.send_to_device(device_id, {
                "type": "photo_saved",
                "filename": filename,
                "size_bytes": len(img_bytes),
                "message": f"Photo saved to Hermes PC ({len(img_bytes) // 1024} KB). Ready for vision models.",
            })

            # If user provided a prompt with photo, dispatch prompt
            if user_prompt:
                full_prompt = f"{user_prompt}\n[Attached Camera Photo: {saved_path}]"
                dev = self.devices.get(device_id)
                dev_name = dev.name if dev else "Companion"
                dev_type = dev.device_type if dev else "smartphone"
                await self._dispatch_prompt(device_id, dev_type, dev_name, full_prompt)

        except Exception as exc:
            log_companion_event("PHOTO_ERROR", f"Failed to save camera photo: {exc}", level="ERROR", device_id=device_id)
            await self.send_to_device(device_id, {
                "type": "error",
                "message": f"Failed to process image: {exc}",
            })

    def notify_all(self, title: str, body: str, vibrate: bool = True):
        """Sends notification and optional vibration pattern to all companion devices."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast_event({
                "type": "notification",
                "title": title,
                "body": body,
                "vibrate": [150, 80, 150] if vibrate else [],
                "timestamp": time.time(),
            }))
        except RuntimeError:
            pass

    def get_status_overview(self) -> Dict[str, Any]:
        """Returns serializable overview of the mesh ecosystem and auth status."""
        pm = get_pairing_manager()
        loc_data = {}
        try:
            from local_model_lab.hermes_location import get_location_engine
            loc_data = get_location_engine().get_current()
        except Exception:
            pass

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
            "paired_devices": pm.list_paired_devices(),
            "recent_logs": get_recent_companion_logs(limit=20),
            "location": loc_data,
            "watch_hud": self.watch_hud_state,
            "snapshots": {
                k: {
                    "device_id": v.get("device_id", k),
                    "device_type": v.get("device_type", "unknown"),
                    "battery": v.get("battery"),
                    "is_charging": v.get("is_charging"),
                    "timestamp": v.get("timestamp"),
                    "width": v.get("width"),
                    "height": v.get("height"),
                    "image": v.get("image", ""),
                }
                for k, v in self.device_snapshots.items()
            },
        }


# Global Singleton Hub Instance
_global_hub: Optional[OmniMeshHub] = None


def get_omni_mesh_hub(port: int = 8000) -> OmniMeshHub:
    global _global_hub
    if _global_hub is None:
        _global_hub = OmniMeshHub(port=port)
    return _global_hub
