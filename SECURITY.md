# Security Policy

## Supported Versions

Episteme is a young project. Security fixes are applied to the latest released
version on the `main` branch.

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

We take the security of Episteme seriously. If you discover a security
vulnerability, please report it **privately** rather than opening a public
issue.

**Do not disclose security-related issues in public GitHub issues, discussions,
or pull requests.**

Instead, please report via one of the following responsible-disclosure channels:

- **GitHub private vulnerability reporting:** use the
  "Report a vulnerability" button under the repository's
  *Security → Advisories* tab.
- **Email:** send details to the maintainer (harisawan-bit) via a GitHub
  private message, or open a security advisory.

Please include:

- A clear description of the vulnerability and its impact.
- Steps to reproduce, or a proof-of-concept.
- Affected version(s) and environment.
- Any suggested remediation, if known.

## What to Expect

- We will acknowledge receipt within **72 hours**.
- We aim to provide a remediation plan or fix within **14 days** for confirmed,
  high-severity issues.
- You will be credited in the advisory (unless you prefer to remain anonymous).

## Scope Notes

Episteme is a dependency-free, local, command-line tool that processes
bibliographic metadata and user-supplied effect-size data. It makes outbound
network calls only to NCBI PubMed E-utilities when you run `episteme run`.
Relevant threat categories include, but are not limited to:

- Unsafe handling of untrusted input files (effects JSON, PubMed responses).
- Injection or parsing flaws in generated SVG / markdown output.
- Improper network handling when fetching from PubMed.

Thank you for helping keep Episteme safe for evidence synthesis.
