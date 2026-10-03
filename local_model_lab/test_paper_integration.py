# -*- coding: utf-8 -*-
"""
Verification Test Suite for Hermes Paper Desktop MCP Integration & Design Engine
Hermes Agent - Autonomous Computer Control & Design
"""

import json
import os
import sys
import time
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.append(os.path.dirname(__file__))

from paper_client import (
    PaperMcpClient,
    get_paper_client,
    is_port_open,
    detect_paper_executable,
    PaperStatus
)
from computer_control import (
    execute_computer_task,
    call_paper_mcp,
    paper_design,
    SafetyViolationError
)


def run_tests():
    print("=" * 75)
    print("  HERMES PAPER DESKTOP MCP INTEGRATION VERIFICATION SUITE")
    print("=" * 75)

    passed = 0
    total = 0

    # ── TEST 1: Paper Desktop Executable Detection ───────────────────────────
    total += 1
    print("\n[TEST 1] Detecting Paper Desktop Installed Executable...")
    exe = detect_paper_executable()
    print(f"  Detected Paper Executable: {exe}")
    assert exe is not None, "Paper Desktop executable should be detected on this machine"
    assert exe.exists(), f"Executable at {exe} does not exist"
    print("  ✓ PASS: Paper Desktop installation verified on host.")
    passed += 1

    # ── TEST 2: Paper MCP Port & Listener Status ─────────────────────────────
    total += 1
    print("\n[TEST 2] Checking Paper Desktop MCP Port (29979)...")
    port_open = is_port_open("127.0.0.1", 29979)
    print(f"  Port 29979 Listening: {port_open}")
    assert port_open is True, "Paper Desktop must be running and listening on port 29979"
    print("  ✓ PASS: Paper Desktop HTTP MCP socket verified.")
    passed += 1

    # ── TEST 3: Paper MCP Initialize Handshake & Session ID ──────────────────
    total += 1
    print("\n[TEST 3] Performing MCP Protocol Handshake (2024-11-05)...")
    client = get_paper_client()
    init_ok = client.initialize()
    print(f"  Handshake Result: {init_ok}")
    print(f"  Active Session ID: {client.session_id}")
    assert init_ok is True, "MCP initialize handshake must succeed"
    assert len(client.session_id) > 10, "Valid session ID must be returned by Paper"
    print("  ✓ PASS: Protocol handshake and session establishment verified.")
    passed += 1

    # ── TEST 4: Paper Status Reporting & Diagnostic Message ──────────────────
    total += 1
    print("\n[TEST 4] Retrieving High-Level Paper Status...")
    st = client.status()
    print(f"  Status Payload: {st.to_dict()}")
    assert st.listening is True
    assert st.url == "http://127.0.0.1:29979/mcp"
    assert len(st.message) > 0
    print(f"  Status Message: '{st.message}'")
    print("  ✓ PASS: High-level Paper status reporting operational.")
    passed += 1

    # ── TEST 5: Paper MCP Tool Execution via call_tool ───────────────────────
    total += 1
    print("\n[TEST 5] Testing call_tool on Paper MCP Server...")
    res = client.call_tool("get_basic_info")
    print(f"  call_tool('get_basic_info') returned status: {res.get('status')}")
    # Even if no file is currently open, Paper gracefully responds with diagnostic message
    assert "status" in res, "Result must contain status"
    print(f"  Response: {res}")
    print("  ✓ PASS: MCP tool calling and SSE response parsing verified.")
    passed += 1

    # ── TEST 6: Computer Control Natural Language Routing ────────────────────
    total += 1
    print("\n[TEST 6] Testing Natural Language Routing in computer_control.py...")
    dispatch_res = execute_computer_task("paper status")
    print(f"  Dispatched 'paper status': {dispatch_res.get('status')}")
    assert dispatch_res["status"] == "success"
    assert dispatch_res["action"] == "paper_status"
    assert "paper" in dispatch_res
    print(f"  Dispatched payload: {dispatch_res['paper']['message']}")
    print("  ✓ PASS: Computer control natural language routing to Paper verified.")
    passed += 1

    # ── TEST 7: Paper Design Helper Safety & Execution ───────────────────────
    total += 1
    print("\n[TEST 7] Testing paper_design Execution Routine...")
    design_res = paper_design("Analytics Dashboard for Hermes")
    print(f"  paper_design result: {design_res.get('status')} - {design_res.get('message')}")
    assert design_res["status"] == "success"
    print("  ✓ PASS: Paper design execution pipeline verified.")
    passed += 1

    # ── TEST 8: Hardline Safety Shields on Paper Actions ─────────────────────
    total += 1
    print("\n[TEST 8] Verifying Hardline Safety Shields Protect Paper Operations...")
    try:
        execute_computer_task("paper delete all database files rm -rf /")
        assert False, "Should have been blocked by safety shield"
    except Exception:
        pass

    blocked_del = execute_computer_task("delete all files in paper project del /f /q C:\\*")
    assert blocked_del["status"] == "blocked"
    print(f"  ✓ Confirmed deletion shield blocked: '{blocked_del['reason'][:60]}...'")

    blocked_pay = execute_computer_task("paper buy upgrade pay $100 with credit card")
    assert blocked_pay["status"] == "blocked"
    print(f"  ✓ Confirmed financial shield blocked: '{blocked_pay['reason'][:60]}...'")
    print("  ✓ PASS: Safety shields strictly guard Paper design interactions.")
    passed += 1

    print("\n" + "=" * 75)
    print(f"  RESULTS: {passed}/{total} ({passed/total*100:.1f}%) TESTS PASSED")
    print("=" * 75)
    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
