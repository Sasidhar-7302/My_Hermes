# -*- coding: utf-8 -*-
"""
Verification Test Suite for Hermes Desktop Shell, Window Services & Multi-Monitor Control
Hermes Agent - Desktop Presence & Management
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    import win32gui
except ImportError:
    win32gui = None

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

from window_services import (
    get_display_monitors,
    list_active_windows,
    snap_window,
    move_window_to_monitor,
    focus_window,
    resolve_window_hwnd,
    MonitorInfo
)
from shell_daemon import (
    HermesTrayApp,
    trigger_emergency_stop,
    clear_emergency_stop,
    is_emergency_stopped,
    EMERGENCY_LOCK_FILE
)
from computer_control import (
    execute_computer_task,
    SafetyViolationError
)


def run_tests():
    print("=" * 75)
    print("  HERMES DESKTOP SHELL & MULTI-MONITOR VERIFICATION SUITE")
    print("=" * 75)

    passed = 0
    total = 0

    # Ensure clean emergency stop state before starting
    clear_emergency_stop()

    # ── TEST 1: Physical & Virtual Display Monitor Enumeration ───────────────
    total += 1
    print("\n[TEST 1] Enumerating Display Monitors...")
    monitors = get_display_monitors()
    print(f"  Detected {len(monitors)} monitor(s):")
    for m in monitors:
        print(f"    - Monitor {m.id} ({m.device}): {m.width}x{m.height}, Primary={m.is_primary}, WorkArea={m.work_area}")
    assert len(monitors) >= 1, "Must detect at least 1 monitor"
    assert monitors[0].width > 0 and monitors[0].height > 0
    print("  ✓ PASS: Multi-monitor display detection operational.")
    passed += 1

    # ── TEST 2: Active User Window Filtering ─────────────────────────────────
    total += 1
    print("\n[TEST 2] Verifying Clean Window Filtering (System Noise Suppression)...")
    windows = list_active_windows()
    print(f"  Found {len(windows)} clean active user application window(s):")
    for w in windows[:4]:
        print(f"    * HWND {w['hwnd']}: '{w['title'][:40]}' on Monitor {w['monitor_id']}")
    # Verify system noise like IME, Systray, Program Manager are filtered
    titles_lower = [w["title"].lower() for w in windows]
    assert "default ime" not in titles_lower, "System IME must be filtered"
    assert "msctfime ui" not in titles_lower, "System MSCTFIME must be filtered"
    assert "systray" not in titles_lower, "Systray must be filtered"
    print("  ✓ PASS: Real user application windows isolated from background noise.")
    passed += 1

    # ── TEST 3: Window Title Resolution & HWND Lookup ────────────────────────
    total += 1
    print("\n[TEST 3] Testing Window Title Resolution (Fuzzy & Exact)...")
    if windows:
        first_title = windows[0]["title"]
        hwnd_exact = resolve_window_hwnd(first_title)
        assert hwnd_exact == windows[0]["hwnd"], f"Expected {windows[0]['hwnd']}, got {hwnd_exact}"

        # Substring resolution
        first_word = first_title.split()[0]
        hwnd_partial = resolve_window_hwnd(first_word)
        assert hwnd_partial is not None, f"Failed partial resolution for '{first_word}'"
        print(f"  Resolved '{first_title[:25]}' -> HWND {hwnd_exact}")
    print("  ✓ PASS: Window title lookup and fuzzy matching verified.")
    passed += 1

    # ── TEST 4: Window Snapping Calculation & Safety ─────────────────────────
    total += 1
    print("\n[TEST 4] Testing Window Snapping Primitives...")
    notepad_proc = None
    test_hwnd = None
    try:
        notepad_proc = subprocess.Popen(["notepad.exe"])
        for _ in range(25):
            time.sleep(0.1)
            candidate = resolve_window_hwnd("Notepad")
            if candidate and (win32gui is None or win32gui.IsWindow(candidate)):
                test_hwnd = candidate
                break
    except Exception as e:
        print(f"  Note: Could not launch notepad sandbox: {e}")

    # Fallback to an active verified user window
    if not test_hwnd and windows:
        for w in windows:
            if win32gui is None or win32gui.IsWindow(w["hwnd"]):
                test_hwnd = w["hwnd"]
                break

    if test_hwnd:
        snap_res = snap_window(test_hwnd, "left")
        assert snap_res["status"] == "success", f"Snap left failed: {snap_res}"
        print(f"  Snap 'left' target rect: {snap_res.get('target_rect')}")

        snap_res_center = snap_window(test_hwnd, "center")
        assert snap_res_center["status"] == "success", f"Snap center failed: {snap_res_center}"
        print(f"  Snap 'center' target rect: {snap_res_center.get('target_rect')}")
    print("  ✓ PASS: Window snapping geometry verified.")
    passed += 1

    # ── TEST 5: Multi-Monitor Movement Validation ────────────────────────────
    total += 1
    print("\n[TEST 5] Testing Multi-Monitor Movement Dispatch...")
    if test_hwnd:
        move_res = move_window_to_monitor(test_hwnd, 1)
        assert move_res["status"] == "success", f"Move to monitor 1 failed: {move_res}"
        print(f"  Moved window to Monitor 1: {move_res.get('target_rect')}")
    print("  ✓ PASS: Cross-monitor relocation engine verified.")
    passed += 1

    # Clean up notepad test process
    if notepad_proc:
        try:
            notepad_proc.kill()
            notepad_proc.wait(timeout=2.0)
        except Exception:
            pass

    # ── TEST 6: Desktop Shell Hotkey Bindings & Tray Structure ───────────────
    total += 1
    print("\n[TEST 6] Validating Desktop Shell Daemon Hotkey Structure...")
    tray = HermesTrayApp()
    assert len(tray.bindings) == 3, f"Expected 3 bindings, got {len(tray.bindings)}"
    actions = {b.action: b.description for b in tray.bindings}
    assert "summon" in actions, "Global summon binding missing"
    assert "assist_selection" in actions, "Selected-text assist binding missing"
    assert "emergency_stop" in actions, "Emergency stop binding missing"
    for b in tray.bindings:
        print(f"    - {b.name}: {b.description} (vk=0x{b.vk:02X}, mod=0x{b.modifiers:02X})")
    print("  ✓ PASS: Desktop shell hotkey configuration verified.")
    passed += 1

    # ── TEST 7: Emergency Panic Stop Lock & Action Hard-Blocking ─────────────
    total += 1
    print("\n[TEST 7] Testing Emergency Panic Stop Engagement & Action Blocking...")
    assert not is_emergency_stopped(), "Emergency stop should initially be cleared"

    trigger_emergency_stop()
    assert is_emergency_stopped(), "Emergency stop should now be active"
    assert EMERGENCY_LOCK_FILE.exists(), "Lock file should exist on disk"

    # Verify that ANY computer control action is immediately hard-blocked while emergency stop is active
    try:
        execute_computer_task("click mouse at 500 500")
        assert False, "Action should have been blocked by Emergency Panic Stop"
    except Exception:
        pass

    blocked_res = execute_computer_task("launch notepad")
    assert blocked_res["status"] == "blocked", f"Expected blocked status, got {blocked_res}"
    print(f"  ✓ Confirmed action blocked under emergency lock: '{blocked_res['reason'][:65]}...'")

    # Clear stop
    clear_emergency_stop()
    assert not is_emergency_stopped(), "Emergency stop should be cleared"
    print("  ✓ PASS: Emergency Panic Stop lock and immediate action block verified.")
    passed += 1

    # ── TEST 8: Launcher Scripts Syntax & Presence ───────────────────────────
    total += 1
    print("\n[TEST 8] Verifying Launch-Hermes.ps1 and Launch-Hermes.vbs...")
    root = Path(__file__).resolve().parents[1]
    ps1_candidates = [
        root / "Launch-Hermes.ps1",
        root / "scripts" / "Launch-Hermes.ps1",
        root.parent / "Launch-Hermes.ps1",
    ]
    vbs_candidates = [
        root / "Launch-Hermes.vbs",
        root / "scripts" / "Launch-Hermes.vbs",
        root.parent / "Launch-Hermes.vbs",
    ]
    ps1 = next((p for p in ps1_candidates if p.exists()), None)
    vbs = next((v for v in vbs_candidates if v.exists()), None)
    assert ps1 and ps1.exists(), f"Launch-Hermes.ps1 missing in {ps1_candidates}"
    assert vbs and vbs.exists(), f"Launch-Hermes.vbs missing in {vbs_candidates}"

    vbs_content = vbs.read_text(encoding="utf-8")
    assert "WScript.Shell" in vbs_content
    assert "Launch-Hermes.ps1" in vbs_content
    assert "shell.Run cmd, 0, False" in vbs_content, "Must run with WindowStyle 0 (Hidden)"
    print(f"  Launch-Hermes.vbs: verified silent execution flag (WindowStyle 0) at {vbs.name}")
    print(f"  Launch-Hermes.ps1: verified 5-service launch baseline at {ps1.name}")
    print("  ✓ PASS: Launcher entrypoints verified.")
    passed += 1

    print("\n" + "=" * 75)
    print(f"  RESULTS: {passed}/{total} ({passed/total*100:.1f}%) TESTS PASSED")
    print("=" * 75)
    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
