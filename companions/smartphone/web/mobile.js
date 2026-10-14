// Hermes Smartphone Client Logic (WebSockets, Camera, Clipboard, Voice, Telemetry)
const WS_PROTOCOL = location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${WS_PROTOCOL}//${location.host}/api/mesh/ws`;

let ws = null;
let deviceId = localStorage.getItem('hermes_phone_id') || ('phone-' + Math.random().toString(36).substring(2, 9));
localStorage.setItem('hermes_phone_id', deviceId);

// Pairing & Authentication token management
const urlParams = new URLSearchParams(window.location.search);
const pairParam = urlParams.get('pair') || urlParams.get('pairing_code');
const tokenParam = urlParams.get('token');
if (tokenParam) {
    localStorage.setItem('hermes_phone_token', tokenParam);
}
let authToken = localStorage.getItem('hermes_phone_token') || tokenParam || '';

let isRecording = false;
let recognition = null;
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
                showToast('Hermes Phone app installed!');
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
        if (navigator.vibrate) navigator.vibrate([40]);
        setTimeout(() => t.classList.remove('show'), 2500);
    }
}

// Battery Telemetry
if ('getBattery' in navigator) {
    navigator.getBattery().then(battery => {
        function updateBattery() {
            const lvl = Math.round(battery.level * 100);
            const bTag = document.getElementById('battery-tag');
            if (bTag) bTag.innerText = (battery.charging ? '⚡ ' : '🔋 ') + lvl + '%';
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

// WebSocket Connection
function connectPhone() {
    let wsUrl = WS_URL;
    const q = [];
    if (authToken) q.push(`token=${encodeURIComponent(authToken)}`);
    if (pairParam) q.push(`pair=${encodeURIComponent(pairParam)}`);
    if (q.length > 0) wsUrl += `?${q.join('&')}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        document.getElementById('connection-orb').style.background = '#10b981';
        showToast('Connected to Hermes Mesh');
        const regPayload = {
            type: 'register',
            device_id: deviceId,
            name: 'Smartphone Companion',
            device_type: 'smartphone',
            user_agent: navigator.userAgent
        };
        if (authToken) regPayload.token = authToken;
        if (pairParam) regPayload.pair = pairParam;
        ws.send(JSON.stringify(regPayload));
    };

    ws.onclose = (event) => {
        document.getElementById('connection-orb').style.background = '#ef4444';
        if (event && event.code === 4001) {
            showToast('⚠️ Unauthorized. Please pair from PC dashboard.');
            setTimeout(connectPhone, 8000);
            return;
        }
        setTimeout(connectPhone, 3000);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleMeshEvent(data);
        } catch (e) {
            console.error('Invalid WS payload', e);
        }
    };
}

function handleMeshEvent(data) {
    if (data.type === 'welcome') {
        if (data.auth_token) {
            authToken = data.auth_token;
            localStorage.setItem('hermes_phone_token', authToken);
            if (pairParam && window.history && window.history.replaceState) {
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        }
        if (data.pc_clipboard) {
            document.getElementById('clip-text').value = data.pc_clipboard;
        }
    } else if (data.type === 'auth_error') {
        showToast('❌ ' + (data.message || 'Authentication error'));
        localStorage.removeItem('hermes_phone_token');
        authToken = '';
    } else if (data.type === 'clipboard_update') {
        document.getElementById('clip-text').value = data.content || '';
        showToast('📋 Clipboard updated from PC');
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(data.content).catch(() => {});
        }
    } else if (data.type === 'notification') {
        showToast(data.title + ': ' + data.body);
        if (navigator.vibrate && data.vibrate) navigator.vibrate(data.vibrate);
    } else if (data.type === 'fast_action_executed') {
        showToast('⚡ Fast Action: ' + (data.tool || 'Executed'));
        appendChatMessage('hermes', '⚡ [System 1 Executed (' + (data.tool || '') + ')]: ' + JSON.stringify(data.result || {}));
        if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
    } else if (data.type === 'panic_alert') {
        showToast('🚨 ' + data.message);
        if (navigator.vibrate) navigator.vibrate([200, 100, 200, 100, 400]);
    } else if (data.type === 'agent_response') {
        appendChatMessage('hermes', data.response);
        if (navigator.vibrate) navigator.vibrate([80]);
    } else if (data.type === 'photo_saved') {
        showToast(data.message);
        appendChatMessage('hermes', '📸 ' + data.message);
    }
}

function appendChatMessage(role, text) {
    const stream = document.getElementById('chat-stream');
    const div = document.createElement('div');
    div.className = 'msg-bubble ' + role;
    div.innerText = text;
    stream.appendChild(div);
    stream.scrollTop = stream.scrollHeight;
}

function sendPrompt() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    appendChatMessage('user', text);
    input.value = '';

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'voice_prompt',
            prompt: text
        }));
    } else {
        showToast('Hub offline');
    }
}

function pushClipboard() {
    const text = document.getElementById('clip-text').value;
    if (!text) return;
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'clipboard_push',
            content: text
        }));
        showToast('⬆️ Pushed to PC clipboard');
    }
}

function pullClipboard() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'clipboard_pull' }));
        showToast('⬇️ Requested PC clipboard');
    }
}

function triggerPanicStop() {
    if (confirm('Engage Emergency Panic Stop on PC?')) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'panic_stop' }));
            showToast('🚨 PANIC STOP SENT');
        }
    }
}

function handlePhotoUpload(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const reader = new FileReader();
        reader.onload = (e) => {
            showToast('Uploading photo to PC...');
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'camera_photo',
                    photo_data: e.target.result,
                    prompt: 'Analyze camera snap from mobile companion'
                }));
            }
        };
        reader.readAsDataURL(file);
    }
}

function toggleVoicePrompt() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        const text = prompt('Voice API not supported on this browser. Enter prompt:');
        if (text) {
            document.getElementById('chat-input').value = text;
            sendPrompt();
        }
        return;
    }

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!recognition) {
        recognition = new SpeechRec();
        recognition.continuous = false;
        recognition.interimResults = true;

        let lastSentPartial = '';
        let lastPartialTime = 0;

        recognition.onstart = () => {
            isRecording = true;
            lastSentPartial = '';
            lastPartialTime = 0;
            document.getElementById('mic-btn').style.background = 'rgba(239, 68, 68, 0.2)';
            document.getElementById('mic-btn').style.borderColor = '#ef4444';
            showToast('🎙️ Listening...');
        };
        recognition.onresult = (event) => {
            let transcript = '';
            for (let i = 0; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            const clean = transcript.trim();
            if (clean) {
                document.getElementById('chat-input').value = clean;
                const now = Date.now();
                if (ws && ws.readyState === WebSocket.OPEN && clean.length >= 3) {
                    if (clean !== lastSentPartial && (now - lastPartialTime >= 140)) {
                        lastSentPartial = clean;
                        lastPartialTime = now;
                        ws.send(JSON.stringify({
                            type: 'voice_partial',
                            transcript: clean,
                            timestamp: now
                        }));
                    }
                }
            }
        };
        recognition.onend = () => {
            isRecording = false;
            document.getElementById('mic-btn').style.background = '';
            document.getElementById('mic-btn').style.borderColor = '';
            const finalVal = document.getElementById('chat-input').value.trim();
            if (finalVal) {
                sendPrompt();
            }
        };
    }

    if (isRecording) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

// ── LIVE SCREEN STREAMING & DESKTOP CONTROL (MUSE "WATCH HERMES WORK") ─────────
let isStreamPaused = false;
let currentMonitor = '2';
let activityPollInterval = null;

function toggleScreenStream() {
    const img = document.getElementById('desktop-stream-img');
    const btn = document.getElementById('stream-toggle-btn');
    const hudStatus = document.getElementById('screen-hud-status');
    if (!img) return;

    isStreamPaused = !isStreamPaused;
    if (isStreamPaused) {
        img.dataset.origSrc = img.src;
        img.src = `/api/desktop/snapshot?monitor=${currentMonitor}&max_width=960&t=${Date.now()}`;
        if (btn) btn.innerText = '▶️ Resume';
        if (hudStatus) {
            hudStatus.innerText = '⏸️ PAUSED';
            hudStatus.style.color = 'var(--text-muted)';
        }
        showToast('Screen stream paused');
    } else {
        img.src = `/api/desktop/stream?monitor=${currentMonitor}&fps=8&max_width=960&quality=60&t=${Date.now()}`;
        if (btn) btn.innerText = '⏸️ Pause';
        if (hudStatus) {
            hudStatus.innerText = '● STREAMING';
            hudStatus.style.color = 'var(--accent-emerald)';
        }
        showToast('Screen stream resumed');
    }
}

function changeMonitor(val) {
    currentMonitor = val;
    const img = document.getElementById('desktop-stream-img');
    if (!img) return;
    if (isStreamPaused) {
        img.src = `/api/desktop/snapshot?monitor=${currentMonitor}&max_width=960&t=${Date.now()}`;
    } else {
        img.src = `/api/desktop/stream?monitor=${currentMonitor}&fps=8&max_width=960&quality=60&t=${Date.now()}`;
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

    // Show visual click indicator ripple
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
            if (navigator.vibrate) navigator.vibrate([30]);
            showToast(`Clicked PC [${Math.round(normX * 100)}%, ${Math.round(normY * 100)}%]`);
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
            if (navigator.vibrate) navigator.vibrate([25]);
            showToast(`Sent key: ${keyName}`);
        } else {
            showToast(`Key error: ${data.message || 'failed'}`);
        }
    } catch (e) {
        showToast(`Failed to send key: ${e.message}`);
    }
}

async function triggerPhoneWake() {
    showToast('⚡ Broadcasting Wake-on-LAN Magic Packet...');
    try {
        const res = await fetch('/api/power/wake', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mac: '00:13:EF:60:04:42' })
        });
        const data = await res.json();
        if (data.status === 'success') {
            if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
            showToast('✅ Wake Packet Sent! PC waking up.');
        } else {
            showToast(`Wake status: ${data.message || 'sent'}`);
        }
    } catch (e) {
        showToast('Wake request dispatched via subnet');
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
            const shortTitle = title.length > 35 ? title.substring(0, 35) + '...' : title;
            badge.innerText = `Focused: ${shortTitle}`;
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

// Service worker registration
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/companions/smartphone/sw.js').catch(() => {});
}

window.onload = () => {
    connectPhone();
    startDesktopActivityPolling();
};
