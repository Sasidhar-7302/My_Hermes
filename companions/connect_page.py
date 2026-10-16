# -*- coding: utf-8 -*-
"""
Hermes Companion Turnkey Onboarding & QR Connect Hub
Renders a comprehensive, responsive, 1-click onboarding experience for
Mobile (iOS / Android), Smartwatch (Wear OS / Apple Watch), and Laptop.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


def render_connect_hub_html(
    lan_ip: str,
    port: int,
    pairing_code: str,
    phone_qr_b64: str,
    watch_qr_b64: str,
    laptop_url: str,
    primary_mac: str = "00:13:EF:60:04:42",
    eth_mac: str = "04:42:1A:EA:BF:E7"
) -> str:
    base_url = f"http://{lan_ip}:{port}"
    phone_url = f"{base_url}/companions/smartphone?pair={pairing_code}"
    watch_url = f"{base_url}/companions/smartwatch?pair={pairing_code}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes Ecosystem — 1-Click Companion Connect</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>">
    <style>
        :root {{
            --bg-canvas: #090d16;
            --bg-card: #111827;
            --bg-input: #1f2937;
            --border-subtle: #374151;
            --accent-green: #10b981;
            --accent-blue: #3b82f6;
            --accent-purple: #a855f7;
            --text-heading: #f9fafb;
            --text-body: #d1d5db;
            --text-muted: #9ca3af;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: var(--bg-canvas);
            color: var(--text-body);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            padding: 30px 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 35px;
        }}
        .title {{
            font-size: 28px;
            font-weight: 800;
            color: var(--text-heading);
            letter-spacing: -0.02em;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}
        .subtitle {{
            font-size: 14px;
            color: var(--text-muted);
            max-width: 680px;
            margin: 0 auto 16px;
        }}
        .pill-group {{
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .pill {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-heading);
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .pulse {{
            width: 8px;
            height: 8px;
            background: var(--accent-green);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--accent-green);
        }}

        /* THREE DEVICE CARDS GRID */
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 24px;
            margin-bottom: 35px;
        }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .card:hover {{
            transform: translateY(-2px);
            border-color: var(--accent-blue);
        }}
        .card-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
        }}
        .card-icon {{
            font-size: 28px;
            background: var(--bg-input);
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
            border: 1px solid var(--border-subtle);
        }}
        .card-title {{
            font-size: 18px;
            font-weight: 700;
            color: var(--text-heading);
        }}
        .card-subtitle {{
            font-size: 11px;
            color: var(--text-muted);
        }}
        .qr-box {{
            background: #ffffff;
            border-radius: 10px;
            padding: 12px;
            margin: 14px auto;
            width: 170px;
            height: 170px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }}
        .qr-box img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
        }}
        .feature-list {{
            list-style: none;
            margin: 16px 0;
            font-size: 12px;
            color: var(--text-body);
        }}
        .feature-list li {{
            margin-bottom: 8px;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }}
        .btn {{
            display: inline-block;
            background: var(--accent-blue);
            color: #ffffff;
            text-decoration: none;
            padding: 10px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            text-align: center;
            cursor: pointer;
            border: none;
            transition: background 0.15s ease;
        }}
        .btn:hover {{
            background: #2563eb;
        }}
        .btn-green {{
            background: var(--accent-green);
            color: #000000;
            font-weight: 700;
        }}
        .btn-green:hover {{
            background: #059669;
            color: #ffffff;
        }}
        .btn-secondary {{
            background: var(--bg-input);
            color: var(--text-heading);
            border: 1px solid var(--border-subtle);
        }}
        .btn-secondary:hover {{
            background: #374151;
        }}

        /* POWER & WAKE-ON-LAN PANEL */
        .power-panel {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 25px;
        }}
        .power-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }}
        .power-box {{
            background: var(--bg-input);
            padding: 16px;
            border-radius: 8px;
            border: 1px solid var(--border-subtle);
        }}
        .code-snippet {{
            font-family: monospace;
            font-size: 11px;
            background: #0b0f19;
            padding: 8px;
            border-radius: 4px;
            color: #38bdf8;
            margin: 8px 0;
            word-break: break-all;
        }}

        /* TOAST */
        #toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--accent-green);
            color: #000;
            padding: 10px 18px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 13px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            display: none;
        }}
        #toast.show {{ display: block; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <h1 class="title">⚡ Hermes OmniMesh Ecosystem</h1>
            <p class="subtitle">Turnkey 1-click connect hub for your Smartphone, Smartwatch, and Laptop. Zero Termux or manual setup required. Includes live desktop screen mirroring, push-to-talk voice, and 24/7 Wake-on-LAN power.</p>
            <div class="pill-group">
                <div class="pill"><div class="pulse"></div> Host PC: {lan_ip}:{port}</div>
                <div class="pill">📶 Wi-Fi MAC: {primary_mac}</div>
                <div class="pill">⚡ 24/7 Keep-Alive: ACTIVE</div>
                <div class="pill">🔑 Pair Session: {pairing_code[:12]}...</div>
                <a href="/api/download/catalog" class="pill" style="text-decoration: none; color: #10b981; border-color: rgba(16, 185, 129, 0.4); font-weight: 700;" download>📊 Download Feature & Test Catalog (.xlsx)</a>
            </div>
        </div>

        <!-- 3 CARDS -->
        <div class="cards-grid">
            <!-- 1. SMARTPHONE -->
            <div class="card">
                <div>
                    <div class="card-header">
                        <div class="card-icon">📱</div>
                        <div>
                            <div class="card-title">Smartphone</div>
                            <div class="card-subtitle">Android & iPhone Native PWA</div>
                        </div>
                    </div>
                    <p style="font-size: 12px; color: var(--text-muted);">Point your phone camera at this QR code to connect and authenticate instantly:</p>
                    <div class="qr-box">
                        <img src="{phone_qr_b64}" alt="Phone Pairing QR" />
                    </div>
                    <ul class="feature-list">
                        <li><span>📺</span> <strong>Watch Hermes Work:</strong> Live desktop screen mirror (Muse style)</li>
                        <li><span>🎙️</span> <strong>Push-to-Talk Voice:</strong> Laya System-1 mid-sentence execution</li>
                        <li><span>📸</span> <strong>Camera Vision Relay:</strong> Instant photo uploads to Vision Agent</li>
                        <li><span>📋</span> <strong>Bi-Directional Clipboard:</strong> Auto-synced with PC clipboard</li>
                        <li><span>⚡</span> <strong>Wake-on-LAN:</strong> 1-tap remote power-on if PC sleeps</li>
                    </ul>
                </div>
                <div>
                    <p style="font-size: 11px; color: #a3e635; margin-bottom: 8px;">💡 Short URL: <code>http://{lan_ip}:{port}/phone</code> &bull; Tap <strong>"📲 Install"</strong> or <strong>"⛶ App Mode"</strong> inside app for zero-browser-bar native mode.</p>
                    <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                        <a href="{phone_url}" target="_blank" class="btn" style="flex: 1;">📱 Open Mobile App</a>
                        <button class="btn btn-secondary" onclick="copyText('http://{lan_ip}:{port}/phone')">📋 Copy</button>
                    </div>
                    <div style="display: flex; gap: 6px;">
                        <a href="/api/companion/install/ios_app.mobileconfig" class="btn btn-secondary" style="flex: 1; font-size: 11px; padding: 6px;">🍏 iOS Native App (.mobileconfig)</a>
                        <a href="/api/companion/install/watch_adb.bat" class="btn btn-secondary" style="flex: 1; font-size: 11px; padding: 6px;">🤖 Android ADB Installer</a>
                    </div>
                </div>
            </div>

            <!-- 2. SMARTWATCH -->
            <div class="card">
                <div>
                    <div class="card-header">
                        <div class="card-icon">⌚</div>
                        <div>
                            <div class="card-title">Smartwatch HUD</div>
                            <div class="card-subtitle">Wear OS, Galaxy Watch, Apple Watch</div>
                        </div>
                    </div>
                    <p style="font-size: 12px; color: var(--text-muted);">Scan on watch or type short URL <code>{lan_ip}:{port}/watch</code> on wrist:</p>
                    <div class="qr-box">
                        <img src="{watch_qr_b64}" alt="Watch Pairing QR" />
                    </div>
                    <ul class="feature-list">
                        <li><span>⌚</span> <strong>AMOLED Wrist HUD:</strong> Battery-efficient pitch black UI (tap clock for fullscreen)</li>
                        <li><span>🎙️</span> <strong>Hold-to-Talk Voice:</strong> Fast desktop command execution</li>
                        <li><span>📳</span> <strong>Physical Wrist Haptics:</strong> Vibrates on task completion</li>
                        <li><span>🚨</span> <strong>Emergency Stop:</strong> Instant global desktop kill switch</li>
                        <li><span>🖥️</span> <strong>Peek at PC:</strong> Live desktop screenshot snapshot</li>
                    </ul>
                </div>
                <div>
                    <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                        <a href="{watch_url}" target="_blank" class="btn btn-green" style="flex: 1;">⌚ Open Watch HUD</a>
                        <button class="btn btn-secondary" onclick="copyText('http://{lan_ip}:{port}/watch')">📋 Copy</button>
                    </div>
                    <div style="display: flex; gap: 6px;">
                        <a href="/api/companion/install/watch_adb.bat" class="btn btn-secondary" style="flex: 1; font-size: 11px; padding: 6px;">⌚ 1-Click Watch ADB Installer (.bat)</a>
                        <a href="/api/companion/install/ios_app.mobileconfig" class="btn btn-secondary" style="flex: 1; font-size: 11px; padding: 6px;">🍏 Watch Profile</a>
                    </div>
                </div>
            </div>

            <!-- 3. LAPTOP -->
            <div class="card">
                <div>
                    <div class="card-header">
                        <div class="card-icon">💻</div>
                        <div>
                            <div class="card-title">Laptop Companion</div>
                            <div class="card-subtitle">Mac, Windows, Linux, Chromebook</div>
                        </div>
                    </div>
                    <p style="font-size: 12px; color: var(--text-muted);">Open directly on your laptop to mirror desktop and distribute compute:</p>
                    <div class="code-snippet">{laptop_url}</div>
                    <ul class="feature-list">
                        <li><span>🖥️</span> <strong>Dual-Screen Mirror:</strong> Monitor 1 & 2 full live streaming</li>
                        <li><span>🖱️</span> <strong>Touch & Mouse Remote:</strong> Click, type, and snap windows</li>
                        <li><span>⚙️</span> <strong>Distributed Worker Node:</strong> Offload local tasks & telemetry</li>
                        <li><span>⚡</span> <strong>1-Click Wake-on-LAN:</strong> Power on host PC from secondary laptop</li>
                    </ul>
                </div>
                <div>
                    <div style="display: flex; gap: 8px;">
                        <a href="{laptop_url}" target="_blank" class="btn" style="flex: 1;">💻 Open Laptop View</a>
                        <button class="btn btn-secondary" onclick="copyText('{laptop_url}')">📋 Copy</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- 24/7 PC POWER & WAKE-ON-LAN MANAGEMENT PANEL -->
        <div class="power-panel">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h2 style="font-size: 16px; font-weight: 700; color: var(--text-heading); display: flex; align-items: center; gap: 8px;">
                        ⚡ 24/7 Host Uptime & Remote Wake-on-LAN (WoL)
                    </h2>
                    <p style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Hermes runs 24/7 on this PC. Even if powered down or sleeping, you can wake it up remotely from your laptop, mobile, or smartwatch.</p>
                </div>
                <div style="display: flex; gap: 8px;">
                    <button class="btn btn-green" onclick="triggerWakePacket()">⚡ Send Test Wake-on-LAN</button>
                    <button class="btn btn-secondary" onclick="toggleKeepAlive()">🛡️ Toggle 24/7 Keep-Alive</button>
                </div>
            </div>

            <div class="power-grid">
                <div class="power-box">
                    <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 700;">Host Network Interfaces</div>
                    <div style="margin-top: 8px; font-size: 12px;">
                        <div>📶 <strong>Wi-Fi 2:</strong> {primary_mac} (IP: {lan_ip})</div>
                        <div style="margin-top: 4px;">🔌 <strong>Ethernet:</strong> {eth_mac}</div>
                        <div style="margin-top: 4px; color: var(--text-muted);">Broadcast: 10.0.0.255 &bull; UDP Port: 9</div>
                    </div>
                </div>

                <div class="power-box">
                    <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 700;">Turnkey Laptop Wake Scripts</div>
                    <p style="font-size: 11px; color: var(--text-muted); margin: 6px 0;">Keep these on your secondary laptop to wake this PC with 1 click:</p>
                    <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                        <a href="/api/power/download/bat" class="btn btn-secondary" style="font-size: 11px; padding: 6px 10px;">💾 Wake-Hermes.bat</a>
                        <a href="/api/power/download/py" class="btn btn-secondary" style="font-size: 11px; padding: 6px 10px;">🐍 wake_hermes.py</a>
                        <a href="/api/power/download/sh" class="btn btn-secondary" style="font-size: 11px; padding: 6px 10px;">🐧 wake_hermes.sh</a>
                    </div>
                </div>

                <div class="power-box">
                    <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 700;">Mobile & Watch Wake Shortcuts</div>
                    <p style="font-size: 11px; color: var(--text-muted); margin: 6px 0;">On iOS / Android, install any free Wake-on-LAN app or use the 1-click button inside the Hermes Mobile Companion.</p>
                    <div style="font-size: 11px; color: var(--accent-green);">✓ Built into Hermes Mobile App</div>
                </div>
            </div>
        </div>
    </div>

    <!-- TOAST -->
    <div id="toast">Copied to clipboard!</div>

    <script>
        function copyText(txt) {{
            navigator.clipboard.writeText(txt).then(() => {{
                showToast("Link copied to clipboard!");
            }}).catch(() => {{
                prompt("Copy this URL:", txt);
            }});
        }}

        function showToast(msg) {{
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 2800);
        }}

        async function triggerWakePacket() {{
            try {{
                const res = await fetch('/api/power/wake', {{ method: 'POST' }});
                const data = await res.json();
                showToast("⚡ Wake-on-LAN Magic Packet broadcasted!");
            }} catch (e) {{
                alert("Wake failed: " + e);
            }}
        }}

        async function toggleKeepAlive() {{
            try {{
                const res = await fetch('/api/power/keepalive', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ enable: true }})
                }});
                const data = await res.json();
                showToast("24/7 Keep-Alive confirmed ACTIVE");
            }} catch (e) {{
                alert("Keep-Alive toggle error: " + e);
            }}
        }}
    </script>
</body>
</html>
"""
    return html
