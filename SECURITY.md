# Security Policy

Amadeus is a **local, single-user command-line tool**. It runs with your user
account's privileges, stores data as plain files under `~/.amadeus/`, and sends
no telemetry. This document describes the supported versions, the threat model,
and how to report a vulnerability.

## Supported Versions

| Version | Supported |
| --- | --- |
| 0.1.x | ✅ Active |
| < 0.1 | ❌ Pre-refactor; unsupported |

Until a 1.0 release, only the latest minor version receives security fixes.

## Threat Model (Summary)

Amadeus has no network listener, no authentication surface, and no multi-tenant
data. The realistic risk surfaces are:

| Surface | Risk | Mitigation |
| --- | --- | --- |
| Web research fetch | Malicious/oversized remote HTML | Timeouts, size caps, parser-only (no JS execution) |
| System cleanup | Deleting unintended paths | Strict allow-list + `--dry-run` |
| Git subprocess | Command execution context | Fixed argument vectors; no shell string interpolation |
| Local LLM | Untrusted model files | You choose the model; inference is offline |
| Storage | Plaintext notes/tasks | Rely on filesystem permissions; see recommendations |

A full discussion lives in [docs/security.md](docs/security.md).

## Reporting a Vulnerability

**Please do not open a public issue for security vulnerabilities.**

1. Email **monkeydluffy55gear5@gmail.com** with the subject line
   `SECURITY: Amadeus`.
2. Include:
   - A description of the vulnerability and its impact.
   - Steps to reproduce (a proof of concept if possible).
   - Affected version (`amadeus --version`) and environment.
   - Any suggested remediation.
3. You will receive an acknowledgement within **5 business days**.

### Disclosure Process

| Stage | Target timeline |
| --- | --- |
| Acknowledgement | ≤ 5 business days |
| Triage & severity assessment | ≤ 10 business days |
| Fix developed & released | Depends on severity (critical issues prioritized) |
| Public disclosure | After a fix is available, coordinated with the reporter |

We support **coordinated disclosure** and will credit reporters who wish to be
named in the release notes and `CHANGELOG.md`.

## Security Recommendations for Users

- Treat `~/.amadeus/` as sensitive — notes may contain private information.
  Restrict permissions: `chmod 700 ~/.amadeus`.
- Only run `amadeus sys clean` after reviewing your `clean_targets` and a
  `--dry-run`. Privileged targets (apt, journald) require appropriate rights.
- Download GGUF models only from trusted sources (e.g. official Hugging Face
  repositories).
- Keep dependencies current: `uv sync` against the committed `uv.lock`.

## Out of Scope

- Vulnerabilities requiring an already-compromised local account.
- Issues in third-party model weights.
- Social-engineering or physical-access attacks.
