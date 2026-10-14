# -*- coding: utf-8 -*-
"""
End-to-End Live Voice & Laya System-1 WebSocket Streaming Test
Simulates real-time push-to-talk voice streaming from Smartwatch and Phone companions over WebSocket.
Verifies mid-sentence action execution, utterance debouncing, and emergency stop.
"""

import os
import sys
import json
import time
import asyncio
import websockets

_app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WS_URL = "ws://127.0.0.1:8000/api/mesh/ws"

async def run_voice_streaming_test():
    print("=" * 75)
    print("  OMNIMESH LIVE VOICE STREAMING & LAYA SYSTEM-1 E2E VERIFICATION")
    print("=" * 75)

    import urllib.request
    pair_req = urllib.request.Request("http://127.0.0.1:8000/api/mesh/pairing_code", data=b"{}", headers={"Content-Type": "application/json"})
    pair_data = json.loads(urllib.request.urlopen(pair_req).read().decode())
    pairing_code = pair_data.get("pairing_code")

    device_id = f"watch-test-{int(time.time())}"

    async with websockets.connect(WS_URL) as ws:
        # 1. Register companion device
        reg_pkt = {
            "type": "register",
            "device_id": device_id,
            "name": "Smartwatch Test Rig",
            "device_type": "smartwatch",
            "pair": pairing_code,
            "user_agent": "Python-Voice-Test/1.0",
            "battery": 88,
            "is_charging": False
        }
        await ws.send(json.dumps(reg_pkt))
        welcome_raw = await ws.recv()
        welcome = json.loads(welcome_raw)
        print(f"✓ Companion connected and registered: {welcome.get('type')}")
        assert welcome.get("type") == "welcome", f"Unexpected welcome: {welcome}"

        # 2. Simulate streaming speech: "turn the volume up"
        speech_chunks = [
            "turn",
            "turn the",
            "turn the volume",
            "turn the volume up",
            "turn the volume up please"
        ]

        fired_packet = None
        start_t = time.time()

        for chunk in speech_chunks:
            print(f"--> Speaking: '{chunk}'")
            pkt = {
                "type": "voice_partial",
                "transcript": chunk,
                "timestamp": time.time()
            }
            await ws.send(json.dumps(pkt))

            # Check if an immediate execution packet comes back
            try:
                resp_raw = await asyncio.wait_for(ws.recv(), timeout=0.25)
                resp = json.loads(resp_raw)
                if resp.get("type") == "fast_action_executed":
                    latency = round((time.time() - start_t) * 1000, 2)
                    fired_packet = resp
                    print(f"⚡ [MID-SENTENCE FIRE]: Tool '{resp.get('tool')}' executed while speaking '{chunk}' in {latency}ms!")
                    break
            except asyncio.TimeoutError:
                pass

        assert fired_packet is not None, "Expected fast_action_executed to trigger mid-sentence!"
        assert fired_packet.get("tool") == "media_control", f"Unexpected tool: {fired_packet.get('tool')}"

        # 3. Verify debouncing on subsequent words of the same utterance
        print("--> Speaking tail of sentence: 'turn the volume up please'")
        await ws.send(json.dumps({
            "type": "voice_partial",
            "transcript": "turn the volume up please",
            "timestamp": time.time()
        }))

        # No duplicate execution should occur
        duplicate_fired = False
        try:
            resp_raw = await asyncio.wait_for(ws.recv(), timeout=0.3)
            resp = json.loads(resp_raw)
            if resp.get("type") == "fast_action_executed":
                duplicate_fired = True
        except asyncio.TimeoutError:
            pass

        assert not duplicate_fired, "Debouncing failed: duplicate fast action fired on sentence continuation!"
        print("✓ Utterance debouncing verified: duplicate firing prevented.")

        # 4. Test Panic Stop streaming
        print("--> Speaking emergency stop: 'emergency stop now'")
        await ws.send(json.dumps({
            "type": "panic_stop",
            "timestamp": time.time()
        }))

        panic_raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
        panic_pkt = json.loads(panic_raw)
        print(f"🚨 Panic response received: {panic_pkt.get('type')} - status={panic_pkt.get('status')}")
        assert panic_pkt.get("type") == "panic_alert", f"Expected panic_alert, got: {panic_pkt}"

        # Clean up emergency stop state
        from local_model_lab.shell_daemon import clear_emergency_stop
        clear_emergency_stop()
        print("✓ Emergency stop cleared cleanly.")

    print("=" * 75)
    print("  ALL VOICE STREAMING & LAYA E2E TESTS PASSED (100%)")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(run_voice_streaming_test())
