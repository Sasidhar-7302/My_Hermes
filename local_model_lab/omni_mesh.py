# -*- coding: utf-8 -*-
"""
Hermes Omni-Mesh: Unified Cross-Device Companion Hub
(Re-exports from companions.hub for seamless backwards compatibility)
"""

import sys
from pathlib import Path

_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from companions.hub import (
    MeshDevice,
    OmniMeshHub,
    get_omni_mesh_hub,
    get_local_lan_ip,
    read_pc_clipboard,
    write_pc_clipboard,
    generate_qr_code_png_base64,
)

__all__ = [
    "MeshDevice",
    "OmniMeshHub",
    "get_omni_mesh_hub",
    "get_local_lan_ip",
    "read_pc_clipboard",
    "write_pc_clipboard",
    "generate_qr_code_png_base64",
]
