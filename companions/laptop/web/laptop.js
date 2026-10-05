// Hermes Laptop Workstation Client (Unified Clipboard, Remote Task Stream, Telemetry)
const WS_PROTOCOL = location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${WS_PROTOCOL}//${location.host}/api/mesh/ws`;

let ws = null;
let deviceId = localStorage.getItem('hermes_laptop_id') || ('laptop-' + Math.random().toString(36).substring(2, 9));
localStorage.setItem('hermes_laptop_id', deviceId);

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
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        document.getElementById('status-orb').style.background = '#10b981';
        showToast('Laptop Connected to Hermes PC Hub');
        ws.send(JSON.stringify({
            type: 'register',
            device_id: deviceId,
            name: 'Laptop Workstation',
            device_type: 'laptop',
            user_agent: navigator.userAgent
        }));
    };

    ws.onclose = () => {
        document.getElementById('status-orb').style.background = '#ef4444';
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
        if (data.pc_clipboard) {
            document.getElementById('clip-area').value = data.pc_clipboard;
        }
        appendLog('SYSTEM', `Handshake verified. Host IP: ${data.host_ip}`);
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
