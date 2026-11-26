<div align="center">

# spec-anything

**Turn any open-source app into a verified clean-room specification — and prove a rebuild matches the real app.**

[![License: MIT](https://img.shields.io/badge/License-MIT-10b981.svg?style=flat-square)](LICENSE)
[![Agents](https://img.shields.io/badge/Agents-Claude%20Code%20%7C%20Codex%20%7C%20OpenBot-0f172a.svg?style=flat-square)](SKILL.md)
[![Verified](https://img.shields.io/badge/Verified-39%2F39%20Gates%20%C2%B7%2041%2F41%20Parity-3b82f6.svg?style=flat-square)](#examples)

**English** · [한국어](README.ko.md)

</div>

---

`spec-anything` is an AI coding skill that inspects an open-source app's **source code**, **official release binary**, and **live running UI** to produce **12 fixed spec files (`01`–`12`)** plus **automated parity tests**.

## Examples

Every example below was rebuilt from scratch using only the generated spec — zero original source code or brand marks copied.

<img src="assets/reimpl-proof-banner.png" alt="Original vs. Clean-Room Rebuild across Excalidraw, Handy, and Pomotroid" width="100%" />

| App (MIT) | What It Is | Parity Tests | Visual Match | Bundle |
| :--- | :--- | :---: | :---: | :--- |
| [**Excalidraw**](https://github.com/excalidraw/excalidraw) `v0.18.1` | Hand-drawn whiteboard | `12 / 12` | `99.5%` (`0.46%` MAE) | [Spec](examples/01-excalidraw-v0.18.1/) · [Rebuild](examples/01-excalidraw-v0.18.1/cleanroom-reimpl/) |
| [**Handy**](https://github.com/cjpais/Handy) `v0.10.2` *(2026)* | Offline speech-to-text | `15 / 15` | `98.3%` (`1.67%` MAE) | [Spec](examples/02-handy-v0.10.2/) · [Rebuild](examples/02-handy-v0.10.2/cleanroom-reimpl/) |
| [**Pomotroid**](https://github.com/Splode/pomotroid) `v1.7.1` | Circular study timer | `14 / 14` | `99.2%` (`0.83%` MAE) | [Spec](examples/03-pomotroid-v1.7.1/) · [Rebuild](examples/03-pomotroid-v1.7.1/cleanroom-reimpl/) |

> Open [`assets/reimpl-proof-interactive.html`](assets/reimpl-proof-interactive.html) locally in any browser to compare all 6 screens with a slider (EN / KO).

## How It Works

1. **Inspect code & official release** — Reads source code and audits the shipped release package (`.dmg`, `.app`, or npm tarball).
2. **Capture live ground truth** — Runs the app in an isolated workspace to record screenshots, UI tokens, schemas, and observed state transitions.
3. **Generate specs & parity tests** — Writes 12 cross-linked deliverables (`01`–`12`) and executable tests that check both the original app and any clean-room rebuild.

<details>
<summary><strong>See all 12 generated deliverables (01–12)</strong></summary>

| Group | Deliverables |
| :--- | :--- |
| **Product & Architecture** | `01` PRD · `02` SDD · `03` Feature Matrix · `08` Clean-Room Blueprint · `12` Implementation Plan |
| **Live Evidence** | `04` Environment & Release Audit · `05` UI Screenshots · `06` Runtime Evidence (`JSONL`) |
| **Contracts & Verification** | `07` Executable Parity Tests · `09` Machine Contracts (JSON Schema / OpenAPI / SQL) · `10` State Flows · `11` UI Tokens |

</details>

## Quick Start

### 1. Install the skill

```bash
mkdir -p ~/.claude/skills/spec-anything
cp -r SKILL.md LICENSE schemas scripts agents references templates ~/.claude/skills/spec-anything/
```

Requires Python `3.10+`. For UI screenshots, pixel diffs, and PDF/DOCX review exports, install:

```bash
pip install jsonschema markdown pillow playwright python-docx && playwright install chromium
```

### 2. Run it from your agent

```text
Use the spec-anything skill on https://github.com/Splode/pomotroid (v1.7.1, tier T3)
to generate deliverables 01–12, build a clean-room reimplementation, and pass all parity tests.
```

### 3. Verify the included examples locally

```bash
for ex in examples/*; do python3 scripts/validate_bundle.py "$ex" --tier T3 --verify-checksums; done
python3 scripts/secret_guard.py . --fail-on-hit
```

## Why `spec-anything`?

| Capability | Greenfield SDD | Static Reverse Spec | `spec-anything` |
| :--- | :---: | :---: | :---: |
| Source extraction & resumable workflow | — | ✓ | ✓ |
| Official release binary / package audit (`SHA-256`) | — | — | ✓ |
| Live UI screenshots, CSS tokens & runtime ledger | — | — | ✓ |
| Executable parity tests & pixel-diff proof | — | — | ✓ |

## Documentation & License

- **[Architecture, Release Audit & Scripts Reference](docs/ARCHITECTURE.md)** — Full 7-phase pipeline, 12-artifact diagram, concrete REA discoveries, 7 automation scripts, and detailed ecosystem comparison.
- **[Skill Definition](SKILL.md)** — Complete agent workflow instructions and quality gates.
- **License** — [MIT](LICENSE). Strictly for authorized clean-room reimplementation and interoperability verification (excludes DRM/access bypass and trademark reuse).
