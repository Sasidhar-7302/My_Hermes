# -*- coding: utf-8 -*-
"""
Hermes 24/7 Power & Remote Wake-on-LAN (WoL) Engine
Ensures Hermes Host PC runs continuously without unattended sleep or hibernation,
and enables remote Wake-on-LAN power-on from Smartphone, Smartwatch, or Laptop.
"""

from __future__ import annotations

import os
import sys
import time
import socket
import struct
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Windows Kernel Power Management Constants
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_USER_PRESENT = 0x00000004
ES_AWAYMODE_REQUIRED = 0x00000040
ES_CONTINUOUS = 0x80000000

_is_keepalive_active = False


def enable_24_7_keepalive(allow_display_sleep: bool = True) -> bool:
    """
    Prevents Windows from entering sleep or hibernation while keeping Hermes 24/7 active.
    If allow_display_sleep is True (default), monitors can turn off / lock to save power
    and prevent OLED/LCD burn-in, while CPU, network, and AI background workers stay 100% awake.
    """
    global _is_keepalive_active
    if sys.platform != "win32":
        return True

    try:
        import ctypes
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        if allow_display_sleep:
            flags |= ES_AWAYMODE_REQUIRED
        else:
            flags |= ES_DISPLAY_REQUIRED

        result = ctypes.windll.kernel32.SetThreadExecutionState(flags)
        _is_keepalive_active = (result != 0)
        if _is_keepalive_active:
            logger.info("Hermes 24/7 Keep-Alive enabled (ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED).")
        return _is_keepalive_active
    except Exception as exc:
        logger.warning(f"Failed to set thread execution state: {exc}")
        return False


def disable_keepalive() -> bool:
    """Restores standard Windows power management."""
    global _is_keepalive_active
    if sys.platform != "win32":
        return True

    try:
        import ctypes
        result = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        _is_keepalive_active = False
        logger.info("Hermes Keep-Alive disabled. Standard Windows power policies restored.")
        return True
    except Exception as exc:
        logger.warning(f"Failed to reset thread execution state: {exc}")
        return False


def is_keepalive_active() -> bool:
    return _is_keepalive_active


# ── WAKE-ON-LAN (WoL) ENGINE ──────────────────────────────────────────────────

DEFAULT_WOL_PROFILES = [
    {
        "interface": "Wi-Fi 2",
        "name": "Realtek 8812BU Wireless LAN 802.11ac USB NIC",
        "mac": "00:13:EF:60:04:42",
        "ip": "10.0.0.60",
        "subnet_broadcast": "10.0.0.255",
        "is_primary": True,
    },
    {
        "interface": "Ethernet",
        "name": "Intel(R) Ethernet Connection (17) I219-V",
        "mac": "04:42:1A:EA:BF:E7",
        "ip": "",
        "subnet_broadcast": "10.0.0.255",
        "is_primary": False,
    }
]


def clean_mac_address(mac_str: str) -> str:
    """Normalizes MAC string to standard uppercase colon-separated format."""
    cleaned = mac_str.replace(":", "").replace("-", "").replace(".", "").strip().upper()
    if len(cleaned) != 12:
        raise ValueError(f"Invalid MAC address format: '{mac_str}' (expected 12 hex chars)")
    return ":".join(cleaned[i:i+2] for i in range(0, 12, 2))


def create_magic_packet(mac_address: str) -> bytes:
    """
    Constructs a standard Wake-on-LAN Magic Packet:
    6 bytes of 0xFF followed by 16 repetitions of the target 6-byte MAC address.
    """
    cleaned = mac_address.replace(":", "").replace("-", "").replace(".", "").strip()
    mac_bytes = bytes.fromhex(cleaned)
    return b"\xFF" * 6 + (mac_bytes * 16)


def send_wake_on_lan(
    mac_address: str = "00:13:EF:60:04:42",
    broadcast_ip: str = "255.255.255.255",
    port: int = 9
) -> Dict[str, Any]:
    """
    Broadcasts a Wake-on-LAN Magic Packet across the network.
    Sends to both the specified broadcast IP and subnet broadcast for maximum router penetration.
    """
    try:
        norm_mac = clean_mac_address(mac_address)
        packet = create_magic_packet(norm_mac)

        targets = [broadcast_ip]
        if broadcast_ip == "255.255.255.255":
            targets.append("10.0.0.255")

        sent_count = 0
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for t_ip in targets:
                try:
                    sock.sendto(packet, (t_ip, port))
                    # Also send to port 7 as standard fallback
                    sock.sendto(packet, (t_ip, 7))
                    sent_count += 2
                except Exception as send_err:
                    logger.debug(f"WoL broadcast to {t_ip}:{port} error: {send_err}")

        return {
            "status": "success",
            "message": f"Wake-on-LAN Magic Packet broadcasted for MAC {norm_mac}",
            "mac": norm_mac,
            "packets_sent": sent_count,
            "targets": targets,
            "ports": [port, 7],
            "timestamp": time.time(),
        }
    except Exception as exc:
        logger.error(f"Failed to send Wake-on-LAN: {exc}")
        return {
            "status": "error",
            "message": str(exc),
            "timestamp": time.time(),
        }


def wake_hermes_pc() -> Dict[str, Any]:
    """Wakes this Hermes PC by broadcasting to all recognized network interfaces."""
    results = []
    for prof in DEFAULT_WOL_PROFILES:
        mac = prof["mac"]
        res = send_wake_on_lan(mac_address=mac, broadcast_ip=prof.get("subnet_broadcast", "255.255.255.255"))
        res["interface"] = prof["interface"]
        results.append(res)
    return {
        "status": "success",
        "summary": "Wake-on-LAN Magic Packets sent to all Hermes PC interfaces.",
        "results": results,
    }


def get_wol_profiles() -> List[Dict[str, Any]]:
    """Returns host network adapter MAC addresses and WoL configuration."""
    return DEFAULT_WOL_PROFILES


# ── STANDALONE WAKE SCRIPTS GENERATOR ─────────────────────────────────────────

def generate_standalone_wake_scripts(output_dir: Optional[Path] = None) -> Dict[str, str]:
    """
    Generates turnkey 1-click Wake-on-LAN scripts for Laptop, Mobile, and secondary devices.
    """
    out = output_dir or (Path(__file__).resolve().parent / "wake_scripts")
    out.mkdir(parents=True, exist_ok=True)

    primary_mac = "00:13:EF:60:04:42"
    eth_mac = "04:42:1A:EA:BF:E7"
    broadcast_ip = "10.0.0.255"

    # 1. Windows Batch Script (.bat) - 1-click on any Windows laptop
    bat_content = f"""@echo off
title Wake Hermes PC (Wake-on-LAN)
echo [Hermes] Broadcasting Wake-on-LAN Magic Packet to {primary_mac}...
powershell -Command "$mac = '{primary_mac}'.Replace(':','').Replace('-',''); $packet = [byte[]](,0xFF * 6) + (,([byte[]]($mac -split '(..)' | ? {{$_}} | %% {{ [Convert]::ToByte($_, 16) }})) * 16); $client = New-Object System.Net.Sockets.UdpClient; $client.Connect('{broadcast_ip}', 9); $client.Send($packet, $packet.Length); $client.Close(); Write-Host 'Magic packet sent successfully!'"
powershell -Command "$mac = '{eth_mac}'.Replace(':','').Replace('-',''); $packet = [byte[]](,0xFF * 6) + (,([byte[]]($mac -split '(..)' | ? {{$_}} | %% {{ [Convert]::ToByte($_, 16) }})) * 16); $client = New-Object System.Net.Sockets.UdpClient; $client.Connect('{broadcast_ip}', 9); $client.Send($packet, $packet.Length); $client.Close(); Write-Host 'Ethernet fallback packet sent!'"
echo.
echo Wake packet sent to Hermes Host PC. Wait ~10-15 seconds for boot.
pause
"""
    (out / "Wake-Hermes.bat").write_text(bat_content, encoding="utf-8")

    # 2. Python Script (.py) - Universal for Mac, Linux, Python laptops, Raspberry Pi
    py_content = f"""# -*- coding: utf-8 -*-
import socket

MACS = ["{primary_mac}", "{eth_mac}"]
BROADCASTS = ["{broadcast_ip}", "255.255.255.255"]
PORTS = [9, 7]

def wake():
    print("[Hermes WoL] Waking Hermes PC...")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for mac in MACS:
            cleaned = mac.replace(":", "").replace("-", "")
            packet = b"\\xFF" * 6 + (bytes.fromhex(cleaned) * 16)
            for b_ip in BROADCASTS:
                for port in PORTS:
                    s.sendto(packet, (b_ip, port))
            print(f"  -> Sent magic packet for MAC {{mac}}")
    print("[Hermes WoL] Packets broadcasted. PC waking up in ~10-15s.")

if __name__ == "__main__":
    wake()
"""
    (out / "wake_hermes.py").write_text(py_content, encoding="utf-8")

    # 3. Unix Bash Script (.sh) for macOS / Linux laptops
    sh_content = f"""#!/usr/bin/env bash
echo "Waking Hermes PC ({primary_mac})..."
python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1); [s.sendto(b'\\xFF'*6 + bytes.fromhex(m.replace(':',''))*16, (b, 9)) for m in ['{primary_mac}','{eth_mac}'] for b in ['{broadcast_ip}','255.255.255.255']]"
echo "Magic packets sent successfully!"
"""
    (out / "wake_hermes.sh").write_text(sh_content, encoding="utf-8")

    return {
        "bat": str(out / "Wake-Hermes.bat"),
        "py": str(out / "wake_hermes.py"),
        "sh": str(out / "wake_hermes.sh"),
    }
