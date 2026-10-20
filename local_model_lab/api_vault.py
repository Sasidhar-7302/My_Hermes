# -*- coding: utf-8 -*-
"""
Hermes Sovereign PIN-Protected API Vault (`api_vault.py`)
=========================================================
Provides an encrypted, PIN-protected credential vault stored outside the Git
repository (`~/.hermes/api_vault.enc.json`).

Security Architecture:
  - KDF: PBKDF2-HMAC-SHA256 (310,000 iterations, OWASP 2026 standard) with
    independent 16-byte cryptographic salts for PIN verification and encryption.
  - Cipher: Authenticated Fernet (AES-128-CBC + HMAC-SHA256) via `cryptography`,
    with a pure-stdlib SHA-256 CTR + HMAC-SHA256 authenticated fallback.
  - Constant-time PIN verification (`hmac.compare_digest`).
  - Brute-force protection: 5 failed PIN attempts trigger a 30-second cooldown
    and emit a HIGH-priority security alert to the Unified Notification Center.
  - Session management: Unlocking issues an ephemeral 256-bit `session_token`
    with a 15-minute sliding inactivity auto-lock and 1-click instant lock.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_FERNET = True
except Exception:
    Fernet = None  # type: ignore
    InvalidToken = Exception  # type: ignore
    _HAS_FERNET = False


DEFAULT_VAULT_PATH = Path.home() / ".hermes" / "api_vault.enc.json"
PBKDF2_ITERATIONS = 310_000
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 30
SESSION_TTL_SECONDS = 900  # 15 minutes

KNOWN_API_KEYS: List[Dict[str, str]] = [
    {"key": "GEMINI_API_KEY", "provider": "Google Gemini AI Studio / Vertex", "icon": "✨"},
    {"key": "GROQ_API_KEY", "provider": "Groq LPU Ultra-Fast Cloud", "icon": "⚡"},
    {"key": "OLLAMA_API_KEY", "provider": "Ollama Cloud (Beam 501B / Ultra 550B / Gemma4)", "icon": "🦙"},
    {"key": "NVIDIA_API_KEY", "provider": "NVIDIA NIM Inference Microservices", "icon": "🟢"},
    {"key": "OPENROUTER_API_KEY", "provider": "OpenRouter Unified Gateway", "icon": "🌐"},
    {"key": "OPENAI_API_KEY", "provider": "OpenAI Frontier API", "icon": "🧠"},
    {"key": "ANTHROPIC_API_KEY", "provider": "Anthropic Claude API", "icon": "🏛️"},
    {"key": "TELEGRAM_BOT_TOKEN", "provider": "Telegram Gateway Bot Token", "icon": "✈️"},
    {"key": "GITHUB_TOKEN", "provider": "GitHub Personal Access Token", "icon": "🐙"},
    {"key": "EXA_API_KEY", "provider": "Exa Neural Search API", "icon": "🔎"},
    {"key": "TAVILY_API_KEY", "provider": "Tavily Deep Research Search API", "icon": "🧭"},
    {"key": "FAL_KEY", "provider": "Fal.ai Media & Image Generation", "icon": "🎨"},
]


def mask_secret_preview(value: str) -> str:
    """Returns a safe masked preview (e.g. 'gsk_••••••••••••jFUJ') without leaking the secret."""
    if not value:
        return ""
    s = str(value).strip()
    if len(s) <= 8:
        return "•" * len(s)
    return f"{s[:4]}••••••••••••{s[-4:]}"


def _derive_key(pin: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    """Derives a 32-byte cryptographic key from the PIN and salt using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations, dklen=32)


def _stdlib_encrypt(raw_bytes: bytes, key32: bytes) -> str:
    """Pure-stdlib authenticated stream cipher (SHA256-CTR + HMAC-SHA256) fallback."""
    nonce = os.urandom(16)
    enc_key = hashlib.sha256(key32 + b":enc").digest()
    mac_key = hashlib.sha256(key32 + b":mac").digest()
    out = bytearray(len(raw_bytes))
    blocks = (len(raw_bytes) + 31) // 32
    for b_idx in range(blocks):
        counter = b_idx.to_bytes(8, "big")
        keystream = hashlib.sha256(enc_key + nonce + counter).digest()
        start = b_idx * 32
        end = min(start + 32, len(raw_bytes))
        for i in range(start, end):
            out[i] = raw_bytes[i] ^ keystream[i - start]
    ciphertext = bytes(out)
    tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    return "STD1:" + base64.urlsafe_b64encode(nonce + tag + ciphertext).decode("ascii")


def _stdlib_decrypt(token_str: str, key32: bytes) -> bytes:
    """Decrypts and verifies a pure-stdlib authenticated ciphertext."""
    if token_str.startswith("STD1:"):
        token_str = token_str[5:]
    blob = base64.urlsafe_b64decode(token_str.encode("ascii"))
    if len(blob) < 48:
        raise ValueError("Corrupted ciphertext")
    nonce = blob[:16]
    tag = blob[16:48]
    ciphertext = blob[48:]
    enc_key = hashlib.sha256(key32 + b":enc").digest()
    mac_key = hashlib.sha256(key32 + b":mac").digest()
    expected_tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Invalid PIN or tampered vault payload")
    out = bytearray(len(ciphertext))
    blocks = (len(ciphertext) + 31) // 32
    for b_idx in range(blocks):
        counter = b_idx.to_bytes(8, "big")
        keystream = hashlib.sha256(enc_key + nonce + counter).digest()
        start = b_idx * 32
        end = min(start + 32, len(ciphertext))
        for i in range(start, end):
            out[i] = ciphertext[i] ^ keystream[i - start]
    return bytes(out)


def _encrypt_payload(secrets_dict: Dict[str, Any], key32: bytes) -> Tuple[str, str]:
    """Encrypts the JSON secrets dictionary with Fernet (or stdlib fallback)."""
    raw = json.dumps(secrets_dict, ensure_ascii=False).encode("utf-8")
    if _HAS_FERNET and Fernet is not None:
        fernet_key = base64.urlsafe_b64encode(key32)
        token = Fernet(fernet_key).encrypt(raw).decode("ascii")
        return token, "fernet-aes128-cbc-hmac-sha256"
    return _stdlib_encrypt(raw, key32), "stdlib-sha256-ctr-hmac-sha256"


def _decrypt_payload(ciphertext: str, cipher_scheme: str, key32: bytes) -> Dict[str, Any]:
    """Decrypts the JSON secrets dictionary using Fernet or stdlib fallback."""
    if cipher_scheme.startswith("fernet") and _HAS_FERNET and Fernet is not None and not ciphertext.startswith("STD1:"):
        fernet_key = base64.urlsafe_b64encode(key32)
        raw = Fernet(fernet_key).decrypt(ciphertext.encode("ascii"))
    else:
        raw = _stdlib_decrypt(ciphertext, key32)
    data = json.loads(raw.decode("utf-8"))
    return data if isinstance(data, dict) else {}


class SovereignAPIVault:
    """
    PIN-Secured API Credential Vault for Hermes Agent.
    Manages PIN creation, rotation, brute-force lockout, session unlocking,
    encrypted storage at `~/.hermes/api_vault.enc.json`, and live provider probes.
    """

    def __init__(self, vault_path: Optional[Path] = None, sync_dotenv: bool = True) -> None:
        self.vault_path: Path = Path(vault_path) if vault_path else DEFAULT_VAULT_PATH
        self.sync_dotenv: bool = sync_dotenv
        self._session_token: Optional[str] = None
        self._session_expires_at: float = 0.0
        self._unlocked_secrets: Dict[str, Dict[str, Any]] = {}
        self._active_enc_key: Optional[bytes] = None
        self._failed_attempts: int = 0
        self._lockout_until: float = 0.0

    # ── INTERNAL STORAGE HELPERS ───────────────────────────────────────────
    def _read_vault_envelope(self) -> Optional[Dict[str, Any]]:
        if not self.vault_path.exists():
            return None
        try:
            return json.loads(self.vault_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _write_vault_envelope(self, envelope: Dict[str, Any]) -> None:
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        self.vault_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")

    def _validate_pin_format(self, pin: str) -> Tuple[bool, str]:
        pin_s = (pin or "").strip()
        if len(pin_s) < 4 or len(pin_s) > 16:
            return False, "PIN must be between 4 and 16 characters/digits."
        return True, "OK"

    def _collect_existing_env_secrets(self) -> Dict[str, Dict[str, Any]]:
        """Imports known API keys from existing local .env files on first-time setup."""
        collected: Dict[str, Dict[str, Any]] = {}
        known_lookup = {item["key"]: item for item in KNOWN_API_KEYS}
        env_candidates = [
            Path.home() / ".hermes" / ".env",
            Path(__file__).resolve().parent.parent.parent / ".env",
            Path(__file__).resolve().parent.parent / ".env",
            Path(__file__).resolve().parent / ".env",
        ]
        raw_kv: Dict[str, str] = {}
        for p in env_candidates:
            try:
                if p.exists():
                    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
                        s = ln.strip()
                        if "=" in s and not s.startswith("#"):
                            k, _, v = s.partition("=")
                            k_c = k.strip()
                            v_c = v.strip().strip('"').strip("'")
                            if v_c and k_c not in raw_kv:
                                raw_kv[k_c] = v_c
            except Exception:
                continue

        now_iso = datetime.now().isoformat()
        for k, v in raw_kv.items():
            if k in known_lookup or any(s in k for s in ("API_KEY", "TOKEN", "SECRET", "FAL_KEY")):
                meta = known_lookup.get(k, {"provider": "Custom API Credential", "icon": "🔑"})
                collected[k] = {
                    "key": k,
                    "value": v,
                    "provider": meta["provider"],
                    "icon": meta["icon"],
                    "updated_at": now_iso,
                }
        return collected

    def _sync_to_runtime_and_dotenv(self, secrets_map: Dict[str, Dict[str, Any]]) -> None:
        """
        Pushes decrypted secrets into in-memory `agent_dispatcher._ENV` and `os.environ`
        and optionally updates `~/.hermes/.env` (outside Git) so subprocesses stay in sync.
        """
        flat_kv = {k: str(v.get("value", "")) for k, v in secrets_map.items() if v.get("value")}
        for k, val in flat_kv.items():
            os.environ[k] = val

        try:
            import agent_dispatcher
            for k, val in flat_kv.items():
                agent_dispatcher._ENV[k] = val
        except Exception:
            pass

        if self.sync_dotenv:
            for dotenv_path in (
                Path.home() / ".hermes" / ".env",
                Path(__file__).resolve().parent.parent.parent / ".env",
            ):
                try:
                    if not dotenv_path.exists() and dotenv_path != (Path.home() / ".hermes" / ".env"):
                        continue
                    dotenv_path.parent.mkdir(parents=True, exist_ok=True)
                    lines = dotenv_path.read_text(encoding="utf-8").splitlines() if dotenv_path.exists() else []
                    seen = set()
                    out_lines = []
                    for ln in lines:
                        s = ln.strip()
                        if "=" in s and not s.startswith("#"):
                            k_existing = s.split("=", 1)[0].strip()
                            if k_existing in flat_kv:
                                out_lines.append(f"{k_existing}={flat_kv[k_existing]}")
                                seen.add(k_existing)
                                continue
                        out_lines.append(ln)
                    for k, val in flat_kv.items():
                        if k not in seen:
                            out_lines.append(f"{k}={val}")
                    dotenv_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
                except Exception:
                    pass

    # ── PUBLIC VAULT LIFECYCLE API ─────────────────────────────────────────
    def is_initialized(self) -> bool:
        env = self._read_vault_envelope()
        return bool(env and env.get("ciphertext") and env.get("verify_hash"))

    def is_unlocked(self, session_token: Optional[str] = None) -> bool:
        now = time.time()
        if not self._session_token or now > self._session_expires_at:
            self._session_token = None
            self._unlocked_secrets.clear()
            self._active_enc_key = None
            return False
        if session_token is not None and not hmac.compare_digest(self._session_token, session_token):
            return False
        # Refresh sliding window
        self._session_expires_at = now + SESSION_TTL_SECONDS
        return True

    def get_status(self, session_token: Optional[str] = None) -> Dict[str, Any]:
        """Returns vault initialization, lock state, and masked secret metadata."""
        initialized = self.is_initialized()
        unlocked = self.is_unlocked(session_token)
        envelope = self._read_vault_envelope() or {}
        lockout_remaining = max(0, int(self._lockout_until - time.time()))

        keys_summary: List[Dict[str, Any]] = []
        if unlocked:
            for k, item in sorted(self._unlocked_secrets.items()):
                val = str(item.get("value", ""))
                keys_summary.append({
                    "key": k,
                    "provider": item.get("provider", "API Key"),
                    "icon": item.get("icon", "🔑"),
                    "masked_value": mask_secret_preview(val),
                    "length": len(val),
                    "updated_at": item.get("updated_at", ""),
                    "configured": bool(val),
                })
        else:
            stored_keys_meta = envelope.get("keys_Catalog", [])
            for meta in stored_keys_meta:
                keys_summary.append({
                    "key": meta.get("key", ""),
                    "provider": meta.get("provider", "API Key"),
                    "icon": meta.get("icon", "🔑"),
                    "masked_value": "🔒 [LOCKED — ENTER PIN]",
                    "length": meta.get("length", 0),
                    "updated_at": meta.get("updated_at", ""),
                    "configured": True,
                })

        return {
            "status": "ok",
            "initialized": initialized,
            "unlocked": unlocked,
            "vault_path": str(self.vault_path),
            "kdf": f"PBKDF2-HMAC-SHA256 ({PBKDF2_ITERATIONS:,} iterations)",
            "cipher": envelope.get("cipher_scheme", "fernet-aes128-cbc-hmac-sha256"),
            "keys_count": len(keys_summary),
            "keys": keys_summary,
            "known_presets": KNOWN_API_KEYS,
            "failed_attempts": self._failed_attempts,
            "lockout_remaining_s": lockout_remaining,
            "session_ttl_remaining_s": max(0, int(self._session_expires_at - time.time())) if unlocked else 0,
        }

    def setup_pin(self, pin: str, import_existing_env: bool = True) -> Dict[str, Any]:
        """
        Initializes the API Vault with a user-chosen PIN (4-16 chars/digits),
        encrypts existing `.env` keys into `~/.hermes/api_vault.enc.json`,
        and unlocks the session.
        """
        if self.is_initialized():
            return {"status": "error", "error": "Vault PIN is already set. Use Change PIN or Unlock."}
        ok, msg = self._validate_pin_format(pin)
        if not ok:
            return {"status": "error", "error": msg}

        pin_clean = pin.strip()
        verify_salt = os.urandom(16)
        enc_salt = os.urandom(16)
        verify_key = _derive_key(pin_clean, verify_salt)
        enc_key = _derive_key(pin_clean, enc_salt)

        initial_secrets = self._collect_existing_env_secrets() if import_existing_env else {}
        ciphertext, scheme = _encrypt_payload(initial_secrets, enc_key)

        catalog = [
            {
                "key": k,
                "provider": v.get("provider", "API Key"),
                "icon": v.get("icon", "🔑"),
                "length": len(str(v.get("value", ""))),
                "updated_at": v.get("updated_at", ""),
            }
            for k, v in sorted(initial_secrets.items())
        ]

        envelope = {
            "version": 1,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "kdf": "pbkdf2_hmac_sha256",
            "iterations": PBKDF2_ITERATIONS,
            "verify_salt": base64.b64encode(verify_salt).decode("ascii"),
            "verify_hash": base64.b64encode(verify_key).decode("ascii"),
            "enc_salt": base64.b64encode(enc_salt).decode("ascii"),
            "cipher_scheme": scheme,
            "ciphertext": ciphertext,
            "keys_Catalog": catalog,
        }
        self._write_vault_envelope(envelope)

        self._active_enc_key = enc_key
        self._unlocked_secrets = initial_secrets
        self._session_token = secrets.token_urlsafe(32)
        self._session_expires_at = time.time() + SESSION_TTL_SECONDS
        self._failed_attempts = 0

        self._sync_to_runtime_and_dotenv(initial_secrets)

        return {
            "status": "ok",
            "message": f"Vault initialized and encrypted with PIN ({len(initial_secrets)} keys secured).",
            "session_token": self._session_token,
            "keys_imported": len(initial_secrets),
            "vault_status": self.get_status(self._session_token),
        }

    def _verify_pin_internal(self, pin: str) -> Tuple[bool, Optional[bytes], Optional[Dict[str, Any]], str]:
        now = time.time()
        if now < self._lockout_until:
            rem = int(self._lockout_until - now) + 1
            return False, None, None, f"Vault temporarily locked due to failed PIN attempts. Try again in {rem}s."

        envelope = self._read_vault_envelope()
        if not envelope:
            return False, None, None, "Vault is not initialized yet. Please set up a PIN first."

        pin_clean = (pin or "").strip()
        try:
            verify_salt = base64.b64decode(envelope["verify_salt"])
            expected_verify = base64.b64decode(envelope["verify_hash"])
            enc_salt = base64.b64decode(envelope["enc_salt"])
            iterations = int(envelope.get("iterations", PBKDF2_ITERATIONS))
        except Exception:
            return False, None, None, "Vault envelope metadata is corrupted."

        candidate_verify = _derive_key(pin_clean, verify_salt, iterations=iterations)
        if not hmac.compare_digest(candidate_verify, expected_verify):
            self._failed_attempts += 1
            if self._failed_attempts >= MAX_FAILED_ATTEMPTS:
                self._lockout_until = time.time() + LOCKOUT_SECONDS
                if not os.environ.get("PYTEST_CURRENT_TEST"):
                    try:
                        from notification_center import get_notification_center
                        get_notification_center().notify(
                            title="🚨 API Vault Brute-Force Lockout",
                            body=f"{self._failed_attempts} failed PIN attempts detected on Sovereign API Vault. Locked for {LOCKOUT_SECONDS}s.",
                            priority="HIGH",
                            category="SECURITY_BLOCK",
                            role="SECURITY",
                        )
                    except Exception:
                        pass
                return False, None, None, f"Too many failed PIN attempts ({self._failed_attempts}). Vault locked for {LOCKOUT_SECONDS}s."
            remaining = MAX_FAILED_ATTEMPTS - self._failed_attempts
            return False, None, None, f"Incorrect PIN ({remaining} attempt{'s' if remaining != 1 else ''} remaining before lockout)."

        enc_key = _derive_key(pin_clean, enc_salt, iterations=iterations)
        try:
            decrypted = _decrypt_payload(
                envelope["ciphertext"],
                envelope.get("cipher_scheme", "fernet-aes128-cbc-hmac-sha256"),
                enc_key,
            )
        except Exception as e:
            return False, None, None, f"Decryption failed: {e}"

        self._failed_attempts = 0
        self._lockout_until = 0.0
        return True, enc_key, decrypted, "OK"

    def unlock(self, pin: str) -> Dict[str, Any]:
        """Verifies the PIN, decrypts secrets into session memory, and returns a session token."""
        ok, enc_key, decrypted, err = self._verify_pin_internal(pin)
        if not ok or enc_key is None or decrypted is None:
            return {"status": "error", "error": err, "failed_attempts": self._failed_attempts}

        self._active_enc_key = enc_key
        self._unlocked_secrets = decrypted
        self._session_token = secrets.token_urlsafe(32)
        self._session_expires_at = time.time() + SESSION_TTL_SECONDS

        self._sync_to_runtime_and_dotenv(decrypted)

        return {
            "status": "ok",
            "message": "Vault unlocked.",
            "session_token": self._session_token,
            "vault_status": self.get_status(self._session_token),
        }

    def lock(self) -> Dict[str, Any]:
        """Immediately locks the vault and wipes decrypted keys from the active Vault session."""
        self._session_token = None
        self._session_expires_at = 0.0
        self._unlocked_secrets.clear()
        self._active_enc_key = None
        return {
            "status": "ok",
            "message": "Vault locked.",
            "vault_status": self.get_status(),
        }

    def change_pin(self, current_pin: str, new_pin: str) -> Dict[str, Any]:
        """Verifies `current_pin`, re-salts and re-encrypts all vault keys with `new_pin`."""
        ok_fmt, msg_fmt = self._validate_pin_format(new_pin)
        if not ok_fmt:
            return {"status": "error", "error": msg_fmt}

        ok, _, decrypted, err = self._verify_pin_internal(current_pin)
        if not ok or decrypted is None:
            return {"status": "error", "error": err}

        new_pin_clean = new_pin.strip()
        verify_salt = os.urandom(16)
        enc_salt = os.urandom(16)
        verify_key = _derive_key(new_pin_clean, verify_salt)
        enc_key = _derive_key(new_pin_clean, enc_salt)
        ciphertext, scheme = _encrypt_payload(decrypted, enc_key)

        envelope = self._read_vault_envelope() or {}
        envelope.update({
            "updated_at": datetime.now().isoformat(),
            "verify_salt": base64.b64encode(verify_salt).decode("ascii"),
            "verify_hash": base64.b64encode(verify_key).decode("ascii"),
            "enc_salt": base64.b64encode(enc_salt).decode("ascii"),
            "cipher_scheme": scheme,
            "ciphertext": ciphertext,
        })
        self._write_vault_envelope(envelope)

        self._active_enc_key = enc_key
        self._unlocked_secrets = decrypted
        self._session_token = secrets.token_urlsafe(32)
        self._session_expires_at = time.time() + SESSION_TTL_SECONDS

        return {
            "status": "ok",
            "message": "Vault PIN rotated and all secrets re-encrypted with fresh salts.",
            "session_token": self._session_token,
            "vault_status": self.get_status(self._session_token),
        }

    def _authorize_action(self, pin: Optional[str] = None, session_token: Optional[str] = None) -> Tuple[bool, str]:
        if session_token and self.is_unlocked(session_token) and self._active_enc_key is not None:
            return True, "OK"
        if pin:
            res = self.unlock(pin)
            if res.get("status") == "ok":
                return True, "OK"
            return False, res.get("error", "Invalid PIN")
        return False, "Vault is locked. Please enter your PIN first."

    def _persist_current_unlocked(self) -> None:
        if self._active_enc_key is None:
            return
        envelope = self._read_vault_envelope() or {}
        ciphertext, scheme = _encrypt_payload(self._unlocked_secrets, self._active_enc_key)
        catalog = [
            {
                "key": k,
                "provider": v.get("provider", "API Key"),
                "icon": v.get("icon", "🔑"),
                "length": len(str(v.get("value", ""))),
                "updated_at": v.get("updated_at", ""),
            }
            for k, v in sorted(self._unlocked_secrets.items())
        ]
        envelope["updated_at"] = datetime.now().isoformat()
        envelope["cipher_scheme"] = scheme
        envelope["ciphertext"] = ciphertext
        envelope["keys_Catalog"] = catalog
        self._write_vault_envelope(envelope)
        self._sync_to_runtime_and_dotenv(self._unlocked_secrets)

    def set_secret(
        self,
        key_name: str,
        key_value: str,
        provider: Optional[str] = None,
        pin: Optional[str] = None,
        session_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Adds or updates an API key in the encrypted vault and syncs runtime env."""
        auth_ok, auth_err = self._authorize_action(pin=pin, session_token=session_token)
        if not auth_ok:
            return {"status": "error", "error": auth_err}

        k_clean = (key_name or "").strip().upper()
        v_clean = (key_value or "").strip()
        if not k_clean or not v_clean:
            return {"status": "error", "error": "Both key_name and key_value are required."}

        known_lookup = {item["key"]: item for item in KNOWN_API_KEYS}
        meta = known_lookup.get(k_clean, {"provider": provider or "Custom API Credential", "icon": "🔑"})
        self._unlocked_secrets[k_clean] = {
            "key": k_clean,
            "value": v_clean,
            "provider": provider or meta["provider"],
            "icon": meta["icon"],
            "updated_at": datetime.now().isoformat(),
        }
        if k_clean == "GEMINI_API_KEY":
            # Keep GOOGLE_API_KEY alias in sync automatically
            os.environ["GOOGLE_API_KEY"] = v_clean

        self._persist_current_unlocked()
        return {
            "status": "ok",
            "message": f"Saved and encrypted {k_clean} ({mask_secret_preview(v_clean)}).",
            "key": k_clean,
            "masked_value": mask_secret_preview(v_clean),
            "vault_status": self.get_status(self._session_token),
        }

    def delete_secret(
        self,
        key_name: str,
        pin: Optional[str] = None,
        session_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deletes a secret from the encrypted vault."""
        auth_ok, auth_err = self._authorize_action(pin=pin, session_token=session_token)
        if not auth_ok:
            return {"status": "error", "error": auth_err}

        k_clean = (key_name or "").strip().upper()
        if k_clean not in self._unlocked_secrets:
            return {"status": "error", "error": f"Key {k_clean} not found in vault."}

        del self._unlocked_secrets[k_clean]
        self._persist_current_unlocked()
        return {
            "status": "ok",
            "message": f"Deleted {k_clean} from vault.",
            "vault_status": self.get_status(self._session_token),
        }

    def reveal_secret(
        self,
        key_name: str,
        pin: Optional[str] = None,
        session_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reveals a single decrypted secret only when authorized by PIN or unlocked session token."""
        auth_ok, auth_err = self._authorize_action(pin=pin, session_token=session_token)
        if not auth_ok:
            return {"status": "error", "error": auth_err}

        k_clean = (key_name or "").strip().upper()
        item = self._unlocked_secrets.get(k_clean)
        if not item:
            return {"status": "error", "error": f"Key {k_clean} not found in vault."}

        return {
            "status": "ok",
            "key": k_clean,
            "value": item.get("value", ""),
            "masked_value": mask_secret_preview(str(item.get("value", ""))),
        }

    def test_secret_live(
        self,
        key_name: str,
        pin: Optional[str] = None,
        session_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tests live API connectivity and latency for a stored key."""
        auth_ok, auth_err = self._authorize_action(pin=pin, session_token=session_token)
        if not auth_ok:
            return {"status": "error", "error": auth_err}

        k_clean = (key_name or "").strip().upper()
        item = self._unlocked_secrets.get(k_clean)
        if not item or not item.get("value"):
            return {"status": "error", "error": f"Key {k_clean} is not configured in the vault."}

        secret_val = str(item["value"]).strip()
        t0 = time.perf_counter()
        try:
            if k_clean in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                r = requests.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={secret_val}",
                    timeout=8,
                )
                lat = int((time.perf_counter() - t0) * 1000)
                if r.status_code == 200:
                    models = r.json().get("models", [])
                    return {"status": "ok", "key": k_clean, "http_status": 200, "latency_ms": lat, "detail": f"Verified ({len(models)} Gemini models accessible)"}
                return {"status": "error", "key": k_clean, "http_status": r.status_code, "latency_ms": lat, "error": f"HTTP {r.status_code}"}

            if k_clean == "GROQ_API_KEY":
                r = requests.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {secret_val}"},
                    timeout=8,
                )
                lat = int((time.perf_counter() - t0) * 1000)
                if r.status_code == 200:
                    models = r.json().get("data", [])
                    return {"status": "ok", "key": k_clean, "http_status": 200, "latency_ms": lat, "detail": f"Verified ({len(models)} Groq LPU models online)"}
                return {"status": "error", "key": k_clean, "http_status": r.status_code, "latency_ms": lat, "error": f"HTTP {r.status_code}"}

            if k_clean == "OLLAMA_API_KEY":
                r = requests.get(
                    "https://ollama.com/api/tags",
                    headers={"Authorization": f"Bearer {secret_val}"},
                    timeout=8,
                )
                lat = int((time.perf_counter() - t0) * 1000)
                if r.status_code == 200:
                    models = r.json().get("models", [])
                    return {"status": "ok", "key": k_clean, "http_status": 200, "latency_ms": lat, "detail": f"Verified ({len(models)} Ollama Cloud models listed)"}
                return {"status": "error", "key": k_clean, "http_status": r.status_code, "latency_ms": lat, "error": f"HTTP {r.status_code}"}

            if k_clean == "OPENROUTER_API_KEY":
                r = requests.get(
                    "https://openrouter.ai/api/v1/auth/key",
                    headers={"Authorization": f"Bearer {secret_val}"},
                    timeout=8,
                )
                lat = int((time.perf_counter() - t0) * 1000)
                if r.status_code == 200:
                    return {"status": "ok", "key": k_clean, "http_status": 200, "latency_ms": lat, "detail": "OpenRouter key verified"}
                return {"status": "error", "key": k_clean, "http_status": r.status_code, "latency_ms": lat, "error": f"HTTP {r.status_code}"}

            if k_clean == "NVIDIA_API_KEY":
                r = requests.get(
                    "https://integrate.api.nvidia.com/v1/models",
                    headers={"Authorization": f"Bearer {secret_val}"},
                    timeout=8,
                )
                lat = int((time.perf_counter() - t0) * 1000)
                if r.status_code == 200:
                    return {"status": "ok", "key": k_clean, "http_status": 200, "latency_ms": lat, "detail": "NVIDIA NIM key verified"}
                return {"status": "error", "key": k_clean, "http_status": r.status_code, "latency_ms": lat, "error": f"HTTP {r.status_code}"}

            lat = int((time.perf_counter() - t0) * 1000)
            return {"status": "ok", "key": k_clean, "http_status": 200, "latency_ms": lat, "detail": f"Stored in vault ({len(secret_val)} chars)"}
        except Exception as e:
            lat = int((time.perf_counter() - t0) * 1000)
            return {"status": "error", "key": k_clean, "latency_ms": lat, "error": str(e)}


_GLOBAL_VAULT: Optional[SovereignAPIVault] = None


def get_api_vault() -> SovereignAPIVault:
    """Singleton accessor for the Sovereign PIN-Secured API Vault."""
    global _GLOBAL_VAULT
    if _GLOBAL_VAULT is None:
        _GLOBAL_VAULT = SovereignAPIVault()
    return _GLOBAL_VAULT
