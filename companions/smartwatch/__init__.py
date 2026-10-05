# -*- coding: utf-8 -*-
"""
Smartwatch Companion Package for Hermes Agent
"""

from pathlib import Path
from typing import Dict, Any
import json

from .bridge import SmartwatchBridge, get_smartwatch_bridge

_DIR = Path(__file__).resolve().parent


def get_smartwatch_manifest() -> Dict[str, Any]:
    """Loads WearOS / Apple Watch PWA manifest."""
    manifest_file = _DIR / "manifest.json"
    if manifest_file.exists():
        return json.loads(manifest_file.read_text(encoding="utf-8"))
    return {}


def render_smartwatch_html(host_ip: str, host_port: int) -> str:
    """Returns the standalone circular smartwatch HUD HTML."""
    html_file = _DIR / "web" / "index.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "<html><body>Hermes Smartwatch HUD</body></html>"
