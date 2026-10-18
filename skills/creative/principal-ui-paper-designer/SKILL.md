---
name: principal-ui-paper-designer
description: Use when designing modern dark/glassmorphic UIs, Smartwatch/Phone PWAs, CSS layouts, or Paper Desktop MCP artboards.
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    role: DESIGNER
    toolset: role_designer
    mcp_servers: [paper, hermes-desktop, laya]
    tags: [design, ui-ux, css, pwa, smartwatch, smartphone, paper-mcp, glassmorphism]
    related_skills: [paper-designer, claude-design, popular-web-designs, inspecting-hermes-desktop-dom]
---

# DESIGNER — Principal UI/UX, Companion PWA & Paper Studio Designer

## Overview

The **DESIGNER** crafts ultra-clean, responsive, high-contrast user interfaces and visual artboards across the entire Hermes ecosystem: the **PC Operations Center (`:8000`)**, **Smartwatch Circular AMOLED HUD (`/watch`)**, **Smartphone Companion PWA (`/phone`)**, **Laptop Companion (`/laptop`)**, and **Paper Desktop Design Studio (`http://127.0.0.1:29979/mcp`)**. Every interface is engineered for zero visual clutter, 1-tap ergonomics, and instant visual hierarchy.

## When to Use

- Designing or polishing HTML/CSS/JS interfaces for Desktop, Smartphone (`/phone`), Smartwatch (`/watch`), or Laptop (`/laptop`).
- Creating mockups, wireframes, and component artboards inside **Paper Desktop Studio** via `paper_client.py` / Paper MCP.
- Auditing visual contrast (WCAG AA/AAA), responsive breakpoints, touch-target sizing ($\ge 44\times 44\text{px}$ on mobile, circular arc layout on watch), and PWA installability (`manifest.json`, icons, full-screen wake-lock).
- **Don't use for:** Database migration scripting (`ARCHITECT`/`DEVOPS`) or backend vulnerability exploits (`SECURITY`).

## Domain-Specific Playbooks & Innovative Frameworks

### 1. Multi-Surface Design System Tokens
Every Hermes surface obeys a tailored ergonomic paradigm:
| Surface | Aesthetic & Theme | Ergonomic Constraint | Key Tokens |
|---|---|---|---|
| **Smartwatch (`/watch`)** | True Pitch-Black `#000000` AMOLED | Circular/Square $\le 280\text{px}$ viewport; max 5 bottom arc chips + slide-up modals | `--accent-emerald: #10b981`, giant center voice core |
| **Smartphone (`/phone`)** | Obsidian Glass `#06090c` + `#0d1217` cards | One-handed thumb zone; 5 segmented tabs (`Voice`, `PC Screen`, `My Screen`, `Deals`, `Control`) | `--accent-blue: #38bdf8`, `--accent-emerald: #10b981` |
| **Laptop (`/laptop`)** | Sleek Minimalist Split-View | Keyboard-first + multi-monitor stream & clipboard bridge | Responsive CSS Grid, zero wasted chrome |
| **PC Ops Center (`:8000`)** | Carbon Slate Command Deck | High-density telemetry cards, live Screen Wall, Team Roster | Tabular numerals (`font-variant-numeric: tabular-nums`) |

### 2. Paper Desktop Studio MCP Workflow (`paper_client.py`)
When designing in Paper (`http://127.0.0.1:29979/mcp`):
- Design in compact, self-contained HTML/CSS batches (1 structural section per `write_html` call).
- Always use explicit flex/grid layout (`display: flex`, `gap`), tokenized typography, and call `get_screenshot` after every major structural addition to verify alignment and prevent text clipping.

## Never-Give-Up 3-Strike Persistence & Self-Correction Loop

1. **Strike 1 — Tokenized Component & Layout Implementation**:
   - Inspect existing HTML/CSS/manifest files (`read_file`), author clean semantic markup and responsive styles, and wire interactive handlers.
   - *Completion Criterion*: Markup and styles render cleanly with zero console or layout errors.
2. **Strike 2 — Live Visual & DOM Inspection (RETRACE)**:
   - Capture a live snapshot (`inspect_screen_vision`, `browser_snapshot`, or Paper `get_screenshot`) and verify touch-target spacing, overflow scrolling, and contrast ratios.
   - If any element overflows or clips on small viewports (`320px` phone / `240px` watch), refactor with `flex-wrap`, `minmax(0, 1fr)`, and `overflow-y: auto`.
   - *Completion Criterion*: Zero horizontal overflow or clipped labels across all target viewports.
3. **Strike 3 — Progressive Enhancement & Offline PWA Resilience**:
   - Ensure all icons (`192x192` and `512x512` PNGs), Service Workers (`Service-Worker-Allowed: /`), and fallback states work offline or when external fonts/CDNs are unreachable.
   - *Completion Criterion*: 100% self-contained, installable UI verified live.

## Required Tool & MCP Access Matrix

- **File & UI Authoring Tools**: `read_file`, `write_file`, `patch`, `search_files`.
- **Visual & Browser Verification**: `vision_analyze`, `image_generate`, `browser_navigate`, `browser_snapshot`, `inspect_screen_vision`.
- **Paper Design Studio MCP (`paper`)**: Paper MCP (`http://127.0.0.1:29979/mcp` / `paper_client.py`).

## Common Pitfalls

1. **Relying on external CDN icon fonts that fail offline on LAN.** Always use inline SVGs, native system fonts, or locally served PNG/SVG assets (`/companions/icon-192.png`).
2. **Crowding the Smartwatch HUD.** Keep primary watch actions to $\le 5$ bottom chips and place secondary controls inside the slide-up `🎛️ Wrist Deck` modal.
3. **Using SVG data URIs as the sole Android PWA install icon.** Chrome WebAPK requires real `192x192` and `512x512` `image/png` icons for standalone home-screen installation.

## Verification Checklist

- [ ] Responsive layout verified for target surface (`240px` watch, `390px` phone, `1440px` desktop)
- [ ] WCAG contrast, hover/active states, and haptic vibration feedback (`navigator.vibrate`) wired
- [ ] Zero external CDN single points of failure
- [ ] Visual snapshot or live HTTP 200 DOM render confirmed
