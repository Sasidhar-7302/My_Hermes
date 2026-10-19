# -*- coding: utf-8 -*-
"""
Hermes Unified Notification Center (`notification_center.py`)
=============================================================
Enterprise-grade, multi-surface notification engine with:
  1. Laya System-1 Priority & Surface Triage (CRITICAL, HIGH, NORMAL, LOW)
  2. Persistent Notification Inbox (`~/.hermes/notifications.json`) & JSONL Audit (`~/.hermes/logs/hermes_notifications.jsonl`)
  3. Real-Time Omni-Mesh Broadcast (Smartwatch AMOLED HUD + Haptics, Smartphone PWA, Laptop Cockpit)
  4. Native Windows 10/11 Toast Notification & Synthesized Acoustic Chimes (`winsound`)
  5. Actionable Notification Buttons (Open in Chintu, Cancel Shutdown, Approve/Deny Security Gate)
  6. Do-Not-Disturb (DND) / Quiet Hours & Surface Preference Controls
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERMES_DIR = Path.home() / ".hermes"
_LOG_DIR = _HERMES_DIR / "logs"
_NOTIF_STORE_FILE = _HERMES_DIR / "notifications.json"
_NOTIF_PREFS_FILE = _HERMES_DIR / "notification_prefs.json"
_NOTIF_JSONL_FILE = _LOG_DIR / "hermes_notifications.jsonl"
_MAX_STORED_NOTIFS = 200
_MAX_JSONL_BYTES = 10 * 1024 * 1024

# Priority definitions and intelligent surface routing rules
PRIORITY_RULES: Dict[str, Dict[str, Any]] = {
    "CRITICAL": {
        "rank": 4,
        "surfaces": ["pc_toast", "dashboard", "smartwatch", "smartphone", "laptop", "telegram"],
        "vibrate": [200, 100, 200, 100, 350],
        "tones_hz_ms": [(880, 110), (1175, 160)],
        "bypass_dnd": True,
        "badge_color": "#ef4444",
    },
    "HIGH": {
        "rank": 3,
        "surfaces": ["pc_toast", "dashboard", "smartwatch", "smartphone", "laptop"],
        "vibrate": [180, 90, 180],
        "tones_hz_ms": [(660, 100), (880, 130)],
        "bypass_dnd": False,
        "badge_color": "#f59e0b",
    },
    "NORMAL": {
        "rank": 2,
        "surfaces": ["dashboard", "smartphone", "laptop"],
        "vibrate": [100],
        "tones_hz_ms": [(523, 90)],
        "bypass_dnd": False,
        "badge_color": "#10b981",
    },
    "LOW": {
        "rank": 1,
        "surfaces": ["dashboard"],
        "vibrate": [],
        "tones_hz_ms": [],
        "bypass_dnd": False,
        "badge_color": "#38bdf8",
    },
}

CATEGORY_ICONS: Dict[str, str] = {
    "SECURITY_APPROVAL": "🛡️",
    "SECURITY_BLOCK": "🚨",
    "DEAL_ALERT": "🛍️",
    "ROSTER_COMPLETE": "✅",
    "SMART_SHUTDOWN": "🌙",
    "SYSTEM_HEALTH": "⚡",
    "COMPANION_EVENT": "📱",
    "INFO": "🔔",
}


@dataclass
class NotificationItem:
    id: str
    timestamp: str
    created_epoch: float
    title: str
    body: str
    priority: str = "NORMAL"          # CRITICAL | HIGH | NORMAL | LOW
    category: str = "INFO"            # SECURITY_APPROVAL | SECURITY_BLOCK | DEAL_ALERT | ROSTER_COMPLETE | SMART_SHUTDOWN | SYSTEM_HEALTH | COMPANION_EVENT | INFO
    role: str = "SYSTEM"
    icon: str = "🔔"
    surfaces: List[str] = field(default_factory=list)
    vibrate: List[int] = field(default_factory=list)
    read: bool = False
    acknowledged: bool = False
    actions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _append_jsonl(record: Dict[str, Any]) -> None:
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        if _NOTIF_JSONL_FILE.exists() and _NOTIF_JSONL_FILE.stat().st_size > _MAX_JSONL_BYTES:
            bak = _NOTIF_JSONL_FILE.with_suffix(".jsonl.1")
            try:
                if bak.exists():
                    bak.unlink()
                _NOTIF_JSONL_FILE.rename(bak)
            except Exception:
                pass
        with open(_NOTIF_JSONL_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


class NotificationCenter:
    """Centralized, thread-safe multi-device notification manager for Hermes."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: List[NotificationItem] = []
        self._prefs: Dict[str, Any] = {
            "dnd_enabled": False,
            "pc_toast_enabled": True,
            "sound_enabled": True,
            "watch_vibrate_enabled": True,
            "watch_haptics_enabled": True,
            "smartphone_push_enabled": True,
            "auto_notify_roster_tasks": True,
            "auto_notify_deals": True,
        }
        self._load_state()

    def _load_state(self) -> None:
        with self._lock:
            try:
                if _NOTIF_PREFS_FILE.exists():
                    with open(_NOTIF_PREFS_FILE, "r", encoding="utf-8") as pf:
                        loaded_p = json.load(pf)
                        if isinstance(loaded_p, dict):
                            self._prefs.update(loaded_p)
            except Exception:
                pass

            try:
                if _NOTIF_STORE_FILE.exists():
                    with open(_NOTIF_STORE_FILE, "r", encoding="utf-8") as nf:
                        raw_list = json.load(nf)
                    if isinstance(raw_list, list):
                        self._items = [
                            NotificationItem(
                                id=str(x.get("id") or f"notif_{uuid.uuid4().hex[:8]}"),
                                timestamp=str(x.get("timestamp") or datetime.now().isoformat()),
                                created_epoch=float(x.get("created_epoch") or time.time()),
                                title=str(x.get("title") or "Hermes Notification"),
                                body=str(x.get("body") or ""),
                                priority=str(x.get("priority") or "NORMAL").upper(),
                                category=str(x.get("category") or "INFO").upper(),
                                role=str(x.get("role") or "SYSTEM"),
                                icon=str(x.get("icon") or "🔔"),
                                surfaces=list(x.get("surfaces") or ["dashboard"]),
                                vibrate=list(x.get("vibrate") or []),
                                read=bool(x.get("read", False)),
                                acknowledged=bool(x.get("acknowledged", False)),
                                actions=list(x.get("actions") or []),
                                metadata=dict(x.get("metadata") or {}),
                            )
                            for x in raw_list[:_MAX_STORED_NOTIFS]
                        ]
            except Exception:
                self._items = []

    def _save_state(self) -> None:
        with self._lock:
            try:
                _HERMES_DIR.mkdir(parents=True, exist_ok=True)
                with open(_NOTIF_STORE_FILE, "w", encoding="utf-8") as nf:
                    json.dump([i.to_dict() for i in self._items[:_MAX_STORED_NOTIFS]], nf, indent=2)
                with open(_NOTIF_PREFS_FILE, "w", encoding="utf-8") as pf:
                    json.dump(self._prefs, pf, indent=2)
            except Exception:
                pass

    def get_preferences(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._prefs)

    def update_preferences(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            for k in list(self._prefs.keys()):
                if k in updates:
                    self._prefs[k] = bool(updates[k])
            if "watch_haptics_enabled" in updates:
                self._prefs["watch_vibrate_enabled"] = bool(updates["watch_haptics_enabled"])
            elif "watch_vibrate_enabled" in updates:
                self._prefs["watch_haptics_enabled"] = bool(updates["watch_vibrate_enabled"])
            self._save_state()
            return {"status": "ok", "preferences": dict(self._prefs), **dict(self._prefs)}

    def _trigger_host_pc_feedback(self, item: NotificationItem, rule: Dict[str, Any]) -> None:
        """Plays acoustic chime and triggers non-blocking Windows toast when enabled."""
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return
        dnd = self._prefs.get("dnd_enabled", False)
        if dnd and not rule.get("bypass_dnd", False):
            return

        def _worker() -> None:
            # 1. Acoustic Chime via winsound
            if self._prefs.get("sound_enabled", True) and rule.get("tones_hz_ms"):
                try:
                    import winsound
                    for freq, dur in rule.get("tones_hz_ms", []):
                        winsound.Beep(int(freq), int(dur))
                except Exception:
                    pass

            # 2. Windows 10/11 Native Toast Notification (for HIGH / CRITICAL or explicit pc_toast)
            if self._prefs.get("pc_toast_enabled", True) and "pc_toast" in item.surfaces and sys.platform == "win32":
                try:
                    safe_title = item.title.replace("'", "").replace('"', "")[:70]
                    safe_body = item.body.replace("'", "").replace('"', "").replace("\n", " ")[:160]
                    ps_script = (
                        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; "
                        "$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                        "$n = $t.GetElementsByTagName('text'); "
                        f"$n.Item(0).AppendChild($t.CreateTextNode('{safe_title}')) > $null; "
                        f"$n.Item(1).AppendChild($t.CreateTextNode('{safe_body}')) > $null; "
                        "$toast = [Windows.UI.Notifications.ToastNotification]::new($t); "
                        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Hermes Agent').Show($toast);"
                    )
                    subprocess.Popen(
                        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
                    )
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    def _broadcast_to_companions(self, item: NotificationItem) -> None:
        """Broadcasts the notification over OmniMeshHub WebSockets to paired companions."""
        try:
            import asyncio
            import inspect
            try:
                from companions import get_omni_mesh_hub
            except ImportError:
                from local_model_lab.omni_mesh import get_omni_mesh_hub
            hub = get_omni_mesh_hub()
            if not hub:
                return
            dnd = self._prefs.get("dnd_enabled", False)
            rule = PRIORITY_RULES.get(item.priority, PRIORITY_RULES["NORMAL"])
            if dnd and not rule.get("bypass_dnd", False):
                return
            vibrate_active = bool(item.vibrate) and self._prefs.get("watch_vibrate_enabled", True)
            res = hub.notify_all(
                title=f"{item.icon} {item.title}",
                body=item.body,
                vibrate=vibrate_active,
            )
            if inspect.iscoroutine(res):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(res)
                except RuntimeError:
                    res.close()
        except Exception:
            pass

    def emit(
        self,
        title: str,
        body: str,
        priority: str = "NORMAL",
        category: str = "INFO",
        role: str = "SYSTEM",
        icon: Optional[str] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        surfaces: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Creates, persists, logs, and routes a notification across the appropriate
        Hermes surfaces based on priority and user preferences.
        """
        prio_u = (priority or "NORMAL").upper()
        if prio_u not in PRIORITY_RULES:
            prio_u = "NORMAL"
        cat_u = (category or "INFO").upper()
        rule = PRIORITY_RULES[prio_u]

        resolved_icon = icon or CATEGORY_ICONS.get(cat_u, "🔔")
        resolved_surfaces = list(surfaces) if surfaces else list(rule["surfaces"])
        resolved_vibrate = list(rule["vibrate"]) if self._prefs.get("watch_vibrate_enabled", True) else []

        item = NotificationItem(
            id=f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            timestamp=datetime.now().isoformat(),
            created_epoch=time.time(),
            title=title,
            body=body,
            priority=prio_u,
            category=cat_u,
            role=role,
            icon=resolved_icon,
            surfaces=resolved_surfaces,
            vibrate=resolved_vibrate,
            read=False,
            acknowledged=False,
            actions=list(actions or []),
            metadata=dict(metadata or {}),
        )

        with self._lock:
            self._items.insert(0, item)
            self._items = self._items[:_MAX_STORED_NOTIFS]
            self._save_state()

        _append_jsonl({
            "event_type": "NOTIFICATION_EMITTED",
            **item.to_dict(),
        })

        self._trigger_host_pc_feedback(item, rule)
        self._broadcast_to_companions(item)
        return item.to_dict()

    def notify(
        self,
        title: str,
        body: str,
        priority: str = "NORMAL",
        category: str = "INFO",
        role: str = "SYSTEM",
        icon: Optional[str] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        surfaces: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """High-level wrapper around emit() returning standardized envelope."""
        item_dict = self.emit(
            title=title,
            body=body,
            priority=priority,
            category=category,
            role=role,
            icon=icon,
            actions=actions,
            metadata=metadata,
            surfaces=surfaces,
        )
        return {
            "status": "ok",
            "notification": item_dict,
            "delivered_surfaces": item_dict.get("surfaces", []),
        }

    def list_notifications(
        self,
        unread_only: bool = False,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        with self._lock:
            filtered = list(self._items)
            if unread_only:
                filtered = [n for n in filtered if not n.read]
            if category and category.upper() not in ("ALL", ""):
                cat_u = category.upper()
                filtered = [n for n in filtered if n.category == cat_u]

            unread_total = sum(1 for n in self._items if not n.read)
            critical_unread = sum(1 for n in self._items if not n.read and n.priority == "CRITICAL")

            return {
                "status": "ok",
                "unread_count": unread_total,
                "critical_unread_count": critical_unread,
                "total_count": len(self._items),
                "notifications": [n.to_dict() for n in filtered[:limit]],
                "preferences": dict(self._prefs),
            }

    def mark_read(self, notif_id: str = "ALL") -> Dict[str, Any]:
        with self._lock:
            marked = 0
            for n in self._items:
                if notif_id.upper() == "ALL" or n.id == notif_id:
                    if not n.read:
                        n.read = True
                        marked += 1
            self._save_state()
            unread_total = sum(1 for n in self._items if not n.read)
            return {"status": "ok", "marked_read": marked, "unread_count": unread_total}

    def clear_notifications(self, mode: str = "READ") -> Dict[str, Any]:
        with self._lock:
            before = len(self._items)
            if (mode or "").upper() == "ALL":
                self._items = []
            else:
                self._items = [n for n in self._items if not n.read]
            removed = before - len(self._items)
            self._save_state()
            return {"status": "ok", "removed": removed, "remaining": len(self._items)}

    def execute_action(self, notif_id: str, action_id: str) -> Dict[str, Any]:
        """Executes a one-click interactive action attached to a notification."""
        target: Optional[NotificationItem] = None
        with self._lock:
            for n in self._items:
                if n.id == notif_id:
                    target = n
                    n.read = True
                    n.acknowledged = True
                    break
            self._save_state()

        if not target:
            return {"status": "error", "message": f"Notification {notif_id} not found"}

        act_spec = next((a for a in target.actions if a.get("id") == action_id), {})
        result_msg = f"Action '{action_id}' acknowledged on {notif_id}"

        if action_id == "open_chintu":
            url = act_spec.get("url") or target.metadata.get("url") or "https://slickdeals.net"
            try:
                from hermes_browser import open_in_chintu_browser
                b_res = open_in_chintu_browser(url)
                result_msg = f"Opened {url} in isolated Chintu Browser ({b_res.get('status', 'ok')})"
            except Exception as e:
                result_msg = f"Chintu launch note: {e}"
        elif action_id == "cancel_shutdown":
            try:
                from smart_shutdown import get_smart_shutdown_monitor
                mon = get_smart_shutdown_monitor()
                if mon:
                    mon.cancel()
                result_msg = "Smart Idle Shutdown cancelled successfully."
            except Exception as e:
                result_msg = f"Cancel shutdown note: {e}"
        elif action_id in ("approve_gate", "reject_gate"):
            decision = "APPROVED" if action_id == "approve_gate" else "REJECTED"
            result_msg = f"Security gate {decision} by user at {datetime.now().strftime('%H:%M:%S')}."

        _append_jsonl({
            "event_type": "NOTIFICATION_ACTION_EXECUTED",
            "notif_id": notif_id,
            "action_id": action_id,
            "result": result_msg,
            "timestamp": datetime.now().isoformat(),
        })
        return {
            "status": "ok",
            "notif_id": notif_id,
            "action_id": action_id,
            "message": result_msg,
            "unread_count": sum(1 for n in self._items if not n.read),
        }


_NOTIF_CENTER_SINGLETON: Optional[NotificationCenter] = None


def get_notification_center() -> NotificationCenter:
    global _NOTIF_CENTER_SINGLETON
    if _NOTIF_CENTER_SINGLETON is None:
        _NOTIF_CENTER_SINGLETON = NotificationCenter()
    return _NOTIF_CENTER_SINGLETON
