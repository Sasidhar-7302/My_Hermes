# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(__file__))
from laya_router import route_request

adversarial_tests = [
    ("Can you write an architectural decision record explaining why we chose Kafka over RabbitMQ?", "ARCHITECT"),
    ("Audit this Dockerfile for insecure root user execution permissions", "SECURITY"),
    ("Write unit tests for the billing API endpoint in Go with mocked database calls", "TESTER"),
    ("Deploy our latest Docker release to production Kubernetes cluster", "DEVOPS"),
    ("Can you review our company valuation and suggest how much equity to grant our first 5 engineers?", "CEO"),
    ("Critical emergency: Users are bypassing authentication using manipulated tokens", "SECURITY"),
    ("Write a Bash script to automate Git worktree creation for new tasks", "DEVOPS"),
    ("What are the key customer personas and pain points for our B2B SaaS platform?", "PM"),
    ("Benchmark the throughput of our database queries under 10,000 requests per second", "TESTER"),
    ("Implement an asynchronous priority queue in Python with thread-safe pop operations", "CODER")
]

print("=" * 75)
print("  ADVERSARIAL & EDGE-CASE ROUTING TEST")
print("=" * 75)
correct = 0
for text, expected in adversarial_tests:
    res = route_request(text)
    match = (res["domain"] == expected)
    if match:
        correct += 1
    mark = "[PASS]" if match else "[FAIL]"
    print(f"{mark} Expected: [{expected:<9}] -> Predicted: [{res['domain']:<9}] ({res['latency_ms']}ms, {res['urgency']:<6}) | \"{text[:45]}...\"")

score = (correct / len(adversarial_tests)) * 100
print("-" * 75)
print(f"Adversarial Score: {correct}/{len(adversarial_tests)} ({score:.1f}%)")
print("=" * 75)
