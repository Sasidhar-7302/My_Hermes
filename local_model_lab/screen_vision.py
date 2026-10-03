# -*- coding: utf-8 -*-
"""
Screen Vision & OmniParser Engine for Hermes
Provides visual screen parsing, visual element grounding, and screen description
using a local-first multi-tier architecture:

1. Local Vision via Ollama (Qwen-VL, Llava, Llama3.2-Vision)
2. Cloud Vision via Google Gemini (gemini-2.0-flash / gemini-1.5-flash)
3. OpenRouter Vision fallback (Qwen-VL / Gemini Vision)
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)

# Ensure Windows UTF-8 stdout safety
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Check PIL
try:
    from PIL import Image, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL not installed. Run: uv pip install pillow")


def load_env_keys() -> Dict[str, str]:
    """Loads API keys from .env without polluting logging."""
    keys: Dict[str, str] = {}
    env_paths = [
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(os.getcwd()) / ".env"
    ]
    for p in env_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            keys[k.strip()] = v.strip().strip('"').strip("'")
            except Exception:
                pass
            break
    # Merge with os.environ
    for k in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "OLLAMA_HOST"):
        if k in os.environ and os.environ[k]:
            keys[k] = os.environ[k]
    return keys


def capture_screen(max_width: int = 1920) -> Tuple[Optional[Image.Image], Optional[bytes], Tuple[int, int]]:
    """
    Captures the primary monitor screenshot.
    Returns: (PIL.Image, jpeg_bytes, (original_width, original_height))
    """
    if not HAS_PIL:
        return None, None, (0, 0)

    img = None
    # 1. Try standard ImageGrab
    try:
        img = ImageGrab.grab()
    except Exception:
        pass

    # 2. Try after attaching to interactive desktop WinSta0\\default
    if img is None:
        try:
            import win32service, win32con
            hwinsta = win32service.OpenWindowStation('WinSta0', False, win32con.GENERIC_ALL)
            hwinsta.SetProcessWindowStation()
            hdesk = win32service.OpenDesktop('default', 0, False, win32con.GENERIC_ALL)
            hdesk.SetThreadDesktop()
            img = ImageGrab.grab()
        except Exception:
            pass

    # 3. Fallback: Create diagnostic canvas if running in headless/locked background shell
    if img is None:
        try:
            import ctypes
            sw = ctypes.windll.user32.GetSystemMetrics(0) or 1920
            sh = ctypes.windll.user32.GetSystemMetrics(1) or 1080
            img = Image.new("RGB", (sw, sh), color=(30, 30, 30))
        except Exception:
            img = Image.new("RGB", (1920, 1080), color=(30, 30, 30))

    try:
        orig_w, orig_h = img.size

        # Resize if overly massive to optimize token consumption and latency
        if orig_w > max_width:
            scale = max_width / float(orig_w)
            new_h = int(orig_h * scale)
            img_resized = img.resize((max_width, new_h), Image.Resampling.LANCZOS)
        else:
            img_resized = img

        buffer = io.BytesIO()
        img_resized.save(buffer, format="JPEG", quality=85)
        raw_bytes = buffer.getvalue()
        return img_resized, raw_bytes, (orig_w, orig_h)
    except Exception as exc:
        logger.error(f"Screen capture processing failed: {exc}")
        return None, None, (0, 0)


class ScreenVision:
    """Multi-backend Vision Grounding & Screen Understanding Engine."""

    def __init__(self, ollama_host: str = "http://127.0.0.1:11434"):
        self.ollama_host = ollama_host.rstrip("/")
        self.keys = load_env_keys()

    def _is_ollama_online(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.ollama_host}/api/tags", headers={"User-Agent": "Hermes-Vision"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_installed_ollama_vision_models(self) -> List[str]:
        """Detects available vision-capable models in local Ollama."""
        try:
            req = urllib.request.Request(f"{self.ollama_host}/api/tags", headers={"User-Agent": "Hermes-Vision"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                vision_keywords = ["vl", "vision", "llava", "moondream", "bakllava"]
                return [m for m in models if any(k in m.lower() for k in vision_keywords)]
        except Exception:
            return []

    def describe_screen(self, prompt: str = "Describe what is currently visible on my screen in 2-3 concise sentences.") -> str:
        """Analyzes the current screen and returns a natural language summary."""
        img, img_bytes, (orig_w, orig_h) = capture_screen()
        if not img or not img_bytes:
            return "Failed to capture desktop screenshot (PIL ImageGrab unavailable)."

        b64_img = base64.b64encode(img_bytes).decode("utf-8")

        # 1. Try Local Ollama Vision
        vision_models = self.get_installed_ollama_vision_models()
        if vision_models:
            v_model = vision_models[0]
            try:
                payload = json.dumps({
                    "model": v_model,
                    "prompt": prompt,
                    "images": [b64_img],
                    "stream": False
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.ollama_host}/api/generate",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=25.0) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    text = res.get("response", "").strip()
                    if text:
                        return f"[Local Vision ({v_model})]: {text}"
            except Exception as e:
                logger.debug(f"Local Ollama vision failed: {e}")

        # 2. Try Gemini Cloud Vision
        gemini_key = self.keys.get("GEMINI_API_KEY")
        if gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
                body = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": b64_img
                                }
                            }
                        ]
                    }],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300}
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(body).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=12.0) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return f"[Gemini Vision]: {text}"
            except Exception as e:
                logger.debug(f"Gemini cloud vision failed: {e}")

        # 3. Try OpenRouter Vision
        or_key = self.keys.get("OPENROUTER_API_KEY")
        if or_key:
            try:
                url = "https://openrouter.ai/api/v1/chat/completions"
                body = {
                    "model": "google/gemini-2.0-flash-001",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                        ]
                    }],
                    "max_tokens": 300
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(body).encode("utf-8"),
                    headers={"Authorization": f"Bearer {or_key}", "Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=15.0) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    text = res["choices"][0]["message"]["content"].strip()
                    return f"[OpenRouter Vision]: {text}"
            except Exception as e:
                logger.debug(f"OpenRouter vision failed: {e}")

        return "Screenshot captured, but no active vision models (Ollama VL / Gemini / OpenRouter) were able to respond."

    def locate_element(self, target_description: str) -> Optional[Dict[str, Any]]:
        """
        Locates a target UI element on the screen using visual grounding.
        Returns coordinate dict: {"center": [x, y], "label": ..., "box_2d": [ymin, xmin, ymax, xmax]}
        Normalized to true desktop pixel coordinates.
        """
        img, img_bytes, (orig_w, orig_h) = capture_screen()
        if not img or not img_bytes:
            return None

        curr_w, curr_h = img.size
        b64_img = base64.b64encode(img_bytes).decode("utf-8")

        prompt = (
            f"You are a computer vision grounding engine. Find the visual element matching: '{target_description}'. "
            f"Return ONLY a JSON object in this exact schema with 0-1000 normalized coordinates: "
            f'{{"found": true, "box_2d": [ymin, xmin, ymax, xmax], "label": "description"}}. '
            f'If not found or visible, return {{"found": false}}.'
        )

        raw_response = ""

        # 1. Local Vision
        vision_models = self.get_installed_ollama_vision_models()
        if vision_models:
            try:
                payload = json.dumps({
                    "model": vision_models[0],
                    "prompt": prompt,
                    "images": [b64_img],
                    "format": "json",
                    "stream": False
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.ollama_host}/api/generate",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=20.0) as resp:
                    raw_response = json.loads(resp.read().decode("utf-8")).get("response", "")
            except Exception:
                pass

        # 2. Gemini Cloud Fallback
        if not raw_response and self.keys.get("GEMINI_API_KEY"):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.keys['GEMINI_API_KEY']}"
                body = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}}
                        ]
                    }],
                    "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(body).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=12.0) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    raw_response = res["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                pass

        if not raw_response:
            return None

        # Parse JSON
        try:
            # Strip markdown fences if present
            cleaned = re.sub(r'```json\s*', '', raw_response)
            cleaned = re.sub(r'```\s*', '', cleaned).strip()
            data = json.loads(cleaned)

            if not data.get("found"):
                return None

            box = data.get("box_2d")  # [ymin, xmin, ymax, xmax] in 0-1000 scale
            if not box or len(box) != 4:
                return None

            ymin, xmin, ymax, xmax = [float(c) for c in box]

            # Scale to actual screen pixels
            real_xmin = int((xmin / 1000.0) * orig_w)
            real_xmax = int((xmax / 1000.0) * orig_w)
            real_ymin = int((ymin / 1000.0) * orig_h)
            real_ymax = int((ymax / 1000.0) * orig_h)

            center_x = (real_xmin + real_xmax) // 2
            center_y = (real_ymin + real_ymax) // 2

            return {
                "found": True,
                "target": target_description,
                "label": data.get("label", target_description),
                "center": (center_x, center_y),
                "bounding_box": (real_xmin, real_ymin, real_xmax - real_xmin, real_ymax - real_ymin),
            }
        except Exception as e:
            logger.debug(f"Failed to parse vision grounding response: {e}")
            return None


# Global Singleton
_global_screen_vision: Optional[ScreenVision] = None


def get_screen_vision() -> ScreenVision:
    """Returns global singleton ScreenVision."""
    global _global_screen_vision
    if _global_screen_vision is None:
        _global_screen_vision = ScreenVision()
    return _global_screen_vision
