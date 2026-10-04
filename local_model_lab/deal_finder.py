# -*- coding: utf-8 -*-
"""
Deal Finder & Price Watch Engine for Hermes Agent
Non-browser, high-performance price scraper & deal tracker across Amazon,
Newegg, Best Buy, Walmart, B&H Photo, and Micro Center.

Safety:
- Strictly Read-Only. Never proceeds to checkout, payment, or cart modification.
- Zero credential leakage.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urljoin, urlparse

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
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


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
    m = re.search(r"(-?\d+(?:\.\d{1,2})?)", raw)
    if not m:
        return None
    try:
        return round(float(m.group(1)), 2)
    except Exception:
        return None


def fetch_html(url: str, timeout_s: int = 12) -> str:
    """Best-effort HTML retrieval with requests."""
    try:
        import requests
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout_s)
        if resp.status_code == 200:
            return resp.text or ""
    except Exception as exc:
        logger.debug(f"HTTP fetch failed for {url}: {exc}")
    return ""


# ── VENDOR PARSERS ──────────────────────────────────────────────────────────

def search_amazon(query: str, max_results: int = 6) -> List[DealListing]:
    """Scrapes Amazon search results page."""
    encoded = quote_plus(query)
    url = f"https://www.amazon.com/s?k={encoded}"
    html = fetch_html(url)
    if not html:
        return []

    results: List[DealListing] = []
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

            link_node = title_node.find("a")
            href = link_node.get("href", "") if link_node else ""
            if href.startswith("/"):
                href = f"https://www.amazon.com{href}"

            # Price extraction
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
                    title=title[:90],
                    price=price_val,
                    shipping=0.0,
                    url=href or url,
                    meta={"rating": "Verified"}
                ))
            if len(results) >= max_results:
                break
    except Exception as exc:
        logger.debug(f"Amazon parse error: {exc}")
    return results


def search_newegg(query: str, max_results: int = 6) -> List[DealListing]:
    """Scrapes Newegg search results page."""
    encoded = quote_plus(query)
    url = f"https://www.newegg.com/p/pl?d={encoded}"
    html = fetch_html(url)
    if not html:
        return []

    results: List[DealListing] = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("div", {"class": "item-cell"})
        for item in items[:max_results * 2]:
            title_node = item.find("a", {"class": "item-title"})
            if not title_node:
                continue
            title = title_node.get_text(strip=True)
            href = title_node.get("href", "")

            # Price extraction
            price_strong = item.find("li", {"class": "price-current"})
            price_val = None
            if price_strong:
                price_val = parse_money(price_strong.get_text(strip=True))

            # Shipping
            ship_node = item.find("li", {"class": "price-ship"})
            ship_val = 0.0
            if ship_node:
                txt = ship_node.get_text(strip=True).lower()
                if "free" not in txt:
                    ship_val = parse_money(txt) or 0.0

            if price_val is not None:
                results.append(DealListing(
                    vendor="Newegg",
                    title=title[:90],
                    price=price_val,
                    shipping=ship_val,
                    url=href or url,
                    meta={"verified": True}
                ))
            if len(results) >= max_results:
                break
    except Exception as exc:
        logger.debug(f"Newegg parse error: {exc}")
    return results


def search_bestbuy(query: str, max_results: int = 6) -> List[DealListing]:
    """Scrapes Best Buy search results page."""
    encoded = quote_plus(query)
    url = f"https://www.bestbuy.com/site/searchpage.jsp?st={encoded}"
    html = fetch_html(url)
    if not html:
        return []

    results: List[DealListing] = []
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
            price_val = None
            if price_box:
                price_val = parse_money(price_box.get_text(strip=True))

            if price_val is not None:
                results.append(DealListing(
                    vendor="Best Buy",
                    title=title[:90],
                    price=price_val,
                    shipping=0.0,
                    url=href or url,
                    meta={"store_pickup": True}
                ))
            if len(results) >= max_results:
                break
    except Exception as exc:
        logger.debug(f"Best Buy parse error: {exc}")
    return results


def search_walmart(query: str, max_results: int = 6) -> List[DealListing]:
    """Scrapes Walmart search results page."""
    encoded = quote_plus(query)
    url = f"https://www.walmart.com/search?q={encoded}"
    html = fetch_html(url)
    if not html:
        return []

    results: List[DealListing] = []
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
            price_val = None
            if price_node:
                price_val = parse_money(price_node.get_text(strip=True))

            if price_val is not None:
                results.append(DealListing(
                    vendor="Walmart",
                    title=title[:90],
                    price=price_val,
                    shipping=0.0,
                    url=href or url,
                    meta={"walmart_direct": True}
                ))
            if len(results) >= max_results:
                break
    except Exception as exc:
        logger.debug(f"Walmart parse error: {exc}")
    return results


def search_bhphoto(query: str, max_results: int = 6) -> List[DealListing]:
    """Scrapes B&H Photo search page."""
    encoded = quote_plus(query)
    url = f"https://www.bhphotovideo.com/c/search?Ntt={encoded}"
    html = fetch_html(url)
    if not html:
        return []

    results: List[DealListing] = []
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
                    title=title[:90],
                    price=price_val,
                    shipping=0.0,
                    url=href or url,
                    meta={"authorized_dealer": True}
                ))
            if len(results) >= max_results:
                break
    except Exception as exc:
        logger.debug(f"BHPhoto parse error: {exc}")
    return results


def search_microcenter(query: str, max_results: int = 6) -> List[DealListing]:
    """Scrapes Micro Center search page."""
    encoded = quote_plus(query)
    url = f"https://www.microcenter.com/search/search_results.aspx?Ntt={encoded}"
    html = fetch_html(url)
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
            title = title_node.get_text(strip=True)
            href = title_node.get("href", "")
            if href.startswith("/"):
                href = f"https://www.microcenter.com{href}"

            price_node = item.find("span", {"itemprop": "price"})
            price_val = parse_money(price_node.get_text(strip=True)) if price_node else None

            if price_val is not None:
                results.append(DealListing(
                    vendor="Micro Center",
                    title=title[:90],
                    price=price_val,
                    shipping=0.0,
                    url=href or url,
                    meta={"in_store": True}
                ))
            if len(results) >= max_results:
                break
    except Exception as exc:
        logger.debug(f"Microcenter parse error: {exc}")
    return results


# ── UNIFIED DEAL SEARCH DISPATCHER ──────────────────────────────────────────

def search_deals(
    query: str,
    vendors: Optional[List[str]] = None,
    max_results_per_vendor: int = 6
) -> List[DealListing]:
    """
    Unified multi-vendor deal comparison across all major retailers.
    Results are sorted by total price ascending (best deal first).
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    chosen_vendors = [v.strip().lower() for v in (vendors or ["amazon", "newegg", "bestbuy", "walmart"])]
    all_listings: List[DealListing] = []

    # Parallel or sequential fetch
    if "amazon" in chosen_vendors:
        all_listings.extend(search_amazon(clean_query, max_results_per_vendor))
    if "newegg" in chosen_vendors:
        all_listings.extend(search_newegg(clean_query, max_results_per_vendor))
    if "bestbuy" in chosen_vendors:
        all_listings.extend(search_bestbuy(clean_query, max_results_per_vendor))
    if "walmart" in chosen_vendors:
        all_listings.extend(search_walmart(clean_query, max_results_per_vendor))
    if "bhphoto" in chosen_vendors:
        all_listings.extend(search_bhphoto(clean_query, max_results_per_vendor))
    if "microcenter" in chosen_vendors:
        all_listings.extend(search_microcenter(clean_query, max_results_per_vendor))

    # Sort by total price ascending, filtering out listings without price
    priced = [it for it in all_listings if it.total is not None and it.total > 0]
    return sorted(priced, key=lambda x: x.total)


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
            vendors=vendors or ["amazon", "newegg", "bestbuy", "walmart"],
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
