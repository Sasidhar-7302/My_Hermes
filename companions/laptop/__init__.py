# -*- coding: utf-8 -*-
"""
Laptop Companion Package for Hermes Agent
"""

from pathlib import Path
from typing import Dict, Any
import json

from .bridge import LaptopBridge, get_laptop_bridge

_DIR = Path(__file__).resolve().parent


def get_laptop_manifest() -> Dict[str, Any]:
    """Loads Laptop Workstation PWA manifest."""
    manifest_file = _DIR / "manifest.json"
    if manifest_file.exists():
        return json.loads(manifest_file.read_text(encoding="utf-8"))
    return {}


def render_laptop_html(host_ip: str, host_port: int) -> str:
    """Returns the standalone laptop workstation HTML."""
    html_file = _DIR / "web" / "index.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "<html><body>Hermes Laptop Workstation</body></html>"
