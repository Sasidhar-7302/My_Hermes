# -*- coding: utf-8 -*-
"""
Laya Persistent CUDA Inference Worker
Runs in laya_runtime venv. Keeps Laya model warm in VRAM (~650MB) on RTX 4060 Ti.
Communicates via standard JSON-RPC over stdin/stdout for sub-35ms response times.
"""

from __future__ import annotations

import os
import sys
import json
import time

# Ensure UTF-8 I/O on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stdin and hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

os.environ["HF_HUB_CACHE"] = "D:/huggingface_cache"

import torch
import laya

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MODEL_PATH = "D:/laya_checkpoints/hermes_laya_v1"
if not os.path.exists(MODEL_PATH):
    MODEL_PATH = "convaiinnovations/laya"

try:
    # Load warm agent directly onto CUDA with specialized Hermes fine-tuned weights
    agent = laya.load(MODEL_PATH, device=DEVICE)
    # Warmup pass
    agent.predict("warmup state", {
        "tier": {
            "type": "choice",
            "instructions": "tier",
            "criteria": {"a": "a", "b": "b"}
        }
    })
    ready_msg = json.dumps({
        "status": "ready",
        "device": str(agent.device),
        "model": MODEL_PATH,
        "cuda": torch.cuda.is_available()
    })
    sys.stdout.write(ready_msg + "\n")
    sys.stdout.flush()
except Exception as exc:
    err_msg = json.dumps({"status": "error", "message": str(exc)})
    sys.stdout.write(err_msg + "\n")
    sys.stdout.flush()
    sys.exit(1)


def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            state = req.get("state", "")
            questions = req.get("questions", {})

            t0 = time.perf_counter()
            res = agent.predict(state, questions)
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)

            out = {
                "id": req_id,
                "status": "ok",
                "latency_ms": latency_ms,
                "answers": res.get("answers", {}),
                "routing": res.get("routing", {})
            }
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()
        except Exception as e:
            out = {
                "id": req.get("id") if "req" in locals() else None,
                "status": "error",
                "error": str(e)
            }
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
