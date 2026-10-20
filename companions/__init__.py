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

    # ── PWA PNG ICONS & ROOT SERVICE WORKER (ANDROID / WEAR OS WEBAPK) ──────
    def _generate_hermes_png_icon(size: int = 192) -> bytes:
        import io
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", (size, size), (6, 9, 12, 255))
            draw = ImageDraw.Draw(img)
            pad = max(8, size // 12)
            draw.ellipse([pad, pad, size - pad, size - pad], fill=(5, 46, 36, 255), outline=(16, 185, 129, 255), width=max(4, size // 32))
            # Lightning bolt polygon
            cx, cy = size // 2, size // 2
            r = size // 3
            bolt = [
                (cx + r * 0.15, cy - r),
                (cx - r * 0.55, cy + r * 0.08),
                (cx - r * 0.05, cy + r * 0.08),
                (cx - r * 0.20, cy + r),
                (cx + r * 0.55, cy - r * 0.08),
                (cx + r * 0.05, cy - r * 0.08),
            ]
            draw.polygon(bolt, fill=(16, 185, 129, 255))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            import base64
            return base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")

    @app.get("/companions/icon-192.png")
    async def get_hermes_icon_192():
        return Response(content=_generate_hermes_png_icon(192), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/companions/icon-512.png")
    async def get_hermes_icon_512():
        return Response(content=_generate_hermes_png_icon(512), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/sw.js")
    @app.get("/companions/smartwatch/sw.js")
    async def get_root_sw_route():
        return Response(
            content=get_smartphone_sw(),
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"},
        )

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
        return Response(
            content=get_smartphone_sw(),
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"},
        )

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
        return Response(
            content=get_smartphone_sw(),
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"},
        )

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

    @app.get("/download/hermes-pixel7pro.apk")
    @app.get("/api/companion/install/hermes-pixel7pro.apk")
    async def download_pixel7pro_apk():
        """Serves the compiled & V2/V3-signed native Android APK for Google Pixel 7 Pro."""
        from local_model_lab.apk_builder import APK_OUTPUT_DIR, build_all_hermes_apks
        apk_path = APK_OUTPUT_DIR / "hermes-pixel7pro.apk"
        if not apk_path.exists():
            build_all_hermes_apks(host_ip=hub.lan_ip, port=hub.port)
        return Response(
            content=apk_path.read_bytes(),
            media_type="application/vnd.android.package-archive",
            headers={
                "Content-Disposition": 'attachment; filename="hermes-pixel7pro.apk"',
                "Cache-Control": "no-cache",
            },
        )

    @app.get("/download/hermes-galaxy-watch8.apk")
    @app.get("/api/companion/install/hermes-galaxy-watch8.apk")
    async def download_galaxy_watch8_apk():
        """Serves the compiled & V2/V3-signed native Wear OS APK for Samsung Galaxy Watch 8."""
        from local_model_lab.apk_builder import APK_OUTPUT_DIR, build_all_hermes_apks
        apk_path = APK_OUTPUT_DIR / "hermes-galaxy-watch8.apk"
        if not apk_path.exists():
            build_all_hermes_apks(host_ip=hub.lan_ip, port=hub.port)
        return Response(
            content=apk_path.read_bytes(),
            media_type="application/vnd.android.package-archive",
            headers={
                "Content-Disposition": 'attachment; filename="hermes-galaxy-watch8.apk"',
                "Cache-Control": "no-cache",
            },
        )

    @app.post("/api/watch/telemetry")
    async def ingest_watch_telemetry_route(request: Request):
        """
        Ingests live biometric & health sensor telemetry from Samsung Galaxy Watch 8
        and Google Pixel 7 Pro, computes the Hermes BioActive Readiness Score (0-100),
        and triggers proactive notifications if anomalies are detected.
        """
        from local_model_lab.watch_health_analyzer import get_watch_health_analyzer
        try:
            data = await request.json()
        except Exception:
            data = {}
        analyzer = get_watch_health_analyzer()
        result = analyzer.ingest_telemetry(data, trigger_notifications=True)
        # Update Watch HUD state on hub as well
        hub.watch_hud_state["biometrics"] = {
            "readiness_score": result["analysis"]["readiness_score"],
            "status_label": result["analysis"]["status_label"],
            "heart_rate_bpm": result["sample"]["heart_rate_bpm"],
            "spo2_pct": result["sample"]["spo2_pct"],
            "stress_score": result["sample"]["stress_score"],
            "steps": result["sample"]["steps"],
            "watch_battery_pct": result["sample"]["watch_battery_pct"],
            "updated_at": result["sample"]["iso_time"],
        }
        return JSONResponse(content=result)

    @app.get("/api/watch/analytics")
    async def get_watch_analytics_route():
        """Returns the latest Samsung Galaxy Watch 8 & Pixel 7 Pro biometric analysis and history."""
        from local_model_lab.watch_health_analyzer import get_watch_health_analyzer
        analyzer = get_watch_health_analyzer()
        return JSONResponse(content=analyzer.get_latest_analytics())

    @app.post("/api/watch/simulate")
    async def simulate_watch_telemetry_route(request: Request):
        """
        Simulates either an 'optimal' biometric sync or an 'anomaly' alert from Samsung Galaxy Watch 8
        so the user can test biometric health analysis & proactive notifications with 1 click.
        """
        from local_model_lab.watch_health_analyzer import get_watch_health_analyzer
        try:
            body = await request.json()
        except Exception:
            body = {}
        mode = str(body.get("mode", "optimal")).lower()
        analyzer = get_watch_health_analyzer()
        if mode == "anomaly":
            sample = {
                "device_model": "Samsung Galaxy Watch 8",
                "phone_model": "Google Pixel 7 Pro",
                "heart_rate_bpm": 136,
                "resting_hr_bpm": 61,
                "hrv_rmssd_ms": 24.0,
                "spo2_pct": 92.0,
                "stress_score": 86,
                "sleep_score": 68,
                "sleep_duration_hours": 5.4,
                "deep_sleep_minutes": 38,
                "rem_sleep_minutes": 55,
                "steps": 6840,
                "active_calories_kcal": 490,
                "skin_temp_c": 36.9,
                "watch_battery_pct": 78,
                "phone_battery_pct": 84,
                "is_wearing": True,
                "activity_state": "resting",
                "source": "watch8_biometric_simulation_anomaly",
            }
        else:
            sample = {
                "device_model": "Samsung Galaxy Watch 8",
                "phone_model": "Google Pixel 7 Pro",
                "heart_rate_bpm": 66,
                "resting_hr_bpm": 58,
                "hrv_rmssd_ms": 62.5,
                "spo2_pct": 98.0,
                "stress_score": 24,
                "sleep_score": 89,
                "sleep_duration_hours": 7.8,
                "deep_sleep_minutes": 88,
                "rem_sleep_minutes": 104,
                "steps": 8420,
                "active_calories_kcal": 560,
                "skin_temp_c": 36.5,
                "watch_battery_pct": 88,
                "phone_battery_pct": 92,
                "is_wearing": True,
                "activity_state": "resting",
                "source": "watch8_biometric_simulation_optimal",
            }
        # Reset cooldown on manual simulation so notification always fires when testing anomaly
        if mode == "anomaly":
            analyzer._last_alert_ts.clear()
        result = analyzer.ingest_telemetry(sample, trigger_notifications=True)
        return JSONResponse(content=result)

    @app.post("/api/watch/adb_install")
    async def api_watch_adb_install_route(request: Request):
        """
        1-Click Wireless ADB APK Installer for Samsung Galaxy Watch 8 or Google Pixel 7 Pro.
        Connects (and optionally pairs) via ADB and installs the native signed APK.
        """
        from local_model_lab.apk_builder import APK_OUTPUT_DIR, build_all_hermes_apks
        from local_model_lab.watch_health_analyzer import install_apk_via_wireless_adb
        try:
            data = await request.json()
        except Exception:
            data = {}
        target_ip_port = str(data.get("target_ip_port", "")).strip()
        device_type = str(data.get("device_type", "watch")).lower()
        pair_ip_port = str(data.get("pair_ip_port", "")).strip() or None
        pair_code = str(data.get("pair_code", "")).strip() or None

        if not target_ip_port:
            return JSONResponse(content={"ok": False, "error": "target_ip_port (e.g. 10.0.0.95:5555) is required"}, status_code=400)

        apk_name = "hermes-galaxy-watch8.apk" if device_type == "watch" else "hermes-pixel7pro.apk"
        apk_path = APK_OUTPUT_DIR / apk_name
        if not apk_path.exists():
            build_all_hermes_apks(host_ip=hub.lan_ip, port=hub.port)

        res = install_apk_via_wireless_adb(
            target_ip_port=target_ip_port,
            apk_path=str(apk_path),
            pair_ip_port=pair_ip_port,
            pair_code=pair_code,
        )
        return JSONResponse(content=res)

    @app.get("/api/companion/install/watch_adb.bat")
    async def download_watch_adb_installer():
        """
        Generates a 1-Click Windows Batch Installer for Samsung Galaxy Watch 8 (Wear OS)
        and Google Pixel 7 Pro over Wireless ADB. Installs the real signed native APK
        (hermes-galaxy-watch8.apk / hermes-pixel7pro.apk) and launches the native app.
        """
        bat_content = f"""@echo off
title Hermes Native APK Installer — Pixel 7 Pro ^& Samsung Galaxy Watch 8
color 0B
set ADB_EXE="%LOCALAPPDATA%\\Android\\Sdk\\platform-tools\\adb.exe"
if not exist %ADB_EXE% set ADB_EXE=adb

echo ============================================================================
echo   HERMES SOVEREIGN: NATIVE APK INSTALLER (PIXEL 7 PRO ^& GALAXY WATCH 8)
echo   Host PC: http://{hub.lan_ip}:{hub.port}
echo ============================================================================
echo.
echo   [HOW TO ENABLE WIRELESS DEBUGGING ON SAMSUNG GALAXY WATCH 8]:
echo   1. Watch Settings -^> About Watch -^> Software Info -^> Tap "Software Version" 7 times
echo   2. Watch Settings -^> Developer Options -^> Enable "ADB Debugging"
echo   3. Tap "Wireless Debugging" -^> Enable it and note the IP:Port (e.g. 10.0.0.95:38123)
echo.
set /p PAIR_NEEDED="Do you need to enter a 6-digit Wireless Pairing Code first? [y/N]: "
if /I "%PAIR_NEEDED%"=="Y" (
    set /p PAIR_ADDR="Enter Pairing IP:Port shown under 'Pair new device': "
    set /p PAIR_CODE="Enter 6-digit Pairing Code: "
    %ADB_EXE% pair %PAIR_ADDR% %PAIR_CODE%
)
echo.
set /p TARGET_ADDR="Enter Watch 8 or Pixel 7 Pro IP:Port [e.g. 10.0.0.95:5555]: "
if "%TARGET_ADDR%"=="" set TARGET_ADDR=10.0.0.84:5555

echo.
echo [*] Connecting to %TARGET_ADDR% via Wireless ADB...
%ADB_EXE% connect %TARGET_ADDR%

echo.
set /p DEV_MODE="Install on Samsung Galaxy Watch 8 (W) or Google Pixel 7 Pro (P)? [W/P, default: W]: "
if /I "%DEV_MODE%"=="P" (
    echo [*] Installing Native Google Pixel 7 Pro APK (com.hermes.sovereign.phone)...
    %ADB_EXE% -s %TARGET_ADDR% install -r "%USERPROFILE%\\.hermes\\apks\\hermes-pixel7pro.apk"
    echo [*] Granting Sensor ^& Notification Permissions...
    %ADB_EXE% -s %TARGET_ADDR% shell pm grant com.hermes.sovereign.phone android.permission.BODY_SENSORS 2>nul
    %ADB_EXE% -s %TARGET_ADDR% shell pm grant com.hermes.sovereign.phone android.permission.ACTIVITY_RECOGNITION 2>nul
    %ADB_EXE% -s %TARGET_ADDR% shell pm grant com.hermes.sovereign.phone android.permission.POST_NOTIFICATIONS 2>nul
    echo [*] Launching Hermes AI Native App on Pixel 7 Pro...
    %ADB_EXE% -s %TARGET_ADDR% shell am start -n com.hermes.sovereign.phone/.MainActivity
) else (
    echo [*] Installing Native Samsung Galaxy Watch 8 APK (com.hermes.sovereign.watch)...
    %ADB_EXE% -s %TARGET_ADDR% install -r "%USERPROFILE%\\.hermes\\apks\\hermes-galaxy-watch8.apk"
    echo [*] Granting Watch 8 BioActive Sensor ^& Notification Permissions...
    %ADB_EXE% -s %TARGET_ADDR% shell pm grant com.hermes.sovereign.watch android.permission.BODY_SENSORS 2>nul
    %ADB_EXE% -s %TARGET_ADDR% shell pm grant com.hermes.sovereign.watch android.permission.ACTIVITY_RECOGNITION 2>nul
    %ADB_EXE% -s %TARGET_ADDR% shell pm grant com.hermes.sovereign.watch android.permission.POST_NOTIFICATIONS 2>nul
    echo [*] Launching Hermes Watch 8 Native App on Wrist...
    %ADB_EXE% -s %TARGET_ADDR% shell am start -n com.hermes.sovereign.watch/.MainActivity
)

echo.
echo [+] Native APK Installed ^& Launched! Look for "Hermes AI" / "Hermes Watch" in your app drawer.
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
        phone_apk_url = f"http://{hub.lan_ip}:{hub.port}/download/hermes-pixel7pro.apk"
        watch_apk_url = f"http://{hub.lan_ip}:{hub.port}/download/hermes-galaxy-watch8.apk"
        phone_qr = generate_qr_code_png_base64(phone_apk_url)
        watch_qr = generate_qr_code_png_base64(watch_apk_url)
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
