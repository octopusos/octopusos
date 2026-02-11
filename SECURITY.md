# Security Policy

## Supported Versions

OctopusOS is currently in **early-stage development**.

Only the **latest release on the default branch** is supported for security reporting.  
Older releases and development snapshots may not receive security fixes.

---

## Reporting a Vulnerability

If you discover a security vulnerability in OctopusOS, **please do not open a public issue**.

Instead, report it privately using one of the following methods:

- GitHub Security Advisories (preferred)
- Email: **security@seacow.tech** *(replace with your preferred contact if needed)*

When reporting, please include:
- A clear description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact and risk assessment
- Any suggested mitigation or fix

You will receive an acknowledgment within a reasonable timeframe.

---

## Responsible Disclosure

We follow a **responsible disclosure** process:

- Security reports are reviewed privately
- Fixes are developed and validated before public disclosure
- Credit may be given to reporters upon request

Please allow time for investigation and remediation before public discussion.

---

## Security Scope

OctopusOS is designed to run **locally or in private environments**.

Out of scope:
- Misconfiguration of user environments
- Exposed deployments on public networks
- Third-party model or provider vulnerabilities

In scope:
- Remote code execution risks
- Privilege escalation
- Data leakage
- Unsafe default configurations
- Injection or sandbox escape vectors

---

## Deployment Warnings

⚠️ **Do not expose OctopusOS directly to the public internet.**

OctopusOS does **not** include:
- Authentication systems
- Multi-tenant isolation
- Hardened sandboxing guarantees

If you deploy OctopusOS in shared or network-accessible environments, you are responsible for additional security controls.

---

## Security Philosophy

OctopusOS prioritizes:
- Explicit execution boundaries
- Observability over hidden behavior
- Failsafe defaults over convenience

Security hardening improves incrementally as the project evolves.

---

Thank you for helping keep OctopusOS and its users safe.