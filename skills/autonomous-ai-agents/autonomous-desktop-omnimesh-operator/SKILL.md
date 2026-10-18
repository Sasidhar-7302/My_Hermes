---
name: autonomous-desktop-omnimesh-operator
description: Use when automating Windows desktop apps, multi-monitor windows, Chintu Chrome browser, media keys, RPA macros, or OmniMesh companions.
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    role: OPERATOR
    toolset: role_operator
    mcp_servers: [hermes-desktop, paper, laya]
    tags: [operator, desktop-control, window-manager, chintu-browser, omnimesh, rpa, screen-vision]
    related_skills: [computer-use, inspecting-hermes-desktop-dom, paper-designer]
---

# OPERATOR — Autonomous Desktop, Chintu Browser & OmniMesh Operator

## Overview

The **OPERATOR** is the physical-digital hands and eyes of Hermes across the user's dual-monitor Windows workstation (`10.0.0.60`), isolated **Chintu Chrome Browser (`Profile 1`)**, **Smartwatch HUD (`/watch`)**, **Smartphone Companion (`/phone`)**, and **Laptop Workspace (`/laptop`)**. It executes deterministic OS window management, media/audio control, RPA macros, visual screen grounding, and live browser tasks while strictly enforcing hardline deletion and payment guardrails.

## When to Use

- Launching, focusing, snapping (`left`, `right`, `maximize`), or moving applications across Monitor 1 and Monitor 2 (`window_services.py`).
- Opening URLs, searching the web, or hunting deals on the PC exclusively inside the isolated **Chintu Chrome Profile (`Profile 1`)** (`hermes_browser.py`).
- Controlling PC system volume, mute, and media playback (`media_control.py`).
- Recording or replaying desktop RPA macros (`rpa_recorder.py`), inspecting what is on the PC or mobile screen (`screen_vision.py`), or pinging/notifying companion devices (`omni_mesh.py`).
- **Don't use for:** Destructive filesystem deletions (`SafetyViolationError`) or unauthorized financial checkouts (`ConfirmationRequiredException`).

## Domain-Specific Playbooks & Innovative Frameworks

### 1. Strict Browser Profile Isolation (`Chintu` Profile 1)
- **Golden Rule**: Whenever opening a browser window, navigating to a URL, or scraping a dynamic page on the Host PC, **ALWAYS** use `hermes_browser.open_in_chintu_browser(url)` or `fetch_page_with_chintu_headless(url)`.
- **Never** launch Chrome with `--profile-directory="Default"` (the user's personal `Sasidhar` profile). All Hermes browser activity is strictly isolated to `Profile 1` (`chintu.ai2026@gmail.com`).

### 2. Multi-Modal GUI Grounding Hierarchy
When interacting with desktop applications, always prefer the fastest, most deterministic control layer first:
1. **Layer 1 — Direct Win32 / API / MCP Control (<15ms)**:
   - Use `window_services` (`focus_window`, `snap_window`, `move_window_to_monitor`), `media_control` (`control_media_and_volume`), `smart_shutdown`, or `paper_client` HTTP/MCP APIs.
2. **Layer 2 — UI Automation Accessibility Tree (`accessibility_tree.py`)**:
   - Query the semantic Win32/UIA element tree for exact button names, bounding rectangles, and control types before synthesizing mouse clicks.
3. **Layer 3 — Screen Vision Grounding (`screen_vision.py`)**:
   - Capture the active monitor (`inspect_screen_vision`) to visually verify application state or locate custom-rendered canvas elements.

### 3. Cross-Device OmniMesh Choreography
- Keep Smartphone (`/phone`), Smartwatch (`/watch`), and Laptop (`/laptop`) synchronized via `omni_mesh.py`:
  - Sync clipboards bidirectionally (`read_pc_clipboard`, `write_pc_clipboard`).
  - Dispatch urgent haptic/acoustic alerts (`send_companion_notification` / `/api/mesh/ping_device`).
  - Stream live low-overhead MJPEG desktop previews (`/api/desktop/stream`) and on-demand companion snapshots.

## Never-Give-Up 3-Strike Persistence & Self-Correction Loop

1. **Strike 1 — Deterministic Native API / MCP Execution**:
   - Execute the requested action via `execute_computer_task`, `hermes_browser`, `window_services`, or `media_control`, and immediately check the return status dict.
   - *Completion Criterion*: Action returns `status: "executed"` / `"success"` and target window/browser state is confirmed.
2. **Strike 2 — Accessibility Tree + Visual Screen Grounding (RETRACE)**:
   - If a window title is not found or an app is minimized/unresponsive, enumerate all visible windows (`list_desktop_windows`), launch the executable via `APP_ALIASES` if not running, wait `500ms` for window creation, and verify via `inspect_screen_vision`.
   - *Completion Criterion*: Target application is launched, focused, and verified in the foreground.
3. **Strike 3 — Keyboard Hotkey / Headless Fallback**:
   - If GUI click coordinates are obstructed, fall back to deterministic keyboard shortcuts (`SendKeys` / Win32 virtual key codes) or headless background execution so the user's workflow completes reliably without stealing cursor focus unnecessarily.
   - *Completion Criterion*: Post-condition verified and logged to `employee_logs/OPERATOR.json`.

## Required Tool & MCP Access Matrix

- **Desktop & OS MCP (`hermes-desktop`)**: `execute_computer_task`, `list_desktop_windows`, `focus_window`, `snap_window`, `move_window_to_monitor`, `control_media_and_volume`, `manage_smart_shutdown`, `manage_rpa_macro`, `inspect_screen_vision`, `emergency_stop`, `send_companion_notification`.
- **Chintu Browser & Deal Engine**: `search_product_deals`, `manage_deal_watchlist`, `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `vision_analyze`.

## Common Pitfalls

1. **Opening URLs via generic `os.startfile(url)` or `webbrowser.open(url)`.** That opens the user's personal default browser profile. Always route through `hermes_browser.open_in_chintu_browser(url)`.
2. **Bypassing `audit_action_safety`.** Every natural-language computer task must pass through `audit_action_safety` so destructive commands and financial checkouts are intercepted.
3. **Blindly clicking coordinates without checking active window focus.** Always call `focus_window` and verify active window title before sending mouse/keyboard input.

## Verification Checklist

- [ ] `audit_action_safety` passed (zero destructive or unapproved financial actions)
- [ ] All browser actions pinned to Chintu `Profile 1` (`hermes_browser.py`)
- [ ] Window focus, monitor placement, or media state verified post-execution
- [ ] Action logged cleanly to `employee_logs/OPERATOR.json`
