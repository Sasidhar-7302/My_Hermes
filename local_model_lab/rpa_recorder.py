# -*- coding: utf-8 -*-
"""
RPA Macro Recorder & Replayer for Hermes Agent
Records user mouse clicks, drags, keystrokes, and delays, saving them as named workflows,
and replays them with humanized natural timing variations.
"""

from __future__ import annotations

import json
import logging
import random
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MACRO_DIR = Path(__file__).resolve().parent / "rpa_macros"
MACRO_DIR.mkdir(parents=True, exist_ok=True)

try:
    from pynput import keyboard, mouse
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

try:
    import pyautogui
    HAS_PYAUTOGUI = True
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
except ImportError:
    HAS_PYAUTOGUI = False


@dataclass
class RecordedAction:
    """A single recorded user action."""
    type: str           # "click", "type", "key_down", "key_up", "scroll", "move"
    timestamp: float    # Seconds since recording started
    x: int = 0
    y: int = 0
    button: str = ""    # "left", "right", "middle"
    key: str = ""       # Key string
    text: str = ""      # Typed characters
    scroll_amount: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RecordedAction:
        return cls(**data)


@dataclass
class Recording:
    """A collection of recorded actions forming an RPA macro."""
    name: str
    created_at: str
    duration: float
    actions: List[RecordedAction]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "duration": self.duration,
            "actions": [a.to_dict() for a in self.actions],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Recording:
        return cls(
            name=data.get("name", "macro"),
            created_at=data.get("created_at", ""),
            duration=float(data.get("duration", 0.0)),
            actions=[RecordedAction.from_dict(a) for a in data.get("actions", [])],
            metadata=data.get("metadata", {}),
        )

    def save(self, filepath: Optional[Path] = None) -> Path:
        target = filepath or (MACRO_DIR / f"{self.name}.json")
        target.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return target

    @classmethod
    def load(cls, filepath: Path) -> Recording:
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return cls.from_dict(data)


class RPARecorder:
    """Manages active macro recording and replaying."""

    def __init__(self):
        self.is_recording = False
        self.is_replaying = False
        self._start_time = 0.0
        self._actions: List[RecordedAction] = []
        self._mouse_listener: Optional[Any] = None
        self._key_listener: Optional[Any] = None

    def start_recording(self, name: str = "new_macro") -> Dict[str, Any]:
        """Begins recording mouse and keyboard actions."""
        if not HAS_PYNPUT:
            return {"status": "error", "message": "pynput is not installed."}
        if self.is_recording:
            return {"status": "error", "message": "Already recording."}

        self._actions = []
        self._start_time = time.time()
        self.is_recording = True

        def _on_click(x, y, button, pressed):
            if pressed and self.is_recording:
                t = time.time() - self._start_time
                btn_name = button.name if hasattr(button, "name") else str(button)
                self._actions.append(RecordedAction(
                    type="click", timestamp=t, x=int(x), y=int(y), button=btn_name
                ))

        def _on_scroll(x, y, dx, dy):
            if self.is_recording:
                t = time.time() - self._start_time
                self._actions.append(RecordedAction(
                    type="scroll", timestamp=t, x=int(x), y=int(y), scroll_amount=int(dy)
                ))

        def _on_press(key):
            if self.is_recording:
                t = time.time() - self._start_time
                key_str = getattr(key, "char", None) or getattr(key, "name", str(key))
                self._actions.append(RecordedAction(
                    type="key", timestamp=t, key=str(key_str)
                ))

        self._mouse_listener = mouse.Listener(on_click=_on_click, on_scroll=_on_scroll)
        self._key_listener = keyboard.Listener(on_press=_on_press)
        self._mouse_listener.start()
        self._key_listener.start()

        return {"status": "recording", "name": name, "started_at": self._start_time}

    def stop_recording(self, name: str = "new_macro") -> Dict[str, Any]:
        """Stops the active recording and persists the macro."""
        if not self.is_recording:
            return {"status": "error", "message": "Not currently recording."}

        self.is_recording = False
        duration = time.time() - self._start_time

        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._key_listener:
            self._key_listener.stop()

        clean_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name).strip("_") or "macro"
        recording = Recording(
            name=clean_name,
            created_at=datetime.now(timezone.utc).isoformat(),
            duration=duration,
            actions=self._actions,
            metadata={"action_count": len(self._actions)}
        )
        saved_path = recording.save()

        return {
            "status": "success",
            "name": clean_name,
            "duration": round(duration, 2),
            "action_count": len(self._actions),
            "file": str(saved_path),
        }

    def replay(self, name: str, speed: float = 1.0) -> Dict[str, Any]:
        """Replays a recorded macro with natural humanized variations."""
        if not HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui is not installed."}

        target = MACRO_DIR / f"{name}.json"
        if not target.exists():
            return {"status": "error", "message": f"Macro '{name}' not found."}

        recording = Recording.load(target)
        self.is_replaying = True

        def _execute_replay():
            try:
                prev_time = 0.0
                for action in recording.actions:
                    if not self.is_replaying:
                        break

                    delta = max(0.01, (action.timestamp - prev_time) / max(0.1, speed))
                    jitter = random.uniform(-0.02, 0.02)
                    time.sleep(max(0.01, delta + jitter))
                    prev_time = action.timestamp

                    if action.type == "click":
                        pyautogui.click(x=action.x, y=action.y, button=action.button or "left")
                    elif action.type == "scroll":
                        pyautogui.scroll(action.scroll_amount * 100)
                    elif action.type == "key" and action.key:
                        if len(action.key) == 1:
                            pyautogui.write(action.key)
                        else:
                            pyautogui.press(action.key)
            except Exception as exc:
                logger.error(f"Replay error: {exc}")
            finally:
                self.is_replaying = False

        thread = threading.Thread(target=_execute_replay, daemon=True)
        thread.start()
        return {"status": "replaying", "name": name, "actions": len(recording.actions)}

    def list_recordings(self) -> List[Dict[str, Any]]:
        """Lists all saved macros."""
        results = []
        for p in MACRO_DIR.glob("*.json"):
            try:
                rec = Recording.load(p)
                results.append({
                    "name": rec.name,
                    "created_at": rec.created_at,
                    "duration": round(rec.duration, 2),
                    "action_count": len(rec.actions),
                    "file": str(p),
                })
            except Exception:
                pass
        return sorted(results, key=lambda x: x["name"])


_rpa_instance = RPARecorder()


def get_rpa_recorder() -> RPARecorder:
    """Returns the singleton RPA recorder instance."""
    return _rpa_instance
