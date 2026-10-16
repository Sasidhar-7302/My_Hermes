"""Hermes health & API key watchdog.

Checks local services (Ollama, gateway, OmniMesh dashboard), host resources
(free disk, available commit memory), and which API keys are configured in the
local ``.env``. Key *presence* is checked, not key validity — use
``hermes doctor`` for live provider probes.

Modes:
  * Interactive (TTY): prints a full summary. ``--notify-telegram`` also sends
    the report via ``hermes send``.
  * Cron (non-TTY or ``--cron``): prints the report to stdout only when the
    health state *changed* since the last run (new problem, or recovery).
    Hermes cron delivers non-empty stdout to Telegram, so an unchanged state
    stays silent instead of re-sending the same alert every run.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx

# app/scripts/hermes_watchdog.py -> parents[2] is the Hermes home directory.
HERMES_HOME = Path(os.environ.get("HERMES_HOME") or Path(__file__).resolve().parents[2])
APP_DIR = HERMES_HOME / "app"
ENV_PATH = HERMES_HOME / ".env"
STATE_PATH = HERMES_HOME / "logs" / "watchdog_state.json"

MIN_FREE_DISK_GB = 5.0
MIN_FREE_COMMIT_GB = 4.0

KEY_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "OPENROUTER_API_KEY": {"name": "OpenRouter", "purpose": "Cloud fallback models"},
    "OLLAMA_API_KEY": {"name": "Ollama Cloud", "purpose": "Ollama cloud models"},
    "NVIDIA_API_KEY": {"name": "NVIDIA NIM", "purpose": "NIM model inference"},
    "GROQ_API_KEY": {"name": "Groq", "purpose": "Fast inference", "revoked": True},
    "GOOGLE_API_KEY": {"name": "Google Gemini", "purpose": "Gemini models", "revoked": True},
    "XAI_API_KEY": {"name": "xAI Grok", "purpose": "x_search tool"},
    "EXA_API_KEY": {"name": "Exa", "purpose": "Neural web search"},
    "TAVILY_API_KEY": {"name": "Tavily", "purpose": "Web search"},
    "FIRECRAWL_API_KEY": {"name": "Firecrawl", "purpose": "Web extraction"},
    "FAL_KEY": {"name": "Fal.ai", "purpose": "Image/video generation"},
    "TELEGRAM_BOT_TOKEN": {"name": "Telegram", "purpose": "Primary gateway", "required": True},
    "DISCORD_BOT_TOKEN": {"name": "Discord", "purpose": "Discord adapter"},
    "SLACK_BOT_TOKEN": {"name": "Slack", "purpose": "Slack adapter"},
    "TERRA_API_KEY": {"name": "Terra", "purpose": "Wearable biometrics"},
    "SPOTIFY_CLIENT_ID": {"name": "Spotify", "purpose": "Playback control"},
}


# ── Collection ────────────────────────────────────────────────────────────


def read_env_key_status() -> Dict[str, str]:
    """Return ``{VAR: configured|commented|empty}`` without exposing values."""
    statuses: Dict[str, str] = {}
    if not ENV_PATH.exists():
        return statuses

    for raw_line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        is_commented = line.startswith("#")
        body = line.lstrip("#").strip()
        if "=" not in body:
            continue
        key, value = body.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if is_commented:
            status = "commented"
        elif value:
            status = "configured"
        else:
            status = "empty"
        # A configured line wins over commented/empty duplicates.
        if statuses.get(key) != "configured":
            statuses[key] = status
    return statuses


def audit_api_keys() -> Dict[str, List[Dict[str, str]]]:
    statuses = read_env_key_status()
    audit: Dict[str, List[Dict[str, str]]] = {"configured": [], "revoked": [], "missing": []}
    for var, meta in KEY_DEFINITIONS.items():
        entry = {"var": var, "name": meta["name"], "purpose": meta["purpose"]}
        if statuses.get(var) == "configured":
            audit["configured"].append(entry)
        elif meta.get("revoked"):
            audit["revoked"].append(entry)
        else:
            entry["required"] = "yes" if meta.get("required") else "no"
            audit["missing"].append(entry)
    return audit


def _check_http(label: str, url: str) -> Dict[str, Any]:
    try:
        response = httpx.get(url, timeout=3.0)
        return {"ok": response.status_code == 200, "label": label, "detail": f"HTTP {response.status_code}"}
    except httpx.HTTPError as exc:
        return {"ok": False, "label": label, "detail": f"offline ({exc.__class__.__name__})"}


def _check_gateway_process() -> Dict[str, Any]:
    label = "Telegram gateway"
    try:
        import psutil
    except ImportError:
        return {"ok": True, "label": label, "detail": "psutil unavailable, not checked"}

    gateway_procs = {}
    for proc in psutil.process_iter(["pid", "ppid", "cmdline"]):
        cmdline = " ".join(proc.info.get("cmdline") or []).lower()
        if "hermes" in cmdline and "gateway run" in cmdline and "powershell" not in cmdline:
            gateway_procs[proc.info["pid"]] = proc.info["ppid"]
    # On Windows a venv launcher spawns child interpreters with the same
    # command line; only processes whose parent is not a gateway are real roots.
    roots = sorted(pid for pid, ppid in gateway_procs.items() if ppid not in gateway_procs)
    if not roots:
        return {"ok": False, "label": label, "detail": "not running"}
    if len(roots) > 1:
        # Two pollers on one bot token make Telegram drop both connections.
        return {"ok": False, "label": label, "detail": f"DUPLICATE instances (PIDs {', '.join(map(str, roots))})"}
    return {"ok": True, "label": label, "detail": f"running (PID {roots[0]})"}


def _ensure_dashboard_running() -> Dict[str, Any]:
    probe = _check_http("OmniMesh dashboard", "http://127.0.0.1:8000/")
    if probe["ok"]:
        return probe
    python_bin = APP_DIR / "venv" / "Scripts" / ("pythonw.exe" if sys.platform == "win32" else "python")
    if not python_bin.exists():
        python_bin = APP_DIR / "venv" / "Scripts" / "python.exe"
    script_path = APP_DIR / "local_model_lab" / "company_dashboard.py"
    if python_bin.exists() and script_path.exists():
        try:
            flags = 0
            if sys.platform == "win32":
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
            subprocess.Popen(
                [str(python_bin), "-X", "utf8", str(script_path)],
                cwd=str(APP_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
            import time
            for _ in range(8):
                time.sleep(1.0)
                reprobe = _check_http("OmniMesh dashboard", "http://127.0.0.1:8000/")
                if reprobe["ok"]:
                    reprobe["detail"] = f"{reprobe['detail']} (auto-restarted)"
                    return reprobe
        except Exception as exc:
            return {"ok": False, "label": "OmniMesh dashboard", "detail": f"offline; restart failed ({exc})"}
    return probe


def check_services() -> Dict[str, Dict[str, Any]]:
    return {
        "ollama": _check_http("Local Ollama", "http://127.0.0.1:11434/api/tags"),
        "dashboard": _ensure_dashboard_running(),
        "gateway": _check_gateway_process(),
    }


def _free_ram_gb() -> float | None:
    """Available physical RAM in GB; ``None`` if unknown."""
    if sys.platform != "win32":
        try:
            import psutil
            return psutil.virtual_memory().available / 1e9
        except ImportError:
            return None

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(MemoryStatusEx)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return status.ullAvailPhys / 1e9


def check_resources() -> Dict[str, Dict[str, Any]]:
    free_disk_gb = shutil.disk_usage(HERMES_HOME).free / 1e9
    resources = {
        "disk": {
            "ok": free_disk_gb >= MIN_FREE_DISK_GB,
            "label": "Free disk",
            "detail": f"{free_disk_gb:.1f} GB (minimum {MIN_FREE_DISK_GB:.0f} GB)",
        }
    }
    free_ram = _free_ram_gb()
    if free_ram is not None:
        resources["memory"] = {
            "ok": free_ram >= MIN_FREE_COMMIT_GB,
            "label": "Available physical RAM",
            "detail": f"{free_ram:.1f} GB (minimum {MIN_FREE_COMMIT_GB:.0f} GB)",
        }
    return resources


# ── State tracking ────────────────────────────────────────────────────────


def health_fingerprint(checks: Dict[str, Dict[str, Any]], audit: Dict[str, List[Dict[str, str]]]) -> str:
    """Hash of the coarse health state (which checks fail, which keys are absent)."""
    state = {
        "failing": sorted(name for name, check in checks.items() if not check["ok"]),
        "revoked": sorted(k["var"] for k in audit["revoked"]),
        "missing_required": sorted(k["var"] for k in audit["missing"] if k["required"] == "yes"),
    }
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


def load_last_fingerprint() -> str | None:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8")).get("fingerprint")
    except (OSError, ValueError):
        return None


def save_fingerprint(fingerprint: str) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({"fingerprint": fingerprint}), encoding="utf-8")


# ── Reporting ─────────────────────────────────────────────────────────────


def build_report(checks: Dict[str, Dict[str, Any]], audit: Dict[str, List[Dict[str, str]]]) -> str:
    lines = ["🛡️ Hermes health report", ""]

    lines.append("System:")
    for check in checks.values():
        icon = "✅" if check["ok"] else "❌"
        lines.append(f"{icon} {check['label']}: {check['detail']}")

    if audit["revoked"]:
        lines += ["", "Revoked keys (disabled in .env, need replacement):"]
        lines += [f"🔴 {k['var']} ({k['name']}): {k['purpose']}" for k in audit["revoked"]]

    if audit["missing"]:
        lines += ["", "Not configured (optional unless marked):"]
        for k in audit["missing"]:
            marker = " REQUIRED" if k["required"] == "yes" else ""
            lines.append(f"⚪ {k['var']} ({k['name']}): {k['purpose']}{marker}")

    if audit["configured"]:
        lines += ["", "Configured: " + ", ".join(k["name"] for k in audit["configured"])]

    lines += [
        "",
        "To add a key: edit Hermes agent\\.env (never commit it), then restart the gateway.",
        "Presence only is checked here; run `hermes doctor` to validate keys.",
    ]
    return "\n".join(lines)


def send_to_telegram(message: str) -> bool:
    hermes_bin = APP_DIR / "venv" / "Scripts" / "hermes.exe"
    command = [str(hermes_bin) if hermes_bin.exists() else "hermes", "send", "--to", "telegram", message]
    try:
        result = subprocess.run(command, cwd=str(APP_DIR), capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[watchdog] send failed: {exc}", file=sys.stderr)
        return False
    if result.returncode != 0:
        print(f"[watchdog] hermes send exited {result.returncode}: {result.stderr.strip()}", file=sys.stderr)
        return False
    print(f"[watchdog] {result.stdout.strip()}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes health & API key watchdog")
    parser.add_argument("--notify-telegram", action="store_true", help="Send the report to Telegram now")
    parser.add_argument("--cron", action="store_true", help="Cron mode: print only when health state changes")
    args = parser.parse_args()

    # Windows pipes default to cp1252, which cannot encode the report's emoji.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    checks = {**check_services(), **check_resources()}
    audit = audit_api_keys()
    report = build_report(checks, audit)

    if args.cron:
        fingerprint = health_fingerprint(checks, audit)
        if fingerprint != load_last_fingerprint():
            print(report)
            save_fingerprint(fingerprint)
        return

    print(report)
    if args.notify_telegram:
        send_to_telegram(report)


if __name__ == "__main__":
    main()
