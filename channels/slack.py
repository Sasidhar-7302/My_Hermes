# -*- coding: utf-8 -*-
"""
Slack Channel Gateway for Hermes Agent
Handles Slack Events API, slash commands (/hermes), HMAC-SHA256 request verification,
and direct bot messages.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests
from fastapi import Request

from .policy import ChannelPolicyManager

logger = logging.getLogger(__name__)


@dataclass
class SlackConfig:
    enabled: bool
    bot_token: str
    signing_secret: str
    allowed_channels: str = ""
    allowed_users: str = ""


class SlackGateway:
    """Slack Events API & slash command webhook adapter."""

    def __init__(self, dispatcher_callback=None):
        self.dispatcher = dispatcher_callback
        self.policy = ChannelPolicyManager()
        self._cfg: Optional[SlackConfig] = self._load_config()

    def _load_config(self) -> Optional[SlackConfig]:
        enabled = os.environ.get("SLACK_ENABLED", "").lower() in ("true", "1", "yes")
        bot_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
        signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "").strip()

        if not (enabled and bot_token and signing_secret):
            return None

        return SlackConfig(
            enabled=enabled,
            bot_token=bot_token,
            signing_secret=signing_secret,
            allowed_channels=os.environ.get("SLACK_ALLOWED_CHANNELS", ""),
            allowed_users=os.environ.get("SLACK_ALLOWED_USERS", ""),
        )

    def is_enabled(self) -> bool:
        return self._cfg is not None

    def get_status(self) -> Dict[str, Any]:
        return {
            "channel": "slack",
            "enabled": self.is_enabled(),
            "has_token": bool(self._cfg and self._cfg.bot_token),
            "has_secret": bool(self._cfg and self._cfg.signing_secret),
        }

    def _verify_signature(self, headers: Dict[str, Any], body: bytes) -> bool:
        if not self._cfg or not self._cfg.signing_secret:
            return False
        timestamp = headers.get("x-slack-request-timestamp", "")
        slack_sig = headers.get("x-slack-signature", "")
        if not timestamp or not slack_sig:
            return False

        # Reject requests older than 5 minutes
        if abs(time.time() - float(timestamp)) > 300:
            return False

        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8', errors='replace')}"
        computed = "v0=" + hmac.new(
            self._cfg.signing_secret.encode("utf-8"),
            sig_basestring.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed, slack_sig)

    async def handle_webhook(self, request: Request) -> Tuple[int, Any]:
        if not self._cfg:
            return 503, {"status": "disabled", "message": "Slack gateway not configured"}

        raw_body = await request.body()
        if not self._verify_signature(dict(request.headers), raw_body):
            return 403, {"error": "Invalid Slack signature"}

        content_type = request.headers.get("content-type", "")

        # 1. Slash Command handling (/hermes <prompt>)
        if "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            text = str(form.get("text", "")).strip()
            user_id = str(form.get("user_id", "")).strip()
            response_url = str(form.get("response_url", "")).strip()

            if not self.policy.is_allowed("slack", user_id):
                code = self.policy.request_pairing_code("slack", user_id)
                return 200, {
                    "text": f"🔒 Hermes Security: You are not paired. Enter pairing code `{code}` in the Hermes Operations Center."
                }

            if self.dispatcher:
                asyncio.create_task(self._process_and_respond(response_url, text, user_id))

            return 200, {"text": "⚡ Hermes is working on your request..."}

        # 2. Events API handling
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except Exception:
            payload = {}

        # URL verification challenge
        if payload.get("type") == "url_verification":
            return 200, {"challenge": payload.get("challenge")}

        if payload.get("type") == "event_callback":
            event = payload.get("event", {})
            if event.get("type") == "message" and not event.get("bot_id"):
                text = str(event.get("text", "")).strip()
                user_id = str(event.get("user", "")).strip()
                channel_id = str(event.get("channel", "")).strip()

                if self.policy.is_allowed("slack", user_id) and self.dispatcher:
                    asyncio.create_task(self._process_and_chat_post(channel_id, text, user_id))

            return 200, {"status": "ok"}

        return 200, {"status": "ignored"}

    async def _process_and_respond(self, response_url: str, text: str, user_id: str):
        if not response_url or not self.dispatcher:
            return
        try:
            response = await self.dispatcher(text, channel="slack", user_id=user_id)
            requests.post(response_url, json={"text": response}, timeout=10)
        except Exception as exc:
            logger.error(f"Slack response_url failed: {exc}")

    async def _process_and_chat_post(self, channel_id: str, text: str, user_id: str):
        if not self.dispatcher:
            return
        try:
            response = await self.dispatcher(text, channel="slack", user_id=user_id)
            self.send_message(channel_id, response)
        except Exception as exc:
            logger.error(f"Slack chat.postMessage failed: {exc}")

    def send_message(self, channel_id: str, message: str) -> bool:
        """Sends an outbound message to a Slack channel via chat.postMessage."""
        if not self._cfg or not self._cfg.bot_token:
            return False
        try:
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {self._cfg.bot_token}",
                "Content-Type": "application/json"
            }
            resp = requests.post(url, headers=headers, json={"channel": channel_id, "text": message}, timeout=10)
            return resp.status_code == 200 and resp.json().get("ok", False)
        except Exception as exc:
            logger.error(f"Failed to post Slack message: {exc}")
            return False
