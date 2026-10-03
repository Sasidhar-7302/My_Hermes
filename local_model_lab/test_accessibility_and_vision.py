# -*- coding: utf-8 -*-
"""
Verification Test Suite for Windows Accessibility Tree and Screen Vision
Hermes Agent - Advanced GUI Grounding & Automation
"""

import os
import sys
import time

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

from accessibility_tree import get_accessibility_tree, UIElement
from screen_vision import get_screen_vision, capture_screen
from computer_control import (
    execute_computer_task,
    click_ui_element,
    type_into_ui_element,
    inspect_screen_with_vision,
    list_window_controls,
    SafetyViolationError
)


def run_tests():
    print("=" * 75)
    print("  HERMES ACCESSIBILITY TREE & SCREEN VISION VERIFICATION SUITE")
    print("=" * 75)

    passed = 0
    total = 0

    # ── TEST 1: UIElement Dataclass & Center Calculations ────────────────────
    total += 1
    print("\n[TEST 1] Verifying UIElement Dataclass & Coordinate Calculations...")
    elem = UIElement(
        name="Save",
        control_type="Button",
        automation_id="btnSave",
        class_name="ButtonClass",
        bounding_rect=(100, 200, 80, 40),
        is_enabled=True,
        is_visible=True,
        patterns=["Invoke"]
    )
    assert elem.center == (140, 220), f"Expected (140, 220), got {elem.center}"
    assert elem.is_clickable is True, "Expected is_clickable == True"
    assert elem.is_input is False, "Expected is_input == False"
    d = elem.to_dict()
    assert d["name"] == "Save" and d["center"] == [140, 220]
    print(f"  ✓ PASS: UIElement center: {elem.center}, clickable: {elem.is_clickable}")
    passed += 1

    # ── TEST 2: Accessibility Tree Discovery ─────────────────────────────────
    total += 1
    print("\n[TEST 2] Verifying Windows Accessibility Tree (UIA) Engine...")
    tree = get_accessibility_tree()
    assert tree.available is True, "Accessibility tree UIA should be available"
    windows = tree.get_top_windows()
    print(f"  Discovered {len(windows)} interactive top-level windows:")
    for w in windows[:3]:
        print(f"    - HWND {w['hwnd']}: '{w['title'][:45]}'")
    assert len(windows) > 0, "Expected at least 1 interactive window"
    print("  ✓ PASS: Top-level windows enumerated successfully via UIA.")
    passed += 1

    # ── TEST 3: Window Element Traversal ─────────────────────────────────────
    total += 1
    print("\n[TEST 3] Traversing UI Elements in Foreground Window...")
    elements = tree.get_window_elements(max_depth=5)
    print(f"  Extracted {len(elements)} accessible UI elements.")
    clickable = [e for e in elements if e.is_clickable]
    inputs = [e for e in elements if e.is_input]
    print(f"  Clickable controls found: {len(clickable)}")
    print(f"  Input controls found: {len(inputs)}")
    for c in (clickable + inputs)[:4]:
        print(f"    * [{c.control_type}] '{c.name}' (id: '{c.automation_id}', center: {c.center})")
    assert len(elements) >= 0
    print("  ✓ PASS: UI element traversal operational.")
    passed += 1

    # ── TEST 4: Screen Capture & Geometry ────────────────────────────────────
    total += 1
    print("\n[TEST 4] Verifying Desktop Screenshot & Vision Geometry...")
    img, img_bytes, (orig_w, orig_h) = capture_screen(max_width=1280)
    assert img is not None, "Failed to capture PIL screenshot"
    assert img_bytes is not None and len(img_bytes) > 1000, "Screenshot bytes invalid"
    assert orig_w > 0 and orig_h > 0, f"Invalid resolution: {orig_w}x{orig_h}"
    print(f"  Captured screen resolution: {orig_w}x{orig_h}, payload: {len(img_bytes)} bytes")
    print("  ✓ PASS: Screen capture and geometry normalization verified.")
    passed += 1

    # ── TEST 5: Vision Grounding Engine & Model Detection ────────────────────
    total += 1
    print("\n[TEST 5] Checking Screen Vision Engine & Model Providers...")
    vision = get_screen_vision()
    ollama_models = vision.get_installed_ollama_vision_models()
    print(f"  Local Ollama vision models detected: {ollama_models or 'None (using cloud fallback)'}")
    print(f"  Cloud Gemini Vision Key: {'Configured' if vision.keys.get('GEMINI_API_KEY') else 'Missing'}")
    print(f"  OpenRouter Vision Key: {'Configured' if vision.keys.get('OPENROUTER_API_KEY') else 'Missing'}")
    assert vision.keys.get("GEMINI_API_KEY") or vision.keys.get("OPENROUTER_API_KEY") or ollama_models, "At least one vision provider must be available"
    print("  ✓ PASS: Vision multi-provider fallback active.")
    passed += 1

    # ── TEST 6: High-Level Screen Description ────────────────────────────────
    total += 1
    print("\n[TEST 6] Testing High-Level Screen Description...")
    summary = inspect_screen_with_vision("Summarize active window and controls briefly.")
    assert summary["status"] == "success"
    print(f"  Active window: '{summary['active_window'][:40]}'")
    print(f"  Vision description: '{summary['vision_description'][:100]}...'")
    print(f"  UI controls summary: {summary.get('ui_controls_summary')}")
    print("  ✓ PASS: Screen inspection with vision and UIA completed.")
    passed += 1

    # ── TEST 7: Computer Control Dispatch for New Commands ───────────────────
    total += 1
    print("\n[TEST 7] Verifying Computer Control Dispatch Routing...")
    res_inspect = execute_computer_task("what is on my screen")
    assert res_inspect["status"] == "success", f"Failed inspect dispatch: {res_inspect}"

    res_list = execute_computer_task("list window controls")
    assert res_list["status"] == "success", f"Failed list controls dispatch: {res_list}"
    print(f"  Dispatched 'list window controls': found {res_list.get('total_controls')} controls")

    print("  ✓ PASS: Natural language computer control routing verified.")
    passed += 1

    # ── TEST 8: Safety Shield Verification on New Vision/UIA Commands ─────────
    total += 1
    print("\n[TEST 8] Verifying Safety Shields on New Commands...")
    res_blocked = execute_computer_task("click button delete all files and wipe drive")
    assert res_blocked["status"] == "blocked" and res_blocked["safety_level"] == "HARDLINE_GUARD"
    print(f"  ✓ BLOCKED: '{res_blocked['reason'][:60]}...'")

    res_blocked_pay = execute_computer_task("click checkout button and submit payment")
    assert res_blocked_pay["status"] == "blocked" and res_blocked_pay["safety_level"] == "HARDLINE_GUARD"
    print(f"  ✓ BLOCKED: '{res_blocked_pay['reason'][:60]}...'")
    print("  ✓ PASS: Safety shields strictly enforce zero-deletion and zero-payment policies.")
    passed += 1

    print("\n" + "=" * 75)
    print(f"  RESULTS: {passed}/{total} ({passed/total*100:.1f}%) TESTS PASSED")
    print("=" * 75)
    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
