# -*- coding: utf-8 -*-
"""
Discord Channel Gateway for Hermes Agent
Handles slash commands, incoming interaction webhooks, Ed25519 signatures,
and outbound message dispatching.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests
from fastapi import Request

from .policy import ChannelPolicyManager

logger = logging.getLogger(__name__)


@dataclass
class DiscordConfig:
    enabled: bool
    application_id: str
    public_key: str
    bot_token: str
    allowed_channels: str = ""
    allowed_users: str = ""


class DiscordGateway:
    """Discord interactions & slash command webhook adapter."""

    def __init__(self, dispatcher_callback=None):
        self.dispatcher = dispatcher_callback
        self.policy = ChannelPolicyManager()
        self._cfg: Optional[DiscordConfig] = self._load_config()

    def _load_config(self) -> Optional[DiscordConfig]:
        enabled = os.environ.get("DISCORD_ENABLED", "").lower() in ("true", "1", "yes")
        app_id = os.environ.get("DISCORD_APPLICATION_ID", "").strip()
        public_key = os.environ.get("DISCORD_PUBLIC_KEY", "").strip()
        bot_token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()

        if not (enabled and app_id and public_key):
            return None

        return DiscordConfig(
            enabled=enabled,
            application_id=app_id,
            public_key=public_key,
            bot_token=bot_token,
            allowed_channels=os.environ.get("DISCORD_ALLOWED_CHANNELS", ""),
            allowed_users=os.environ.get("DISCORD_ALLOWED_USERS", ""),
        )

    def is_enabled(self) -> bool:
        return self._cfg is not None

    def get_status(self) -> Dict[str, Any]:
        return {
            "channel": "discord",
            "enabled": self.is_enabled(),
            "has_token": bool(self._cfg and self._cfg.bot_token),
            "app_id": self._cfg.application_id if self._cfg else "",
        }

    def _verify_signature(self, headers: Dict[str, Any], body: bytes) -> bool:
        if not self._cfg or not self._cfg.public_key:
            return False
        sig = headers.get("x-signature-ed25519") or headers.get("X-Signature-Ed25519")
        ts = headers.get("x-signature-timestamp") or headers.get("X-Signature-Timestamp")
        if not sig or not ts:
            return False
        try:
            from nacl.signing import VerifyKey
            verify_key = VerifyKey(bytes.fromhex(self._cfg.public_key))
            verify_key.verify(ts.encode("utf-8") + body, bytes.fromhex(sig))
            return True
        except Exception:
            return False

    async def handle_webhook(self, request: Request) -> Tuple[int, Any]:
        if not self._cfg:
            return 503, {"status": "disabled", "message": "Discord gateway not configured"}

        raw_body = await request.body()
        # Verify Ed25519 signature if PyNaCl available
        try:
            import nacl  # noqa: F401
            if not self._verify_signature(dict(request.headers), raw_body):
                return 401, {"error": "Invalid signature"}
        except ImportError:
            pass

        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except Exception:
            payload = {}

        # 1. Discord PING response
        if payload.get("type") == 1:
            return 200, {"type": 1}

        # 2. Slash command or message component interaction
        if payload.get("type") in (2, 3):
            user_data = payload.get("member", {}).get("user") or payload.get("user") or {}
            user_id = str(user_data.get("id", ""))
            channel_id = str(payload.get("channel_id", ""))

            # Authorization check
            if not self.policy.is_allowed("discord", user_id):
                code = self.policy.request_pairing_code("discord", user_id)
                return 200, {
                    "type": 4,
                    "data": {
                        "content": f"🔒 Hermes Security: You are not authorized. Pairing code: `{code}`. Approve this in the Hermes Operations Center.",
                        "flags": 64  # Ephemeral (visible only to user)
                    }
                }

            # Extract command text
            data = payload.get("data", {})
            options = data.get("options", [])
            prompt = options[0].get("value", "") if options else data.get("name", "")

            # Dispatch in background and defer response
            token = payload.get("token")
            if token and self.dispatcher:
                asyncio.create_task(self._process_and_followup(token, prompt, user_id))

            # Immediate ACK with deferred response (type 5)
            return 200, {"type": 5}

        return 200, {"status": "ignored"}

    async def _process_and_followup(self, token: str, prompt: str, user_id: str):
        """Processes command through Hermes dispatcher and sends follow-up response."""
        try:
            response_text = await self.dispatcher(prompt, channel="discord", user_id=user_id)
            if self._cfg:
                url = f"https://discord.com/api/v10/webhooks/{self._cfg.application_id}/{token}/messages/@original"
                requests.patch(url, json={"content": response_text[:2000]}, timeout=10)
        except Exception as exc:
            logger.error(f"Discord follow-up error: {exc}")

    def send_message(self, channel_id: str, message: str) -> bool:
        """Sends an outbound message to a Discord channel using Bot token."""
        if not self._cfg or not self._cfg.bot_token:
            return False
        try:
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            headers = {
                "Authorization": f"Bot {self._cfg.bot_token}",
                "Content-Type": "application/json"
            }
            resp = requests.post(url, headers=headers, json={"content": message[:2000]}, timeout=10)
            return resp.status_code in (200, 201)
        except Exception as exc:
            logger.error(f"Failed to send Discord message: {exc}")
            return False
