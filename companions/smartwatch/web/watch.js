// Hermes Smartwatch Client Logic (Galaxy Watch / Wear OS / OLED Wrist HUD)
// Optimized for Push-to-Send Voice Notes, Wrist Haptics, and Shared Clipboard
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
let isHolding = false;
let currentTranscript = '';
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
        try {
            navigator.vibrate(pattern);
        } catch (_) {}
    }
}

// Battery Telemetry
if ('getBattery' in navigator) {
    navigator.getBattery().then(battery => {
        function sendBattery() {
            const level = Math.round(battery.level * 100);
            const pill = document.getElementById('battery-pill');
            if (pill) {
                pill.innerText = (battery.charging ? '⚡ ' : '🔋 ') + level + '%';
            }
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
        const dot = document.getElementById('status-dot');
        const stText = document.getElementById('status-text');
        if (dot) dot.style.background = '#10b981';
        if (stText) stText.innerText = 'ONLINE';
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
        const dot = document.getElementById('status-dot');
        const stText = document.getElementById('status-text');
        if (dot) dot.style.background = '#ef4444';
        if (stText) stText.innerText = 'OFFLINE';

        if (event && event.code === 4001) {
            showWatchToast('⚠️ Pair from PC');
            setCaption('Scan QR code on PC');
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
    if (data.type === 'welcome') {
        if (data.auth_token) {
            authToken = data.auth_token;
            localStorage.setItem('hermes_watch_token', authToken);
            if (pairParam && window.history && window.history.replaceState) {
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        }
        setCaption('Hold to Talk');
    } else if (data.type === 'auth_error') {
        showWatchToast('❌ Unpaired');
        setCaption('Pair with PC QR code');
        localStorage.removeItem('hermes_watch_token');
        authToken = '';
    } else if (data.type === 'notification') {
        showWatchToast(data.title || 'Notification');
        vibrate(data.vibrate || [100, 50, 100]);
        displayAgentReply(data.body || data.title || '');
    } else if (data.type === 'panic_alert') {
        showWatchToast('🚨 EMERGENCY STOP');
        vibrate([300, 100, 300, 100, 500]);
        setCaption('Panic Stop Active');
    } else if (data.type === 'agent_response') {
        displayAgentReply(data.response || 'Action completed.');
        vibrate([80]);
        speakAloud(data.response);
    } else if (data.type === 'clipboard_update') {
        showWatchToast('📋 PC Clip Synced');
        vibrate([60]);
        setCaption(`Clip: ${(data.content || '').substring(0, 20)}...`);
        setTimeout(() => setCaption('Hold to Talk'), 3000);
    }
}

function setCaption(text, isLive = false) {
    const caption = document.getElementById('voice-caption');
    if (caption) {
        caption.innerText = text;
        if (isLive) {
            caption.classList.add('live');
        } else {
            caption.classList.remove('live');
        }
    }
}

// Agent Reply Presentation & TTS
function displayAgentReply(text) {
    const modal = document.getElementById('reply-modal');
    const replyText = document.getElementById('reply-text');
    if (modal && replyText) {
        replyText.innerText = text;
        modal.classList.add('show');
    }
    setCaption('Answer received');
}

function dismissReplyModal() {
    const modal = document.getElementById('reply-modal');
    if (modal) {
        modal.classList.remove('show');
    }
    setCaption('Hold to Talk');
}

function speakAloud(text) {
    if ('speechSynthesis' in window && text) {
        try {
            const cleanText = text.replace(/[*#`_]/g, '').substring(0, 140);
            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.rate = 1.05;
            window.speechSynthesis.speak(utterance);
        } catch (_) {}
    }
}

// ── PUSH-TO-SEND VOICE NOTE ENGINE ──────────────────────────────────────────
function initSpeechRecognition() {
    if (recognition) return recognition;
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) return null;

    recognition = new SpeechRec();
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onstart = () => {
        isListening = true;
        currentTranscript = '';
        updateVoiceVisuals(true);
        setCaption('Listening...', true);
    };

    recognition.onresult = (event) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        currentTranscript = transcript.trim();
        if (currentTranscript) {
            setCaption(currentTranscript, true);
        }
    };

    recognition.onerror = (e) => {
        console.warn('Speech error', e);
        updateVoiceVisuals(false);
        setCaption('Hold to Talk');
        isListening = false;
    };

    recognition.onend = () => {
        isListening = false;
        updateVoiceVisuals(false);
        if (currentTranscript) {
            sendWatchPrompt(currentTranscript);
            currentTranscript = '';
        } else {
            setCaption('Hold to Talk');
        }
    };

    return recognition;
}

function updateVoiceVisuals(active) {
    const btn = document.getElementById('voice-core-btn');
    const ripples = document.querySelectorAll('.voice-ripple');
    if (btn) {
        if (active) {
            btn.classList.add('recording');
        } else {
            btn.classList.remove('recording');
        }
    }
    ripples.forEach(r => {
        if (active) r.classList.add('active');
        else r.classList.remove('active');
    });
}

function startPushToTalk() {
    if (isListening) return;
    vibrate([40]);

    const rec = initSpeechRecognition();
    if (rec) {
        try {
            rec.start();
        } catch (_) {}
    } else {
        const text = prompt('Enter message for Hermes:');
        if (text) sendWatchPrompt(text);
    }
}

function stopPushToTalk() {
    if (!isListening) return;
    vibrate([40, 40]);
    setCaption('Sending to Hermes...');

    if (recognition) {
        try {
            recognition.stop();
        } catch (_) {}
    }
}

function toggleVoicePrompt() {
    if (isListening) {
        stopPushToTalk();
    } else {
        startPushToTalk();
    }
}

// Backward-compatible alias for test suite
function startVoicePrompt() {
    toggleVoicePrompt();
}

function sendWatchPrompt(promptText) {
    if (!promptText) return;
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'voice_prompt',
            prompt: promptText
        }));
        showWatchToast('Dispatched 🚀');
        vibrate([50]);
        setCaption('Waiting for Hermes...');
    } else {
        showWatchToast('Mesh offline');
        setCaption('Mesh offline');
    }
}

// ── FLANKING WRIST ACTIONS ──────────────────────────────────────────────────
function grabPcClipboard() {
    vibrate([40]);
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'clipboard_pull' }));
        showWatchToast('Fetching clip...');
    } else {
        showWatchToast('Offline');
    }
}

function panicStop() {
    vibrate([150, 50, 150]);
    if (confirm('Engage Emergency Panic Stop on PC?')) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'panic_stop' }));
            showWatchToast('🚨 PANIC STOP SENT');
            setCaption('Emergency stop sent');
        }
    }
}

// Attach Touch / Hold listeners to Voice Core
function setupVoiceEventListeners() {
    const voiceBtn = document.getElementById('voice-core-btn');
    if (!voiceBtn) return;

    // Pointer events (handles touch & mouse hold)
    voiceBtn.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        isHolding = true;
        startPushToTalk();
    });

    voiceBtn.addEventListener('pointerup', (e) => {
        e.preventDefault();
        if (isHolding) {
            isHolding = false;
            stopPushToTalk();
        }
    });

    voiceBtn.addEventListener('pointercancel', () => {
        if (isHolding) {
            isHolding = false;
            stopPushToTalk();
        }
    });
}

window.addEventListener('DOMContentLoaded', () => {
    connectWatch();
    setupVoiceEventListeners();
});
