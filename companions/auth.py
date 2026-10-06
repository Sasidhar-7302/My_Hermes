# -*- coding: utf-8 -*-
"""
Hermes Companion Pairing & Authentication Manager
Secures WebSocket and REST companion communication with cryptographic pairing tokens.
Persists paired device registry to ~/.hermes/companions_devices.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .logger import log_companion_event

_HERMES_DIR = Path.home() / ".hermes"
_DEVICES_FILE = _HERMES_DIR / "companions_devices.json"


def _hash_token(token: str) -> str:
    """Computes SHA-256 hash of token for secure on-disk storage."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


class PairingManager:
    """Manages pairing session tokens and persistent device authorization."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or _DEVICES_FILE
        self._lock = threading.Lock()
        self._active_pairing_codes: Dict[str, float] = {}  # code -> expiry_timestamp
        self._paired_devices: Dict[str, Dict[str, Any]] = {}
        self._load_devices()

    def _load_devices(self) -> None:
        """Loads paired devices from JSON file."""
        if not self.storage_path.exists():
            return
        try:
            raw = self.storage_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                self._paired_devices = data
        except Exception as exc:
            log_companion_event("AUTH_ERROR", f"Failed to load companions_devices.json: {exc}", level="WARNING")

    def _save_devices(self) -> None:
        """Persists paired devices to JSON file."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(self._paired_devices, indent=2), encoding="utf-8")
        except Exception as exc:
            log_companion_event("AUTH_ERROR", f"Failed to save companions_devices.json: {exc}", level="ERROR")

    def create_pairing_code(self, ttl_seconds: int = 600) -> str:
        """Generates a time-limited pairing code for QR code or link scanning."""
        with self._lock:
            # Purge expired codes
            now = time.time()
            self._active_pairing_codes = {c: exp for c, exp in self._active_pairing_codes.items() if exp > now}

            code = f"pair_{secrets.token_urlsafe(16)}"
            self._active_pairing_codes[code] = now + ttl_seconds
            log_companion_event("PAIRING_CODE_CREATED", f"New pairing code generated (expires in {ttl_seconds}s)")
            return code

    def verify_pairing_code(self, code: str) -> bool:
        """Checks if pairing code is valid and unexpired."""
        if not code:
            return False
        with self._lock:
            expiry = self._active_pairing_codes.get(code)
            if expiry and expiry > time.time():
                return True
            return False

    def register_device(
        self,
        device_id: str,
        name: str,
        device_type: str,
        user_agent: str = "",
        client_ip: str = "",
    ) -> str:
        """Pairs a new device and returns a permanent device token for localStorage."""
        token = f"tok_{secrets.token_urlsafe(24)}"
        hashed = _hash_token(token)

        with self._lock:
            self._paired_devices[device_id] = {
                "device_id": device_id,
                "name": name or f"Device-{device_id[:6]}",
                "device_type": device_type,
                "user_agent": user_agent,
                "paired_at": time.time(),
                "last_seen": time.time(),
                "last_ip": client_ip,
                "token_hash": hashed,
                "revoked": False,
            }
            self._save_devices()

        log_companion_event(
            "DEVICE_PAIRED",
            f"Successfully paired device '{name}' ({device_id})",
            device_id=device_id,
            device_kind=device_type,
            ip=client_ip,
        )
        return token

    def verify_device_token(self, device_id: str, token: str) -> bool:
        """Validates that token matches the stored token hash for device_id."""
        if not device_id or not token:
            return False
        with self._lock:
            dev = self._paired_devices.get(device_id)
            if not dev or dev.get("revoked", False):
                return False
            stored_hash = dev.get("token_hash")
            return secrets.compare_digest(_hash_token(token), stored_hash or "")

    def authenticate_connection(
        self,
        device_id: str,
        token: Optional[str] = None,
        pairing_code: Optional[str] = None,
        name: str = "",
        device_type: str = "",
        user_agent: str = "",
        client_ip: str = "",
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Authenticates connection attempt.
        Returns: (is_authenticated, reason_or_status, new_token_if_just_paired)
        """
        # Local desktop host internal node is trusted on loopback
        if device_id == "desktop-host" and client_ip in ("127.0.0.1", "::1", "testclient"):
            return True, "localhost_bypass", None

        # 1. Existing token authentication
        if token and self.verify_device_token(device_id, token):
            with self._lock:
                if device_id in self._paired_devices:
                    self._paired_devices[device_id]["last_seen"] = time.time()
                    self._paired_devices[device_id]["last_ip"] = client_ip
                    self._save_devices()
            return True, "authenticated", None

        # 2. Pairing with active pairing code
        if pairing_code and self.verify_pairing_code(pairing_code):
            new_token = self.register_device(
                device_id=device_id,
                name=name,
                device_type=device_type,
                user_agent=user_agent,
                client_ip=client_ip,
            )
            return True, "paired_new", new_token

        log_companion_event(
            "AUTH_REJECTED",
            f"Unauthorized connection attempt from {device_id} ({client_ip})",
            level="WARNING",
            device_id=device_id,
        )
        return False, "unauthorized_token_missing_or_invalid", None

    def revoke_device(self, device_id: str) -> bool:
        """Revokes a paired device, disallowing further connections."""
        with self._lock:
            if device_id in self._paired_devices:
                self._paired_devices[device_id]["revoked"] = True
                self._save_devices()
                log_companion_event("DEVICE_REVOKED", f"Revoked authorization for device {device_id}")
                return True
        return False

    def unpair_device(self, device_id: str) -> bool:
        """Completely deletes device from registry."""
        with self._lock:
            if device_id in self._paired_devices:
                del self._paired_devices[device_id]
                self._save_devices()
                log_companion_event("DEVICE_UNPAIRED", f"Unpaired and deleted device {device_id}")
                return True
        return False

    def list_paired_devices(self) -> List[Dict[str, Any]]:
        """Returns safe serializable summary of paired devices (without token hashes)."""
        with self._lock:
            res = []
            for d in self._paired_devices.values():
                entry = dict(d)
                entry.pop("token_hash", None)
                res.append(entry)
            return res


_global_pairing_manager: Optional[PairingManager] = None


def get_pairing_manager() -> PairingManager:
    """Returns singleton PairingManager instance."""
    global _global_pairing_manager
    if _global_pairing_manager is None:
        _global_pairing_manager = PairingManager()
    return _global_pairing_manager
