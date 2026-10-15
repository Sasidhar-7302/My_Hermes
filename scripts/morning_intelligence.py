"""Deterministic Morning Intelligence runner.

Search and source gating are deterministic.  The configured local Ollama model
is used only to compress already-opened evidence into a concise story object.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_candidates import (
    DEVELOPMENT_GENERIC_TERMS,
    EDITORIAL_CATEGORIES,
    TARGET_PER_CATEGORY,
    canonical_candidate_url,
    category_relevant,
    collect_candidates,
    direct_candidate,
    find_corroboration,
    registrable_domain,
    title_terms,
)
from runtime_clock import runtime_timezone

from hermes_cli.config import load_config
from hermes_cli.plugins import discover_plugins
from tools.web_tools import web_extract_tool


TIMEZONE = runtime_timezone()
MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)
PUBLISHED_RE = re.compile(
    rf"({MONTHS})\s+(\d{{1,2}}),\s+(20\d{{2}}),?\s+"
    r"(?:at\s+)?(\d{1,2}):(\d{2})\s*(AM|PM)\s*(UTC|GMT|ET|EDT|EST|PT|PDT|PST)",
    re.IGNORECASE,
)
ISO_PUBLISHED_RE = re.compile(
    r"\b(20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?"
    r"(?:Z|[+-]\d{2}:?\d{2}))\b"
)
NUMERIC_PUBLISHED_RE = re.compile(
    r"\b(20\d{2}-\d{2}-\d{2})[ T](\d{1,2}):(\d{2})(?::\d{2})?\s*"
    r"(UTC|GMT|ET|EDT|EST|PT|PDT|PST)\b",
    re.IGNORECASE,
)
HTML_PUBLISHED_PATTERNS = (
    re.compile(
        r'["\']datePublished["\']\s*:\s*["\']([^"\']+)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+(?:property|name)=["\']article:published_time["\'][^>]+'
        r'content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+'
        r'(?:property|name)=["\']article:published_time["\']',
        re.IGNORECASE,
    ),
    re.compile(r'<time[^>]+datetime=["\']([^"\']+)["\']', re.IGNORECASE),
)
ENTITY_TYPES = {
    "company",
    "person",
    "product",
    "organization",
    "government",
    "market",
    "technology",
    "place",
}
MAX_TOTAL_STORIES = 20
MIN_TOTAL_STORIES = 15
MAX_TELEGRAM_MESSAGES = 5
MAX_VERIFIED_POOL = 30
READER_SECTIONS = (
    (
        "AI, software and security",
        ("AI and software", "Cybersecurity and digital risk"),
    ),
    (
        "Business, careers and startups",
        (
            "Markets and business",
            "Career and self-development",
            "Startups and product strategy",
        ),
    ),
    (
        "Policy and world",
        ("AI policy and regulation", "Geopolitics"),
    ),
    (
        "Science, inventions and health",
        ("Science and inventions", "Health and wellbeing"),
    ),
    (
        "Space, agriculture, climate and energy",
        ("Space and rockets", "Agriculture technology", "Climate and energy"),
    ),
)
MAX_STORIES_PER_READER_SECTION = 5
PRIMARY_SOURCE_KINDS = {
    "openai.com": "company",
    "anthropic.com": "company",
    "huggingface.co": "company",
    "microsoft.com": "company",
    "googleblog.com": "company",
    "blog.google": "company",
    "deepmind.google": "company",
    "meta.com": "company",
    "nvidia.com": "company",
    "ibm.com": "company",
    "amazon.com": "company",
    "github.blog": "company",
    "coursera.org": "company",
    "whitehouse.gov": "government",
    "bls.gov": "government",
    "sec.gov": "regulator",
    "federalreserve.gov": "regulator",
    "europa.eu": "government",
    "consilium.europa.eu": "government",
    "eur-lex.europa.eu": "government",
    "un.org": "government",
    "oecd.org": "research",
    "mit.edu": "research",
    "stanford.edu": "research",
    "cisa.gov": "government",
    "nasa.gov": "government",
    "esa.int": "government",
    "nsf.gov": "research",
    "usda.gov": "research",
    "fao.org": "government",
    "energy.gov": "government",
    "noaa.gov": "government",
    "usgs.gov": "research",
    "cloudflare.com": "company",
    "fb.com": "company",
}


def parse_published(text: str) -> datetime | None:
    iso_match = ISO_PUBLISHED_RE.search(text)
    if iso_match:
        try:
            return datetime.fromisoformat(
                iso_match.group(1).replace("Z", "+00:00")
            )
        except ValueError:
            pass
    match = PUBLISHED_RE.search(text)
    if match:
        month, day, year, hour, minute, meridiem, zone = match.groups()
        raw = f"{month} {day} {year} {hour}:{minute} {meridiem}"
        if month.casefold() == "sept":
            raw = f"Sep {day} {year} {hour}:{minute} {meridiem}"
        parsed = None
        for month_format in ("%B", "%b"):
            try:
                parsed = datetime.strptime(
                    raw,
                    f"{month_format} %d %Y %I:%M %p",
                )
                break
            except ValueError:
                continue
        if parsed is None:
            return None
        zone_upper = zone.upper()
        if zone_upper in {"UTC", "GMT"}:
            return parsed.replace(tzinfo=ZoneInfo("UTC"))
        if zone_upper in {"PT", "PDT", "PST"}:
            return parsed.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
        return parsed.replace(tzinfo=ZoneInfo("America/New_York"))
    numeric_match = NUMERIC_PUBLISHED_RE.search(text)
    if not numeric_match:
        return None
    day, hour, minute, zone = numeric_match.groups()
    parsed = datetime.strptime(f"{day} {hour}:{minute}", "%Y-%m-%d %H:%M")
    zone_upper = zone.upper()
    if zone_upper in {"UTC", "GMT"}:
        return parsed.replace(tzinfo=ZoneInfo("UTC"))
    if zone_upper in {"PT", "PDT", "PST"}:
        return parsed.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
    return parsed.replace(tzinfo=ZoneInfo("America/New_York"))


def parse_html_published(html: str) -> datetime | None:
    for pattern in HTML_PUBLISHED_PATTERNS:
        for match in pattern.finditer(html):
            value = match.group(1).strip()
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                parsed = parse_published(value)
            if parsed is not None and parsed.tzinfo is not None:
                return parsed
    return None


def fetch_publication_time(url: str) -> datetime | None:
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 HermesMorningIntelligence/1.1"},
            timeout=30,
        )
        response.raise_for_status()
        return (
            parse_html_published(response.text)
            or parse_published(response.text)
            or parse_url_publication_date(url)
        )
    except Exception:
        return parse_url_publication_date(url)


def parse_url_publication_date(url: str) -> datetime | None:
    """Parse publisher date paths as date-precision metadata."""
    path = urlsplit(url).path
    patterns = (
        (r"/(20\d{2})/(\d{2})/(\d{2})(?:/|$)", (1, 2, 3)),
        (r"/(\d{2})/(\d{2})/(20\d{2})(?:/|$)", (3, 1, 2)),
        (r"(?:blog|news)(20\d{4})", (1,)),
    )
    for pattern, order in patterns:
        match = re.search(pattern, path)
        if not match:
            continue
        try:
            if len(order) == 1:
                compact = match.group(order[0])
                parsed = datetime.strptime(compact, "%Y%m%d")
            else:
                parsed = datetime(
                    int(match.group(order[0])),
                    int(match.group(order[1])),
                    int(match.group(order[2])),
                )
            return parsed.replace(tzinfo=TIMEZONE)
        except ValueError:
            continue
    mit_match = re.search(r"/(20\d{2})/[^/?#]+-(\d{2})(\d{2})(?:/|$)", path)
    if mit_match:
        try:
            return datetime(
                int(mit_match.group(1)),
                int(mit_match.group(2)),
                int(mit_match.group(3)),
                tzinfo=TIMEZONE,
            )
        except ValueError:
            pass
    return None


def fetch_direct_article(url: str) -> tuple[str, datetime | None]:
    """Best-effort direct extraction for pages the configured provider omits."""
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
                )
            },
            timeout=30,
        )
        response.raise_for_status()
    except Exception:
        return "", None
    raw = response.text
    paragraphs = []
    for match in re.findall(r"<p\b[^>]*>(.*?)</p>", raw, flags=re.IGNORECASE | re.DOTALL):
        text = html.unescape(re.sub(r"<[^>]+>", " ", match))
        text = re.sub(r"\s+", " ", text).strip()
        if 35 <= len(text) <= 2000:
            paragraphs.append(text)
    return "\n".join(paragraphs)[:16000], parse_html_published(raw)


def extract_article(url: str) -> tuple[str, datetime | None, str]:
    """Open one article through the configured provider, then direct HTTP."""
    provider_error = ""
    try:
        payload = json.loads(
            asyncio.run(web_extract_tool([url], "markdown", char_limit=14000))
        )
        results = payload.get("results", [])
        if results:
            item = results[0]
            provider_error = str(item.get("error") or "")
            content = str(item.get("content") or "")
            if not provider_error and len(clean_markdown(content)) >= 500:
                metadata = item.get("metadata") or {}
                published = parse_published(
                    str(
                        item.get("published_at")
                        or metadata.get("published_at")
                        or ""
                    )
                )
                return content, published or parse_published(content), ""
    except Exception as exc:
        provider_error = str(exc)
    content, published = fetch_direct_article(url)
    if len(clean_markdown(content)) >= 500:
        return content, published, ""
    return "", published, provider_error or "article content was unavailable"


def clean_markdown(value: str) -> str:
    value = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"[#*_`>|]", " ", value)
    value = re.sub(r"^\s*[-•]\s+", "", value)
    return re.sub(r"\s+", " ", value).strip()


def clip(value: str, limit: int) -> str:
    value = clean_markdown(value)
    if len(value) <= limit:
        return value
    window = value[: limit + 1]
    stops = [match.end() for match in re.finditer(r"[.!?](?=\s|$)", window)]
    if stops and stops[-1] >= max(45, int(limit * 0.55)):
        return window[: stops[-1]].strip()
    shortened = value[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return shortened.rstrip(".") + "."


def concise_sentence(value: str, limit: int) -> str:
    """Return one complete, bounded sentence without splitting abbreviations."""
    cleaned = clean_markdown(value)
    protected = cleaned.replace("U.S.", "U<dot>S<dot>").replace(
        "U.K.", "U<dot>K<dot>"
    )
    protected = re.sub(
        r"\b(Inc|Co|Corp)\.(?=\s+[a-z])",
        r"\1<dot>",
        protected,
    )
    parts = re.split(r"(?<=[.!?])\s+", protected)
    for part in parts:
        restored = part.replace("<dot>", ".").strip()
        if len(restored) >= 25 and restored.endswith((".", "!", "?")):
            return clip(restored, limit)
    return clip(cleaned, limit)


def ends_in_fragment(value: str) -> bool:
    words = re.findall(r"[A-Za-z]+", value.casefold())
    return bool(words) and words[-1] in {
        "a", "an", "and", "as", "at", "by", "for", "from", "in", "of",
        "on", "or", "the", "to", "with",
    }


def clean_headline(value: str) -> str:
    value = re.sub(
        r"\s*(?:\||[-–—])\s*(?:Reuters|TechCrunch|The Verge|Fortune|Bloomberg|"
        r"CNBC|Axios|Semafor|Financial Times)\s*$",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\s+Shaping Europe(?:'|’|’)s digital future\s*$",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\s+(?:and\s+)?(?:\.\.\.|…)\s*$", "", value)
    return clean_markdown(value)


def sentence_candidates(
    content: str,
    headline: str = "",
    *,
    minimum_overlap: int = 2,
) -> list[str]:
    """Return complete article-like sentences, excluding headings and chrome."""
    headline_terms = title_terms(headline)
    sentences = []
    blocks = [clean_markdown(line) for line in content.splitlines()]
    if len(blocks) <= 1:
        blocks = [clean_markdown(content)]
    for block in blocks:
        protected = block.replace(" U.S.", " U<dot>S<dot>").replace(
            " U.K.", " U<dot>K<dot>"
        )
        protected = re.sub(
            r"\b(Inc|Co|Corp)\.(?=\s+[a-z])",
            r"\1<dot>",
            protected,
        )
        for raw in re.split(r"(?<=[.!?])\s+", protected):
            value = raw.replace("<dot>", ".").strip()
            terms = title_terms(value)
            if not 45 <= len(value) <= 650:
                continue
            if not value.endswith((".", "!", "?")):
                continue
            if headline_terms and len(terms & headline_terms) < minimum_overlap:
                continue
            lowered = value.casefold()
            if any(
                marker in lowered
                for marker in (
                    "sign up for",
                    "all rights reserved",
                    "contact us",
                    "cookie",
                    "gift this article",
                    "advertisement",
                    "privacy policy",
                    "skip to main content",
                    "add axios on google",
                    "consent powered by",
                    "this artist's concept",
                    "this artist’s concept",
                    "reflection visible",
                    "works inside the international space station",
                )
            ):
                continue
            if title_similarity(value, headline) >= 0.82:
                continue
            sentences.append(value)
    return list(dict.fromkeys(sentences))


def title_similarity(left: str, right: str) -> float:
    left_terms, right_terms = title_terms(left), title_terms(right)
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms | right_terms)


def evidence_excerpt(content: str, headline: str) -> str:
    sentences = sentence_candidates(content, headline)
    return clip(sentences[0], 250) if sentences else ""


def article_slice(content: str, headline: str) -> str:
    sentences = sentence_candidates(content, headline, minimum_overlap=1)
    return " ".join(sentences[:12])[:5000]


def category_relevance(category: str, headline: str = "") -> str:
    terms = title_terms(headline)
    if category == "AI and software":
        if terms & {"agent", "agents", "coding", "developer", "developers"}:
            return (
                "Compare this with the coding and agent workflows you are "
                "building and the skills they now require."
            )
        if terms & {"chip", "chips", "semiconductor", "gpu", "infrastructure"}:
            return (
                "Use this to update assumptions about AI performance, hardware "
                "availability, and infrastructure cost."
            )
    if category == "Markets and business" and terms & {
        "funding", "raises", "acquisition", "ipo", "valuation",
    }:
        return (
            "Use this as a benchmark for startup financing, market appetite, "
            "and how technology companies are valued."
        )
    if category == "Career and self-development" and terms & {
        "hiring", "jobs", "skills", "training", "learning",
    }:
        return (
            "Use this signal to prioritize the technical and leadership skills "
            "that employers are rewarding."
        )
    if category == "Geopolitics":
        if terms & {"chip", "chips", "semiconductor", "tariff", "tariffs", "trade"}:
            return (
                "Track this for effects on chip supply, technology access, "
                "pricing, and cross-border product strategy."
            )
        if terms & {"iran", "oil", "energy", "missile", "war"}:
            return (
                "Track this for near-term effects on energy prices, currencies, "
                "supply chains, and business risk."
            )
    if category == "Space and rockets" and terms & {
        "rocket", "rockets", "launch", "launches", "propulsion", "spacecraft",
    }:
        return (
            "Track this for advances in launch cost, propulsion, spacecraft "
            "capability, and commercial space infrastructure."
        )
    if category == "Agriculture technology":
        if terms & {"ai", "robot", "robots", "robotics", "sensor", "sensors", "drone", "drones"}:
            return (
                "Study this as a practical example of AI, robotics, or sensing "
                "creating measurable value outside software."
            )
        return (
            "Track this for technologies improving farm productivity, resource "
            "use, food supply, and climate resilience."
        )
    if category == "Science and inventions":
        return (
            "Use this to spot emerging capabilities worth learning, testing, "
            "or applying before they become mainstream."
        )
    return concise_sentence(
        {
            "AI and software": (
                "Use this to reassess the AI tools, architecture choices, and "
                "competitive assumptions behind products you build."
            ),
            "Markets and business": (
                "Use this as context for customer budgets, funding conditions, "
                "and the business environment around technology projects."
            ),
            "AI policy and regulation": (
                "Track this for changes to compliance, data, or product-design "
                "requirements affecting AI systems."
            ),
            "Geopolitics": (
                "Track this for possible effects on energy, chip supply, currencies, "
                "and technology-business operations."
            ),
            "Career and self-development": (
                "Use this signal to choose which technical, leadership, or working "
                "skills to practice next."
            ),
            "Cybersecurity and digital risk": (
                "Use this to reduce security exposure in your software, accounts, "
                "data, and AI-agent workflows."
            ),
            "Science and inventions": (
                "Track this for discoveries and inventions that could change what "
                "you can build, study, or apply next."
            ),
            "Agriculture technology": (
                "Track this for practical uses of AI, robotics, sensors, and biology "
                "in food production and resilient farming."
            ),
            "Space and rockets": (
                "Track this for launch, satellite, and aerospace capabilities that "
                "may create new technical and commercial opportunities."
            ),
            "Startups and product strategy": (
                "Use this to reassess product positioning, customer demand, and "
                "how new technology businesses are being built."
            ),
            "Health and wellbeing": (
                "Use this to make better evidence-based choices about health, "
                "focus, resilience, and the technologies affecting care."
            ),
            "Climate and energy": (
                "Track this for effects on infrastructure, operating costs, "
                "technology demand, and long-term business conditions."
            ),
        }.get(
            category,
            "Use this development to update decisions about your active projects.",
        ),
        130,
    )


def model_settings() -> tuple[str, str]:
    config = load_config() or {}
    model_cfg = config.get("model") or {}
    if isinstance(model_cfg, str):
        return model_cfg, "http://127.0.0.1:11434/v1"
    return (
        str(model_cfg.get("default") or model_cfg.get("model") or "hermes-local:latest"),
        str(model_cfg.get("base_url") or "http://127.0.0.1:11434/v1").rstrip("/"),
    )


def summarize_with_ollama(
    candidate: dict,
    source_one: str,
    source_two: str,
) -> dict | None:
    model, base_url = model_settings()
    prompt = {
        "task": (
            "Return one JSON object only. Summarize this verified paired-source story "
            "for a personal morning intelligence brief. Explain practical relevance "
            "to an AI founder and software engineer, including career development, "
            "skills, judgment, or active projects when genuinely supported. Use only "
            "supplied evidence; no investment advice, speculation, military language, "
            "generic motivation, or markdown."
        ),
        "required_shape": {
            "headline": "factual headline under 140 characters",
            "summary": "one factual sentence under 220 characters",
            "why_it_matters": "one practical relevance sentence under 130 characters",
            "facts": ["one to three atomic supported claims"],
            "entities": [{"name": "entity", "type": "company|person|product|organization|government|market|technology|place"}],
            "topics": ["two to five short topics"],
        },
        "candidate": candidate,
        "source_one": source_one,
        "source_two": source_two,
    }
    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": "Bearer ollama"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a precise news editor. Output valid JSON only."},
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                "temperature": 0.1,
                "max_tokens": 700,
                "response_format": {"type": "json_object"},
            },
            timeout=35,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        start, end = content.find("{"), content.rfind("}")
        if start < 0 or end <= start:
            return None
        value = json.loads(content[start : end + 1])
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def fallback_summary(candidate: dict, evidence_override: str = "") -> dict:
    evidence = evidence_override or str(candidate.get("search_evidence") or "")
    sentences = sentence_candidates(
        evidence,
        candidate["title"],
        minimum_overlap=1,
    )
    eligible = [
        sentence
        for sentence in sentences
        if 55 <= len(clean_markdown(sentence)) <= 220
        if not ends_in_fragment(sentence)
        and "today's edition of" not in sentence.casefold()
        and "our weekday newsletter" not in sentence.casefold()
        and "isn't just about" not in sentence.casefold()
        and "is not just about" not in sentence.casefold()
        and "access proven architectures" not in sentence.casefold()
    ]
    action_terms = {
        "announced", "approved", "banned", "built", "developed", "found",
        "introduced", "launched", "published", "raised", "released",
        "reported", "selected", "signed", "tested", "unveiled",
    }
    eligible.sort(
        key=lambda sentence: (
            bool(title_terms(sentence) & action_terms),
            bool(re.search(r"\d", sentence)),
            len(title_terms(sentence) & title_terms(candidate["title"])),
            min(len(sentence), 180),
        ),
        reverse=True,
    )
    chosen = eligible[:1] or [
        sentence
        for sentence in sentences
        if not ends_in_fragment(sentence)
    ][:1]
    summary = concise_sentence(chosen[0], 220) if chosen else ""
    category = str(candidate.get("category") or "technology")
    names = []
    for value in re.findall(r"\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,2}", candidate["title"]):
        value = value.strip(" .-")
        value = re.sub(r"\s+AI$", "", value)
        if value == "Samsung Elec":
            value = "Samsung Electronics"
        if len(value) > 2 and value not in {"Reuters"} and value not in names:
            names.append(value)
    return {
        "headline": clean_headline(candidate["title"])[:140],
        "summary": summary,
        "why_it_matters": category_relevance(category, candidate["title"]),
        "facts": [clip(chosen[0], 280)] if chosen else [],
        "entities": [{"name": item, "type": "company"} for item in names[:5]]
        or [{"name": category, "type": "technology"}],
        "topics": [category, "AI and technology"],
    }


def normalize_summary(
    value: dict | None,
    candidate: dict,
    evidence_override: str = "",
) -> dict:
    fallback = fallback_summary(candidate, evidence_override)
    data = value or fallback
    headline = clip(str(data.get("headline") or fallback["headline"]), 140)
    raw_summary = clean_markdown(
        str(data.get("summary") or fallback["summary"])
    )
    summary = (
        fallback["summary"]
        if len(raw_summary) > 220
        else concise_sentence(raw_summary, 220)
    )
    raw_why = clean_markdown(
        str(data.get("why_it_matters") or fallback["why_it_matters"])
    )
    why = concise_sentence(raw_why, 130)
    if len(raw_why) > 130 or ends_in_fragment(why):
        why = fallback["why_it_matters"]
    facts = [
        clip(str(item), 280)
        for item in (data.get("facts") or fallback["facts"])
        if len(clean_markdown(str(item))) >= 8
    ][:3]
    entities = []
    for item in data.get("entities") or fallback["entities"]:
        if not isinstance(item, dict):
            continue
        name = clean_markdown(str(item.get("name") or ""))[:100]
        kind = str(item.get("type") or "organization").casefold()
        if len(name) >= 2:
            entities.append({"name": name, "type": kind if kind in ENTITY_TYPES else "organization"})
    topics = [
        clean_markdown(str(item))[:80]
        for item in (data.get("topics") or fallback["topics"])
        if len(clean_markdown(str(item))) >= 2
    ][:5]
    return {
        "headline": headline if len(headline) >= 8 else fallback["headline"],
        "summary": summary,
        "why_it_matters": why if len(why) >= 10 else fallback["why_it_matters"],
        "facts": facts,
        "entities": entities or fallback["entities"],
        "topics": topics or fallback["topics"],
    }


def summary_quality(summary: dict, candidate: dict) -> tuple[bool, str]:
    """Reject weak model/fallback text instead of sending it to Telegram."""
    text = clean_markdown(str(summary.get("summary") or ""))
    facts = [clean_markdown(str(item)) for item in summary.get("facts") or []]
    if len(text) < 55:
        return False, "summary is too short"
    if title_similarity(text, candidate["title"]) >= 0.72:
        return False, "summary substantially repeats the headline"
    headline_grounding = (
        title_terms(candidate["title"]) - DEVELOPMENT_GENERIC_TERMS
    )
    summary_grounding = title_terms(text) - DEVELOPMENT_GENERIC_TERMS
    if len(headline_grounding & summary_grounding) < 2:
        return False, "summary does not describe the headline's development"
    if text[-1:] != ".":
        return False, "summary does not contain a complete sentence"
    if ends_in_fragment(text):
        return False, "summary ends in a sentence fragment"
    if any(
        marker in text.casefold()
        for marker in (
            "today's edition of",
            "our weekday newsletter",
            "daily dose of what's going on",
            "sign up for our newsletter",
            "isn't just about",
            "is not just about",
            "access proven architectures",
            "this artist's concept",
            "this artist’s concept",
            "reflection visible",
            "all smiles in this",
            "photo taken shortly after",
        )
    ):
        return False, "summary is newsletter boilerplate rather than the development"
    if not facts:
        return False, "summary has no supported atomic claim"
    if not any(
        len(title_terms(text) & title_terms(value)) >= 2
        for value in facts
    ):
        return False, "summary is not grounded in its claims"
    return True, ""


def same_development(left: str, right: str) -> bool:
    """Detect different publishers covering the same underlying event."""
    def comparable(value: str) -> set[str]:
        return {
            term[:-1] if len(term) > 4 and term.endswith("s") else term
            for term in title_terms(value)
            if term not in DEVELOPMENT_GENERIC_TERMS
        }

    left_terms, right_terms = comparable(left), comparable(right)
    if not left_terms or not right_terms:
        return False
    common = len(left_terms & right_terms)
    overlap = common / min(len(left_terms), len(right_terms))
    return common >= 3 and overlap >= 0.33


def prior_story_relationship(
    headline: str,
    summary: str,
    prior_stories: list[dict],
) -> tuple[dict[str, str] | None, bool]:
    """Return an UPDATES edge or flag repeated coverage with no material change."""
    current = f"{headline} {summary}"
    current_terms = title_terms(current)
    current_numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", current))
    change_terms = {
        "approves", "approved", "rejects", "rejected", "launches", "launched",
        "releases", "released", "raises", "raised", "cuts", "cut", "expands",
        "expanded", "halts", "halted", "resumes", "resumed", "files", "filed",
        "wins", "won", "loses", "lost", "settles", "settled", "acquires",
        "acquired", "agrees", "agreed", "orders", "ordered", "delays", "delayed",
    }
    for prior in prior_stories:
        prior_headline = str(prior.get("headline") or "")
        if not same_development(headline, prior_headline):
            continue
        prior_text = f"{prior_headline} {prior.get('summary') or ''}"
        prior_terms = title_terms(prior_text)
        prior_numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", prior_text))
        has_new_state = bool((current_terms & change_terms) - prior_terms)
        has_new_number = bool(current_numbers - prior_numbers)
        relation_target = str(prior.get("story_id") or "")
        if relation_target and (has_new_state or has_new_number):
            return {"story_id": relation_target, "type": "updates"}, False
        return None, True
    return None, False


def interleave_candidates(candidates: list[dict]) -> list[dict]:
    """Round-robin categories so one abundant topic cannot consume the run."""
    grouped = {
        category: [
            item
            for item in candidates
            if str(item.get("category") or "") == category
        ]
        for category in EDITORIAL_CATEGORIES
    }
    output: list[dict] = []
    for index in range(max((len(items) for items in grouped.values()), default=0)):
        for category in EDITORIAL_CATEGORIES:
            if index < len(grouped[category]):
                output.append(grouped[category][index])
    return output


def select_briefing_stories(stories: list[dict]) -> list[dict]:
    """Choose up to 20 stories balanced across five reader-facing sections."""
    grouped = {
        category: [
            item
            for item in sorted(
                stories,
                key=lambda story: bool(story.get("_backfill")),
            )
            if item.get("category") == category
        ][:TARGET_PER_CATEGORY]
        for category in EDITORIAL_CATEGORIES
    }
    section_queues: list[list[dict]] = []
    for _section_name, categories in READER_SECTIONS:
        queue: list[dict] = []
        for index in range(TARGET_PER_CATEGORY):
            for category in categories:
                if index < len(grouped[category]):
                    queue.append(grouped[category][index])
        section_queues.append(queue[:MAX_STORIES_PER_READER_SECTION])

    selected: list[dict] = []
    for index in range(MAX_STORIES_PER_READER_SECTION):
        for queue in section_queues:
            if index < len(queue):
                selected.append(queue[index])
                if len(selected) >= MAX_TOTAL_STORIES:
                    return selected
    return selected


def corrected_category(category: str, headline: str, summary: str) -> str:
    """Correct obvious search-query category bleed before storage/rendering."""
    terms = title_terms(f"{headline} {summary}")
    geopolitical_actors = {
        "china", "iran", "russia", "ukraine", "israel", "gaza", "taiwan",
        "europe", "european", "india", "pakistan", "korea",
    }
    geopolitical_actions = {
        "ban", "bans", "banned", "import", "imports", "trade", "tariff",
        "tariffs", "sanction", "sanctions", "missile", "missiles", "attack",
        "attacks", "war", "conflict", "diplomatic", "diplomacy",
    }
    if terms & geopolitical_actors and terms & geopolitical_actions:
        return "Geopolitics"
    if terms & {
        "cybersecurity", "security", "breach", "malware", "ransomware", "vulnerability",
        "vulnerabilities", "exploit", "exploits", "cve",
    }:
        return "Cybersecurity and digital risk"
    if terms & {
        "agriculture", "agricultural", "agtech", "farm", "farms", "farmer",
        "farmers", "farming", "crop", "crops", "soil", "irrigation",
        "livestock", "harvest", "foodtech",
    }:
        return "Agriculture technology"
    if terms & {
        "space", "rocket", "rockets", "spacecraft", "satellite", "satellites",
        "orbit", "orbital", "lunar", "moon", "mars", "spacex", "artemis",
        "astronaut", "astronauts", "spacewalk", "spacewalks", "propulsion",
    }:
        return "Space and rockets"
    market_terms = {
        "stocks", "stock", "markets", "market", "selloff", "earnings",
        "ipo", "funding", "acquisition", "shares", "investors",
    }
    if terms & market_terms:
        return "Markets and business"
    if terms & {
        "health", "healthcare", "medical", "medicine", "disease", "treatment",
        "vaccine", "vaccines", "mental", "wellbeing", "cancer", "clinical",
        "drug", "drugs", "hospital", "patient", "patients",
    }:
        return "Health and wellbeing"
    if terms & {
        "scientist", "scientists", "discovery", "discoveries", "invention",
        "inventions", "breakthrough", "quantum", "biotech", "materials",
        "physics", "chemistry", "biology", "genome", "telescope", "astronomy",
        "asteroid", "comet", "galaxy", "galaxies", "laboratory", "experiment",
        "experiments", "eclipse",
    } or {"black", "hole"} <= terms:
        return "Science and inventions"
    if terms & {
        "climate", "emissions", "wildfire", "wildfires", "solar", "battery",
        "batteries", "nuclear",
    }:
        return "Climate and energy"
    return category


def fresh_enough(published: datetime, verified: datetime, hours: int) -> bool:
    age = verified - published.astimezone(verified.tzinfo)
    return timedelta(hours=-2) <= age <= timedelta(hours=hours)


def publisher(url: str) -> str:
    domain = registrable_domain(urlsplit(url).hostname or "")
    return {
        "reuters.com": "Reuters",
        "bbc.com": "BBC",
        "bbc.co.uk": "BBC",
        "cnbc.com": "CNBC",
        "ft.com": "Financial Times",
        "wsj.com": "The Wall Street Journal",
        "nytimes.com": "The New York Times",
        "washingtonpost.com": "The Washington Post",
        "theguardian.com": "The Guardian",
        "npr.org": "NPR",
        "axios.com": "Axios",
        "politico.com": "Politico",
        "wired.com": "Wired",
        "theverge.com": "The Verge",
        "fortune.com": "Fortune",
        "forbes.com": "Forbes",
        "bloomberg.com": "Bloomberg",
        "apnews.com": "AP",
        "techcrunch.com": "TechCrunch",
        "arstechnica.com": "Ars Technica",
        "technologyreview.com": "MIT Technology Review",
        "bleepingcomputer.com": "BleepingComputer",
        "semafor.com": "Semafor",
        "theregister.com": "The Register",
        "zdnet.com": "ZDNet",
        "businessinsider.com": "Business Insider",
        "weforum.org": "World Economic Forum",
        "bls.gov": "U.S. Bureau of Labor Statistics",
        "hbr.org": "Harvard Business Review",
        "mit.edu": "MIT",
        "github.blog": "GitHub",
        "blog.google": "Google",
        "deepmind.google": "Google DeepMind",
        "nvidia.com": "NVIDIA",
        "microsoft.com": "Microsoft",
        "openai.com": "OpenAI",
        "anthropic.com": "Anthropic",
        "coursera.org": "Coursera",
        "amazon.com": "AWS",
        "fb.com": "Meta",
        "cisa.gov": "CISA",
        "nasa.gov": "NASA",
        "esa.int": "ESA",
        "nsf.gov": "U.S. National Science Foundation",
        "usda.gov": "USDA",
        "fao.org": "UN Food and Agriculture Organization",
        "energy.gov": "U.S. Department of Energy",
        "noaa.gov": "NOAA",
        "usgs.gov": "U.S. Geological Survey",
        "sec.gov": "U.S. SEC",
        "federalreserve.gov": "Federal Reserve",
        "huggingface.co": "Hugging Face",
        "oecd.org": "OECD",
        "europa.eu": "European Commission",
        "nature.com": "Nature",
        "science.org": "Science",
    }.get(domain, domain)


def source_policy(url: str) -> dict[str, str]:
    host = (urlsplit(url).hostname or "").casefold().removeprefix("www.")
    if host == "community.openai.com":
        return {"source_type": "reputable"}
    domain = registrable_domain(host)
    path = urlsplit(url).path.casefold()
    if (
        domain == "nature.com"
        and re.search(r"/articles/s\d", path)
    ) or (
        domain == "science.org"
        and "/doi/" in path
    ):
        return {"source_type": "primary", "primary_kind": "research"}
    primary_kind = PRIMARY_SOURCE_KINDS.get(domain)
    if primary_kind:
        return {"source_type": "primary", "primary_kind": primary_kind}
    return {"source_type": "reputable"}


def publisher_group(url: str) -> str:
    domain = registrable_domain(urlsplit(url).hostname or "")
    return {
        "bbc.com": "bbc",
        "bbc.co.uk": "bbc",
    }.get(domain, domain)


def reader_primary_url(
    sources: list[dict[str, str]],
    fallback: str,
) -> str:
    """Prefer an opened official or broadly accessible article for the headline."""
    paywalled = {
        "bloomberg.com",
        "ft.com",
        "wsj.com",
        "nytimes.com",
        "washingtonpost.com",
        "economist.com",
        "fortune.com",
        "businessinsider.com",
    }

    def priority(source: dict[str, str]) -> tuple[int, int]:
        domain = registrable_domain(urlsplit(source["url"]).hostname or "")
        return (
            0 if source.get("source_type") == "primary" else 1,
            1 if domain in paywalled else 0,
        )

    return min(sources, key=priority)["url"] if sources else fallback


def deliver_messages(
    messages: list[str],
    *,
    preview: bool = False,
    command_runner=subprocess.run,
    sleep_fn=time.sleep,
    max_attempts: int = 3,
) -> None:
    """Send topic-section messages directly so Telegram boundaries stay intentional."""
    if not 1 <= len(messages) <= MAX_TELEGRAM_MESSAGES:
        raise RuntimeError("Morning briefing must contain between one and five messages")
    if preview:
        print("\n\n--- MESSAGE BREAK ---\n\n".join(messages))
        return
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    sibling_cli = Path(sys.executable).with_name(
        "hermes.exe" if os.name == "nt" else "hermes"
    )
    hermes_cli = str(sibling_cli) if sibling_cli.exists() else shutil.which("hermes")
    command_prefix = (
        [hermes_cli]
        if hermes_cli
        else [sys.executable, "-m", "hermes_cli.main"]
    )
    for index, message in enumerate(messages, start=1):
        detail = "unknown delivery error"
        for attempt in range(1, max_attempts + 1):
            result = command_runner(
                [
                    *command_prefix,
                    "send",
                    "--to",
                    "telegram",
                    "--quiet",
                    message,
                ],
                capture_output=True,
                text=True,
                timeout=90,
                creationflags=creationflags,
            )
            if result.returncode == 0:
                break
            detail = (
                result.stderr
                or result.stdout
                or f"delivery command exited with code {result.returncode}"
            ).strip()
            if attempt < max_attempts:
                sleep_fn(2 ** attempt)
        else:
            raise RuntimeError(
                f"Telegram category message {index}/{len(messages)} failed "
                f"after {max_attempts} attempts: {detail}"
            )


def wait_for_local_delivery(hour: int = 8, minute: int = 0) -> None:
    """Hold a completed early-morning briefing until its local delivery target."""
    now = datetime.now(TIMEZONE)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if 5 <= now.hour < hour and target > now:
        time.sleep((target - now).total_seconds())


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and deliver Morning Intelligence")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print topic-section messages without sending them to Telegram.",
    )
    parser.add_argument(
        "--candidates-file",
        type=Path,
        help="Use a previously collected candidate JSON file for reproducible preview testing.",
    )
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Print rejection reasons and category counts to stderr.",
    )
    args = parser.parse_args()
    discover_plugins()
    store_module = importlib.import_module("hermes_plugins.news_intelligence.store")
    payload = (
        json.loads(args.candidates_file.read_text(encoding="utf-8"))
        if args.candidates_file
        else collect_candidates()
    )
    verified = datetime.fromisoformat(str(payload["collected_at"]))
    with store_module.NewsStore() as prior_store:
        prior = prior_store.query(
            "",
            start_date=(verified.date() - timedelta(days=14)).isoformat(),
            end_date=verified.date().isoformat(),
            limit=100,
        )
    prior_stories = list(prior.get("results", []))
    prior_urls = set()
    for item in prior_stories:
        prior_urls.add(str(item.get("canonical_url") or ""))
        prior_urls.update(
            str(source.get("canonical_url") or source.get("url") or "")
            for source in item.get("sources", [])
        )
    rejection_reasons: list[str] = []
    stories: list[dict] = []
    category_counts = {category: 0 for category in EDITORIAL_CATEGORIES}
    selected_urls: set[str] = set()
    allowed_dates = set(payload.get("dates_searched") or [verified.date().isoformat()])
    freshness_hours = int(payload.get("freshness_hours") or 24)
    preferred_freshness_hours = int(
        payload.get("preferred_freshness_hours") or 24
    )
    loop_start_time = time.monotonic()
    MAX_LOOP_DURATION = 1500  # 25 min max budget to ensure cron completion well within 3600s

    for candidate in interleave_candidates(list(payload.get("candidates", []))):
        elapsed = time.monotonic() - loop_start_time
        if elapsed > MAX_LOOP_DURATION:
            print(
                f"[Morning Intelligence] Run duration budget reached ({round(elapsed)}s). "
                f"Proceeding to briefing with {len(stories)} verified stories.",
                file=sys.stderr,
            )
            break
        fast_mode = (elapsed > 1200)

        if len(stories) >= MAX_TOTAL_STORIES:
            break
        category = str(candidate.get("category") or "")
        if (
            category not in category_counts
            or category_counts[category] >= TARGET_PER_CATEGORY
            or len(stories) >= MAX_VERIFIED_POOL
        ):
            continue
        candidate["url"] = canonical_candidate_url(candidate["url"])
        primary_url = candidate["url"]
        if not direct_candidate(primary_url):
            rejection_reasons.append("candidate URL is not a direct article")
            continue
        if primary_url in prior_urls or primary_url in selected_urls:
            continue

        content, provider_published, extract_error = extract_article(primary_url)
        if not content:
            rejection_reasons.append(
                f"could not open {primary_url}"
                + (f": {extract_error}" if extract_error else "")
            )
            continue

        primary_published = (
            provider_published
            or parse_published(content)
            or parse_published(str(candidate.get("published_at") or ""))
            or fetch_publication_time(primary_url)
            or parse_published(str(candidate.get("search_evidence") or ""))
        )
        primary_excerpt = evidence_excerpt(content, candidate["title"])
        primary_slice = article_slice(content, candidate["title"])
        if primary_published is None:
            rejection_reasons.append(
                f"no verifiable publication time for {primary_url}"
            )
            continue
        if not fresh_enough(primary_published, verified, freshness_hours):
            rejection_reasons.append(f"candidate is outside freshness window: {primary_url}")
            continue
        if any(
            same_development(candidate["title"], item["headline"])
            for item in stories
        ):
            rejection_reasons.append(f"duplicate development skipped: {primary_url}")
            continue
        if not primary_excerpt or len(primary_slice) < 180:
            rejection_reasons.append(f"no supporting article content in {primary_url}")
            continue

        source_items = [
            {
                "url": primary_url,
                "publisher": publisher(primary_url),
                **source_policy(primary_url),
                "published_at": primary_published.isoformat(),
                "opened_at": verified.isoformat(),
                "evidence_excerpt": primary_excerpt,
                **(
                    {"syndication_origin": "Bloomberg"}
                    if publisher(primary_url) == "Fortune"
                    and re.search(r"\bBloomberg\b", content)
                    else {}
                ),
            }
        ]
        contents = [primary_slice]
        urls = [primary_url]

        if source_policy(primary_url)["source_type"] != "primary":
            options = list(candidate.get("corroboration_options") or [])
            try:
                options.extend(
                    find_corroboration(candidate, allowed_dates, limit=6)
                )
            except Exception as exc:
                rejection_reasons.append(f"corroboration search failed: {exc}")
            option_urls: set[str] = set()
            for partner in options:
                partner_url = canonical_candidate_url(str(partner.get("url") or ""))
                if (
                    not partner_url
                    or partner_url in option_urls
                    or not direct_candidate(partner_url)
                    or partner_url in prior_urls
                    or partner_url in selected_urls
                    or publisher_group(partner_url) == publisher_group(primary_url)
                ):
                    continue
                option_urls.add(partner_url)
                partner_content, partner_published_hint, _ = extract_article(partner_url)
                if not partner_content:
                    continue
                partner_published = (
                    partner_published_hint
                    or parse_published(partner_content)
                    or parse_published(str(partner.get("published_at") or ""))
                    or fetch_publication_time(partner_url)
                    or parse_published(str(partner.get("search_evidence") or ""))
                )
                partner_excerpt = evidence_excerpt(
                    partner_content,
                    candidate["title"],
                )
                partner_slice = article_slice(partner_content, candidate["title"])
                if (
                    partner_published is None
                    or not fresh_enough(
                        partner_published,
                        verified,
                        freshness_hours,
                    )
                    or not partner_excerpt
                    or len(partner_slice) < 180
                ):
                    continue
                source_items.append(
                    {
                        "url": partner_url,
                        "publisher": publisher(partner_url),
                        **source_policy(partner_url),
                        "published_at": partner_published.isoformat(),
                        "opened_at": verified.isoformat(),
                        "evidence_excerpt": partner_excerpt,
                    }
                )
                contents.append(partner_slice)
                urls.append(partner_url)
                break
            if len(source_items) < 2:
                rejection_reasons.append(
                    f"no readable independent corroboration for {primary_url}"
                )
                continue

        ollama_summary = (
            None
            if fast_mode
            else summarize_with_ollama(
                candidate,
                contents[0],
                contents[1] if len(contents) > 1 else "",
            )
        )
        summary = normalize_summary(
            ollama_summary,
            candidate,
            " ".join(contents),
        )
        quality_ok, quality_reason = summary_quality(summary, candidate)
        if not quality_ok:
            summary = normalize_summary(
                None,
                candidate,
                " ".join(contents),
            )
            quality_ok, quality_reason = summary_quality(summary, candidate)
        if not quality_ok:
            rejection_reasons.append(
                f"editorial quality gate failed ({quality_reason}) for {primary_url}"
            )
            continue
        corrected = corrected_category(
            category,
            summary["headline"],
            summary["summary"],
        )
        if corrected != category:
            if category_counts[corrected] >= TARGET_PER_CATEGORY:
                rejection_reasons.append(
                    f"corrected category is already full: {primary_url}"
                )
                continue
            category = corrected
            summary["why_it_matters"] = category_relevance(
                category,
                summary["headline"],
            )
        if not category_relevant(
            category,
            summary["headline"],
            summary["summary"],
        ):
            rejection_reasons.append(
                f"story does not substantively match {category}: {primary_url}"
            )
            continue
        if any(
            same_development(summary["headline"], item["headline"])
            for item in stories
        ):
            rejection_reasons.append(f"duplicate development skipped: {primary_url}")
            continue
        prior_relation, repeated = prior_story_relationship(
            summary["headline"],
            summary["summary"],
            prior_stories,
        )
        if repeated:
            rejection_reasons.append(
                f"previously covered without a material change: {primary_url}"
            )
            continue
        story = {
            "category": category,
            "headline": summary["headline"],
            "summary": summary["summary"],
            "why_it_matters": summary["why_it_matters"],
            "published_at": primary_published.isoformat(),
            "primary_url": reader_primary_url(source_items, primary_url),
            "sources": source_items,
            "facts": [
                {
                    "claim": claim,
                    "source_urls": urls,
                    "confidence": 0.9,
                }
                for claim in summary["facts"]
            ],
            "entities": summary["entities"],
            "topics": list(dict.fromkeys([category, *summary["topics"]]))[:8],
            "relations": [prior_relation] if prior_relation else [],
            "_backfill": not fresh_enough(
                primary_published,
                verified,
                preferred_freshness_hours,
            ),
        }
        stories.append(story)
        category_counts[category] += 1
        selected_urls.update(urls)

    if stories:
        stories = select_briefing_stories(stories)
        if not args.candidates_file:
            verified = datetime.now(TIMEZONE)
            for story in stories:
                for source in story["sources"]:
                    source["opened_at"] = verified.isoformat()
        category_counts = {
            category: sum(
                1 for story in stories if story["category"] == category
            )
            for category in EDITORIAL_CATEGORIES
        }
        if args.preview:
            with tempfile.TemporaryDirectory(prefix="hermes-news-preview-") as temp_home:
                with store_module.NewsStore(temp_home) as store:
                    result = store.store_briefing(
                        verified.date().isoformat(),
                        verified.isoformat(),
                        stories,
                        sync_memory=False,
                    )
        else:
            with store_module.NewsStore() as store:
                result = store.store_briefing(
                    verified.date().isoformat(),
                    verified.isoformat(),
                    stories,
                )
        if result.get("success"):
            if args.diagnostics:
                print(
                    "Accepted by category: "
                    + json.dumps(category_counts, ensure_ascii=False),
                    file=sys.stderr,
                )
                for item in stories:
                    print(
                        "Proposed: "
                        f"{item['category']} | {item['headline']} | "
                        f"{item['published_at']} | "
                        + ", ".join(
                            f"{source['publisher']}@{source['published_at']}"
                            for source in item["sources"]
                        ),
                        file=sys.stderr,
                    )
                for detail, count in Counter(rejection_reasons).most_common():
                    print(f"Rejected ({count}): {detail}", file=sys.stderr)
                for rejected in result.get("rejected", []):
                    print(
                        "Validator rejected: "
                        f"{rejected.get('headline')}: {rejected.get('reason')}",
                        file=sys.stderr,
                    )
            messages = list(result["briefing_messages"])
            accepted_count = int(result.get("accepted_count") or len(stories))
            if accepted_count < 15:
                messages[-1] += (
                    "\n\nCoverage note: "
                    f"{accepted_count} stories passed verification today; "
                    "the target is 15-20, and unverified items were omitted."
                )
            if not args.preview:
                wait_for_local_delivery()
            deliver_messages(messages, preview=args.preview)
            return
        rejection_reasons.extend(
            str(item.get("reason") or "validation failed")
            for item in result.get("rejected", [])
        )
        rejection_reasons.append(str(result.get("error") or "validation failed"))

    if rejection_reasons:
        if args.preview:
            for detail in rejection_reasons:
                print(f"Rejected: {detail}", file=sys.stderr)
        normalized_reasons = [
            re.sub(r"\s+for https?://\S+$", "", text)
            for text in rejection_reasons
        ]
        reason = "; ".join(
            f"{text} ({count})"
            for text, count in Counter(normalized_reasons).most_common(5)
        )
    else:
        reason = "no independently corroborated fresh candidates"
    deliver_messages(
        [
            "Morning Intelligence could not be produced today because no "
            "candidate passed the freshness, readability, and source checks. "
            "Nothing was archived. The next scheduled run will try again."
        ],
        preview=args.preview,
    )


if __name__ == "__main__":
    main()
