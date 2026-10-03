# -*- coding: utf-8 -*-
"""
PII & Secret Redaction Shield for Hermes Agent
Masks Personally Identifiable Information (PII) and secret credentials
before prompts are sent to cloud LLMs or stored in durable employee logs.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


class PIIShield:
    """Masks sensitive PII patterns and secrets in text."""

    PATTERNS: Dict[str, str] = {
        "CREDIT_CARD": r"\b(?:\d[ -]*?){13,19}\b",
        "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
        "BANK_ACCOUNT": r"\b(?:bank\s+account|account|acct|a/c)\s*(?:number|no\.?|#)?\s*[:=]?\s*\d{6,17}\b",
        "ROUTING_NUMBER": r"\b(?:routing|aba)\s*(?:number|no\.?|#)?\s*[:=]?\s*\d{9}\b",
        "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "PHONE": r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b",
        "IP_ADDRESS": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "DATE_OF_BIRTH": r"\b(?:dob|date\s+of\s+birth|birthdate|born)\s*[:=]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "GROQ_KEY": r"\bgsk_[A-Za-z0-9]{20,}\b",
        "GOOGLE_KEY": r"\bAIza[A-Za-z0-9_-]{30,}\b",
        "OPENAI_KEY": r"\bsk-[A-Za-z0-9_-]{20,}\b",
        "NVIDIA_KEY": r"\bnvapi-[A-Za-z0-9_-]{20,}\b",
        "GITHUB_TOKEN": r"\bgh[pousr]_[A-Za-z0-9]{20,}\b",
        "SLACK_TOKEN": r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b",
        "GENERIC_SECRET": r"\b([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASS|CREDENTIAL)[A-Z0-9_]*)\s*[:=]\s*([^\s,;]+)",
    }

    @classmethod
    def mask(cls, text: str) -> str:
        """Redacts all known PII and credentials from the input text."""
        if not text:
            return ""

        masked = str(text)
        for label, pattern in cls.PATTERNS.items():
            if label == "GENERIC_SECRET":
                masked = re.sub(pattern, r"\1=[REDACTED_SECRET]", masked, flags=re.IGNORECASE)
            else:
                masked = re.sub(pattern, f"[{label}]", masked, flags=re.IGNORECASE)

        return masked

    @classmethod
    def detect_entities(cls, text: str) -> List[Dict[str, Any]]:
        """Detects and returns all sensitive entities found in the text."""
        if not text:
            return []

        findings: List[Dict[str, Any]] = []
        for label, pattern in cls.PATTERNS.items():
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                findings.append({
                    "type": label,
                    "span": [match.start(), match.end()],
                    "preview": f"[{label}]"
                })
        return findings

    @classmethod
    def has_sensitive_data(cls, text: str) -> bool:
        """Returns True if any PII or secret is detected in the text."""
        return cls.mask(text) != text


_shield_instance = PIIShield()


def mask_sensitive_text(text: str) -> str:
    """Global helper to mask sensitive text."""
    return _shield_instance.mask(text)


def has_sensitive_data(text: str) -> bool:
    """Global helper to check if text contains sensitive data."""
    return _shield_instance.has_sensitive_data(text)
