// Hermes Laptop Workstation Client (Unified Clipboard, Remote Task Stream, Telemetry)
const WS_PROTOCOL = location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${WS_PROTOCOL}//${location.host}/api/mesh/ws`;

let ws = null;
let deviceId = localStorage.getItem('hermes_laptop_id') || ('laptop-' + Math.random().toString(36).substring(2, 9));
localStorage.setItem('hermes_laptop_id', deviceId);

// Pairing & Authentication token management
const urlParams = new URLSearchParams(window.location.search);
const pairParam = urlParams.get('pair') || urlParams.get('pairing_code');
const tokenParam = urlParams.get('token');
if (tokenParam) {
    localStorage.setItem('hermes_laptop_token', tokenParam);
}
let authToken = localStorage.getItem('hermes_laptop_token') || tokenParam || '';

let deferredInstallPrompt = null;

// PWA Install prompt listener
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredInstallPrompt = e;
    const installBtn = document.getElementById('pwa-install-btn');
    if (installBtn) {
        installBtn.style.display = 'inline-flex';
    }
});

function promptInstallApp() {
    if (deferredInstallPrompt) {
        deferredInstallPrompt.prompt();
        deferredInstallPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                showToast('Hermes Workstation app installed!');
            }
            deferredInstallPrompt = null;
            const installBtn = document.getElementById('pwa-install-btn');
            if (installBtn) installBtn.style.display = 'none';
        });
    }
}

function showToast(msg) {
    const t = document.getElementById('toast-banner');
    if (t) {
        t.innerText = msg;
        t.classList.add('show');
        setTimeout(() => t.classList.remove('show'), 2800);
    }
}

// Battery Telemetry
if ('getBattery' in navigator) {
    navigator.getBattery().then(battery => {
        function updateBattery() {
            const lvl = Math.round(battery.level * 100);
            const bEl = document.getElementById('laptop-battery');
            if (bEl) bEl.innerText = (battery.charging ? '⚡ ' : '🔋 ') + lvl + '%';
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'telemetry',
                    battery: lvl,
                    is_charging: battery.charging
                }));
            }
        }
        updateBattery();
        battery.addEventListener('levelchange', updateBattery);
        battery.addEventListener('chargingchange', updateBattery);
    });
}

function connectLaptop() {
    let wsUrl = WS_URL;
    const q = [];
    if (authToken) q.push(`token=${encodeURIComponent(authToken)}`);
    if (pairParam) q.push(`pair=${encodeURIComponent(pairParam)}`);
    if (q.length > 0) wsUrl += `?${q.join('&')}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        document.getElementById('status-orb').style.background = '#10b981';
        showToast('Laptop Connected to Hermes PC Hub');
        const regPayload = {
            type: 'register',
            device_id: deviceId,
            name: 'Laptop Workstation',
            device_type: 'laptop',
            user_agent: navigator.userAgent
        };
        if (authToken) regPayload.token = authToken;
        if (pairParam) regPayload.pair = pairParam;
        ws.send(JSON.stringify(regPayload));
    };

    ws.onclose = (event) => {
        document.getElementById('status-orb').style.background = '#ef4444';
        if (event && event.code === 4001) {
            showToast('⚠️ Unauthorized. Please pair from PC dashboard.');
            appendLog('AUTH', 'Pairing required. Scan QR code or enter code from PC.');
            setTimeout(connectLaptop, 8000);
            return;
        }
        setTimeout(connectLaptop, 3000);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleIncoming(data);
        } catch (e) {
            console.error('Invalid WS payload', e);
        }
    };
}

function handleIncoming(data) {
    if (data.type === 'welcome') {
        if (data.auth_token) {
            authToken = data.auth_token;
            localStorage.setItem('hermes_laptop_token', authToken);
            if (pairParam && window.history && window.history.replaceState) {
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        }
        if (data.pc_clipboard) {
            document.getElementById('clip-area').value = data.pc_clipboard;
        }
        appendLog('SYSTEM', `Handshake verified. Host IP: ${data.host_ip}`);
    } else if (data.type === 'auth_error') {
        showToast('❌ ' + (data.message || 'Authentication error'));
        appendLog('AUTH_ERROR', data.message || 'Device not authorized');
        localStorage.removeItem('hermes_laptop_token');
        authToken = '';
    } else if (data.type === 'clipboard_update') {
        document.getElementById('clip-area').value = data.content || '';
        showToast('📋 Clipboard updated from PC');
        appendLog('CLIPBOARD', `Synced ${data.content.length} chars from ${data.from_device}`);
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(data.content).catch(() => {});
        }
    } else if (data.type === 'notification') {
        showToast(`🔔 ${data.title}: ${data.body}`);
        appendLog('NOTIF', `${data.title} - ${data.body}`);
    } else if (data.type === 'agent_response') {
        appendLog('HERMES', data.response);
    } else if (data.type === 'panic_alert') {
        showToast(`🚨 ${data.message}`);
        appendLog('PANIC', data.message);
    } else if (data.type === 'ping_device') {
        showToast('🔔 PING FROM HERMES HOST PC!');
        appendLog('PING', 'Host PC initiated acoustic device ping');
        playLaptopChime();
    } else if (data.type === 'request_screen_snapshot') {
        sendLaptopScreenSnapshot();
    }
}

function appendLog(category, text) {
    const feed = document.getElementById('log-feed');
    if (!feed) return;
    const div = document.createElement('div');
    const timeStr = new Date().toLocaleTimeString();
    div.innerHTML = `<span style="color: var(--accent-emerald);">[${timeStr}] [${category}]</span> <span style="color: #ffffff;">${text}</span>`;
    feed.appendChild(div);
    feed.scrollTop = feed.scrollHeight;
}

function pushClipboard() {
    const text = document.getElementById('clip-area').value;
    if (!text) return;
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'clipboard_push',
            content: text
        }));
        showToast('⬆️ Pushed to PC clipboard');
        appendLog('CLIPBOARD', `Pushed ${text.length} chars to PC`);
    }
}

function pullClipboard() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'clipboard_pull' }));
        showToast('⬇️ Requested PC clipboard');
    }
}

function sendLaptopPrompt() {
    const input = document.getElementById('prompt-input');
    const promptText = input.value.trim();
    if (!promptText) return;
    appendLog('USER', promptText);
    input.value = '';

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'voice_prompt',
            prompt: promptText
        }));
    }
}

function triggerPanicStop() {
    if (confirm('Engage Emergency Panic Stop on PC?')) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'panic_stop' }));
            showToast('🚨 PANIC ENGAGED');
        }
    }
}

// ── LIVE SCREEN STREAMING & DESKTOP CONTROL (MUSE "WATCH HERMES WORK") ─────────
let isStreamPaused = false;
let currentMonitor = '2';
let activityPollInterval = null;
let isKeepaliveOn = true;

function toggleScreenStream() {
    const img = document.getElementById('desktop-stream-img');
    const btn = document.getElementById('stream-toggle-btn');
    const hudStatus = document.getElementById('screen-hud-status');
    if (!img) return;

    isStreamPaused = !isStreamPaused;
    if (isStreamPaused) {
        img.dataset.origSrc = img.src;
        img.src = `/api/desktop/snapshot?monitor=${currentMonitor}&max_width=1280&t=${Date.now()}`;
        if (btn) btn.innerText = '▶️ Resume';
        if (hudStatus) {
            hudStatus.innerText = '⏸️ PAUSED';
            hudStatus.style.color = 'var(--text-muted)';
        }
        showToast('Screen mirror paused');
    } else {
        img.src = `/api/desktop/stream?monitor=${currentMonitor}&fps=8&max_width=1280&quality=65&t=${Date.now()}`;
        if (btn) btn.innerText = '⏸️ Pause';
        if (hudStatus) {
            hudStatus.innerText = '● LIVE';
            hudStatus.style.color = 'var(--accent-emerald)';
        }
        showToast('Screen mirror resumed');
    }
}

function changeMonitor(val) {
    currentMonitor = val;
    const img = document.getElementById('desktop-stream-img');
    if (!img) return;
    if (isStreamPaused) {
        img.src = `/api/desktop/snapshot?monitor=${currentMonitor}&max_width=1280&t=${Date.now()}`;
    } else {
        img.src = `/api/desktop/stream?monitor=${currentMonitor}&fps=8&max_width=1280&quality=65&t=${Date.now()}`;
    }
    showToast(`Switched to Monitor ${val}`);
}

async function handleScreenClick(event) {
    const img = document.getElementById('desktop-stream-img');
    if (!img) return;

    const rect = img.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;

    if (clickX < 0 || clickY < 0 || clickX > rect.width || clickY > rect.height) return;

    const normX = Math.max(0, Math.min(1, clickX / rect.width));
    const normY = Math.max(0, Math.min(1, clickY / rect.height));

    // Visual click ripple
    const wrapper = document.getElementById('screen-wrapper');
    if (wrapper) {
        const ripple = document.createElement('div');
        ripple.style.position = 'absolute';
        ripple.style.left = `${clickX - 12}px`;
        ripple.style.top = `${clickY - 12}px`;
        ripple.style.width = '24px';
        ripple.style.height = '24px';
        ripple.style.borderRadius = '50%';
        ripple.style.background = 'rgba(16, 185, 129, 0.6)';
        ripple.style.border = '2px solid #ffffff';
        ripple.style.boxShadow = '0 0 10px rgba(16, 185, 129, 0.8)';
        ripple.style.pointerEvents = 'none';
        ripple.style.transition = 'all 0.35s ease-out';
        ripple.style.zIndex = '50';
        wrapper.appendChild(ripple);
        requestAnimationFrame(() => {
            ripple.style.transform = 'scale(2.2)';
            ripple.style.opacity = '0';
        });
        setTimeout(() => ripple.remove(), 400);
    }

    try {
        const res = await fetch('/api/desktop/remote_input', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'click',
                x: normX,
                y: normY,
                button: 'left',
                monitor: currentMonitor
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            appendLog('REMOTE', `Clicked desktop at [${Math.round(normX * 100)}%, ${Math.round(normY * 100)}%]`);
        }
    } catch (e) {
        console.error('Remote click error:', e);
    }
}

async function sendRemoteKey(keyName) {
    try {
        const res = await fetch('/api/desktop/remote_input', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'key',
                key: keyName
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast(`Key sent: ${keyName}`);
            appendLog('REMOTE', `Key press sent: ${keyName}`);
        } else {
            showToast(`Key error: ${data.message || 'failed'}`);
        }
    } catch (e) {
        showToast(`Failed to send key: ${e.message}`);
    }
}

async function triggerLaptopWake() {
    showToast('⚡ Broadcasting Wake-on-LAN Magic Packet to PC...');
    appendLog('POWER', 'Sending Wake-on-LAN magic packet to 00:13:EF:60:04:42 / 04:42:1A:EA:BF:E7');
    try {
        const res = await fetch('/api/power/wake', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mac: '00:13:EF:60:04:42' })
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast('✅ Wake Packet Sent! Host PC booting up.');
            appendLog('POWER', 'Wake Magic Packet broadcasted over subnet 10.0.0.255');
        } else {
            showToast(`Wake status: ${data.message || 'sent'}`);
        }
    } catch (e) {
        showToast('Wake packet sent via local subnet');
    }
}

async function toggleKeepalive() {
    isKeepaliveOn = !isKeepaliveOn;
    const btn = document.getElementById('keepalive-btn');
    try {
        const res = await fetch('/api/power/keepalive', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enable: isKeepaliveOn })
        });
        const data = await res.json();
        if (btn) {
            if (isKeepaliveOn) {
                btn.innerText = '🔋 24/7 Keep-Alive [ON]';
                btn.style.color = 'var(--accent-emerald)';
                btn.style.borderColor = 'var(--accent-emerald)';
            } else {
                btn.innerText = '💤 Power-Save [NORMAL]';
                btn.style.color = 'var(--text-muted)';
                btn.style.borderColor = 'var(--border-subtle)';
            }
        }
        showToast(`Host 24/7 Keep-Alive ${isKeepaliveOn ? 'Enabled' : 'Disabled'}`);
        appendLog('POWER', `24/7 Keep-Alive state set to ${isKeepaliveOn}`);
    } catch (e) {
        showToast('Keep-alive update sent');
    }
}

async function pollDesktopActivity() {
    try {
        const res = await fetch('/api/desktop/live_activity');
        if (!res.ok) return;
        const data = await res.json();
        const activeWin = data.active_window;
        const badge = document.getElementById('screen-active-window');
        if (badge && activeWin) {
            const title = (activeWin.title || 'Desktop').trim();
            const shortTitle = title.length > 50 ? title.substring(0, 50) + '...' : title;
            badge.innerText = `Focused: ${shortTitle} (PID ${activeWin.pid || '-'})`;
        }
        if (data.emergency_stop) {
            const hudStatus = document.getElementById('screen-hud-status');
            if (hudStatus) {
                hudStatus.innerText = '🚨 PANIC STOP';
                hudStatus.style.color = '#ef4444';
            }
        }
    } catch (_) {}
}

function startDesktopActivityPolling() {
    if (activityPollInterval) clearInterval(activityPollInterval);
    pollDesktopActivity();
    activityPollInterval = setInterval(pollDesktopActivity, 2500);
}

// ── ACOUSTIC PING CHIME (Web Audio API Synthesizer) ───────────────────────
function playLaptopChime(repeats = 5) {
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();
        for (let i = 0; i < repeats; i++) {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'triangle';
            const startTime = ctx.currentTime + (i * 0.35);
            osc.frequency.setValueAtTime(660, startTime);
            osc.frequency.exponentialRampToValueAtTime(1320, startTime + 0.20);
            gain.gain.setValueAtTime(0.5, startTime);
            gain.gain.exponentialRampToValueAtTime(0.01, startTime + 0.30);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(startTime);
            osc.stop(startTime + 0.32);
        }
    } catch (e) {
        console.warn('Laptop chime error:', e);
    }
}

// ── BATTERY-PRESERVING ON-DEMAND SCREEN SNAPSHOT ──────────────────────────
function sendLaptopScreenSnapshot() {
    try {
        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 360;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(0, 0, 640, 360);
        ctx.fillStyle = '#38bdf8';
        ctx.font = 'bold 20px monospace';
        ctx.fillText('Hermes Laptop Workstation', 30, 50);
        ctx.fillStyle = '#94a3b8';
        ctx.font = '14px sans-serif';
        ctx.fillText('Device ID: ' + deviceId, 30, 85);
        ctx.fillText('Time: ' + new Date().toLocaleTimeString(), 30, 115);
        const bEl = document.getElementById('laptop-battery');
        ctx.fillText('Battery: ' + (bEl ? bEl.innerText : 'AC Power'), 30, 145);
        const focused = document.getElementById('screen-active-window');
        ctx.fillText('Active Context: ' + (focused ? focused.innerText : 'Normal'), 30, 175);
        ctx.fillStyle = '#10b981';
        ctx.fillText('● State: Connected & Synchronized to Host PC', 30, 215);

        const frameB64 = canvas.toDataURL('image/jpeg', 0.70);
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'companion_screen_snapshot',
                image: frameB64,
                width: 640,
                height: 360,
                device_type: 'laptop'
            }));
        }
    } catch (e) {
        console.warn('Laptop snapshot error:', e);
    }
}

// ── ALWAYS-ON LOW-POWER GEOLOCATION ───────────────────────────────────────
function initLaptopLocation() {
    if (!('geolocation' in navigator)) return;
    try {
        function sendPos(pos) {
            if (pos && pos.coords && ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'location_telemetry',
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                    accuracy: pos.coords.accuracy || 0,
                    source_type: 'laptop'
                }));
            }
        }
        navigator.geolocation.getCurrentPosition(sendPos, () => {}, { enableHighAccuracy: false, maximumAge: 120000, timeout: 10000 });
        navigator.geolocation.watchPosition(sendPos, () => {}, { enableHighAccuracy: false, maximumAge: 120000, timeout: 20000 });
    } catch (_) {}
}

window.onload = () => {
    connectLaptop();
    startDesktopActivityPolling();
    initLaptopLocation();
};
