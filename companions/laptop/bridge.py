# -*- coding: utf-8 -*-
"""
Hermes Laptop Companion Bridge
Coordinates secondary laptop workstations, remote worker nodes, and cross-PC clipboard sharing.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LaptopBridge:
    """Coordinates laptop workstations and remote worker tasks."""

    def __init__(self):
        self.active_laptops: Dict[str, Dict[str, Any]] = {}
        self.command_queue: List[Dict[str, Any]] = []

    def register_laptop_node(self, node_id: str, hostname: str, os_type: str = "Laptop", ip: str = "127.0.0.1"):
        """Registers a secondary laptop node in the mesh network."""
        self.active_laptops[node_id] = {
            "node_id": node_id,
            "name": hostname,
            "hostname": hostname,
            "os_type": os_type,
            "ip": ip,
            "last_heartbeat": time.time(),
            "cpu_percent": 0.0,
            "ram_percent": 0.0,
        }
        logger.info(f"💻 Registered laptop workstation node '{hostname}' ({node_id}) from {ip}")

    def register_node(self, node_id: str, hostname: str, ip: str = "127.0.0.1", os_type: str = "Laptop"):
        """Convenience alias for register_laptop_node."""
        return self.register_laptop_node(node_id=node_id, hostname=hostname, os_type=os_type, ip=ip)

    def get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves details of a registered laptop node."""
        return self.active_laptops.get(node_id)

    def update_telemetry(self, node_id: str, cpu_pct: float, ram_pct: float, battery_pct: Optional[int] = None):
        """Updates resource utilization metrics reported by the laptop."""
        if node_id in self.active_laptops:
            self.active_laptops[node_id].update({
                "cpu_percent": cpu_pct,
                "ram_percent": ram_pct,
                "battery_percent": battery_pct,
                "last_heartbeat": time.time(),
            })

    def dispatch_remote_task(self, target_laptop_id: str, command: str, task_id: str) -> Dict[str, Any]:
        """Queues a terminal command to be executed remotely on the laptop worker node."""
        task = {
            "task_id": task_id,
            "target_node": target_laptop_id,
            "command": command,
            "status": "QUEUED",
            "created_at": time.time(),
        }
        self.command_queue.append(task)
        logger.info(f"💻 Dispatched remote command to laptop {target_laptop_id}: '{command}'")
        return task


_laptop_bridge_instance: Optional[LaptopBridge] = None


def get_laptop_bridge() -> LaptopBridge:
    global _laptop_bridge_instance
    if _laptop_bridge_instance is None:
        _laptop_bridge_instance = LaptopBridge()
    return _laptop_bridge_instance
