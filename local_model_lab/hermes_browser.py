# -*- coding: utf-8 -*-
"""
Hermes Dedicated Browser Engine (Pinned to 'Chintu' Profile)
============================================================
Guarantees that Hermes NEVER uses or touches the user's personal Chrome profile
('Default' / 'Sasidhar') and NEVER triggers the 'Who's using Chrome?' picker.

Two Modes:
1. Visible Interactive Mode (`open_in_chintu_browser`):
   Explicitly passes `--profile-directory="Profile 1"` (Chintu AI) to `chrome.exe`.
2. Background Headless Scraper Mode (`fetch_dom_with_chintu_browser`):
   Uses an isolated Chintu-seeded `--user-data-dir` (`~/.hermes/chintu_browser_data`)
   with `--headless=new --dump-dom` and `CREATE_NO_WINDOW` so background deal
   checks and web scraping run invisibly without stealing focus or opening popups.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Profile 1 = "Chintu" (chintu.ai2026@gmail.com)
# Default   = "Sasidhar" (Personal profile — STRICTLY BLOCKED)
CHINTU_PROFILE_DIR = os.environ.get("HERMES_CHROME_PROFILE", "Profile 1")
BLOCKED_PERSONAL_PROFILES = {"default", "sasidhar"}

HERMES_BROWSER_DATA_DIR = Path.home() / ".hermes" / "chintu_browser_data"

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)


def find_chrome_executable() -> Optional[str]:
    """Locates the installed Google Chrome binary on Windows."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    found = shutil.which("chrome") or shutil.which("chrome.exe")
    return found


def resolve_chintu_profile_info() -> Dict[str, Any]:
    """Reads Chrome Local State to confirm the Chintu profile directory and metadata."""
    local_state_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data" / "Local State"
    result = {
        "profile_directory": CHINTU_PROFILE_DIR,
        "profile_name": "Chintu",
        "email": "chintu.ai2026@gmail.com",
        "personal_profile_blocked": True,
        "chrome_executable": find_chrome_executable(),
        "headless_data_dir": str(HERMES_BROWSER_DATA_DIR),
    }
    if local_state_path.exists():
        try:
            data = json.loads(local_state_path.read_text(encoding="utf-8"))
            info_cache = data.get("profile", {}).get("info_cache", {})
            # Dynamically find profile named "Chintu" if present
            for prof_dir, meta in info_cache.items():
                name = str(meta.get("name", "")).strip()
                shortcut = str(meta.get("shortcut_name", "")).strip()
                if "chintu" in name.lower() or "chintu" in shortcut.lower():
                    result["profile_directory"] = prof_dir
                    result["profile_name"] = name or "Chintu"
                    result["email"] = meta.get("user_name", result["email"])
                    break
        except Exception as exc:
            logger.debug(f"Could not read Chrome Local State: {exc}")
    return result


def _ensure_chintu_headless_dir() -> Path:
    """Seeds the isolated headless user-data-dir from Chintu's Profile 1 preferences once."""
    HERMES_BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    default_sub = HERMES_BROWSER_DATA_DIR / "Default"
    default_sub.mkdir(parents=True, exist_ok=True)

    prefs_target = default_sub / "Preferences"
    if not prefs_target.exists():
        info = resolve_chintu_profile_info()
        prof_dir = info["profile_directory"]
        chrome_user_data = Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"
        src_prefs = chrome_user_data / prof_dir / "Preferences"
        if src_prefs.exists():
            try:
                shutil.copy2(src_prefs, prefs_target)
            except Exception:
                pass
    return HERMES_BROWSER_DATA_DIR


def get_chintu_chrome_command(url: Optional[str] = None, new_window: bool = False) -> List[str]:
    """Builds the exact command list to launch Chrome inside the Chintu profile without profile picker."""
    chrome_exe = find_chrome_executable() or "chrome.exe"
    info = resolve_chintu_profile_info()
    prof_dir = info["profile_directory"]
    if prof_dir.strip().lower() in BLOCKED_PERSONAL_PROFILES:
        prof_dir = "Profile 1"

    cmd = [
        chrome_exe,
        f"--profile-directory={prof_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if new_window:
        cmd.append("--new-window")
    if url:
        cmd.append(url)
    return cmd


def open_in_chintu_browser(url: str = "https://www.google.com", new_window: bool = False) -> Dict[str, Any]:
    """
    Opens a URL visibly inside the dedicated 'Chintu' Chrome profile (Profile 1).
    Never opens the 'Who's using Chrome?' profile selector or the personal 'Sasidhar' profile.
    """
    clean_url = str(url or "https://www.google.com").strip()
    if not clean_url.startswith(("http://", "https://", "chrome://")):
        clean_url = "https://" + clean_url

    cmd = get_chintu_chrome_command(url=clean_url, new_window=new_window)
    info = resolve_chintu_profile_info()
    try:
        proc = subprocess.Popen(cmd, shell=False)
        return {
            "status": "success",
            "pid": proc.pid,
            "url": clean_url,
            "profile_directory": info["profile_directory"],
            "profile_name": info["profile_name"],
            "message": f"Opened in {info['profile_name']} Chrome profile ({info['profile_directory']})",
        }
    except Exception as exc:
        return {
            "status": "error",
            "url": clean_url,
            "message": f"Failed to launch Chintu Chrome: {exc}",
        }


def fetch_dom_with_chintu_browser(url: str, timeout_s: int = 12) -> str:
    """
    Renders a JavaScript webpage invisibly in the background using Chrome's
    `--headless=new --dump-dom` engine with the isolated Chintu browser data dir.
    Zero popup windows, zero focus stealing, and zero interference with personal Chrome.
    """
    chrome_exe = find_chrome_executable()
    if not chrome_exe:
        return ""

    data_dir = _ensure_chintu_headless_dir()
    cmd = [
        chrome_exe,
        "--headless=new",
        f"--user-data-dir={data_dir}",
        f"--user-agent={DEFAULT_UA}",
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-gpu",
        "--window-size=1440,900",
        "--dump-dom",
        url,
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            creationflags=creationflags,
        )
        if proc.stdout and len(proc.stdout) > 500:
            return proc.stdout
    except Exception as exc:
        logger.debug(f"Headless Chintu DOM fetch failed for {url}: {exc}")
    return ""
