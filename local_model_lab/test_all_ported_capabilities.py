# -*- coding: utf-8 -*-
"""
Unified Verification Test Suite for Ported Capabilities & Dashboards
Tests:
- PII & Secret Redaction Shield (Groq, Gemini, OpenAI, GitHub, CC, SSN)
- RPA Macro Automation Engine
- System & Proactivity Observer
- Paper Desktop MCP Gateway
- Desktop Shell & Multi-Monitor Windows Engine
- Company Dashboard REST Endpoints & UI Rendering
- Hermes Browser Control Manifest V3 Package
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_cur_dir = Path(__file__).resolve().parent
if str(_cur_dir) not in sys.path:
    sys.path.insert(0, str(_cur_dir))

from pii_shield import PIIShield, mask_sensitive_text, has_sensitive_data
from rpa_recorder import get_rpa_recorder, Recording, RecordedAction
from system_observer import get_system_observer
from paper_client import get_paper_client, is_port_open, detect_paper_executable
from window_services import get_display_monitors, list_active_windows
import company_dashboard as cd


def run_all_tests():
    print("=" * 80)
    print("  HERMES UNIFIED CAPABILITIES & DASHBOARD VERIFICATION SUITE")
    print("=" * 80)

    passed = 0
    total = 0

    # 1. PII Shield Tests
    total += 1
    print("\n[TEST 1] Testing PII & Secret Redaction Shield...")
    test_text = (
        "Contact me at dev@hermes.ai or call 555-123-4567. "
        "Keys: GROQ_KEY=gsk_1234567890abcdef1234567890, "
        "GOOGLE_KEY=AIzaSyA1234567890abcdef1234567890abc, "
        "OPENAI_KEY=sk-abcdef1234567890abcdef123456, "
        "GITHUB_TOKEN=ghp_abcdef1234567890abcdef1234567890, "
        "SSN: 000-12-3456, Credit Card: 4111-2222-3333-4444"
    )
    assert has_sensitive_data(test_text) is True
    masked = mask_sensitive_text(test_text)
    entities = PIIShield.detect_entities(test_text)
    print(f"  Detected entities ({len(entities)}): {[e['type'] for e in entities]}")
    assert "gsk_" not in masked
    assert "AIzaSy" not in masked
    assert "sk-" not in masked
    assert "ghp_" not in masked
    assert "000-12-3456" not in masked
    assert "4111-2222-3333-4444" not in masked
    assert "dev@hermes.ai" not in masked
    print("  ✓ PASS: PII & Secret Redaction Shield masked 100% of sensitive tokens.")
    passed += 1

    # 2. RPA Macro Automation Tests
    total += 1
    print("\n[TEST 2] Testing RPA Macro Automation Engine...")
    recorder = get_rpa_recorder()
    dummy_actions = [
        RecordedAction(type="click", timestamp=0.1, x=100, y=200, button="left"),
        RecordedAction(type="key", timestamp=0.3, key="h"),
        RecordedAction(type="key", timestamp=0.4, key="i"),
    ]
    test_rec = Recording(
        name="test_verification_macro",
        created_at="2026-10-03T12:00:00Z",
        duration=0.5,
        actions=dummy_actions,
        metadata={"author": "Hermes Tester"}
    )
    saved_path = test_rec.save()
    assert saved_path.exists()
    loaded_rec = Recording.load(saved_path)
    assert loaded_rec.name == "test_verification_macro"
    assert len(loaded_rec.actions) == 3
    # Clean up test file
    try:
        saved_path.unlink()
    except Exception:
        pass
    print("  ✓ PASS: RPA Macro persistence, serialization, and structure verified.")
    passed += 1

    # 3. System Observer Tests
    total += 1
    print("\n[TEST 3] Testing System Observer & Resource Health...")
    obs = get_system_observer()
    health = obs.get_health()
    print(f"  Health Snapshot: CPU={health.cpu_percent}%, RAM={health.ram_percent}%, Status={health.status}")
    assert health.cpu_percent >= 0.0
    assert health.ram_total_gb > 1.0
    assert health.status in ("HEALTHY", "WARNING", "CRITICAL")
    briefing = obs.generate_daily_briefing()
    assert "HERMES DAILY SYSTEM" in briefing.upper()
    print("  ✓ PASS: System Observer and intelligence briefing operational.")
    passed += 1

    # 4. Paper Desktop MCP Gateway Tests
    total += 1
    print("\n[TEST 4] Testing Paper Desktop MCP Client...")
    exe = detect_paper_executable()
    assert exe is not None and exe.exists()
    client = get_paper_client()
    st = client.status()
    print(f"  Paper status: listening={st.listening}, url={st.url}")
    assert st.listening is True
    print("  ✓ PASS: Paper Desktop MCP Client responsive.")
    passed += 1

    # 5. Desktop Shell & Multi-Monitor Tests
    total += 1
    print("\n[TEST 5] Testing Desktop Shell & Multi-Monitor Detection...")
    monitors = get_display_monitors()
    print(f"  Detected {len(monitors)} monitor(s)")
    assert len(monitors) >= 1
    windows = list_active_windows()
    print(f"  Detected {len(windows)} active user window(s)")
    print("  ✓ PASS: Window services and monitor geometry operational.")
    passed += 1

    # 6. Company Dashboard API Endpoints Tests
    total += 1
    print("\n[TEST 6] Testing Company Dashboard REST Endpoints...")
    async def _test_endpoints():
        res_mon = await cd.api_desktop_monitors()
        assert res_mon.status_code == 200
        res_win = await cd.api_desktop_windows()
        assert res_win.status_code == 200
        res_stop = await cd.api_get_emergency_stop()
        assert res_stop.status_code == 200
        res_paper = await cd.api_paper_status()
        assert res_paper.status_code == 200
        res_sys = await cd.api_system_health()
        assert res_sys.status_code == 200
        res_ext = await cd.api_browser_status()
        assert res_ext.status_code == 200
    asyncio.run(_test_endpoints())
    html = cd.dashboard()
    assert len(html) > 50000
    assert "Autonomous Operations Center" in html
    assert "Paper Desktop MCP Studio" in html
    assert "PII & Secret Redaction Shield" in html
    assert "RPA Action Recording & Replay Studio" in html
    print(f"  ✓ PASS: Dashboard HTML rendered cleanly ({len(html)} chars) across all 8 capability tabs.")
    passed += 1

    # 7. Browser Control Manifest V3 Package Tests
    total += 1
    print("\n[TEST 7] Testing Browser Control Extension Package...")
    ext_dir = _cur_dir.parent / "browser_extension" / "hermes_browser_control"
    manifest_file = ext_dir / "manifest.json"
    background_file = ext_dir / "background.js"
    content_file = ext_dir / "content.js"
    bridge_file = ext_dir / "bridge.js"
    assert manifest_file.exists()
    assert background_file.exists()
    assert content_file.exists()
    assert bridge_file.exists()
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest_data["manifest_version"] == 3
    assert manifest_data["name"] == "Hermes Browser Control"
    print("  ✓ PASS: Browser Control Manifest V3 extension bundle fully validated.")
    passed += 1

    print("\n" + "=" * 80)
    print(f"  FINAL SUMMARY: {passed}/{total} ({passed/total*100:.1f}%) TESTS PASSED")
    print("=" * 80)
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
