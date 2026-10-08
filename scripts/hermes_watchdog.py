"""Hermes Autonomous Health & API Key Watchdog.

Audits Hermes runtime health, checks active and missing API keys, verifies
service connectivity (Ollama, Gateway, OmniMesh Hub, Provider APIs), and sends
structured alert notifications directly to Telegram.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

APP_DIR = Path(__file__).resolve().parent.parent
HERMES_HOME = APP_DIR.parent
ENV_PATH = HERMES_HOME / ".env"
CONFIG_PATH = HERMES_HOME / "config.yaml"


def load_env_variables() -> Dict[str, Dict[str, Any]]:
    """Parse .env file to discover active, commented-out, and empty keys."""
    results: Dict[str, Dict[str, Any]] = {}
    if not ENV_PATH.exists():
        return results

    try:
        content = ENV_PATH.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        print(f"Error reading .env: {exc}", file=sys.stderr)
        return results

    for line in content.splitlines():
        line_strip = line.strip()
        if not line_strip:
            continue

        is_commented = line_strip.startswith("#")
        cleaned_line = line_strip.lstrip("#").strip()
        if "=" not in cleaned_line:
            continue

        key, val = cleaned_line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'\"")

        # Determine status
        if is_commented:
            status = "disabled_or_revoked"
        elif not val:
            status = "empty"
        else:
            status = "configured"

        # Keep the most relevant status if key repeats
        if key not in results or (results[key]["status"] != "configured" and status == "configured"):
            results[key] = {
                "status": status,
                "has_value": bool(val),
                "length": len(val) if val else 0,
            }

    return results


def check_api_keys() -> Dict[str, Any]:
    """Audit core, fallback, search, and platform API keys."""
    env_vars = load_env_variables()

    # Track specific API key categories
    key_definitions = {
        # Core & LLM Providers
        "OPENROUTER_API_KEY": {
            "name": "OpenRouter API",
            "tier": "Core / Fallback",
            "description": "Multi-model cloud fallback (DeepSeek, GLM, Kimi, Nemotron)",
            "required": False,
        },
        "OLLAMA_API_KEY": {
            "name": "Ollama Cloud API",
            "tier": "Core / Cloud",
            "description": "Ollama cloud models and remote endpoints",
            "required": False,
        },
        "NVIDIA_API_KEY": {
            "name": "NVIDIA NIM",
            "tier": "Fallback",
            "description": "NVIDIA high-performance NIM model inference",
            "required": False,
        },
        "GROQ_API_KEY": {
            "name": "Groq Cloud API",
            "tier": "High-Speed Inference",
            "description": "Fast Llama/Qwen inference (currently compromised/revoked)",
            "required": False,
            "was_compromised": True,
        },
        "GOOGLE_API_KEY": {
            "name": "Google / Gemini API",
            "tier": "Vision / Extraction",
            "description": "Gemini 2.5 Flash multimodal & extraction (compromised/revoked)",
            "required": False,
            "was_compromised": True,
        },
        "XAI_API_KEY": {
            "name": "xAI API (Grok)",
            "tier": "Intelligence / Search",
            "description": "Enables x_search real-time X/Twitter intelligence tool",
            "required": False,
        },
        # Search & Web Intelligence
        "EXA_API_KEY": {
            "name": "Exa Neural Search",
            "tier": "Search Engine",
            "description": "Deep neural semantic web search for research & briefing",
            "required": False,
        },
        "TAVILY_API_KEY": {
            "name": "Tavily Search API",
            "tier": "Search Engine",
            "description": "Real-time AI search agent engine",
            "required": False,
        },
        "FIRECRAWL_API_KEY": {
            "name": "Firecrawl Scraper API",
            "tier": "Web Extraction",
            "description": "Clean markdown web extraction & deep crawling",
            "required": False,
        },
        # Creative & Generative
        "FAL_KEY": {
            "name": "Fal.ai Compute",
            "tier": "Image / Media Gen",
            "description": "FLUX and high-speed image/video generation",
            "required": False,
        },
        # Integrations & Chat Platforms
        "TELEGRAM_BOT_TOKEN": {
            "name": "Telegram Bot Token",
            "tier": "Primary Gateway",
            "description": "Telegram 2-way companion & notifications",
            "required": True,
        },
        "DISCORD_BOT_TOKEN": {
            "name": "Discord Bot Token",
            "tier": "Platform Adapter",
            "description": "Discord bot channel & server integration",
            "required": False,
        },
        "SLACK_BOT_TOKEN": {
            "name": "Slack Bot Token",
            "tier": "Platform Adapter",
            "description": "Slack workspace bot and incident responses",
            "required": False,
        },
        "TERRA_API_KEY": {
            "name": "Terra API (Wearables)",
            "tier": "Companion Health",
            "description": "Smartwatch biometrics (Garmin, Apple Watch, Galaxy)",
            "required": False,
        },
        "SPOTIFY_CLIENT_ID": {
            "name": "Spotify API",
            "tier": "Media Playback",
            "description": "Spotify playback control tool",
            "required": False,
        },
    }

    configured_keys = []
    missing_keys = []
    compromised_keys = []

    for env_name, meta in key_definitions.items():
        state = env_vars.get(env_name, {})
        status = state.get("status", "not_in_env")

        entry = {
            "var": env_name,
            "name": meta["name"],
            "tier": meta["tier"],
            "description": meta["description"],
            "status": status,
        }

        if meta.get("was_compromised"):
            if status == "disabled_or_revoked" or status != "configured":
                compromised_keys.append(entry)
            else:
                configured_keys.append(entry)
        elif status == "configured":
            configured_keys.append(entry)
        else:
            missing_keys.append(entry)

    return {
        "configured": configured_keys,
        "missing": missing_keys,
        "compromised": compromised_keys,
    }


def check_runtime_services() -> Dict[str, Any]:
    """Check health of Ollama, Gateway, and OmniMesh hub."""
    services = {}

    # 1. Local Ollama
    try:
        r = httpx.get("http://127.0.0.1:11434/api/tags", timeout=3.0)
        if r.status_code == 200:
            models = [m.get("name") for m in r.json().get("models", [])]
            services["ollama"] = {
                "ok": True,
                "label": "Local Ollama (11434)",
                "detail": f"Active ({len(models)} models available: {', '.join(models[:3])})",
            }
        else:
            services["ollama"] = {
                "ok": False,
                "label": "Local Ollama (11434)",
                "detail": f"HTTP {r.status_code}",
            }
    except Exception as exc:
        services["ollama"] = {
            "ok": False,
            "label": "Local Ollama (11434)",
            "detail": f"Offline ({exc.__class__.__name__})",
        }

    # 2. Company Dashboard / OmniMesh Hub
    try:
        r = httpx.get("http://127.0.0.1:8000/", timeout=3.0)
        if r.status_code == 200:
            services["omnimesh"] = {
                "ok": True,
                "label": "OmniMesh Hub / Dashboard (8000)",
                "detail": "Online (200 OK)",
            }
        else:
            services["omnimesh"] = {
                "ok": False,
                "label": "OmniMesh Hub / Dashboard (8000)",
                "detail": f"HTTP {r.status_code}",
            }
    except Exception as exc:
        services["omnimesh"] = {
            "ok": False,
            "label": "OmniMesh Hub / Dashboard (8000)",
            "detail": f"Offline ({exc.__class__.__name__})",
        }

    # 3. Gateway Daemon Process
    try:
        import psutil
        gateway_running = False
        gateway_pid = None
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            cmdline = " ".join(p.info.get("cmdline") or [])
            if "hermes" in cmdline.lower() and "gateway" in cmdline.lower() and "run" in cmdline.lower():
                gateway_running = True
                gateway_pid = p.info.get("pid")
                break
        services["gateway"] = {
            "ok": gateway_running,
            "label": "Telegram Gateway Daemon",
            "detail": f"Running (PID: {gateway_pid})" if gateway_running else "Not Running",
        }
    except Exception as exc:
        services["gateway"] = {
            "ok": True,  # Assume ok if psutil not present
            "label": "Telegram Gateway Daemon",
            "detail": f"Unable to inspect psutil: {exc}",
        }

    return services


def generate_telegram_alert(
    api_audit: Dict[str, Any], services: Dict[str, Any]
) -> str:
    """Format a clean, readable Markdown alert for Telegram."""
    lines = [
        "🛡️ *Hermes Health & API Key Status Report*",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # Service Status Section
    lines.append("*📡 System & Daemon Status:*")
    all_services_ok = True
    for s_key, s_data in services.items():
        icon = "✅" if s_data["ok"] else "❌"
        if not s_data["ok"]:
            all_services_ok = False
        lines.append(f"{icon} *{s_data['label']}:* {s_data['detail']}")

    lines.append("")

    # Compromised / Revoked Section
    if api_audit["compromised"]:
        lines.append("⚠️ *Compromised / Revoked API Keys:*")
        lines.append("_(These were disabled to protect account safety and prevent failover loops)_")
        for k in api_audit["compromised"]:
            lines.append(f"• 🔴 `{k['var']}` ({k['name']})")
            lines.append(f"   ↳ _{k['description']}_")
        lines.append("")

    # Missing Optional Keys Section
    if api_audit["missing"]:
        lines.append("🔑 *Missing / Inactive API Keys:*")
        lines.append("_(Add these to your local `.env` to unlock extra capabilities)_")
        for k in api_audit["missing"]:
            lines.append(f"• ⚪ `{k['var']}` ({k['name']})")
            lines.append(f"   ↳ _{k['description']}_")
        lines.append("")

    # Active / Healthy Providers Section
    if api_audit["configured"]:
        lines.append("✨ *Active & Working Capabilities:*")
        for k in api_audit["configured"]:
            lines.append(f"• 🟢 `{k['var']}`: {k['name']}")
        lines.append("")

    # Instructions
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📝 *How to add replacement keys:*")
    lines.append("Open `Hermes agent\\.env` and paste your new keys:")
    lines.append("```bash")
    if api_audit["compromised"]:
        for k in api_audit["compromised"]:
            lines.append(f"{k['var']}=your_new_key_here")
    lines.append("```")
    lines.append("Hermes will automatically detect updated keys on next turn.")

    return "\n".join(lines)


def send_to_telegram(message: str) -> bool:
    """Send message to Telegram via hermes CLI."""
    hermes_bin = APP_DIR / "venv" / "Scripts" / "hermes.exe"
    if not hermes_bin.exists():
        hermes_bin = Path("hermes")

    try:
        res = subprocess.run(
            [str(hermes_bin), "send", "--to", "telegram", message],
            cwd=str(APP_DIR),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if res.returncode == 0:
            print(f"[Watchdog] Successfully sent notification to Telegram: {res.stdout.strip()}")
            return True
        else:
            print(f"[Watchdog] Hermes send error ({res.returncode}): {res.stderr.strip()}", file=sys.stderr)
            return False
    except Exception as exc:
        print(f"[Watchdog] Execution failed: {exc}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Hermes Health & API Key Watchdog")
    parser.add_argument(
        "--notify-telegram",
        action="store_true",
        help="Send health report and missing API keys directly to Telegram",
    )
    parser.add_argument(
        "--alert-on-error",
        action="store_true",
        help="Only send Telegram alert if services are down or compromised keys exist",
    )
    parser.add_argument(
        "--cron",
        action="store_true",
        help="Hermes cron mode: emit alert directly to stdout if alert is needed, otherwise stay silent",
    )
    args = parser.parse_args()

    api_audit = check_api_keys()
    services = check_runtime_services()

    has_compromised = bool(api_audit["compromised"])
    has_service_down = any(not s["ok"] for s in services.values())
    alert_needed = has_compromised or has_service_down

    alert_text = generate_telegram_alert(api_audit, services)

    # Check if running interactively or inside a pipeline/cron
    is_tty = sys.stdout.isatty()

    if args.cron or not is_tty:
        # Cron mode / pipeline mode: Hermes delivers non-empty stdout to Telegram
        if alert_needed:
            print(alert_text)
        return

    print("[Watchdog] Auditing Hermes health and API keys...")
    print("\n--- Diagnostic Summary ---")
    print(f"Active Keys: {len(api_audit['configured'])}")
    print(f"Compromised / Revoked: {len(api_audit['compromised'])}")
    print(f"Missing Optional: {len(api_audit['missing'])}")
    for s_name, s_data in services.items():
        print(f"Service [{s_name}]: {'OK' if s_data['ok'] else 'FAIL'} - {s_data['detail']}")

    if args.notify_telegram or (args.alert_on_error and alert_needed):
        print("\n[Watchdog] Dispatching Telegram notification...")
        send_to_telegram(alert_text)
    else:
        print("\n[Watchdog] Notification skipped (run with --notify-telegram to dispatch).")


if __name__ == "__main__":
    main()
