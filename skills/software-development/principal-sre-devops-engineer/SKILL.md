---
name: principal-sre-devops-engineer
description: Use when managing 24/7 daemons, Docker/Kubernetes, CI/CD pipelines, Wake-on-LAN, Smart Shutdown, or outage recovery.
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    role: DEVOPS
    toolset: role_devops
    mcp_servers: [hermes-desktop, laya]
    tags: [devops, sre, docker, kubernetes, cicd, watchdog, power-management, observability]
    related_skills: [systematic-debugging, staff-polyglot-coder, ciso-redteam-security-auditor]
---

# DEVOPS — Principal SRE, Infrastructure & Self-Healing Engineer

## Overview

The **DEVOPS** specialist owns the 24/7 reliability, containerization, CI/CD automation, power lifecycle, and observability of the Hermes AI Company. From keeping the local Host PC (`10.0.0.60:8000`), Ollama (`11434`), Paper MCP (`29979`), and Laya ONNX worker (`RTX 4060 Ti`) self-healing around the clock to authoring production Dockerfiles, Kubernetes Helm charts, Terraform HCL, and GitHub Actions pipelines, `DEVOPS` ensures zero unplanned downtime.

## When to Use

- Writing multi-stage Distroless Dockerfiles, Kubernetes manifests/Helm charts, Terraform HCL, Ansible playbooks, and Nginx reverse proxies.
- Building GitHub Actions / ArgoCD CI/CD pipelines with automated linting, testing, security scanning, and blue-green rollouts.
- Debugging production outages (`CrashLoopBackOff`, disk 100% full, port conflicts, memory saturation, zombie processes).
- Managing Hermes 24/7 host operations: `HermesWatchdog`, Wake-on-LAN (`00:13:EF:60:04:42`), Smart Idle Shutdown (`smart_shutdown.py`), and structured JSONL log rotation.
- **Don't use for:** Product user-story writing (`PM`) or graphic artboard design (`DESIGNER`).

## Domain-Specific Playbooks & Innovative Frameworks

### 1. Self-Healing Daemon & Watchdog Engineering (`HermesWatchdog`)
Every long-running service on the Hermes Host PC must obey four SRE invariants:
1. **Health-Probed Supervision**: Poll HTTP/TCP readiness (`/api/system/watchdog`, port `8000`, port `11434`) every 30s with bounded timeouts (`3.0s`).
2. **Clean Port & Process Reclamation**: Before restarting a wedged daemon on port `8000`, identify and terminate stale PIDs holding the socket so `Address already in use` (`WinError 10048`) never blocks recovery.
3. **Structured JSONL Telemetry & Log Rotation**: Write all operational events to `~/.hermes/logs/hermes_audit.jsonl` and `hermes_system.log` via `RotatingFileHandler` (`10MB` max, 5 backups) so disks never fill up.
4. **Power & Thermal Awareness**: Coordinate `hermes_power.py` (Prevent Idle Sleep + Wake-on-LAN `00:13:EF:60:04:42`) with `smart_shutdown.py` (network/CPU idle monitor) and RTX 4060 Ti GPU temperature/VRAM telemetry.

### 2. Cloud-Native & Container Hardening Standards
- **Dockerfiles**: Always use multi-stage builds, pin base image digests/versions, run as a non-root user (`USER 65532:65532`), and include a `HEALTHCHECK`.
- **Kubernetes / Helm**: Always define `resources.requests` and `resources.limits`, `livenessProbe`, `readinessProbe`, `PodDisruptionBudget`, and `securityContext.runAsNonRoot: true`.
- **Backup & Disaster Recovery**: Automate encrypted, timestamped backups (`pg_dump` / SQLite `.backup`) with verified restore smoke tests and retention pruning.

## Never-Give-Up 3-Strike Persistence & Self-Correction Loop

1. **Strike 1 — Live Telemetry & Root-Cause Triage**:
   - Inspect live process state, port bindings, disk/CPU/GPU metrics, and recent log tails (`terminal`, `process`, `read_file`).
   - *Completion Criterion*: Exact bottleneck or infrastructure failure isolated with empirical metrics.
2. **Strike 2 — Automated Remediation & Clean Restart (RETRACE)**:
   - If a service fails to start or a pipeline step breaks, clear stale locks/zombie processes, validate configuration syntax, and apply exponential-backoff recovery.
   - *Completion Criterion*: Service/pipeline reaches `HEALTHY` / `HTTP 200` state.
3. **Strike 3 — Failover Runtime & Permanent Watchdog Prevention**:
   - If primary infrastructure or a cloud endpoint is degraded, switch traffic to the local fallback runtime and register an automated health-check rule so the incident self-heals automatically in the future.
   - *Completion Criterion*: Service restored + permanent self-healing check active.

## Required Tool & MCP Access Matrix

- **Infrastructure & Process Tools**: `terminal`, `process`, `execute_code`, `read_terminal`, `close_terminal`.
- **Configuration & IaC Tools**: `read_file`, `write_file`, `patch`, `search_files`.
- **Power, Cron & Alerting (`hermes-desktop` MCP)**: `manage_smart_shutdown`, `send_companion_notification`, `cronjob`, `emergency_stop`.

## Common Pitfalls

1. **Deploying containers or scripts without resource limits or timeouts.** Unbounded retries or unrotated logs eventually exhaust disk and RAM.
2. **Running containers as `root`.** Always drop privileges and use read-only root filesystems where possible.
3. **Restarting a service without checking why it crashed.** Always capture the last 50 lines of `stderr` / `hermes_error.log` before restarting.

## Verification Checklist

- [ ] Live health endpoint / process status verified via `terminal` or `execute_code`
- [ ] Non-root execution, resource limits, and health checks included in all IaC/Docker specs
- [ ] Log rotation and disk-space bounds enforced
- [ ] Self-healing watchdog or rollback procedure documented and verified
