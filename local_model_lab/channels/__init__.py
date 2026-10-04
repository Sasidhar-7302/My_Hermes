# -*- coding: utf-8 -*-
"""
Multi-Channel Gateway Adapters Package for Hermes Agent
Connectors for Discord, Slack, WhatsApp, Telegram, and Universal Relay.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .policy import ChannelPolicyManager
from .discord import DiscordGateway
from .slack import SlackGateway
from .whatsapp import WhatsAppGateway
from .telegram import TelegramGateway
from .relay import RelayGateway

logger = logging.getLogger(__name__)

_policy_instance: Optional[ChannelPolicyManager] = None
_discord_instance: Optional[DiscordGateway] = None
_slack_instance: Optional[SlackGateway] = None
_whatsapp_instance: Optional[WhatsAppGateway] = None
_telegram_instance: Optional[TelegramGateway] = None
_relay_instance: Optional[RelayGateway] = None


async def default_channel_dispatcher(prompt: str, channel: str = "web", user_id: str = "") -> str:
    """Dispatches a channel prompt through Hermes agent company dispatcher."""
    try:
        from local_model_lab.agent_dispatcher import route_request, call_model, log_task
        from local_model_lab.pii_shield import mask_sensitive_text

        # Sanitize prompt before dispatch
        clean_prompt = mask_sensitive_text(prompt)

        # Route to appropriate role
        route_res = route_request(clean_prompt)
        role = route_res.get("domain", "CEO") if isinstance(route_res, dict) else str(route_res)
        from local_model_lab.role_registry import ROLES

        role_info = ROLES.get(role, ROLES["CEO"])
        soul = role_info.get("soul", "")
        models = role_info.get("models", [])

        system_msg = f"{soul}\nYou are communicating via {channel.upper()} with user {user_id}. Provide concise, helpful responses."
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": clean_prompt},
        ]

        # Failover cascade across verified models
        for m in models:
            resp, lat, status = call_model(m["provider"], m["id"], messages)
            if resp:
                log_task(role, clean_prompt, resp, lat, m["id"])
                return resp

        return f"[{role}] All model quota cascades exhausted. Please check API keys in Hermes dashboard."
    except Exception as exc:
        logger.error(f"Channel dispatch error: {exc}")
        return f"Hermes Agent error: {str(exc)}"


def get_channel_policy_manager() -> ChannelPolicyManager:
    global _policy_instance
    if _policy_instance is None:
        _policy_instance = ChannelPolicyManager()
    return _policy_instance


def get_discord_gateway() -> DiscordGateway:
    global _discord_instance
    if _discord_instance is None:
        _discord_instance = DiscordGateway(dispatcher_callback=default_channel_dispatcher)
    return _discord_instance


def get_slack_gateway() -> SlackGateway:
    global _slack_instance
    if _slack_instance is None:
        _slack_instance = SlackGateway(dispatcher_callback=default_channel_dispatcher)
    return _slack_instance


def get_whatsapp_gateway() -> WhatsAppGateway:
    global _whatsapp_instance
    if _whatsapp_instance is None:
        _whatsapp_instance = WhatsAppGateway(dispatcher_callback=default_channel_dispatcher)
    return _whatsapp_instance


def get_telegram_gateway() -> TelegramGateway:
    global _telegram_instance
    if _telegram_instance is None:
        _telegram_instance = TelegramGateway(dispatcher_callback=default_channel_dispatcher)
    return _telegram_instance


def get_relay_gateway() -> RelayGateway:
    global _relay_instance
    if _relay_instance is None:
        _relay_instance = RelayGateway(dispatcher_callback=default_channel_dispatcher)
    return _relay_instance


def get_all_channel_statuses() -> Dict[str, Any]:
    """Returns overview of all multi-channel gateways."""
    policy = get_channel_policy_manager()
    return {
        "discord": get_discord_gateway().get_status(),
        "slack": get_slack_gateway().get_status(),
        "whatsapp": get_whatsapp_gateway().get_status(),
        "telegram": get_telegram_gateway().get_status(),
        "relay": get_relay_gateway().get_status(),
        "policy": policy.get_summary(),
    }
