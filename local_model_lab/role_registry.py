# -*- coding: utf-8 -*-
"""
Hermes Agent Company - Role Registry (QUOTA AWARE)
Configured to maximize the Free Tiers of Groq, NVIDIA NIM, Gemini, and OpenRouter,
while using Local Ollama as the ultimate unlimited fallback.
"""

PROVIDER_BASE_URLS = {
    "ollama_local":  "http://127.0.0.1:11434/v1",
    "openrouter":    "https://openrouter.ai/api/v1",
    "nvidia":        "https://integrate.api.nvidia.com/v1",
    "groq":          "https://api.groq.com/openai/v1",
    "gemini":        None,
}

PROVIDER_KEY_NAMES = {
    "ollama_local":  None,
    "openrouter":    "OPENROUTER_API_KEY",
    "nvidia":        "NVIDIA_API_KEY",
    "groq":          "GROQ_API_KEY",
    "gemini":        "GEMINI_API_KEY",
}

# ─────────────────────────────────────────────────────────────────────────────
# QUOTA & LIMITS STRATEGY (FREE TIERS)
# ─────────────────────────────────────────────────────────────────────────────
# GROQ:      Insanely fast (<400ms). Strict RPM (Requests Per Minute) limits.
#            Use for: Fast routing, DevOps commands, quick testing.
# NVIDIA:    Credit-based free tier. Huge models (550B, 120B).
#            Use for: Heavy lifting (Architect, Coder, Security).
# GEMINI:    15 RPM / 1M tokens free tier. Huge context window.
#            Use for: PM specs, massive log reading, document parsing.
# LOCAL:     Unlimited. Free. Private. Slow (10s+).
#            Use for: CEO, Fallbacks, sensitive data.

VERIFIED_MODELS = {
    # GROQ (Ultra Fast, RPM limited)
    "groq-gpt120b":  {"id": "openai/gpt-oss-120b", "provider": "groq", "latency_ms": 331, "quota": "Strict RPM"},
    "groq-qwen27b":  {"id": "qwen/qwen3.8-27b",    "provider": "groq", "latency_ms": 307, "quota": "Strict RPM"},
    
    # NVIDIA NIM (Heavy Lifting, Credit limited)
    "nim-550b":      {"id": "nvidia/nemotron-3-ultra-550b-a55b", "provider": "nvidia", "latency_ms": 839, "quota": "Credits"},
    "nim-120b":      {"id": "nvidia/nemotron-3-super-120b-a12b", "provider": "nvidia", "latency_ms": 957, "quota": "Credits"},
    "nim-30b":       {"id": "nvidia/nemotron-3.5-lightning-30b-a3b", "provider": "nvidia", "latency_ms": 1841, "quota": "Credits"},
    
    # GEMINI (Huge Context, 15 RPM)
    "gemini-flash":  {"id": "gemini-3.8-flash",    "provider": "gemini", "latency_ms": 6345, "quota": "15 RPM"},
    "gemini-pro":    {"id": "gemini-3.1-pro-preview","provider":"gemini","latency_ms": 4000, "quota": "15 RPM"},
    
    # OPENROUTER (Free Tier)
    "or-deepseek":   {"id": "deepseek/deepseek-v4.1-flash", "provider": "openrouter", "latency_ms": 582, "quota": "OR Free Tier"},
    "or-glm53":      {"id": "z-ai/glm-5.3",                 "provider": "openrouter", "latency_ms": 707, "quota": "OR Free Tier"},
    
    # LOCAL (Unlimited)
    "local-qwen9b":  {"id": "qwen3.5:9b",          "provider": "ollama_local", "latency_ms": 15402, "quota": "Unlimited"},
    "local-llama":   {"id": "llama3.1:latest",     "provider": "ollama_local", "latency_ms": 10794, "quota": "Unlimited"},
}

def M(key):
    m = dict(VERIFIED_MODELS[key])
    m["name"] = key
    return m

# ─────────────────────────────────────────────────────────────────────────────
# QUOTA-OPTIMIZED ROLES
# ─────────────────────────────────────────────────────────────────────────────
ROLES = {
    "CEO": {
        "soul": "You are the CEO. Delegate tasks, review outputs, and write lessons to memory.",
        "models": [M("local-qwen9b"), M("groq-gpt120b"), M("gemini-flash")],
        "fire_threshold": 0.45,
    },
    "PM": {
        "soul": "You are the PM. Write clear specs, criteria, and priorities. No code.",
        "models": [M("gemini-flash"), M("or-glm53"), M("groq-gpt120b"), M("local-qwen9b")],
        "fire_threshold": 0.70,
    },
    "ARCHITECT": {
        "soul": "You are the Architect. Design folder structures, schemas, APIs, and stack.",
        "models": [M("nim-550b"), M("groq-gpt120b"), M("nim-120b"), M("local-qwen9b")],
        "fire_threshold": 0.72,
    },
    "CODER": {
        "soul": "You are the Coder. Write clean, tested, documented code based on specs.",
        "models": [M("nim-550b"), M("groq-qwen27b"), M("nim-120b"), M("local-qwen9b")],
        "fire_threshold": 0.62,
    },
    "TESTER": {
        "soul": "You are the Tester. Write tests, find bugs, block bad code.",
        "models": [M("groq-qwen27b"), M("or-deepseek"), M("gemini-flash"), M("local-qwen9b")],
        "fire_threshold": 0.68,
    },
    "SECURITY": {
        "soul": "You are the Security Auditor. Find OWASP flaws, hardcoded secrets. Block bad code.",
        "models": [M("nim-550b"), M("groq-gpt120b"), M("local-qwen9b")],
        "fire_threshold": 0.78,
    },
    "DEVOPS": {
        "soul": "You are the DevOps Engineer. Write bash, CI/CD, docker. Fix infrastructure.",
        "models": [M("groq-qwen27b"), M("nim-30b"), M("or-deepseek"), M("local-llama")],
        "fire_threshold": 0.65,
    },
    "OPERATOR": {
        "soul": "You are the Desktop & Computer Operator. Execute safe OS actions, manage applications, control windows, and automate workflows with strict deletion and payment shields.",
        "models": [M("local-qwen9b"), M("groq-qwen27b"), M("nim-120b")],
        "fire_threshold": 0.70,
    },
}
