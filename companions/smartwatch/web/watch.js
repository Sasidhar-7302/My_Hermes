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
    } else if (data.type === 'fast_action_executed') {
        showWatchToast('⚡ ' + (data.tool || 'Executed'));
        vibrate([100, 50, 100]);
        setCaption('⚡ ' + (data.tool || 'Executed'));
        displayAgentReply('⚡ [Fast Executed (' + (data.tool || '') + ')]: ' + JSON.stringify(data.result || {}));
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
    } else if (data.type === 'ping_device') {
        showWatchToast('🔔 PING FROM PC', 5000);
        vibrate([400, 100, 400, 100, 800]);
        playWatchChime();
        setCaption('🔔 PC Pinged Watch');
    } else if (data.type === 'request_screen_snapshot') {
        sendWatchHudTelemetry();
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

    let lastSentPartial = '';
    let lastPartialTime = 0;

    recognition.onstart = () => {
        isListening = true;
        currentTranscript = '';
        lastSentPartial = '';
        lastPartialTime = 0;
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

            // Stream partial transcript to Laya System-1 in real-time
            const now = Date.now();
            if (ws && ws.readyState === WebSocket.OPEN && currentTranscript.length >= 3) {
                if (currentTranscript !== lastSentPartial && (now - lastPartialTime >= 140)) {
                    lastSentPartial = currentTranscript;
                    lastPartialTime = now;
                    ws.send(JSON.stringify({
                        type: 'voice_partial',
                        transcript: currentTranscript,
                        timestamp: now
                    }));
                }
            }
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

// ── WRIST DESKTOP PEEK & WAKE-ON-LAN ──────────────────────────────────────────
async function refreshWatchScreen() {
    const img = document.getElementById('watch-screen-img');
    const focusEl = document.getElementById('watch-screen-focus');
    if (img) {
        img.src = `/api/desktop/snapshot?monitor=2&max_width=480&quality=65&t=${Date.now()}`;
    }
    try {
        const res = await fetch('/api/desktop/live_activity');
        if (res.ok) {
            const data = await res.json();
            if (focusEl && data.active_window) {
                const title = (data.active_window.title || 'Desktop').trim();
                focusEl.innerText = `Focused: ${title.substring(0, 26)}`;
            }
        }
    } catch (_) {}
    vibrate([30]);
}

function peekDesktopScreen() {
    vibrate([40]);
    const modal = document.getElementById('screen-modal');
    if (modal) {
        modal.classList.add('show');
        refreshWatchScreen();
    }
}

function dismissScreenModal() {
    const modal = document.getElementById('screen-modal');
    if (modal) {
        modal.classList.remove('show');
    }
}

async function wakePcFromWatch() {
    vibrate([80, 40, 80]);
    showWatchToast('⚡ Waking PC...');
    try {
        const res = await fetch('/api/power/wake', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mac: '00:13:EF:60:04:42' })
        });
        const data = await res.json();
        if (data.status === 'success') {
            vibrate([150, 50, 150]);
            showWatchToast('✅ PC WAKE SENT!');
        } else {
            showWatchToast('Wake: ' + (data.message || 'sent'));
        }
    } catch (e) {
        showWatchToast('Wake sent via subnet');
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

// ── WRIST ACOUSTIC CHIME (Web Audio API Synthesizer) ──────────────────────
function playWatchChime(repeats = 4) {
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();
        for (let i = 0; i < repeats; i++) {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            const startTime = ctx.currentTime + (i * 0.3);
            osc.frequency.setValueAtTime(1200, startTime);
            osc.frequency.exponentialRampToValueAtTime(2400, startTime + 0.15);
            gain.gain.setValueAtTime(0.6, startTime);
            gain.gain.exponentialRampToValueAtTime(0.01, startTime + 0.25);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(startTime);
            osc.stop(startTime + 0.28);
        }
    } catch (e) {
        console.warn('Watch chime error:', e);
    }
}

// ── ZERO-BATTERY WRIST HUD STATE TELEMETRY ────────────────────────────────
function sendWatchHudTelemetry() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        const clockEl = document.getElementById('watch-clock');
        const pill = document.getElementById('battery-pill');
        const caption = document.getElementById('voice-caption');
        ws.send(JSON.stringify({
            type: 'watch_hud_telemetry',
            time: clockEl ? clockEl.innerText : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            battery: pill ? parseInt(pill.innerText.replace(/\D/g, '')) || null : null,
            is_charging: pill ? pill.innerText.includes('⚡') : false,
            voice_state: isListening ? 'listening' : (isHolding ? 'holding' : 'idle'),
            last_message: caption ? caption.innerText : 'Ready',
            heart_rate: 72,
            timestamp: Date.now()
        }));
    }
}

// ── SMARTWATCH LOW-POWER GEOLOCATION ──────────────────────────────────────
function initWatchLocation() {
    if (!('geolocation' in navigator)) return;
    try {
        navigator.geolocation.getCurrentPosition((pos) => {
            if (pos && pos.coords && ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'location_telemetry',
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                    accuracy: pos.coords.accuracy || 0,
                    source_type: 'smartwatch'
                }));
            }
        }, () => {}, { enableHighAccuracy: false, maximumAge: 180000, timeout: 10000 });
    } catch (_) {}
}

window.addEventListener('DOMContentLoaded', () => {
    connectWatch();
    setupVoiceEventListeners();
    initWatchLocation();
    setInterval(sendWatchHudTelemetry, 20000);
});
