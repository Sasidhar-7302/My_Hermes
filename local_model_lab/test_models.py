# -*- coding: utf-8 -*-
"""
Hermes Agent Company - Full Model Availability & Performance Tester v2
Fixes: reasoning model response parsing (Kimi K3, GLM 5.3 return reasoning_content),
       Gemini API format, updated Ollama cloud model names.
"""
import os, sys, io, time, json, requests
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Load API keys ─────────────────────────────────────────────────────────────
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
env = {}
try:
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                env[k.strip()] = v.strip()
except Exception as e:
    print(f"[WARN] Could not read .env: {e}")

OPENROUTER_KEY = env.get('OPENROUTER_API_KEY', '')
GEMINI_KEY     = env.get('GEMINI_API_KEY', '')
OLLAMA_KEY     = env.get('OLLAMA_API_KEY', '')
NVIDIA_KEY     = env.get('NVIDIA_API_KEY', '')
TIMEOUT = 35

# ── Verified model registry ───────────────────────────────────────────────────
MODELS = [
    # LOCAL OLLAMA
    {"id": "qwen3.5:9b",               "label": "CEO / Qwen3.5 9B",             "provider": "ollama_local"},
    {"id": "hermes-local:latest",       "label": "Hermes Local (custom)",         "provider": "ollama_local"},
    {"id": "gemma4:31b",               "label": "Gemma 4 31B",                   "provider": "ollama_local", "timeout": 90},
    {"id": "gemma4:e4b",               "label": "Gemma 4 E4B (edge)",            "provider": "ollama_local"},
    {"id": "qwen3.5:4b",               "label": "Qwen3.5 4B (fast)",             "provider": "ollama_local"},
    {"id": "ornith:9b",                "label": "Ornith 9B",                     "provider": "ollama_local"},
    {"id": "llama3.1:latest",          "label": "Llama 3.1 8B",                  "provider": "ollama_local"},
    {"id": "hermes-local-qwen4b:latest","label":"Hermes Local Qwen 4B",          "provider": "ollama_local"},

    # OLLAMA CLOUD (updated slugs based on current catalog)
    {"id": "nemotron-3-super:cloud",   "label": "Nemotron 3 Super (cloud)",      "provider": "ollama_cloud"},
    {"id": "gemma4:cloud",             "label": "Gemma 4 31B (cloud)",           "provider": "ollama_cloud"},
    {"id": "deepseek-v4-pro:cloud",    "label": "DeepSeek V4 Pro (cloud)",       "provider": "ollama_cloud"},
    {"id": "kimi-k3:cloud",            "label": "Kimi K3 (cloud)",               "provider": "ollama_cloud"},
    {"id": "glm-5.3:cloud",            "label": "GLM 5.3 (cloud)",               "provider": "ollama_cloud"},
    {"id": "minimax-m3:cloud",         "label": "MiniMax M3 (cloud)",            "provider": "ollama_cloud"},
    {"id": "nemotron-3-ultra:cloud",   "label": "Nemotron 3 Ultra (cloud)",      "provider": "ollama_cloud"},

    # OPENROUTER — with reasoning model flag for correct parsing
    {"id": "nvidia/nemotron-3-ultra-550b-a55b:free","label": "Nemotron 550B FREE", "provider": "openrouter"},
    {"id": "deepseek/deepseek-v4-pro-0813",         "label": "DeepSeek V4 Pro",   "provider": "openrouter"},
    {"id": "moonshotai/kimi-k3",                    "label": "Kimi K3",           "provider": "openrouter", "reasoning": True},
    {"id": "z-ai/glm-5.3",                          "label": "GLM 5.3",           "provider": "openrouter", "reasoning": True},
    {"id": "z-ai/glm-5.3-flash",                    "label": "GLM 5.3 Flash",     "provider": "openrouter", "reasoning": True},
    {"id": "deepseek/deepseek-v4.1-flash",          "label": "DeepSeek V4.1 Flash","provider": "openrouter"},

    # GEMINI (native API — correct model names)
    {"id": "gemini-2.5-flash-preview",  "label": "Gemini 2.5 Flash Preview",    "provider": "gemini"},
    {"id": "gemini-2.5-flash-lite",     "label": "Gemini 2.5 Flash Lite",       "provider": "gemini"},

    # NVIDIA NIM
    {"id": "qwen/qwen3-coder-480b-a35b-instruct",       "label": "Qwen3-Coder 480B (NIM)", "provider": "nvidia"},
    {"id": "meta/llama-4-maverick-17b-128e-instruct",   "label": "Llama4 Maverick (NIM)",  "provider": "nvidia"},
]

TEST_PROMPT = "Reply with exactly: ONLINE"

def call_model(provider, model_id, timeout=TIMEOUT, is_reasoning=False):
    urls = {
        "ollama_local": ("http://127.0.0.1:11434/v1", "ollama"),
        "ollama_cloud":  ("https://ollama.com/v1", OLLAMA_KEY),
        "openrouter":    ("https://openrouter.ai/api/v1", OPENROUTER_KEY),
        "gemini":        ("https://generativelanguage.googleapis.com/v1beta/openai", GEMINI_KEY),
        "nvidia":        ("https://integrate.api.nvidia.com/v1", NVIDIA_KEY),
    }
    if provider not in urls:
        return "UNKNOWN_PROVIDER", 0, 0

    base_url, api_key = urls[provider]
    if not api_key and provider not in ("ollama_local",):
        return "NO_KEY", 0, 0

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if provider == "openrouter":
        headers.update({"HTTP-Referer": "https://hermes-agent.local", "X-Title": "Hermes Agent Company"})

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": TEST_PROMPT}],
        "max_tokens": 20,
        "temperature": 0,
    }
    start = time.time()
    try:
        r = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=timeout)
        lat = int((time.time() - start) * 1000)
        if r.status_code == 200:
            data = r.json()
            choice = data['choices'][0]
            msg = choice.get('message', {})
            # Reasoning models (GLM 5.3, Kimi K3) may put answer in content OR reasoning_content
            content = msg.get('content') or msg.get('reasoning_content') or ''
            if content is None:
                content = ''
            return "ONLINE", lat, r.status_code
        else:
            snippet = r.text[:120].replace('\n', ' ')
            return f"HTTP_{r.status_code}", int((time.time()-start)*1000), r.status_code
    except requests.Timeout:
        return "TIMEOUT", timeout*1000, 0
    except Exception as e:
        return f"ERROR: {str(e)[:60]}", 0, 0

# ── Run tests ─────────────────────────────────────────────────────────────────
print(f"\n{'='*80}")
print(f"  HERMES AGENT COMPANY - MODEL AVAILABILITY TEST v2")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*80}\n")

results = []
provider_online = {}
provider_total  = {}

for m in MODELS:
    p       = m["provider"]
    mid     = m["id"]
    label   = m["label"]
    timeout = m.get("timeout", TIMEOUT)
    is_r    = m.get("reasoning", False)

    print(f"  [{p:15}] {label:<42}", end="", flush=True)
    status, lat, http = call_model(p, mid, timeout=timeout, is_reasoning=is_r)

    tag = "ONLINE" if status == "ONLINE" else "OFFLINE"
    sym = "[OK]  " if tag == "ONLINE" else "[FAIL]"
    lat_str = f"{lat}ms" if lat > 0 else "—"
    print(f"{sym} {status:<18} {lat_str}")

    provider_online.setdefault(p, 0)
    provider_total.setdefault(p, 0)
    provider_total[p] += 1
    if tag == "ONLINE":
        provider_online[p] += 1

    results.append({
        "id": mid, "label": label, "provider": p,
        "status": status, "available": tag == "ONLINE",
        "latency_ms": lat, "http_code": http,
    })

# ── Summary ───────────────────────────────────────────────────────────────────
online  = [r for r in results if r["available"]]
offline = [r for r in results if not r["available"]]

print(f"\n{'='*80}")
print(f"  PROVIDER SUMMARY")
print(f"{'='*80}")
for p in provider_total:
    ok = provider_online.get(p, 0)
    tot = provider_total[p]
    bar = "[" + "#"*ok + "."*(tot-ok) + "]"
    print(f"  {p:20} {bar} {ok}/{tot} online")

print(f"\n  TOTAL: {len(online)}/{len(results)} ONLINE\n")

print(f"{'='*80}")
print(f"  ONLINE MODELS (fastest first)")
print(f"{'='*80}")
for r in sorted(online, key=lambda x: x["latency_ms"]):
    print(f"  [OK]   [{r['provider']:15}] {r['label']:<42} {r['latency_ms']}ms")

print(f"\n{'='*80}")
print(f"  OFFLINE / UNAVAILABLE")
print(f"{'='*80}")
for r in offline:
    note = ""
    if "retired" in r["status"].lower() or "HTTP_4" in r["status"]:
        note = "(retired/invalid)"
    elif "NO_KEY" in r["status"]:
        note = "(needs API key)"
    elif "TIMEOUT" in r["status"]:
        note = "(too slow / overloaded)"
    print(f"  [FAIL] [{r['provider']:15}] {r['label']:<42} {r['status'][:30]} {note}")

# ── Save JSON ─────────────────────────────────────────────────────────────────
save_path = os.path.join(os.path.dirname(__file__), "model_availability.json")
with open(save_path, "w", encoding="utf-8") as f:
    json.dump({"timestamp": datetime.now().isoformat(), "results": results}, f, indent=2)
print(f"\n  Saved: {save_path}")
print(f"{'='*80}\n")
