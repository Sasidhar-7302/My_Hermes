# -*- coding: utf-8 -*-
"""
Channel Policy & Authorization Manager for Hermes Agent
Manages user allowlists, pairing codes, and access policies across all communication channels.
"""

from __future__ import annotations

import json
import logging
import random
import string
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_POLICY_FILE = Path(__file__).resolve().parent.parent / "local_model_lab" / "channel_allowlist.json"


class ChannelPolicyManager:
    """Manages channel allowlists, pairing requests, and agent profile routing."""

    def __init__(self, filepath: Optional[Path] = None):
        self.filepath = filepath or DEFAULT_POLICY_FILE
        self._data: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.filepath.exists():
            try:
                self._data = json.loads(self.filepath.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning(f"Failed to load channel policy: {exc}")
                self._data = {}

    def _save(self) -> None:
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Failed to save channel policy: {exc}")

    def _ensure_channel(self, channel: str) -> Dict[str, Any]:
        ch = channel.lower()
        if ch not in self._data:
            self._data[ch] = {
                "allowlist": [],
                "pending_codes": {},
                "agents": {},
            }
        return self._data[ch]

    def is_allowed(self, channel: str, user_id: str) -> bool:
        """Checks if user_id is on channel allowlist."""
        entry = self._ensure_channel(channel)
        allowlist = entry.get("allowlist", [])
        # If allowlist is empty, default to allowing if pairing is disabled, or requiring pairing
        return str(user_id) in [str(u) for u in allowlist]

    def add_to_allowlist(self, channel: str, user_id: str) -> None:
        entry = self._ensure_channel(channel)
        allowlist = entry.setdefault("allowlist", [])
        uid_str = str(user_id)
        if uid_str not in allowlist:
            allowlist.append(uid_str)
            self._save()

    def remove_from_allowlist(self, channel: str, user_id: str) -> bool:
        entry = self._ensure_channel(channel)
        allowlist = entry.get("allowlist", [])
        uid_str = str(user_id)
        if uid_str in allowlist:
            allowlist.remove(uid_str)
            self._save()
            return True
        return False

    def request_pairing_code(self, channel: str, user_id: str) -> str:
        """Generates a 6-digit numeric pairing code valid for 10 minutes."""
        entry = self._ensure_channel(channel)
        pending = entry.setdefault("pending_codes", {})
        code = "".join(random.choices(string.digits, k=6))
        pending[code] = {
            "user_id": str(user_id),
            "created_at": time.time(),
            "expires_at": time.time() + 600,
        }
        self._save()
        return code

    def approve_pairing_code(self, channel: str, code: str) -> Optional[str]:
        """Approves a pairing code and adds user to channel allowlist."""
        entry = self._ensure_channel(channel)
        pending = entry.get("pending_codes", {})
        c = code.strip()
        if c in pending:
            item = pending.pop(c)
            if item.get("expires_at", 0) >= time.time():
                user_id = item.get("user_id")
                if user_id:
                    self.add_to_allowlist(channel, user_id)
                    self._save()
                    return user_id
            self._save()
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Returns overview of allowed users and pending codes across channels."""
        summary = {}
        for ch in ["telegram", "discord", "slack", "whatsapp", "relay"]:
            entry = self._ensure_channel(ch)
            summary[ch] = {
                "allowed_users": entry.get("allowlist", []),
                "pending_codes_count": len(entry.get("pending_codes", {})),
            }
        return summary
