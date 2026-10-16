# -*- coding: utf-8 -*-
"""
Hermes Omni-Mesh Companions Package
Dedicated modular architecture for Smartwatch, Smartphone, and Laptop.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from .hub import (
    MeshDevice,
    OmniMeshHub,
    get_omni_mesh_hub,
    get_local_lan_ip,
    read_pc_clipboard,
    write_pc_clipboard,
    generate_qr_code_png_base64,
)
from .smartwatch import (
    SmartwatchBridge,
    get_smartwatch_bridge,
    get_smartwatch_manifest,
    render_smartwatch_html,
)
from .smartphone import (
    SmartphoneBridge,
    get_smartphone_bridge,
    get_smartphone_manifest,
    get_smartphone_sw,
    render_smartphone_html,
)
from .laptop import (
    LaptopBridge,
    get_laptop_bridge,
    get_laptop_manifest,
    render_laptop_html,
)

_COMPANIONS_DIR = Path(__file__).resolve().parent


def register_companion_routes(app: FastAPI):
    """Registers all standalone companion routes and WebSocket endpoints onto FastAPI app."""
    hub = get_omni_mesh_hub()

    # ── SMARTWATCH ROUTES (+ SHORT WRIST ALIASES) ───────────────────────────
    @app.get("/companions/smartwatch", response_class=HTMLResponse)
    @app.get("/companion/smartwatch", response_class=HTMLResponse)
    @app.get("/companion/watch", response_class=HTMLResponse)
    @app.get("/watch", response_class=HTMLResponse)
    @app.get("/w", response_class=HTMLResponse)
    async def get_smartwatch_page():
        return HTMLResponse(content=render_smartwatch_html(hub.lan_ip, hub.port))

    @app.get("/companions/smartwatch/manifest.json")
    async def get_smartwatch_manifest_route():
        return JSONResponse(content=get_smartwatch_manifest())

    @app.get("/companions/smartwatch/web/watch.css")
    async def get_smartwatch_css():
        css_file = _COMPANIONS_DIR / "smartwatch" / "web" / "watch.css"
        return Response(content=css_file.read_text(encoding="utf-8") if css_file.exists() else "", media_type="text/css")

    @app.get("/companions/smartwatch/web/watch.js")
    async def get_smartwatch_js():
        js_file = _COMPANIONS_DIR / "smartwatch" / "web" / "watch.js"
        return Response(content=js_file.read_text(encoding="utf-8") if js_file.exists() else "", media_type="application/javascript")

    # ── SMARTPHONE ROUTES (+ SHORT MOBILE ALIASES) ──────────────────────────
    @app.get("/companions/smartphone", response_class=HTMLResponse)
    @app.get("/companion/smartphone", response_class=HTMLResponse)
    @app.get("/companion/mobile", response_class=HTMLResponse)
    @app.get("/phone", response_class=HTMLResponse)
    @app.get("/mobile", response_class=HTMLResponse)
    @app.get("/m", response_class=HTMLResponse)
    async def get_smartphone_page():
        return HTMLResponse(content=render_smartphone_html(hub.lan_ip, hub.port))

    @app.get("/companions/smartphone/manifest.json")
    async def get_smartphone_manifest_route():
        return JSONResponse(content=get_smartphone_manifest())

    @app.get("/companions/smartphone/sw.js")
    async def get_smartphone_sw_route():
        return Response(content=get_smartphone_sw(), media_type="application/javascript")

    @app.get("/companions/smartphone/web/mobile.css")
    async def get_smartphone_css():
        css_file = _COMPANIONS_DIR / "smartphone" / "web" / "mobile.css"
        return Response(content=css_file.read_text(encoding="utf-8") if css_file.exists() else "", media_type="text/css")

    @app.get("/companions/smartphone/web/mobile.js")
    async def get_smartphone_js():
        js_file = _COMPANIONS_DIR / "smartphone" / "web" / "mobile.js"
        return Response(content=js_file.read_text(encoding="utf-8") if js_file.exists() else "", media_type="application/javascript")

    # ── LAPTOP ROUTES (+ SHORT ALIASES) ─────────────────────────────────────
    @app.get("/companions/laptop", response_class=HTMLResponse)
    @app.get("/companion/laptop", response_class=HTMLResponse)
    @app.get("/laptop", response_class=HTMLResponse)
    @app.get("/l", response_class=HTMLResponse)
    async def get_laptop_page():
        return HTMLResponse(content=render_laptop_html(hub.lan_ip, hub.port))

    @app.get("/companions/laptop/manifest.json")
    async def get_laptop_manifest_route():
        return JSONResponse(content=get_laptop_manifest())

    @app.get("/companions/laptop/web/laptop.css")
    async def get_laptop_css():
        css_file = _COMPANIONS_DIR / "laptop" / "web" / "laptop.css"
        return Response(content=css_file.read_text(encoding="utf-8") if css_file.exists() else "", media_type="text/css")

    @app.get("/companions/laptop/web/laptop.js")
    async def get_laptop_js():
        js_file = _COMPANIONS_DIR / "laptop" / "web" / "laptop.js"
        return Response(content=js_file.read_text(encoding="utf-8") if js_file.exists() else "", media_type="application/javascript")

    # ── UNIFIED / BACKWARD-COMPATIBLE /companion ROUTE ─────────────────────
    @app.get("/companion", response_class=HTMLResponse)
    async def get_companion_page(mode: Optional[str] = None):
        if mode == "watch":
            return HTMLResponse(content=render_smartwatch_html(hub.lan_ip, hub.port))
        elif mode == "laptop":
            return HTMLResponse(content=render_laptop_html(hub.lan_ip, hub.port))
        return HTMLResponse(content=render_smartphone_html(hub.lan_ip, hub.port))

    @app.get("/companion/manifest.json")
    async def get_companion_manifest():
        return JSONResponse(content=get_smartphone_manifest())

    @app.get("/companion/sw.js")
    async def get_companion_sw():
        return Response(content=get_smartphone_sw(), media_type="application/javascript")

    # ── STANDALONE NATIVE APP INSTALLERS (MOBILE & WATCH) ──────────────────
    @app.get("/api/companion/install/ios_app.mobileconfig")
    async def download_ios_mobileconfig(target: str = "all"):
        """
        Generates an Apple iOS/iPadOS/watchOS Configuration Profile (.mobileconfig)
        that installs Hermes Mobile and Hermes Watch HUD as 100% Full-Screen
        Standalone WebClip Apps (FullScreen=true, no Safari address bar).
        """
        from .auth import get_pairing_manager
        pair_code = get_pairing_manager().create_pairing_code(ttl_seconds=86400 * 30)
        phone_url = f"http://{hub.lan_ip}:{hub.port}/phone?pair={pair_code}"
        watch_url = f"http://{hub.lan_ip}:{hub.port}/watch?pair={pair_code}"
        mobileconfig_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>FullScreen</key>
            <true/>
            <key>IgnoreManifestScope</key>
            <true/>
            <key>IsRemovable</key>
            <true/>
            <key>Label</key>
            <string>Hermes AI</string>
            <key>PayloadDescription</key>
            <string>Hermes Standalone Full-Screen Mobile Companion</string>
            <key>PayloadDisplayName</key>
            <string>Hermes Mobile App</string>
            <key>PayloadIdentifier</key>
            <string>ai.hermes.companion.mobile.webclip</string>
            <key>PayloadType</key>
            <string>com.apple.webClip.managed</string>
            <key>PayloadUUID</key>
            <string>8A4E9921-1000-4000-8000-0013EF600442</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>Precomposed</key>
            <true/>
            <key>URL</key>
            <string>{phone_url}</string>
        </dict>
        <dict>
            <key>FullScreen</key>
            <true/>
            <key>IgnoreManifestScope</key>
            <true/>
            <key>IsRemovable</key>
            <true/>
            <key>Label</key>
            <string>Hermes Watch</string>
            <key>PayloadDescription</key>
            <string>Hermes Standalone AMOLED Smartwatch HUD</string>
            <key>PayloadDisplayName</key>
            <string>Hermes Watch HUD</string>
            <key>PayloadIdentifier</key>
            <string>ai.hermes.companion.watch.webclip</string>
            <key>PayloadType</key>
            <string>com.apple.webClip.managed</string>
            <key>PayloadUUID</key>
            <string>8A4E9922-1000-4000-8000-0013EF600442</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>Precomposed</key>
            <true/>
            <key>URL</key>
            <string>{watch_url}</string>
        </dict>
    </array>
    <key>PayloadDescription</key>
    <string>Installs Hermes Mobile Companion and Hermes Watch HUD as full-screen native apps connected to {hub.lan_ip}:{hub.port}.</string>
    <key>PayloadDisplayName</key>
    <string>Hermes AI Native Companion Suite</string>
    <key>PayloadIdentifier</key>
    <string>ai.hermes.companion.suite</string>
    <key>PayloadOrganization</key>
    <string>Hermes Autonomous Systems</string>
    <key>PayloadRemovalDisallowed</key>
    <false/>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>8A4E9920-1000-4000-8000-0013EF600442</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>"""
        return Response(
            content=mobileconfig_xml.encode("utf-8"),
            media_type="application/x-apple-aspen-config",
            headers={"Content-Disposition": 'attachment; filename="Hermes_Native_Apps.mobileconfig"'},
        )

    @app.get("/api/companion/install/watch_adb.bat")
    async def download_watch_adb_installer():
        """
        Generates a 1-Click Windows Batch Installer for WearOS Smartwatches (Galaxy Watch, Pixel Watch)
        and Android Smartphones over Wireless ADB. Configures Chrome to treat http://{hub.lan_ip}:{hub.port}
        as a secure native origin and launches the standalone full-screen HUD on the watch/phone.
        """
        from .auth import get_pairing_manager
        pair_code = get_pairing_manager().create_pairing_code(ttl_seconds=86400 * 30)
        bat_content = f"""@echo off
title Hermes Smartwatch & Android Native App Installer
color 0B
echo ============================================================================
echo   HERMES OMNI-MESH: 1-CLICK SMARTWATCH (WEAR OS) ^& ANDROID APP INSTALLER
echo   Host PC: http://{hub.lan_ip}:{hub.port}
echo ============================================================================
echo.
echo   [HOW TO USE FOR SMARTWATCH (Galaxy Watch / Pixel Watch / Wear OS)]:
echo   1. On your Watch: Settings -^> Developer Options -^> Enable "ADB Debugging"
echo   2. Tap "Wireless debugging" on Watch and note the IP:Port (e.g. 10.0.0.95:5555)
echo   (Or press ENTER to auto-configure your Android Phone at 10.0.0.84:5555)
echo.
set /p TARGET_ADDR="Enter Watch or Phone IP:Port [default: 10.0.0.84:5555]: "
if "%TARGET_ADDR%"=="" set TARGET_ADDR=10.0.0.84:5555

echo.
echo [*] Connecting to %TARGET_ADDR% via Wireless ADB...
adb connect %TARGET_ADDR%

echo [*] Whitelisting Hermes Host (http://{hub.lan_ip}:{hub.port}) as a Native Secure Origin...
adb -s %TARGET_ADDR% shell "echo 'chrome --unsafely-treat-insecure-origin-as-secure=http://{hub.lan_ip}:{hub.port} --no-first-run' > /data/local/tmp/chrome-command-line"

echo.
set /p DEV_MODE="Is this a Smartwatch (W) or Smartphone (P)? [W/P, default: W]: "
if /I "%DEV_MODE%"=="P" (
    echo [*] Launching Hermes Standalone Smartphone App on %TARGET_ADDR%...
    adb -s %TARGET_ADDR% shell am start -a android.intent.action.VIEW -d "http://{hub.lan_ip}:{hub.port}/phone?pair={pair_code}"
) else (
    echo [*] Launching Hermes Standalone Smartwatch HUD on %TARGET_ADDR%...
    adb -s %TARGET_ADDR% shell am start -a android.intent.action.VIEW -d "http://{hub.lan_ip}:{hub.port}/watch?pair={pair_code}"
)

echo.
echo [+] Done! Tap "Add to Home Screen" / "Install App" on your device for permanent icon.
pause
"""
        return Response(
            content=bat_content.encode("utf-8"),
            media_type="application/x-bat",
            headers={"Content-Disposition": 'attachment; filename="Install-Hermes-Watch-And-Phone.bat"'},
        )

    @app.post("/api/mesh/heartbeat")
    async def api_mesh_http_heartbeat(request: Request):
        """Lightweight HTTP keepalive for mobile/watch companions when backgrounded."""
        client_ip = request.client.host if request.client else "127.0.0.1"
        try:
            data = await request.json()
        except Exception:
            data = {}
        dev_id = str(data.get("device_id", ""))
        if dev_id and dev_id in hub.devices:
            dev = hub.devices[dev_id]
            dev.last_seen = time.time()
            dev.connected = True
            if "battery" in data and data["battery"] is not None:
                dev.battery_level = int(data["battery"])
            if "is_charging" in data and data["is_charging"] is not None:
                dev.is_charging = bool(data["is_charging"])
            return JSONResponse(content={"status": "ok", "connected": True, "host_ip": hub.lan_ip})
        return JSONResponse(content={"status": "ok", "connected": False, "host_ip": hub.lan_ip})

    # ── TURNKEY 1-CLICK ONBOARDING & CONNECT HUB ─────────────────────────────
    @app.get("/connect", response_class=HTMLResponse)
    async def get_connect_hub_page():
        from .connect_page import render_connect_hub_html
        from .auth import get_pairing_manager
        pm = get_pairing_manager()
        pair_code = pm.create_pairing_code(ttl_seconds=1800)
        phone_qr = hub.get_pairing_qr("smartphone")
        watch_qr = hub.get_pairing_qr("smartwatch")
        laptop_url = hub.get_companion_url("laptop", pairing_code=pair_code)
        return HTMLResponse(content=render_connect_hub_html(
            lan_ip=hub.lan_ip,
            port=hub.port,
            pairing_code=pair_code,
            phone_qr_b64=phone_qr,
            watch_qr_b64=watch_qr,
            laptop_url=laptop_url,
        ))

    @app.get("/api/power/download/{script_type}")
    async def download_wake_script(script_type: str):
        from local_model_lab.hermes_power import generate_standalone_wake_scripts
        scripts = generate_standalone_wake_scripts()
        st = script_type.lower()
        if st in ("bat", "cmd"):
            p = scripts["bat"]
            fname = "Wake-Hermes.bat"
            media = "application/x-bat"
        elif st in ("sh", "bash"):
            p = scripts["sh"]
            fname = "wake_hermes.sh"
            media = "application/x-sh"
        else:
            p = scripts["py"]
            fname = "wake_hermes.py"
            media = "text/x-python"
        
        with open(p, "rb") as f:
            content = f.read()
        return Response(
            content=content,
            media_type=media,
            headers={"Content-Disposition": f'attachment; filename="{fname}"'}
        )

    @app.get("/api/download/catalog")
    async def download_feature_catalog():
        from pathlib import Path
        candidates = [
            _COMPANIONS_DIR.parent / "Hermes_Complete_Feature_and_Test_Catalog.xlsx",
            _COMPANIONS_DIR.parent.parent / "Hermes_Complete_Feature_and_Test_Catalog.xlsx",
            Path("Hermes_Complete_Feature_and_Test_Catalog.xlsx"),
        ]
        target = None
        for c in candidates:
            if c.exists():
                target = c
                break
        if target:
            with open(target, "rb") as f:
                content = f.read()
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": 'attachment; filename="Hermes_Complete_Feature_and_Test_Catalog.xlsx"'}
            )
        return JSONResponse(content={"error": "Catalog file not found"}, status_code=404)

    # ── COMPANION LOGS & AUTH ADMIN APIS ────────────────────────────────────
    @app.get("/api/mesh/logs")
    async def get_mesh_logs(limit: int = 50, level: Optional[str] = None):
        from .logger import get_recent_companion_logs
        return JSONResponse(content={"logs": get_recent_companion_logs(limit=limit, min_level=level)})

    @app.get("/api/mesh/paired_devices")
    async def get_mesh_paired_devices():
        from .auth import get_pairing_manager
        return JSONResponse(content={"devices": get_pairing_manager().list_paired_devices()})

    @app.post("/api/mesh/revoke_device")
    async def revoke_mesh_device(request: Request):
        from .auth import get_pairing_manager
        data = await request.json()
        dev_id = str(data.get("device_id", ""))
        ok = get_pairing_manager().revoke_device(dev_id)
        if ok:
            await hub.unregister_connection(dev_id, immediate=True)
        return JSONResponse(content={"status": "revoked" if ok else "not_found", "device_id": dev_id})

    @app.post("/api/mesh/pairing_code")
    async def generate_pairing_code_route():
        from .auth import get_pairing_manager
        code = get_pairing_manager().create_pairing_code(ttl_seconds=600)
        return JSONResponse(content={"pairing_code": code, "expires_in": 600})

    # ── ALWAYS-ON GEOLOCATION INTELLIGENCE & CONTEXT APIS ───────────────────
    @app.get("/api/location/current")
    async def get_current_location_route():
        from local_model_lab.hermes_location import get_location_engine
        engine = get_location_engine()
        return JSONResponse(content=engine.get_current())

    @app.post("/api/location/update")
    async def update_location_route(request: Request):
        from local_model_lab.hermes_location import get_location_engine
        data = await request.json()
        lat = data.get("latitude")
        lon = data.get("longitude")
        if lat is None or lon is None:
            return JSONResponse(content={"error": "latitude and longitude required"}, status_code=400)
        engine = get_location_engine()
        res = engine.update_location(
            latitude=float(lat),
            longitude=float(lon),
            accuracy=float(data.get("accuracy", 0.0)),
            altitude=data.get("altitude"),
            speed=data.get("speed"),
            heading=data.get("heading"),
            source_device=str(data.get("device_id", "manual-api")),
            source_type=str(data.get("source_type", "smartphone")),
        )
        return JSONResponse(content=res)

    @app.post("/api/location/set_home")
    async def set_home_location_route(request: Request):
        from local_model_lab.hermes_location import get_location_engine
        data = {}
        try:
            data = await request.json()
        except Exception:
            pass
        engine = get_location_engine()
        res = engine.set_home(
            latitude=float(data["latitude"]) if "latitude" in data else None,
            longitude=float(data["longitude"]) if "longitude" in data else None,
        )
        return JSONResponse(content=res)

    @app.get("/api/location/history")
    async def get_location_history_route():
        from local_model_lab.hermes_location import get_location_engine
        engine = get_location_engine()
        return JSONResponse(content={"history": engine.get_history()})

    # ── COMPANION MATRIX: SCREEN SNAPSHOT & DEVICE PING APIS ────────────────
    @app.post("/api/mesh/ping_device")
    async def ping_mesh_device(request: Request):
        data = await request.json()
        dev_id = str(data.get("device_id", ""))
        tone = str(data.get("tone", "chime"))
        if not dev_id:
            return JSONResponse(content={"error": "device_id required"}, status_code=400)
        ok = await hub.ping_device(dev_id, tone=tone)
        return JSONResponse(content={"status": "sent" if ok else "device_offline", "device_id": dev_id})

    @app.post("/api/mesh/request_snapshot")
    async def request_companion_snapshot(request: Request):
        data = await request.json()
        dev_id = str(data.get("device_id", ""))
        if not dev_id:
            return JSONResponse(content={"error": "device_id required"}, status_code=400)
        ok = await hub.request_screen_snapshot(dev_id)
        return JSONResponse(content={"status": "requested" if ok else "device_offline", "device_id": dev_id})

    @app.get("/api/mesh/companion_snapshots")
    async def get_companion_snapshots():
        return JSONResponse(content={"snapshots": hub.device_snapshots})

    @app.get("/api/mesh/watch_hud")
    async def get_watch_hud_route():
        return JSONResponse(content={"hud": hub.watch_hud_state})



__all__ = [
    "OmniMeshHub",
    "MeshDevice",
    "get_omni_mesh_hub",
    "get_local_lan_ip",
    "read_pc_clipboard",
    "write_pc_clipboard",
    "generate_qr_code_png_base64",
    "SmartwatchBridge",
    "get_smartwatch_bridge",
    "SmartphoneBridge",
    "get_smartphone_bridge",
    "LaptopBridge",
    "get_laptop_bridge",
    "register_companion_routes",
]
