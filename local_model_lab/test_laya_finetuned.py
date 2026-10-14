# -*- coding: utf-8 -*-
"""
Verification Suite for Fine-Tuned Laya System-1 Model
Tests real forward-pass latency, classification, and execution on RTX 4060 Ti.
"""

import sys
import os
import time

sys.path.append(os.path.dirname(__file__))

from laya_real_bridge import get_laya_bridge, evaluate_streaming_transcript

bridge = get_laya_bridge()
print("=" * 75)
print("  FINE-TUNED LAYA SYSTEM-1 MODEL VERIFICATION (RTX 4060 Ti)")
print("=" * 75)
print(f"Bridge Worker Ready: {bridge.is_available()}")

test_cases = [
    ("mute system audio", "media_control", "plain_code"),
    ("turn the volume up", "media_control", "plain_code"),
    ("bring visual studio code to front", "window_manager", "plain_code"),
    ("snap this window to the left", "window_manager", "plain_code"),
    ("shut down my computer in 30 minutes", "smart_shutdown", "plain_code"),
    ("find the best price for RTX 4070 Ti Super", "deal_finder", "plain_code"),
    ("start recording a new macro called fill_form", "rpa_macro", "plain_code"),
    ("describe what is on my screen right now", "screen_vision", "plain_code"),
    ("open paper app and create a new artboard", "paper_design", "plain_code"),
    ("explain how transformer self-attention mechanisms calculate key value queries", "general_agent", "local_llm"),
    ("delete all records from production database", "general_agent", "human_approval"),
]

passed = 0
latencies = []

for text, exp_tool, exp_tier in test_cases:
    t0 = time.perf_counter()
    res = evaluate_streaming_transcript(text, session_id=f"verify_{passed}", fire_threshold=0.70, execute_action=False)
    lat = round((time.perf_counter() - t0) * 1000, 2)
    latencies.append(lat)

    pred_tool = res.get("tool")
    pred_tier = res.get("execution_tier")
    action = res.get("action")
    conf = res.get("confidence", 0.0)

    match = (pred_tool == exp_tool)
    if match:
        passed += 1
    mark = "[PASS]" if match else "[FAIL]"
    print(f"{mark} ({lat}ms, conf: {conf:.2f}) '{text[:42]}...'")
    print(f"       Expected: tool={exp_tool:<15} tier={exp_tier}")
    print(f"       Got:      tool={str(pred_tool):<15} tier={str(pred_tier)} -> action={action}")

print("-" * 75)
print(f"Accuracy: {passed}/{len(test_cases)} ({(passed/len(test_cases))*100:.1f}%)")
print(f"Average Roundtrip Latency: {sum(latencies)/len(latencies):.1f} ms (Target: < 35ms)")
print("=" * 75)
