# -*- coding: utf-8 -*-
"""
Telegram Channel Gateway for Hermes Agent
Handles Telegram Bot API webhooks, long polling, and markdown message replies.
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
class TelegramConfig:
    enabled: bool
    token: str
    allowed_user_id: str = ""


class TelegramGateway:
    """Telegram Bot API adapter."""

    def __init__(self, dispatcher_callback=None):
        self.dispatcher = dispatcher_callback
        self.policy = ChannelPolicyManager()
        self._cfg: Optional[TelegramConfig] = self._load_config()

    def _load_config(self) -> Optional[TelegramConfig]:
        enabled = os.environ.get("TELEGRAM_ENABLED", "").lower() in ("true", "1", "yes")
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        allowed_user = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "").strip()

        if not (enabled and token):
            return None

        cfg = TelegramConfig(
            enabled=enabled,
            token=token,
            allowed_user_id=allowed_user,
        )
        if allowed_user:
            self.policy.add_to_allowlist("telegram", allowed_user)
        return cfg

    def is_enabled(self) -> bool:
        return self._cfg is not None

    def get_status(self) -> Dict[str, Any]:
        return {
            "channel": "telegram",
            "enabled": self.is_enabled(),
            "has_token": bool(self._cfg and self._cfg.token),
            "allowed_user_id": self._cfg.allowed_user_id if self._cfg else "",
        }

    async def handle_webhook(self, request: Request) -> Tuple[int, Any]:
        if not self._cfg:
            return 503, {"status": "disabled", "message": "Telegram gateway not configured"}

        try:
            update = await request.json()
        except Exception:
            return 400, {"error": "Invalid JSON"}

        message = update.get("message", {}) or update.get("edited_message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        user_id = str(message.get("from", {}).get("id", ""))
        text = str(message.get("text", "")).strip()

        if not text or not chat_id:
            return 200, {"status": "ignored"}

        # Pairing verification command: /pair 123456
        if text.startswith("/pair") or text.startswith("pair "):
            code = text.split()[-1].strip()
            approved_user = self.policy.approve_pairing_code("telegram", code)
            if approved_user:
                self.send_message(chat_id, "✅ *Hermes Agent:* Pairing approved! You can now send prompts.")
                return 200, {"status": "paired"}
            else:
                self.send_message(chat_id, "❌ *Hermes Agent:* Invalid or expired pairing code.")
                return 200, {"status": "invalid_code"}

        # Authorization check
        if not self.policy.is_allowed("telegram", user_id):
            code = self.policy.request_pairing_code("telegram", user_id)
            self.send_message(
                chat_id,
                f"🔒 *Hermes Security:*\nYou are not authorized.\nYour pairing code is: `{code}`\n"
                "Enter this code in the Hermes Operations Center or reply: `/pair <code>`"
            )
            return 200, {"status": "pairing_requested"}

        # Authorized: Dispatch to Hermes Agent
        if self.dispatcher:
            asyncio.create_task(self._process_and_reply(chat_id, text, user_id))

        return 200, {"status": "received"}

    async def _process_and_reply(self, chat_id: str, prompt: str, user_id: str):
        if not self.dispatcher:
            return
        try:
            response = await self.dispatcher(prompt, channel="telegram", user_id=user_id)
            self.send_message(chat_id, response)
        except Exception as exc:
            logger.error(f"Telegram dispatch failed: {exc}")

    def send_message(self, chat_id: str, message: str) -> bool:
        """Sends an outbound message to a Telegram chat via Bot API."""
        if not self._cfg or not self._cfg.token:
            return False
        try:
            url = f"https://api.telegram.org/bot{self._cfg.token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message[:4000],
                "parse_mode": "Markdown",
            }
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as exc:
            logger.error(f"Failed to send Telegram message: {exc}")
            return False
