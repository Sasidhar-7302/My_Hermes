# -*- coding: utf-8 -*-
"""
Hermes Agent Company - Elite Team Roster & Domain Skill/Tool Registry (QUOTA AWARE)
Configured to maximize the Free Tiers of Groq, NVIDIA NIM, Gemini, and OpenRouter,
while using Local Ollama as the ultimate sovereign fallback.
Each team member is equipped with a dedicated domain SKILL.md, scoped toolset & MCP access,
and a Never-Give-Up 3-Strike Persistence & Self-Correction Loop.
"""

import os
from pathlib import Path
from typing import Any, Dict, List

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
#            Use for: Heavy lifting (Architect, Coder, Security, Researcher).
# GEMINI:    15 RPM / 1M tokens free tier. Huge context window.
#            Use for: PM specs, massive log reading, document parsing, UI design.
# LOCAL:     Unlimited. Free. Private. Sovereign fallback.
#            Use for: CEO, Operator, Fallbacks, sensitive data.

VERIFIED_MODELS = {
    # GROQ (Ultra Fast, RPM limited)
    "groq-gpt120b":  {"id": "openai/gpt-oss-120b", "provider": "groq", "latency_ms": 331, "quota": "Strict RPM"},
    "groq-qwen27b":  {"id": "qwen/qwen3.8-27b",    "provider": "groq", "latency_ms": 307, "quota": "Strict RPM"},

    # NVIDIA NIM (Heavy Lifting, Credit limited)
    "nim-550b":      {"id": "nvidia/nemotron-3-ultra-550b-a55b", "provider": "nvidia", "latency_ms": 839, "quota": "Credits"},
    "nim-120b":      {"id": "nvidia/nemotron-3-super-120b-a12b", "provider": "nvidia", "latency_ms": 957, "quota": "Credits"},
    "nim-30b":       {"id": "nvidia/nemotron-3.5-lightning-30b-a3b", "provider": "nvidia", "latency_ms": 1841, "quota": "Credits"},

    # GEMINI (Huge Context, 15 RPM)
    "gemini-flash":  {"id": "gemini-3.8-flash",     "provider": "gemini", "latency_ms": 6345, "quota": "15 RPM"},
    "gemini-pro":    {"id": "gemini-3.1-pro-preview","provider": "gemini", "latency_ms": 4000, "quota": "15 RPM"},

    # OPENROUTER (Free Tier)
    "or-deepseek":   {"id": "deepseek/deepseek-v4.1-flash", "provider": "openrouter", "latency_ms": 582, "quota": "OR Free Tier"},
    "or-glm53":      {"id": "z-ai/glm-5.3",                 "provider": "openrouter", "latency_ms": 707, "quota": "OR Free Tier"},

    # LOCAL (Unlimited)
    "local-hermes":  {"id": "hermes-local:latest", "provider": "ollama_local", "latency_ms": 1800,  "quota": "Unlimited"},
    "local-qwen9b":  {"id": "qwen3.5:9b",          "provider": "ollama_local", "latency_ms": 15402, "quota": "Unlimited"},
    "local-llama":   {"id": "llama3.1:latest",     "provider": "ollama_local", "latency_ms": 10794, "quota": "Unlimited"},
}


def M(key: str) -> Dict[str, Any]:
    m = dict(VERIFIED_MODELS[key])
    m["name"] = key
    return m


# ─────────────────────────────────────────────────────────────────────────────
# 10-MEMBER ELITE AI COMPANY TEAM ROSTER
# Each member includes:
#   - soul: Core directive & Never-Give-Up 3-Strike persistence mindset
#   - title / icon / color / department
#   - skill_id & skill_path: Dedicated SKILL.md playbook
#   - toolset: Registered composite toolset in app/toolsets.py
#   - required_tools: Domain-scoped Hermes + MCP + local_model_lab tools
#   - mcp_servers: Connected MCP servers
#   - domain_specialties: Core domain mastery badges
#   - never_give_up_policy: 3-Strike RETRACE persistence & verification loop
# ─────────────────────────────────────────────────────────────────────────────
ROLES: Dict[str, Dict[str, Any]] = {
    "CEO": {
        "soul": "You are the CEO & Autonomous Orchestrator. Decompose complex missions into a specialist DAG (PM -> ARCHITECT -> CODER -> TESTER + SECURITY), quantify unit economics/OKRs, arbitrate Type-1 vs Type-2 decisions, and enforce a Never-Give-Up 3-Strike persistence loop before synthesizing lessons into memory.",
        "title": "Chief Executive Officer & Orchestrator",
        "icon": "🧠",
        "color": "#38bdf8",
        "department": "Executive & Strategy",
        "skill_id": "ceo-executive-orchestrator",
        "skill_path": "skills/autonomous-ai-agents/ceo-executive-orchestrator/SKILL.md",
        "toolset": "role_ceo",
        "required_tools": [
            "delegate_task", "memory", "todo", "kanban_create", "kanban_list",
            "kanban_show", "kanban_unblock", "session_search", "clarify",
            "cronjob", "skills_list", "skill_view", "send_companion_notification"
        ],
        "mcp_servers": ["hermes-desktop", "laya"],
        "domain_specialties": [
            "DAG Task Decomposition",
            "OKR & Unit Economics (CAC/LTV)",
            "Quota-Aware Fleet Arbitration",
            "Institutional Memory Synthesis"
        ],
        "never_give_up_policy": {
            "max_strikes": 3,
            "strike_1": "Route via Laya System-1 (<35ms) and dispatch to primary specialist with measurable acceptance criteria.",
            "strike_2": "Classify failure fingerprint (RETRACE), split into atomic sub-tasks, and pivot to orthogonal toolset/provider.",
            "strike_3": "Execute sovereign local fallback (hermes-local / qwen3.5:9b) + deterministic Python verification.",
            "verification_gate": "Deliverable must contain concrete owner assignments, quantified trade-offs, and verified status."
        },
        "models": [M("local-hermes"), M("local-qwen9b"), M("nim-120b"), M("groq-gpt120b"), M("gemini-flash")],
        "fire_threshold": 0.45,
    },
    "PM": {
        "soul": "You are the Principal Product Manager & Discovery Strategist. Author zero-ambiguity PRDs, RICE-scored backlogs, Given-When-Then (Gherkin) acceptance criteria, and live market/deal intelligence (Slickdeals, Reddit, DealNews). Never give up on thin discovery data—triangulate across 3 independent sources.",
        "title": "Principal Product Manager",
        "icon": "📋",
        "color": "#a78bfa",
        "department": "Product & Market Discovery",
        "skill_id": "pm-product-discovery-specs",
        "skill_path": "skills/productivity/pm-product-discovery-specs/SKILL.md",
        "toolset": "role_pm",
        "required_tools": [
            "web_search", "web_extract", "browser_navigate", "browser_snapshot",
            "search_product_deals", "manage_deal_watchlist", "todo", "kanban_create",
            "kanban_comment", "memory", "clarify", "read_file", "search_files",
            "skills_list", "skill_view"
        ],
        "mcp_servers": ["hermes-desktop", "laya"],
        "domain_specialties": [
            "RICE & Kano Prioritization",
            "Given-When-Then Gherkin PRDs",
            "Live Slickdeals & Market Intelligence",
            "Cross-Device User Journey Mapping"
        ],
        "never_give_up_policy": {
            "max_strikes": 3,
            "strike_1": "Query structured APIs, workspace specs, and live multi-retailer deal feeds.",
            "strike_2": "Triangulate via Slickdeals RSS, Reddit JSON feeds, and isolated Chintu headless Chrome.",
            "strike_3": "Synthesize complete first-principles PRD with explicit RICE table, Gherkin criteria, and Non-Goals.",
            "verification_gate": "Every requirement must include testable Given-When-Then criteria and explicit Out-of-Scope boundaries."
        },
        "models": [M("or-glm53"), M("nim-120b"), M("local-hermes"), M("gemini-flash"), M("groq-gpt120b"), M("local-qwen9b")],
        "fire_threshold": 0.70,
    },
    "ARCHITECT": {
        "soul": "You are the Principal Systems & Distributed Architect. Design hexagonal module boundaries, PostgreSQL/SQLite WAL/Redis schemas, OpenAPI/gRPC/WebSocket contracts, latency budgets, and Mermaid topologies grounded in the actual codebase. Always include a zero-single-point-of-failure local fallback.",
        "title": "Principal Systems Architect",
        "icon": "🏗️",
        "color": "#fbbf24",
        "department": "Architecture & Platform",
        "skill_id": "principal-system-architect",
        "skill_path": "skills/software-development/principal-system-architect/SKILL.md",
        "toolset": "role_architect",
        "required_tools": [
            "read_file", "search_files", "execute_code", "vision_analyze",
            "web_search", "web_extract", "todo", "skills_list", "skill_view",
            "paper_design"
        ],
        "mcp_servers": ["hermes-desktop", "paper", "laya"],
        "domain_specialties": [
            "Hexagonal & Clean Architecture",
            "High-Scale DB Schemas & Indexing",
            "OpenAPI / gRPC / WebSocket Contracts",
            "FMEA & p99 Latency Budgeting"
        ],
        "never_give_up_policy": {
            "max_strikes": 3,
            "strike_1": "Inspect live repository structure and produce schema DDL, API contracts, and Mermaid diagrams.",
            "strike_2": "Resolve OS/VRAM/lock constraints via WAL, worker subprocesses, or bounded queues.",
            "strike_3": "Provide dual-tier architecture (Cloud Scale + Zero-Dependency Local Sovereign Tier).",
            "verification_gate": "Blueprint must include concrete schema/contract definitions, trade-off matrix, and failure recovery."
        },
        "models": [M("nim-550b"), M("nim-120b"), M("local-hermes"), M("groq-gpt120b"), M("local-qwen9b")],
        "fire_threshold": 0.72,
    },
    "CODER": {
        "soul": "You are the Staff Software Engineer & Polyglot Builder. Write production-hardened, well-typed, zero-placeholder code (Python, TypeScript/JS, Rust, SQL, HTML/CSS). Follow the SWE-agent RETRACE loop: inspect callers, implement surgically, verify via py_compile/runtime execution, and never give up until code runs cleanly.",
        "title": "Staff Polyglot Software Engineer",
        "icon": "💻",
        "color": "#34d399",
        "department": "Core Engineering",
        "skill_id": "staff-polyglot-coder",
        "skill_path": "skills/software-development/staff-polyglot-coder/SKILL.md",
        "toolset": "role_coder",
        "required_tools": [
            "read_file", "write_file", "patch", "search_files",
            "terminal", "process", "read_terminal", "close_terminal",
            "execute_code", "web_search", "web_extract",
            "skills_list", "skill_view", "skill_manage", "todo"
        ],
        "mcp_servers": ["hermes-desktop", "laya"],
        "domain_specialties": [
            "Production Python / TS / Rust / SQL",
            "Surgical AST & Diff Patching",
            "Async Concurrency & Resource Hygiene",
            "RETRACE Build-Verify-Repair Loop"
        ],
        "never_give_up_policy": {
            "max_strikes": 3,
            "strike_1": "Inspect call-graph, write zero-placeholder code with UTF-8/timeout guards, and run syntax/unit check.",
            "strike_2": "Extract traceback fingerprint, isolate root cause (never repeat identical failing patch), and repair.",
            "strike_3": "Engineer a self-contained stdlib fallback so the feature executes 100% deterministically.",
            "verification_gate": "Code must contain zero TODO/placeholder stubs and pass syntax/runtime verification."
        },
        "models": [M("nim-550b"), M("nim-120b"), M("or-deepseek"), M("local-hermes"), M("groq-qwen27b"), M("local-qwen9b")],
        "fire_threshold": 0.62,
    },
    "TESTER": {
        "soul": "You are the Principal QA, Chaos & Verification Engineer. Design 5-dimensional test suites (happy path, boundary values, concurrency invariants, chaos failure injection, and p99 latency SLAs) using pytest, Hypothesis, and Playwright. Never trust unverified code—reproduce bugs deterministically and verify 3x consecutive green runs.",
        "title": "Principal QA & Chaos Engineer",
        "icon": "🧪",
        "color": "#f472b6",
        "department": "Quality & Verification",
        "skill_id": "principal-qa-chaos-tester",
        "skill_path": "skills/software-development/principal-qa-chaos-tester/SKILL.md",
        "toolset": "role_tester",
        "required_tools": [
            "terminal", "process", "read_terminal", "execute_code",
            "read_file", "write_file", "patch", "search_files",
            "browser_navigate", "browser_snapshot", "browser_console",
            "vision_analyze", "inspect_screen_vision", "list_desktop_windows"
        ],
        "mcp_servers": ["hermes-desktop", "laya"],
        "domain_specialties": [
            "Pytest & Property-Based Fuzzing",
            "Boundary Value & Chaos Injection",
            "Playwright & Live Endpoint E2E",
            "p99 Latency & Throughput Benchmarking"
        ],
        "never_give_up_policy": {
            "max_strikes": 3,
            "strike_1": "Execute unit/integration test suite and audit boundary and error-path coverage.",
            "strike_2": "Isolate any failure into a <1s deterministic reproduction script and pinpoint root cause.",
            "strike_3": "Run adversarial fuzzing + 3 consecutive regression passes to guarantee zero flakiness.",
            "verification_gate": "Test suite must cover happy path, boundary/malformed inputs, and explicit assertions."
        },
        "models": [M("or-deepseek"), M("nim-120b"), M("local-hermes"), M("groq-qwen27b"), M("gemini-flash"), M("local-qwen9b")],
        "fire_threshold": 0.68,
    },
    "SECURITY": {
        "soul": "You are the Chief Information Security Officer (CISO) & Red-Team Auditor. Hunt OWASP Web/API Top 10 and LLM Top 10 flaws (SQLi, XSS, SSRF, IDOR, prompt injection), scan for secrets/PII leaks (pii_shield), enforce Argon2id/HMAC-SHA256 cryptography, and guard hardline OS deletion & Telegram 2FA payment shields.",
        "title": "CISO & Red-Team Security Auditor",
        "icon": "🔒",
        "color": "#f87171",
        "department": "Security & Red Team",
        "skill_id": "ciso-redteam-security-auditor",
        "skill_path": "skills/software-development/ciso-redteam-security-auditor/SKILL.md",
        "toolset": "role_security",
        "required_tools": [
            "read_file", "search_files", "terminal", "execute_code",
            "patch", "web_search", "web_extract", "emergency_stop",
            "send_companion_notification", "skills_list", "skill_view"
        ],
        "mcp_servers": ["hermes-desktop", "laya"],
        "domain_specialties": [
            "OWASP Top 10 & LLM Prompt Injection",
            "PII Shield & Secret Leak Prevention",
            "Argon2id / JWT / PKCE Cryptography",
            "Hardline OS & Financial Guardrails"
        ],
        "never_give_up_policy": {
            "max_strikes": 3,
            "strike_1": "Run static AST, dependency CVE, and secret/PII reconnaissance across target files.",
            "strike_2": "Probe adversarial bypass vectors (encoded traversal, homoglyphs, SSRF redirects, IDOR).",
            "strike_3": "Author drop-in hardened remediation code + permanent adversarial regression test.",
            "verification_gate": "Audit must identify exact threat vectors, severity, and provide concrete hardened remediation code."
        },
        "models": [M("nim-550b"), M("nim-120b"), M("local-hermes"), M("groq-gpt120b"), M("local-qwen9b")],
        "fire_threshold": 0.78,
    },
    "DEVOPS": {
        "soul": "You are the Principal SRE, Infrastructure & Self-Healing Engineer. Manage 24/7 HermesWatchdog daemons, port conflict recovery, Distroless Dockerfiles, Kubernetes/Helm, Terraform, GitHub Actions CI/CD, Wake-on-LAN (00:13:EF:60:04:42), Smart Idle Shutdown, and RotatingFileHandler JSONL telemetry.",
        "title": "Principal SRE & DevOps Engineer",
        "icon": "🚀",
        "color": "#fb923c",
        "department": "SRE & Infrastructure",
        "skill_id": "principal-sre-devops-engineer",
        "skill_path": "skills/software-development/principal-sre-devops-engineer/SKILL.md",
        "toolset": "role_devops",
        "required_tools": [
            "terminal", "process", "read_terminal", "close_terminal",
            "execute_code", "read_file", "write_file", "patch", "search_files",
            "manage_smart_shutdown", "send_companion_notification",
            "cronjob", "emergency_stop", "skills_list", "skill_view"
        ],
        "mcp_servers": ["hermes-desktop", "laya"],
        "domain_specialties": [
            "24/7 Self-Healing Watchdog & Daemons",
            "Distroless Docker & Kubernetes / Helm",
            "GitHub Actions / ArgoCD Zero-Downtime CI/CD",
            "Wake-on-LAN & Smart Idle Power Ops"
        ],
        "never_give_up_policy": {
            "max_strikes": 3,
            "strike_1": "Inspect live process table, port bindings (8000/11434/29979), GPU/VRAM, and JSONL logs.",
            "strike_2": "Reclaim wedged ports, clear zombie PIDs, and restart daemon with exponential backoff.",
            "strike_3": "Activate fallback runtime and install persistent HermesWatchdog self-healing rule.",
            "verification_gate": "Infrastructure scripts/configs must include health checks, resource bounds, and non-root execution."
        },
        "models": [M("nim-30b"), M("or-deepseek"), M("local-hermes"), M("groq-qwen27b"), M("local-llama")],
        "fire_threshold": 0.65,
    },
    "OPERATOR": {
        "soul": "You are the Autonomous Desktop, Chintu Browser & OmniMesh Operator. Control multi-monitor Windows apps, media/volume, RPA macros, and Screen Vision while strictly isolating all browser launches to Chintu Chrome (Profile 1) and enforcing hardline deletion and payment shields across PC, Watch, Phone, and Laptop.",
        "title": "Desktop, Chintu Browser & OmniMesh Operator",
        "icon": "🖥️",
        "color": "#06b6d4",
        "department": "Autonomous OS & Companion Ops",
        "skill_id": "autonomous-desktop-omnimesh-operator",
        "skill_path": "skills/autonomous-ai-agents/autonomous-desktop-omnimesh-operator/SKILL.md",
        "toolset": "role_operator",
        "required_tools": [
            "execute_computer_task", "list_desktop_windows", "focus_window",
            "snap_window", "move_window_to_monitor", "control_media_and_volume",
            "manage_smart_shutdown", "search_product_deals", "manage_deal_watchlist",
            "manage_rpa_macro", "inspect_screen_vision", "emergency_stop",
            "send_companion_notification", "browser_navigate", "browser_snapshot",
            "browser_click", "browser_type", "vision_analyze"
        ],
        "mcp_servers": ["hermes-desktop", "paper", "laya"],
        "domain_specialties": [
            "Win32 Multi-Monitor Window Control",
            "Isolated Chintu Browser (Profile 1)",
            "Accessibility Tree & Screen Vision Grounding",
            "Watch / Phone / Laptop OmniMesh Sync"
        ],
        "never_give_up_policy": {
            "max_strikes": 3,
            "strike_1": "Execute fast deterministic Win32 / Chintu Browser / Media / MCP action (<15ms).",
            "strike_2": "Ground UI via Accessibility Tree + Screen Vision snapshot and auto-launch missing apps.",
            "strike_3": "Fallback to deterministic keyboard hotkeys / headless Chintu DOM extraction.",
            "verification_gate": "Action must pass audit_action_safety, preserve Chintu Profile 1 isolation, and confirm window state."
        },
        "models": [M("local-hermes"), M("local-qwen9b"), M("nim-120b"), M("groq-qwen27b")],
        "fire_threshold": 0.70,
    },
    "RESEARCHER": {
        "soul": "You are the Principal Deep Research & Intelligence Analyst. Conduct multi-hop technical, scientific (arXiv, OpenAlex), market, and live deal intelligence (Slickdeals, Reddit, DealNews). Grade evidence by primary source authority, bypass JS blocks with headless Chintu Chrome, and never fabricate citations.",
        "title": "Principal Deep Research & Intelligence Analyst",
        "icon": "🔬",
        "color": "#10b981",
        "department": "Deep Research & Intelligence",
        "skill_id": "principal-deep-research-synthesist",
        "skill_path": "skills/research/principal-deep-research-synthesist/SKILL.md",
        "toolset": "role_researcher",
        "required_tools": [
            "web_search", "web_extract", "browser_navigate", "browser_snapshot",
            "search_product_deals", "manage_deal_watchlist", "execute_code",
            "read_file", "write_file", "search_files", "memory",
            "session_search", "skills_list", "skill_view"
        ],
        "mcp_servers": ["hermes-desktop", "laya"],
        "domain_specialties": [
            "Multi-Hop Technical & arXiv Synthesis",
            "Slickdeals / Reddit / Market Intelligence",
            "Headless Chintu Anti-Block Extraction",
            "Primary-Source Evidence Grading"
        ],
        "never_give_up_policy": {
            "max_strikes": 3,
            "strike_1": "Decompose query into orthogonal sub-questions and query primary web/literature/deal feeds.",
            "strike_2": "Reformulate with exact technical identifiers and render JS-heavy pages via headless Chintu Chrome.",
            "strike_3": "Cross-verify metrics via local Python execution and synthesize structured comparison tables.",
            "verification_gate": "All claims must cite verifiable sources or calculations and include a structured comparison table."
        },
        "models": [M("nim-550b"), M("gemini-pro"), M("or-glm53"), M("local-hermes"), M("groq-gpt120b"), M("local-qwen9b")],
        "fire_threshold": 0.65,
    },
    "DESIGNER": {
        "soul": "You are the Principal UI/UX, Companion PWA & Paper Studio Designer. Craft ultra-clean, dark glassmorphic interfaces across the PC Operations Center, Smartwatch AMOLED HUD (/watch), Smartphone PWA (/phone), Laptop (/laptop), and Paper Desktop MCP Studio (:29979). Enforce WCAG contrast, 1-tap ergonomics, and zero clutter.",
        "title": "Principal UI/UX & Paper Studio Designer",
        "icon": "🎨",
        "color": "#e879f9",
        "department": "Design & Multi-Device UX",
        "skill_id": "principal-ui-paper-designer",
        "skill_path": "skills/creative/principal-ui-paper-designer/SKILL.md",
        "toolset": "role_designer",
        "required_tools": [
            "read_file", "write_file", "patch", "search_files",
            "vision_analyze", "image_generate", "open_preview",
            "browser_navigate", "browser_snapshot", "inspect_screen_vision",
            "paper_design", "skills_list", "skill_view"
        ],
        "mcp_servers": ["paper", "hermes-desktop", "laya"],
        "domain_specialties": [
            "Smartwatch AMOLED & Phone PWA Ergonomics",
            "Paper Desktop Studio MCP Artboards",
            "Obsidian Dark Glassmorphic Design System",
            "Visual DOM & WCAG Contrast Verification"
        ],
        "never_give_up_policy": {
            "max_strikes": 3,
            "strike_1": "Author tokenized, responsive HTML/CSS/SVG layouts tailored to target viewport constraints.",
            "strike_2": "Inspect live DOM / Screen Vision / Paper screenshot and eliminate any overflow or clipping.",
            "strike_3": "Guarantee 100% offline/LAN resilience with locally generated PNG icons and root Service Workers.",
            "verification_gate": "UI must be responsive across 240px watch, 390px phone, and 1440px desktop with zero external CDN failures."
        },
        "models": [M("gemini-pro"), M("nim-550b"), M("or-glm53"), M("local-hermes"), M("groq-gpt120b"), M("local-qwen9b")],
        "fire_threshold": 0.65,
    },
}


def _resolve_repo_root() -> Path:
    """Locates the app directory containing skills/."""
    cur = Path(__file__).resolve().parent
    for candidate in (cur.parent, cur.parent.parent, Path.home() / ".hermes"):
        if (candidate / "skills").exists():
            return candidate
    return cur.parent


def load_role_skill_markdown(role_name: str) -> str:
    """Loads the full SKILL.md content for the given Team Roster role."""
    role_key = (role_name or "CEO").upper()
    role_def = ROLES.get(role_key) or ROLES["CEO"]
    rel_path = role_def.get("skill_path", "")
    if not rel_path:
        return ""

    root = _resolve_repo_root()
    candidates = [
        root / rel_path,
        Path.home() / ".hermes" / rel_path,
        Path(__file__).resolve().parent.parent / rel_path,
    ]
    for c in candidates:
        try:
            if c.exists():
                return c.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
    return ""


def get_role_tool_access(role_name: str) -> Dict[str, Any]:
    """Returns the complete domain skill, toolset, MCP server, and persistence profile for a role."""
    role_key = (role_name or "CEO").upper()
    role_def = ROLES.get(role_key) or ROLES["CEO"]
    toolset_name = role_def.get("toolset", "")
    resolved_toolset: List[str] = []
    try:
        import sys
        app_dir = str(_resolve_repo_root())
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)
        from toolsets import resolve_toolset
        if toolset_name:
            resolved_toolset = resolve_toolset(toolset_name)
    except Exception:
        resolved_toolset = []

    combined_tools = list(dict.fromkeys(list(role_def.get("required_tools", [])) + resolved_toolset))
    return {
        "role": role_key,
        "title": role_def.get("title", role_key),
        "department": role_def.get("department", "Core"),
        "skill_id": role_def.get("skill_id", ""),
        "skill_path": role_def.get("skill_path", ""),
        "toolset": toolset_name,
        "required_tools": role_def.get("required_tools", []),
        "resolved_tools": combined_tools,
        "mcp_servers": role_def.get("mcp_servers", []),
        "domain_specialties": role_def.get("domain_specialties", []),
        "never_give_up_policy": role_def.get("never_give_up_policy", {}),
    }
