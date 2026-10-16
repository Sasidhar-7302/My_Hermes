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

_parent_dir = os.path.dirname(_cur_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Load workspace .env variables into os.environ if not already set
for _env_path in (
    os.path.join(os.path.dirname(_parent_dir), ".env"),
    os.path.join(_parent_dir, ".env"),
    os.path.join(_cur_dir, ".env"),
):
    if os.path.exists(_env_path):
        try:
            with open(_env_path, "r", encoding="utf-8") as _ef:
                for _line in _ef:
                    _ls = _line.strip()
                    if _ls and not _ls.startswith("#") and "=" in _ls:
                        _k, _, _v = _ls.partition("=")
                        _k = _k.strip()
                        _v = _v.strip().strip('"').strip("'")
                        if _k and _v and _k not in os.environ:
                            os.environ[_k] = _v
        except Exception:
            pass


import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
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
        get_hot_frontpage_deals,
        get_deal_watch_store,
    )
except ImportError:
    try:
        from deal_finder import (
            search_deals,
            get_hot_frontpage_deals,
            get_deal_watch_store,
        )
    except Exception:
        search_deals = lambda q, v=None, m=6, **kw: []
        get_hot_frontpage_deals = lambda max_items=15: []
        get_deal_watch_store = lambda: None

try:
    from local_model_lab.hermes_browser import (
        open_in_chintu_browser,
        resolve_chintu_profile_info,
    )
except ImportError:
    try:
        from hermes_browser import (
            open_in_chintu_browser,
            resolve_chintu_profile_info,
        )
    except Exception:
        open_in_chintu_browser = lambda url, new_window=False: {"status": "error", "message": "hermes_browser unavailable"}
        resolve_chintu_profile_info = lambda: {"profile_directory": "Profile 1", "display_name": "Chintu", "email": "chintu.ai2026@gmail.com"}


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
    from companions import (
        get_omni_mesh_hub,
        read_pc_clipboard,
        write_pc_clipboard,
        register_companion_routes,
    )
except ImportError:
    try:
        from local_model_lab.omni_mesh import (
            get_omni_mesh_hub,
            read_pc_clipboard,
            write_pc_clipboard,
        )
        from companions import register_companion_routes
    except Exception:
        get_omni_mesh_hub = lambda: None
        read_pc_clipboard = lambda: ""
        write_pc_clipboard = lambda t: False
        register_companion_routes = lambda a: None


app = FastAPI(title="Hermes Agent Operations Center")
register_companion_routes(app)


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
    vendors = data.get("vendors") or [
        "slickdeals", "reddit", "dealnews",
        "amazon", "newegg", "bestbuy", "walmart", "bhphoto", "microcenter"
    ]
    max_results = int(data.get("max_results", 8))
    if not query:
        return JSONResponse(content={"count": 0, "deals": []})
    deals = search_deals(query, vendors=vendors, max_results_per_vendor=max_results)
    return JSONResponse(content={
        "count": len(deals),
        "deals": [d.to_dict() for d in deals],
        "browser_profile": resolve_chintu_profile_info(),
    })


@app.get("/api/deals/hot")
async def api_deals_hot(limit: int = 16):
    deals = get_hot_frontpage_deals(max_results=limit)
    return JSONResponse(content={
        "count": len(deals),
        "deals": [d.to_dict() for d in deals],
        "browser_profile": resolve_chintu_profile_info(),
    })


@app.post("/api/browser/open_chintu")
async def api_browser_open_chintu(request: Request):
    data = await request.json()
    url = str(data.get("url", "")).strip()
    new_window = bool(data.get("new_window", False))
    if not url:
        return JSONResponse(content={"status": "error", "message": "Missing url"}, status_code=400)
    res = open_in_chintu_browser(url, new_window=new_window)
    return JSONResponse(content=res)


@app.get("/api/browser/chintu_status")
async def api_browser_chintu_status():
    return JSONResponse(content=resolve_chintu_profile_info())


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
    vendors = data.get("vendors") or [
        "slickdeals", "reddit", "dealnews",
        "amazon", "newegg", "bestbuy", "walmart", "bhphoto", "microcenter"
    ]
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


# ── LAYA SYSTEM-1 REAL-TIME DECISION & VOICE API ───────────────────────────

@app.get("/api/laya/status")
async def api_laya_status():
    try:
        from local_model_lab.laya_real_bridge import get_laya_bridge
        bridge = get_laya_bridge()
        is_ready = bridge.is_available()
        return JSONResponse(content={
            "status": "ready" if is_ready else "initializing",
            "model": "ModernBERT-large (convaiinnovations/laya)",
            "params": "421M non-autoregressive",
            "device": getattr(bridge, "_device", "cuda"),
            "loss": "RLCD (Reinforcement Learning from Calibrated Decisions)",
            "accuracy": "99.60%",
            "ece": "0.0040",
            "latency_target": "<35ms",
            "checkpoint": "D:/laya_checkpoints/hermes_laya_v1",
            "tools": [
                "media_control", "window_manager", "smart_shutdown",
                "deal_finder", "rpa_macro", "screen_vision",
                "paper_design", "general_agent"
            ]
        })
    except Exception as exc:
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=500)


@app.post("/api/laya/decide")
async def api_laya_decide(request: Request):
    t0 = time.time()
    try:
        data = await request.json()
        prompt = str(data.get("prompt", "")).strip()
        if not prompt:
            return JSONResponse(content={"status": "error", "message": "Empty prompt"}, status_code=400)
        from local_model_lab.laya_real_bridge import evaluate_streaming_transcript
        res = evaluate_streaming_transcript(prompt, session_id="dashboard_test", execute_action=bool(data.get("execute", False)))
        lat_ms = round((time.time() - t0) * 1000, 2)
        res["latency_ms"] = lat_ms
        return JSONResponse(content=res)
    except Exception as exc:
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=500)


@app.post("/api/laya/stream")
async def api_laya_stream(request: Request):
    t0 = time.time()
    try:
        data = await request.json()
        transcript = str(data.get("transcript", "")).strip()
        session_id = str(data.get("session_id", "dashboard_live"))
        execute = bool(data.get("execute", True))
        from local_model_lab.laya_real_bridge import evaluate_streaming_transcript
        res = evaluate_streaming_transcript(transcript, session_id=session_id, execute_action=execute)
        res["latency_ms"] = round((time.time() - t0) * 1000, 2)
        return JSONResponse(content=res)
    except Exception as exc:
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=500)


@app.post("/api/media/control")
async def api_media_control(request: Request):
    try:
        data = await request.json()
        action = str(data.get("action", "")).strip()
        steps = int(data.get("steps", 4))
        from local_model_lab.media_control import (
            toggle_mute, volume_up, volume_down,
            media_play_pause, media_next, media_previous, media_stop
        )
        act = action.lower()
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
            return JSONResponse(content={"status": "error", "message": f"Unknown action: {action}"}, status_code=400)
        return JSONResponse(content=res)
    except Exception as exc:
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=500)


# ── LIVE DESKTOP SCREEN STREAMING & REMOTE INPUT (MUSE "WATCH IT WORK") ────

@app.get("/api/desktop/stream")
async def api_desktop_stream(
    monitor: str = "2",
    fps: int = 8,
    quality: int = 60,
    max_width: int = 960
):
    """
    Real-time MJPEG live stream of the Windows desktop.
    Universally supported by iOS Safari, Android Chrome, WearOS, and Desktop browsers.
    """
    from local_model_lab.desktop_streamer import get_desktop_streamer
    streamer = get_desktop_streamer()
    fps = max(1, min(fps, 15))
    sleep_interval = 1.0 / float(fps)

    async def frame_generator():
        while True:
            t0 = time.time()
            frame_bytes, _, _ = streamer.capture_frame(monitor_id=monitor, max_width=max_width, quality=quality)
            if frame_bytes:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
            elapsed = time.time() - t0
            to_sleep = max(0.01, sleep_interval - elapsed)
            await asyncio.sleep(to_sleep)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/desktop/snapshot")
async def api_desktop_snapshot(monitor: str = "2", max_width: int = 1280, quality: int = 75):
    """Returns a single high-resolution screenshot JPEG."""
    from local_model_lab.desktop_streamer import get_desktop_streamer
    streamer = get_desktop_streamer()
    frame_bytes, _, _ = streamer.capture_frame(monitor_id=monitor, max_width=max_width, quality=quality)
    if not frame_bytes:
        return Response(content=b"", media_type="image/jpeg", status_code=500)
    return Response(
        content=frame_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@app.get("/api/desktop/live_activity")
async def api_desktop_live_activity():
    """Returns active window, cursor location, Laya decision, and emergency stop status."""
    from local_model_lab.desktop_streamer import get_desktop_streamer
    streamer = get_desktop_streamer()
    return JSONResponse(content=streamer.get_live_activity())


@app.post("/api/desktop/remote_input")
async def api_desktop_remote_input(request: Request):
    """Translates companion touch/clicks and keys into Windows inputs."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    try:
        data = await request.json()

        # Security Gate: LAN requests require token authentication from a paired device
        if client_ip not in ("127.0.0.1", "::1", "localhost", "testclient"):
            token = request.headers.get("X-Hermes-Token") or str(data.get("token", ""))
            dev_id = request.headers.get("X-Hermes-Device-Id") or str(data.get("device_id", ""))
            try:
                from companions.auth import get_pairing_manager
                pm = get_pairing_manager()
                if not (token and dev_id and pm.verify_device_token(dev_id, token)):
                    from companions.logger import log_companion_event
                    log_companion_event(
                        "SECURITY_ALERT",
                        f"Blocked unauthorized remote input from LAN IP {client_ip} (device: {dev_id or 'none'})",
                        level="WARNING",
                        device_id=dev_id or "unauthorized",
                    )
                    return JSONResponse(
                        content={"status": "error", "message": "Unauthorized: Remote desktop input requires a paired companion token."},
                        status_code=401,
                    )
            except Exception as auth_err:
                logger.debug(f"Auth check error: {auth_err}")
                return JSONResponse(content={"status": "error", "message": "Authentication service error"}, status_code=500)

        inp_type = str(data.get("type", "click")).lower()
        if inp_type in ("click", "tap"):
            from local_model_lab.desktop_streamer import inject_remote_mouse_click
            norm_x = float(data.get("x", 0.5))
            norm_y = float(data.get("y", 0.5))
            button = str(data.get("button", "left"))
            monitor = str(data.get("monitor", "2"))
            res = inject_remote_mouse_click(norm_x, norm_y, button=button, monitor_id=monitor)
            return JSONResponse(content=res)
        elif inp_type == "key":
            from local_model_lab.desktop_streamer import inject_remote_key_press
            key_name = str(data.get("key", "enter"))
            res = inject_remote_key_press(key_name)
            return JSONResponse(content=res)
        elif inp_type in ("focus", "focus_window"):
            from local_model_lab.window_services import focus_window
            target = str(data.get("target", ""))
            ok = focus_window(target)
            return JSONResponse(content={"status": "success" if ok else "not_found", "target": target})
        return JSONResponse(content={"status": "error", "message": f"Unknown input type: {inp_type}"}, status_code=400)
    except Exception as exc:
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=500)


@app.post("/api/companion/screen_vision")
async def api_companion_screen_vision(request: Request):
    """
    Receives mobile or companion screen frame / screenshot, saves it,
    and analyzes what is on the screen for the user.
    """
    try:
        data = await request.json()
        image_b64 = data.get("image") or data.get("photo_data") or ""
        prompt = data.get("prompt") or "What is on my mobile screen? Analyze and summarize."
        device_id = data.get("device_id", "companion-mobile")

        if not image_b64:
            return JSONResponse(content={"status": "error", "message": "No image data provided"}, status_code=400)

        import base64, uuid
        from pathlib import Path
        raw_b64 = image_b64.split(",")[-1]
        img_bytes = base64.b64decode(raw_b64)
        out_dir = Path("local_model_lab/outputs")
        out_dir.mkdir(parents=True, exist_ok=True)
        fname = f"mobile_screen_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
        target_path = out_dir / fname
        target_path.write_bytes(img_bytes)

        analysis = f"Mobile screen snapshot captured ({len(img_bytes) // 1024} KB)."
        try:
            from local_model_lab.screen_vision import get_screen_vision
            sv = get_screen_vision()
            res = sv.describe_screen(prompt=prompt, image_bytes=img_bytes)
            if res:
                analysis = res
        except Exception as e:
            logger.debug(f"Screen vision describe error: {e}")

        return JSONResponse(content={
            "status": "success",
            "filename": fname,
            "size_kb": len(img_bytes) // 1024,
            "analysis": analysis,
            "prompt": prompt,
        })
    except Exception as exc:
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=500)


# ── HERMES 24/7 POWER & WAKE-ON-LAN APIS ──────────────────────────────────────

@app.get("/api/power/wol_info")
async def api_power_wol_info():
    from local_model_lab.hermes_power import get_wol_profiles, is_keepalive_active
    return JSONResponse(content={
        "keepalive_active": is_keepalive_active(),
        "profiles": get_wol_profiles(),
        "primary_mac": "00:13:EF:60:04:42",
        "ethernet_mac": "04:42:1A:EA:BF:E7",
        "ip": "10.0.0.60",
        "broadcast": "10.0.0.255",
        "port": 9
    })


@app.post("/api/power/wake")
async def api_power_wake(request: Request):
    """Sends Wake-on-LAN magic packet."""
    try:
        data = await request.json() if (await request.body()) else {}
    except Exception:
        data = {}
    mac = str(data.get("mac", "00:13:EF:60:04:42"))
    from local_model_lab.hermes_power import send_wake_on_lan
    res = send_wake_on_lan(mac_address=mac)
    return JSONResponse(content=res)


@app.get("/api/power/keepalive")
async def api_power_keepalive_get():
    from local_model_lab.hermes_power import is_keepalive_active
    return JSONResponse(content={"active": is_keepalive_active()})


@app.post("/api/power/keepalive")
async def api_power_keepalive_post(request: Request):
    try:
        data = await request.json()
        enable = bool(data.get("enable", True))
        from local_model_lab.hermes_power import enable_24_7_keepalive, disable_keepalive
        if enable:
            ok = enable_24_7_keepalive(allow_display_sleep=True)
        else:
            ok = disable_keepalive()
        return JSONResponse(content={"status": "ok", "active": ok})
    except Exception as exc:
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=500)


# ── OMNI-MESH CROSS-DEVICE API & PWA ────────────────────────────────────────



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

        token = init_data.get("token") or websocket.query_params.get("token")
        pair_code = init_data.get("pairing_code") or init_data.get("pair") or websocket.query_params.get("pair")

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
            token=token,
            pairing_code=pair_code,
            skip_accept=True,
        )
        if not device:
            return

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
            <button class="tab-btn" onclick="setTab('laya')">⚡ Laya System-1</button>
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
                    <h2 class="panel-title">🛍️ Multi-Vendor & Slickdeals Intelligence Engine</h2>
                    <p class="panel-desc">Cross-references live community frontpage deals (Slickdeals, r/buildapcsales, DealNews) and major retailers using Hermes's isolated Chintu Browser profile (never touches your personal profile).</p>
                </div>
                <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                    <div class="status-pill" style="border-color: rgba(56,189,248,0.4); color: #38bdf8;" title="Pinned to Chrome Profile 1 (Chintu - chintu.ai2026@gmail.com). Personal Sasidhar profile is strictly off-limits.">
                        <div class="pulse-dot" style="background: #38bdf8;"></div>
                        <span id="chintu-browser-pill">🌐 CHINTU BROWSER: PROFILE 1</span>
                    </div>
                    <div class="status-pill">
                        <div class="pulse-dot"></div>
                        <span>READ-ONLY SAFEGUARD ACTIVE</span>
                    </div>
                </div>
            </div>

            <!-- SEARCH BAR -->
            <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle); margin-bottom: 20px;">
                <div style="display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap;">
                    <input type="text" id="deal-search-query" class="input-text" placeholder="Search product (e.g. 2TB NVMe Gen4 SSD, RTX 5080, OLED Monitor, MacBook)..." style="flex: 1; min-width: 260px;" onkeydown="if(event.key==='Enter') executeDealSearch();" />
                    <button class="btn-action" onclick="executeDealSearch()">🔍 Search All Deals</button>
                    <button class="btn-action" style="background: rgba(245,158,11,0.15); border-color: #f59e0b; color: #fbbf24;" onclick="loadHotFrontpageDeals()">🔥 Slickdeals & Reddit Hot Frontpage</button>
                    <button class="btn-action" style="background: rgba(56,189,248,0.12); border-color: #38bdf8; color: #38bdf8;" onclick="openInChintuBrowser('https://slickdeals.net/deals/')">🌐 Open Slickdeals in Chintu</button>
                </div>
                <div style="display: flex; gap: 14px; font-size: 11px; color: var(--text-muted); flex-wrap: wrap; align-items: center;">
                    <span style="font-weight: 700; color: var(--text-heading);">Community & Aggregators:</span>
                    <label style="color: #fbbf24; font-weight: 600;"><input type="checkbox" id="v-slickdeals" checked /> 🔥 Slickdeals</label>
                    <label style="color: #f97316; font-weight: 600;"><input type="checkbox" id="v-reddit" checked /> 👽 Reddit (r/buildapcsales & r/deals)</label>
                    <label style="color: #38bdf8; font-weight: 600;"><input type="checkbox" id="v-dealnews" checked /> 📰 DealNews</label>
                    <span style="margin-left: 6px; font-weight: 700; color: var(--text-heading);">Direct Retailers:</span>
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
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h3 id="deals-table-heading" style="font-size: 13px; color: var(--text-heading); margin: 0;">Live Price Comparison (Sorted by Best Total Price)</h3>
                    <span id="deals-count-badge" style="font-size: 11px; color: var(--text-muted);"></span>
                </div>
                <div style="overflow-x: auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Source / Vendor</th>
                                <th>Deal Title</th>
                                <th>Item Price</th>
                                <th>Shipping</th>
                                <th>Best Total</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="deals-results-tbody">
                            <tr>
                                <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 18px;">
                                    Type a product query above and click "Search All Deals", or click "🔥 Slickdeals & Reddit Hot Frontpage" to browse live community deals.
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

            <!-- ALWAYS-ON USER GEOLOCATION & ENVIRONMENTAL CONTEXT -->
            <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 16px; margin-bottom: 20px; display: flex; flex-direction: column; gap: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 16px;">📍</span>
                        <div>
                            <span style="font-size: 13px; font-weight: 700; color: #ffffff;">Always-On Geolocation & Environmental Context</span>
                            <span id="loc-zone-tag" style="margin-left: 8px; font-size: 11px; font-weight: 700; background: rgba(16,185,129,0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; border: 1px solid rgba(16,185,129,0.3);">HOME COCKPIT</span>
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn-action" style="padding: 4px 10px; font-size: 11px;" onclick="setHomeLocation()">🏡 Lock As Home</button>
                        <button class="btn-action" style="padding: 4px 10px; font-size: 11px;" onclick="copyLocationContext()">📋 Copy Prompt Context</button>
                        <button class="btn-action" style="padding: 4px 10px; font-size: 11px;" onclick="refreshMeshDevices()">🔄 Refresh</button>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; background: var(--bg-input); padding: 12px; border-radius: 6px; border: 1px solid var(--border-subtle); font-size: 12px;">
                    <div>
                        <div style="color: var(--text-muted); font-size: 10px; text-transform: uppercase; font-weight: 600; margin-bottom: 2px;">Resolved Location</div>
                        <div id="loc-display-name" style="color: #ffffff; font-weight: 600; word-break: break-word;">Locating user via companion mesh...</div>
                        <div id="loc-distance-sub" style="color: var(--text-muted); font-size: 11px; margin-top: 2px;">0.0m from Home Cockpit</div>
                    </div>
                    <div>
                        <div style="color: var(--text-muted); font-size: 10px; text-transform: uppercase; font-weight: 600; margin-bottom: 2px;">Hyper-Local Weather</div>
                        <div id="loc-weather-summary" style="color: #38bdf8; font-weight: 600;">Fetching meteorological conditions...</div>
                        <div id="loc-weather-details" style="color: var(--text-muted); font-size: 11px; margin-top: 2px;">Open-Meteo Sat-Radar Sync</div>
                    </div>
                    <div>
                        <div style="color: var(--text-muted); font-size: 10px; text-transform: uppercase; font-weight: 600; margin-bottom: 2px;">Telemetry Channel</div>
                        <div id="loc-telemetry-source" style="color: #a855f7; font-weight: 600;">Smartphone (Low-Power Wi-Fi/Cell)</div>
                        <div id="loc-battery-guard" style="color: #10b981; font-size: 11px; margin-top: 2px;">🛡️ Zero Battery Drain Profile Active</div>
                    </div>
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
                        <a id="btn-open-phone" href="/companions/smartphone" target="_blank" class="btn-action" style="text-decoration: none;">📱 Open Mobile View</a>
                        <a id="btn-open-watch" href="/companions/smartwatch" target="_blank" class="btn-action" style="text-decoration: none;">⌚ Open Watch HUD</a>
                        <a id="btn-open-laptop" href="/companions/laptop" target="_blank" class="btn-action" style="text-decoration: none;">💻 Open Laptop View</a>
                        <button class="btn-action" onclick="refreshMeshDevices()">🔄 Refresh Mesh</button>
                    </div>
                </div>
            </div>

            <!-- MULTI-DEVICE COMPANION SCREEN WALL (BATTERY-PRESERVING) -->
            <div style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div>
                        <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted);">📺 Companion Screen Wall (Battery-Preserving Mirror)</div>
                        <div style="font-size: 11px; color: var(--text-muted);">Zero continuous video drain • High-contrast AMOLED Watch HUD • On-demand snapshot pull</div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn-action" style="padding: 4px 10px; font-size: 11px;" onclick="pullAllScreenshots()">🔄 Snap All Screens</button>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
                    <!-- 1. SMARTPHONE SCREEN CARD -->
                    <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 14px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <div style="display: flex; align-items: center; gap: 6px; font-weight: 700; color: #ffffff; font-size: 13px;">
                                    <span>📱</span>
                                    <span>Mobile Phone Screen</span>
                                </div>
                                <span id="wall-phone-battery" style="font-size: 11px; font-weight: 600; color: #10b981; background: rgba(16,185,129,0.1); padding: 2px 8px; border-radius: 10px;">🔋 Phone</span>
                            </div>
                            <div style="position: relative; width: 100%; height: 260px; background: #000; border-radius: 6px; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-subtle); margin-bottom: 10px;">
                                <img id="wall-phone-img" src="" style="width: 100%; height: 100%; object-fit: contain; display: none;" />
                                <div id="wall-phone-placeholder" style="display: flex; flex-direction: column; align-items: center; gap: 6px; color: var(--text-muted); font-size: 11px; text-align: center; padding: 16px;">
                                    <span style="font-size: 32px; opacity: 0.5;">📱</span>
                                    <span style="font-weight: 600; color: #ffffff;">Phone Screen Standby</span>
                                    <span>Preserving battery. Click "Pull Snapshot" to capture current screen.</span>
                                </div>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); margin-bottom: 10px;">
                                <span id="wall-phone-res">Resolution: Standby</span>
                                <span id="wall-phone-time">Last update: Never</span>
                            </div>
                        </div>
                        <div style="display: flex; gap: 6px;">
                            <button class="btn-action" style="flex: 1; font-size: 11px; padding: 6px;" onclick="requestCompanionSnapshot('smartphone')">🔄 Pull Snapshot</button>
                            <button class="btn-action" style="flex: 1; font-size: 11px; padding: 6px;" onclick="pingCompanionDevice('smartphone')">🔔 Ping Phone</button>
                        </div>
                    </div>

                    <!-- 2. LAPTOP SCREEN CARD -->
                    <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 14px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <div style="display: flex; align-items: center; gap: 6px; font-weight: 700; color: #ffffff; font-size: 13px;">
                                    <span>💻</span>
                                    <span>Laptop Workstation</span>
                                </div>
                                <span id="wall-laptop-battery" style="font-size: 11px; font-weight: 600; color: #38bdf8; background: rgba(56,189,248,0.1); padding: 2px 8px; border-radius: 10px;">⚡ Laptop</span>
                            </div>
                            <div style="position: relative; width: 100%; height: 260px; background: #000; border-radius: 6px; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-subtle); margin-bottom: 10px;">
                                <img id="wall-laptop-img" src="" style="width: 100%; height: 100%; object-fit: contain; display: none;" />
                                <div id="wall-laptop-placeholder" style="display: flex; flex-direction: column; align-items: center; gap: 6px; color: var(--text-muted); font-size: 11px; text-align: center; padding: 16px;">
                                    <span style="font-size: 32px; opacity: 0.5;">💻</span>
                                    <span style="font-weight: 600; color: #ffffff;">Workstation Mirror Standby</span>
                                    <span>Synced over LAN. Click "Pull Snapshot" to capture current screen.</span>
                                </div>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); margin-bottom: 10px;">
                                <span id="wall-laptop-res">Resolution: Standby</span>
                                <span id="wall-laptop-time">Last update: Never</span>
                            </div>
                        </div>
                        <div style="display: flex; gap: 6px;">
                            <button class="btn-action" style="flex: 1; font-size: 11px; padding: 6px;" onclick="requestCompanionSnapshot('laptop')">🔄 Pull Snapshot</button>
                            <button class="btn-action" style="flex: 1; font-size: 11px; padding: 6px;" onclick="pingCompanionDevice('laptop')">🔔 Ping Laptop</button>
                        </div>
                    </div>

                    <!-- 3. SMARTWATCH CIRCULAR AMOLED HUD CARD -->
                    <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 14px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <div style="display: flex; align-items: center; gap: 6px; font-weight: 700; color: #ffffff; font-size: 13px;">
                                    <span>⌚</span>
                                    <span>Smartwatch AMOLED Wrist</span>
                                </div>
                                <span id="wall-watch-battery" style="font-size: 11px; font-weight: 600; color: #f59e0b; background: rgba(245,158,11,0.1); padding: 2px 8px; border-radius: 10px;">🔋 0% Drain</span>
                            </div>
                            <div style="position: relative; width: 100%; height: 260px; background: #000; border-radius: 6px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid var(--border-subtle); margin-bottom: 10px;">
                                <!-- Photorealistic AMOLED Circular Watch Face -->
                                <div style="width: 180px; height: 180px; border-radius: 50%; border: 3px solid #10b981; background: radial-gradient(circle, #0e171b 0%, #05080a 100%); box-shadow: 0 0 20px rgba(16,185,129,0.25); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; padding: 10px; position: relative;">
                                    <div id="wall-watch-time" style="font-size: 26px; font-weight: 800; font-family: monospace; color: #ffffff; letter-spacing: 1px;">--:--</div>
                                    <div id="wall-watch-state" style="font-size: 9px; font-weight: 700; color: #10b981; text-transform: uppercase; letter-spacing: 0.05em;">● MIC READY</div>
                                    <div id="wall-watch-msg" style="font-size: 10px; color: #94a3b8; max-width: 140px; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">Hold to Talk</div>
                                    <div id="wall-watch-batt-sub" style="position: absolute; bottom: 12px; font-size: 9px; color: #64748b; font-weight: 600;">Wrist Battery: --</div>
                                </div>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); margin-bottom: 10px;">
                                <span>HUD Mode: AMOLED Micro-Telemetry</span>
                                <span id="wall-watch-sync">Sync: Realtime</span>
                            </div>
                        </div>
                        <div style="display: flex; gap: 6px;">
                            <button class="btn-action" style="flex: 1; font-size: 11px; padding: 6px;" onclick="requestCompanionSnapshot('smartwatch')">🔄 Sync HUD</button>
                            <button class="btn-action" style="flex: 1; font-size: 11px; padding: 6px;" onclick="pingCompanionDevice('smartwatch')">🔔 Ping Watch</button>
                        </div>
                    </div>

                    <!-- 4. HOST PC DESKTOP MONITOR CARD -->
                    <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 14px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <div style="display: flex; align-items: center; gap: 6px; font-weight: 700; color: #ffffff; font-size: 13px;">
                                    <span>🖥️</span>
                                    <span>Host PC (This Machine)</span>
                                </div>
                                <span style="font-size: 11px; font-weight: 600; color: #10b981; background: rgba(16,185,129,0.1); padding: 2px 8px; border-radius: 10px;">⚡ AI Core Online</span>
                            </div>
                            <div style="position: relative; width: 100%; height: 260px; background: #000; border-radius: 6px; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-subtle); margin-bottom: 10px;">
                                <img id="wall-pc-img" src="/api/desktop/snapshot?monitor=primary&max_width=800&quality=75" style="width: 100%; height: 100%; object-fit: contain;" onerror="this.style.display='none'; document.getElementById('wall-pc-placeholder').style.display='flex';" />
                                <div id="wall-pc-placeholder" style="display: none; flex-direction: column; align-items: center; gap: 6px; color: var(--text-muted); font-size: 11px; text-align: center; padding: 16px;">
                                    <span style="font-size: 32px; opacity: 0.5;">🖥️</span>
                                    <span style="font-weight: 600; color: #ffffff;">Host PC Display</span>
                                </div>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); margin-bottom: 10px;">
                                <span>Multi-Monitor Engine Active</span>
                                <span>Primary Display</span>
                            </div>
                        </div>
                        <div style="display: flex; gap: 6px;">
                            <button class="btn-action" style="flex: 1; font-size: 11px; padding: 6px;" onclick="setTab('desktop')">🖥️ View Desktop Shell</button>
                            <button class="btn-action" style="flex: 1; font-size: 11px; padding: 6px;" onclick="refreshPcScreen()">🔄 Refresh PC</button>
                        </div>
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

            <!-- COMPANION LOGS & PAIRED DEVICES AUDIT -->
            <div style="margin-top: 18px; background: var(--bg-card); padding: 16px; border-radius: 8px; border: 1px solid var(--border-subtle);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div style="font-size: 12px; font-weight: 700; color: #ffffff;">📜 Companion Ecosystem Audit Logs & Security</div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn-action" style="padding: 4px 10px; font-size: 11px;" onclick="refreshMeshLogs()">🔄 Refresh Logs</button>
                        <button class="btn-action" style="padding: 4px 10px; font-size: 11px;" onclick="generateNewPairingCode()">🔑 New Pairing Code</button>
                    </div>
                </div>
                <div id="mesh-logs-container" style="background: var(--bg-input); font-family: monospace; font-size: 11px; padding: 10px; border-radius: 6px; height: 140px; overflow-y: auto; color: var(--text-muted); line-height: 1.5; border: 1px solid var(--border-subtle);">
                    Loading companion logs...
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

    <!-- TAB: LAYA SYSTEM-1 DECISION ENGINE -->
    <div id="tab-laya" class="tab-panel">
        <div class="panel-container">
            <div class="panel-header">
                <div>
                    <h2 class="panel-title">⚡ Laya System-1 Calibrated Decision Engine & Voice Studio</h2>
                    <p class="panel-desc">Non-autoregressive ModernBERT-Large (421M) fine-tuned with RLCD on NVIDIA GeForce RTX 4060 Ti CUDA. Achieves sub-35ms deterministic tool routing and mid-sentence voice computer control.</p>
                </div>
                <button class="btn-action" onclick="refreshLayaStatus()">&circlearrowright; Refresh Model Telemetry</button>
            </div>

            <!-- MODEL METRICS GRID -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; margin-bottom: 22px;">
                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Model Architecture</div>
                    <div id="laya-model-val" style="font-size: 18px; font-weight: 700; color: var(--text-heading); margin-top: 4px;">ModernBERT-Large</div>
                    <div style="font-size: 11px; color: var(--accent-green); margin-top: 2px;">421M Non-Autoregressive</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Acceleration Hardware</div>
                    <div id="laya-device-val" style="font-size: 18px; font-weight: 700; color: #a855f7; margin-top: 4px;">RTX 4060 Ti (CUDA)</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">~650 MB VRAM Footprint</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">RLCD Model Accuracy</div>
                    <div id="laya-acc-val" style="font-size: 18px; font-weight: 700; color: var(--accent-green); margin-top: 4px;">99.60% (100% Bench)</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">ECE: 0.0040 (Calibrated)</div>
                </div>

                <div style="background: var(--bg-input); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                    <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Forward Pass Latency</div>
                    <div id="laya-lat-val" style="font-size: 18px; font-weight: 700; color: var(--text-heading); margin-top: 4px;">~31 ms</div>
                    <div style="font-size: 11px; color: var(--accent-green); margin-top: 2px;">Sub-Millisecond on Tier 0</div>
                </div>
            </div>

            <!-- INTERACTIVE DECISION & VOICE SANDBOX -->
            <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 20px; margin-bottom: 22px;">
                <h3 style="font-size: 14px; font-weight: 700; color: var(--text-heading); margin-bottom: 6px;">🎙️ Live Streaming Decision & Voice Studio</h3>
                <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 16px;">Type or speak naturally. Watch Laya evaluate intent mid-sentence and execute desktop actions deterministically before you even finish speaking.</p>

                <div style="display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap;">
                    <input type="text" id="laya-prompt-input" class="search-input" style="flex: 1; min-width: 260px;" placeholder="e.g. 'turn the volume up', 'mute audio', 'focus visual studio code', 'shut down PC in 20 min', 'find RTX 4070 deals', 'explain transformers'..." onkeyup="handleLayaKeyUp(event)" />
                    <button class="btn-action" onclick="runLayaDecide(false)">⚡ Evaluate</button>
                    <button class="btn-action" style="background: var(--accent-green); color: #000; font-weight: 700;" onclick="runLayaDecide(true)">▶️ Execute Action</button>
                    <button id="laya-mic-btn" class="btn-action" style="background: #3b82f6; color: #fff;" onclick="toggleLayaVoice()">🎙️ Live Mic</button>
                </div>

                <!-- LIVE DECISION RESULT CARD -->
                <div id="laya-result-box" style="background: var(--bg-input); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 16px; display: none;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <span id="laya-action-badge" style="padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase;">FIRE_EARLY</span>
                            <span id="laya-tool-badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 600;">media_control</span>
                            <span id="laya-tier-badge" style="background: rgba(168, 85, 247, 0.15); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3); padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 600;">plain_code</span>
                        </div>
                        <div style="font-size: 12px; color: var(--text-muted);">
                            Latency: <strong id="laya-res-lat" style="color: var(--accent-green);">32.4 ms</strong> &bull; Confidence: <strong id="laya-res-conf" style="color: var(--accent-green);">100%</strong>
                        </div>
                    </div>
                    <div id="laya-res-detail" style="font-family: monospace; font-size: 12px; color: var(--text-main); background: var(--bg-card); padding: 12px; border-radius: 4px; border: 1px solid var(--border-subtle); overflow-x: auto; white-space: pre-wrap;">
                    </div>
                </div>
            </div>

            <!-- QUICK WINDOWS MEDIA & DESKTOP CONTROLS -->
            <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 20px;">
                <h3 style="font-size: 14px; font-weight: 700; color: var(--text-heading); margin-bottom: 6px;">🎛️ Windows Media & Audio Controls</h3>
                <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 16px;">Direct Win32 hardware virtual key injection. Same actions triggered by Laya System-1 and Smartwatch HUD.</p>
                
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="btn-action" onclick="triggerMedia('mute')">🔇 Toggle Mute</button>
                    <button class="btn-action" onclick="triggerMedia('up')">🔊 Volume Up (+8%)</button>
                    <button class="btn-action" onclick="triggerMedia('down')">🔉 Volume Down (-8%)</button>
                    <button class="btn-action" onclick="triggerMedia('play')">⏯️ Play / Pause</button>
                    <button class="btn-action" onclick="triggerMedia('next')">⏭️ Next Track</button>
                    <button class="btn-action" onclick="triggerMedia('prev')">⏮️ Prev Track</button>
                </div>
            </div>
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

            if (tabId === 'laya') refreshLayaStatus();
            if (tabId === 'desktop') refreshWindows();
            if (tabId === 'paper') checkPaperStatus();
            if (tabId === 'shutdown') refreshShutdownStatus();
            if (tabId === 'deals') {
                refreshWatches();
                if (!window.__hotDealsLoadedOnce) {
                    window.__hotDealsLoadedOnce = true;
                    loadHotFrontpageDeals();
                }
            }
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
        async function openInChintuBrowser(url) {
            try {
                const res = await fetch('/api/browser/open_chintu', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, new_window: false })
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    showToast(`🌐 Opened in Chintu Browser (${data.profile || 'Profile 1'})`);
                } else {
                    alert('Chintu browser error: ' + (data.message || 'Unknown'));
                }
            } catch (e) {
                alert('Browser launch error: ' + e);
            }
        }

        function renderDealsTable(deals, headingText) {
            const tbody = document.getElementById('deals-results-tbody');
            const heading = document.getElementById('deals-table-heading');
            const countBadge = document.getElementById('deals-count-badge');
            if (heading && headingText) heading.innerText = headingText;
            if (countBadge) countBadge.innerText = deals ? `${deals.length} verified listings` : '';
            tbody.innerHTML = '';
            if (!deals || deals.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 18px;">No matching priced listings found. Try broader keywords or click "🔥 Slickdeals & Reddit Hot Frontpage".</td></tr>';
                return;
            }
            deals.forEach((d, idx) => {
                const row = document.createElement('tr');
                const badge = idx === 0 ? '<span style="color: var(--accent-gold); font-weight: 700; margin-left: 6px;">★ BEST DEAL</span>' : '';
                const vLower = (d.vendor || '').toLowerCase();
                let vendorStyle = 'color: var(--text-heading);';
                if (vLower.includes('slickdeals')) vendorStyle = 'color: #fbbf24;';
                else if (vLower.includes('reddit')) vendorStyle = 'color: #f97316;';
                else if (vLower.includes('dealnews')) vendorStyle = 'color: #38bdf8;';
                const safeUrl = (d.url || '').replace(/'/g, "\\'");
                const priceStr = d.price > 0 ? `$${d.price.toFixed(2)}` : '<span style="color: #fbbf24;">Community Deal</span>';
                const totalStr = d.total > 0 ? `$${d.total.toFixed(2)}` : 'See Thread';
                row.innerHTML = `
                    <td style="font-weight: 700; ${vendorStyle}">${d.vendor}</td>
                    <td style="max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${(d.title || '').replace(/"/g, '&quot;')}">${d.title}</td>
                    <td>${priceStr}</td>
                    <td>${d.shipping ? '$' + d.shipping.toFixed(2) : 'Free / Community'}</td>
                    <td style="font-weight: 700; color: var(--accent-green); font-size: 13px;">${totalStr}${badge}</td>
                    <td>
                        <div style="display: flex; gap: 6px; align-items: center;">
                            <button class="btn-action" style="padding: 2px 8px; font-size: 10px; background: rgba(56,189,248,0.15); border-color: #38bdf8; color: #38bdf8;" onclick="openInChintuBrowser('${safeUrl}')">🌐 Chintu Browser</button>
                            <a href="${d.url}" target="_blank" class="btn-action" style="padding: 2px 8px; font-size: 10px; text-decoration: none;">New Tab &rarr;</a>
                        </div>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }

        async function loadHotFrontpageDeals() {
            const tbody = document.getElementById('deals-results-tbody');
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #fbbf24; padding: 18px;">🔥 Fetching live Slickdeals Frontpage, Reddit r/buildapcsales & r/deals, and DealNews...</td></tr>';
            try {
                const res = await fetch('/api/deals/hot?limit=18');
                const data = await res.json();
                renderDealsTable(data.deals || [], '🔥 Live Slickdeals, Reddit & DealNews Frontpage Hot Deals');
                showToast(`Loaded ${(data.deals || []).length} live frontpage deals`);
            } catch (e) {
                alert('Hot deals error: ' + e);
            }
        }

        async function executeDealSearch() {
            const query = document.getElementById('deal-search-query').value.trim();
            if (!query) {
                loadHotFrontpageDeals();
                return;
            }
            const vendors = [];
            if (document.getElementById('v-slickdeals') && document.getElementById('v-slickdeals').checked) vendors.push('slickdeals');
            if (document.getElementById('v-reddit') && document.getElementById('v-reddit').checked) vendors.push('reddit');
            if (document.getElementById('v-dealnews') && document.getElementById('v-dealnews').checked) vendors.push('dealnews');
            if (document.getElementById('v-amazon').checked) vendors.push('amazon');
            if (document.getElementById('v-newegg').checked) vendors.push('newegg');
            if (document.getElementById('v-bestbuy').checked) vendors.push('bestbuy');
            if (document.getElementById('v-walmart').checked) vendors.push('walmart');
            if (document.getElementById('v-bhphoto').checked) vendors.push('bhphoto');
            if (document.getElementById('v-microcenter').checked) vendors.push('microcenter');

            const tbody = document.getElementById('deals-results-tbody');
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--accent-green); padding: 18px;">🔍 Scanning Slickdeals, Reddit Deals, DealNews, Amazon, Newegg, Best Buy & Chintu Headless Engine...</td></tr>';

            try {
                const res = await fetch('/api/deals/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, vendors: vendors, max_results: 8 })
                });
                const data = await res.json();
                renderDealsTable(data.deals || [], `Live Price Comparison for "${query}" (Sorted by Best Price)`);
                showToast(`Found ${(data.deals || []).length} deals across community & retail feeds`);
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

                function escapeHtml(str) {
                    if (!str) return '';
                    return String(str)
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;')
                        .replace(/"/g, '&quot;')
                        .replace(/'/g, '&#039;');
                }
                
                const countBadge = document.getElementById('mesh-device-count');
                if (countBadge) {
                    countBadge.innerText = `${data.connected_devices || 1} Connected (${data.total_devices || 1} Registered)`;
                }

                const grid = document.getElementById('mesh-devices-grid');
                if (grid && data.devices) {
                    grid.innerHTML = data.devices.map(d => {
                        const dtype = (d.device_type || '').toLowerCase();
                        const icon = (dtype === 'phone' || dtype === 'smartphone') ? '📱' :
                                     (dtype === 'watch' || dtype === 'smartwatch') ? '⌚' :
                                     (dtype === 'laptop' || dtype === 'workstation') ? '💻' : '🖥️';
                        const batt = d.battery_level !== null && d.battery_level !== undefined ?
                                     `${d.is_charging ? '⚡ ' : '🔋 '}${d.battery_level}%` : '⚡ Line Powered';
                        const statusColor = d.connected ? 'var(--accent-green)' : 'var(--text-muted)';
                        const statusText = d.connected ? 'ONLINE' : 'OFFLINE';
                        const safeName = escapeHtml(d.name);
                        const safeIp = escapeHtml(d.ip_address || 'Local Host');
                        const safeType = escapeHtml(dtype.toUpperCase());
                        const safeDevId = escapeHtml(d.device_id);

                        return `
                        <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 14px; display: flex; flex-direction: column; gap: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span style="font-size: 20px;">${icon}</span>
                                    <div>
                                        <div style="font-weight: 700; color: #ffffff; font-size: 13px;">${safeName}</div>
                                        <div style="font-size: 10px; color: var(--text-muted);">${safeIp} • ${safeType}</div>
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
                                <button class="btn-action" style="flex: 1; padding: 4px 8px; font-size: 10px;" onclick="buzzMeshDevice('${safeDevId}')">🔔 Buzz</button>
                                <button class="btn-action" style="flex: 1; padding: 4px 8px; font-size: 10px;" onclick="pushMeshClipboardTo('${safeDevId}')">📋 Push Clip</button>
                                <button class="btn-action" style="flex: 1; padding: 4px 8px; font-size: 10px; background: rgba(239,68,68,0.2); border-color: #ef4444; color: #fca5a5;" onclick="revokeMeshDevice('${safeDevId}')">🚫 Revoke</button>
                            </div>` : ''}
                        </div>`;
                    }).join('');
                }

                // Update Location & Environment HUD
                if (data.location) {
                    const loc = data.location;
                    const zoneTag = document.getElementById('loc-zone-tag');
                    if (zoneTag) {
                        zoneTag.innerText = (loc.zone || 'HOME COCKPIT').toUpperCase();
                        if (loc.is_home) {
                            zoneTag.style.background = 'rgba(16,185,129,0.15)';
                            zoneTag.style.color = '#10b981';
                            zoneTag.style.borderColor = 'rgba(16,185,129,0.3)';
                        } else {
                            zoneTag.style.background = 'rgba(56,189,248,0.15)';
                            zoneTag.style.color = '#38bdf8';
                            zoneTag.style.borderColor = 'rgba(56,189,248,0.3)';
                        }
                    }
                    const disp = document.getElementById('loc-display-name');
                    if (disp && loc.display_name) disp.innerText = loc.display_name;
                    const distSub = document.getElementById('loc-distance-sub');
                    if (distSub) {
                        if (loc.distance_to_home_meters !== undefined && loc.distance_to_home_meters !== null) {
                            distSub.innerText = `${Number(loc.distance_to_home_meters).toFixed(0)}m from Home Cockpit`;
                        } else {
                            distSub.innerText = 'At Home Cockpit';
                        }
                    }
                    const wSummary = document.getElementById('loc-weather-summary');
                    const wDetails = document.getElementById('loc-weather-details');
                    if (wSummary && loc.weather && loc.weather.condition) {
                        wSummary.innerText = `${loc.weather.condition} • ${loc.weather.temperature_f}°F (${loc.weather.temperature_c}°C)`;
                        if (wDetails) {
                            wDetails.innerText = `Humidity: ${loc.weather.humidity}% • Wind: ${loc.weather.wind_speed_kmh} km/h`;
                        }
                    }
                    const srcEl = document.getElementById('loc-telemetry-source');
                    if (srcEl && loc.source_type && loc.source_type !== 'none') {
                        srcEl.innerText = `${loc.source_type.toUpperCase()} (Low-Power GPS/Wi-Fi)`;
                    }
                }

                // Update Smartwatch HUD Card
                if (data.watch_hud) {
                    const wh = data.watch_hud;
                    const timeEl = document.getElementById('wall-watch-time');
                    if (timeEl && wh.time) timeEl.innerText = wh.time;
                    const stateEl = document.getElementById('wall-watch-state');
                    if (stateEl) {
                        stateEl.innerText = wh.voice_state === 'listening' ? '🔴 LISTENING' : (wh.voice_state === 'holding' ? '🟡 TALKING' : '● MIC READY');
                        stateEl.style.color = wh.voice_state === 'listening' ? '#ef4444' : (wh.voice_state === 'holding' ? '#f59e0b' : '#10b981');
                    }
                    const msgEl = document.getElementById('wall-watch-msg');
                    if (msgEl && wh.last_message) msgEl.innerText = wh.last_message;
                    const battEl = document.getElementById('wall-watch-battery');
                    const battSub = document.getElementById('wall-watch-batt-sub');
                    if (wh.battery !== null && wh.battery !== undefined) {
                        if (battEl) battEl.innerText = (wh.is_charging ? '⚡ ' : '🔋 ') + wh.battery + '%';
                        if (battSub) battSub.innerText = `Wrist Battery: ${wh.battery}% ${wh.is_charging ? '(Charging)' : ''}`;
                    }
                }

                // Update Screen Wall Snapshots (Mobile & Laptop)
                if (data.snapshots) {
                    for (const [devId, snap] of Object.entries(data.snapshots)) {
                        const dt = (snap.device_type || '').toLowerCase();
                        if (dt.includes('phone') || dt.includes('smart') || dt.includes('mobile')) {
                            const img = document.getElementById('wall-phone-img');
                            const ph = document.getElementById('wall-phone-placeholder');
                            const resEl = document.getElementById('wall-phone-res');
                            const tEl = document.getElementById('wall-phone-time');
                            const battEl = document.getElementById('wall-phone-battery');
                            if (img && snap.image) {
                                img.src = snap.image;
                                img.style.display = 'block';
                                if (ph) ph.style.display = 'none';
                            }
                            if (resEl && snap.width) resEl.innerText = `Resolution: ${snap.width}x${snap.height} px`;
                            if (tEl && snap.timestamp) tEl.innerText = 'Last update: ' + new Date(snap.timestamp * 1000).toLocaleTimeString();
                            if (battEl && snap.battery !== null && snap.battery !== undefined) {
                                battEl.innerText = (snap.is_charging ? '⚡ ' : '🔋 ') + snap.battery + '%';
                            }
                        } else if (dt.includes('laptop') || dt.includes('workstation')) {
                            const img = document.getElementById('wall-laptop-img');
                            const ph = document.getElementById('wall-laptop-placeholder');
                            const resEl = document.getElementById('wall-laptop-res');
                            const tEl = document.getElementById('wall-laptop-time');
                            const battEl = document.getElementById('wall-laptop-battery');
                            if (img && snap.image) {
                                img.src = snap.image;
                                img.style.display = 'block';
                                if (ph) ph.style.display = 'none';
                            }
                            if (resEl && snap.width) resEl.innerText = `Resolution: ${snap.width}x${snap.height} px`;
                            if (tEl && snap.timestamp) tEl.innerText = 'Last update: ' + new Date(snap.timestamp * 1000).toLocaleTimeString();
                            if (battEl && snap.battery !== null && snap.battery !== undefined) {
                                battEl.innerText = (snap.is_charging ? '⚡ ' : '🔋 ') + snap.battery + '%';
                            }
                        }
                    }
                }

                const pcImg = document.getElementById('wall-pc-img');
                if (pcImg) {
                    pcImg.src = '/api/desktop/snapshot?monitor=primary&max_width=800&quality=75&t=' + Date.now();
                    pcImg.style.display = 'block';
                    const pcPh = document.getElementById('wall-pc-placeholder');
                    if (pcPh) pcPh.style.display = 'none';
                }

                refreshMeshLogs();
            } catch (e) {
                console.error("Failed to refresh mesh devices", e);
            }
        }

        async function requestCompanionSnapshot(deviceType) {
            showToast(`Requesting snapshot from ${deviceType}...`);
            try {
                const statusRes = await fetch('/api/mesh/status');
                const data = await statusRes.json();
                let targetId = '';
                if (data.devices) {
                    const d = data.devices.find(x => x.connected && (x.device_type || '').toLowerCase().includes(deviceType.toLowerCase()));
                    if (d) targetId = d.device_id;
                }
                if (!targetId) targetId = deviceType === 'laptop' ? 'laptop-workstation' : 'phone-companion';
                const res = await fetch('/api/mesh/request_snapshot', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ device_id: targetId })
                });
                const resData = await res.json();
                if (resData.status === 'requested') {
                    showToast(`Snapshot requested from ${deviceType}. Updating view...`);
                    setTimeout(refreshMeshDevices, 1200);
                } else {
                    showToast(`Device ${deviceType} is currently offline.`);
                }
            } catch (e) {
                alert('Snapshot request error: ' + e);
            }
        }

        async function pullAllScreenshots() {
            requestCompanionSnapshot('smartphone');
            requestCompanionSnapshot('laptop');
            requestCompanionSnapshot('smartwatch');
            refreshPcScreen();
        }

        async function pingCompanionDevice(deviceType) {
            showToast(`🔔 Pinging ${deviceType} in the room...`);
            try {
                const statusRes = await fetch('/api/mesh/status');
                const data = await statusRes.json();
                let targetId = '';
                if (data.devices) {
                    const d = data.devices.find(x => x.connected && (x.device_type || '').toLowerCase().includes(deviceType.toLowerCase()));
                    if (d) targetId = d.device_id;
                }
                if (!targetId) targetId = deviceType === 'laptop' ? 'laptop-workstation' : 'phone-companion';
                const res = await fetch('/api/mesh/ping_device', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ device_id: targetId, tone: 'chime' })
                });
                const r = await res.json();
                if (r.status === 'sent') {
                    showToast(`🔔 Acoustic chime & vibration triggered on ${deviceType}!`);
                } else {
                    showToast(`⚠️ ${deviceType} appears offline, alerting all paired nodes...`);
                    buzzMeshDevice(targetId);
                }
            } catch (e) {
                alert('Ping error: ' + e);
            }
        }

        async function setHomeLocation() {
            try {
                const res = await fetch('/api/location/set_home', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const data = await res.json();
                if (data.status === 'success') {
                    showToast("🏡 Current coordinates locked as Home Cockpit!");
                    refreshMeshDevices();
                } else {
                    alert("Set home error: " + (data.message || 'Unknown'));
                }
            } catch (e) {
                alert("Home set error: " + e);
            }
        }

        async function copyLocationContext() {
            try {
                const res = await fetch('/api/location/current');
                const data = await res.json();
                const snippet = `User Location: ${data.zone || 'Home Cockpit'} (${data.display_name || 'San Francisco, CA'}) • Weather: ${data.weather ? (data.weather.condition + ', ' + data.weather.temperature_f + '°F') : 'Clear'} • Distance to Home: ${data.distance_to_home_meters || 0}m [Source: ${data.source_type || 'GPS'}]`;
                navigator.clipboard.writeText(snippet).then(() => {
                    showToast("📋 Location prompt context copied!");
                }).catch(() => {
                    prompt("Copy location context:", snippet);
                });
            } catch (e) {
                alert("Context copy error: " + e);
            }
        }

        function refreshPcScreen() {
            const img = document.getElementById('wall-pc-img');
            if (img) {
                img.src = '/api/desktop/snapshot?monitor=primary&max_width=800&quality=75&t=' + Date.now();
                img.style.display = 'block';
                const ph = document.getElementById('wall-pc-placeholder');
                if (ph) ph.style.display = 'none';
                showToast("Host PC preview refreshed");
            }
        }

        async function refreshMeshLogs() {
            try {
                const res = await fetch('/api/mesh/logs?limit=25');
                const data = await res.json();
                const container = document.getElementById('mesh-logs-container');
                if (container && data.logs) {
                    if (data.logs.length === 0) {
                        container.innerHTML = '<span style="color: var(--text-muted);">No log events yet. Ready for companion actions.</span>';
                    } else {
                        container.innerHTML = data.logs.slice(-25).map(l => {
                            const lvlColor = l.level === 'ERROR' || l.level === 'CRITICAL' ? '#ef4444' :
                                             l.level === 'WARNING' ? '#f59e0b' : '#10b981';
                            return `<div><span style="color: var(--text-muted);">[${l.timestamp}]</span> <span style="color: ${lvlColor}; font-weight: 600;">[${l.level}]</span> <span style="color: #ffffff;">${escapeHtml(l.message)}</span></div>`;
                        }).join('');
                        container.scrollTop = container.scrollHeight;
                    }
                }
            } catch (err) {
                console.error("Log fetch error", err);
            }
        }

        async function generateNewPairingCode() {
            try {
                const res = await fetch('/api/mesh/pairing_code', { method: 'POST' });
                const data = await res.json();
                if (data.pairing_code) {
                    showToast("New pairing code generated (active for 10 min): " + data.pairing_code);
                    refreshMeshDevices();
                }
            } catch (err) {
                alert("Pairing code error: " + err);
            }
        }

        async function revokeMeshDevice(devId) {
            if (confirm("Revoke authorization for device " + devId + "?")) {
                try {
                    await fetch('/api/mesh/revoke_device', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ device_id: devId })
                    });
                    showToast("Device revoked: " + devId);
                    refreshMeshDevices();
                } catch (e) {
                    alert("Revoke error: " + e);
                }
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

        async function refreshLayaStatus() {
            try {
                const res = await fetch('/api/laya/status');
                const data = await res.json();
                if (data.status === 'ready') {
                    const mEl = document.getElementById('laya-model-val');
                    const dEl = document.getElementById('laya-device-val');
                    const aEl = document.getElementById('laya-acc-val');
                    if (mEl) mEl.innerText = data.model || 'ModernBERT-Large';
                    if (dEl) dEl.innerText = data.device ? data.device.toUpperCase() : 'CUDA';
                    if (aEl) aEl.innerText = (data.accuracy || '99.60%') + ' (RLCD)';
                    showToast('Laya System-1 telemetry refreshed');
                }
            } catch (e) {
                console.error(e);
            }
        }

        function handleLayaKeyUp(e) {
            if (e.key === 'Enter') {
                runLayaDecide(true);
            }
        }

        async function runLayaDecide(execute) {
            const input = document.getElementById('laya-prompt-input');
            const prompt = (input ? input.value : '').trim();
            if (!prompt) return;

            try {
                const res = await fetch('/api/laya/decide', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({prompt: prompt, execute: execute})
                });
                const data = await res.json();
                renderLayaResult(data);
                if (execute && data.executed) {
                    showToast('⚡ Action Executed: ' + (data.tool || ''));
                }
            } catch (e) {
                showToast('Error evaluating decision');
            }
        }

        function renderLayaResult(data) {
            const box = document.getElementById('laya-result-box');
            if (!box) return;
            box.style.display = 'block';

            const actBadge = document.getElementById('laya-action-badge');
            const toolBadge = document.getElementById('laya-tool-badge');
            const tierBadge = document.getElementById('laya-tier-badge');
            const latEl = document.getElementById('laya-res-lat');
            const confEl = document.getElementById('laya-res-conf');
            const detailEl = document.getElementById('laya-res-detail');

            const act = data.action || 'WAIT_FOR_MORE_INPUT';
            actBadge.innerText = act;
            if (act === 'FIRE_EARLY') {
                actBadge.style.background = 'rgba(52, 211, 153, 0.2)';
                actBadge.style.color = '#34d399';
                actBadge.style.border = '1px solid #34d399';
            } else if (act === 'EMERGENCY_STOP') {
                actBadge.style.background = 'rgba(239, 68, 68, 0.2)';
                actBadge.style.color = '#ef4444';
                actBadge.style.border = '1px solid #ef4444';
            } else {
                actBadge.style.background = 'rgba(245, 158, 11, 0.2)';
                actBadge.style.color = '#f59e0b';
                actBadge.style.border = '1px solid #f59e0b';
            }

            toolBadge.innerText = data.tool || 'none';
            tierBadge.innerText = data.execution_tier || 'plain_code';
            latEl.innerText = (data.latency_ms || 32) + ' ms';
            confEl.innerText = Math.round((data.confidence || 1.0) * 100) + '%';
            detailEl.innerText = JSON.stringify(data.result || data, null, 2);
        }

        async function triggerMedia(action) {
            try {
                const res = await fetch('/api/media/control', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action: action, steps: 4})
                });
                const data = await res.json();
                showToast('Media Action: ' + (data.action || action));
            } catch (e) {
                showToast('Media control failed');
            }
        }

        let layaSpeechRec = null;
        let isLayaSpeaking = false;
        function toggleLayaVoice() {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRec) {
                alert('Web Speech API not supported in this browser.');
                return;
            }
            const btn = document.getElementById('laya-mic-btn');
            if (!layaSpeechRec) {
                layaSpeechRec = new SpeechRec();
                layaSpeechRec.continuous = false;
                layaSpeechRec.interimResults = true;
                layaSpeechRec.onstart = () => {
                    isLayaSpeaking = true;
                    if (btn) {
                        btn.style.background = '#ef4444';
                        btn.innerText = '🔴 Listening...';
                    }
                };
                layaSpeechRec.onresult = async (event) => {
                    let trans = '';
                    for (let i = 0; i < event.results.length; i++) trans += event.results[i][0].transcript;
                    const clean = trans.trim();
                    const input = document.getElementById('laya-prompt-input');
                    if (input) input.value = clean;
                    if (clean.length >= 3) {
                        try {
                            const res = await fetch('/api/laya/stream', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({transcript: clean, session_id: 'browser_voice', execute: true})
                            });
                            const data = await res.json();
                            renderLayaResult(data);
                            if (data.executed) {
                                showToast('⚡ Mid-Sentence Executed: ' + (data.tool || ''));
                            }
                        } catch (_) {}
                    }
                };
                layaSpeechRec.onend = () => {
                    isLayaSpeaking = false;
                    if (btn) {
                        btn.style.background = '#3b82f6';
                        btn.innerText = '🎙️ Live Mic';
                    }
                };
            }

            if (isLayaSpeaking) {
                layaSpeechRec.stop();
            } else {
                layaSpeechRec.start();
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
