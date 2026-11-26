<div align="center">

# spec-anything

**Turn any open-source app into a verified clean-room specification — and prove a rebuild matches the real app.**

[![License: MIT](https://img.shields.io/badge/License-MIT-10b981.svg?style=flat-square)](LICENSE)
[![Agents](https://img.shields.io/badge/Agents-Claude%20Code%20%7C%20Codex%20%7C%20OpenBot-0f172a.svg?style=flat-square)](SKILL.md)
[![Verified](https://img.shields.io/badge/Verified-45%2F45%20Gates%20%C2%B7%2041%2F41%20Parity-3b82f6.svg?style=flat-square)](#examples)

**English** · [한국어](README.ko.md)

[Examples](#examples) · [How It Works](#how-it-works) · [Quick Start](#quick-start) · [Under the Hood](#under-the-hood-detailed-mechanism)

</div>

---

<table>
  <tr>
    <td width="25%" valign="top">
      <strong>Study real software</strong><br/>
      Inspects source code, official releases (<code>.dmg</code>, <code>.app</code>, npm), and live running screens together.
    </td>
    <td width="25%" valign="top">
      <strong>Clean-Room or Deep</strong><br/>
      Run black-box surface capture (<code>clean-room</code>) or full source, decompiler, and trace analysis (<code>deep</code>).
    </td>
    <td width="25%" valign="top">
      <strong>Checked, not guessed</strong><br/>
      Generates 12 cross-linked specs plus runnable parity tests and UI pixel-diff heatmaps.
    </td>
    <td width="25%" valign="top">
      <strong>Agent-ready skill</strong><br/>
      9 deterministic scripts and adapters for Claude Code, Codex CLI, OpenBot, Ghidra, IDA, and Frida.
    </td>
  </tr>
</table>

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

1. **Inspect code & official release** — Reads pinned source code and audits the shipped binary or package (`.dmg`, `.app`, ELF/PE, or npm tarball).
2. **Run the app live** — Launches the app in an isolated workspace to capture multi-state screenshots, measured CSS tokens, schemas, and observed state transitions.
3. **Generate 12 specs & parity tests** — Outputs fixed deliverables (`01`–`12`) and executable tests that check both the original app and any clean-room rebuild.

### Clean-Room vs. Deep Mode

- **`clean-room` (black-box)**: Observes only public UI, measured layout/CSS tokens, and external I/O without reading proprietary source internals.
- **`deep` (authorized open-source / owned targets)**: Unlocks full source extraction, official release REA auditing, headless **Ghidra** / **IDA** decompilation, and read-only **Frida** dynamic tracing.

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

### 2. Check installed engines & run from your agent

```bash
python3 scripts/doctor.py
```

```text
Use the spec-anything skill on https://github.com/Splode/pomotroid (v1.7.1, mode deep, tier T3)
to generate deliverables 01–12, build a clean-room reimplementation, and pass all parity tests.
```

### 3. Verify all 3 included examples locally (45/45 gates + governance & security self-tests)

```bash
for ex in examples/*; do python3 scripts/validate_bundle.py "$ex" --tier T3 --verify-checksums; done
python3 scripts/validate_bundle.py --self-test
python3 scripts/frida_trace_bridge.py self-test
python3 scripts/secret_guard.py --self-test && python3 scripts/secret_guard.py . --fail-on-hit --scan-injections
```

---

## Under the Hood: Detailed Mechanism

Everything below documents the complete internal pipeline, multi-backend reverse-engineering architecture, concrete audit discoveries, and mechanical validation gates.

### 1. Four-Layer Triangulation & Inspired Open-Source Foundations

Reading source code alone misses what official releases actually package, compile, and render. `spec-anything` builds on spec-driven & reverse-planning foundations from [`daishir0/cc-rsg`](https://github.com/daishir0/cc-rsg), [`WindowHyun/Reverse_Spec_and_PRD`](https://github.com/WindowHyun/Reverse_Spec_and_PRD), [`github/spec-kit`](https://github.com/github/spec-kit), and [`Fission-AI/OpenSpec`](https://github.com/Fission-AI/OpenSpec), combines clean-room workflow design from [`storytold/craft-anything`](https://github.com/storytold/craft-anything), and connects optional static/dynamic reverse-engineering backends from [`NationalSecurityAgency/ghidra`](https://github.com/NationalSecurityAgency/ghidra), [`HexRaysSA/ida-mcp`](https://github.com/HexRaysSA/ida-mcp) / [`mrexodia/ida-pro-mcp`](https://github.com/mrexodia/ida-pro-mcp), and [`frida/frida`](https://github.com/frida/frida):

```mermaid
flowchart LR
    T[Target Repo and Official Release] --> L1[Lane 1 Static Source Map and Git Census]
    T --> L2[Lane 2 Release REA OS Tools Ghidra IDA]
    T --> L3[Lane 3 Live Runtime Playwright and Frida]
    L1 --> EV[06 Machine-Readable Evidence Ledger JSONL]
    L2 --> EV
    L3 --> EV
    EV --> SP[01-03 08-12 Specs Contracts and UI Tokens]
    EV --> PT[07 Executable Parity Tests and Pixel Diff]
    SP --> CR[Clean-Room Reimplementation]
    CR --> PT
```

| Inspired Project / Ecosystem | Architectural Pattern Adopted in `spec-anything` | Concrete Implementation |
| :--- | :--- | :--- |
| **[`daishir0/cc-rsg`](https://github.com/daishir0/cc-rsg)** | Resumable 7-phase state machine (`state.json`), Question Bank, multi-language static extractor with Loud Warnings, anti-macro coverage gate, English machine layer + multi-language prose, structure-only Mermaid | `scripts/state_manager.py`, `scripts/source_map.py`, `scripts/validate_bundle.py` (`--max-macro-ratio`, `S4`, `S5`) |
| **[`WindowHyun/Reverse_Spec_and_PRD`](https://github.com/WindowHyun/Reverse_Spec_and_PRD)** | Parser-fact boundary (`facts.md`), automated secret redaction, dual-audience PM/Design & Dev/QA review documents with `file://` SSRF-safe HTML/SVG/DOCX/PDF export | `scripts/source_map.py --facts`, `scripts/secret_guard.py`, `scripts/render_review.py` |
| **[`github/spec-kit`](https://github.com/github/spec-kit)** & **[`Fission-AI/OpenSpec`](https://github.com/Fission-AI/OpenSpec)** | Spec-driven development baseline (`PRD → SDD → Contracts → Implementation Plan`) adapted from greenfield creation to verified reverse-engineering parity | Fixed `01`–`12` taxonomy (`references/deliverables-01-12.md`) anchored on `03` Feature IDs |
| **[`storytold/craft-anything`](https://github.com/storytold/craft-anything)** | Explicit `clean-room` vs. `deep` operating boundary, `doctor` preflight diagnostics, Hypothesis → Finding → Evidence tracking, multi-state visual comparison | `scripts/doctor.py`, `--mode clean-room` / `--mode deep` in `scripts/state_manager.py`, Playwright pixel-diff MAE verification |
| **[`NationalSecurityAgency/ghidra`](https://github.com/NationalSecurityAgency/ghidra)** & **[`pyghidra-mcp`](https://github.com/clearbluejar/pyghidra-mcp)** | Headless-first binary decompilation (`analyzeHeadless` / `pyghidra`), multi-binary project sessions, stripped symbol recovery, xrefs & call-target resolution | `scripts/inspect_release.py --backend ghidra`, `references/adapters/re-backends.md`, `rea-ghidra` MCP mapping into `04` / `06` / `10` |
| **[`HexRaysSA/ida-mcp`](https://github.com/HexRaysSA/ida-mcp)** & **[`mrexodia/ida-pro-mcp`](https://github.com/mrexodia/ida-pro-mcp)** | Headless `idat` / `idalib` multi-worker sessions (`idb_open` / `decompile` / `xrefs_to`), read-only `ida://` IDB metadata & local type resources, strict byte-offset & signedness verification | `scripts/inspect_release.py --backend ida`, `scripts/doctor.py` IDA 9.4+ / `ida-hcli` detection, `ida://types` → `09_contracts/` mapping |
| **[`frida/frida`](https://github.com/frida/frida)** & **[`frida/frida-tools`](https://github.com/frida/frida-tools)** | Dynamic read-only `Interceptor` runtime observation (SQLite C-API, ObjC `NSUserDefaults`, POSIX I/O, IPC streams) & `frida-itrace` `"ITR2"` binary framing | `scripts/frida_trace_bridge.py` (`emit-hook`, `ingest-jsonl`, `ingest-itrace`, offline `self-test` validating directly against `schemas/evidence.schema.json`) |

See [`references/adapters/re-backends.md`](references/adapters/re-backends.md) for full backend setup commands, MCP contracts, and non-bypass safety boundaries.

### 2. Governance, Safety & State-Integrity Layer (`v4.1`)

To prevent AI over-claiming, silent stale-evidence reuse, race corruption, and untrusted-input prompt injection, `spec-anything` enforces six deterministic governance mechanisms on top of the 4-layer engine:

| Governance Mechanism | What It Enforces | Implementation |
| :--- | :--- | :--- |
| **Machine-Ceiling Downgrade-Only Gate & Anti-Slop** | Computes deterministic `grade_ceiling` (`A`–`F`) and `can_claim_full_coverage` from observed ratio, failures, and degraded tools — AI verdicts may only maintain or downgrade, never exceed the ceiling; rejects `N/A`/`TODO`/`TBD`/`none`/`-`/empty payloads | `scripts/validate_bundle.py` (`GOV1`, optional exit `42` via `--strict-ceiling`), `schemas/parity_report.schema.json` |
| **Untrusted-Evidence Prompt-Injection Guard** | Enforces a fixed `SECURITY CONTRACT` preamble on evidence snapshots and scans 4 categories (`instruction_override`, `identity_hijack`, `tool_call_forgery`, `exfiltration_channel`) as non-blocking `[AI-Safety]` advisories | `scripts/secret_guard.py --scan-injections`, `SKILL.md`, `references/adapters/re-backends.md` |
| **3-Axis Bijective Tool Coverage Accounting** | Tracks every analyzer across `applicability × installation × execution` + `evidence_quality`, requires non-primary tools to appear in exactly one of `missing_tools` or `must_rerun_tools`, and separates `terminal_state_completion_rate` from `primary_tool_success_rate` | `scripts/doctor.py --emit-coverage`, `schemas/tool_coverage.schema.json`, `scripts/validate_bundle.py` (`GOV2`) |
| **Tamper- & Race-Safe State Machine + Epoch Isolation** | Uses atomic `temp + fsync + os.replace` writes, POSIX `fcntl.flock` session locks (`session_busy`), target-digest Epoch reset (`lineage_base_revision`), deterministic `cache_key`, retry budget (`max=3`), `reopen_events`, and append-only `RUN_MANIFEST.jsonl` | `scripts/state_manager.py`, `schemas/state.schema.json` |
| **3-Tier Secret Confidence Classifier** | Classifies secret detections into `info` (name only), `low` (short/placeholder), and `high` (prefix tokens, Bearer ≥20 chars, or ≥16 chars with ≥2 character classes), blocking gates only on `high` leaks | `scripts/secret_guard.py` (`SEC1`, `--min-confidence`) |
| **Non-Scope Contract, Defect Non-Inheritance & Requirement Levels** | Requires explicit "Specified Contract vs. Reimplementer Discretion" tables, upstream accidental-bug non-inheritance memos in `02`/`08`, and `must` / `should` / `optional` grading in `03` | `references/deliverables-01-12.md`, `schemas/feature_matrix.schema.json` |

### 3. Fixed 12-Artifact System (`01`–`12`) & 7-Phase Closed-Loop Pipeline

Every target produces the same **12 fixed deliverables**, cross-linked by `Feature ID` (`F-001`), `Evidence ID` (`EV-001`), and `Screen ID` (`SCR-001`), tagged with an explicit 5-state honesty enum (`observed`, `code-verified`, `inferred`, `assumed`, `unverified`), sealed with `SHA256SUMS.txt`, and checked by **15 mechanical quality gates**:

<img src="assets/12-artifacts-map.png" alt="The Fixed 12-Artifact System (01–12) and Mechanical Quality Gates" width="100%" />

```mermaid
flowchart LR
    P0[Phase 0 Doctor Mode and Tier Lock] --> P1[Phase 1 Static Map Census and REA Audit]
    P1 --> P2[Phase 2 03 Feature Matrix and 04 Environment]
    P2 --> P3[Phase 3 Live Runtime 05 UI 06 JSONL 09-11]
    P3 --> P4[Phase 4 07 Parity Tests Reading 06 and 15 Gates]
    P4 -->|Gate Fail Loopback| P3
    P4 --> P5[Phase 5 Conflict Resolution and Question Closure]
    P5 --> P6[Phase 6 01 02 08 12 SHA256SUMS and Review Views]
```

- **Closed-Loop Oracle Rule (`06 → 07`)**: `07` parity tests MUST read inputs, preconditions, and expected outputs directly from `06_evidence/ledger.jsonl`. Tests pass against the **live upstream original first** (`upstream_baseline`), then verify any clean-room rebuild (`reimplementation_diff`) with identical assertions and Playwright pixel-diff tolerances.
- **English Machine Layer + Multi-Language Narrative**: All schema keys, IDs (`F-001`, `EV-001`, `SCR-001`), `[REF: path:start-end]` citations, and literal `## Sources Read` headings stay English forever so automated validators remain deterministic, while prose renders in English, Korean, or Japanese.

### 4. What Static Code Reading Misses: Verified Live REA Findings

| Gap Missed by Static Reading Alone | Verified Live Across the 3 Included MIT Examples |
| :--- | :--- |
| **Published package vs. monorepo drift** | In [`Excalidraw v0.18.1`](examples/01-excalidraw-v0.18.1/), audited the official npm tarball (`dist/prod/index.js`, `65` ESM exports, SHA-512 verified) and captured `.excalidraw` v2 JSON roundtrip + light/dark canvas renders (`0.18%`–`0.46%` MAE). |
| **Renamed desktop IPC & notarized binary surface** | In [`Handy v0.10.2`](examples/02-handy-v0.10.2/) *(Nov 2026)*, audited the notarized macOS `arm64` `.dmg` (`14.3 MB`) and Mach-O binary, verifying all **`133 / 133`** Tauri v2 IPC commands and confirming legacy command removal (`change_push_to_talk` → `change_shortcut_activation_setting`). |
| **Embedded binary assets & hidden state sentinels** | In [`Pomotroid v1.7.1`](examples/03-pomotroid-v1.7.1/), proved the universal macOS Mach-O (`x86_64 + arm64`, `16.0 MB`) embeds exact commit SHA `4a02ac7` + all 38 themes inside the binary, and verified the `long_breaks_enabled=false` cycle sentinel (`work_round_number: 0 → 1`) plus `MIGRATION_1..6` SQLite WAL rules. |

### 5. Ecosystem Comparison

| Capability | Greenfield SDD (`spec-kit` / `OpenSpec`) | Frontend Reverse (`Reverse_Spec_and_PRD`) | Static Reverse (`cc-rsg`) | Clean-Room Engine (`craft-anything`) | Core RE (`Ghidra` / `IDA` / `Frida`) | `spec-anything` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Fixed 12-artifact clean-room PRD/SDD/Blueprint taxonomy (`01`–`12`) | — | — | — | — | — | ✓ |
| Deterministic multi-language static map & git file census | — | — | ✓ | ✓ | — | ✓ |
| Secret redaction & `file://` SSRF-safe dual-audience review renderer | — | ✓ | — | — | — | ✓ |
| Clean-Room vs. Deep boundary & 3-axis `doctor` coverage | — | — | — | ✓ | — | ✓ |
| Native binary decompilation & dynamic runtime tracing integration | — | — | — | ✓ | ✓ | ✓ |
| Machine-readable `06` JSONL ledger directly consumed by `07` parity tests | — | — | — | — | — | ✓ |
| 15-gate validator (Machine Ceiling, Anti-Slop, Prompt-Injection, `SHA256SUMS`) | — | — | ✓ | — | — | ✓ |

### 6. Deterministic Automation Scripts (`scripts/`)

| Script | Responsibility |
| :--- | :--- |
| [`scripts/doctor.py`](scripts/doctor.py) | Preflight readiness checker across core CLI tools, Playwright/PIL, OS native binary tools, Ghidra, IDA (`idalib`/`ida-hcli`), and Frida + 3-axis bijective `tool_coverage.json` emitter |
| [`scripts/state_manager.py`](scripts/state_manager.py) | Atomic `temp+os.replace` + POSIX `flock` 7-phase state machine, `--mode clean-room` / `--mode deep`, target-digest Epoch reset, retry budget, and append-only `RUN_MANIFEST.jsonl` |
| [`scripts/source_map.py`](scripts/source_map.py) | Multi-language static extractor (Go, TS/JS, Svelte, Vue, Python, Rust, SQL, HTML, CSS) with Loud Warnings on low coverage |
| [`scripts/file_inventory.py`](scripts/file_inventory.py) | Git-commit tracked file census and `03` Feature ID / exclusion disposition verifier |
| [`scripts/inspect_release.py`](scripts/inspect_release.py) | Official release archive/binary REA auditor (SHA-256, `checksums.txt`, `lipo`, `otool`, `nm`, `readelf`, `codesign`, `go version -m`, custom `--probe`, Ghidra/IDA backend detection) |
| [`scripts/frida_trace_bridge.py`](scripts/frida_trace_bridge.py) | Authorized read-only Frida Gum hook generator (`sqlite`, `objc-storage`, `posix-io`, `ipc`), JSONL & `frida-itrace` (`ITR2`) parser into `06_evidence/ledger.jsonl`, offline `self-test` |
| [`scripts/secret_guard.py`](scripts/secret_guard.py) | 3-tier (`high`/`low`/`info`) secret confidence classifier + 4-category `[AI-Safety]` untrusted prompt-injection detector (`--fail-on-hit`, `--scan-injections`, `--self-test`) |
| [`scripts/validate_bundle.py`](scripts/validate_bundle.py) | 15-gate mechanical & governance validator (12 deliverables, `[REF:]`, `## Sources Read`, macro ratio, structure-only Mermaid, JSON Schema, FK integrity, `06→07` linkage, OpenAPI/Schema/SQLite execution, 3-tier secrets, Machine Ceiling & Anti-Slop, 3-axis bijective coverage, `SHA256SUMS.txt`, `--strict-ceiling` exit `42`) |
| [`scripts/render_review.py`](scripts/render_review.py) | Dual-audience PM/Design & Dev/QA single-file HTML, SVG, DOCX, and `file://` SSRF-safe PDF review renderer |

### 7. Clean-Room Policy, References & License

- **Authorized Scope Only**: Strictly intended for authorized open-source functional reimplementation, language porting, and interoperability verification. Explicitly prohibits vulnerability exploitation, access-control/DRM/anti-cheat bypass, memory patching, and unauthorized redistribution of copyrighted UI assets, fonts, or brand trademarks.
- **Additional Docs**: [`SKILL.md`](SKILL.md) · [`references/adapters/re-backends.md`](references/adapters/re-backends.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **License**: Released under the **[MIT License](LICENSE)**.
