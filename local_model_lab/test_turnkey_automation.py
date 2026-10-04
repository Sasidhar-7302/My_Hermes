# -*- coding: utf-8 -*-
"""
Turnkey Automation Capabilities Test Suite
Verifies:
1. Smart Shutdown Engine (network-idle detection, user activity checks, config, status snapshot, start/cancel)
2. Multi-Vendor Deal Finder & DealWatchStore (money parsing, store persistence, search, alert triggers)
3. Multi-Channel Adapters (Policy manager, pairing codes, Discord, Slack, WhatsApp, Telegram, Universal Relay)
4. Operations Center Dashboard REST API endpoints for all 3 turnkey suites via FastAPI TestClient
"""

import sys
import os
import time
import tempfile
from pathlib import Path

# Ensure UTF-8 stdout
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_cur_dir = Path(__file__).resolve().parent
if str(_cur_dir) not in sys.path:
    sys.path.insert(0, str(_cur_dir))

# Add parent directory for top-level channels imports
_parent_dir = _cur_dir.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from smart_shutdown import (
    SmartShutdownConfig,
    SmartShutdownMonitor,
    get_smart_shutdown_monitor,
    get_user_idle_seconds,
)
from deal_finder import (
    DealListing,
    DealWatchStore,
    parse_money,
    search_deals,
    get_deal_watch_store,
)
from channels.policy import ChannelPolicyManager
from channels.discord import DiscordGateway
from channels.slack import SlackGateway
from channels.whatsapp import WhatsAppGateway
from channels.telegram import TelegramGateway
from channels.relay import RelayGateway
from channels import (
    get_all_channel_statuses,
    get_channel_policy_manager,
    get_discord_gateway,
    get_slack_gateway,
    get_whatsapp_gateway,
    get_telegram_gateway,
    get_relay_gateway,
)

import company_dashboard as cd
from starlette.testclient import TestClient


def run_tests():
    print("=" * 80)
    print("  HERMES TURNKEY AUTOMATION CAPABILITIES TEST SUITE")
    print("=" * 80)
    passed = 0
    total = 0

    # -------------------------------------------------------------------------
    # TEST 1: Smart Shutdown Engine
    # -------------------------------------------------------------------------
    total += 1
    print("\n[TEST 1] Testing Smart Shutdown Engine...")
    cfg = SmartShutdownConfig(
        idle_minutes=15,
        idle_kbps=20.0,
        active_kbps=100.0,
        action="sleep",
        sample_seconds=1,
        countdown_seconds=5,
    )
    assert cfg.idle_minutes == 15
    assert cfg.action == "sleep"

    idle_sec = get_user_idle_seconds()
    assert isinstance(idle_sec, (float, int))
    assert idle_sec >= 0.0
    print(f"  ✓ User idle seconds detected: {idle_sec:.2f}s")

    monitor = get_smart_shutdown_monitor()
    status = monitor.snapshot()
    assert "running" in status
    assert "status" in status
    assert "action" in status
    assert "user_idle_seconds" in status
    print(f"  ✓ Status snapshot retrieved: running={status['running']}, status={status['status']}")

    # Start monitor and cancel
    ok, msg = monitor.start(cfg)
    assert ok is True
    time.sleep(0.5)
    st = monitor.snapshot()
    assert st["running"] is True
    ok_cancel, cancel_msg = monitor.cancel()
    assert ok_cancel is True
    time.sleep(0.2)
    assert monitor.snapshot()["running"] is False
    print("  ✓ Start & Cancel workflow executed cleanly.")
    passed += 1

    # -------------------------------------------------------------------------
    # TEST 2: Deal Finder & DealWatchStore
    # -------------------------------------------------------------------------
    total += 1
    print("\n[TEST 2] Testing Deal Finder & Watch Store...")
    assert parse_money("$149.99") == 149.99
    assert parse_money("USD 2,499.00") == 2499.0
    assert parse_money("invalid text") is None
    print("  ✓ Price parser regex verified across currency formats.")

    dl = DealListing(
        vendor="Amazon",
        title="RTX 4090 OC 24GB",
        price=1599.99,
        shipping=0.0,
        url="https://amazon.com/dp/B0TEST",
        meta={"rating": "4.8/5", "availability": "In Stock"},
    )
    assert dl.vendor == "Amazon"
    assert dl.total == 1599.99

    # Use a temporary file for DealWatchStore testing
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_store_file = Path(tmpdir) / "test_watches.json"
        store = DealWatchStore(filepath=tmp_store_file)
        assert len(store.list_watches()) == 0

        # Add watch
        w = store.add_watch(query="RTX 4080 Super", target_price=950.0, vendors=["amazon", "newegg"])
        assert w.target_price == 950.0
        assert len(store.list_watches()) == 1
        print(f"  ✓ Added watch for '{w.query}' targeting ${w.target_price:.2f}")

        # Check watch with mock listings
        import deal_finder
        orig_search = deal_finder.search_deals
        try:
            deal_finder.search_deals = lambda q, vendors=None, max_results_per_vendor=4: [
                DealListing(
                    vendor="Newegg",
                    title="RTX 4080 Super OC Edition",
                    price=899.99,
                    shipping=0.0,
                    url="https://newegg.com/p/TEST",
                )
            ]
            res = store.check_watch(w.id)
            assert res is not None
            assert res["triggered_alert"] is True
            assert res["best_deal"]["total"] == 899.99
            print(f"  ✓ Target price hit triggered alert! Price dropped to ${res['best_deal']['total']:.2f}")
        finally:
            deal_finder.search_deals = orig_search

        # Remove watch
        removed = store.remove_watch(w.id)
        assert removed is True
        assert len(store.list_watches()) == 0
        print("  ✓ Watch removal and store state persistence verified.")

    passed += 1

    # -------------------------------------------------------------------------
    # TEST 3: Multi-Channel Policy Manager & Pairing
    # -------------------------------------------------------------------------
    total += 1
    print("\n[TEST 3] Testing Multi-Channel Policy & Connectors...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_policy_file = Path(tmpdir) / "test_policy.json"
        pm = ChannelPolicyManager(filepath=tmp_policy_file)

        # Unapproved user check
        assert pm.is_allowed("telegram", "user_12345") is False

        # Generate pairing request
        code = pm.request_pairing_code("telegram", "user_12345")
        assert len(code) == 6
        assert code.isdigit()
        print(f"  ✓ Generated 6-digit numeric pairing code: {code}")

        # Invalid code approval
        assert pm.approve_pairing_code("telegram", "000000") is None

        # Valid code approval
        approved_user = pm.approve_pairing_code("telegram", code)
        assert approved_user == "user_12345"
        assert pm.is_allowed("telegram", "user_12345") is True
        print(f"  ✓ Approved pairing code successfully added {approved_user} to allowlist.")

    # Test individual channel connector status & handling
    statuses = get_all_channel_statuses()
    assert "discord" in statuses
    assert "slack" in statuses
    assert "whatsapp" in statuses
    assert "telegram" in statuses
    assert "relay" in statuses
    assert "policy" in statuses
    print("  ✓ Channel status aggregation verified across 5 connectors.")

    # Test individual channel connector status & configuration
    discord = get_discord_gateway()
    assert discord.get_status()["channel"] == "discord"
    print("  ✓ Discord Gateway status verified.")

    slack = get_slack_gateway()
    assert slack.get_status()["channel"] == "slack"
    print("  ✓ Slack Gateway status verified.")

    whatsapp = get_whatsapp_gateway()
    assert whatsapp.get_status()["channel"] == "whatsapp"
    print("  ✓ WhatsApp Gateway status verified.")

    telegram = get_telegram_gateway()
    assert telegram.get_status()["channel"] == "telegram"
    print("  ✓ Telegram Gateway status verified.")

    relay = get_relay_gateway()
    assert relay.get_status()["channel"] == "relay"
    print("  ✓ Universal Webhook Relay status verified.")

    passed += 1

    # -------------------------------------------------------------------------
    # TEST 4: Company Dashboard REST Endpoints via TestClient
    # -------------------------------------------------------------------------
    total += 1
    print("\n[TEST 4] Testing Dashboard REST Endpoints & UI Rendering...")
    client = TestClient(cd.app)

    # 1. UI Root check
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "Smart Shutdown" in html
    assert "Deal Finder" in html
    assert "Multi-Channel" in html
    assert "tab-shutdown" in html
    assert "tab-deals" in html
    assert "tab-channels" in html
    print("  ✓ Dashboard HTML contains all 3 turnkey automation tabs.")

    # 2. Smart Shutdown endpoints
    r = client.get("/api/shutdown/status")
    assert r.status_code == 200
    data = r.json()
    assert "running" in data
    assert "status" in data

    r = client.post("/api/shutdown/start", json={"idle_minutes": 20, "action": "sleep"})
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

    r = client.post("/api/shutdown/cancel")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
    print("  ✓ /api/shutdown/* endpoints verified.")

    # 3. Deal Finder endpoints
    r = client.get("/api/deals/watches")
    assert r.status_code == 200
    data = r.json()
    assert "watches" in data

    r = client.post("/api/deals/watches/add", json={"query": "Mechanical Keyboard", "target_price": 79.99, "vendors": ["amazon"]})
    assert r.status_code == 200
    added = r.json()
    assert added.get("status") == "ok"
    assert "watch" in added
    watch_id = added["watch"]["id"]

    r = client.post("/api/deals/watches/remove", json={"watch_id": watch_id})
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
    print("  ✓ /api/deals/* endpoints verified.")

    # 4. Multi-Channel endpoints
    r = client.get("/api/channels/status")
    assert r.status_code == 200
    c_status = r.json()
    assert "discord" in c_status
    assert "slack" in c_status
    assert "whatsapp" in c_status
    assert "telegram" in c_status
    assert "relay" in c_status

    r = client.post("/api/channels/simulate_test", json={"channel": "discord", "user_id": "test_dev", "prompt": "hello test"})
    assert r.status_code == 200
    assert "response" in r.json()
    print("  ✓ /api/channels/* endpoints verified.")

    passed += 1

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"  ALL TURNKEY TESTS PASSED: {passed}/{total} (100%)")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_tests()
    if not success:
        sys.exit(1)
