# -*- coding: utf-8 -*-
"""
Deal Finder, Aggregator & Price Watch Engine for Hermes Agent
=============================================================
Combines:
1. Community Deal Aggregators:
   - Slickdeals (Frontpage Hot Deals & Live Search RSS/HTML)
   - Reddit Deal Communities (r/buildapcsales, r/deals, r/TechDeals, r/laptopdeals)
   - DealNews (Curated Electronics & Computing Deals)
2. Multi-Vendor Retailers (with Chintu Headless Browser DOM Fallback):
   - Amazon, Newegg, Best Buy, Walmart, B&H Photo, Micro Center, Costco, Target, eBay
3. Dedicated 'Chintu' Chrome Profile Integration:
   - Never touches the user's personal 'Sasidhar' (Default) Chrome profile.
   - Uses isolated Chintu headless DOM rendering (`--headless=new --dump-dom`) for
     background checks and `Profile 1` (`Chintu`) when opening deals visibly.

Safety:
- Strictly Read-Only. Never proceeds to checkout, payment, or cart modification.
"""

from __future__ import annotations

import concurrent.futures
import html as html_lib
import json
import logging
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

# Ensure Windows UTF-8 stdout safety
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logger = logging.getLogger(__name__)

WATCH_FILE = Path(__file__).resolve().parent / "deal_watches.json"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

STORE_KEYWORDS = [
    ("amazon", "Amazon"),
    ("amzn", "Amazon"),
    ("newegg", "Newegg"),
    ("best buy", "Best Buy"),
    ("bestbuy", "Best Buy"),
    ("walmart", "Walmart"),
    ("costco", "Costco"),
    ("target", "Target"),
    ("micro center", "Micro Center"),
    ("microcenter", "Micro Center"),
    ("b&h", "B&H Photo"),
    ("bhphoto", "B&H Photo"),
    ("ebay", "eBay"),
    ("home depot", "Home Depot"),
    ("lowe's", "Lowe's"),
    ("lowes", "Lowe's"),
    ("adorama", "Adorama"),
    ("lenovo", "Lenovo"),
    ("dell", "Dell"),
    ("hp.com", "HP Store"),
    ("samsung", "Samsung"),
    ("apple", "Apple"),
    ("steam", "Steam"),
    ("woot", "Woot"),
]


@dataclass(frozen=True)
class DealListing:
    vendor: str
    title: str
    price: Optional[float]
    shipping: Optional[float]
    url: str
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def total(self) -> Optional[float]:
        if self.price is None:
            return None
        if self.shipping is None:
            return round(float(self.price), 2)
        return round(float(self.price) + float(self.shipping), 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vendor": self.vendor,
            "title": self.title,
            "price": self.price,
            "shipping": self.shipping,
            "total": self.total,
            "url": self.url,
            "meta": self.meta,
        }


def parse_money(value: str) -> Optional[float]:
    """Extracts numeric dollar value from string like '$199.99' or '1,249.00'."""
    raw = str(value or "").strip().replace(",", "")
    # Prefer explicit dollar-prefixed number first
    m_dollar = re.search(r"\$\s*(\d+(?:\.\d{1,2})?)", raw)
    if m_dollar:
        try:
            val = round(float(m_dollar.group(1)), 2)
            if 0.5 <= val <= 50000:
                return val
        except Exception:
            pass
    m = re.search(r"(-?\d+(?:\.\d{1,2})?)", raw)
    if not m:
        return None
    try:
        return round(float(m.group(1)), 2)
    except Exception:
        return None


def extract_price_from_title(title: str) -> Optional[float]:
    """Extracts the primary deal price from a Slickdeals/Reddit/DealNews headline."""
    raw = str(title or "").replace(",", "")
    matches = re.findall(r"\$\s*(\d+(?:\.\d{1,2})?)", raw)
    if not matches:
        return None
    # Usually the deal price is the first or last $ amount; avoid "$X off" discounts
    for m_obj in re.finditer(r"\$\s*(\d+(?:\.\d{1,2})?)(?!\s*(?:off|discount|gift|rebate|save|savings))", raw, re.IGNORECASE):
        try:
            val = round(float(m_obj.group(1)), 2)
            if 0.5 <= val <= 50000:
                return val
        except Exception:
            continue
    try:
        return round(float(matches[0]), 2)
    except Exception:
        return None


def detect_merchant_from_text(text: str, default_source: str = "Slickdeals") -> str:
    """Identifies the underlying store (e.g. 'Amazon via Slickdeals') from title/description."""
    lower = str(text or "").lower()
    for kw, store_name in STORE_KEYWORDS:
        if kw in lower:
            if store_name.lower() == default_source.lower():
                return store_name
            return f"{store_name} ({default_source})"
    return default_source


def fetch_html(url: str, timeout_s: int = 10, use_chintu_browser_fallback: bool = False) -> str:
    """Best-effort HTML retrieval with requests, falling back to Chintu Headless Chrome DOM when needed."""
    text = ""
    try:
        import requests
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout_s)
        if resp.status_code == 200 and len(resp.text or "") > 1500:
            text = resp.text
    except Exception as exc:
        logger.debug(f"HTTP fetch failed for {url}: {exc}")

    # Check if blocked by bot challenge / CAPTCHA or empty
    is_blocked = (
        not text
        or len(text) < 2500
        or "Automated access" in text
        or "Robot or human" in text
        or "Enter the characters you see below" in text
    )
    if is_blocked and use_chintu_browser_fallback:
        try:
            try:
                from local_model_lab.hermes_browser import fetch_dom_with_chintu_browser
            except ImportError:
                from hermes_browser import fetch_dom_with_chintu_browser
            dom = fetch_dom_with_chintu_browser(url, timeout_s=max(10, timeout_s))
            if dom and len(dom) > len(text):
                return dom
        except Exception as exc:
            logger.debug(f"Chintu browser fallback error for {url}: {exc}")
    return text


# ── 1. SLICKDEALS LIVE SEARCH & FRONTPAGE ENGINE ────────────────────────────

def search_slickdeals(query: str = "", max_results: int = 10, frontpage_only: bool = False) -> List[DealListing]:
    """
    Fetches live verified community deals from Slickdeals.
    Supports both keyword search and Frontpage Hot Deals mode.
    """
    if frontpage_only or not query.strip():
        url = "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1"
    else:
        encoded = quote_plus(query.strip())
        url = f"https://slickdeals.net/newsearch.php?q={encoded}&searcharea=deals&searchin=first&rss=1"

    xml_text = fetch_html(url, timeout_s=10, use_chintu_browser_fallback=False)
    if not xml_text or "<item>" not in xml_text:
        return []

    results: List[DealListing] = []
    try:
        root = ET.fromstring(xml_text)
        items = root.findall(".//item")
        for item in items:
            raw_title = html_lib.unescape(item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = html_lib.unescape(item.findtext("description") or "")
            pub_date = (item.findtext("pubDate") or "").strip()

            if not raw_title:
                continue

            price_val = extract_price_from_title(raw_title) or extract_price_from_title(desc)
            if price_val is None:
                continue

            # Check shipping
            lower_all = f"{raw_title} {desc}".lower()
            ship_val = 0.0 if ("free s/h" in lower_all or "free shipping" in lower_all or "free store pickup" in lower_all) else 0.0

            vendor_label = detect_merchant_from_text(f"{raw_title} {link}", default_source="Slickdeals")
            badge = "🔥 Frontpage" if (frontpage_only or "fp" in link) else "👍 Community Deal"

            # Extract coupon code if mentioned in description
            coupon_match = re.search(r"(?:code|coupon|promo)\s*[:\-]?\s*([A-Z0-9]{4,16})", desc, re.IGNORECASE)
            coupon = coupon_match.group(1) if coupon_match else None

            results.append(DealListing(
                vendor=vendor_label,
                title=raw_title[:115],
                price=price_val,
                shipping=ship_val,
                url=link,
                meta={
                    "source": "slickdeals",
                    "badge": badge,
                    "coupon": coupon,
                    "published": pub_date[:22] if pub_date else "Live",
                    "browser_profile": "Chintu",
                }
            ))
            if len(results) >= max_results:
                break
    except Exception as exc:
        logger.debug(f"Slickdeals parse error: {exc}")
    return results


# ── 2. REDDIT DEAL COMMUNITIES (r/buildapcsales, r/deals, r/TechDeals) ──────

def search_reddit_deals(query: str = "", max_results: int = 8) -> List[DealListing]:
    """
    Fetches real-time community-vetted deals from r/buildapcsales, r/deals, r/laptopdeals, and r/TechDeals.
    """
    subs = "buildapcsales+deals+TechDeals+laptopdeals"
    if query.strip():
        encoded = quote_plus(query.strip())
        url = f"https://old.reddit.com/r/{subs}/search.rss?q={encoded}&restrict_sr=on&sort=new"
    else:
        url = f"https://old.reddit.com/r/{subs}/hot.rss"

    xml_text = fetch_html(url, timeout_s=10)
    if not xml_text or "<entry>" not in xml_text:
        return []

    results: List[DealListing] = []
    try:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(xml_text)
        entries = root.findall("atom:entry", ns)
        for entry in entries:
            raw_title = html_lib.unescape(entry.findtext("atom:title", default="", namespaces=ns)).strip()
            if not raw_title:
                continue

            link_el = entry.find("atom:link", ns)
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            content_html = html_lib.unescape(entry.findtext("atom:content", default="", namespaces=ns))

            # Find direct outbound store link if present inside Reddit content
            ext_link_match = re.search(r'href="(https?://(?!(?:www\.|old\.)?reddit\.com)[^"]+)"', content_html)
            target_url = ext_link_match.group(1) if ext_link_match else link

            price_val = extract_price_from_title(raw_title)
            if price_val is None:
                continue

            vendor_label = detect_merchant_from_text(f"{raw_title} {target_url}", default_source="Reddit Deals")
            results.append(DealListing(
                vendor=vendor_label,
                title=raw_title[:115],
                price=price_val,
                shipping=0.0,
                url=target_url or link,
                meta={
                    "source": "reddit",
                    "badge": "👽 r/Deals Verified",
                    "reddit_thread": link,
                    "browser_profile": "Chintu",
                }
            ))
            if len(results) >= max_results:
                break
    except Exception as exc:
        logger.debug(f"Reddit deals parse error: {exc}")
    return results


# ── 3. DEALNEWS CURATED DEALS ENGINE ────────────────────────────────────────

def search_dealnews(query: str = "", max_results: int = 8) -> List[DealListing]:
    """Fetches curated deals from DealNews RSS & search."""
    url = "https://www.dealnews.com/c142/Computers/?rss=1"
    xml_text = fetch_html(url, timeout_s=10)
    if not xml_text or "<item>" not in xml_text:
        return []

    q_terms = [t.lower() for t in query.strip().split() if len(t) >= 2]
    results: List[DealListing] = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.findall(".//item"):
            raw_title = html_lib.unescape(item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = html_lib.unescape(item.findtext("description") or "")
            combined = f"{raw_title} {desc}".lower()

            if q_terms and not all(t in combined for t in q_terms):
                continue

            price_val = extract_price_from_title(raw_title) or extract_price_from_title(desc)
            if price_val is None:
                continue

            vendor_label = detect_merchant_from_text(f"{raw_title} {desc}", default_source="DealNews")
            results.append(DealListing(
                vendor=vendor_label,
                title=raw_title[:115],
                price=price_val,
                shipping=0.0,
                url=link,
                meta={
                    "source": "dealnews",
                    "badge": "📰 Editor Pick",
                    "browser_profile": "Chintu",
                }
            ))
            if len(results) >= max_results:
                break
    except Exception as exc:
        logger.debug(f"DealNews parse error: {exc}")
    return results


# ── 4. DIRECT RETAILER PARSERS (WITH CHINTU HEADLESS BROWSER FALLBACK) ──────

def search_amazon(query: str, max_results: int = 6, use_browser: bool = True) -> List[DealListing]:
    """Scrapes Amazon search results via HTTP + Chintu Headless Chrome fallback + Slickdeals Amazon index."""
    encoded = quote_plus(query)
    url = f"https://www.amazon.com/s?k={encoded}"
    html = fetch_html(url, use_chintu_browser_fallback=use_browser)

    results: List[DealListing] = []
    if html:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            items = soup.find_all("div", {"data-component-type": "s-search-result"})
            for item in items[:max_results * 2]:
                title_node = item.find("h2")
                if not title_node:
                    continue
                title = title_node.get_text(strip=True)
                if not title or len(title) < 4:
                    continue

                link_node = title_node.find("a") or item.find("a", {"class": "a-link-normal"})
                href = link_node.get("href", "") if link_node else ""
                if href.startswith("/"):
                    href = f"https://www.amazon.com{href}"

                price_whole = item.find("span", {"class": "a-price-whole"})
                price_frac = item.find("span", {"class": "a-price-fraction"})
                price_val = None
                if price_whole:
                    whole_str = price_whole.get_text(strip=True).replace(".", "").replace(",", "")
                    frac_str = price_frac.get_text(strip=True) if price_frac else "00"
                    price_val = parse_money(f"{whole_str}.{frac_str}")
                elif item.find("span", {"class": "a-offscreen"}):
                    price_val = parse_money(item.find("span", {"class": "a-offscreen"}).get_text(strip=True))

                if price_val is not None:
                    results.append(DealListing(
                        vendor="Amazon",
                        title=title[:105],
                        price=price_val,
                        shipping=0.0,
                        url=href or url,
                        meta={"badge": "🛒 Prime Direct", "browser_profile": "Chintu"}
                    ))
                if len(results) >= max_results:
                    break
        except Exception as exc:
            logger.debug(f"Amazon parse error: {exc}")

    # Supplement with verified Amazon deals from Slickdeals if Amazon bot-wall blocked direct DOM
    if len(results) < 2:
        sd_amazon = search_slickdeals(f"{query} amazon", max_results=max_results)
        for d in sd_amazon:
            if "amazon" in d.vendor.lower() or "amazon" in d.title.lower():
                results.append(DealListing(
                    vendor="Amazon (Verified Deal)",
                    title=d.title,
                    price=d.price,
                    shipping=d.shipping,
                    url=d.url,
                    meta=d.meta,
                ))
                if len(results) >= max_results:
                    break
    return results


def search_newegg(query: str, max_results: int = 6, use_browser: bool = True) -> List[DealListing]:
    """Scrapes Newegg search results using HTTP + Chintu Headless Chrome DOM rendering."""
    encoded = quote_plus(query)
    url = f"https://www.newegg.com/p/pl?d={encoded}"
    html = fetch_html(url, use_chintu_browser_fallback=use_browser)
    if not html:
        return []

    results: List[DealListing] = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("div", {"class": "item-cell"}) or soup.find_all("div", {"class": "item-container"})
        for item in items[:max_results * 2]:
            title_node = item.find("a", {"class": "item-title"})
            if not title_node:
                continue
            title = title_node.get_text(strip=True)
            href = title_node.get("href", "")

            price_strong = item.find("li", {"class": "price-current"})
            price_val = parse_money(price_strong.get_text(strip=True)) if price_strong else None

            ship_node = item.find("li", {"class": "price-ship"})
            ship_val = 0.0
            if ship_node:
                txt = ship_node.get_text(strip=True).lower()
                if "free" not in txt:
                    ship_val = parse_money(txt) or 0.0

            if price_val is not None:
                results.append(DealListing(
                    vendor="Newegg",
                    title=title[:105],
                    price=price_val,
                    shipping=ship_val,
                    url=href or url,
                    meta={"badge": "🥚 Newegg Direct", "browser_profile": "Chintu"}
                ))
            if len(results) >= max_results:
                break
    except Exception as exc:
        logger.debug(f"Newegg parse error: {exc}")
    return results


def search_bestbuy(query: str, max_results: int = 6, use_browser: bool = True) -> List[DealListing]:
    """Scrapes Best Buy deals via Chintu Browser + Slickdeals BestBuy feed."""
    encoded = quote_plus(query)
    url = f"https://www.bestbuy.com/site/searchpage.jsp?st={encoded}"
    html = fetch_html(url, use_chintu_browser_fallback=use_browser)

    results: List[DealListing] = []
    if html:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            items = soup.find_all("li", {"class": "sku-item"})
            for item in items[:max_results * 2]:
                header = item.find("h4", {"class": "sku-title"}) or item.find("h4", {"class": "sku-header"})
                if not header:
                    continue
                title_link = header.find("a")
                if not title_link:
                    continue
                title = title_link.get_text(strip=True)
                href = title_link.get("href", "")
                if href.startswith("/"):
                    href = f"https://www.bestbuy.com{href}"

                price_box = item.find("div", {"class": "priceView-customer-price"})
                price_val = parse_money(price_box.get_text(strip=True)) if price_box else None

                if price_val is not None:
                    results.append(DealListing(
                        vendor="Best Buy",
                        title=title[:105],
                        price=price_val,
                        shipping=0.0,
                        url=href or url,
                        meta={"badge": "🏷️ Store Pickup", "browser_profile": "Chintu"}
                    ))
                if len(results) >= max_results:
                    break
        except Exception as exc:
            logger.debug(f"Best Buy parse error: {exc}")

    if len(results) < 2:
        sd_bb = search_slickdeals(f"{query} best buy", max_results=max_results)
        for d in sd_bb:
            if "best buy" in d.vendor.lower() or "bestbuy" in d.title.lower() or "best buy" in d.title.lower():
                results.append(DealListing(
                    vendor="Best Buy (Verified Deal)",
                    title=d.title,
                    price=d.price,
                    shipping=d.shipping,
                    url=d.url,
                    meta=d.meta,
                ))
                if len(results) >= max_results:
                    break
    return results


def search_walmart(query: str, max_results: int = 6, use_browser: bool = True) -> List[DealListing]:
    """Scrapes Walmart search results + verified Walmart community deals."""
    encoded = quote_plus(query)
    url = f"https://www.walmart.com/search?q={encoded}"
    html = fetch_html(url, use_chintu_browser_fallback=use_browser)

    results: List[DealListing] = []
    if html:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            items = soup.find_all("div", {"data-item-id": True})
            for item in items[:max_results * 2]:
                title_node = item.find("span", {"data-automation-id": "product-title"})
                if not title_node:
                    continue
                title = title_node.get_text(strip=True)
                link_node = item.find("a")
                href = link_node.get("href", "") if link_node else ""
                if href.startswith("/"):
                    href = f"https://www.walmart.com{href}"

                price_node = item.find("div", {"data-automation-id": "product-price"})
                price_val = parse_money(price_node.get_text(strip=True)) if price_node else None

                if price_val is not None:
                    results.append(DealListing(
                        vendor="Walmart",
                        title=title[:105],
                        price=price_val,
                        shipping=0.0,
                        url=href or url,
                        meta={"badge": "🔵 Walmart Direct", "browser_profile": "Chintu"}
                    ))
                if len(results) >= max_results:
                    break
        except Exception as exc:
            logger.debug(f"Walmart parse error: {exc}")

    if len(results) < 2:
        sd_wm = search_slickdeals(f"{query} walmart", max_results=max_results)
        for d in sd_wm:
            if "walmart" in d.vendor.lower() or "walmart" in d.title.lower():
                results.append(DealListing(
                    vendor="Walmart (Verified Deal)",
                    title=d.title,
                    price=d.price,
                    shipping=d.shipping,
                    url=d.url,
                    meta=d.meta,
                ))
                if len(results) >= max_results:
                    break
    return results


def search_bhphoto(query: str, max_results: int = 6, use_browser: bool = True) -> List[DealListing]:
    """Scrapes B&H Photo search page."""
    encoded = quote_plus(query)
    url = f"https://www.bhphotovideo.com/c/search?Ntt={encoded}"
    html = fetch_html(url, use_chintu_browser_fallback=use_browser)
    results: List[DealListing] = []
    if html:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            items = soup.find_all("div", {"data-selenium": "miniProductPage"})
            for item in items[:max_results * 2]:
                title_node = item.find("span", {"data-selenium": "miniProductPageName"})
                if not title_node:
                    continue
                title = title_node.get_text(strip=True)
                link = item.find("a")
                href = link.get("href", "") if link else ""
                price_node = item.find("span", {"data-selenium": "uppedDecimalPriceFirst"})
                price_val = parse_money(price_node.get_text(strip=True)) if price_node else None

                if price_val is not None:
                    results.append(DealListing(
                        vendor="B&H Photo",
                        title=title[:105],
                        price=price_val,
                        shipping=0.0,
                        url=href or url,
                        meta={"badge": "📸 Auth Dealer", "browser_profile": "Chintu"}
                    ))
                if len(results) >= max_results:
                    break
        except Exception as exc:
            logger.debug(f"BHPhoto parse error: {exc}")
    return results


def search_microcenter(query: str, max_results: int = 6, use_browser: bool = True) -> List[DealListing]:
    """Scrapes Micro Center search page."""
    encoded = quote_plus(query)
    url = f"https://www.microcenter.com/search/search_results.aspx?Ntt={encoded}"
    html = fetch_html(url, use_chintu_browser_fallback=use_browser)
    if not html:
        return []

    results: List[DealListing] = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("li", {"class": "product_wrapper"})
        for item in items[:max_results * 2]:
            title_node = item.find("a", {"data-name": True})
            if not title_node:
                continue
            title = title_node.get_text(strip=True) or title_node.get("data-name", "")
            href = title_node.get("href", "")
            if href.startswith("/"):
                href = f"https://www.microcenter.com{href}"

            price_node = item.find("span", {"itemprop": "price"})
            price_val = parse_money(price_node.get_text(strip=True)) if price_node else parse_money(title_node.get("data-price", ""))

            if price_val is not None:
                results.append(DealListing(
                    vendor="Micro Center",
                    title=title[:105],
                    price=price_val,
                    shipping=0.0,
                    url=href or url,
                    meta={"badge": "🏬 Micro Center", "browser_profile": "Chintu"}
                ))
            if len(results) >= max_results:
                break
    except Exception as exc:
        logger.debug(f"Microcenter parse error: {exc}")
    return results


# ── UNIFIED MULTI-SOURCE DEAL SEARCH & FRONTPAGE DISPATCHER ─────────────────

DEFAULT_VENDORS = [
    "slickdeals",
    "reddit",
    "dealnews",
    "amazon",
    "newegg",
    "bestbuy",
    "walmart",
    "bhphoto",
    "microcenter",
]


def get_hot_frontpage_deals(max_results: int = 20) -> List[DealListing]:
    """
    Returns today's hottest live Frontpage deals across Slickdeals, Reddit (r/buildapcsales & r/deals), and DealNews.
    """
    all_deals: List[DealListing] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        f_sd = pool.submit(search_slickdeals, "", max_results, True)
        f_rd = pool.submit(search_reddit_deals, "", 10)
        f_dn = pool.submit(search_dealnews, "", 8)
        for fut in (f_sd, f_rd, f_dn):
            try:
                all_deals.extend(fut.result(timeout=12))
            except Exception:
                pass
    return all_deals[:max_results]


def search_deals(
    query: str,
    vendors: Optional[List[str]] = None,
    max_results_per_vendor: int = 6,
    use_browser: bool = True,
) -> List[DealListing]:
    """
    Unified multi-vendor & community deal comparison across Slickdeals, Reddit, DealNews,
    Amazon, Newegg, Best Buy, Walmart, B&H Photo, and Micro Center.
    Executes in parallel for fast response and sorts by total price ascending.
    """
    clean_query = query.strip()
    if not clean_query:
        return get_hot_frontpage_deals(max_results=20)

    chosen_vendors = [v.strip().lower() for v in (vendors or DEFAULT_VENDORS)]
    tasks = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        if "slickdeals" in chosen_vendors:
            tasks.append(pool.submit(search_slickdeals, clean_query, max_results_per_vendor + 4, False))
        if "reddit" in chosen_vendors:
            tasks.append(pool.submit(search_reddit_deals, clean_query, max_results_per_vendor + 2))
        if "dealnews" in chosen_vendors:
            tasks.append(pool.submit(search_dealnews, clean_query, max_results_per_vendor))
        if "amazon" in chosen_vendors:
            tasks.append(pool.submit(search_amazon, clean_query, max_results_per_vendor, use_browser))
        if "newegg" in chosen_vendors:
            tasks.append(pool.submit(search_newegg, clean_query, max_results_per_vendor, use_browser))
        if "bestbuy" in chosen_vendors:
            tasks.append(pool.submit(search_bestbuy, clean_query, max_results_per_vendor, use_browser))
        if "walmart" in chosen_vendors:
            tasks.append(pool.submit(search_walmart, clean_query, max_results_per_vendor, use_browser))
        if "bhphoto" in chosen_vendors:
            tasks.append(pool.submit(search_bhphoto, clean_query, max_results_per_vendor, False))
        if "microcenter" in chosen_vendors:
            tasks.append(pool.submit(search_microcenter, clean_query, max_results_per_vendor, use_browser))

        all_listings: List[DealListing] = []
        for fut in tasks:
            try:
                all_listings.extend(fut.result(timeout=16))
            except Exception as exc:
                logger.debug(f"Vendor search worker timeout/error: {exc}")

    # Deduplicate by normalized title prefix and sort by total price ascending
    seen_titles = set()
    unique_priced: List[DealListing] = []
    for it in all_listings:
        if it.total is None or it.total <= 0:
            continue
        norm_t = re.sub(r"\W+", "", it.title.lower())[:45]
        if norm_t in seen_titles:
            continue
        seen_titles.add(norm_t)
        unique_priced.append(it)

    return sorted(unique_priced, key=lambda x: x.total)


# ── DEAL WATCH & ALERT STORE ────────────────────────────────────────────────

@dataclass
class DealWatch:
    id: str
    query: str
    target_price: Optional[float]
    vendors: List[str]
    interval_minutes: int = 180
    enabled: bool = True
    created_at: str = ""
    last_checked_at: Optional[str] = None
    last_best_total: Optional[float] = None
    last_best_vendor: Optional[str] = None
    last_best_url: Optional[str] = None
    last_alert_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DealWatch:
        return cls(**data)


class DealWatchStore:
    """Manages persistent product deal alerts on disk."""

    def __init__(self, filepath: Optional[Path] = None):
        self.filepath = filepath or WATCH_FILE
        self._watches: Dict[str, DealWatch] = {}
        self._load()

    def _load(self):
        if self.filepath.exists():
            try:
                data = json.loads(self.filepath.read_text(encoding="utf-8"))
                self._watches = {k: DealWatch.from_dict(v) for k, v in data.items()}
            except Exception as exc:
                logger.warning(f"Failed to load deal watches: {exc}")

    def _save(self):
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.to_dict() for k, v in self._watches.items()}
            self.filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.error(f"Failed to save deal watches: {exc}")

    def add_watch(
        self,
        query: str,
        target_price: Optional[float] = None,
        vendors: Optional[List[str]] = None,
        interval_minutes: int = 180
    ) -> DealWatch:
        import uuid
        watch_id = str(uuid.uuid4())[:8]
        now_iso = datetime.now(timezone.utc).isoformat()
        watch = DealWatch(
            id=watch_id,
            query=query.strip(),
            target_price=target_price,
            vendors=vendors or DEFAULT_VENDORS,
            interval_minutes=max(10, interval_minutes),
            enabled=True,
            created_at=now_iso,
        )
        self._watches[watch_id] = watch
        self._save()
        return watch

    def remove_watch(self, watch_id: str) -> bool:
        if watch_id in self._watches:
            del self._watches[watch_id]
            self._save()
            return True
        return False

    def list_watches(self) -> List[DealWatch]:
        return list(self._watches.values())

    def check_watch(self, watch_id: str) -> Optional[Dict[str, Any]]:
        watch = self._watches.get(watch_id)
        if not watch:
            return None

        listings = search_deals(watch.query, vendors=watch.vendors, max_results_per_vendor=4)
        now_iso = datetime.now(timezone.utc).isoformat()
        watch.last_checked_at = now_iso

        best = listings[0] if listings else None
        triggered_alert = False

        if best:
            watch.last_best_total = best.total
            watch.last_best_vendor = best.vendor
            watch.last_best_url = best.url

            if watch.target_price is not None and best.total <= watch.target_price:
                triggered_alert = True
                watch.last_alert_at = now_iso

        self._save()
        return {
            "watch": watch.to_dict(),
            "best_deal": best.to_dict() if best else None,
            "triggered_alert": triggered_alert,
            "all_deals": [l.to_dict() for l in listings[:8]],
        }


# Global store singleton
_watch_store_instance: Optional[DealWatchStore] = None


def get_deal_watch_store() -> DealWatchStore:
    global _watch_store_instance
    if _watch_store_instance is None:
        _watch_store_instance = DealWatchStore()
    return _watch_store_instance
