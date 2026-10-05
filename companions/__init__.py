# -*- coding: utf-8 -*-
"""
Hermes Omni-Mesh Companions Package
Dedicated modular architecture for Smartwatch, Smartphone, and Laptop.
"""

from __future__ import annotations

import json
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

    # ── SMARTWATCH ROUTES ───────────────────────────────────────────────────
    @app.get("/companions/smartwatch", response_class=HTMLResponse)
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

    # ── SMARTPHONE ROUTES ───────────────────────────────────────────────────
    @app.get("/companions/smartphone", response_class=HTMLResponse)
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

    # ── LAPTOP ROUTES ───────────────────────────────────────────────────────
    @app.get("/companions/laptop", response_class=HTMLResponse)
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
