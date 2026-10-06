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

window.onload = connectLaptop;
