"""Deterministic behavioral smoke tests for an Ollama model."""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path


def chat(model: str, prompt: str, timeout: int) -> tuple[str, float]:
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            "keep_alive": "15m",
            "options": {"temperature": 0},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.load(response)
    elapsed = time.perf_counter() - start
    return str(result.get("message", {}).get("content", "")).strip(), elapsed


def evaluate(case: dict, response: str) -> list[str]:
    failures: list[str] = []
    lowered = response.lower()
    if case.get("must_be_question") is True and "?" not in response:
        failures.append("response is not a question")
    if case.get("must_be_question") is False and "?" in response:
        failures.append("response asked an unnecessary question")
    for value in case.get("contains_all", []):
        if value.lower() not in lowered:
            failures.append(f"missing required text: {value}")
    choices = case.get("contains_any", [])
    if choices and not any(value.lower() in lowered for value in choices):
        failures.append(f"missing all alternatives: {choices}")
    for value in case.get("forbidden", []):
        if value.lower() in lowered:
            failures.append(f"contains forbidden text: {value}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="hermes-local:latest")
    parser.add_argument(
        "--cases", type=Path, default=Path(__file__).with_name("eval_cases.jsonl")
    )
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    results = []
    for line in args.cases.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        try:
            response, seconds = chat(args.model, case["prompt"], args.timeout)
            failures = evaluate(case, response)
        except Exception as exc:
            response, seconds, failures = "", 0.0, [str(exc)]
        result = {
            "id": case["id"],
            "passed": not failures,
            "seconds": round(seconds, 2),
            "failures": failures,
            "response": response,
        }
        results.append(result)
        print(json.dumps(result, ensure_ascii=False))

    summary = {
        "model": args.model,
        "passed": sum(item["passed"] for item in results),
        "total": len(results),
        "pass_rate": (
            sum(item["passed"] for item in results) / len(results) if results else 0
        ),
        "results": results,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}))
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

