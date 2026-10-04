# -*- coding: utf-8 -*-
"""
Universal Webhook Relay Gateway for Hermes Agent
Accepts generic webhook relays from external automation tools (Signal, Teams, Home Assistant, n8n, Zapier)
and routes back responses.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional, Tuple

import requests
from fastapi import Request

from .policy import ChannelPolicyManager

logger = logging.getLogger(__name__)


class RelayGateway:
    """Universal webhook relay adapter."""

    def __init__(self, dispatcher_callback=None):
        self.dispatcher = dispatcher_callback
        self.policy = ChannelPolicyManager()

    def is_enabled(self) -> bool:
        return os.environ.get("RELAY_ENABLED", "true").lower() in ("true", "1", "yes")

    def get_status(self) -> Dict[str, Any]:
        return {
            "channel": "relay",
            "enabled": self.is_enabled(),
            "has_secret": bool(os.environ.get("RELAY_WEBHOOK_SECRET", "")),
        }

    async def handle_webhook(self, request: Request) -> Tuple[int, Any]:
        if not self.is_enabled():
            return 503, {"status": "disabled"}

        secret = os.environ.get("RELAY_WEBHOOK_SECRET", "").strip()
        if secret:
            token = request.headers.get("x-relay-token") or request.headers.get("authorization", "").replace("Bearer ", "")
            if token != secret:
                return 401, {"error": "Invalid relay token"}

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        text = str(payload.get("text") or payload.get("message") or payload.get("prompt") or "").strip()
        user_id = str(payload.get("user_id") or payload.get("from") or "relay_user")
        reply_url = str(payload.get("reply_url") or payload.get("response_url") or "")

        if not text:
            return 400, {"error": "Missing prompt or text in relay payload"}

        if self.dispatcher:
            response = await self.dispatcher(text, channel="relay", user_id=user_id)
            if reply_url:
                try:
                    requests.post(reply_url, json={"text": response}, timeout=10)
                except Exception as exc:
                    logger.warning(f"Failed to post to reply_url: {exc}")
            return 200, {"status": "success", "response": response}

        return 200, {"status": "received", "prompt": text}
