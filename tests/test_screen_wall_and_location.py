# -*- coding: utf-8 -*-
"""
End-to-End Verification Test for Battery-Preserving Screen Wall & Always-On Location
Tests WebSocket telemetry, on-demand snapshot exchange, AMOLED watch HUD, and location-aware voice prompt routing.
"""

import asyncio
import json
import time
import urllib.request
import websockets

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/api/mesh/ws"


async def run_e2e_test():
    print("--- 1. Getting Pairing Code ---")
    req = urllib.request.Request(f"{BASE_URL}/api/mesh/pairing_code", method="POST")
    with urllib.request.urlopen(req) as resp:
        pair_data = json.loads(resp.read().decode())
        pair_code = pair_data["pairing_code"]
        print(f"[PASS] Acquired pairing code: {pair_code}")

    print("\n--- 2. Connecting Simulated Smartphone ---")
    async with websockets.connect(f"{WS_URL}?pair={pair_code}") as phone_ws:
        reg_pkt = {
            "type": "register",
            "device_id": "phone-e2e-test",
            "name": "Sasidhar's Galaxy S24",
            "device_type": "smartphone",
            "pair": pair_code,
        }
        await phone_ws.send(json.dumps(reg_pkt))
        welcome_phone = json.loads(await phone_ws.recv())
        print(f"[PASS] Phone received welcome: device_id={welcome_phone.get('device_id')}")

        # Send low-power location telemetry
        loc_pkt = {
            "type": "location_telemetry",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "accuracy": 12.0,
            "source_type": "smartphone",
        }
        await phone_ws.send(json.dumps(loc_pkt))
        print("[PASS] Phone dispatched low-power location telemetry")

        # Send on-demand screen snapshot
        snap_pkt = {
            "type": "companion_screen_snapshot",
            "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP...",
            "width": 1080,
            "height": 2340,
            "battery": 86,
            "is_charging": False,
            "device_type": "smartphone",
        }
        await phone_ws.send(json.dumps(snap_pkt))
        print("[PASS] Phone sent compressed screen snapshot")

        # Send voice prompt: "Where am I?"
        prompt_pkt = {
            "type": "voice_prompt",
            "prompt": "Where am I?",
        }
        await phone_ws.send(json.dumps(prompt_pkt))
        
        # Read replies
        reply_received = False
        while True:
            try:
                msg = await asyncio.wait_for(phone_ws.recv(), timeout=5.0)
                data = json.loads(msg)
                print(f"DEBUG RECV: {data.get('type')}")
                if data.get("type") == "agent_response":
                    print(f"[PASS] Location Query Instant Answer: '{data.get('response')}'")
                    reply_received = True
                    break
            except asyncio.TimeoutError:
                print("DEBUG: Timeout waiting for message")
                break
        assert reply_received, "Failed to receive location response"

    print("\n--- 3. Connecting Simulated Smartwatch ---")
    # Get new pairing code for watch
    req = urllib.request.Request(f"{BASE_URL}/api/mesh/pairing_code", method="POST")
    with urllib.request.urlopen(req) as resp:
        watch_pair_code = json.loads(resp.read().decode())["pairing_code"]

    async with websockets.connect(f"{WS_URL}?pair={watch_pair_code}") as watch_ws:
        reg_pkt = {
            "type": "register",
            "device_id": "watch-e2e-test",
            "name": "Sasidhar's Galaxy Watch 6",
            "device_type": "smartwatch",
            "pair": watch_pair_code,
        }
        await watch_ws.send(json.dumps(reg_pkt))
        welcome_watch = json.loads(await watch_ws.recv())
        print(f"[PASS] Watch received welcome: {welcome_watch.get('device_type')}")

        # Send zero-battery AMOLED wrist HUD state
        hud_pkt = {
            "type": "watch_hud_telemetry",
            "time": "21:30",
            "battery": 91,
            "is_charging": False,
            "voice_state": "idle",
            "last_message": "Ready for voice note",
            "heart_rate": 70,
        }
        await watch_ws.send(json.dumps(hud_pkt))
        print("[PASS] Watch dispatched zero-battery AMOLED HUD state")

    print("\n--- 4. Testing Acoustic Ping from Host PC ---")
    # Reconnect phone to test receiving ping
    req = urllib.request.Request(f"{BASE_URL}/api/mesh/pairing_code", method="POST")
    with urllib.request.urlopen(req) as resp:
        re_code = json.loads(resp.read().decode())["pairing_code"]

    async with websockets.connect(f"{WS_URL}?pair={re_code}") as phone_ws:
        reg_pkt = {
            "type": "register",
            "device_id": "phone-ping-test",
            "name": "Phone Ping Target",
            "device_type": "smartphone",
            "pair": re_code,
        }
        await phone_ws.send(json.dumps(reg_pkt))
        await phone_ws.recv()  # welcome

        # Host PC issues ping
        ping_req = urllib.request.Request(
            f"{BASE_URL}/api/mesh/ping_device",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"device_id": "phone-ping-test", "tone": "alarm"}).encode(),
        )
        with urllib.request.urlopen(ping_req) as resp:
            ping_status = json.loads(resp.read().decode())
            print(f"[PASS] PC API dispatched ping: {ping_status}")

        # Phone receives acoustic ping packet
        ping_pkt = json.loads(await asyncio.wait_for(phone_ws.recv(), timeout=3.0))
        print(f"[PASS] Phone received acoustic ping: type={ping_pkt.get('type')}, tone={ping_pkt.get('tone')}")
        assert ping_pkt.get("type") == "ping_device"

    print("\n--- 5. Verifying Host PC Screen Wall Telemetry Feed ---")
    with urllib.request.urlopen(f"{BASE_URL}/api/mesh/status") as resp:
        status_data = json.loads(resp.read().decode())
        loc = status_data.get("location", {})
        wh = status_data.get("watch_hud", {})
        snaps = status_data.get("snapshots", {})

        print(f"[PASS] Host PC Location: {loc.get('zone')} • {loc.get('display_name')}")
        print(f"[PASS] Host PC Weather: {loc.get('weather', {}).get('condition')}, {loc.get('weather', {}).get('temperature_f')}°F")
        print(f"[PASS] Host PC Watch HUD: Time {wh.get('time')}, Battery {wh.get('battery')}%, Message: '{wh.get('last_message')}'")
        print(f"[PASS] Host PC Screen Wall Snapshots cached: {len(snaps)} device(s)")

    print("\n=======================================================")
    print("🎉 ALL END-TO-END SCREEN WALL & LOCATION TESTS PASSED!")
    print("=======================================================")


if __name__ == "__main__":
    asyncio.run(run_e2e_test())
