# -*- coding: utf-8 -*-
"""
Hermes Decision Dataset Synthesizer for Laya RLCD Fine-Tuning
Generates 700+ domain-specific decision examples matching Laya's {state, questions, gold} JSONL schema.
Targets RTX 4060 Ti fine-tuning with strictly proper scoring rules (RLCD).
"""

from __future__ import annotations

import os
import json
import random
from pathlib import Path

random.seed(42)

OUTPUT_DIR = Path("D:/laya_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_FILE = OUTPUT_DIR / "hermes_decisions_train.jsonl"
EVAL_FILE = OUTPUT_DIR / "hermes_decisions_eval.jsonl"

TOOL_QUESTIONS_SCHEMA = {
    "target_tool": {
        "type": "choice",
        "instructions": "Which specific deterministic tool handles this request?",
        "criteria": {
            "media_control": "volume up, volume down, mute, unmute, pause, resume, play music, skip song",
            "window_manager": "focus window, switch to window, snap window, minimize, bring to front, launch app",
            "smart_shutdown": "shut down PC, sleep timer, power off when download finishes, idle shutdown",
            "deal_finder": "search prices, find deals, track product price, check discounts across stores",
            "rpa_macro": "record macro, replay macro, automate repetitive clicks and keystrokes",
            "screen_vision": "describe screen, what is visible on my screen, take screenshot, locate element",
            "paper_design": "open paper, design artboard, create mockup in Paper desktop MCP",
            "general_agent": "complex multi-step reasoning, coding, conversational response, explanation"
        }
    },
    "execution_tier": {
        "type": "choice",
        "instructions": "Determine the optimal execution tier for this request.",
        "criteria": {
            "plain_code": "Instant deterministic OS tool or macro with zero LLM inference",
            "human_approval": "Destructive deletion, financial transaction, or high-risk command requiring approval",
            "local_llm": "Routine local inference, coding, private text processing",
            "cloud_llm": "Massive context, deep architecture, multi-agent delegation"
        }
    },
    "target_companion": {
        "type": "choice",
        "instructions": "Which companion device surface is optimal for this request?",
        "criteria": {
            "smartwatch": "Urgent haptic alert, push-to-talk voice note, health biometric",
            "smartphone": "Mobile notification, phone clipboard, on-the-go quick glance",
            "desktop_pc": "Active monitor, desktop window control, graphic design, screen vision",
            "laptop": "Remote machine synchronization, terminal execution"
        }
    }
}

# Template definitions per tool
TOOL_TEMPLATES = {
    "media_control": [
        "mute the volume", "unmute audio", "mute speakers", "mute my pc",
        "turn the volume up", "increase volume by 10 percent", "make it louder", "volume up please",
        "turn it down", "lower the volume", "make it quieter", "volume down",
        "pause the music", "resume playback", "play spotify", "pause youtube",
        "skip to next track", "next song please", "play previous track", "restart this song",
        "stop playback", "stop the music immediately", "silence all audio",
        "toggle mute", "set volume louder", "decrease audio level"
    ],
    "window_manager": [
        "open notepad", "launch chrome", "bring visual studio code to front", "switch to terminal",
        "focus the brave browser window", "focus google chrome", "open windows calculator",
        "snap this window to the left", "snap current window right", "maximize the active window",
        "snap window to top half", "restore window size", "center window on screen",
        "move this window to monitor 2", "move chrome to the second display", "show all open windows",
        "list visible windows", "switch to telegram", "minimize all windows", "focus slack window",
        "bring spotify to foreground", "snap code editor to left and browser to right"
    ],
    "smart_shutdown": [
        "shut down my computer in 30 minutes", "set a shutdown timer for 1 hour",
        "sleep the pc when network goes idle", "turn off the computer after the download finishes",
        "put pc to sleep in 45 minutes", "cancel the pending shutdown timer",
        "abort shutdown", "hibernate pc after steam finishes downloading",
        "schedule automatic sleep for midnight", "shut down the system immediately",
        "power off computer when bandwidth drops below 50 kbps", "check shutdown timer status",
        "is there an active shutdown monitor running", "cancel sleep timer"
    ],
    "deal_finder": [
        "find the best price for RTX 4070 Ti Super", "search deals on sony wh-1000xm5 headphones",
        "is there a discount on macbook air m3 on best buy or amazon",
        "compare prices for samsung 990 pro 2tb ssd across newegg and amazon",
        "track price drops for lg oled c4 65 inch tv", "add a price watch for rtx 4060 under 280 dollars",
        "check my active deal watchlist", "find cheapest price for nintendo switch oled",
        "are there any sales on logitech mx master 3s mouse", "search amazon and micro center for ryzen 7800x3d deals"
    ],
    "rpa_macro": [
        "start recording a new macro called fill_form", "start macro recording",
        "stop recording the macro", "save the recorded keystrokes as daily_login",
        "replay the macro fill_form", "run macro daily_login at 2x speed",
        "replay the last recorded actions", "list all available rpa macros",
        "automate these repeated clicks using rpa", "execute macro invoice_export"
    ],
    "screen_vision": [
        "describe what is on my screen right now", "what window do i currently have open",
        "take a screenshot and summarize the visible content", "what is shown on monitor 1",
        "locate the submit button on the screen", "where is the search bar in this application",
        "inspect the foreground window layout", "capture screen and tell me if there is an error message",
        "can you see the chart on my display"
    ],
    "paper_design": [
        "open paper app and create a new artboard", "design a modern hero section in paper",
        "create a mobile app mockup on paper canvas", "generate a dashboard card component in paper",
        "build an ecommerce product card layout in paper design studio",
        "connect to paper mcp server on port 29979", "create an artboard 1920 by 1080 called landing page"
    ],
    "general_agent": [
        "explain how transformer self-attention mechanisms calculate key value queries",
        "write a python script to parse yaml configuration files",
        "draft an executive summary for our q3 product roadmap",
        "help me debug this memory allocation exception in rust",
        "what is the difference between cockroachdb and postgresql sharding",
        "write unit tests for this authentication handler using pytest",
        "analyze this git diff and suggest architectural improvements",
        "summarize the latest news on agentic AI frameworks",
        "how do i configure a multi-stage dockerfile for go applications",
        "refactor this function to reduce its cyclomatic complexity"
    ]
}

# Template variations with conversational wrappers to train robustness
WRAPPERS = [
    "{cmd}",
    "can you {cmd}",
    "please {cmd}",
    "hermes {cmd}",
    "hey hermes {cmd}",
    "could you please {cmd}",
    "i want you to {cmd}",
    "quick {cmd}",
    "go ahead and {cmd}",
    "{cmd} right now"
]

def generate_dataset():
    records = []

    for tool, cmds in TOOL_TEMPLATES.items():
        tier = "plain_code"
        companion = "desktop_pc"

        if tool == "general_agent":
            tier = "local_llm"
            companion = "laptop"
        elif tool == "media_control":
            companion = "smartwatch"
        elif tool == "deal_finder":
            companion = "smartphone"

        for base_cmd in cmds:
            for w in WRAPPERS:
                text = w.format(cmd=base_cmd).strip()
                # Vary casing slightly
                if random.random() < 0.2:
                    text = text.lower()
                elif random.random() < 0.2:
                    text = text.capitalize()

                # Build record
                record = {
                    "state": text,
                    "questions": TOOL_QUESTIONS_SCHEMA,
                    "expected": {
                        "target_tool": tool,
                        "execution_tier": tier,
                        "target_companion": companion
                    }
                }
                records.append(record)

    # Add dangerous commands requiring human approval
    dangerous = [
        ("delete all records from production database", "general_agent", "human_approval", "desktop_pc"),
        ("rm -rf / on the remote production server", "general_agent", "human_approval", "laptop"),
        ("format drive c and wipe all partitions", "window_manager", "human_approval", "desktop_pc"),
        ("transfer 5000 dollars via wire transfer", "general_agent", "human_approval", "smartphone"),
        ("execute pay now on the checkout page", "window_manager", "human_approval", "smartphone"),
        ("drop database schema users cascade", "general_agent", "human_approval", "laptop"),
    ]
    for text, t, tier, comp in dangerous:
        for w in ["{cmd}", "please {cmd}", "hermes {cmd}"]:
            records.append({
                "state": w.format(cmd=text),
                "questions": TOOL_QUESTIONS_SCHEMA,
                "expected": {
                    "target_tool": t,
                    "execution_tier": tier,
                    "target_companion": comp
                }
            })

    random.shuffle(records)

    split_idx = int(len(records) * 0.85)
    train_records = records[:split_idx]
    eval_records = records[split_idx:]

    with open(TRAIN_FILE, "w", encoding="utf-8") as f:
        for r in train_records:
            f.write(json.dumps(r) + "\n")

    with open(EVAL_FILE, "w", encoding="utf-8") as f:
        for r in eval_records:
            f.write(json.dumps(r) + "\n")

    print(f"Generated {len(train_records)} training records -> {TRAIN_FILE}")
    print(f"Generated {len(eval_records)} evaluation records -> {EVAL_FILE}")

if __name__ == "__main__":
    generate_dataset()
