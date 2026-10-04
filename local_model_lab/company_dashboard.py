# -*- coding: utf-8 -*-
"""
Hermes Agent Company Dashboard & Executive Operations Center
Integrates Multi-Agent Team Roster, Multi-Monitor Desktop Shell, Paper Desktop MCP Studio,
PII Redaction Shield, RPA Macro Studio, System & Proactivity Observer, Browser Control,
Smart Network-Idle Shutdown, Multi-Vendor Deal Finder & Watchlist, and Multi-Channel Gateways.
"""

import os
import sys
import json
import re
import time
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_cur_dir = os.path.dirname(os.path.abspath(__file__))
if _cur_dir not in sys.path:
    sys.path.insert(0, _cur_dir)

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

try:
    from local_model_lab import role_registry
    from local_model_lab.role_registry import ROLES, VERIFIED_MODELS
except ImportError:
    import role_registry
    from role_registry import ROLES, VERIFIED_MODELS

# Import peripheral Hermes modules with graceful fallbacks
try:
    from local_model_lab.window_services import (
        get_display_monitors,
        list_active_windows,
        snap_window,
        move_window_to_monitor,
        focus_window,
    )
except ImportError:
    try:
        from window_services import (
            get_display_monitors,
            list_active_windows,
            snap_window,
            move_window_to_monitor,
            focus_window,
        )
    except Exception:
        get_display_monitors = lambda: []
        list_active_windows = lambda: []
        snap_window = lambda t, p: {"status": "error", "message": "window_services unavailable"}
        move_window_to_monitor = lambda t, m: {"status": "error", "message": "window_services unavailable"}
        focus_window = lambda t: False

try:
    from local_model_lab.shell_daemon import (
        is_emergency_stopped,
        trigger_emergency_stop,
        clear_emergency_stop,
    )
except ImportError:
    try:
        from shell_daemon import (
            is_emergency_stopped,
            trigger_emergency_stop,
            clear_emergency_stop,
        )
    except Exception:
        is_emergency_stopped = lambda: False
        trigger_emergency_stop = lambda: "EMERGENCY_STOP_ENGAGED"
        clear_emergency_stop = lambda: None

try:
    from local_model_lab.paper_client import (
        get_paper_client,
        is_port_open,
        detect_paper_executable,
    )
except ImportError:
    try:
        from paper_client import (
            get_paper_client,
            is_port_open,
            detect_paper_executable,
        )
    except Exception:
        get_paper_client = lambda: None
        is_port_open = lambda host="127.0.0.1", port=29979, timeout=0.5: False
        detect_paper_executable = lambda: None

try:
    from local_model_lab.pii_shield import PIIShield, mask_sensitive_text
except ImportError:
    try:
        from pii_shield import PIIShield, mask_sensitive_text
    except Exception:
        class PIIShield:
            PATTERNS = {}
            @classmethod
            def mask(cls, text): return text
            @classmethod
            def detect_entities(cls, text): return []
            @classmethod
            def has_sensitive_data(cls, text): return False
        mask_sensitive_text = lambda text: text

try:
    from local_model_lab.rpa_recorder import get_rpa_recorder
except ImportError:
    try:
        from rpa_recorder import get_rpa_recorder
    except Exception:
        get_rpa_recorder = lambda: None

try:
    from local_model_lab.system_observer import get_system_observer
except ImportError:
    try:
        from system_observer import get_system_observer
    except Exception:
        get_system_observer = lambda: None

# ── TURNKEY AUTOMATION MODULE IMPORTS ───────────────────────────────────────
try:
    from local_model_lab.smart_shutdown import (
        get_smart_shutdown_monitor,
        SmartShutdownConfig,
    )
except ImportError:
    try:
        from smart_shutdown import (
            get_smart_shutdown_monitor,
            SmartShutdownConfig,
        )
    except Exception:
        get_smart_shutdown_monitor = lambda: None
        SmartShutdownConfig = lambda **kwargs: None

try:
    from local_model_lab.deal_finder import (
        search_deals,
        get_deal_watch_store,
    )
except ImportError:
    try:
        from deal_finder import (
            search_deals,
            get_deal_watch_store,
        )
    except Exception:
        search_deals = lambda q, v=None, m=6: []
        get_deal_watch_store = lambda: None

try:
    import channels
    from channels import (
        get_all_channel_statuses,
        get_channel_policy_manager,
        get_discord_gateway,
        get_slack_gateway,
        get_whatsapp_gateway,
        get_telegram_gateway,
        get_relay_gateway,
        default_channel_dispatcher,
    )
except ImportError:
    try:
        from local_model_lab import channels
        from local_model_lab.channels import (
            get_all_channel_statuses,
            get_channel_policy_manager,
            get_discord_gateway,
            get_slack_gateway,
            get_whatsapp_gateway,
            get_telegram_gateway,
            get_relay_gateway,
            default_channel_dispatcher,
        )
    except Exception:
        get_all_channel_statuses = lambda: {}
        get_channel_policy_manager = lambda: None
        get_discord_gateway = lambda: None
        get_slack_gateway = lambda: None
        get_whatsapp_gateway = lambda: None
        get_telegram_gateway = lambda: None
        get_relay_gateway = lambda: None
        default_channel_dispatcher = None

# ── OMNI-MESH CROSS-DEVICE IMPORTS ──────────────────────────────────────────
try:
    from local_model_lab.omni_mesh import (
        get_omni_mesh_hub,
        read_pc_clipboard,
        write_pc_clipboard,
    )
    from local_model_lab.companion_web import (
        render_companion_html,
        MANIFEST_JSON,
        SERVICE_WORKER_JS,
    )
except ImportError:
    try:
        from omni_mesh import (
            get_omni_mesh_hub,
            read_pc_clipboard,
            write_pc_clipboard,
        )
        from companion_web import (
            render_companion_html,
            MANIFEST_JSON,
            SERVICE_WORKER_JS,
        )
    except Exception:
        get_omni_mesh_hub = lambda: None
        read_pc_clipboard = lambda: ""
        write_pc_clipboard = lambda t: False
        render_companion_html = lambda h, p: "<html><body>Hermes Companion</body></html>"
        MANIFEST_JSON = {}
        SERVICE_WORKER_JS = ""


app = FastAPI(title="Hermes Agent Operations Center")

ROLE_META = {
    "CEO": {
        "icon": "🧠",
        "title": "Chief Executive Officer",
        "desc": "System orchestrator. Delegates tasks, reviews outputs, and synthesizes lessons into memory.",
        "color": "#38bdf8"
    },
    "PM": {
        "icon": "📋",
        "title": "Product Manager",
        "desc": "Converts user vision into unambiguous specs, acceptance criteria, and prioritized feature scope.",
        "color": "#a78bfa"
    },
    "ARCHITECT": {
        "icon": "🏗️",
        "title": "System Architect",
        "desc": "Designs directory structure, database schemas, API contracts, protocols, and scaling topology.",
        "color": "#fbbf24"
    },
    "CODER": {
        "icon": "💻",
        "title": "Lead Software Engineer",
        "desc": "Writes clean, tested, and documented code based strictly on architecture specs.",
        "color": "#34d399"
    },
    "TESTER": {
        "icon": "🧪",
        "title": "QA & Test Engineer",
        "desc": "Validates edge cases, writes automated test suites, and blocks buggy implementations.",
        "color": "#f472b6"
    },
    "SECURITY": {
        "icon": "🔒",
        "title": "Security Auditor",
        "desc": "Audits code for OWASP vulnerabilities, credential leaks, and insecure dependencies.",
        "color": "#f87171"
    },
    "DEVOPS": {
        "icon": "🚀",
        "title": "DevOps & Infrastructure",
        "desc": "Manages scripts, Docker containers, CI/CD automation, and deployment stability.",
        "color": "#fb923c"
    },
    "OPERATOR": {
        "icon": "🖥️",
        "title": "Desktop & Computer Operator",
        "desc": "Automates OS tasks, window management, and application workflows under strict deletion & payment shields.",
        "color": "#06b6d4"
    }
}


def get_tasks():
    tasks_file = os.path.join(os.path.dirname(__file__), 'role_tasks.json')
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def get_employee_logs(role: str = None):
    emp_dir = os.path.join(os.path.dirname(__file__), 'employee_logs')
    if role:
        emp_file = os.path.join(emp_dir, f"{role}.json")
        if os.path.exists(emp_file):
            try:
                with open(emp_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        all_tasks = get_tasks()
        return [t for t in all_tasks if t.get("role") == role]
    return get_tasks()


def save_soul(role, new_soul):
    reg_file = os.path.join(os.path.dirname(__file__), 'role_registry.py')
    with open(reg_file, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = rf'("{role}":\s*\{{[^}}]*?"soul":\s*")(?:[^"\\]|\\.)*(")'
    escaped_soul = new_soul.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    new_content, count = re.subn(pattern, rf'\g<1>{escaped_soul}\g<2>', content, count=1)

    if count > 0:
        with open(reg_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


# ==============================================================================
# REST API ENDPOINTS
# ==============================================================================

@app.get("/api/employee_logs/{role}")
async def api_get_employee_logs(role: str):
    logs = get_employee_logs(role)
    return JSONResponse(content={"role": role, "count": len(logs), "logs": logs})


@app.post("/api/update_soul")
async def api_update_soul(request: Request):
    data = await request.json()
    role = data.get("role")
    soul = data.get("soul")
    if role and soul is not None:
        success = save_soul(role, soul)
        return {"status": "ok" if success else "error"}
    return {"status": "bad_request"}


@app.get("/api/desktop/monitors")
async def api_desktop_monitors():
    monitors = [m.to_dict() for m in get_display_monitors()]
    return JSONResponse(content={"count": len(monitors), "monitors": monitors})


@app.get("/api/desktop/windows")
async def api_desktop_windows():
    raw_windows = list_active_windows()
    formatted = []
    for w in raw_windows:
        if isinstance(w, dict):
            rect = w.get("rect", (0, 0, 0, 0))
            formatted.append({
                "hwnd": w.get("hwnd", 0),
                "title": w.get("title", "Untitled"),
                "monitor": w.get("monitor_id", 1),
                "is_active": w.get("is_active", False),
                "x": rect[0] if len(rect) > 0 else 0,
                "y": rect[1] if len(rect) > 1 else 0,
                "width": rect[2] if len(rect) > 2 else 0,
                "height": rect[3] if len(rect) > 3 else 0,
            })
        elif hasattr(w, "to_dict"):
            formatted.append(w.to_dict())
        else:
            formatted.append(dict(w))
    return JSONResponse(content={"count": len(formatted), "windows": formatted})


@app.post("/api/desktop/snap")
async def api_desktop_snap(request: Request):
    data = await request.json()
    target = data.get("target")
    position = data.get("position", "left")
    res = snap_window(target, position)
    return JSONResponse(content=res)


@app.post("/api/desktop/move_monitor")
async def api_desktop_move_monitor(request: Request):
    data = await request.json()
    target = data.get("target")
    monitor_id = int(data.get("monitor_id", 1))
    res = move_window_to_monitor(target, monitor_id)
    return JSONResponse(content=res)


@app.get("/api/desktop/emergency_stop")
async def api_get_emergency_stop():
    return JSONResponse(content={"stopped": is_emergency_stopped()})


@app.post("/api/desktop/emergency_stop")
async def api_post_emergency_stop(request: Request):
    data = await request.json()
    stopped = data.get("stopped", True)
    if stopped:
        trigger_emergency_stop()
    else:
        clear_emergency_stop()
    return JSONResponse(content={"stopped": is_emergency_stopped()})


@app.get("/api/paper/status")
async def api_paper_status():
    listening = is_port_open(port=29979)
    exe_path = detect_paper_executable()
    res = {
        "listening": listening,
        "port": 29979,
        "executable_found": bool(exe_path),
        "executable_path": str(exe_path) if exe_path else "",
        "session_id": "",
        "file_name": "",
        "artboards": 0,
    }
    if listening:
        client = get_paper_client()
        if client:
            try:
                status = client.get_status()
                res.update({
                    "session_id": status.session_id,
                    "file_name": status.file_name,
                    "artboards": status.artboards,
                    "file_open": status.file_open,
                })
            except Exception as e:
                res["message"] = str(e)
    return JSONResponse(content=res)


@app.post("/api/paper/artboard")
async def api_paper_artboard(request: Request):
    data = await request.json()
    name = data.get("name", "Screen")
    w = int(data.get("width", 1440))
    h = int(data.get("height", 900))
    client = get_paper_client()
    if not client or not is_port_open():
        return JSONResponse(content={"status": "error", "message": "Paper Desktop MCP server is offline"}, status_code=503)
    res = client.create_artboard(name=name, width=w, height=h)
    return JSONResponse(content=res)


@app.post("/api/paper/write_html")
async def api_paper_write_html(request: Request):
    data = await request.json()
    html_code = data.get("html", "")
    mode = data.get("mode", "replace")
    client = get_paper_client()
    if not client or not is_port_open():
        return JSONResponse(content={"status": "error", "message": "Paper Desktop MCP server is offline"}, status_code=503)
    res = client.write_html(html=html_code, mode=mode)
    return JSONResponse(content=res)


@app.post("/api/security/mask_pii")
async def api_security_mask_pii(request: Request):
    data = await request.json()
    text = data.get("text", "")
    masked = PIIShield.mask(text)
    entities = PIIShield.detect_entities(text)
    return JSONResponse(content={
        "original_len": len(text),
        "masked_len": len(masked),
        "entities_count": len(entities),
        "entities": entities,
        "masked_text": masked,
        "has_sensitive": len(entities) > 0,
    })


@app.get("/api/rpa/macros")
async def api_rpa_macros():
    recorder = get_rpa_recorder()
    if not recorder:
        return JSONResponse(content={"macros": []})
    macros = recorder.list_recordings()
    return JSONResponse(content={"count": len(macros), "macros": macros, "is_recording": recorder.is_recording, "is_replaying": recorder.is_replaying})


@app.post("/api/rpa/record/start")
async def api_rpa_record_start(request: Request):
    data = await request.json()
    name = data.get("name", f"macro_{int(time.time())}")
    recorder = get_rpa_recorder()
    if not recorder:
        return JSONResponse(content={"status": "error", "message": "RPA recorder unavailable"}, status_code=500)
    res = recorder.start_recording(name)
    return JSONResponse(content=res)


@app.post("/api/rpa/record/stop")
async def api_rpa_record_stop():
    recorder = get_rpa_recorder()
    if not recorder:
        return JSONResponse(content={"status": "error", "message": "RPA recorder unavailable"}, status_code=500)
    res = recorder.stop_recording()
    return JSONResponse(content=res)


@app.post("/api/rpa/replay")
async def api_rpa_replay(request: Request):
    data = await request.json()
    name = data.get("name", "")
    speed = float(data.get("speed", 1.0))
    recorder = get_rpa_recorder()
    if not recorder:
        return JSONResponse(content={"status": "error", "message": "RPA recorder unavailable"}, status_code=500)
    res = recorder.replay(name=name, speed=speed)
    return JSONResponse(content=res)


@app.get("/api/system/health")
async def api_system_health():
    obs = get_system_observer()
    if not obs:
        return JSONResponse(content={"status": "UNKNOWN", "cpu_percent": 0, "ram_percent": 0, "disk_percent": 0})
    health = obs.get_health()
    return JSONResponse(content=health.to_dict())


@app.get("/api/system/briefing")
async def api_system_briefing():
    obs = get_system_observer()
    if not obs:
        return JSONResponse(content={"briefing": "System observer unavailable"})
    briefing = obs.generate_daily_briefing()
    return JSONResponse(content={"briefing": briefing})


@app.get("/api/browser/status")
async def api_browser_status():
    ext_dir = os.path.join(os.path.dirname(__file__), "..", "browser_extension", "hermes_browser_control")
    exists = os.path.exists(ext_dir)
    return JSONResponse(content={
        "installed": exists,
        "path": os.path.abspath(ext_dir) if exists else "",
        "version": "1.0.0",
        "manifest_version": 3,
        "capabilities": [
            "Real-session cookie & auth reuse",
            "Bypasses Cloudflare / Turnstile bot challenge pages",
            "Sub-50ms DOM interactive element extraction",
            "Autonomous CAPTCHA & gate detection",
        ]
    })


# ── SMART SHUTDOWN API ──────────────────────────────────────────────────────

@app.get("/api/shutdown/status")
async def api_shutdown_status():
    mon = get_smart_shutdown_monitor()
    return JSONResponse(content=mon.snapshot() if mon else {"running": False, "status": "UNAVAILABLE"})


@app.post("/api/shutdown/start")
async def api_shutdown_start(request: Request):
    mon = get_smart_shutdown_monitor()
    if not mon:
        return JSONResponse(content={"status": "error", "message": "Smart shutdown unavailable"}, status_code=500)
    data = await request.json()
    cfg = SmartShutdownConfig(
        idle_minutes=int(data.get("idle_minutes", 2)),
        idle_kbps=float(data.get("idle_kbps", 35.0)),
        active_kbps=float(data.get("active_kbps", 150.0)),
        action=str(data.get("action", "shutdown")).lower(),
        countdown_seconds=int(data.get("countdown_seconds", 60)),
        require_user_idle_seconds=int(data.get("require_user_idle_seconds", 120)),
    )
    ok, msg = mon.start(cfg)
    return JSONResponse(content={"status": "ok" if ok else "error", "message": msg, "snapshot": mon.snapshot()})


@app.post("/api/shutdown/cancel")
async def api_shutdown_cancel():
    mon = get_smart_shutdown_monitor()
    if not mon:
        return JSONResponse(content={"status": "error", "message": "Smart shutdown unavailable"}, status_code=500)
    ok, msg = mon.cancel()
    return JSONResponse(content={"status": "ok" if ok else "error", "message": msg, "snapshot": mon.snapshot()})


# ── DEAL FINDER API ─────────────────────────────────────────────────────────

@app.post("/api/deals/search")
async def api_deals_search(request: Request):
    data = await request.json()
    query = str(data.get("query", "")).strip()
    vendors = data.get("vendors") or ["amazon", "newegg", "bestbuy", "walmart"]
    max_results = int(data.get("max_results", 6))
    if not query:
        return JSONResponse(content={"count": 0, "deals": []})
    deals = search_deals(query, vendors=vendors, max_results_per_vendor=max_results)
    return JSONResponse(content={"count": len(deals), "deals": [d.to_dict() for d in deals]})


@app.get("/api/deals/watches")
async def api_deals_watches():
    store = get_deal_watch_store()
    watches = store.list_watches() if store else []
    return JSONResponse(content={"count": len(watches), "watches": [w.to_dict() for w in watches]})


@app.post("/api/deals/watches/add")
async def api_deals_watch_add(request: Request):
    data = await request.json()
    query = str(data.get("query", "")).strip()
    target_price = float(data["target_price"]) if data.get("target_price") is not None else None
    vendors = data.get("vendors") or ["amazon", "newegg", "bestbuy", "walmart"]
    interval = int(data.get("interval_minutes", 180))
    store = get_deal_watch_store()
    if not store:
        return JSONResponse(content={"status": "error", "message": "Store unavailable"}, status_code=500)
    watch = store.add_watch(query=query, target_price=target_price, vendors=vendors, interval_minutes=interval)
    return JSONResponse(content={"status": "ok", "watch": watch.to_dict()})


@app.post("/api/deals/watches/remove")
async def api_deals_watch_remove(request: Request):
    data = await request.json()
    watch_id = str(data.get("watch_id", ""))
    store = get_deal_watch_store()
    ok = store.remove_watch(watch_id) if store else False
    return JSONResponse(content={"status": "ok" if ok else "not_found"})


@app.post("/api/deals/watches/check")
async def api_deals_watch_check(request: Request):
    data = await request.json()
    watch_id = str(data.get("watch_id", ""))
    store = get_deal_watch_store()
    res = store.check_watch(watch_id) if store else None
    if not res:
        return JSONResponse(content={"status": "not_found"}, status_code=404)
    return JSONResponse(content={"status": "ok", **res})


# ── MULTI-CHANNEL GATEWAYS API ──────────────────────────────────────────────

@app.get("/api/channels/status")
async def api_channels_status():
    return JSONResponse(content=get_all_channel_statuses())


@app.post("/api/channels/pair")
async def api_channels_pair(request: Request):
    data = await request.json()
    channel = str(data.get("channel", "")).strip().lower()
    code = str(data.get("code", "")).strip()
    policy = get_channel_policy_manager()
    user_id = policy.approve_pairing_code(channel, code) if policy else None
    if user_id:
        return JSONResponse(content={"status": "ok", "message": f"Approved {channel} user {user_id}", "user_id": user_id})
    return JSONResponse(content={"status": "error", "message": "Invalid or expired pairing code"}, status_code=400)


@app.post("/api/channels/allowlist/add")
async def api_channels_allowlist_add(request: Request):
    data = await request.json()
    channel = str(data.get("channel", "")).strip().lower()
    user_id = str(data.get("user_id", "")).strip()
    policy = get_channel_policy_manager()
    if policy and channel and user_id:
        policy.add_to_allowlist(channel, user_id)
        return JSONResponse(content={"status": "ok", "allowlist": policy.get_summary().get(channel, {}).get("allowed_users", [])})
    return JSONResponse(content={"status": "bad_request"}, status_code=400)


@app.post("/api/channels/simulate_test")
async def api_channels_simulate_test(request: Request):
    data = await request.json()
    channel = str(data.get("channel", "web")).strip().lower()
    prompt = str(data.get("prompt", "")).strip()
    user_id = str(data.get("user_id", "test_user"))
    if not prompt:
        return JSONResponse(content={"status": "error", "message": "Empty prompt"}, status_code=400)
    if default_channel_dispatcher:
        resp = await default_channel_dispatcher(prompt, channel=channel, user_id=user_id)
        return JSONResponse(content={"status": "ok", "response": resp, "channel": channel})
    return JSONResponse(content={"status": "error", "message": "Dispatcher unavailable"}, status_code=500)


# ── OMNI-MESH CROSS-DEVICE API & PWA ────────────────────────────────────────

@app.get("/companion", response_class=HTMLResponse)
async def get_companion_page():
    hub = get_omni_mesh_hub()
    ip = hub.lan_ip if hub else "127.0.0.1"
    port = hub.port if hub else 8000
    return HTMLResponse(content=render_companion_html(ip, port))


@app.get("/companion/manifest.json")
async def get_companion_manifest():
    return JSONResponse(content=MANIFEST_JSON)


@app.get("/companion/sw.js")
async def get_companion_sw():
    from fastapi import Response
    return Response(content=SERVICE_WORKER_JS, media_type="application/javascript")


@app.websocket("/api/mesh/ws")
async def websocket_mesh_endpoint(websocket: WebSocket):
    hub = get_omni_mesh_hub()
    if not hub:
        await websocket.close()
        return
    client_ip = websocket.client.host if websocket.client else "127.0.0.1"
    device = None
    try:
        await websocket.accept()
        raw = await websocket.receive_text()
        try:
            init_data = json.loads(raw)
        except Exception:
            init_data = {}
        import uuid
        dev_id = str(init_data.get("device_id") or str(uuid.uuid4())[:8])
        device = await hub.register_connection(
            websocket=websocket,
            device_id=dev_id,
            name=init_data.get("name", "Companion"),
            device_type=init_data.get("device_type", "phone"),
            client_ip=client_ip,
            user_agent=init_data.get("user_agent", ""),
            battery=init_data.get("battery"),
            is_charging=init_data.get("is_charging"),
            skip_accept=True,
        )
        while True:
            msg_text = await websocket.receive_text()
            data = json.loads(msg_text)
            await hub.handle_inbound_message(device.device_id, data)
    except WebSocketDisconnect:
        if device and hub:
            await hub.unregister_connection(device.device_id)
    except Exception as exc:
        logger.debug(f"Mesh WebSocket disconnected/error: {exc}")
        if device and hub:
            await hub.unregister_connection(device.device_id)


@app.get("/api/mesh/status")
async def api_mesh_status():
    hub = get_omni_mesh_hub()
    return JSONResponse(content=hub.get_status_overview() if hub else {"status": "disabled"})


@app.post("/api/mesh/notify")
async def api_mesh_notify(request: Request):
    data = await request.json()
    title = str(data.get("title", "Hermes Alert"))
    body = str(data.get("body", "Notification from PC"))
    vibrate = bool(data.get("vibrate", True))
    device_id = data.get("device_id")
    hub = get_omni_mesh_hub()
    if hub:
        if device_id:
            await hub.send_to_device(device_id, {
                "type": "notification",
                "title": title,
                "body": body,
                "vibrate": [150, 80, 150] if vibrate else [],
            })
        else:
            hub.notify_all(title, body, vibrate=vibrate)
        return JSONResponse(content={"status": "sent"})
    return JSONResponse(content={"status": "error", "message": "Hub unavailable"}, status_code=500)


@app.post("/api/mesh/clipboard/push")
async def api_mesh_clipboard_push(request: Request):
    data = await request.json()
    text = str(data.get("text", ""))
    write_pc_clipboard(text)
    hub = get_omni_mesh_hub()
    if hub:
        await hub.broadcast_event({
            "type": "clipboard_update",
            "content": text,
            "from_device": "desktop-host",
        })
    return JSONResponse(content={"status": "ok", "synced": text})


@app.get("/api/mesh/clipboard/get")
async def api_mesh_clipboard_get():
    return JSONResponse(content={"clipboard": read_pc_clipboard()})


# ==============================================================================
# MAIN DASHBOARD UI
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
def dashboard():
    tasks = get_tasks()

    import importlib
    importlib.reload(role_registry)
    current_roles = role_registry.ROLES

    num_roles = len(current_roles)
    num_tasks = len(tasks)

    # Initial probe for stats
    paper_online = is_port_open(port=29979)
    stopped_state = is_emergency_stopped()
    monitors_list = get_display_monitors()
    num_monitors = len(monitors_list)
    windows_list = list_active_windows()
    num_windows = len(windows_list)

    obs = get_system_observer()
    health_data = obs.get_health().to_dict() if obs else {"cpu_percent": 0.0, "ram_percent": 0.0}

    # Turnkey module states
    shutdown_mon = get_smart_shutdown_monitor()
    shutdown_snap = shutdown_mon.snapshot() if shutdown_mon else {"running": False, "status": "INACTIVE"}
    watch_store = get_deal_watch_store()
    num_watches = len(watch_store.list_watches()) if watch_store else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Hermes Operations Center</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {{
            --bg-canvas: #041411;
            --bg-card: #061e19;
            --bg-card-alt: #082620;
            --bg-input: #020d0b;
            --border-subtle: #0d3830;
            --border-bright: #1c6153;
            --text-heading: #f6e6a1;
            --text-main: #d3f3e3;
            --text-muted: #719f8e;
            --accent-green: #34d399;
            --accent-gold: #fbbf24;
            --accent-red: #f87171;
            --accent-blue: #38bdf8;
            --btn-bg: #0b332b;
            --btn-hover: #124b3f;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg-canvas);
            color: var(--text-main);
            padding: 20px 28px 60px;
            font-size: 13px;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}

        ::-webkit-scrollbar {{
            width: 6px;
            height: 6px;
        }}
        ::-webkit-scrollbar-track {{
            background: transparent;
        }}
        ::-webkit-scrollbar-thumb {{
            background: var(--border-subtle);
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--border-bright);
        }}

        /* TOP STATS BAR */
        .stats-bar {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 12px;
            margin-bottom: 22px;
        }}

        .stat-widget {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
            padding: 12px 14px;
            display: flex;
            align-items: center;
            gap: 12px;
            position: relative;
            overflow: hidden;
        }}

        .stat-widget::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, transparent, var(--border-bright), transparent);
        }}

        .stat-icon {{
            font-size: 20px;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
        }}

        .stat-meta {{
            display: flex;
            flex-direction: column;
        }}

        .stat-label {{
            font-size: 10px;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--text-muted);
            font-weight: 600;
        }}

        .stat-val {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-heading);
            margin-top: 2px;
        }}

        /* NAVIGATION TABS HEADER */
        .nav-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-subtle);
            padding-bottom: 14px;
            margin-bottom: 22px;
            flex-wrap: wrap;
            gap: 14px;
        }}

        .nav-title-group {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .nav-badge {{
            background: rgba(52, 211, 153, 0.12);
            color: var(--accent-green);
            border: 1px solid rgba(52, 211, 153, 0.3);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.08em;
        }}

        .section-title {{
            color: var(--text-heading);
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        .tab-controls {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            background: var(--bg-card);
            padding: 4px;
            border-radius: 6px;
            border: 1px solid var(--border-subtle);
        }}

        .tab-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .tab-btn:hover {{
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.03);
        }}

        .tab-btn.active {{
            background: var(--btn-bg);
            color: var(--text-heading);
            border: 1px solid var(--border-bright);
        }}

        .tab-panel {{
            display: none;
            animation: fadeIn 0.15s ease;
        }}

        .tab-panel.active {{
            display: block;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* BUTTONS & CONTROLS */
        .btn-action {{
            background: var(--btn-bg);
            border: 1px solid var(--border-subtle);
            color: var(--text-heading);
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}

        .btn-action:hover {{
            background: var(--btn-hover);
            border-color: var(--border-bright);
        }}

        .btn-danger {{
            background: rgba(248, 113, 113, 0.15);
            border-color: rgba(248, 113, 113, 0.35);
            color: #fca5a5;
        }}

        .btn-danger:hover {{
            background: rgba(248, 113, 113, 0.3);
            border-color: var(--accent-red);
        }}

        /* EMPLOYEE CARDS GRID */
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 18px;
        }}

        .employee-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            transition: transform 0.15s ease, border-color 0.15s ease;
        }}

        .employee-card:hover {{
            border-color: var(--border-bright);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
        }}

        .card-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}

        .role-identity {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .role-avatar {{
            font-size: 24px;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            width: 44px;
            height: 44px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .role-details {{
            display: flex;
            flex-direction: column;
        }}

        .role-badge-row {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .role-name {{
            color: var(--text-heading);
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 0.05em;
        }}

        .role-subhead {{
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 1px;
        }}

        .status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 3px 8px;
            border-radius: 9999px;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            background: rgba(52, 211, 153, 0.12);
            color: var(--accent-green);
            border: 1px solid rgba(52, 211, 153, 0.25);
        }}

        .pulse-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: var(--accent-green);
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0% {{ opacity: 0.4; transform: scale(0.9); }}
            50% {{ opacity: 1; transform: scale(1.1); }}
            100% {{ opacity: 0.4; transform: scale(0.9); }}
        }}

        .roster-section {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 10px 12px;
        }}

        .roster-title-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 10px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
            font-weight: 600;
        }}

        .chain-flow {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px;
        }}

        .chain-node {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-family: ui-monospace, SFMono-Regular, monospace;
            color: var(--text-main);
        }}

        .node-idx {{
            color: var(--text-heading);
            font-weight: 700;
            font-size: 10px;
        }}

        .node-quota {{
            font-size: 9px;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.05);
            padding: 1px 4px;
            border-radius: 3px;
        }}

        .chain-arrow {{
            color: var(--text-muted);
        }}

        .soul-container {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .soul-header {{
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
            font-weight: 600;
        }}

        .soul-box {{
            width: 100%;
            height: 90px;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 10px;
            color: var(--text-main);
            font-family: ui-monospace, SFMono-Regular, monospace;
            font-size: 11px;
            resize: vertical;
            outline: none;
            line-height: 1.4;
        }}

        .soul-box:focus {{
            border-color: var(--border-bright);
        }}

        .action-row {{
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 10px;
        }}

        .btn-save {{
            background: var(--btn-bg);
            border: 1px solid var(--border-subtle);
            color: var(--text-heading);
            padding: 5px 12px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .btn-save:hover {{
            background: var(--btn-hover);
            border-color: var(--border-bright);
        }}

        .save-indicator {{
            color: var(--accent-green);
            font-size: 11px;
            opacity: 0;
            transition: opacity 0.2s ease;
        }}

        .save-indicator.visible {{
            opacity: 1;
        }}

        /* ACCORDION ACTIVITY LOGS */
        .emp-logs-accordion {{
            border-top: 1px solid var(--border-subtle);
            padding-top: 10px;
        }}

        .btn-toggle-logs {{
            width: 100%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            color: var(--text-muted);
            padding: 7px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .btn-toggle-logs:hover {{
            color: var(--text-main);
            border-color: var(--border-bright);
        }}

        .emp-logs-panel {{
            margin-top: 8px;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            max-height: 220px;
            overflow-y: auto;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .emp-log-item {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 4px;
            padding: 8px;
            font-size: 11px;
        }}

        .emp-log-top {{
            display: flex;
            justify-content: space-between;
            color: var(--text-muted);
            font-size: 10px;
            margin-bottom: 4px;
        }}

        .emp-log-task {{
            color: var(--text-heading);
            margin-bottom: 4px;
        }}

        .emp-log-resp {{
            color: var(--text-main);
            white-space: pre-wrap;
            font-family: ui-monospace, monospace;
            font-size: 10px;
            max-height: 80px;
            overflow-y: auto;
            background: var(--bg-canvas);
            padding: 6px;
            border-radius: 4px;
        }}

        /* GENERIC TABLES & DATA CONTAINERS */
        .panel-container {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}

        .panel-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-subtle);
        }}

        .panel-title {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-heading);
            letter-spacing: 0.05em;
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .panel-desc {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 2px;
        }}

        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}

        .data-table th {{
            text-align: left;
            padding: 10px 12px;
            color: var(--text-muted);
            font-size: 10px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            border-bottom: 1px solid var(--border-subtle);
            background: var(--bg-input);
        }}

        .data-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-subtle);
            color: var(--text-main);
        }}

        .data-table tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}

        /* FORMS & INPUTS */
        .input-text, .input-select, .input-textarea {{
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 4px;
            padding: 8px 12px;
            color: var(--text-main);
            font-size: 12px;
            outline: none;
        }}

        .input-text:focus, .input-select:focus, .input-textarea:focus {{
            border-color: var(--border-bright);
        }}

        /* LOG AUDIT TRAIL */
        .filter-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            gap: 14px;
            flex-wrap: wrap;
        }}

        .filter-chips {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}

        .chip {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            color: var(--text-muted);
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .chip:hover {{
            color: var(--text-main);
            border-color: var(--border-bright);
        }}

        .chip.active {{
            background: var(--btn-bg);
            color: var(--text-heading);
            border-color: var(--border-bright);
        }}

        .search-input {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 7px 12px;
            color: var(--text-main);
            font-size: 12px;
            width: 260px;
            outline: none;
        }}

        .search-input:focus {{
            border-color: var(--border-bright);
        }}

        .logs-stream {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .log-entry {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 14px 18px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .log-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-subtle);
            padding-bottom: 8px;
        }}

        .log-role-tag {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-weight: 700;
            color: var(--text-heading);
            font-size: 12px;
        }}

        .log-metrics {{
            font-size: 11px;
            color: var(--text-muted);
            display: flex;
            gap: 10px;
        }}

        .log-prompt {{
            font-size: 12px;
            color: var(--text-main);
        }}

        .log-output {{
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 4px;
            padding: 10px 12px;
            font-family: ui-monospace, SFMono-Regular, monospace;
            font-size: 11px;
            white-space: pre-wrap;
            max-height: 180px;
            overflow-y: auto;
            color: #bbf7d0;
        }}

        /* TOAST NOTIFICATION */
        #toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--bg-card-alt);
            border: 1px solid var(--border-bright);
            color: var(--text-heading);
            padding: 12px 20px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.25s ease;
            z-index: 9999;
        }}

        #toast.show {{
            transform: translateY(0);
            opacity: 1;
        }}
    </style>
</head>
<body>

    <!-- TOP SYSTEM STATS BAR -->
    <div class="stats-bar">
        <div class="stat-widget">
            <div class="stat-icon">👥</div>
            <div class="stat-meta">
                <span class="stat-label">Agents</span>
                <span class="stat-val">{num_roles} Roles</span>
            </div>
        </div>

        <div class="stat-widget">
            <div class="stat-icon">🖥️</div>
            <div class="stat-meta">
                <span class="stat-label">Monitors & Windows</span>
                <span class="stat-val">{num_monitors} Mon &bull; {num_windows} Win</span>
            </div>
        </div>

        <div class="stat-widget">
            <div class="stat-icon">🎨</div>
            <div class="stat-meta">
                <span class="stat-label">Paper MCP</span>
                <span class="stat-val" style="color: {'var(--accent-green)' if paper_online else 'var(--text-muted)'};">
                    {'ONLINE' if paper_online else 'STANDBY'}
                </span>
            </div>
        </div>

        <div class="stat-widget">
            <div class="stat-icon">🌙</div>
            <div class="stat-meta">
                <span class="stat-label">Smart Power</span>
                <span class="stat-val" id="top-stat-shutdown" style="color: {'var(--accent-gold)' if shutdown_snap.get('running') else 'var(--text-muted)'};">
                    {shutdown_snap.get('status', 'INACTIVE')}
                </span>
            </div>
        </div>

        <div class="stat-widget">
            <div class="stat-icon">🛍️</div>
            <div class="stat-meta">
                <span class="stat-label">Deal Watches</span>
                <span class="stat-val" id="top-stat-watches">{num_watches} Active</span>
            </div>
        </div>

        <div class="stat-widget">
            <div class="stat-icon">🔒</div>
            <div class="stat-meta">
                <span class="stat-label">PII Shield</span>
                <span class="stat-val" style="color: var(--accent-green);">ARMED</span>
            </div>
        </div>

        <div class="stat-widget">
            <div class="stat-icon">📱</div>
            <div class="stat-meta">
                <span class="stat-label">Omni-Mesh</span>
                <span class="stat-val" id="top-stat-mesh" style="color: var(--accent-green);">CONNECTED</span>
            </div>
        </div>

        <div class="stat-widget">
            <div class="stat-icon">🚨</div>
            <div class="stat-meta">
                <span class="stat-label">Panic Stop</span>
                <span class="stat-val" id="top-stat-stop" style="color: {'var(--accent-red)' if stopped_state else 'var(--accent-green)'};">
                    {'STOPPED' if stopped_state else 'READY'}
                </span>
            </div>
        </div>
    </div>

    <!-- TABS NAVIGATION HEADER -->
    <div class="nav-header">
        <div class="nav-title-group">
            <div class="nav-badge">HERMES 1.0</div>
            <h1 class="section-title">Autonomous Operations Center</h1>
        </div>
        <div class="tab-controls">
            <button class="tab-btn active" onclick="setTab('roster')">👥 Team Roster</button>
            <button class="tab-btn" onclick="setTab('desktop')">🖥️ Desktop & Monitors</button>
            <button class="tab-btn" onclick="setTab('paper')">🎨 Paper MCP Studio</button>
            <button class="tab-btn" onclick="setTab('shutdown')">🌙 Smart Shutdown</button>
            <button class="tab-btn" onclick="setTab('deals')">🛍️ Deal Finder</button>
            <button class="tab-btn" onclick="setTab('channels')">💬 Multi-Channel</button>
            <button class="tab-btn" onclick="setTab('mesh')">📱 Omni-Mesh</button>
            <button class="tab-btn" onclick="setTab('security')">🔒 PII Shield</button>
            <button class="tab-btn" onclick="setTab('rpa')">🤖 RPA Studio</button>
            <button class="tab-btn" onclick="setTab('system')">⚡ System Health</button>
            <button class="tab-btn" onclick="setTab('browser')">🌐 Browser Extension</button>
            <button class="tab-btn" onclick="setTab('logs')">📜 Audit Trail</button>
        </div>
    </div>

    <!-- TAB 1: TEAM ROSTER -->
    <div id="tab-roster" class="tab-panel active">
        <div class="cards-grid">
"""

    for role_name, data in current_roles.items():
        soul = data.get("soul", "")
        models = data.get("models", [])
        meta = ROLE_META.get(role_name, {
            "icon": "🤖",
            "title": f"{role_name} Agent",
            "desc": "Autonomous specialist",
            "color": "#38bdf8"
        })

        nodes_html = []
        for i, m in enumerate(models):
            nodes_html.append(f"""
                <div class="chain-node">
                    <span class="node-idx">#{i+1}</span>
                    <span>{m['name']}</span>
                    <span class="node-quota">{m['quota']}</span>
                </div>
            """)

        chain_html = ' <span class="chain-arrow">&rarr;</span> '.join(nodes_html)

        html += f"""
            <div class="employee-card">
                <div class="card-top">
                    <div class="role-identity">
                        <div class="role-avatar">{meta['icon']}</div>
                        <div class="role-details">
                            <div class="role-badge-row">
                                <span class="role-name">{role_name}</span>
                            </div>
                            <span class="role-subhead">{meta['title']}</span>
                        </div>
                    </div>
                    <div class="status-pill">
                        <div class="pulse-dot"></div>
                        <span>ONLINE</span>
                    </div>
                </div>

                <div class="roster-section">
                    <div class="roster-title-row">
                        <span>Model Failover Cascade</span>
                        <span>Auto-Failover</span>
                    </div>
                    <div class="chain-flow">
                        {chain_html}
                    </div>
                </div>

                <div class="soul-container">
                    <div class="soul-header">
                        <span>Soul Directives & Memory</span>
                        <span>Auto-Synchronized</span>
                    </div>
                    <textarea id="soul-{role_name}" class="soul-box">{soul}</textarea>
                    <div class="action-row">
                        <span id="saved-{role_name}" class="save-indicator">&check; Updated!</span>
                        <button class="btn-save" onclick="updateSoul('{role_name}')">Save Directives</button>
                    </div>
                </div>

                <div class="emp-logs-accordion">
                    <button class="btn-toggle-logs" onclick="toggleEmpLogs('{role_name}')">
                        <span>📜 Activity Log ({len(get_employee_logs(role_name))})</span>
                        <span id="arrow-{role_name}">▼</span>
                    </button>
                    <div id="logs-{role_name}" class="emp-logs-panel" style="display: none;">
        """

        emp_logs = get_employee_logs(role_name)
        if emp_logs:
            for item in emp_logs[:10]:
                ts = item.get("timestamp", "")[:19].replace("T", " ")
                lat = item.get("latency_ms", 0)
                mdl = item.get("model", "")
                tsk = item.get("task", "")
                rsp = item.get("response", "")
                html += f"""
                        <div class="emp-log-item">
                            <div class="emp-log-top">
                                <span>{ts}</span>
                                <span style="color: var(--accent-green);">{lat}ms &bull; {mdl}</span>
                            </div>
                            <div class="emp-log-task"><strong>Task:</strong> {tsk}</div>
                            <div class="emp-log-resp">{rsp}</div>
                        </div>
                """
        else:
            html += f"""
                        <div class="emp-log-item" style="color: var(--text-muted); text-align: center; padding: 12px;">
                            No tasks recorded yet for {role_name}. Dispatched actions will appear here.
                        </div>
            """

        html += f"""
                    </div>
                </div>
            </div>
        """

    html += """
        </div>
    </div>

    <!-- TAB 2: DESKTOP & MONITORS -->
    <div id="tab-desktop" class="tab-panel">
        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">🖥️ Physical Display Monitors</h2>
                    <p class="panel-desc">Real-time coordinate systems and work areas across your connected displays.</p>
                </div>
                <button class="btn-action" onclick="refreshDesktop()">&circlearrowright; Refresh Displays</button>
            </div>
            <div id="monitors-cards-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px;">
    """

    for m in monitors_list:
        html += f"""
                <div style="background: var(--bg-input); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 14px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <span style="font-weight: 700; color: var(--text-heading);">Display {m.id} {'(Primary)' if m.is_primary else ''}</span>
                        <span style="font-size: 10px; color: var(--accent-green); font-weight: 600;">ACTIVE</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted);">
                        <div>Device: {m.device}</div>
                        <div>Resolution: <strong>{m.width} x {m.height}</strong></div>
                        <div>Work Area: {m.work_area[0]}, {m.work_area[1]} to {m.work_area[2]}, {m.work_area[3]}</div>
                    </div>
                </div>
        """

    html += """
            </div>
        </div>

        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">🚨 Desktop Hotkeys & Safety Kill-Switch</h2>
                    <p class="panel-desc">Win32 background daemon global shortcuts and emergency override.</p>
                </div>
                <div>
                    <button id="btn-toggle-panic" class="btn-action btn-danger" onclick="toggleEmergencyStop()">
                        🚨 ENGAGE EMERGENCY PANIC STOP
                    </button>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px;">
                <div style="background: var(--bg-input); padding: 12px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-weight: 700; color: var(--text-heading); font-size: 12px; margin-bottom: 4px;">Ctrl + Alt + Space</div>
                    <div style="font-size: 11px; color: var(--text-muted);">Global Summon: Instantly raises Hermes prompt bar from any active game, IDE, or app.</div>
                </div>
                <div style="background: var(--bg-input); padding: 12px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-weight: 700; color: var(--text-heading); font-size: 12px; margin-bottom: 4px;">Ctrl + Alt + C</div>
                    <div style="font-size: 11px; color: var(--text-muted);">Selected-Text Assist: Copies highlighted text in any window and sends directly to Hermes.</div>
                </div>
                <div style="background: var(--bg-input); padding: 12px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-weight: 700; color: var(--accent-red); font-size: 12px; margin-bottom: 4px;">Ctrl + Esc</div>
                    <div style="font-size: 11px; color: var(--text-muted);">Emergency Panic Stop: Instantly freezes all mouse/keyboard automated actions across Windows.</div>
                </div>
            </div>
        </div>

        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">🪟 Real User Windows & One-Click Snapping</h2>
                    <p class="panel-desc">Clean list of active applications (system noise filtered out). Snap or move across monitors instantly.</p>
                </div>
                <button class="btn-action" onclick="refreshWindows()">&circlearrowright; Refresh Windows</button>
            </div>
            <div style="overflow-x: auto;">
                <table class="data-table" id="windows-table">
                    <thead>
                        <tr>
                            <th>HWND</th>
                            <th>Window Title</th>
                            <th>Status</th>
                            <th>Monitor</th>
                            <th>Coordinates</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="windows-tbody">
    """

    for w in windows_list[:25]:
        hwnd = w.get("hwnd", 0) if isinstance(w, dict) else getattr(w, "hwnd", 0)
        title = w.get("title", "") if isinstance(w, dict) else getattr(w, "title", "")
        mon = w.get("monitor_id", 1) if isinstance(w, dict) else getattr(w, "monitor_id", 1)
        rect = w.get("rect", (0, 0, 0, 0)) if isinstance(w, dict) else getattr(w, "rect", (0, 0, 0, 0))
        wx = rect[0] if len(rect) > 0 else 0
        wy = rect[1] if len(rect) > 1 else 0
        ww = rect[2] if len(rect) > 2 else 0
        wh = rect[3] if len(rect) > 3 else 0

        html += f"""
                        <tr>
                            <td>{hwnd}</td>
                            <td style="font-weight: 600; color: var(--text-heading); max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                {title}
                            </td>
                            <td>Active Window</td>
                            <td>Monitor {mon}</td>
                            <td style="font-family: monospace; font-size: 11px;">{ww}x{wh} @ ({wx},{wy})</td>
                            <td>
                                <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                                    <button class="btn-action" style="padding: 3px 6px; font-size: 10px;" onclick="snapWin('{hwnd}', 'left')">◧ Left</button>
                                    <button class="btn-action" style="padding: 3px 6px; font-size: 10px;" onclick="snapWin('{hwnd}', 'right')">◨ Right</button>
                                    <button class="btn-action" style="padding: 3px 6px; font-size: 10px;" onclick="snapWin('{hwnd}', 'maximize')">🗖 Max</button>
                                    <button class="btn-action" style="padding: 3px 6px; font-size: 10px;" onclick="moveWin('{hwnd}', 2)">To Mon 2</button>
                                </div>
                            </td>
                        </tr>
        """

    html += """
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- TAB 3: PAPER MCP STUDIO -->
    <div id="tab-paper" class="tab-panel">
        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">🎨 Paper Desktop MCP Studio</h2>
                    <p class="panel-desc">Autonomous visual design, artboards, and HTML-to-Canvas rendering on port 29979.</p>
                </div>
                <button class="btn-action" onclick="checkPaperStatus()">&circlearrowright; Refresh Status</button>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-bottom: 18px;">
                <div style="background: var(--bg-input); padding: 14px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Paper Protocol Handshake</div>
                    <div style="font-size: 14px; font-weight: 700; color: var(--text-heading); margin-top: 4px;">MCP Spec 2024-11-05</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Local Endpoint: <code>http://127.0.0.1:29979/mcp</code></div>
                </div>
                <div style="background: var(--bg-input); padding: 14px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Available Tools</div>
                    <div style="font-size: 14px; font-weight: 700; color: var(--accent-green); margin-top: 4px;">36 Autonomous MCP Tools</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Includes write_html, create_artboard, get_screenshot</div>
                </div>
                <div style="background: var(--bg-input); padding: 14px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Design Loop Policy</div>
                    <div style="font-size: 14px; font-weight: 700; color: var(--accent-gold); margin-top: 4px;">Autonomous Critique Loop</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Read &bull; Plan &bull; 1-3 Edits &bull; Screenshot &bull; Critique</div>
                </div>
            </div>

            <!-- ARTBOARD GENERATOR -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <h3 style="font-size: 13px; color: var(--text-heading); margin-bottom: 12px;">📐 Create Design Artboard</h3>
                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <div>
                            <label style="font-size: 11px; color: var(--text-muted);">Artboard Name</label>
                            <input type="text" id="paper-artboard-name" class="input-text" style="width: 100%; margin-top: 4px;" value="Executive Operations Dashboard" />
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <div>
                                <label style="font-size: 11px; color: var(--text-muted);">Width (px)</label>
                                <input type="number" id="paper-artboard-w" class="input-text" style="width: 100%; margin-top: 4px;" value="1440" />
                            </div>
                            <div>
                                <label style="font-size: 11px; color: var(--text-muted);">Height (px)</label>
                                <input type="number" id="paper-artboard-h" class="input-text" style="width: 100%; margin-top: 4px;" value="900" />
                            </div>
                        </div>
                        <div style="margin-top: 8px;">
                            <button class="btn-action" onclick="createPaperArtboard()">🚀 Create Artboard in Paper</button>
                        </div>
                    </div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <h3 style="font-size: 13px; color: var(--text-heading); margin-bottom: 12px;">💻 Write HTML to Canvas</h3>
                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <div>
                            <label style="font-size: 11px; color: var(--text-muted);">HTML Code / Design Element</label>
                            <textarea id="paper-html-code" class="input-textarea" style="width: 100%; height: 95px; margin-top: 4px; font-family: monospace;" placeholder="<div style='background: #111; color: white; padding: 24px; border-radius: 8px;'><h1>Enterprise Hero Screen</h1></div>"></textarea>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                            <select id="paper-html-mode" class="input-select">
                                <option value="replace">Mode: Replace</option>
                                <option value="append">Mode: Append</option>
                            </select>
                            <button class="btn-action" onclick="writePaperHtml()">✨ Render HTML on Canvas</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- TAB 4: SMART SHUTDOWN -->
    <div id="tab-shutdown" class="tab-panel">
        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">🌙 Smart Network-Idle Shutdown & Sleep</h2>
                    <p class="panel-desc">Monitors ongoing downloads and batch jobs. Safely powers down or puts the PC to sleep after completion.</p>
                </div>
                <button class="btn-action" onclick="refreshShutdownStatus()">&circlearrowright; Refresh Status</button>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; margin-bottom: 20px;">
                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Current Throughput</div>
                    <div id="sd-rate-val" style="font-size: 22px; font-weight: 700; color: var(--accent-green); margin-top: 4px;">0 KB/s</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Network Inbound Rate</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Monitor State</div>
                    <div id="sd-status-val" style="font-size: 22px; font-weight: 700; color: var(--text-heading); margin-top: 4px;">INACTIVE</div>
                    <div id="sd-state-sub" style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Ready to configure</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Idle Duration</div>
                    <div id="sd-idle-val" style="font-size: 22px; font-weight: 700; color: var(--text-heading); margin-top: 4px;">0s / 120s</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Low-traffic accumulation</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Safety Safeguards</div>
                    <div style="font-size: 14px; font-weight: 700; color: var(--accent-green); margin-top: 4px;">Active User Guard</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Won't sleep while you type / click</div>
                </div>
            </div>

            <!-- CONFIGURATION & CONTROLS -->
            <div style="background: var(--bg-input); padding: 18px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                <h3 style="font-size: 13px; color: var(--text-heading); margin-bottom: 12px;">⚙️ Configure Smart Power Policy</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="font-size: 11px; color: var(--text-muted);">Action on Idle</label>
                        <select id="sd-action" class="input-select" style="width: 100%; margin-top: 4px;">
                            <option value="shutdown">Shutdown PC</option>
                            <option value="sleep">Put PC to Sleep</option>
                            <option value="hibernate">Hibernate PC</option>
                        </select>
                    </div>

                    <div>
                        <label style="font-size: 11px; color: var(--text-muted);">Idle Minutes Required</label>
                        <input type="number" id="sd-idle-min" class="input-text" style="width: 100%; margin-top: 4px;" value="2" min="1" max="60" />
                    </div>

                    <div>
                        <label style="font-size: 11px; color: var(--text-muted);">Low Throughput Cutoff (KB/s)</label>
                        <input type="number" id="sd-idle-kbps" class="input-text" style="width: 100%; margin-top: 4px;" value="35" min="5" max="2000" />
                    </div>

                    <div>
                        <label style="font-size: 11px; color: var(--text-muted);">Active Download Min (KB/s)</label>
                        <input type="number" id="sd-active-kbps" class="input-text" style="width: 100%; margin-top: 4px;" value="150" min="20" max="20000" />
                    </div>
                </div>

                <div style="display: flex; gap: 12px; align-items: center;">
                    <button id="btn-sd-start" class="btn-action" onclick="startShutdownMonitor()">🚀 Engage Smart Shutdown</button>
                    <button id="btn-sd-cancel" class="btn-action btn-danger" style="display: none;" onclick="cancelShutdownMonitor()">⏹️ Abort / Cancel</button>
                    <span id="sd-msg-banner" style="font-size: 11px; color: var(--text-muted);">Configure parameters above and click Engage.</span>
                </div>
            </div>
        </div>
    </div>

    <!-- TAB 5: DEAL FINDER & WATCHLIST -->
    <div id="tab-deals" class="tab-panel">
        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">🛍️ Multi-Vendor Deal Finder & Price Drop Tracker</h2>
                    <p class="panel-desc">Scrapes and cross-references live prices across Amazon, Newegg, Best Buy, Walmart, B&H Photo, and Micro Center without browser overhead.</p>
                </div>
                <div class="status-pill">
                    <div class="pulse-dot"></div>
                    <span>READ-ONLY SAFEGUARD ACTIVE</span>
                </div>
            </div>

            <!-- SEARCH BAR -->
            <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle); margin-bottom: 20px;">
                <div style="display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap;">
                    <input type="text" id="deal-search-query" class="input-text" placeholder="Search product (e.g. 2TB NVMe Gen4 SSD, RTX 4070 Super)..." style="flex: 1; min-width: 260px;" />
                    <button class="btn-action" onclick="executeDealSearch()">🔍 Search Deals</button>
                </div>
                <div style="display: flex; gap: 14px; font-size: 11px; color: var(--text-muted); flex-wrap: wrap;">
                    <span>Include:</span>
                    <label><input type="checkbox" id="v-amazon" checked /> Amazon</label>
                    <label><input type="checkbox" id="v-newegg" checked /> Newegg</label>
                    <label><input type="checkbox" id="v-bestbuy" checked /> Best Buy</label>
                    <label><input type="checkbox" id="v-walmart" checked /> Walmart</label>
                    <label><input type="checkbox" id="v-bhphoto" checked /> B&H Photo</label>
                    <label><input type="checkbox" id="v-microcenter" checked /> Micro Center</label>
                </div>
            </div>

            <!-- SEARCH RESULTS TABLE -->
            <div style="margin-bottom: 24px;">
                <h3 style="font-size: 13px; color: var(--text-heading); margin-bottom: 10px;">Live Price Comparison (Sorted by Best Price)</h3>
                <div style="overflow-x: auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Vendor</th>
                                <th>Item Title</th>
                                <th>Item Price</th>
                                <th>Shipping</th>
                                <th>Best Total</th>
                                <th>Link</th>
                            </tr>
                        </thead>
                        <tbody id="deals-results-tbody">
                            <tr>
                                <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 18px;">
                                    Type a product query above and click "Search Deals" to compare prices across vendors.
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- WATCHLIST MANAGER -->
            <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <h3 style="font-size: 13px; color: var(--text-heading);">🔔 Active Deal Watches & Price Alerts</h3>
                        <p style="font-size: 11px; color: var(--text-muted);">Hermes periodically scans these items and alerts you when prices reach your target.</p>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <input type="text" id="watch-query" class="input-text" placeholder="Item query" style="width: 180px;" />
                        <input type="number" id="watch-target" class="input-text" placeholder="Target ($)" style="width: 100px;" />
                        <button class="btn-action" onclick="createDealWatch()">+ Add Watch</button>
                    </div>
                </div>

                <div style="overflow-x: auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Tracked Product</th>
                                <th>Target Price</th>
                                <th>Last Best Price</th>
                                <th>Best Retailer</th>
                                <th>Last Checked</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="watches-tbody">
                            <tr>
                                <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 14px;">
                                    No price watches configured. Add one above!
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- TAB 6: MULTI-CHANNEL GATEWAYS -->
    <div id="tab-channels" class="tab-panel">
        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">💬 Multi-Channel Adapters & Gateways</h2>
                    <p class="panel-desc">Connect Hermes to WhatsApp, Discord, Slack, Telegram, and Universal Webhooks with pairing code authorization.</p>
                </div>
                <button class="btn-action" onclick="refreshChannels()">&circlearrowright; Refresh Gateways</button>
            </div>

            <!-- GATEWAYS OVERVIEW CARDS -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 20px;">
                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: var(--text-heading);">Discord Gateway</span>
                        <span id="st-discord" class="status-pill offline">OFFLINE</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">Slash commands (/hermes) & interaction webhooks with Ed25519 signature verification.</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: var(--text-heading);">Slack Gateway</span>
                        <span id="st-slack" class="status-pill offline">OFFLINE</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">Events API & slash commands with HMAC-SHA256 request verification.</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: var(--text-heading);">WhatsApp Gateway</span>
                        <span id="st-whatsapp" class="status-pill offline">OFFLINE</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">Twilio & Baileys bridge adapters with phone pairing codes.</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: var(--text-heading);">Telegram Bot</span>
                        <span id="st-telegram" class="status-pill offline">OFFLINE</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">Bot API webhooks & markdown responses.</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: var(--text-heading);">Universal Relay</span>
                        <span id="st-relay" class="status-pill">ONLINE</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">HTTP Webhook relay for Home Assistant, n8n, and custom bots.</div>
                </div>
            </div>

            <!-- PAIRING CODE & ALLOWLIST MANAGER -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <h3 style="font-size: 13px; color: var(--text-heading); margin-bottom: 10px;">🔑 Approve Channel Pairing Code</h3>
                    <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">When an unknown user messages Hermes on WhatsApp/Discord/Slack, enter their 6-digit code here to grant access:</p>
                    <div style="display: flex; gap: 8px;">
                        <select id="pair-channel" class="input-select">
                            <option value="whatsapp">WhatsApp</option>
                            <option value="discord">Discord</option>
                            <option value="slack">Slack</option>
                            <option value="telegram">Telegram</option>
                        </select>
                        <input type="text" id="pair-code" class="input-text" placeholder="6-digit code" style="width: 120px;" maxlength="6" />
                        <button class="btn-action" onclick="submitPairing()">Approve & Pair</button>
                    </div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <h3 style="font-size: 13px; color: var(--text-heading); margin-bottom: 10px;">🧪 Test Dispatcher Simulator</h3>
                    <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">Simulate an incoming message from any channel to test role routing & failover cascades:</p>
                    <div style="display: flex; gap: 8px;">
                        <select id="sim-channel" class="input-select">
                            <option value="discord">Discord</option>
                            <option value="slack">Slack</option>
                            <option value="whatsapp">WhatsApp</option>
                            <option value="telegram">Telegram</option>
                            <option value="relay">Relay</option>
                        </select>
                        <input type="text" id="sim-prompt" class="input-text" placeholder="Prompt message..." style="flex: 1;" />
                        <button class="btn-action" onclick="simulateChannelMessage()">Send Test</button>
                    </div>
                    <div id="sim-output" style="margin-top: 10px; font-family: monospace; font-size: 11px; background: var(--bg-canvas); padding: 8px; border-radius: 4px; color: var(--accent-green); display: none;"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- TAB: OMNI-MESH CROSS-DEVICE ECOSYSTEM -->
    <div id="tab-mesh" class="tab-panel">
        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">📱 Hermes Omni-Mesh: Multi-Device Ecosystem</h2>
                    <p class="panel-desc">Real-time companion mesh unifying Desktop PC, Android/iOS Smartphone, Smartwatch (WearOS / Apple Watch), and Laptop.</p>
                </div>
                <div class="status-pill">
                    <div class="pulse-dot"></div>
                    <span id="mesh-hub-badge">HUB OPERATIONAL</span>
                </div>
            </div>

            <!-- PAIRING & COMPANION ACCESS -->
            <div style="display: grid; grid-template-columns: 200px 1fr; gap: 20px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 18px; margin-bottom: 20px;">
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; background: var(--bg-input); border-radius: 8px; padding: 10px;">
                    <img id="mesh-qr-img" src="" alt="Pairing QR" style="width: 150px; height: 150px; border-radius: 6px; border: 1px solid var(--border-subtle); object-fit: contain; background: #000;" />
                    <span style="font-size: 10px; color: var(--text-muted); margin-top: 6px; text-transform: uppercase; font-weight: 600;">1-Tap Phone / Watch Scan</span>
                </div>
                <div style="display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="font-size: 14px; font-weight: 700; color: #ffffff; margin-bottom: 4px;">Hermes Companion PWA</div>
                        <p style="font-size: 12px; color: var(--text-muted); line-height: 1.5;">
                            Zero Termux hassle. Open this link on your phone, watch, or laptop to install the Hermes Companion. Includes <strong>instant clipboard sync</strong>, <strong>camera-to-vision relay</strong>, <strong>wrist haptics & voice prompts</strong>, and <strong>emergency panic controls</strong>.
                        </p>
                        <div style="display: flex; align-items: center; gap: 8px; margin-top: 10px;">
                            <input type="text" id="mesh-companion-url" class="input-text" readonly style="flex: 1; font-family: monospace; font-size: 12px;" />
                            <button class="btn-action" onclick="copyMeshUrl()">📋 Copy Link</button>
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px;">
                        <a id="btn-open-phone" href="/companion?mode=phone" target="_blank" class="btn-action" style="text-decoration: none;">📱 Open Mobile View</a>
                        <a id="btn-open-watch" href="/companion?mode=watch" target="_blank" class="btn-action" style="text-decoration: none;">⌚ Open Watch HUD</a>
                        <a id="btn-open-laptop" href="/companion?mode=laptop" target="_blank" class="btn-action" style="text-decoration: none;">💻 Open Laptop View</a>
                        <button class="btn-action" onclick="refreshMeshDevices()">🔄 Refresh Mesh</button>
                    </div>
                </div>
            </div>

            <!-- CONNECTED DEVICES GRID -->
            <div style="margin-bottom: 20px;">
                <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 12px; display: flex; justify-content: space-between;">
                    <span>Active Mesh Nodes</span>
                    <span id="mesh-device-count" style="color: var(--accent-green);">1 Connected</span>
                </div>
                <div id="mesh-devices-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px;">
                    <!-- Dynamically populated -->
                </div>
            </div>

            <!-- UNIFIED CLIPBOARD & BROADCAST -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div class="panel-section" style="background: var(--bg-card); padding: 16px; border-radius: 8px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 12px; font-weight: 700; color: #ffffff; margin-bottom: 6px;">📋 Cross-Device Unified Clipboard</div>
                    <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px;">Push text directly to your phone, watch, or secondary laptop clipboard, or pull from PC:</p>
                    <textarea id="mesh-clip-input" class="input-textarea" style="width: 100%; height: 80px;" placeholder="Enter text to push across devices..."></textarea>
                    <div style="display: flex; gap: 8px; margin-top: 10px;">
                        <button class="btn-action" onclick="pushMeshClipboard()">⬆️ Broadcast to All Devices</button>
                        <button class="btn-action" onclick="pullMeshClipboard()">⬇️ Fetch PC Clipboard</button>
                    </div>
                </div>

                <div class="panel-section" style="background: var(--bg-card); padding: 16px; border-radius: 8px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 12px; font-weight: 700; color: #ffffff; margin-bottom: 6px;">🔔 Push Notification & Wrist Haptic Alert</div>
                    <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px;">Send a test alert with physical vibration to all connected phones & smartwatches:</p>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        <input type="text" id="mesh-notif-title" class="input-text" placeholder="Title (e.g. Model Training Complete)" value="Hermes AI Alert" />
                        <input type="text" id="mesh-notif-body" class="input-text" placeholder="Message content..." value="All benchmarks completed successfully." />
                        <div>
                            <button class="btn-action" onclick="sendMeshAlert()">⚡ Send Push & Buzz</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- TAB 7: SECURITY & PII SHIELD -->
    <div id="tab-security" class="tab-panel">
        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">🔒 PII & Secret Redaction Shield</h2>
                    <p class="panel-desc">Real-time masking engine guarding against credential compromises, API key leaks, and personal data exposure.</p>
                </div>
                <div class="status-pill">
                    <div class="pulse-dot"></div>
                    <span>SHIELD ENGAGED</span>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 18px;">
                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <h3 style="font-size: 13px; color: var(--text-heading); margin-bottom: 10px;">🛡️ Protected Credentials & Entities</h3>
                    <ul style="list-style: none; display: flex; flex-direction: column; gap: 6px; font-size: 11px; color: var(--text-main);">
                        <li>✅ <strong>Groq API Keys:</strong> <code>gsk_[A-Za-z0-9]{{20,}}</code> &rarr; [GROQ_KEY]</li>
                        <li>✅ <strong>Google Gemini Keys:</strong> <code>AIza[A-Za-z0-9_-]{{30,}}</code> &rarr; [GOOGLE_KEY]</li>
                        <li>✅ <strong>OpenAI Keys:</strong> <code>sk-[A-Za-z0-9_-]{{20,}}</code> &rarr; [OPENAI_KEY]</li>
                        <li>✅ <strong>GitHub Tokens:</strong> <code>gh[pousr]_[A-Za-z0-9]{{20,}}</code> &rarr; [GITHUB_TOKEN]</li>
                        <li>✅ <strong>Credit Cards:</strong> 13 to 19-digit Luhn formats &rarr; [CREDIT_CARD]</li>
                        <li>✅ <strong>Social Security Numbers:</strong> <code>XXX-XX-XXXX</code> &rarr; [SSN]</li>
                        <li>✅ <strong>Bank Accounts & Routing Numbers:</strong> &rarr; [BANK_ACCOUNT]</li>
                        <li>✅ <strong>Personal Emails & Phone Numbers:</strong> &rarr; [EMAIL] / [PHONE]</li>
                    </ul>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <h3 style="font-size: 13px; color: var(--text-heading); margin-bottom: 10px;">⚡ Zero-Knowledge Guarantee</h3>
                    <p style="font-size: 11px; color: var(--text-muted); line-height: 1.6;">
                        Before any prompt, transcript snippet, or task log is transmitted to cloud LLMs or written to public git commits,
                        it is parsed through <code>pii_shield.py</code>. All recognized credentials and sensitive identifiers are replaced
                        with tokenized tags. Raw keys never leave your machine unredacted.
                    </p>
                    <div style="margin-top: 12px; padding: 10px; background: rgba(52, 211, 153, 0.08); border: 1px solid rgba(52, 211, 153, 0.2); border-radius: 4px; font-size: 11px; color: var(--accent-green);">
                        Git Filter-Repo & Zero-Credential Policy Active across all 22,000+ repository commits.
                    </div>
                </div>
            </div>

            <!-- LIVE INTERACTIVE REDACTION TESTER -->
            <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                <h3 style="font-size: 13px; color: var(--text-heading); margin-bottom: 10px;">🧪 Live Redaction Sandbox</h3>
                <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">Type or paste text with dummy keys, passwords, or emails to verify masking in real-time:</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                    <div>
                        <label style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Input Text</label>
                        <textarea id="pii-input" class="input-textarea" style="width: 100%; height: 110px; margin-top: 4px;" placeholder="My email is alice@company.com and my secret key is SAMPLE_REDACTED_API_KEY_12345."></textarea>
                        <div style="margin-top: 8px;">
                            <button class="btn-action" onclick="testPiiMasking()">🛡️ Test Redaction</button>
                        </div>
                    </div>
                    <div>
                        <label style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Redacted Output</label>
                        <textarea id="pii-output" class="input-textarea" style="width: 100%; height: 110px; margin-top: 4px; color: var(--accent-green);" readonly placeholder="Masked output will appear here..."></textarea>
                        <div id="pii-stats" style="margin-top: 8px; font-size: 11px; color: var(--text-muted);">Entities detected: 0</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- TAB 8: RPA MACRO STUDIO -->
    <div id="tab-rpa" class="tab-panel">
        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">🤖 RPA Action Recording & Replay Studio</h2>
                    <p class="panel-desc">Record precision mouse movements, clicks, and keystrokes. Replay with humanized natural timing.</p>
                </div>
                <button class="btn-action" onclick="refreshMacros()">&circlearrowright; Refresh Workflows</button>
            </div>

            <!-- RECORDING CONTROLS -->
            <div style="display: flex; gap: 14px; align-items: center; background: var(--bg-input); padding: 14px; border-radius: 6px; border: 1px solid var(--border-subtle); margin-bottom: 18px; flex-wrap: wrap;">
                <input type="text" id="rpa-new-name" class="input-text" placeholder="Macro workflow name (e.g. ExportReport)" style="width: 260px;" />
                <button id="btn-start-record" class="btn-action" onclick="startMacroRecord()">🔴 Start Recording</button>
                <button id="btn-stop-record" class="btn-action btn-danger" style="display: none;" onclick="stopMacroRecord()">⏹️ Stop & Save</button>
                <span id="rpa-rec-status" style="font-size: 11px; color: var(--text-muted);">Ready to record.</span>
            </div>

            <!-- SAVED MACROS LIST -->
            <h3 style="font-size: 13px; color: var(--text-heading); margin-bottom: 12px;">Saved Macro Automations</h3>
            <div style="overflow-x: auto;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Macro Name</th>
                            <th>Actions</th>
                            <th>Duration (sec)</th>
                            <th>Created At</th>
                            <th>Replay Speed</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="rpa-macros-tbody">
                        <tr>
                            <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 18px;">
                                No macro workflows saved yet. Enter a name above and click "Start Recording" to capture your workflow.
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- TAB 9: SYSTEM & HEALTH -->
    <div id="tab-system" class="tab-panel">
        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">⚡ Host System Observer & Resource Health</h2>
                    <p class="panel-desc">Continuous monitoring of hardware limits to prevent runaway tasks from freezing the OS.</p>
                </div>
                <button class="btn-action" onclick="refreshSystemHealth()">&circlearrowright; Refresh Metrics</button>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 20px;">
                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">CPU Utilization</div>
                    <div id="sys-cpu-val" style="font-size: 20px; font-weight: 700; color: var(--text-heading); margin-top: 4px;">{health_data.get('cpu_percent', 0)}%</div>
                    <div style="font-size: 11px; color: var(--accent-green); margin-top: 2px;">Normal Operating Band</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">RAM Memory Usage</div>
                    <div id="sys-ram-val" style="font-size: 20px; font-weight: 700; color: var(--text-heading); margin-top: 4px;">{health_data.get('ram_percent', 0)}%</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">{health_data.get('ram_used_gb', 0)} GB / {health_data.get('ram_total_gb', 16)} GB</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">System Disk Space</div>
                    <div id="sys-disk-val" style="font-size: 20px; font-weight: 700; color: var(--text-heading); margin-top: 4px;">{health_data.get('disk_percent', 0)}%</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">{health_data.get('disk_free_gb', 0)} GB Free</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Observer Status</div>
                    <div id="sys-status-val" style="font-size: 20px; font-weight: 700; color: var(--accent-green); margin-top: 4px;">HEALTHY</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Proactive Watchdog Active</div>
                </div>
            </div>

            <!-- PROACTIVE BRIEFING PREVIEW -->
            <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h3 style="font-size: 13px; color: var(--text-heading);">📰 Executive Daily Intelligence Briefing Preview</h3>
                    <button class="btn-action" onclick="generateBriefing()">Generate Live Briefing</button>
                </div>
                <div id="briefing-box" style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 4px; padding: 14px; font-family: ui-monospace, monospace; font-size: 11px; color: var(--text-main); line-height: 1.6; white-space: pre-wrap; max-height: 240px; overflow-y: auto;">
Click "Generate Live Briefing" to compile system health, active agent status, and today's audit metrics.
                </div>
            </div>
        </div>
    </div>

    <!-- TAB 10: BROWSER EXTENSION -->
    <div id="tab-browser" class="tab-panel">
        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">🌐 Hermes Browser Control (Manifest V3)</h2>
                    <p class="panel-desc">Direct DOM integration in Chrome and Edge with zero bot detection and persistent user logins.</p>
                </div>
                <div class="status-pill">
                    <div class="pulse-dot"></div>
                    <span>MANIFEST V3 READY</span>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 20px;">
                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <h3 style="font-size: 13px; color: var(--text-heading); margin-bottom: 12px;">🌟 Key Architecture Advantages</h3>
                    <div style="display: flex; flex-direction: column; gap: 10px; font-size: 11px; color: var(--text-main);">
                        <div>
                            <strong>1. Zero Cloudflare Bot Detection:</strong>
                            <p style="color: var(--text-muted); margin-top: 2px;">Unlike Playwright/Selenium which start in suspicious headless Chromium profiles, this runs directly inside your daily browser with your natural fingerprints.</p>
                        </div>
                        <div>
                            <strong>2. Retains All Active Cookies & Logins:</strong>
                            <p style="color: var(--text-muted); margin-top: 2px;">No need to log in to GitHub, Google, or internal intranets every session. Hermes operates right alongside you.</p>
                        </div>
                        <div>
                            <strong>3. Autonomous Gate & CAPTCHA Sniffer:</strong>
                            <p style="color: var(--text-muted); margin-top: 2px;">Automatically detects login walls, Cloudflare turnstiles, and cookie consent modals.</p>
                        </div>
                    </div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <h3 style="font-size: 13px; color: var(--text-heading); margin-bottom: 12px;">📥 How to Load into Chrome / Edge</h3>
                    <ol style="margin-left: 18px; font-size: 11px; color: var(--text-main); display: flex; flex-direction: column; gap: 8px;">
                        <li>Open your browser and navigate to: <code>chrome://extensions</code> (or <code>edge://extensions</code>).</li>
                        <li>Toggle on <strong>Developer mode</strong> in the upper right corner.</li>
                        <li>Click the <strong>Load unpacked</strong> button.</li>
                        <li>Select the directory:<br>
                            <code style="color: var(--accent-green); background: var(--bg-card); padding: 2px 6px; border-radius: 3px; display: inline-block; margin-top: 4px;">
                                app/browser_extension/hermes_browser_control
                            </code>
                        </li>
                        <li>The extension will activate and bridge all active tabs via <code>window.__HERMES_BROWSER_CONTROL__</code>!</li>
                    </ol>
                </div>
            </div>
        </div>
    </div>

    <!-- TAB 11: AUDIT TRAIL -->
    <div id="tab-logs" class="tab-panel">
        <div class="filter-bar">
            <div class="filter-chips">
"""

    role_counts = {}
    for t in tasks:
        r = t.get("role", "OTHER")
        role_counts[r] = role_counts.get(r, 0) + 1

    chips_html = f'<button class="chip active" onclick="filterLogs(\'ALL\')">All Tasks ({num_tasks})</button>'
    for r in current_roles.keys():
        c = role_counts.get(r, 0)
        chips_html += f'<button class="chip" onclick="filterLogs(\'{r}\')">{r} ({c})</button>'

    html += f"""
                {chips_html}
            </div>
            <input type="text" class="search-input" id="log-search" placeholder="Search prompts, models, outputs..." onkeyup="searchLogs()" />
        </div>
        <div class="logs-stream">
    """

    if not tasks:
        html += """
            <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 32px; text-align: center; color: var(--text-muted);">
                <p>No agent tasks logged yet. Tasks run through <code>agent_dispatcher.py</code> will appear here automatically.</p>
            </div>
        """
    else:
        for t in tasks:
            timestamp = t.get("timestamp", "")[:19].replace("T", " ")
            role = t.get("role", "SYSTEM")
            meta = ROLE_META.get(role, {"icon": "🤖"})
            html += f"""
            <div class="log-entry" data-role="{role}">
                <div class="log-header">
                    <div class="log-role-tag">
                        <span>{meta['icon']}</span>
                        <span>{role} &bull; {t.get('model', 'Model')}</span>
                    </div>
                    <div class="log-metrics">
                        <span>{timestamp}</span>
                        <span style="color: var(--accent-green); font-weight: 600;">{t.get('latency_ms', 0)}ms</span>
                    </div>
                </div>
                <div class="log-prompt"><strong>Prompt:</strong> {t.get('task', '')}</div>
                <div class="log-output">{t.get('response', '')}</div>
            </div>
            """

    html += """
        </div>
    </div>

    <!-- TOAST POPUP -->
    <div id="toast">
        <span>&check;</span>
        <span id="toast-msg">Action performed successfully</span>
    </div>

    <!-- CLIENT SCRIPT LOGIC -->
    <script>
        function setTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

            event.target.classList.add('active');
            const targetPanel = document.getElementById('tab-' + tabId);
            if (targetPanel) {
                targetPanel.classList.add('active');
            }

            if (tabId === 'desktop') refreshWindows();
            if (tabId === 'paper') checkPaperStatus();
            if (tabId === 'shutdown') refreshShutdownStatus();
            if (tabId === 'deals') refreshWatches();
            if (tabId === 'channels') refreshChannels();
            if (tabId === 'mesh') refreshMeshDevices();
            if (tabId === 'rpa') refreshMacros();
            if (tabId === 'system') refreshSystemHealth();
        }

        function toggleEmpLogs(role) {
            const panel = document.getElementById('logs-' + role);
            const arrow = document.getElementById('arrow-' + role);
            if (!panel) return;
            if (panel.style.display === 'none' || !panel.style.display) {
                panel.style.display = 'flex';
                arrow.innerText = '▲';
            } else {
                panel.style.display = 'none';
                arrow.innerText = '▼';
            }
        }

        let currentFilter = 'ALL';
        function filterLogs(role) {
            currentFilter = role;
            document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            applyFilters();
        }

        function searchLogs() {
            applyFilters();
        }

        function applyFilters() {
            const query = (document.getElementById('log-search')?.value || '').toLowerCase();
            const entries = document.querySelectorAll('.log-entry');
            entries.forEach(entry => {
                const role = entry.getAttribute('data-role');
                const text = entry.innerText.toLowerCase();
                const roleMatch = (currentFilter === 'ALL' || role === currentFilter);
                const searchMatch = !query || text.includes(query);
                entry.style.display = (roleMatch && searchMatch) ? 'flex' : 'none';
            });
        }

        async function updateSoul(role) {
            const textarea = document.getElementById('soul-' + role);
            const soul = textarea.value;
            const indicator = document.getElementById('saved-' + role);

            try {
                const res = await fetch('/api/update_soul', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ role: role, soul: soul })
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    indicator.classList.add('visible');
                    setTimeout(() => indicator.classList.remove('visible'), 2500);
                    showToast(`Updated ${role} Soul directives`);
                } else {
                    alert('Error saving directives');
                }
            } catch (err) {
                alert('Connection error: ' + err);
            }
        }

        // --- Desktop Shell & Windows Logic ---
        async function refreshWindows() {
            try {
                const res = await fetch('/api/desktop/windows');
                const data = await res.json();
                const tbody = document.getElementById('windows-tbody');
                if (!tbody) return;
                tbody.innerHTML = '';
                if (!data.windows || data.windows.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 14px;">No active user windows found.</td></tr>';
                    return;
                }
                data.windows.forEach(w => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${w.hwnd}</td>
                        <td style="font-weight: 600; color: var(--text-heading); max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${w.title}</td>
                        <td>Active Window</td>
                        <td>Monitor ${w.monitor}</td>
                        <td style="font-family: monospace; font-size: 11px;">${w.width}x${w.height} @ (${w.x},${w.y})</td>
                        <td>
                            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                                <button class="btn-action" style="padding: 3px 6px; font-size: 10px;" onclick="snapWin('${w.hwnd}', 'left')">◧ Left</button>
                                <button class="btn-action" style="padding: 3px 6px; font-size: 10px;" onclick="snapWin('${w.hwnd}', 'right')">◨ Right</button>
                                <button class="btn-action" style="padding: 3px 6px; font-size: 10px;" onclick="snapWin('${w.hwnd}', 'maximize')">🗖 Max</button>
                                <button class="btn-action" style="padding: 3px 6px; font-size: 10px;" onclick="moveWin('${w.hwnd}', 2)">To Mon 2</button>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
                showToast(`Refreshed ${data.windows.length} active windows`);
            } catch (e) {
                console.error(e);
            }
        }

        async function snapWin(hwnd, pos) {
            try {
                const res = await fetch('/api/desktop/snap', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target: hwnd, position: pos })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    showToast(`Snapped window: ${pos}`);
                    refreshWindows();
                } else {
                    alert('Snap error: ' + data.message);
                }
            } catch (e) {
                alert('Snap error: ' + e);
            }
        }

        async function moveWin(hwnd, monId) {
            try {
                const res = await fetch('/api/desktop/move_monitor', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target: hwnd, monitor_id: monId })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    showToast(`Moved to monitor ${monId}`);
                    refreshWindows();
                } else {
                    alert('Move error: ' + data.message);
                }
            } catch (e) {
                alert('Move error: ' + e);
            }
        }

        let isStopped = """ + ("true" if stopped_state else "false") + """;
        async function toggleEmergencyStop() {
            isStopped = !isStopped;
            try {
                const res = await fetch('/api/desktop/emergency_stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ stopped: isStopped })
                });
                const data = await res.json();
                const btn = document.getElementById('btn-toggle-panic');
                const topStat = document.getElementById('top-stat-stop');
                if (data.stopped) {
                    btn.innerText = "🛡️ DISENGAGE EMERGENCY STOP";
                    btn.classList.remove('btn-danger');
                    btn.classList.add('btn-action');
                    topStat.innerText = "STOPPED";
                    topStat.style.color = "var(--accent-red)";
                    showToast("🚨 EMERGENCY PANIC STOP ENGAGED!");
                } else {
                    btn.innerText = "🚨 ENGAGE EMERGENCY PANIC STOP";
                    btn.classList.add('btn-danger');
                    topStat.innerText = "READY";
                    topStat.style.color = "var(--accent-green)";
                    showToast("Emergency stop disengaged. System operational.");
                }
            } catch (e) {
                alert('Toggle error: ' + e);
            }
        }

        // --- Paper MCP Logic ---
        async function checkPaperStatus() {
            try {
                const res = await fetch('/api/paper/status');
                const data = await res.json();
                if (data.listening) {
                    showToast(`Paper Desktop MCP Online &bull; ${data.artboards} Artboard(s)`);
                } else {
                    showToast("Paper Desktop MCP offline (Port 29979 closed)");
                }
            } catch (e) {
                console.error(e);
            }
        }

        async function createPaperArtboard() {
            const name = document.getElementById('paper-artboard-name').value;
            const w = document.getElementById('paper-artboard-w').value;
            const h = document.getElementById('paper-artboard-h').value;
            try {
                const res = await fetch('/api/paper/artboard', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name, width: parseInt(w), height: parseInt(h) })
                });
                const data = await res.json();
                if (data.status === 'error') {
                    alert('Paper error: ' + data.message);
                } else {
                    showToast(`Created Artboard '${name}' (${w}x${h}) in Paper`);
                }
            } catch (e) {
                alert('Paper connection error: ' + e);
            }
        }

        async function writePaperHtml() {
            const code = document.getElementById('paper-html-code').value;
            const mode = document.getElementById('paper-html-mode').value;
            if (!code.trim()) {
                alert('Please enter HTML code to render');
                return;
            }
            try {
                const res = await fetch('/api/paper/write_html', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ html: code, mode: mode })
                });
                const data = await res.json();
                if (data.status === 'error') {
                    alert('Paper error: ' + data.message);
                } else {
                    showToast("Rendered HTML elements directly onto Paper canvas!");
                }
            } catch (e) {
                alert('Paper error: ' + e);
            }
        }

        // --- Smart Shutdown Logic ---
        async function refreshShutdownStatus() {
            try {
                const res = await fetch('/api/shutdown/status');
                const data = await res.json();
                document.getElementById('sd-rate-val').innerText = `${data.current_rate_kbps || 0} KB/s`;
                document.getElementById('sd-status-val').innerText = data.status || 'INACTIVE';
                document.getElementById('sd-state-sub').innerText = data.message || 'Ready';
                document.getElementById('sd-idle-val').innerText = `${data.idle_seconds || 0}s / ${data.idle_target_seconds || 120}s`;

                const topStat = document.getElementById('top-stat-shutdown');
                if (topStat) {
                    topStat.innerText = data.status || 'INACTIVE';
                    topStat.style.color = data.running ? 'var(--accent-gold)' : 'var(--text-muted)';
                }

                const btnStart = document.getElementById('btn-sd-start');
                const btnCancel = document.getElementById('btn-sd-cancel');
                if (data.running) {
                    btnStart.style.display = 'none';
                    btnCancel.style.display = 'inline-flex';
                } else {
                    btnStart.style.display = 'inline-flex';
                    btnCancel.style.display = 'none';
                }
            } catch (e) {
                console.error(e);
            }
        }

        async function startShutdownMonitor() {
            const action = document.getElementById('sd-action').value;
            const idleMin = parseInt(document.getElementById('sd-idle-min').value);
            const idleKbps = parseFloat(document.getElementById('sd-idle-kbps').value);
            const activeKbps = parseFloat(document.getElementById('sd-active-kbps').value);

            try {
                const res = await fetch('/api/shutdown/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        action: action,
                        idle_minutes: idleMin,
                        idle_kbps: idleKbps,
                        active_kbps: activeKbps
                    })
                });
                const data = await res.json();
                showToast(data.message);
                refreshShutdownStatus();
            } catch (e) {
                alert('Start shutdown error: ' + e);
            }
        }

        async function cancelShutdownMonitor() {
            try {
                const res = await fetch('/api/shutdown/cancel', { method: 'POST' });
                const data = await res.json();
                showToast(data.message);
                refreshShutdownStatus();
            } catch (e) {
                alert('Cancel error: ' + e);
            }
        }

        // --- Deal Finder & Watchlist Logic ---
        async function executeDealSearch() {
            const query = document.getElementById('deal-search-query').value.trim();
            if (!query) {
                alert('Please enter a product to search');
                return;
            }
            const vendors = [];
            if (document.getElementById('v-amazon').checked) vendors.push('amazon');
            if (document.getElementById('v-newegg').checked) vendors.push('newegg');
            if (document.getElementById('v-bestbuy').checked) vendors.push('bestbuy');
            if (document.getElementById('v-walmart').checked) vendors.push('walmart');
            if (document.getElementById('v-bhphoto').checked) vendors.push('bhphoto');
            if (document.getElementById('v-microcenter').checked) vendors.push('microcenter');

            const tbody = document.getElementById('deals-results-tbody');
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--accent-green); padding: 18px;">Scanning retailers (Amazon, Newegg, Best Buy...)...</td></tr>';

            try {
                const res = await fetch('/api/deals/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, vendors: vendors, max_results: 6 })
                });
                const data = await res.json();
                tbody.innerHTML = '';
                if (!data.deals || data.deals.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 18px;">No matching priced listings found. Try broader keywords.</td></tr>';
                    return;
                }
                data.deals.forEach((d, idx) => {
                    const row = document.createElement('tr');
                    const badge = idx === 0 ? '<span style="color: var(--accent-gold); font-weight: 700; margin-left: 6px;">★ BEST DEAL</span>' : '';
                    row.innerHTML = `
                        <td style="font-weight: 700; color: var(--text-heading);">${d.vendor}</td>
                        <td style="max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${d.title}</td>
                        <td>$${d.price.toFixed(2)}</td>
                        <td>${d.shipping ? '$' + d.shipping.toFixed(2) : 'Free / In-Store'}</td>
                        <td style="font-weight: 700; color: var(--accent-green); font-size: 13px;">$${d.total.toFixed(2)}${badge}</td>
                        <td><a href="${d.url}" target="_blank" class="btn-action" style="padding: 2px 8px; font-size: 10px; text-decoration: none;">View Item &rarr;</a></td>
                    `;
                    tbody.appendChild(row);
                });
                showToast(`Found ${data.deals.length} deals across vendors`);
            } catch (e) {
                alert('Search error: ' + e);
            }
        }

        async function refreshWatches() {
            try {
                const res = await fetch('/api/deals/watches');
                const data = await res.json();
                const tbody = document.getElementById('watches-tbody');
                if (!tbody) return;
                tbody.innerHTML = '';
                if (!data.watches || data.watches.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 14px;">No active price watches.</td></tr>';
                    return;
                }
                data.watches.forEach(w => {
                    const targetStr = w.target_price ? `$${w.target_price.toFixed(2)}` : 'Any Drop';
                    const bestStr = w.last_best_total ? `$${w.last_best_total.toFixed(2)}` : 'N/A';
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td style="font-family: monospace;">${w.id}</td>
                        <td style="font-weight: 600; color: var(--text-heading);">${w.query}</td>
                        <td style="color: var(--accent-gold);">${targetStr}</td>
                        <td style="color: var(--accent-green); font-weight: 700;">${bestStr}</td>
                        <td>${w.last_best_vendor || 'N/A'}</td>
                        <td>${w.last_checked_at ? w.last_checked_at.slice(0, 19).replace('T', ' ') : 'Never'}</td>
                        <td>
                            <div style="display: flex; gap: 4px;">
                                <button class="btn-action" style="padding: 2px 6px; font-size: 10px;" onclick="checkWatchNow('${w.id}')">Scan</button>
                                <button class="btn-action btn-danger" style="padding: 2px 6px; font-size: 10px;" onclick="deleteWatch('${w.id}')">&times;</button>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            } catch (e) {
                console.error(e);
            }
        }

        async function createDealWatch() {
            const query = document.getElementById('watch-query').value.trim();
            const target = document.getElementById('watch-target').value;
            if (!query) {
                alert('Please enter a product query');
                return;
            }
            try {
                const res = await fetch('/api/deals/watches/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, target_price: target ? parseFloat(target) : null })
                });
                const data = await res.json();
                showToast(`Created Deal Watch: ${query}`);
                document.getElementById('watch-query').value = '';
                document.getElementById('watch-target').value = '';
                refreshWatches();
            } catch (e) {
                alert('Watch error: ' + e);
            }
        }

        async function deleteWatch(id) {
            try {
                await fetch('/api/deals/watches/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ watch_id: id })
                });
                showToast('Removed deal watch');
                refreshWatches();
            } catch (e) {
                alert('Delete error: ' + e);
            }
        }

        async function checkWatchNow(id) {
            showToast('Scanning retailer prices...');
            try {
                const res = await fetch('/api/deals/watches/check', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ watch_id: id })
                });
                const data = await res.json();
                if (data.best_deal) {
                    showToast(`Scanned: Best price $${data.best_deal.total.toFixed(2)} on ${data.best_deal.vendor}`);
                } else {
                    showToast('Scan complete (no new prices)');
                }
                refreshWatches();
            } catch (e) {
                alert('Scan error: ' + e);
            }
        }

        // --- Multi-Channel Gateways Logic ---
        async function refreshChannels() {
            try {
                const res = await fetch('/api/channels/status');
                const data = await res.json();

                const updatePill = (id, active) => {
                    const el = document.getElementById(id);
                    if (!el) return;
                    if (active) {
                        el.innerText = 'ONLINE';
                        el.className = 'status-pill';
                    } else {
                        el.innerText = 'STANDBY';
                        el.className = 'status-pill offline';
                    }
                };

                updatePill('st-discord', data.discord?.enabled);
                updatePill('st-slack', data.slack?.enabled);
                updatePill('st-whatsapp', data.whatsapp?.enabled);
                updatePill('st-telegram', data.telegram?.enabled);
                updatePill('st-relay', data.relay?.enabled);
            } catch (e) {
                console.error(e);
            }
        }

        async function submitPairing() {
            const ch = document.getElementById('pair-channel').value;
            const code = document.getElementById('pair-code').value.trim();
            if (!code || code.length !== 6) {
                alert('Please enter a 6-digit pairing code');
                return;
            }
            try {
                const res = await fetch('/api/channels/pair', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ channel: ch, code: code })
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    showToast(`✅ ${data.message}`);
                    document.getElementById('pair-code').value = '';
                } else {
                    alert('Pairing error: ' + data.message);
                }
            } catch (e) {
                alert('Pairing error: ' + e);
            }
        }

        async function simulateChannelMessage() {
            const ch = document.getElementById('sim-channel').value;
            const prompt = document.getElementById('sim-prompt').value.trim();
            if (!prompt) {
                alert('Please enter a prompt to simulate');
                return;
            }
            const out = document.getElementById('sim-output');
            out.style.display = 'block';
            out.innerText = `[${ch.toUpperCase()}] Routing to Hermes Agent...`;

            try {
                const res = await fetch('/api/channels/simulate_test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ channel: ch, prompt: prompt })
                });
                const data = await res.json();
                out.innerText = `[${ch.toUpperCase()} REPLY]\n${data.response}`;
                showToast(`Dispatched via ${ch}`);
            } catch (e) {
                out.innerText = `Error: ${e}`;
            }
        }

        // --- PII Shield Tester ---
        async function testPiiMasking() {
            const text = document.getElementById('pii-input').value;
            try {
                const res = await fetch('/api/security/mask_pii', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text })
                });
                const data = await res.json();
                document.getElementById('pii-output').value = data.masked_text;
                document.getElementById('pii-stats').innerText = `Entities detected & redacted: ${data.entities_count} items`;
                showToast(`Redacted ${data.entities_count} sensitive entities`);
            } catch (e) {
                alert('PII Masking error: ' + e);
            }
        }

        // --- RPA Macros Logic ---
        async function refreshMacros() {
            try {
                const res = await fetch('/api/rpa/macros');
                const data = await res.json();
                const tbody = document.getElementById('rpa-macros-tbody');
                tbody.innerHTML = '';
                if (!data.macros || data.macros.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 18px;">No macro workflows saved yet. Enter a name above and click "Start Recording" to capture your workflow.</td></tr>';
                    return;
                }
                data.macros.forEach(m => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td style="font-weight: 700; color: var(--text-heading);">${m.name}</td>
                        <td>${m.action_count} steps</td>
                        <td>${m.duration}s</td>
                        <td>${m.created_at ? m.created_at.slice(0, 19).replace('T', ' ') : 'N/A'}</td>
                        <td>
                            <select id="spd-${m.name}" class="input-select" style="padding: 2px 6px; font-size: 11px;">
                                <option value="1.0">1.0x (Normal)</option>
                                <option value="1.5">1.5x (Fast)</option>
                                <option value="2.0">2.0x (Hyper)</option>
                            </select>
                        </td>
                        <td>
                            <button class="btn-action" style="padding: 4px 8px; font-size: 11px;" onclick="replayMacro('${m.name}')">▶️ Replay</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            } catch (e) {
                console.error(e);
            }
        }

        async function startMacroRecord() {
            const name = document.getElementById('rpa-new-name').value.trim() || 'workflow';
            try {
                const res = await fetch('/api/rpa/record/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name })
                });
                const data = await res.json();
                if (data.status === 'recording') {
                    document.getElementById('btn-start-record').style.display = 'none';
                    document.getElementById('btn-stop-record').style.display = 'inline-flex';
                    document.getElementById('rpa-rec-status').innerText = `🔴 RECORDING '${name}'... (Move mouse, click, type)`;
                    document.getElementById('rpa-rec-status').style.color = "var(--accent-red)";
                    showToast(`Recording macro: ${name}`);
                }
            } catch (e) {
                alert('Record error: ' + e);
            }
        }

        async function stopMacroRecord() {
            try {
                const res = await fetch('/api/rpa/record/stop', { method: 'POST' });
                const data = await res.json();
                document.getElementById('btn-start-record').style.display = 'inline-flex';
                document.getElementById('btn-stop-record').style.display = 'none';
                document.getElementById('rpa-rec-status').innerText = `Saved '${data.name}' (${data.actions} actions, ${data.duration}s)`;
                document.getElementById('rpa-rec-status').style.color = "var(--accent-green)";
                showToast(`Saved macro '${data.name}' with ${data.actions} actions!`);
                refreshMacros();
            } catch (e) {
                alert('Stop error: ' + e);
            }
        }

        async function replayMacro(name) {
            const spd = document.getElementById('spd-' + name)?.value || '1.0';
            try {
                const res = await fetch('/api/rpa/replay', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name, speed: parseFloat(spd) })
                });
                const data = await res.json();
                showToast(`Replaying '${name}' at ${spd}x speed`);
            } catch (e) {
                alert('Replay error: ' + e);
            }
        }

        // --- System Health & Briefing ---
        async function refreshSystemHealth() {
            try {
                const res = await fetch('/api/system/health');
                const data = await res.json();
                document.getElementById('sys-cpu-val').innerText = `${data.cpu_percent}%`;
                document.getElementById('sys-ram-val').innerText = `${data.ram_percent}%`;
                document.getElementById('sys-disk-val').innerText = `${data.disk_percent}%`;
                document.getElementById('sys-status-val').innerText = data.status;
                showToast("System health metrics updated");
            } catch (e) {
                console.error(e);
            }
        }

        async function generateBriefing() {
            try {
                const res = await fetch('/api/system/briefing');
                const data = await res.json();
                document.getElementById('briefing-box').innerText = data.briefing;
                showToast("Executive briefing generated");
            } catch (e) {
                alert('Briefing error: ' + e);
            }
        }

        // --- Omni-Mesh Cross-Device JavaScript ---
        async function refreshMeshDevices() {
            try {
                const res = await fetch('/api/mesh/status');
                const data = await res.json();
                
                if (data.pairing_qr) {
                    const qrEl = document.getElementById('mesh-qr-img');
                    if (qrEl) qrEl.src = data.pairing_qr;
                }
                if (data.companion_url) {
                    const urlEl = document.getElementById('mesh-companion-url');
                    if (urlEl) urlEl.value = data.companion_url;
                }
                
                const countBadge = document.getElementById('mesh-device-count');
                if (countBadge) {
                    countBadge.innerText = `${data.connected_devices || 1} Connected (${data.total_devices || 1} Registered)`;
                }

                const grid = document.getElementById('mesh-devices-grid');
                if (grid && data.devices) {
                    grid.innerHTML = data.devices.map(d => {
                        const icon = d.device_type === 'phone' ? '📱' :
                                     d.device_type === 'watch' ? '⌚' :
                                     d.device_type === 'laptop' ? '💻' : '🖥️';
                        const batt = d.battery_level !== null && d.battery_level !== undefined ?
                                     `${d.is_charging ? '⚡ ' : '🔋 '}${d.battery_level}%` : '⚡ Line Powered';
                        const statusColor = d.connected ? 'var(--accent-green)' : 'var(--text-muted)';
                        const statusText = d.connected ? 'ONLINE' : 'OFFLINE';

                        return `
                        <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 14px; display: flex; flex-direction: column; gap: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span style="font-size: 20px;">${icon}</span>
                                    <div>
                                        <div style="font-weight: 700; color: #ffffff; font-size: 13px;">${d.name}</div>
                                        <div style="font-size: 10px; color: var(--text-muted);">${d.ip_address || 'Local Host'} • ${d.device_type.toUpperCase()}</div>
                                    </div>
                                </div>
                                <span style="font-size: 10px; font-weight: 700; color: ${statusColor}; background: rgba(16,185,129,0.1); padding: 3px 8px; border-radius: 10px;">
                                    ${statusText}
                                </span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); padding: 4px 0; border-top: 1px solid var(--border-subtle);">
                                <span>Power</span>
                                <span style="color: var(--text-heading); font-weight: 600;">${batt}</span>
                            </div>
                            ${d.device_id !== 'desktop-host' ? `
                            <div style="display: flex; gap: 6px; margin-top: 4px;">
                                <button class="btn-action" style="flex: 1; padding: 4px 8px; font-size: 10px;" onclick="buzzMeshDevice('${d.device_id}')">🔔 Buzz</button>
                                <button class="btn-action" style="flex: 1; padding: 4px 8px; font-size: 10px;" onclick="pushMeshClipboardTo('${d.device_id}')">📋 Push Clip</button>
                            </div>` : ''}
                        </div>`;
                    }).join('');
                }
            } catch (e) {
                console.error("Failed to refresh mesh devices", e);
            }
        }

        function copyMeshUrl() {
            const urlInput = document.getElementById('mesh-companion-url');
            if (urlInput) {
                navigator.clipboard.writeText(urlInput.value).then(() => {
                    showToast("Companion link copied to clipboard!");
                }).catch(() => {
                    urlInput.select();
                    document.execCommand('copy');
                    showToast("Link copied!");
                });
            }
        }

        async function pushMeshClipboard() {
            const text = document.getElementById('mesh-clip-input').value;
            if (!text) {
                alert("Please enter text to push.");
                return;
            }
            try {
                const res = await fetch('/api/mesh/clipboard/push', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text })
                });
                await res.json();
                showToast("Clipboard broadcast to all companion devices!");
            } catch (e) {
                alert("Push error: " + e);
            }
        }

        async function pullMeshClipboard() {
            try {
                const res = await fetch('/api/mesh/clipboard/get');
                const data = await res.json();
                document.getElementById('mesh-clip-input').value = data.clipboard || '';
                showToast("Fetched PC clipboard");
            } catch (e) {
                alert("Pull error: " + e);
            }
        }

        async function sendMeshAlert() {
            const title = document.getElementById('mesh-notif-title').value;
            const body = document.getElementById('mesh-notif-body').value;
            try {
                await fetch('/api/mesh/notify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: title, body: body, vibrate: true })
                });
                showToast("Push notification & haptic buzz dispatched!");
            } catch (e) {
                alert("Alert error: " + e);
            }
        }

        async function buzzMeshDevice(deviceId) {
            try {
                await fetch('/api/mesh/notify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ device_id: deviceId, title: "Hermes Ping", body: "Direct device buzz from PC", vibrate: true })
                });
                showToast(`Buzzed device ${deviceId}`);
            } catch (e) {
                alert("Buzz error: " + e);
            }
        }

        function showToast(text) {
            const toast = document.getElementById('toast');
            document.getElementById('toast-msg').innerText = text;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }
    </script>
</body>
</html>
"""
    return html


if __name__ == "__main__":
    print("Starting Hermes Autonomous Operations Center on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
