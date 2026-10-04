# -*- coding: utf-8 -*-
"""
Hermes Omni-Mesh Companion Web Application (PWA)
Serves the responsive multi-device client for Phone, Smartwatch, and Laptop.
"""

from __future__ import annotations

MANIFEST_JSON = {
    "name": "Hermes Companion",
    "short_name": "Hermes",
    "start_url": "/companion",
    "display": "standalone",
    "background_color": "#070a0d",
    "theme_color": "#10b981",
    "icons": [
        {
            "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='45' fill='%23059669'/><path d='M30 50 L50 25 L70 50 L50 75 Z' fill='%23ffffff'/></svg>",
            "sizes": "192x192 512x512",
            "type": "image/svg+xml"
        }
    ]
}

SERVICE_WORKER_JS = """// Hermes Companion Service Worker
const CACHE_NAME = 'hermes-companion-v1';
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : { title: 'Hermes Alert', body: 'New notification from PC' };
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/companion/icon.svg',
            vibrate: data.vibrate || [100, 50, 100]
        })
    );
});
"""

def render_companion_html(host_ip: str, host_port: int) -> str:
    """Generates the multi-device companion interface."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#070a0d">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>Hermes Companion</title>
    <link rel="manifest" href="/companion/manifest.json">
    <style>
        :root {{
            --bg-base: #06090c;
            --bg-card: #0d1217;
            --bg-input: #121921;
            --border-subtle: rgba(255, 255, 255, 0.08);
            --border-bright: rgba(16, 185, 129, 0.35);
            --accent-green: #10b981;
            --accent-green-dim: rgba(16, 185, 129, 0.15);
            --accent-red: #ef4444;
            --accent-red-dim: rgba(239, 68, 68, 0.15);
            --accent-gold: #f59e0b;
            --text-main: #e2e8f0;
            --text-muted: #94a3b8;
            --text-bright: #ffffff;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}

        body {{
            background: var(--bg-base);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }}

        /* ── DEVICE MODE VIEWS ── */
        .mode-container {{
            display: none;
            width: 100%;
            height: 100%;
        }}

        .mode-container.active {{
            display: flex;
            flex-direction: column;
        }}

        /* ── WATCH MODE (Circular / Compact HUD) ── */
        #view-watch {{
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: #000000;
            padding: 12px;
            text-align: center;
        }}

        .watch-hud {{
            width: 100%;
            max-width: 300px;
            aspect-ratio: 1;
            border-radius: 50%;
            border: 2px solid var(--accent-green);
            background: radial-gradient(circle, #0e141a 0%, #000000 85%);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 18px;
            gap: 8px;
            box-shadow: 0 0 25px rgba(16, 185, 129, 0.2);
            position: relative;
        }}

        .watch-status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-green);
            display: inline-block;
            box-shadow: 0 0 6px var(--accent-green);
        }}

        .watch-btn {{
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            color: var(--text-bright);
            padding: 8px 14px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            width: 85%;
            justify-content: center;
        }}

        .watch-btn:active {{
            transform: scale(0.95);
            background: var(--accent-green-dim);
            border-color: var(--accent-green);
        }}

        .watch-btn.panic {{
            background: var(--accent-red-dim);
            border-color: var(--accent-red);
            color: #fca5a5;
        }}

        .watch-btn.panic:active {{
            background: rgba(239, 68, 68, 0.4);
        }}

        /* ── PHONE MODE (Main Mobile Companion) ── */
        #view-phone {{
            max-width: 480px;
            margin: 0 auto;
            width: 100%;
            padding: 16px;
            gap: 16px;
        }}

        .app-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
        }}

        .brand-badge {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .pulse-orb {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--accent-green);
            box-shadow: 0 0 8px var(--accent-green);
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.4; transform: scale(0.85); }}
        }}

        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .card-title {{
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .btn-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}

        .action-btn {{
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            color: var(--text-main);
            padding: 12px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 6px;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .action-btn:active {{
            transform: scale(0.97);
            border-color: var(--accent-green);
            background: var(--accent-green-dim);
            color: var(--text-bright);
        }}

        .action-btn.danger {{
            border-color: rgba(239, 68, 68, 0.4);
            color: #fca5a5;
        }}

        .action-btn.danger:active {{
            background: var(--accent-red-dim);
            border-color: var(--accent-red);
        }}

        .chat-stream {{
            height: 180px;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
            padding: 10px;
            overflow-y: auto;
            font-size: 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .msg-bubble {{
            padding: 8px 12px;
            border-radius: 8px;
            max-width: 88%;
            line-height: 1.4;
        }}

        .msg-bubble.user {{
            align-self: flex-end;
            background: var(--accent-green-dim);
            border: 1px solid var(--border-bright);
            color: var(--text-bright);
        }}

        .msg-bubble.hermes {{
            align-self: flex-start;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-subtle);
            color: var(--text-main);
        }}

        .input-bar {{
            display: flex;
            gap: 8px;
        }}

        .text-input {{
            flex: 1;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            color: #ffffff;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13px;
            outline: none;
        }}

        .text-input:focus {{
            border-color: var(--accent-green);
        }}

        .mode-toggle-bar {{
            position: fixed;
            bottom: 12px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(13, 18, 23, 0.95);
            border: 1px solid var(--border-subtle);
            backdrop-filter: blur(8px);
            padding: 6px 12px;
            border-radius: 20px;
            display: flex;
            gap: 8px;
            z-index: 1000;
        }}

        .mode-pill {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
        }}

        .mode-pill.active {{
            background: var(--accent-green-dim);
            color: var(--accent-green);
        }}

        /* Toast Popup */
        #toast-banner {{
            position: fixed;
            top: 16px;
            left: 50%;
            transform: translateX(-50%) translateY(-100px);
            background: #10b981;
            color: #000000;
            padding: 10px 18px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            box-shadow: 0 4px 14px rgba(0,0,0,0.5);
            transition: transform 0.3s cubic-bezier(0.18, 0.89, 0.32, 1.28);
            z-index: 9999;
        }}

        #toast-banner.show {{
            transform: translateX(-50%) translateY(0);
        }}
    </style>
</head>
<body>

    <!-- Toast Notification -->
    <div id="toast-banner">Hermes Connected</div>

    <!-- ── WATCH MODE ── -->
    <div id="view-watch" class="mode-container">
        <div class="watch-hud">
            <div style="font-size: 10px; font-weight: 700; color: var(--accent-green); display: flex; align-items: center; gap: 6px;">
                <span class="watch-status-dot"></span> HERMES WATCH HUD
            </div>
            <div id="watch-time" style="font-size: 20px; font-weight: 700; color: #ffffff;">12:00</div>
            
            <button class="watch-btn" onclick="startVoiceRecording()">
                🎙️ <span id="watch-voice-label">Talk to Hermes</span>
            </button>
            <button class="watch-btn" onclick="pullClipboard()">
                📋 Get PC Clipboard
            </button>
            <button class="watch-btn panic" onclick="triggerPanicStop()">
                🚨 PANIC STOP
            </button>
            
            <div id="watch-response" style="font-size: 10px; color: var(--text-muted); max-height: 40px; overflow: hidden; text-overflow: ellipsis;">
                Ready on wrist
            </div>
        </div>
    </div>

    <!-- ── PHONE / LAPTOP MODE ── -->
    <div id="view-phone" class="mode-container active">
        <div class="app-header">
            <div class="brand-badge">
                <div class="pulse-orb" id="connection-orb"></div>
                <div>
                    <div style="font-size: 14px; font-weight: 700; color: #ffffff;">HERMES COMPANION</div>
                    <div id="hub-label" style="font-size: 11px; color: var(--text-muted);">Host: {host_ip}:{host_port}</div>
                </div>
            </div>
            <div id="battery-tag" style="font-size: 11px; color: var(--accent-green); background: var(--accent-green-dim); padding: 4px 8px; border-radius: 6px;">
                🔋 --%
            </div>
        </div>

        <!-- Unified Clipboard Sync Card -->
        <div class="card">
            <div class="card-title">
                📋 Unified Cross-Device Clipboard
            </div>
            <textarea id="clip-text" class="text-input" style="height: 65px; resize: none;" placeholder="Type or paste to sync with PC clipboard..."></textarea>
            <div class="btn-grid">
                <button class="action-btn" onclick="pushClipboard()">
                    <span>⬆️ Push to PC</span>
                </button>
                <button class="action-btn" onclick="pullClipboard()">
                    <span>⬇️ Pull from PC</span>
                </button>
            </div>
        </div>

        <!-- Hardware & Vision Sensors Card -->
        <div class="card">
            <div class="card-title">
                📸 Sensors & Vision Bridge
            </div>
            <div class="btn-grid">
                <label class="action-btn" style="cursor: pointer;">
                    <input type="file" accept="image/*" capture="environment" style="display: none;" onchange="handlePhotoUpload(this)">
                    <span>📷 Snap for Vision</span>
                </label>
                <button class="action-btn" id="mic-btn" onclick="toggleVoicePrompt()">
                    <span>🎙️ Push to Talk</span>
                </button>
            </div>
            <button class="action-btn danger" onclick="triggerPanicStop()">
                <span>🚨 Emergency Panic Stop</span>
            </button>
        </div>

        <!-- Live Agent Chat Card -->
        <div class="card" style="flex: 1;">
            <div class="card-title">
                ⚡ Hermes Dispatch Stream
            </div>
            <div class="chat-stream" id="chat-stream">
                <div class="msg-bubble hermes">
                    Connected to Hermes Core. You can send prompts, push photos, or sync your clipboard seamlessly.
                </div>
            </div>
            <div class="input-bar">
                <input type="text" id="chat-input" class="text-input" placeholder="Ask Hermes or trigger action..." onkeydown="if(event.key==='Enter') sendPrompt()">
                <button class="action-btn" style="width: 50px;" onclick="sendPrompt()">➤</button>
            </div>
        </div>
    </div>

    <!-- Mode Selector Pills -->
    <div class="mode-toggle-bar">
        <button class="mode-pill active" id="btn-phone-mode" onclick="switchMode('phone')">📱 Mobile</button>
        <button class="mode-pill" id="btn-watch-mode" onclick="switchMode('watch')">⌚ Watch</button>
    </div>

    <script>
        const HOST_IP = '{host_ip}';
        const HOST_PORT = '{host_port}';
        const WS_URL = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/api/mesh/ws';
        
        let ws = null;
        let deviceId = localStorage.getItem('hermes_mesh_id') || ('dev-' + Math.random().toString(36).substring(2, 9));
        localStorage.setItem('hermes_mesh_id', deviceId);

        let isRecording = false;
        let recognition = null;

        // Auto-detect Watch screen (<380px or circular)
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('mode') === 'watch' || window.innerWidth < 340) {{
            switchMode('watch');
        }}

        function switchMode(mode) {{
            document.querySelectorAll('.mode-container').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.mode-pill').forEach(el => el.classList.remove('active'));
            if (mode === 'watch') {{
                document.getElementById('view-watch').classList.add('active');
                document.getElementById('btn-watch-mode').classList.add('active');
            }} else {{
                document.getElementById('view-phone').classList.add('active');
                document.getElementById('btn-phone-mode').classList.add('active');
            }}
        }}

        function showToast(msg) {{
            const t = document.getElementById('toast-banner');
            t.innerText = msg;
            t.classList.add('show');
            if (navigator.vibrate) navigator.vibrate([40]);
            setTimeout(() => t.classList.remove('show'), 2500);
        }}

        // Clock for watch
        function updateTime() {{
            const now = new Date();
            const el = document.getElementById('watch-time');
            if (el) el.innerText = now.toLocaleTimeString([], {{hour: '2-digit', minute:'2-digit'}});
        }}
        setInterval(updateTime, 1000);
        updateTime();

        // Battery monitoring
        if ('getBattery' in navigator) {{
            navigator.getBattery().then(battery => {{
                function updateBattery() {{
                    const lvl = Math.round(battery.level * 100);
                    const bTag = document.getElementById('battery-tag');
                    if (bTag) bTag.innerText = (battery.charging ? '⚡ ' : '🔋 ') + lvl + '%';
                    if (ws && ws.readyState === WebSocket.OPEN) {{
                        ws.send(JSON.stringify({{
                            type: 'telemetry',
                            battery: lvl,
                            is_charging: battery.charging
                        }}));
                    }}
                }}
                updateBattery();
                battery.addEventListener('levelchange', updateBattery);
                battery.addEventListener('chargingchange', updateBattery);
            }});
        }}

        // WebSocket Connection
        function connectMesh() {{
            ws = new WebSocket(WS_URL);

            ws.onopen = () => {{
                document.getElementById('connection-orb').style.background = '#10b981';
                showToast('Connected to Hermes Mesh');
                // Register device
                ws.send(JSON.stringify({{
                    type: 'register',
                    device_id: deviceId,
                    name: (window.innerWidth < 340 ? 'Smartwatch' : 'Smartphone'),
                    device_type: (window.innerWidth < 340 ? 'watch' : 'phone'),
                    user_agent: navigator.userAgent
                }}));
            }};

            ws.onclose = () => {{
                document.getElementById('connection-orb').style.background = '#ef4444';
                setTimeout(connectMesh, 3000);
            }};

            ws.onmessage = (event) => {{
                try {{
                    const data = JSON.parse(event.data);
                    handleMeshEvent(data);
                }} catch (e) {{
                    console.error('Invalid WS payload', e);
                }}
            }};
        }}

        function handleMeshEvent(data) {{
            if (data.type === 'welcome') {{
                if (data.pc_clipboard) {{
                    document.getElementById('clip-text').value = data.pc_clipboard;
                }}
            }} else if (data.type === 'clipboard_update') {{
                document.getElementById('clip-text').value = data.content || '';
                showToast('📋 Clipboard updated from PC');
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(data.content).catch(() => {{}});
                }}
            }} else if (data.type === 'notification') {{
                showToast(data.title + ': ' + data.body);
                if (navigator.vibrate && data.vibrate) navigator.vibrate(data.vibrate);
            }} else if (data.type === 'panic_alert') {{
                showToast('🚨 ' + data.message);
                if (navigator.vibrate) navigator.vibrate([200, 100, 200, 100, 400]);
            }} else if (data.type === 'agent_response') {{
                appendChatMessage('hermes', data.response);
                const wResp = document.getElementById('watch-response');
                if (wResp) wResp.innerText = data.response;
                if (navigator.vibrate) navigator.vibrate([80]);
            }} else if (data.type === 'photo_saved') {{
                showToast(data.message);
                appendChatMessage('hermes', '📸 ' + data.message);
            }}
        }}

        function appendChatMessage(role, text) {{
            const stream = document.getElementById('chat-stream');
            const div = document.createElement('div');
            div.className = 'msg-bubble ' + role;
            div.innerText = text;
            stream.appendChild(div);
            stream.scrollTop = stream.scrollHeight;
        }}

        function sendPrompt() {{
            const input = document.getElementById('chat-input');
            const text = input.value.trim();
            if (!text) return;
            appendChatMessage('user', text);
            input.value = '';

            if (ws && ws.readyState === WebSocket.OPEN) {{
                ws.send(JSON.stringify({{
                    type: 'voice_prompt',
                    prompt: text
                }}));
            }} else {{
                showToast('Hub offline');
            }}
        }}

        function pushClipboard() {{
            const text = document.getElementById('clip-text').value;
            if (!text) return;
            if (ws && ws.readyState === WebSocket.OPEN) {{
                ws.send(JSON.stringify({{
                    type: 'clipboard_push',
                    content: text
                }}));
                showToast('⬆️ Pushed to PC clipboard');
            }}
        }}

        function pullClipboard() {{
            if (ws && ws.readyState === WebSocket.OPEN) {{
                ws.send(JSON.stringify({{
                    type: 'clipboard_pull'
                }}));
                showToast('⬇️ Requested PC clipboard');
            }}
        }}

        function triggerPanicStop() {{
            if (confirm('Engage Emergency Panic Stop on PC?')) {{
                if (ws && ws.readyState === WebSocket.OPEN) {{
                    ws.send(JSON.stringify({{
                        type: 'panic_stop'
                    }}));
                    showToast('🚨 PANIC STOP SENT');
                }}
            }}
        }}

        function handlePhotoUpload(input) {{
            if (input.files && input.files[0]) {{
                const file = input.files[0];
                const reader = new FileReader();
                reader.onload = (e) => {{
                    showToast('Uploading photo to PC...');
                    if (ws && ws.readyState === WebSocket.OPEN) {{
                        ws.send(JSON.stringify({{
                            type: 'camera_photo',
                            photo_data: e.target.result,
                            prompt: 'Analyze camera snap from mobile companion'
                        }}));
                    }}
                }};
                reader.readAsDataURL(file);
            }}
        }}

        function toggleVoicePrompt() {{
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
                const text = prompt('Voice API not supported on this browser. Enter prompt:');
                if (text) {{
                    document.getElementById('chat-input').value = text;
                    sendPrompt();
                }}
                return;
            }}

            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!recognition) {{
                recognition = new SpeechRec();
                recognition.continuous = false;
                recognition.interimResults = false;
                recognition.onstart = () => {{
                    isRecording = true;
                    document.getElementById('mic-btn').style.background = 'rgba(239, 68, 68, 0.2)';
                    document.getElementById('mic-btn').style.borderColor = '#ef4444';
                    showToast('🎙️ Listening...');
                }};
                recognition.onresult = (event) => {{
                    const transcript = event.results[0][0].transcript;
                    document.getElementById('chat-input').value = transcript;
                    sendPrompt();
                }};
                recognition.onend = () => {{
                    isRecording = false;
                    document.getElementById('mic-btn').style.background = '';
                    document.getElementById('mic-btn').style.borderColor = '';
                }};
            }}

            if (isRecording) {{
                recognition.stop();
            }} else {{
                recognition.start();
            }}
        }}

        function startVoiceRecording() {{
            toggleVoicePrompt();
        }}

        // Register Service Worker for PWA
        if ('serviceWorker' in navigator) {{
            navigator.serviceWorker.register('/companion/sw.js').catch(() => {{}});
        }}

        window.onload = connectMesh;
    </script>
</body>
</html>
"""
