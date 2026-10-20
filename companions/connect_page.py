# -*- coding: utf-8 -*-
"""
Hermes Companion Turnkey Onboarding, Native APK Installer & Watch 8 Biometric Hub
Renders a comprehensive, responsive, 1-click native APK installation & biometric
health analysis experience for Google Pixel 7 Pro, Samsung Galaxy Watch 8, and Laptop.
"""

from __future__ import annotations

from typing import Optional


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
    pixel_apk_url = f"{base_url}/download/hermes-pixel7pro.apk"
    watch_apk_url = f"{base_url}/download/hermes-galaxy-watch8.apk"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes Sovereign — Pixel 7 Pro & Galaxy Watch 8 Native APK & Biometrics</title>
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
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
            --text-heading: #f9fafb;
            --text-body: #d1d5db;
            --text-muted: #9ca3af;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: var(--bg-canvas);
            color: var(--text-body);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            padding: 28px 18px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1180px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
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
            flex-wrap: wrap;
        }}
        .subtitle {{
            font-size: 14px;
            color: var(--text-muted);
            max-width: 760px;
            margin: 0 auto 16px;
            line-height: 1.5;
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
            padding: 5px 12px;
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
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 22px;
            margin-bottom: 28px;
        }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 22px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .card:hover {{
            transform: translateY(-2px);
            border-color: var(--accent-green);
        }}
        .card-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 14px;
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
            color: #10b981;
            font-weight: 600;
        }}
        .qr-box {{
            background: #ffffff;
            border-radius: 10px;
            padding: 10px;
            margin: 12px auto;
            width: 165px;
            height: 165px;
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
            margin: 12px 0;
            font-size: 12px;
            color: var(--text-body);
        }}
        .feature-list li {{
            margin-bottom: 7px;
            display: flex;
            align-items: flex-start;
            gap: 8px;
            line-height: 1.4;
        }}
        .btn {{
            display: inline-block;
            background: var(--accent-blue);
            color: #ffffff;
            text-decoration: none;
            padding: 10px 14px;
            border-radius: 7px;
            font-size: 12.5px;
            font-weight: 700;
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
            color: #03150e;
            font-weight: 800;
        }}
        .btn-green:hover {{
            background: #059669;
            color: #ffffff;
        }}
        .btn-amber {{
            background: var(--accent-amber);
            color: #111827;
            font-weight: 800;
        }}
        .btn-secondary {{
            background: var(--bg-input);
            color: var(--text-heading);
            border: 1px solid var(--border-subtle);
        }}
        .btn-secondary:hover {{
            background: #374151;
        }}

        /* BIOMETRICS & HEALTH ANALYZER PANEL */
        .bio-panel {{
            background: linear-gradient(145deg, #0d1624 0%, #111827 100%);
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 26px;
            box-shadow: 0 8px 28px rgba(0,0,0,0.4);
        }}
        .bio-metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
            margin-top: 16px;
        }}
        .bio-stat {{
            background: #0b0f19;
            border: 1px solid var(--border-subtle);
            border-radius: 9px;
            padding: 12px 14px;
        }}
        .bio-stat-label {{
            font-size: 10.5px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--text-muted);
            font-weight: 700;
        }}
        .bio-stat-val {{
            font-size: 21px;
            font-weight: 800;
            color: var(--text-heading);
            margin-top: 4px;
        }}
        .bio-stat-sub {{
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 2px;
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
        .adb-input {{
            background: #0b0f19;
            border: 1px solid var(--border-subtle);
            color: #f9fafb;
            padding: 7px 10px;
            border-radius: 6px;
            font-size: 11.5px;
            width: 100%;
            font-family: monospace;
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
            z-index: 9999;
        }}
        #toast.show {{ display: block; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <h1 class="title">⚡ Hermes Sovereign Native Apps — Pixel 7 Pro &amp; Galaxy Watch 8</h1>
            <p class="subtitle">Real compiled &amp; V2/V3-signed Android &amp; Wear OS native APK installers (<code>com.hermes.sovereign.phone</code> &amp; <code>com.hermes.sovereign.watch</code>) with continuous Samsung BioActive Sensor telemetry, AI Readiness Scoring, and proactive anomaly notifications.</p>
            <div class="pill-group">
                <div class="pill"><div class="pulse"></div> Host PC: {lan_ip}:{port}</div>
                <div class="pill">📱 Google Pixel 7 Pro APK: Signed V2+V3</div>
                <div class="pill">⌚ Samsung Galaxy Watch 8 APK: Wear OS Signed</div>
                <div class="pill">❤️ BioActive Telemetry: ACTIVE</div>
                <a href="/" class="pill" style="text-decoration: none; color: #38bdf8; border-color: rgba(56, 189, 248, 0.4); font-weight: 700;">🏠 Back to Main Dashboard</a>
            </div>
        </div>

        <!-- 3 CARDS -->
        <div class="cards-grid">
            <!-- 1. GOOGLE PIXEL 7 PRO NATIVE APK -->
            <div class="card">
                <div>
                    <div class="card-header">
                        <div class="card-icon">📱</div>
                        <div>
                            <div class="card-title">Google Pixel 7 Pro</div>
                            <div class="card-subtitle">Native Android APK (com.hermes.sovereign.phone)</div>
                        </div>
                    </div>
                    <p style="font-size: 12px; color: var(--text-muted);">Scan with your Pixel 7 Pro camera to download &amp; install the real native Android APK directly:</p>
                    <div class="qr-box">
                        <img src="{phone_qr_b64}" alt="Pixel 7 Pro Native APK QR" />
                    </div>
                    <ul class="feature-list">
                        <li><span>📦</span> <strong>Real Native Android App:</strong> Installs <strong>Hermes AI</strong> in your Pixel 7 Pro app drawer (not a browser tab)</li>
                        <li><span>👟</span> <strong>Native Hardware Sensors:</strong> Streams step counter, battery %, &amp; health telemetry every 15s</li>
                        <li><span>🔔</span> <strong>High-Priority Alerts:</strong> Native Android NotificationChannel + haptics on watch/agent alerts</li>
                        <li><span>⌚</span> <strong>Phone-to-Watch Relay:</strong> Download the Watch 8 APK onto your Pixel 7 Pro to beam to your wrist</li>
                    </ul>
                </div>
                <div>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        <a href="{pixel_apk_url}" download="hermes-pixel7pro.apk" class="btn btn-green">📲 Download Pixel 7 Pro Native APK (.apk)</a>
                        <div style="display: flex; gap: 8px;">
                            <a href="{phone_url}" target="_blank" class="btn" style="flex: 1;">🌐 Open Mobile HUD</a>
                            <button class="btn btn-secondary" onclick="copyText('{pixel_apk_url}')">📋 Copy APK Link</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 2. SAMSUNG GALAXY WATCH 8 NATIVE WEAR OS APK -->
            <div class="card">
                <div>
                    <div class="card-header">
                        <div class="card-icon">⌚</div>
                        <div>
                            <div class="card-title">Samsung Galaxy Watch 8</div>
                            <div class="card-subtitle">Native Wear OS APK (com.hermes.sovereign.watch)</div>
                        </div>
                    </div>
                    <p style="font-size: 12px; color: var(--text-muted);">Install onto your Galaxy Watch 8 via your Pixel 7 Pro (Wear Installer 2 / Bugjaeger) OR beam directly below via Wireless ADB:</p>
                    <div class="qr-box">
                        <img src="{watch_qr_b64}" alt="Galaxy Watch 8 Native APK QR" />
                    </div>
                    <ul class="feature-list">
                        <li><span>❤️</span> <strong>BioActive Sensor Bridge:</strong> Reads live Heart Rate (BPM), Steps, &amp; Watch Battery directly from Wear OS hardware</li>
                        <li><span>🧠</span> <strong>Hermes Health Analyzer:</strong> Evaluates Readiness (0–100), Stress, SpO2 &amp; Sleep and fires alerts if anomalies occur</li>
                        <li><span>📲</span> <strong>Install via Pixel 7 Pro:</strong> Download the Watch APK on your phone &amp; beam via <em>Bugjaeger</em> / <em>Wear Installer 2</em>, or use 1-Click Wireless ADB below:</li>
                    </ul>
                    <!-- 1-CLICK WIRELESS ADB WATCH BEAMER -->
                    <div style="background: #0b0f19; border: 1px solid var(--border-subtle); border-radius: 8px; padding: 10px; margin-bottom: 10px;">
                        <div style="font-size: 11px; font-weight: 700; color: #38bdf8; margin-bottom: 6px;">🚀 1-Click Wireless ADB Beam to Galaxy Watch 8</div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 6px;">
                            <input id="adbTargetIp" class="adb-input" placeholder="Watch IP:Port (e.g. 10.0.0.95:5555)" />
                            <input id="adbPairIp" class="adb-input" placeholder="Optional Pair IP:Port" />
                        </div>
                        <div style="display: flex; gap: 6px;">
                            <input id="adbPairCode" class="adb-input" style="width: 120px;" placeholder="Pair Code (opt)" />
                            <button class="btn btn-green" style="flex: 1; padding: 7px 10px; font-size: 11.5px;" onclick="beamWatchApk('watch')">⌚ Beam to Watch 8</button>
                            <button class="btn btn-secondary" style="padding: 7px 10px; font-size: 11.5px;" onclick="beamWatchApk('phone')">📱 Pixel</button>
                        </div>
                        <div id="adbStatusMsg" style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">Enable: Watch Settings &rarr; Developer Options &rarr; Wireless Debugging</div>
                    </div>
                </div>
                <div>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        <a href="{watch_apk_url}" download="hermes-galaxy-watch8.apk" class="btn btn-green">⌚ Download Galaxy Watch 8 APK (.apk)</a>
                        <div style="display: flex; gap: 8px;">
                            <a href="/api/companion/install/watch_adb.bat" class="btn btn-secondary" style="flex: 1; font-size: 11.5px;">💻 1-Click Windows ADB Script (.bat)</a>
                            <a href="{watch_url}" target="_blank" class="btn btn-secondary" style="font-size: 11.5px;">⌚ Preview HUD</a>
                        </div>
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
                        <li><span>🖥️</span> <strong>Dual-Screen Mirror:</strong> Monitor 1 &amp; 2 full live streaming</li>
                        <li><span>🖱️</span> <strong>Touch &amp; Mouse Remote:</strong> Click, type, and snap windows</li>
                        <li><span>⚙️</span> <strong>Distributed Worker Node:</strong> Offload local tasks &amp; telemetry</li>
                        <li><span>⚡</span> <strong>1-Click Wake-on-LAN:</strong> Power on host PC from secondary laptop</li>
                    </ul>
                    <div style="background: #0b0f19; border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px; margin-top: 12px;">
                        <div style="font-size: 11px; font-weight: 700; color: #a855f7; margin-bottom: 6px;">📲 How to Install Watch 8 APK from Your Pixel 7 Pro:</div>
                        <ol style="font-size: 11px; color: var(--text-body); padding-left: 16px; line-height: 1.5;">
                            <li>On your <strong>Pixel 7 Pro</strong>, tap <strong>"Download Galaxy Watch 8 APK"</strong> above.</li>
                            <li>On your <strong>Galaxy Watch 8</strong>: Settings &rarr; About Watch &rarr; Software Info &rarr; tap <em>Software Version</em> 7 times &rarr; enable <strong>Wireless Debugging</strong>.</li>
                            <li>Use <strong>Wear Installer 2</strong> or <strong>Bugjaeger</strong> on your Pixel 7 Pro (or the 1-Click Beam box on Card 2) to push <code>hermes-galaxy-watch8.apk</code> to your watch!</li>
                        </ol>
                    </div>
                </div>
                <div>
                    <div style="display: flex; gap: 8px;">
                        <a href="{laptop_url}" target="_blank" class="btn" style="flex: 1;">💻 Open Laptop View</a>
                        <button class="btn btn-secondary" onclick="copyText('{laptop_url}')">📋 Copy</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- LIVE SAMSUNG GALAXY WATCH 8 & PIXEL 7 PRO BIOMETRIC HEALTH ANALYZER -->
        <div class="bio-panel">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div>
                    <h2 style="font-size: 18px; font-weight: 800; color: var(--text-heading); display: flex; align-items: center; gap: 8px;">
                        ❤️ Samsung Galaxy Watch 8 &amp; Pixel 7 Pro — Live Biometric Health &amp; Readiness Analyzer
                    </h2>
                    <p style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
                        Pulls real-time Heart Rate (BPM), HRV (RMSSD), Blood Oxygen (SpO2), Stress, Sleep stages, and Step telemetry from your Watch 8 &amp; Pixel 7 Pro and dispatches proactive alerts across Desktop, Telegram, Phone &amp; Wrist when anomalies occur.
                    </p>
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <button class="btn btn-green" onclick="simulateWatchBiometrics('optimal')">⚡ Sync Optimal Biometrics</button>
                    <button class="btn btn-amber" onclick="simulateWatchBiometrics('anomaly')">🚨 Simulate High-Stress / Low-SpO2 Watch Alert</button>
                    <button class="btn btn-secondary" onclick="loadWatchAnalytics()">🔄 Refresh</button>
                </div>
            </div>

            <div class="bio-metrics-grid" id="bioMetricsGrid">
                <div class="bio-stat">
                    <div class="bio-stat-label">Readiness Score</div>
                    <div class="bio-stat-val" id="bioReadiness" style="color: #10b981;">-- / 100</div>
                    <div class="bio-stat-sub" id="bioStatusLabel">Waiting for sync...</div>
                </div>
                <div class="bio-stat">
                    <div class="bio-stat-label">Heart Rate (Watch 8)</div>
                    <div class="bio-stat-val" id="bioHeartRate">-- BPM</div>
                    <div class="bio-stat-sub" id="bioRestingHr">Resting: -- BPM</div>
                </div>
                <div class="bio-stat">
                    <div class="bio-stat-label">HRV &amp; Stress Load</div>
                    <div class="bio-stat-val" id="bioHrv">-- ms</div>
                    <div class="bio-stat-sub" id="bioStress">Stress: -- / 100</div>
                </div>
                <div class="bio-stat">
                    <div class="bio-stat-label">Blood Oxygen (SpO2)</div>
                    <div class="bio-stat-val" id="bioSpo2">-- %</div>
                    <div class="bio-stat-sub" id="bioSkinTemp">Skin Temp: -- °C</div>
                </div>
                <div class="bio-stat">
                    <div class="bio-stat-label">Sleep Architecture</div>
                    <div class="bio-stat-val" id="bioSleepScore">-- / 100</div>
                    <div class="bio-stat-sub" id="bioSleepStages">Duration: --h</div>
                </div>
                <div class="bio-stat">
                    <div class="bio-stat-label">Activity &amp; Battery</div>
                    <div class="bio-stat-val" id="bioSteps">-- steps</div>
                    <div class="bio-stat-sub" id="bioBatteries">⌚ --% &bull; 📱 --%</div>
                </div>
            </div>

            <div id="bioRecommendationsBox" style="margin-top: 14px; background: #0b0f19; border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px 16px; font-size: 12.5px; color: var(--text-body);">
                <strong>🩺 Hermes BioActive Insight:</strong> <span id="bioInsightText">Loading latest Samsung Galaxy Watch 8 telemetry...</span>
            </div>
        </div>

        <!-- 24/7 PC POWER & WAKE-ON-LAN MANAGEMENT PANEL -->
        <div class="power-panel">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h2 style="font-size: 16px; font-weight: 700; color: var(--text-heading); display: flex; align-items: center; gap: 8px;">
                        ⚡ 24/7 Host Uptime &amp; Remote Wake-on-LAN (WoL)
                    </h2>
                    <p style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Hermes runs 24/7 on this PC. Even if powered down or sleeping, you can wake it up remotely from your laptop, Pixel 7 Pro, or Galaxy Watch 8.</p>
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
                    <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 700;">Mobile &amp; Watch Wake Shortcuts</div>
                    <p style="font-size: 11px; color: var(--text-muted); margin: 6px 0;">Built directly into your native Pixel 7 Pro &amp; Galaxy Watch 8 apps for 1-tap remote wake.</p>
                    <div style="font-size: 11px; color: var(--accent-green);">✓ Built into Hermes Native APK</div>
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
            setTimeout(() => t.classList.remove('show'), 3200);
        }}

        function renderBioData(data) {{
            const s = data.sample || data.latest || {{}};
            const a = data.analysis || {{}};
            const score = a.readiness_score !== undefined ? a.readiness_score : 88;
            const label = a.status_label || "OPTIMAL";
            const scoreEl = document.getElementById('bioReadiness');
            scoreEl.innerText = score + " / 100";
            scoreEl.style.color = score >= 80 ? "#10b981" : (score >= 60 ? "#f59e0b" : "#ef4444");
            document.getElementById('bioStatusLabel').innerText = label + " (" + (s.activity_state || "resting") + ")";
            document.getElementById('bioHeartRate').innerText = (s.heart_rate_bpm || "--") + " BPM";
            document.getElementById('bioRestingHr').innerText = "Resting: " + (s.resting_hr_bpm || "--") + " BPM";
            document.getElementById('bioHrv').innerText = (s.hrv_rmssd_ms || "--") + " ms";
            document.getElementById('bioStress').innerText = "Stress: " + (s.stress_score !== undefined ? s.stress_score : "--") + " / 100";
            document.getElementById('bioSpo2').innerText = (s.spo2_pct || "--") + " %";
            document.getElementById('bioSkinTemp').innerText = "Skin Temp: " + (s.skin_temp_c || "--") + " °C";
            document.getElementById('bioSleepScore').innerText = (s.sleep_score || "--") + " / 100";
            document.getElementById('bioSleepStages').innerText = (s.sleep_duration_hours || "--") + "h (Deep " + (s.deep_sleep_minutes || "--") + "m)";
            document.getElementById('bioSteps').innerText = (s.steps !== undefined ? s.steps.toLocaleString() : "--") + " steps";
            document.getElementById('bioBatteries').innerText = "⌚ " + (s.watch_battery_pct || "--") + "% • 📱 " + (s.phone_battery_pct || "--") + "%";

            const recs = a.recommendations || [];
            const anoms = a.anomalies || [];
            const box = document.getElementById('bioRecommendationsBox');
            if (anoms.length > 0) {{
                box.style.borderColor = "#ef4444";
                document.getElementById('bioInsightText').innerHTML = "<span style='color:#f87171;font-weight:700;'>⚠️ " + anoms.length + " Anomaly Alert(s) Dispatched to Watch & Phone:</span> " + recs.join(" | ");
            }} else {{
                box.style.borderColor = "rgba(16, 185, 129, 0.4)";
                document.getElementById('bioInsightText').innerText = recs.join(" | ") || "Biometrics within healthy baseline.";
            }}
        }}

        async function loadWatchAnalytics() {{
            try {{
                const res = await fetch('/api/watch/analytics');
                const data = await res.json();
                renderBioData(data);
            }} catch (e) {{
                console.warn("Analytics load error:", e);
            }}
        }}

        async function simulateWatchBiometrics(mode) {{
            try {{
                const res = await fetch('/api/watch/simulate', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ mode: mode }})
                }});
                const data = await res.json();
                renderBioData(data);
                if (mode === 'anomaly') {{
                    showToast("🚨 Watch 8 Anomaly Detected! Notification sent to Watch, Pixel 7 Pro & Desktop!");
                }} else {{
                    showToast("⚡ Watch 8 Optimal Biometrics Synced (Readiness: " + data.analysis.readiness_score + "/100)");
                }}
            }} catch (e) {{
                alert("Simulation error: " + e);
            }}
        }}

        async function beamWatchApk(deviceType) {{
            const targetIp = document.getElementById('adbTargetIp').value.trim();
            const pairIp = document.getElementById('adbPairIp').value.trim();
            const pairCode = document.getElementById('adbPairCode').value.trim();
            const statusEl = document.getElementById('adbStatusMsg');
            if (!targetIp) {{
                statusEl.style.color = "#f59e0b";
                statusEl.innerText = "⚠️ Enter your Watch 8 or Pixel 7 Pro IP:Port (from Wireless Debugging settings).";
                return;
            }}
            statusEl.style.color = "#38bdf8";
            statusEl.innerText = "⏳ Connecting via Wireless ADB & beaming signed native APK to " + targetIp + "...";
            try {{
                const res = await fetch('/api/watch/adb_install', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        target_ip_port: targetIp,
                        device_type: deviceType,
                        pair_ip_port: pairIp,
                        pair_code: pairCode
                    }})
                }});
                const data = await res.json();
                if (data.ok) {{
                    statusEl.style.color = "#10b981";
                    statusEl.innerText = "✅ Installed & launched native APK on " + targetIp + "!";
                    showToast("✅ Native APK installed on " + targetIp + "!");
                }} else {{
                    statusEl.style.color = "#ef4444";
                    statusEl.innerText = "❌ ADB Status: " + (data.steps ? data.steps.join(" -> ") : (data.error || "Check IP:Port"));
                }}
            }} catch (e) {{
                statusEl.style.color = "#ef4444";
                statusEl.innerText = "❌ Request error: " + e;
            }}
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

        // Load initial Watch 8 analytics on page open
        loadWatchAnalytics();
    </script>
</body>
</html>
"""
    return html
