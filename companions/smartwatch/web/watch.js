// Hermes Smartwatch Client Logic (WebSockets, Wrist Haptics, Speech-to-Text)
const WS_PROTOCOL = location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${WS_PROTOCOL}//${location.host}/api/mesh/ws`;

let ws = null;
let deviceId = localStorage.getItem('hermes_watch_id') || ('watch-' + Math.random().toString(36).substring(2, 8));
localStorage.setItem('hermes_watch_id', deviceId);

// Pairing & Authentication token management
const urlParams = new URLSearchParams(window.location.search);
const pairParam = urlParams.get('pair') || urlParams.get('pairing_code');
const tokenParam = urlParams.get('token');
if (tokenParam) {
    localStorage.setItem('hermes_watch_token', tokenParam);
}
let authToken = localStorage.getItem('hermes_watch_token') || tokenParam || '';

let isListening = false;
let recognition = null;

// Clock updates
function updateClock() {
    const now = new Date();
    const clockEl = document.getElementById('watch-clock');
    if (clockEl) {
        clockEl.innerText = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
}
setInterval(updateClock, 1000);
updateClock();

function showWatchToast(text, duration = 2000) {
    const toast = document.getElementById('watch-toast');
    if (toast) {
        toast.innerText = text;
        toast.classList.add('active');
        vibrate([50]);
        setTimeout(() => toast.classList.remove('active'), duration);
    }
}

function vibrate(pattern) {
    if (navigator.vibrate) {
        navigator.vibrate(pattern);
    }
}

// Battery Telemetry
if ('getBattery' in navigator) {
    navigator.getBattery().then(battery => {
        function sendBattery() {
            const level = Math.round(battery.level * 100);
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'telemetry',
                    battery: level,
                    is_charging: battery.charging
                }));
            }
        }
        sendBattery();
        battery.addEventListener('levelchange', sendBattery);
        battery.addEventListener('chargingchange', sendBattery);
    });
}

// WebSocket Connection
function connectWatch() {
    let wsUrl = WS_URL;
    const q = [];
    if (authToken) q.push(`token=${encodeURIComponent(authToken)}`);
    if (pairParam) q.push(`pair=${encodeURIComponent(pairParam)}`);
    if (q.length > 0) wsUrl += `?${q.join('&')}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        document.getElementById('status-dot').style.background = '#10b981';
        showWatchToast('Wrist Connected');
        vibrate([80]);

        const regPayload = {
            type: 'register',
            device_id: deviceId,
            name: 'Smartwatch HUD',
            device_type: 'smartwatch',
            user_agent: navigator.userAgent
        };
        if (authToken) regPayload.token = authToken;
        if (pairParam) regPayload.pair = pairParam;
        ws.send(JSON.stringify(regPayload));
    };

    ws.onclose = (event) => {
        document.getElementById('status-dot').style.background = '#ef4444';
        if (event && event.code === 4001) {
            showWatchToast('⚠️ Pair from PC');
            const footer = document.getElementById('watch-footer');
            if (footer) footer.innerText = 'Pairing required on PC dashboard';
            setTimeout(connectWatch, 8000);
            return;
        }
        setTimeout(connectWatch, 3000);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleIncomingPacket(data);
        } catch (e) {
            console.error('Invalid watch packet', e);
        }
    };
}

function handleIncomingPacket(data) {
    const footer = document.getElementById('watch-footer');
    if (data.type === 'welcome') {
        if (data.auth_token) {
            authToken = data.auth_token;
            localStorage.setItem('hermes_watch_token', authToken);
            if (pairParam && window.history && window.history.replaceState) {
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        }
        if (footer) footer.innerText = 'Ready on wrist';
    } else if (data.type === 'auth_error') {
        showWatchToast('❌ Unpaired');
        if (footer) footer.innerText = 'Pair with PC QR code';
        localStorage.removeItem('hermes_watch_token');
        authToken = '';
    } else if (data.type === 'notification') {
        showWatchToast(data.title || 'Notification');
        vibrate(data.vibrate || [100, 50, 100]);
        if (footer) footer.innerText = data.body || '';
    } else if (data.type === 'panic_alert') {
        showWatchToast('🚨 EMERGENCY STOP');
        vibrate([300, 100, 300, 100, 500]);
        if (footer) footer.innerText = 'Panic Stop Active';
    } else if (data.type === 'agent_response') {
        showWatchToast('Agent Answer');
        vibrate([100]);
        if (footer) footer.innerText = data.response || '';
    } else if (data.type === 'clipboard_update') {
        showWatchToast('PC Clip Copied');
        vibrate([60]);
        if (footer) footer.innerText = `Clip: ${data.content.substring(0, 35)}...`;
    }
}

// 1. Grab PC Clipboard
function grabPcClipboard() {
    vibrate([40]);
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'clipboard_pull' }));
        showWatchToast('Fetching clip...');
    }
}

// 2. Trigger Panic Stop
function panicStop() {
    vibrate([200]);
    if (confirm('Engage Emergency Panic Stop on PC?')) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'panic_stop' }));
            showWatchToast('🚨 PANIC ENGAGED');
        }
    }
}

// 3. Voice Input to Hermes
function startVoicePrompt() {
    vibrate([40]);
    const footer = document.getElementById('watch-footer');

    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        const text = prompt('Voice API not available. Speak prompt:');
        if (text) sendWatchPrompt(text);
        return;
    }

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!recognition) {
        recognition = new SpeechRec();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.onstart = () => {
            isListening = true;
            document.getElementById('voice-btn').style.background = 'rgba(239, 68, 68, 0.3)';
            showWatchToast('🎙️ Listening...');
            vibrate([60]);
        };
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (footer) footer.innerText = `You: ${transcript}`;
            sendWatchPrompt(transcript);
        };
        recognition.onend = () => {
            isListening = false;
            document.getElementById('voice-btn').style.background = '';
        };
    }

    if (isListening) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

function sendWatchPrompt(promptText) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'voice_prompt',
            prompt: promptText
        }));
        showWatchToast('Sent to Hermes');
        vibrate([50]);
    }
}

window.onload = connectWatch;
