# -*- coding: utf-8 -*-
"""
Smartphone Companion Package for Hermes Agent
"""

from pathlib import Path
from typing import Dict, Any
import json

from .bridge import SmartphoneBridge, get_smartphone_bridge

_DIR = Path(__file__).resolve().parent


def get_smartphone_manifest() -> Dict[str, Any]:
    """Loads Android / iOS PWA manifest."""
    manifest_file = _DIR / "manifest.json"
    if manifest_file.exists():
        return json.loads(manifest_file.read_text(encoding="utf-8"))
    return {}


def get_smartphone_sw() -> str:
    """Returns Service Worker script content."""
    sw_file = _DIR / "sw.js"
    if sw_file.exists():
        return sw_file.read_text(encoding="utf-8")
    return "// Service worker"


def render_smartphone_html(host_ip: str, host_port: int) -> str:
    """Returns the standalone smartphone companion app HTML."""
    html_file = _DIR / "web" / "index.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "<html><body>Hermes Smartphone Companion</body></html>"
