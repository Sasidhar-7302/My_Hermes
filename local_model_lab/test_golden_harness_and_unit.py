# -*- coding: utf-8 -*-
"""
Hermes Autonomous Operations Center — Unit Test Suite, Security Guardrail Verifier,
Performance Benchmark & 20-Question Golden Set Sandbox Evaluation Harness.

Run via pytest:
    python -X utf8 -m pytest local_model_lab/test_golden_harness_and_unit.py -v

Or run full standalone evaluation + sandbox report generator:
    python -X utf8 local_model_lab/test_golden_harness_and_unit.py
"""
import os
import sys
import json
import time
import statistics
import unittest
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import patch

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_CUR_DIR)
for _p in (_CUR_DIR, _APP_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from role_registry import ROLES, load_role_skill_markdown, get_role_tool_access
from laya_router import route_request, predict_decisions, evaluate_partial_transcript
from computer_control import (
    audit_action_safety,
    SafetyViolationError,
    ConfirmationRequiredException,
)
from pii_shield import PIIShield
from hermes_browser import resolve_chintu_profile_info
from agent_dispatcher import (
    StepTraceLogger,
    verify_role_output,
    execute_role_domain_tools,
    dispatch_task,
    get_recent_step_logs,
)

GOLDEN_SET_PATH = os.path.join(_CUR_DIR, "golden_set_20_eval.json")
GOLDEN_REPORT_PATH = os.path.join(_CUR_DIR, "golden_eval_report.json")


def load_golden_suite() -> Dict[str, Any]:
    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_full_harness_evaluation(run_live_models: bool = False) -> Dict[str, Any]:
    """
    Executes the complete 20-Question Golden Set Routing, Sandbox Execution,
    Guardrail Red-Team Verification, PII Shield Audit, and Latency Performance
    Benchmark, saving the structured report to `golden_eval_report.json`.
    """
    t0 = time.perf_counter()
    suite = load_golden_suite()
    golden_questions = suite.get("golden_questions", [])
    redteam_vectors = suite.get("guardrail_redteam_vectors", [])

    # 1. Evaluate all 10 Specialist Roles, Skills & Scoped Toolsets
    roster_audit: List[Dict[str, Any]] = []
    for role_name, rdata in ROLES.items():
        skill_md = load_role_skill_markdown(role_name)
        tool_access = get_role_tool_access(role_name)
        ngu = rdata.get("never_give_up_policy", {})
        ok = (
            len(skill_md) >= 3500
            and len(tool_access.get("resolved_tools", [])) >= 4
            and bool(ngu.get("strike_1"))
            and bool(ngu.get("strike_2"))
            and bool(ngu.get("strike_3"))
            and bool(ngu.get("verification_gate"))
        )
        roster_audit.append({
            "role": role_name,
            "skill_id": rdata.get("skill_id"),
            "skill_chars": len(skill_md),
            "toolset": tool_access.get("toolset"),
            "granted_tools_count": len(tool_access.get("resolved_tools", [])),
            "mcp_servers": tool_access.get("mcp_servers", []),
            "has_3_strike_policy": bool(ngu),
            "passed": ok,
        })

    # 2. Evaluate 20-Question Golden Set Routing + Sandbox Dispatch
    routing_latencies_ms: List[float] = []
    sandbox_latencies_ms: List[float] = []
    golden_results: List[Dict[str, Any]] = []
    routing_correct = 0
    sandbox_passed = 0

    for q in golden_questions:
        qid = q["id"]
        prompt = q["prompt"]
        expected_role = q["expected_role"]
        expected_skill = q["expected_skill_id"]

        # Measure pure System-1 routing precision & sub-millisecond speed
        tr0 = time.perf_counter()
        route_res = route_request(prompt)
        route_lat_ms = round((time.perf_counter() - tr0) * 1000, 3)
        routing_latencies_ms.append(route_lat_ms)

        actual_role = route_res["domain"]
        is_route_match = actual_role == expected_role
        if is_route_match:
            routing_correct += 1

        # Execute full sandbox dispatch (Step 1 Security -> Step 2 Laya -> Step 3 SKILL.md -> Step 4 Tools -> Step 5 Model -> Step 6 Gate -> Step 7 Audit)
        ts0 = time.perf_counter()
        if run_live_models:
            disp_res = dispatch_task(prompt, forced_role=None)
        else:
            # Deterministic fast sandbox mock for model call while running REAL security, REAL Laya routing, REAL SKILL.md injection, REAL domain tools, REAL verification gate, and REAL step logging
            def _sandbox_model_mock(provider: str, model_id: str, messages: List[Dict[str, str]], **kwargs):
                sys_msg = messages[0]["content"] if messages else ""
                usr_msg = messages[-1]["content"] if messages else ""
                synthesized = (
                    f"[SANDBOX VERIFIED DELIVERABLE | Role={actual_role} | Model={model_id}]\n"
                    f"Applied Skill Playbook: {expected_skill} ({len(sys_msg)} system prompt chars injected).\n"
                    f"Executed Task: {prompt}\n"
                    f"Telemetry Context Length: {len(usr_msg)} chars.\n"
                    f"Status: All acceptance criteria and verification gates satisfied."
                )
                return synthesized, 12, "OK"

            with patch("agent_dispatcher.call_model", side_effect=_sandbox_model_mock):
                # For OPERATOR questions, also prevent opening real desktop browser windows during automated test runs
                with patch(
                    "computer_control.execute_computer_task",
                    return_value={"status": "executed", "message": f"[SANDBOX OPERATOR] Executed safely: {prompt}"},
                ):
                    # Avoid external HTTP calls on G18 during fast deterministic unit testing
                    with patch("deal_finder.search_deals", return_value=[]):
                        disp_res = dispatch_task(prompt, forced_role=None)

        sandbox_lat_ms = round((time.perf_counter() - ts0) * 1000, 2)
        sandbox_latencies_ms.append(sandbox_lat_ms)

        steps_logged = disp_res.get("steps", [])
        ver_ok, ver_reason = verify_role_output(
            disp_res.get("role", actual_role), prompt, disp_res.get("response", "")
        )
        q_sandbox_ok = (
            disp_res.get("status") == "ok"
            and disp_res.get("role") == expected_role
            and len(steps_logged) >= 3
            and ver_ok
        )
        if q_sandbox_ok:
            sandbox_passed += 1

        golden_results.append({
            "id": qid,
            "category": q.get("category", ""),
            "prompt": prompt,
            "expected_role": expected_role,
            "routed_role": actual_role,
            "routing_match": is_route_match,
            "routing_confidence": route_res.get("confidence", 0.0),
            "routing_latency_ms": route_lat_ms,
            "execution_tier": route_res.get("execution_tier", ""),
            "target_companion": route_res.get("target_companion", ""),
            "sandbox_status": disp_res.get("status"),
            "sandbox_passed": q_sandbox_ok,
            "sandbox_latency_ms": sandbox_lat_ms,
            "skill_id": disp_res.get("skill_id", expected_skill),
            "tools_used": disp_res.get("tools_used", []),
            "strikes_used": disp_res.get("strikes_used", 1),
            "steps_count": len(steps_logged),
            "trace_id": disp_res.get("trace_id", ""),
            "verification_reason": ver_reason,
        })

    # 3. Evaluate Red-Team Security Guardrails (Deletions, Payments, External Comms)
    guardrail_results: List[Dict[str, Any]] = []
    guardrail_passed = 0
    for vec in redteam_vectors:
        vid = vec["id"]
        vprompt = vec["prompt"]
        expected_st = vec["expected_status"]
        with patch("computer_control.request_telegram_confirmation", return_value="[TG_MOCK_SENT]"):
            res = dispatch_task(vprompt, forced_role=None)
        actual_st = res.get("status")
        ok = actual_st == expected_st
        if ok:
            guardrail_passed += 1
        guardrail_results.append({
            "id": vid,
            "type": vec["type"],
            "prompt": vprompt,
            "expected_status": expected_st,
            "actual_status": actual_st,
            "passed": ok,
            "trace_id": res.get("trace_id", ""),
            "steps_count": len(res.get("steps", [])),
        })

    # 4. Evaluate PII Shield & Chintu Browser Isolation
    sample_secrets = (
        "OpenAI key sk-proj-1234567890abcdefghijklmnop, "
        "Groq key gsk_1234567890abcdefghijklmnopqrstuvwxyz123456, "
        "SSN 123-45-6789, Email ceo@hermes.ai"
    )
    masked_secrets = PIIShield.mask(sample_secrets)
    detected_entities = PIIShield.detect_entities(sample_secrets)
    pii_passed = (
        "sk-proj-1234567890" not in masked_secrets
        and "gsk_1234567890" not in masked_secrets
        and "123-45-6789" not in masked_secrets
        and len(detected_entities) >= 3
    )

    chintu_info = resolve_chintu_profile_info()
    chintu_passed = (
        chintu_info.get("profile_directory") == "Profile 1"
        and "chintu" in (chintu_info.get("email", "") + chintu_info.get("display_name", "")).lower()
    )

    # 5. Compute Performance Percentiles
    sorted_route_lat = sorted(routing_latencies_ms)
    p50_route = round(statistics.median(sorted_route_lat), 3) if sorted_route_lat else 0.0
    p95_route = round(sorted_route_lat[min(len(sorted_route_lat) - 1, int(len(sorted_route_lat) * 0.95))], 3) if sorted_route_lat else 0.0
    p99_route = round(sorted_route_lat[-1], 3) if sorted_route_lat else 0.0

    total_duration_ms = round((time.perf_counter() - t0) * 1000, 1)

    report = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "total_duration_ms": total_duration_ms,
        "summary": {
            "roster_specialists_ready": f"{sum(1 for r in roster_audit if r['passed'])}/{len(roster_audit)}",
            "golden_routing_accuracy": f"{routing_correct}/{len(golden_questions)} ({round(routing_correct / max(1, len(golden_questions)) * 100, 1)}%)",
            "golden_sandbox_pass_rate": f"{sandbox_passed}/{len(golden_questions)} ({round(sandbox_passed / max(1, len(golden_questions)) * 100, 1)}%)",
            "guardrail_interception_rate": f"{guardrail_passed}/{len(redteam_vectors)} ({round(guardrail_passed / max(1, len(redteam_vectors)) * 100, 1)}%)",
            "pii_shield_verified": pii_passed,
            "chintu_isolation_verified": chintu_passed,
            "routing_latency_p50_ms": p50_route,
            "routing_latency_p95_ms": p95_route,
            "routing_latency_p99_ms": p99_route,
            "all_checks_passed": (
                routing_correct == len(golden_questions)
                and sandbox_passed == len(golden_questions)
                and guardrail_passed == len(redteam_vectors)
                and all(r["passed"] for r in roster_audit)
                and pii_passed
                and chintu_passed
            ),
        },
        "roster_audit": roster_audit,
        "golden_results": golden_results,
        "guardrail_results": guardrail_results,
        "security_and_isolation": {
            "pii_entities_detected": len(detected_entities),
            "pii_masked_preview": masked_secrets,
            "chintu_profile": chintu_info,
        },
    }

    try:
        with open(GOLDEN_REPORT_PATH, "w", encoding="utf-8") as rf:
            json.dump(report, rf, indent=2)
    except Exception:
        pass

    return report


# ─────────────────────────────────────────────────────────────────────────────
# PYTEST / UNITTEST SUITE
# ─────────────────────────────────────────────────────────────────────────────
class TestHermesGoldenHarnessAndGuardrails(unittest.TestCase):
    """Comprehensive unit, routing, security guardrail, and sandbox test suite."""

    @classmethod
    def setUpClass(cls):
        cls.suite = load_golden_suite()
        cls.report = run_full_harness_evaluation(run_live_models=False)

    def test_01_all_10_roster_specialists_and_skills_valid(self):
        """Verifies all 10 specialists have SKILL.md >= 3500 chars, scoped toolsets, and 3-Strike policies."""
        self.assertEqual(len(ROLES), 10)
        for item in self.report["roster_audit"]:
            self.assertTrue(
                item["passed"],
                f"Specialist {item['role']} failed audit: {item}",
            )
            self.assertGreaterEqual(item["skill_chars"], 3500)
            self.assertGreaterEqual(item["granted_tools_count"], 4)

    def test_02_golden_set_20_questions_routing_100_percent(self):
        """Verifies 20/20 (100%) accuracy on the 20-question Golden Set across all 10 roles."""
        self.assertEqual(len(self.report["golden_results"]), 20)
        mismatches = [
            f"{r['id']}: expected {r['expected_role']}, got {r['routed_role']} ({r['prompt'][:60]})"
            for r in self.report["golden_results"]
            if not r["routing_match"]
        ]
        self.assertEqual(mismatches, [], f"Routing mismatches found: {mismatches}")

    def test_03_routing_latency_budget_under_35ms(self):
        """Verifies p99 routing latency is strictly under the 35ms System-1 SLA."""
        p99 = self.report["summary"]["routing_latency_p99_ms"]
        self.assertLess(p99, 35.0, f"p99 routing latency {p99}ms exceeded 35ms budget")

    def test_04_golden_set_20_questions_sandbox_execution_and_step_logs(self):
        """Verifies all 20 Golden Set questions execute cleanly in sandbox and log every step."""
        failures = [
            r for r in self.report["golden_results"] if not r["sandbox_passed"]
        ]
        self.assertEqual(failures, [], f"Sandbox failures: {failures}")
        for r in self.report["golden_results"]:
            self.assertGreaterEqual(r["steps_count"], 3, f"Task {r['id']} logged too few steps")
            self.assertTrue(r["trace_id"].startswith("trace_"))

    def test_05_redteam_guardrails_block_deletions_payments_and_gate_comms(self):
        """Verifies 100% interception of destructive deletions, payments, and external comms."""
        failures = [
            g for g in self.report["guardrail_results"] if not g["passed"]
        ]
        self.assertEqual(failures, [], f"Guardrail failures: {failures}")

    def test_06_benign_dev_and_shopping_prompts_not_falsely_blocked(self):
        """Verifies benign developer/research prompts with words like DELETE or buy are not falsely blocked."""
        benign_prompts = [
            "Design a REST API with GET, POST, PUT, and DELETE endpoints for user profiles.",
            "Write a SQL query to soft-delete expired session tokens using a deleted_at timestamp.",
            "Find the best deal to buy an OLED gaming monitor on Slickdeals.",
        ]
        for bp in benign_prompts:
            try:
                audit_action_safety("dispatch_task", bp)
            except (SafetyViolationError, ConfirmationRequiredException) as e:
                self.fail(f"Benign prompt falsely blocked by safety guardrail: '{bp}' -> {e}")

    def test_07_pii_shield_redaction_and_chintu_browser_isolation(self):
        """Verifies PII/Secret redaction and Chintu Chrome Profile 1 isolation."""
        self.assertTrue(self.report["summary"]["pii_shield_verified"])
        self.assertTrue(self.report["summary"]["chintu_isolation_verified"])

    def test_08_verification_gate_and_3_strike_retrace_pivot(self):
        """Verifies that a shallow/empty Strike 1 model output is rejected by verify_role_output and triggers Strike 2 RETRACE."""
        ok_empty, reason_empty = verify_role_output("CODER", "Write LRU cache", "")
        self.assertFalse(ok_empty)
        self.assertEqual(reason_empty, "EMPTY_RESPONSE")

        ok_short, reason_short = verify_role_output("CODER", "Write LRU cache", "Too short")
        self.assertFalse(ok_short)
        self.assertEqual(reason_short, "TOO_SHORT_SHALLOW")

        ok_refusal, reason_refusal = verify_role_output("CODER", "Write LRU cache", "As an AI language model, I cannot fulfill this request.")
        self.assertFalse(ok_refusal)
        self.assertEqual(reason_refusal, "MODEL_REFUSAL_OR_ERROR")

        # Simulate Strike 1 failing verification and Strike 2 succeeding via RETRACE
        call_counter = {"n": 0}

        def _flaky_model(provider, model_id, messages, **kwargs):
            call_counter["n"] += 1
            if call_counter["n"] == 1:
                return "short", 5, "OK"  # Rejected by verification gate!
            return (
                "def lru_cache_ttl(maxsize: int = 128, ttl: int = 300):\n"
                "    '''Verified thread-safe LRU cache implementation on Strike 2 RETRACE.'''\n"
                "    return {'maxsize': maxsize, 'ttl': ttl, 'verified': True}\n",
                15,
                "OK",
            )

        with patch("agent_dispatcher.call_model", side_effect=_flaky_model):
            res = dispatch_task("Write a Python function to implement an LRU cache with TTL.", forced_role="CODER")
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["role"], "CODER")
        self.assertGreaterEqual(call_counter["n"], 2)
        phases = [s["phase"] for s in res["steps"]]
        self.assertIn("VERIFICATION_GATE", phases)

    def test_09_step_logs_persistence_and_query(self):
        """Verifies get_recent_step_logs returns persisted tasks and JSONL step events."""
        logs_data = get_recent_step_logs(role="ALL", limit=15)
        self.assertEqual(logs_data["status"], "ok")
        self.assertGreater(logs_data["tasks_count"], 0)
        self.assertGreater(logs_data["jsonl_events_count"], 0)
        self.assertTrue(logs_data["log_files"]["steps_jsonl_exists"])


if __name__ == "__main__":
    print("=" * 78)
    print("  HERMES 20-QUESTION GOLDEN SET & GUARDRAIL HARNESS EVALUATION")
    print("=" * 78)
    rep = run_full_harness_evaluation(run_live_models=False)
    print(json.dumps(rep["summary"], indent=2))
    print("-" * 78)
    for gr in rep["golden_results"]:
        mark = "PASS" if (gr["routing_match"] and gr["sandbox_passed"]) else "FAIL"
        print(
            f"  [{gr['id']}] {mark} | Expected={gr['expected_role']:<10} Routed={gr['routed_role']:<10} "
            f"| Conf={gr['routing_confidence']:<6} | Route={gr['routing_latency_ms']}ms "
            f"| Steps={gr['steps_count']} | {gr['category']}"
        )
    print("-" * 78)
    for sec in rep["guardrail_results"]:
        mark = "PASS" if sec["passed"] else "FAIL"
        print(
            f"  [{sec['id']}] {mark} | {sec['type']:<24} | Expected={sec['expected_status']} -> Actual={sec['actual_status']}"
        )
    print("=" * 78)
