# -*- coding: utf-8 -*-
"""
Benchmark Test Suite for Laya System-1 Router
Tests classification accuracy, confusion matrix, and latency across 7 roles.
"""
import time
import json
from laya_router import route_request

# Comprehensive 105-task benchmark across 7 roles (15 tasks per role)
BENCHMARK_DATASET = [
    # ── CEO (Strategy, Orchestration, Budgeting, High-Level Decisions) ───────
    {"role": "CEO", "urgency": "NORMAL", "text": "We need to plan our product launch timeline and allocate the $50k budget across marketing and engineering."},
    {"role": "CEO", "urgency": "NORMAL", "text": "Evaluate our quarterly OKRs and decide whether we should pivot the company focus towards enterprise B2B."},
    {"role": "CEO", "urgency": "NORMAL", "text": "Coordinate the entire engineering and design team to prepare our investor pitch deck for Series A."},
    {"role": "CEO", "urgency": "HIGH", "text": "Urgent crisis: Our primary cloud vendor suspended our account. Formulate an executive response and crisis plan."},
    {"role": "CEO", "urgency": "NORMAL", "text": "Review our team's past month performance and determine hiring needs for the next quarter."},
    {"role": "CEO", "urgency": "NORMAL", "text": "Synthesize the learnings and customer feedback from our beta launch into executive strategic decisions."},
    {"role": "CEO", "urgency": "NORMAL", "text": "Assess the competitive landscape against our top rival and define our market differentiation strategy."},
    {"role": "CEO", "urgency": "NORMAL", "text": "Analyze whether we should acquire this small open-source startup or build the tooling in-house."},
    {"role": "CEO", "urgency": "NORMAL", "text": "Determine our pricing tier structure: free tier vs pro vs enterprise custom pricing."},
    {"role": "CEO", "urgency": "NORMAL", "text": "Set up our corporate governance and equity compensation guidelines for founding team members."},
    {"role": "CEO", "urgency": "HIGH", "text": "Immediate executive decision needed: A major partner wants an exclusive licensing contract by tomorrow."},
    {"role": "CEO", "urgency": "NORMAL", "text": "How should we organize our company departmental roadmaps for the upcoming fiscal year?"},
    {"role": "CEO", "urgency": "LOW", "text": "Brainstorm long-term 5-year visions for expanding into autonomous AI enterprise agents."},
    {"role": "CEO", "urgency": "NORMAL", "text": "Review the weekly KPI dashboard across revenue, churn, customer acquisition cost, and lifetime value."},
    {"role": "CEO", "urgency": "NORMAL", "text": "Mediate conflicting priorities between the product roadmap and technical debt cleanup."},

    # ── PM (Requirements, User Stories, PRDs, Scope, Roadmaps) ──────────────
    {"role": "PM", "urgency": "NORMAL", "text": "Draft a comprehensive PRD for our new real-time collaboration canvas feature."},
    {"role": "PM", "urgency": "NORMAL", "text": "Break down the checkout workflow into user stories with clear Given-When-Then acceptance criteria."},
    {"role": "PM", "urgency": "NORMAL", "text": "Prioritize our backlog items for sprint 14 using the RICE scoring methodology."},
    {"role": "PM", "urgency": "NORMAL", "text": "Define the user onboarding funnel steps and determine the key activation drop-off metrics."},
    {"role": "PM", "urgency": "NORMAL", "text": "Write functional requirements for social login integration including Google, Apple, and GitHub."},
    {"role": "PM", "urgency": "NORMAL", "text": "Create an epic and feature tickets for team role-based access management in Jira."},
    {"role": "PM", "urgency": "NORMAL", "text": "Conduct user persona analysis for software engineering leads adopting our developer platform."},
    {"role": "PM", "urgency": "NORMAL", "text": "Draft the release notes and customer-facing change log for our v2.0 product rollout."},
    {"role": "PM", "urgency": "NORMAL", "text": "Define the MVP feature scope for our mobile companion app and document what is out-of-scope."},
    {"role": "PM", "urgency": "NORMAL", "text": "Structure customer interview questions to validate willingness to pay for premium analytics."},
    {"role": "PM", "urgency": "NORMAL", "text": "Write the user story mapping for the notification center across email, push, and in-app alerts."},
    {"role": "PM", "urgency": "HIGH", "text": "Critical requirement update needed immediately: Billing partner API changed requirements for PSD2 compliance."},
    {"role": "PM", "urgency": "NORMAL", "text": "Define the feedback collection mechanism and NPS survey trigger points in the user journey."},
    {"role": "PM", "urgency": "NORMAL", "text": "Review user telemetry data to identify underutilized product features and recommend roadmap adjustments."},
    {"role": "PM", "urgency": "LOW", "text": "Collect feature wishlists from Discord community and group them into thematic product pillars."},

    # ── ARCHITECT (System Design, DB Schemas, API Contracts, Scalability) ───
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Design a high-scale database schema in PostgreSQL for a multi-tenant SaaS application."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Architect an event-driven system topology using Apache Kafka and Debezium for change data capture."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Define the gRPC service contracts and Protobuf definitions for our microservices communication layer."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Design a hybrid caching strategy using Redis Cluster and in-memory L1 cache with cache-invalidation rules."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Evaluate whether we should migrate from monolithic PostgreSQL to CockroachDB or TiDB for geo-distributed scaling."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Design the GraphQL schema and resolver architecture for our federated data graph."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Architect a distributed rate limiter that handles 50,000 req/sec across multiple geographic regions."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Define the system design for an asynchronous task queue with dead-letter exchanges and idempotency keys."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Propose the folder structure, domain boundaries, and hexagonal architecture patterns for our new Go backend."},
    {"role": "ARCHITECT", "urgency": "HIGH", "text": "Urgent architecture failure: Database connection pool exhaustion under peak load; redesign connection pooling topology."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Design the data model and indexing strategy in MongoDB for flexible polymorphic profile metadata."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Design a zero-downtime database migration strategy for splitting a 500GB table into sharded partitions."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Architect a resilient webhook delivery system with exponential backoff and message replay capabilities."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Define the API design conventions (RESTful endpoints, error envelopes, pagination, versioning) for our v3 API."},
    {"role": "ARCHITECT", "urgency": "NORMAL", "text": "Design the WebSocket connection cluster architecture for handling 100,000 concurrent active connections."},

    # ── CODER (Implementation, Bug Fixes, Functions, Algorithms) ───────────
    {"role": "CODER", "urgency": "NORMAL", "text": "Implement an asynchronous LRU cache with TTL expiration in Python using asyncio and double-linked lists."},
    {"role": "CODER", "urgency": "NORMAL", "text": "Write a Python function to parse and validate semantic version strings according to SemVer 2.0."},
    {"role": "CODER", "urgency": "NORMAL", "text": "Fix the off-by-one index error in the binary search implementation in utils.py."},
    {"role": "CODER", "urgency": "HIGH", "text": "Urgent bug fix: Production NullPointer exception in the payment processing callback handler."},
    {"role": "CODER", "urgency": "NORMAL", "text": "Write a recursive algorithm to invert a binary tree and return its serialized representation."},
    {"role": "CODER", "urgency": "NORMAL", "text": "Implement a retry decorator with exponential jitter in TypeScript for failing network calls."},
    {"role": "CODER", "urgency": "NORMAL", "text": "Refactor this 300-line monolithic function into modular helper functions with strict type hints."},
    {"role": "CODER", "urgency": "NORMAL", "text": "Write a fast CSV streaming parser that processes 1GB files chunk-by-chunk without loading all into RAM."},
    {"role": "CODER", "urgency": "NORMAL", "text": "Implement a Dijkstra shortest path algorithm in Python for weighted directed graphs."},
    {"role": "CODER", "urgency": "NORMAL", "text": "Write a debounce and throttle utility function in JavaScript for frontend input handlers."},
    {"role": "CODER", "urgency": "NORMAL", "text": "Fix the memory leak caused by unclosed file descriptors in the log parser worker loop."},
    {"role": "CODER", "urgency": "NORMAL", "text": "Write a Python script to compress image assets to WebP format using Pillow with multithreading."},
    {"role": "CODER", "urgency": "HIGH", "text": "Fix broken regex in production: phone number parser is failing on international E.164 formats."},
    {"role": "CODER", "urgency": "NORMAL", "text": "Implement a thread-safe circular ring buffer in Rust for audio stream processing."},
    {"role": "CODER", "urgency": "NORMAL", "text": "Write an SQL query with window functions to calculate 7-day rolling average user retention."},

    # ── TESTER (QA, Pytest, Mocking, Edge Cases, Test Coverage) ─────────────
    {"role": "TESTER", "urgency": "NORMAL", "text": "Write a comprehensive pytest test suite for the user authentication service with mock database sessions."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Generate negative and edge-case unit test inputs for our credit card Luhn algorithm validator."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Create end-to-end integration tests using Playwright for the checkout and payment flow."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Write benchmark stress tests with Locust to evaluate throughput under 5,000 simulated concurrent users."},
    {"role": "TESTER", "urgency": "HIGH", "text": "Urgent test failure: CI pipeline test suite broke on main branch after latest PR merge."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Increase test coverage for the billing module from 65% to 90% by writing missing test fixtures."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Write fuzz testing scenarios for the JSON parser using Hypothesis to catch unhandled exceptions."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Create mock responses and unit tests for external Stripe and PayPal third-party APIs."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Perform boundary value analysis and write automated QA test assertions for date interval calculations."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Write integration tests verifying that database transactions rollback cleanly upon unexpected server crashes."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Set up snapshot testing for our React design system component library in Vitest."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Write load tests to measure P99 latency degradation under heavy read-write database operations."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Create smoke test scripts to verify health endpoints across all microservices post-deployment."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Verify backward compatibility by writing regression test suites for legacy v1 API endpoints."},
    {"role": "TESTER", "urgency": "NORMAL", "text": "Write contract tests using Pact to verify consumer-provider expectations between frontend and backend."},

    # ── SECURITY (OWASP, Vulnerability Audits, Auth, Exploit Checks) ────────
    {"role": "SECURITY", "urgency": "HIGH", "text": "Audit our backend authentication endpoints for OWASP Top 10 vulnerabilities like broken object level auth."},
    {"role": "SECURITY", "urgency": "HIGH", "text": "Urgent: A critical CVE was reported in our third-party JSON Web Token library. Check our exposure."},
    {"role": "SECURITY", "urgency": "HIGH", "text": "Inspect our query construction in the search endpoint to ensure zero vulnerability to blind SQL injection."},
    {"role": "SECURITY", "urgency": "NORMAL", "text": "Conduct a security audit of our AWS IAM roles and policies to enforce the principle of least privilege."},
    {"role": "SECURITY", "urgency": "NORMAL", "text": "Implement Content Security Policy (CSP) headers and audit frontend templates against Cross-Site Scripting (XSS)."},
    {"role": "SECURITY", "urgency": "HIGH", "text": "Emergency: Accidental API secret key committed to a public Git repository. Execute key revocation protocol."},
    {"role": "SECURITY", "urgency": "NORMAL", "text": "Review our password hashing implementation to ensure migration from bcrypt to Argon2id with proper salt."},
    {"role": "SECURITY", "urgency": "NORMAL", "text": "Scan our Docker container images and npm dependencies for known high-severity vulnerabilities with Trivy."},
    {"role": "SECURITY", "urgency": "NORMAL", "text": "Audit our Cross-Origin Resource Sharing (CORS) configuration to prevent unauthorized origin reflections."},
    {"role": "SECURITY", "urgency": "NORMAL", "text": "Check our file upload handler to prevent Server-Side Request Forgery (SSRF) and malicious file execution."},
    {"role": "SECURITY", "urgency": "NORMAL", "text": "Implement rate limiting and brute-force protection with account lockout for login and 2FA endpoints."},
    {"role": "SECURITY", "urgency": "NORMAL", "text": "Perform a threat model analysis on our OAuth2 single sign-on redirect flow and PKCE exchange."},
    {"role": "SECURITY", "urgency": "HIGH", "text": "Review API endpoints for IDOR (Insecure Direct Object Reference) allowing users to access other accounts."},
    {"role": "SECURITY", "urgency": "NORMAL", "text": "Audit encrypted data-at-rest keys and evaluate envelope encryption implementation with AWS KMS."},
    {"role": "SECURITY", "urgency": "NORMAL", "text": "Check session management cookies for HttpOnly, Secure, and SameSite=Strict security flags."},

    # ── DEVOPS (Docker, Kubernetes, CI/CD, Terraform, Cloud, Scripts) ───────
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Write a multi-stage Dockerfile to compile our Go backend and produce a minimal Distroless container image."},
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Create a GitHub Actions workflow to run automated tests, linting, and publish Docker images to GHCR."},
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Write Terraform HCL scripts to provision an AWS ECS Fargate cluster with an Application Load Balancer."},
    {"role": "DEVOPS", "urgency": "HIGH", "text": "Urgent prod incident: Kubernetes pod CrashLoopBackOff on production ingress controller. Debug and restart."},
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Configure Prometheus metrics scraping and set up Grafana alert rules for CPU and memory saturation."},
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Write a Bash script to automate daily automated PostgreSQL database backups and upload encrypted dumps to S3."},
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Set up a blue-green zero-downtime deployment pipeline in ArgoCD for our Kubernetes microservices."},
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Create Kubernetes Helm charts and values.yaml for deploying staging and production environments."},
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Configure Nginx reverse proxy configuration with TLS 1.3 certificates, gzip compression, and caching."},
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Automate log aggregation by deploying Fluent Bit daemonsets shipping logs to Elasticsearch."},
    {"role": "DEVOPS", "urgency": "HIGH", "text": "Immediate production outage: Disk space 100% full on root volume of production database server."},
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Write an Ansible playbook to configure SSH hardening, fail2ban, and automatic security updates on Ubuntu servers."},
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Configure AWS CloudFront CDN distribution with custom cache policies and origin request routing."},
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Create a cleanup cron job script to prune dangling Docker images, volumes, and temporary build caches."},
    {"role": "DEVOPS", "urgency": "NORMAL", "text": "Set up OpenTelemetry collector agent on Linux nodes to export distributed traces to Jaeger."}
]

def run_benchmark():
    print("=" * 75)
    print("  LAYA SYSTEM-1 ROUTER BENCHMARK (105 REALISTIC WORKSPACE TASKS)")
    print("=" * 75)

    total = len(BENCHMARK_DATASET)
    role_correct = 0
    urgency_correct = 0
    latencies = []
    
    confusion = {r: {r2: 0 for r2 in ["CEO", "PM", "ARCHITECT", "CODER", "TESTER", "SECURITY", "DEVOPS"]} for r in ["CEO", "PM", "ARCHITECT", "CODER", "TESTER", "SECURITY", "DEVOPS"]}
    misclassifications = []

    start_total = time.time()
    for i, item in enumerate(BENCHMARK_DATASET):
        res = route_request(item["text"])
        latencies.append(res["latency_ms"])
        
        pred_role = res["domain"]
        expected_role = item["role"]
        
        pred_urgency = res["urgency"]
        expected_urgency = item["urgency"]

        confusion[expected_role][pred_role] += 1

        is_role_match = (pred_role == expected_role)
        is_urg_match = (pred_urgency == expected_urgency)

        if is_role_match:
            role_correct += 1
        else:
            misclassifications.append({
                "text": item["text"],
                "expected": expected_role,
                "predicted": pred_role,
                "urgency_expected": expected_urgency,
                "urgency_predicted": pred_urgency
            })

        if is_urg_match:
            urgency_correct += 1

    total_time = time.time() - start_total
    avg_latency = sum(latencies) / len(latencies)

    role_acc = (role_correct / total) * 100
    urg_acc = (urgency_correct / total) * 100

    print(f"\n[RESULTS SUMMARY]")
    print(f"  Total Evaluated:        {total} tasks (15 per role)")
    print(f"  Role Accuracy:          {role_correct}/{total} ({role_acc:.1f}%)")
    print(f"  Urgency Accuracy:       {urgency_correct}/{total} ({urg_acc:.1f}%)")
    print(f"  Avg Latency per Task:   {avg_latency:.1f} ms (Target: ~33ms)")
    print(f"  Total Benchmark Time:   {total_time:.2f} seconds")

    print("\n[PER-ROLE RECALL]")
    for role in ["CEO", "PM", "ARCHITECT", "CODER", "TESTER", "SECURITY", "DEVOPS"]:
        correct_for_role = confusion[role][role]
        total_for_role = sum(confusion[role].values())
        rec = (correct_for_role / total_for_role) * 100
        print(f"  {role:<10}: {correct_for_role}/{total_for_role} ({rec:.1f}%)")

    if misclassifications:
        print(f"\n[MISCLASSIFICATIONS ({len(misclassifications)})]")
        for m in misclassifications[:12]:
            print(f"  Expected [{m['expected']}] -> Got [{m['predicted']}] | \"{m['text'][:70]}...\"")
        if len(misclassifications) > 12:
            print(f"  ...and {len(misclassifications) - 12} more.")

    return {
        "role_accuracy": role_acc,
        "urgency_accuracy": urg_acc,
        "avg_latency": avg_latency,
        "misclassifications": misclassifications
    }

if __name__ == "__main__":
    run_benchmark()
