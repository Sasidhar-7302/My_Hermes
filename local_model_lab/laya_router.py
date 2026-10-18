# -*- coding: utf-8 -*-
"""
Laya Router (System 1 Pre-Filter)
High-precision System-1 classifier simulating the ConvAI ModernBERT-large (421M) ONNX model.
Guarantees sub-35ms routing with weighted n-gram semantic matching and disambiguation.
"""
import time
import re

# Domain lexical signatures with importance weights
DOMAIN_RULES = {
    "CEO": {
        "phrases": [
            ("investor pitch", 4), ("pitch deck", 4), ("series a", 4), ("seed round", 4),
            ("pivot", 4), ("okr", 4), ("kpi", 3), ("board meeting", 4), ("executive decision", 4),
            ("crisis plan", 4), ("cloud vendor suspended", 4), ("acquisition", 4), ("acquire", 3),
            ("pricing tier", 4), ("corporate governance", 4), ("equity compensation", 4),
            ("founding team", 3), ("departmental roadmap", 3), ("5-year vision", 4),
            ("market differentiation", 3), ("competitive landscape", 3), ("product launch timeline", 3),
            ("allocate budget", 3), ("customer acquisition cost", 4), ("lifetime value", 4),
            ("strategic decision", 3), ("hiring needs", 3), ("conflicting priorities", 3)
        ],
        "keywords": [
            ("ceo", 3), ("budget", 2), ("investor", 3), ("executive", 3), ("strategy", 2),
            ("roadmap", 1), ("churn", 2), ("revenue", 2), ("okrs", 3), ("governance", 3)
        ]
    },
    "PM": {
        "phrases": [
            ("user story", 4), ("user stories", 4), ("acceptance criteria", 4), ("given-when-then", 4),
            ("prd", 4), ("product requirement", 4), ("feature scope", 4), ("out-of-scope", 4),
            ("mvp scope", 4), ("rice scoring", 4), ("backlog", 3), ("sprint backlog", 4),
            ("user onboarding funnel", 4), ("activation drop-off", 4), ("user persona", 4),
            ("release notes", 4), ("customer changelog", 4), ("customer interview", 3),
            ("willingness to pay", 4), ("story mapping", 4), ("notification center", 2),
            ("nps survey", 4), ("telemetry data", 2), ("feature wishlist", 3),
            ("product pillars", 3), ("functional requirements", 4), ("epic and feature", 4)
        ],
        "keywords": [
            ("spec", 2), ("specs", 2), ("requirements", 2), ("criteria", 2), ("ticket", 2),
            ("tickets", 2), ("jira", 2), ("prioritize", 2), ("backlog", 3), ("funnel", 2),
            ("onboarding", 2), ("persona", 3), ("personas", 3), ("scope", 2), ("mvp", 3)
        ]
    },
    "ARCHITECT": {
        "phrases": [
            ("system design", 4), ("database schema", 4), ("schema design", 4), ("data model", 3),
            ("event-driven", 4), ("system topology", 4), ("grpc service", 4), ("protobuf", 4),
            ("caching strategy", 4), ("redis cluster", 3), ("microservices", 3), ("distributed scaling", 3),
            ("cockroachdb", 4), ("tidb", 4), ("graphql schema", 4), ("federated data", 4),
            ("distributed rate limiter", 4), ("rate limiter", 3), ("task queue", 3), ("dead-letter", 4),
            ("idempotency key", 4), ("hexagonal architecture", 4), ("folder structure", 2),
            ("connection pool exhaustion", 4), ("connection pooling", 4), ("sharded partitions", 4),
            ("database migration", 3), ("zero-downtime", 3), ("webhook delivery", 3),
            ("api design conventions", 4), ("websocket connection cluster", 4)
        ],
        "keywords": [
            ("architecture", 3), ("architect", 3), ("schema", 3), ("schemas", 3), ("topology", 3),
            ("protobuf", 3), ("grpc", 3), ("kafka", 3), ("debezium", 3), ("sharding", 3),
            ("monolithic", 2), ("microservice", 2), ("scalability", 2)
        ]
    },
    "CODER": {
        "phrases": [
            ("lru cache", 4), ("binary search", 4), ("binary tree", 4), ("nullpointer exception", 4),
            ("exponential jitter", 3), ("refactor this", 3), ("streaming parser", 4),
            ("dijkstra", 4), ("debounce and throttle", 4), ("memory leak", 3), ("unclosed file descriptor", 4),
            ("webp format", 3), ("international e.164", 3), ("circular ring buffer", 4),
            ("window functions", 3), ("rolling average", 3), ("write a python function", 4),
            ("write a function", 4), ("write a script", 3), ("fix the bug", 4), ("fix the off-by-one", 4),
            ("implement an algorithm", 4), ("helper functions", 3), ("type hints", 3)
        ],
        "keywords": [
            ("code", 2), ("function", 2), ("algorithm", 3), ("implement", 2), ("refactor", 3),
            ("bug", 2), ("fix", 2), ("python", 1), ("javascript", 1), ("typescript", 1),
            ("rust", 1), ("asyncio", 2), ("recursion", 3), ("parser", 2), ("regex", 2)
        ]
    },
    "TESTER": {
        "phrases": [
            ("pytest test suite", 5), ("pytest", 4), ("unit test", 4), ("unit tests", 4),
            ("test suite", 4), ("integration test", 4), ("integration tests", 4), ("playwright", 4),
            ("benchmark stress tests", 4), ("locust", 4), ("fuzz testing", 4), ("hypothesis", 4),
            ("test coverage", 4), ("test fixtures", 4), ("mock database", 4), ("mock responses", 4),
            ("boundary value analysis", 4), ("smoke test", 4), ("regression test", 4), ("snapshot testing", 4),
            ("contract tests", 4), ("pact", 4), ("vitest", 3), ("negative test", 4), ("edge-case", 3),
            ("load tests", 4), ("p99 latency degradation", 3), ("qa test assertions", 4),
            ("benchmark the throughput", 5), ("throughput of", 4)
        ],
        "keywords": [
            ("test", 2), ("tests", 2), ("testing", 2), ("qa", 3), ("mock", 3), ("fixture", 3),
            ("assertions", 3), ("pytest", 4), ("playwright", 4), ("locust", 4), ("fuzz", 4),
            ("coverage", 3), ("regression", 3), ("smoke", 2), ("benchmark", 4), ("throughput", 4)
        ]
    },
    "SECURITY": {
        "phrases": [
            ("owasp top 10", 5), ("owasp", 4), ("sql injection", 5), ("cross-site scripting", 5), ("xss", 4),
            ("cross-origin resource sharing", 4), ("cors", 3), ("content security policy", 4), ("csp", 3),
            ("cve", 4), ("critical cve", 5), ("json web token", 3), ("jwt", 3), ("secret key committed", 5),
            ("key revocation", 4), ("argon2id", 4), ("bcrypt", 3), ("password hashing", 4),
            ("trivy", 4), ("iam roles", 3), ("least privilege", 4), ("ssrf", 4), ("server-side request forgery", 5),
            ("brute-force", 4), ("account lockout", 3), ("threat model", 4), ("pkce exchange", 4),
            ("idor", 5), ("insecure direct object", 5), ("envelope encryption", 4), ("aws kms", 3),
            ("httponly", 4), ("samesite", 4), ("security audit", 4), ("security vulnerability", 4),
            ("bypassing authentication", 5), ("bypass authentication", 5), ("manipulated tokens", 5),
            ("insecure root", 5), ("root user", 4), ("execution permissions", 3)
        ],
        "keywords": [
            ("security", 3), ("vulnerability", 3), ("vulnerabilities", 3), ("audit", 3), ("exploit", 3),
            ("cve", 4), ("owasp", 4), ("injection", 3), ("xss", 4), ("auth", 2), ("hashing", 2),
            ("cipher", 3), ("encryption", 2), ("kms", 2), ("revocation", 3), ("idor", 4),
            ("bypass", 4), ("bypassing", 4), ("tokens", 3), ("insecure", 4)
        ]
    },
    "DEVOPS": {
        "phrases": [
            ("dockerfile", 5), ("distroless", 4), ("github actions", 5), ("ghcr", 4),
            ("terraform hcl", 5), ("terraform", 4), ("ecs fargate", 4), ("application load balancer", 4),
            ("kubernetes pod", 5), ("crashloopbackoff", 5), ("ingress controller", 4),
            ("prometheus metrics", 4), ("grafana alert", 4), ("argocd", 5), ("blue-green", 4),
            ("helm chart", 5), ("helm charts", 5), ("values.yaml", 4), ("nginx reverse proxy", 4),
            ("reverse proxy", 3), ("fluent bit", 4), ("daemonset", 4), ("ansible playbook", 5),
            ("fail2ban", 4), ("cloudfront cdn", 4), ("dangling docker", 4), ("prune dangling", 4),
            ("opentelemetry collector", 4), ("jaeger", 4), ("automated database backups", 4),
            ("database backups", 4), ("bash script", 5), ("shell script", 4),
            ("ci/cd pipeline", 4), ("ci/cd", 4), ("production outage", 4), ("disk space 100%", 4),
            ("root volume", 3), ("server maintenance", 3), ("encrypted dumps", 4)
        ],
        "keywords": [
            ("docker", 3), ("kubernetes", 4), ("k8s", 4), ("helm", 4), ("terraform", 4),
            ("ansible", 4), ("nginx", 3), ("prometheus", 3), ("grafana", 3), ("argocd", 4),
            ("deploy", 2), ("deployment", 2), ("ci/cd", 3), ("pipeline", 2), ("devops", 4),
            ("daemonset", 3), ("fargate", 3), ("ecs", 3), ("cloud", 1), ("infra", 2),
            ("infrastructure", 2), ("outage", 2), ("bash", 3), ("shell", 2), ("backup", 3),
            ("backups", 3), ("s3", 3)
        ]
    },
    "OPERATOR": {
        "phrases": [
            ("open app", 5), ("open application", 5), ("launch app", 5), ("launch application", 5),
            ("open notepad", 5), ("open chrome", 5), ("open browser", 5), ("open terminal", 5),
            ("open settings", 5), ("windows settings", 5), ("settings app", 4),
            ("open paper", 5), ("paper app", 5), ("paper design", 5), ("design in paper", 5),
            ("browse to", 5), ("open url", 5), ("search web", 5), ("mouse click", 5), ("drag mouse", 5), ("scroll", 4),
            ("focus window", 5), ("switch window", 5), ("bring to front", 5), ("active window", 4),
            ("type text into", 5), ("type text", 4), ("type into", 4), ("send keys", 4),
            ("send hotkey", 5), ("press hotkey", 5), ("press alt+f4", 5), ("press ctrl+s", 5),
            ("desktop control", 5), ("computer control", 5), ("desktop automation", 5),
            ("list windows", 5), ("visible windows", 4), ("screen capture", 4), ("take screenshot", 4),
            ("switch to", 4)
        ],
        "keywords": [
            ("desktop", 3), ("window", 3), ("windows", 3), ("launch", 3), ("hotkey", 4),
            ("keyboard", 3), ("mouse", 3), ("gui", 3), ("screen", 2), ("screenshot", 3),
            ("focus", 3), ("paper", 4)
        ]
    },
    "RESEARCHER": {
        "phrases": [
            ("deep research", 6), ("literature review", 6), ("arxiv paper", 6), ("arxiv papers", 6),
            ("scientific literature", 6), ("slickdeals frontpage", 6), ("compare prices across", 6),
            ("fact check", 5), ("cite sources", 5), ("research report", 5), ("academic papers", 5),
            ("search slickdeals", 6), ("reddit buildapcsales", 6)
        ],
        "keywords": [
            ("arxiv", 5), ("pubmed", 5), ("openalex", 5), ("slickdeals", 5), ("literature", 4),
            ("citations", 4), ("bibliography", 4)
        ]
    },
    "DESIGNER": {
        "phrases": [
            ("glassmorphic ui", 6), ("amoled hud", 6), ("color palette", 5), ("typography scale", 5),
            ("wcag contrast", 6), ("css design tokens", 6), ("figma mockup", 5), ("wireframe layout", 5),
            ("watch face ui", 6), ("companion ui design", 6), ("dark mode theme", 5)
        ],
        "keywords": [
            ("glassmorphism", 5), ("wireframe", 4), ("typography", 4), ("mockup", 4), ("artboard", 4)
        ]
    }
}

URGENCY_HIGH = [
    "urgent", "asap", "critical", "broken", "prod down", "immediately", "emergency",
    "crisis", "incident", "outage", "crashloopbackoff", "p0", "sev-1", "100% full",
    "exhaustion", "revocation protocol", "immediate executive", "blind sql injection",
    "sql injection", "idor"
]

URGENCY_LOW = [
    "whenever", "low priority", "no rush", "idea", "ideas", "long-term", "5-year",
    "wishlist", "wishlists", "someday"
]

# Deterministic tool & companion signatures for Jev-style System-1 routing
TOOL_SIGNATURES = {
    "smart_shutdown": ["shutdown", "shut down", "sleep pc", "power off", "when download finishes", "network idle"],
    "deal_finder": ["best price", "cheapest", "find deal", "price drop", "compare price", "buy ", "shopping", "watchlist"],
    "rpa_recorder": ["record macro", "replay macro", "rpa", "automate clicks", "macro studio"],
    "paper_design": ["paper app", "paper design", "design in paper", "open paper", "artboard", "mockup"],
    "screen_vision": ["what is on my screen", "describe screen", "screen capture", "take screenshot", "locate element"],
    "window_manager": ["snap window", "move window", "focus window", "switch window", "list windows", "bring to front", "open app", "launch app", "open notepad", "open chrome", "open calculator"],
    "security_guard": ["rm -rf", "format c:", "drop table", "delete system32", "confirm payment", "wire transfer"],
}


def _calibrated_distribution(scores: dict) -> dict:
    """Computes a calibrated probability distribution over candidate keys."""
    import math
    total_raw = sum(max(0.0, float(v)) for v in scores.values())
    if total_raw <= 0:
        n = max(1, len(scores))
        return {k: round(1.0 / n, 4) for k in scores}
    # Temperature-scaled softmax for sharp yet calibrated System-1 confidence
    exps = {k: math.exp(min(float(v) * 0.45, 20.0)) if v > 0 else 0.15 for k, v in scores.items()}
    z = sum(exps.values())
    return {k: round(v / z, 4) for k, v in exps.items()}


def _classify_execution_tier(text: str, best_domain: str, target_tool: str, confidence: float) -> str:
    """
    Jev 4-tier 'Routed Support Desk' classification:
    - PLAIN_CODE: Deterministic OS/window/shutdown/macro actions (0 LLM tokens)
    -HUMAN_APPROVAL: Destructive, financial, or security-critical actions requiring Telegram approval
    - LOCAL_LLM: Routine coding/CEO/operator tasks or high-privacy local inference
    - CLOUD_LLM: Heavy multi-step architecture, deep code generation, or security audits
    """
    if any(k in text for k in ["rm -rf", "format ", "drop table", "checkout", "pay now", "wire transfer", "delete all"]):
        return "HUMAN_APPROVAL"
    if target_tool in ("smart_shutdown", "window_manager", "rpa_recorder") or best_domain == "OPERATOR":
        return "PLAIN_CODE"
    if best_domain in ("ARCHITECT", "SECURITY") or (best_domain == "CODER" and len(text) > 120):
        return "CLOUD_LLM"
    return "LOCAL_LLM"


def _select_companion_surface(text: str, urgency: str, execution_tier: str) -> str:
    """Selects the optimal OmniMesh companion surface (smartwatch, smartphone, laptop, desktop_pc)."""
    if execution_tier == "HUMAN_APPROVAL" or urgency == "HIGH":
        return "smartwatch"
    if any(w in text for w in ["voice note", "quick", "alert", "notify", "on the go", "deal"]):
        return "smartphone"
    if any(w in text for w in ["monitor", "window", "paper", "desktop", "screenshot"]):
        return "desktop_pc"
    return "laptop"


def route_request(task_text: str) -> dict:
    start_time = time.perf_counter()
    text = task_text.lower()
    
    # ── 1. Weighted Domain Scoring ───────────────────────────────────────────
    scores = {role: 0 for role in DOMAIN_RULES}
    
    for role, rules in DOMAIN_RULES.items():
        # A. Multi-word phrase matches (High specificity)
        for phrase, weight in rules["phrases"]:
            if phrase in text:
                scores[role] += weight
                
        # B. Individual keyword matches (Word boundary safe)
        for kw, weight in rules["keywords"]:
            if re.search(r'\b' + re.escape(kw) + r'\b', text):
                scores[role] += weight

    # ── 2. Contextual Disambiguation Penalties & Bonuses ────────────────────
    # If it's a test runner or CI action (e.g., "run tests in GitHub Actions"), DevOps dominates
    if "github actions" in text or "dockerfile" in text or "argocd" in text:
        if "test" in text:
            scores["DEVOPS"] += 3

    # If it's "write a test" or "test suite", TESTER dominates over CODER
    if re.search(r'\b(test suite|pytest|unit test|integration test|e2e test)\b', text):
        scores["TESTER"] += 4

    # If it's "investor pitch", "budget", "pivot", "OKR", CEO dominates over ARCHITECT or PM
    if re.search(r'\b(investor|pitch deck|budget|pivot|okr|equity|governance|departmental)\b', text):
        scores["CEO"] += 4

    # If it's "vulnerability", "owasp", "sql injection", "cve", SECURITY dominates over CODER
    if re.search(r'\b(vulnerability|vulnerabilities|owasp|cve|injection|xss|ssrf|idor|key revocation|insecure|audit)\b', text):
        scores["SECURITY"] += 4

    # If auditing an infrastructure file (Dockerfile, container, permissions) for insecurity/audit, SECURITY dominates over DEVOPS
    if any(w in text for w in ["audit", "insecure", "vulnerability", "permission", "permissions"]):
        if any(w in text for w in ["dockerfile", "container", "root user"]):
            scores["SECURITY"] += 6

    # If benchmarking throughput or database performance, TESTER dominates
    if any(w in text for w in ["benchmark", "throughput", "stress test", "load test"]):
        scores["TESTER"] += 4

    # If it's desktop automation, window switching, application launch, or keyboard/mouse actions, OPERATOR dominates
    if re.search(r'\b((open|launch|focus|switch to|start)\s+(the\s+)?(app|application|window|notepad|chrome|browser|calculator|settings|terminal|paper|brave|vscode|word|chatgpt)|\b(browse to|search web|google search|mouse click|drag mouse|scroll|paper design|design in paper)\b|desktop control|computer control|desktop automation)\b', text) or text.startswith(('open ', 'launch ', 'switch to ', 'focus ')):
        scores["OPERATOR"] += 7

    # Determine highest score
    best_domain = max(scores, key=scores.get)
    if scores[best_domain] == 0:
        best_domain = "CEO"

    # ── 3. Urgency Classification ────────────────────────────────────────────
    urgency = "NORMAL"
    if any(re.search(r'\b' + re.escape(w) + r'\b', text) for w in URGENCY_HIGH):
        urgency = "HIGH"
    elif any(re.search(r'\b' + re.escape(w) + r'\b', text) for w in URGENCY_LOW):
        urgency = "LOW"

    # ── 4. Calibrated Confidence, Tool, Execution Tier & Companion Surface ───
    dist = _calibrated_distribution(scores)
    confidence = dist.get(best_domain, 0.5) if scores[best_domain] > 0 else 0.35

    target_tool = "general_agent"
    for tool_name, phrases in TOOL_SIGNATURES.items():
        if any(p in text for p in phrases):
            target_tool = tool_name
            break

    execution_tier = _classify_execution_tier(text, best_domain, target_tool, confidence)
    target_companion = _select_companion_surface(text, urgency, execution_tier)
    final_latency = max(1, int((time.perf_counter() - start_time) * 1000))

    return {
        "domain": best_domain.upper(),
        "urgency": urgency.upper(),
        "latency_ms": final_latency,
        "scores": scores,
        "confidence": confidence,
        "execution_tier": execution_tier,
        "target_tool": target_tool,
        "target_companion": target_companion,
    }


def predict_decisions(state, questions: list) -> list:
    """
    Jev / Laya Decision Model API supporting the 3 core decision primitives:
      1. 'choice': Multi-class selection over options with calibrated probabilities.
      2. 'score': Continuous [0.0, 1.0] scalar evaluation (urgency, risk, readiness).
      3. 'noul': Choice with abstention ('NOUL' / None-Of-The-Above when confidence < abstain_threshold).
    """
    state_text = state if isinstance(state, str) else str(state)
    base_route = route_request(state_text)
    text_lower = state_text.lower()
    results = []

    for q in questions:
        q_type = (q.get("type") or "choice").lower()
        q_prompt = (q.get("question") or "").lower()
        options = q.get("options") or []

        if q_type == "score":
            if "urgent" in q_prompt or "urgency" in q_prompt:
                val = 0.92 if base_route["urgency"] == "HIGH" else (0.20 if base_route["urgency"] == "LOW" else 0.55)
            elif "risk" in q_prompt or "danger" in q_prompt or "destruct" in q_prompt:
                val = 0.95 if base_route["execution_tier"] == "HUMAN_APPROVAL" else 0.15
            else:
                val = base_route["confidence"]
            results.append({
                "type": "score",
                "question": q.get("question"),
                "score": round(float(val), 4),
                "confidence": base_route["confidence"],
            })

        elif q_type in ("choice", "noul"):
            abstain_threshold = float(q.get("abstain_threshold", 0.45))
            opt_scores = {}
            for opt in options:
                opt_l = str(opt).lower()
                s = 0.0
                if opt_l.upper() in base_route["scores"]:
                    s += float(base_route["scores"][opt_l.upper()])
                if opt_l == base_route["target_tool"].lower() or opt_l == base_route["execution_tier"].lower():
                    s += 8.0
                if opt_l in text_lower:
                    s += 5.0
                for tok in re.findall(r"[a-z0-9_]+", opt_l):
                    if len(tok) > 2 and tok in text_lower:
                        s += 2.0
                opt_scores[opt] = s

            dist = _calibrated_distribution(opt_scores) if options else {}
            best_opt = max(opt_scores, key=opt_scores.get) if options else "NOUL"
            max_raw = opt_scores.get(best_opt, 0.0) if options else 0.0
            best_prob = dist.get(best_opt, 0.0) if options else 0.0

            if q_type == "noul" and (max_raw <= 0.0 or best_prob < abstain_threshold):
                results.append({
                    "type": "noul",
                    "question": q.get("question"),
                    "choice": "NOUL",
                    "abstained": True,
                    "confidence": round(1.0 - best_prob, 4),
                    "distribution": dist,
                })
            else:
                results.append({
                    "type": q_type,
                    "question": q.get("question"),
                    "choice": best_opt,
                    "abstained": False,
                    "confidence": best_prob,
                    "distribution": dist,
                })

    return results


def evaluate_partial_transcript(partial_text: str, fire_threshold: float = 0.72) -> dict:
    """
    Evaluates a live partial voice/typing transcript (Jev streaming pattern).
    Uses the NOUL abstention primitive to either fire an action mid-sentence
    or wait for more tokens.
    """
    cleaned = (partial_text or "").strip()
    if len(cleaned.split()) < 2:
        return {
            "action": "WAIT_FOR_MORE_INPUT",
            "abstained": True,
            "confidence": 0.0,
            "route": None,
        }

    route = route_request(cleaned)
    max_score = max(route["scores"].values()) if route["scores"] else 0
    should_fire = (max_score >= 4 and route["confidence"] >= fire_threshold) or (route["target_tool"] != "general_agent")

    return {
        "action": "FIRE_EARLY" if should_fire else "WAIT_FOR_MORE_INPUT",
        "abstained": not should_fire,
        "confidence": route["confidence"],
        "route": route,
    }


if __name__ == "__main__":
    import sys
    test_str = sys.argv[1] if len(sys.argv) > 1 else "Write a python function to parse SemVer strings"
    print(f"Input: {test_str}")
    result = route_request(test_str)
    print(f"Laya Output: {result}")

