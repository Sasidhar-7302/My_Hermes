# -*- coding: utf-8 -*-
"""
Hermes Companion Platform Gateway Adapter
Connects the Omni-Mesh Companion Hub (Smartwatch, Smartphone, Laptop) directly into the
Hermes Gateway to create authentic Hermes Agent sessions with tools, memory, and multi-turn execution.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import (
    BasePlatformAdapter,
    MessageEvent,
    MessageType,
    SendResult,
)

logger = logging.getLogger(__name__)


def check_companion_requirements() -> bool:
    """Check if companion adapter dependencies are available."""
    try:
        from companions.hub import get_omni_mesh_hub
        return True
    except Exception:
        return False


class CompanionAdapter(BasePlatformAdapter):
    """
    Companion Ecosystem <-> Hermes Gateway Adapter.
    Routes inbound prompts from Smartwatch, Smartphone, and Laptop into real Hermes Agent sessions.
    """

    def __init__(self, config: PlatformConfig):
        # Platform("companion") resolves via dynamic _missing_ on Platform enum
        super().__init__(config, Platform("companion"))
        self._hub = None

    async def connect(self, *, is_reconnect: bool = False) -> bool:
        """Binds the gateway listener to OmniMeshHub."""
        from companions.hub import get_omni_mesh_hub

        self._hub = get_omni_mesh_hub()
        self._hub.set_gateway_listener(self._on_inbound_mesh_prompt)
        self._running = True
        logger.info("[companion] Connected to Omni-Mesh Hub. Ready for companion sessions.")
        return True

    async def disconnect(self) -> None:
        """Unbinds the gateway listener."""
        if self._hub:
            self._hub.set_gateway_listener(None)
        self._running = False
        logger.info("[companion] Disconnected from Omni-Mesh Hub.")

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        """Sends the Hermes agent response back to the originating companion device."""
        from companions.hub import get_omni_mesh_hub

        hub = self._hub or get_omni_mesh_hub()
        ok = await hub.send_agent_reply(device_id=chat_id, response_text=content)
        return SendResult(success=ok)

    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        from companions.hub import get_omni_mesh_hub

        hub = self._hub or get_omni_mesh_hub()
        dev = hub.devices.get(chat_id)
        if dev:
            return {"name": dev.name, "type": dev.device_type, "chat_id": chat_id}
        return {"name": f"Companion-{chat_id[:6]}", "type": "dm", "chat_id": chat_id}

    async def _on_inbound_mesh_prompt(
        self, device_id: str, device_type: str, device_name: str, prompt: str
    ) -> None:
        """Processes prompt from companion device and passes it to the Hermes Agent execution pipeline."""
        source = self.build_source(
            chat_id=device_id,
            chat_name=f"{device_name} ({device_type})",
            chat_type="dm",
            user_id=device_id,
            user_name=device_name,
        )

        event = MessageEvent(
            text=prompt,
            message_type=MessageType.TEXT,
            source=source,
            raw_message={"device_id": device_id, "device_type": device_type},
            message_id=f"mesh_{int(time.time() * 1000)}",
        )

        task = asyncio.create_task(self.handle_message(event))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)


def _build_adapter(config: PlatformConfig) -> CompanionAdapter:
    return CompanionAdapter(config)


def _is_connected(config: PlatformConfig) -> bool:
    return True


def register(ctx) -> None:
    """Plugin entry point registered by the Hermes plugin engine."""
    ctx.register_platform(
        name="companion",
        label="Companion Ecosystem",
        adapter_factory=_build_adapter,
        check_fn=check_companion_requirements,
        is_connected=_is_connected,
        allow_all_env="COMPANION_ALLOW_ALL_USERS",
        emoji="📱",
        pii_safe=True,
    )
