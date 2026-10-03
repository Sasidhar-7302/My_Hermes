# -*- coding: utf-8 -*-
"""
Paper Desktop MCP Client & Design Gateway for Hermes Agent
Enables autonomous UI/UX design, artboard creation, HTML rendering, and design inspection
via Paper Desktop's local MCP server (http://127.0.0.1:29979/mcp).
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Ensure UTF-8 stdout safety on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def is_port_open(host: str = "127.0.0.1", port: int = 29979, timeout: float = 0.5) -> bool:
    """Checks whether the Paper MCP port is open and listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            return sock.connect_ex((host, port)) == 0
        except Exception:
            return False


def detect_paper_executable() -> Optional[Path]:
    """Detects the installed Paper Desktop executable on Windows."""
    candidates: List[Path] = []
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", "")
    user_profile = os.environ.get("USERPROFILE", "")

    if local_app_data:
        candidates.append(Path(local_app_data) / "Programs" / "Paper" / "Paper.exe")
    if program_files:
        candidates.append(Path(program_files) / "Paper" / "Paper.exe")
    if user_profile:
        candidates.append(Path(user_profile) / "AppData" / "Local" / "Programs" / "Paper" / "Paper.exe")

    for cand in candidates:
        if cand.exists() and cand.is_file():
            return cand.resolve()
    return None


@dataclass
class PaperStatus:
    """Status of the Paper Desktop application and MCP server."""
    listening: bool
    url: str
    session_id: str = ""
    file_open: bool = False
    file_name: str = ""
    artboards: int = 0
    selected_nodes: int = 0
    message: str = ""
    raw_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "listening": self.listening,
            "url": self.url,
            "session_id": self.session_id,
            "file_open": self.file_open,
            "file_name": self.file_name,
            "artboards": self.artboards,
            "selected_nodes": self.selected_nodes,
            "message": self.message,
            "raw_info": self.raw_info,
        }


class PaperMcpClient:
    """
    Client for interacting with Paper Desktop's HTTP MCP Server.
    Protocol: JSON-RPC 2.0 over HTTP with SSE streaming support.
    Default endpoint: http://127.0.0.1:29979/mcp
    """

    DEFAULT_URL = "http://127.0.0.1:29979/mcp"
    PROTOCOL_VERSION = "2024-11-05"

    def __init__(self, url: str = DEFAULT_URL, auto_launch: bool = True):
        self.url = url
        self.auto_launch = auto_launch
        self.session_id: str = ""
        self._initialized: bool = False

    def ensure_paper_running(self, timeout_seconds: float = 10.0) -> bool:
        """Verifies Paper is running and listening; launches it if not."""
        if is_port_open():
            return True

        if not self.auto_launch:
            return False

        exe = detect_paper_executable()
        if not exe:
            logger.warning("Paper.exe not found on disk. Cannot auto-launch.")
            return False

        logger.info(f"Launching Paper Desktop from {exe}...")
        try:
            subprocess.Popen([str(exe)], creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        except Exception as exc:
            logger.error(f"Failed to launch Paper Desktop: {exc}")
            return False

        # Wait for port to open
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if is_port_open():
                time.sleep(1.0)  # Allow HTTP server to fully initialize
                return True
            time.sleep(0.5)

        return False

    def _post(self, payload: Dict[str, Any], timeout: float = 15.0) -> Tuple[Dict[str, Any], Optional[str]]:
        """Sends an HTTP JSON-RPC request to Paper MCP."""
        import requests

        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id

        resp = requests.post(self.url, headers=headers, json=payload, timeout=timeout)
        new_sess = resp.headers.get("mcp-session-id")

        # Parse SSE or plain JSON response
        text = resp.text or ""
        parsed = {}
        if "text/event-stream" in resp.headers.get("Content-Type", "") or text.lstrip().startswith("event:"):
            data_lines = [l[6:] for l in text.splitlines() if l.startswith("data: ")]
            if data_lines:
                parsed = json.loads("\n".join(data_lines))
        elif text.strip():
            parsed = json.loads(text)

        return parsed, new_sess

    def initialize(self) -> bool:
        """Performs MCP initialize handshake and notifications/initialized notification."""
        if not self.ensure_paper_running():
            return False

        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": self.PROTOCOL_VERSION,
                "clientInfo": {"name": "hermes-agent-paper-client", "version": "1.0"},
                "capabilities": {"tools": {}},
            },
        }

        try:
            resp, sess_id = self._post(init_payload)
            if sess_id:
                self.session_id = sess_id

            # Send required initialized notification
            notify_payload = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
            self._post(notify_payload, timeout=5.0)
            self._initialized = True
            return True
        except Exception as exc:
            logger.warning(f"Paper MCP initialize handshake failed: {exc}")
            self._initialized = False
            return False

    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calls a specific tool on the Paper MCP server."""
        if not self._initialized or not self.session_id:
            if not self.initialize():
                return {
                    "status": "error",
                    "message": "Paper Desktop is not reachable or MCP handshake failed.",
                }

        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000) % 100000,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
        }

        try:
            resp, _ = self._post(payload, timeout=30.0)
            result = resp.get("result", {})
            if result.get("isError"):
                content = result.get("content", [])
                err_text = content[0].get("text", "") if content else "Tool error"
                return {"status": "error", "message": err_text, "tool": tool_name}

            content = result.get("content", [])
            data: Any = None
            if content and isinstance(content, list):
                first = content[0]
                if isinstance(first, dict) and first.get("type") == "text":
                    try:
                        data = json.loads(first.get("text", ""))
                    except Exception:
                        data = first.get("text")
                else:
                    data = content
            else:
                data = result

            return {"status": "success", "tool": tool_name, "data": data}
        except Exception as exc:
            logger.error(f"Paper tool '{tool_name}' failed: {exc}")
            return {"status": "error", "message": str(exc), "tool": tool_name}

    def status(self) -> PaperStatus:
        """Returns the high-level connection and file status of Paper Desktop."""
        if not is_port_open():
            return PaperStatus(
                listening=False,
                url=self.url,
                message="Paper Desktop MCP port 29979 is closed. Paper is not running.",
            )

        if not self._initialized:
            self.initialize()

        res = self.call_tool("get_basic_info")
        if res.get("status") == "error":
            msg = res.get("message", "")
            return PaperStatus(
                listening=True,
                url=self.url,
                session_id=self.session_id,
                file_open=False,
                message=f"Paper is running, but no file is open: {msg}",
            )

        data = res.get("data") or {}
        fname = str(data.get("fileName") or "Untitled")
        artboards = int(data.get("artboardCount") or len(data.get("artboards") or []))

        sel_res = self.call_tool("get_selection")
        sel_count = 0
        if sel_res.get("status") == "success":
            sel_data = sel_res.get("data") or {}
            sel_count = int(sel_data.get("count") or len(sel_data.get("selectedNodes") or []))

        return PaperStatus(
            listening=True,
            url=self.url,
            session_id=self.session_id,
            file_open=True,
            file_name=fname,
            artboards=artboards,
            selected_nodes=sel_count,
            message=f"Paper connected. File: '{fname}', {artboards} artboards, {sel_count} nodes selected.",
            raw_info=data,
        )

    # ── High-Level Paper Design Operations ───────────────────────────────────

    def get_basic_info(self) -> Dict[str, Any]:
        """Gets current file name, artboard list, and canvas metadata."""
        return self.call_tool("get_basic_info")

    def get_selection(self) -> Dict[str, Any]:
        """Gets currently selected nodes on the Paper canvas."""
        return self.call_tool("get_selection")

    def get_tree_summary(self) -> Dict[str, Any]:
        """Gets high-level hierarchy summary of all artboards and major groups."""
        return self.call_tool("get_tree_summary")

    def get_font_family_info(self) -> Dict[str, Any]:
        """Lists available typography and fonts supported in Paper Desktop."""
        return self.call_tool("get_font_family_info")

    def create_artboard(
        self,
        name: str = "Artboard",
        width: int = 1440,
        height: int = 900,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new artboard frame on the Paper canvas.
        Default: Desktop web resolution (1440x900).
        """
        styles: Dict[str, Any] = {
            "width": f"{width}px",
            "height": f"{height}px",
        }
        if x is not None and y is not None:
            styles["left"] = f"{x}px"
            styles["top"] = f"{y}px"

        args: Dict[str, Any] = {
            "name": name,
            "styles": styles,
        }
        return self.call_tool("create_artboard", args)

    def write_html(
        self,
        html: str,
        target_node_id: Optional[str] = None,
        mode: str = "append",
    ) -> Dict[str, Any]:
        """
        Writes HTML into a Paper artboard or node.
        mode: 'append', 'prepend', or 'replace'.
        """
        args: Dict[str, Any] = {"html": html, "mode": mode}
        if target_node_id:
            args["targetNodeId"] = target_node_id
        return self.call_tool("write_html", args)

    def set_text_content(self, node_id: str, new_text: str) -> Dict[str, Any]:
        """Updates text inside a specific Text node."""
        args = {"updates": [{"nodeId": node_id, "text": new_text}]}
        return self.call_tool("set_text_content", args)

    def update_styles(self, node_id: str, styles: Dict[str, Any]) -> Dict[str, Any]:
        """Updates CSS-style visual properties on a specific node."""
        args = {"nodeId": node_id, "styles": styles}
        return self.call_tool("update_styles", args)

    def finish_working(self) -> Dict[str, Any]:
        """Completes active node editing session and frees canvas locks."""
        return self.call_tool("finish_working_on_nodes")


# Global singleton instance
_paper_client_instance: Optional[PaperMcpClient] = None


def get_paper_client() -> PaperMcpClient:
    """Returns the singleton Paper MCP client."""
    global _paper_client_instance
    if _paper_client_instance is None:
        _paper_client_instance = PaperMcpClient()
    return _paper_client_instance
