# -*- coding: utf-8 -*-
"""
WhatsApp Channel Gateway for Hermes Agent
Supports inbound & outbound messaging via Twilio WhatsApp API or Baileys Bridge,
with pairing authorization.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests
from fastapi import Request

from .policy import ChannelPolicyManager

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppConfig:
    enabled: bool
    provider: str  # "twilio" or "baileys"
    account_sid: str = ""
    auth_token: str = ""
    from_number: str = ""
    baileys_url: str = ""
    baileys_token: str = ""


class WhatsAppGateway:
    """WhatsApp messaging gateway supporting Twilio and Baileys."""

    def __init__(self, dispatcher_callback=None):
        self.dispatcher = dispatcher_callback
        self.policy = ChannelPolicyManager()
        self._cfg: Optional[WhatsAppConfig] = self._load_config()

    def _load_config(self) -> Optional[WhatsAppConfig]:
        enabled = os.environ.get("WHATSAPP_ENABLED", "").lower() in ("true", "1", "yes")
        provider = os.environ.get("WHATSAPP_PROVIDER", "twilio").lower()

        sid = os.environ.get("WHATSAPP_ACCOUNT_SID", "").strip()
        auth_token = os.environ.get("WHATSAPP_AUTH_TOKEN", "").strip()
        from_num = os.environ.get("WHATSAPP_FROM_NUMBER", "").strip()

        baileys_url = os.environ.get("WHATSAPP_BAILEYS_URL", "").strip()
        baileys_token = os.environ.get("WHATSAPP_BAILEYS_TOKEN", "").strip()

        if not enabled:
            return None

        return WhatsAppConfig(
            enabled=enabled,
            provider=provider,
            account_sid=sid,
            auth_token=auth_token,
            from_number=from_num,
            baileys_url=baileys_url,
            baileys_token=baileys_token,
        )

    def is_enabled(self) -> bool:
        return self._cfg is not None

    def get_status(self) -> Dict[str, Any]:
        return {
            "channel": "whatsapp",
            "enabled": self.is_enabled(),
            "provider": self._cfg.provider if self._cfg else "twilio",
            "has_credentials": bool(
                self._cfg and (
                    (self._cfg.account_sid and self._cfg.auth_token) or
                    (self._cfg.baileys_url)
                )
            ),
            "from_number": self._cfg.from_number if self._cfg else "",
        }

    async def handle_webhook(self, request: Request) -> Tuple[int, Any]:
        if not self._cfg:
            return 503, {"status": "disabled", "message": "WhatsApp gateway not configured"}

        form = await request.form()
        from_number = str(form.get("From", "")).replace("whatsapp:", "").strip()
        body = str(form.get("Body", "")).strip()

        if not from_number or not body:
            return 200, {"status": "ignored"}

        # Pairing verification command: /pair 123456
        if body.lower().startswith("pair ") or body.lower().startswith("/pair"):
            code = body.split()[-1].strip()
            user_paired = self.policy.approve_pairing_code("whatsapp", code)
            if user_paired:
                self.send_message(from_number, "✅ Hermes Agent: WhatsApp pairing approved! You can now send prompts.")
                return 200, {"status": "paired"}
            else:
                self.send_message(from_number, "❌ Hermes Agent: Invalid or expired pairing code.")
                return 200, {"status": "invalid_code"}

        # Check authorization
        if not self.policy.is_allowed("whatsapp", from_number):
            code = self.policy.request_pairing_code("whatsapp", from_number)
            self.send_message(
                from_number,
                f"🔒 Hermes Security: Unauthorized phone number.\nPairing code: {code}\n"
                "Enter this code in the Hermes Operations Center or reply: /pair <code>"
            )
            return 200, {"status": "pairing_requested"}

        # Authorized: Dispatch to Hermes Agent
        if self.dispatcher:
            asyncio.create_task(self._process_and_reply(from_number, body))

        return 200, {"status": "received"}

    async def _process_and_reply(self, to_number: str, message: str):
        if not self.dispatcher:
            return
        try:
            response = await self.dispatcher(message, channel="whatsapp", user_id=to_number)
            self.send_message(to_number, response)
        except Exception as exc:
            logger.error(f"WhatsApp dispatch failed: {exc}")

    def send_message(self, to_number: str, message: str) -> bool:
        """Sends outbound WhatsApp message via Twilio or Baileys."""
        if not self._cfg:
            return False

        clean_to = to_number.replace("whatsapp:", "").strip()
        if not clean_to.startswith("+") and not clean_to.startswith("whatsapp:"):
            clean_to = f"+{clean_to}"

        # 1. Twilio API
        if self._cfg.provider == "twilio" and self._cfg.account_sid and self._cfg.auth_token:
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self._cfg.account_sid}/Messages.json"
                from_field = f"whatsapp:{self._cfg.from_number}" if not self._cfg.from_number.startswith("whatsapp:") else self._cfg.from_number
                to_field = f"whatsapp:{clean_to}"

                resp = requests.post(
                    url,
                    auth=(self._cfg.account_sid, self._cfg.auth_token),
                    data={"From": from_field, "To": to_field, "Body": message[:1600]},
                    timeout=10,
                )
                return resp.status_code in (200, 201)
            except Exception as exc:
                logger.error(f"Twilio WhatsApp send failed: {exc}")
                return False

        # 2. Baileys Bridge
        elif self._cfg.provider == "baileys" and self._cfg.baileys_url:
            try:
                url = f"{self._cfg.baileys_url.rstrip('/')}/send"
                headers = {"Authorization": f"Bearer {self._cfg.baileys_token}"} if self._cfg.baileys_token else {}
                resp = requests.post(
                    url,
                    headers=headers,
                    json={"recipient": clean_to, "message": message},
                    timeout=10,
                )
                return resp.status_code in (200, 201)
            except Exception as exc:
                logger.error(f"Baileys WhatsApp send failed: {exc}")
                return False

        return False
