// Hermes Smartphone Client Logic (WebSockets, Camera, Clipboard, Voice, Telemetry)
const WS_PROTOCOL = location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${WS_PROTOCOL}//${location.host}/api/mesh/ws`;

let ws = null;
let deviceId = localStorage.getItem('hermes_phone_id') || ('phone-' + Math.random().toString(36).substring(2, 9));
localStorage.setItem('hermes_phone_id', deviceId);

let isRecording = false;
let recognition = null;

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
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        document.getElementById('connection-orb').style.background = '#10b981';
        showToast('Connected to Hermes Mesh');
        ws.send(JSON.stringify({
            type: 'register',
            device_id: deviceId,
            name: 'Smartphone Companion',
            device_type: 'smartphone',
            user_agent: navigator.userAgent
        }));
    };

    ws.onclose = () => {
        document.getElementById('connection-orb').style.background = '#ef4444';
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
        if (data.pc_clipboard) {
            document.getElementById('clip-text').value = data.pc_clipboard;
        }
    } else if (data.type === 'clipboard_update') {
        document.getElementById('clip-text').value = data.content || '';
        showToast('📋 Clipboard updated from PC');
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(data.content).catch(() => {});
        }
    } else if (data.type === 'notification') {
        showToast(data.title + ': ' + data.body);
        if (navigator.vibrate && data.vibrate) navigator.vibrate(data.vibrate);
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
        recognition.interimResults = false;
        recognition.onstart = () => {
            isRecording = true;
            document.getElementById('mic-btn').style.background = 'rgba(239, 68, 68, 0.2)';
            document.getElementById('mic-btn').style.borderColor = '#ef4444';
            showToast('🎙️ Listening...');
        };
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            document.getElementById('chat-input').value = transcript;
            sendPrompt();
        };
        recognition.onend = () => {
            isRecording = false;
            document.getElementById('mic-btn').style.background = '';
            document.getElementById('mic-btn').style.borderColor = '';
        };
    }

    if (isRecording) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

// Service worker registration
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/companions/smartphone/sw.js').catch(() => {});
}

window.onload = connectPhone;
