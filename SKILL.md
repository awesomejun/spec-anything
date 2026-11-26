---
name: spec-anything
description: >
  Turn any open-source GitHub repository and optional authorized official release
  into an evidence-backed, 12-artifact clean-room specification (01 PRD through
  12 Implementation Sequence) with machine-readable contracts (09), live UI/runtime
  evidence (05, 06), release binary/bundle auditing (OS REA, Ghidra, IDA, Frida),
  Clean-Room vs. Deep operating modes, and executable differential parity tests (07).
  Use when reverse-specifying an existing app, porting to another language or stack,
  auditing release-vs-source parity, or generating verifiable clean-room PRD and SDD deliverables.
argument-hint: <repo_url_or_path> [--release <artifact_path_or_url>] [--mode clean-room|deep] [--tier T1|T2|T3] [--depth outline|comprehensive|interactive] [--lang en|ko|ja] [--render html,docx,pdf]
allowed-tools: >
  Read, Write, Edit, Glob, Grep, Task, AskUserQuestion,
  Bash(python3 */scripts/doctor.py *),
  Bash(python3 */scripts/state_manager.py *),
  Bash(python3 */scripts/source_map.py *),
  Bash(python3 */scripts/file_inventory.py *),
  Bash(python3 */scripts/inspect_release.py *),
  Bash(python3 */scripts/frida_trace_bridge.py *),
  Bash(python3 */scripts/secret_guard.py *),
  Bash(python3 */scripts/validate_bundle.py *),
  Bash(python3 */scripts/render_review.py *),
  Bash(git *), Bash(shasum *), Bash(sqlite3 *)
---

# spec-anything — Evidence-Backed 12-Artifact Clean-Room Spec & Parity Harness (v4.0)

`spec-anything` turns any authorized open-source app (and its official release binary or package) into a **fixed 12-artifact specification (`01`–`12`)** anchored on **Feature IDs (`03`)**, **machine-readable runtime observations (`06` JSONL)**, **machine-readable contracts (`09`)**, and **executable differential parity tests (`07`)** that prove a clean-room rebuild matches the real running app.

---

## Core Architecture & Design Principles

1. **Fixed 12-Artifact Taxonomy (No Extra Numbers)**
   Every run produces the exact 12 deliverables (`01` through `12`) defined in `references/deliverables-01-12.md`. Never invent `13+`. When a deliverable genuinely does not apply (for example, UI screenshots on a headless CLI), retain the numbered document with explicit `N/A` rationale and re-verification conditions.
2. **Clean-Room vs. Deep Operating Modes (Inspired by `storytold/craft-anything`)**
   Confirm operating mode explicitly in Phase 0:
   - **`clean-room` (black-box surface)**: Observes only public behavior — live multi-viewport UI screenshots, visible DOM/accessibility text, measured `getComputedStyle` CSS tokens, public API/IPC responses, and observable file/storage outputs. Never reads proprietary/unlicensed source code or copies copyrighted assets.
   - **`deep` (authorized open-source / owned targets)**: Adds pinned source extraction, official release binary/bundle REA auditing, static decompilation (**Ghidra** / **IDA**), and read-only dynamic runtime tracing (**Frida**).
3. **4-Layer Analysis & Instrumentation Engine (OS REA · Ghidra · IDA · Frida)**
   Never record official release behavior by reading public source alone. Cross-check independent lanes via `references/adapters/re-backends.md`:
   - **Preflight `doctor`**: Run `python3 scripts/doctor.py` to detect available OS binary tools, Ghidra (`analyzeHeadless` / `pyghidra` / `pyghidra-mcp`), IDA (`HexRaysSA/ida-mcp` / `idalib` / `idat`), and Frida (`frida-trace` / `frida-itrace`).
   - **Pinned source tree** (`code-verified`): Deterministic multi-language extraction (`scripts/source_map.py`) + git tracked file census (`scripts/file_inventory.py`).
   - **Official release static/decompiler lane** (`observed` / `release_rea`): `scripts/inspect_release.py` (SHA-256, `codesign`, `otool`, `lipo`, `nm`, `readelf`, `go version -m`, Tauri/Electron/npm/Mach-O/ELF probes), optionally deepened via headless **Ghidra** (`pyghidra-mcp` / `rea-ghidra`) or **IDA Pro** (`HexRaysSA/ida-mcp` / `idalib` workers & `ida://` read-only resources).
   - **Isolated runtime & dynamic tracing lane** (`observed`): Headless Playwright multi-state UI capture + `getComputedStyle` tokens + HTTP/IPC/SQLite persistence + restart recovery, optionally augmented by read-only **Frida** observers (`scripts/frida_trace_bridge.py` → `06_evidence/ledger.jsonl`).
4. **Resumable 7-Phase State Machine (`.spec-anything/state.json`)**
   Persist phase progress, mode (`clean-room`|`deep`), target commit/release digests, execution tier (`T1`|`T2`|`T3`), and Hypothesis / Question Bank entries via `scripts/state_manager.py`. Long sessions support `continue`, `rewind`, and targeted re-runs when upstream releases change.
5. **5-State Honesty & Single Foreign Key Traceability**
   Every requirement (`03`) and evidence record (`06`) binds on `Feature ID` (`F-XXX`), carries `Evidence ID` (`EV-XXX`), `[REF: path:start-end]` or stable bundle/binary address, artifact SHA-256, limitations, and exact status enum:
   `observed` | `code-verified` | `inferred` | `assumed` | `unverified`.
6. **Executable Closed-Loop Parity (`06` → `07`)**
   `07` parity tests MUST read observed inputs, preconditions, and expected outputs directly from `06_evidence/ledger.jsonl`. Verify against the **live upstream original first** (`upstream_baseline` PASS), then run the exact same unmodified harness against any clean-room reimplementation (`reimplementation_diff`) with Playwright pixel-diff MAE verification.
7. **English Machine Layer + Multi-Language Narrative Layer**
   Keep skill instructions, JSON schema keys, ASCII file slugs, Feature/Evidence/Screen/Test IDs, status enums, `[REF: path:start-end]`, `[CONFIDENCE: HIGH|MED|LOW]`, and literal `## Sources Read` in **English forever** so automated validators never break. Render narrative prose in `goal.json.output_language` (`en`, `ko`, or `ja`).
8. **Structure-Only Mermaid, Secret Redaction & SSRF-Safe Rendering**
   Forbid hardcoded colors in Mermaid diagrams. Run `scripts/secret_guard.py --fail-on-hit` before sealing deliverables. `scripts/render_review.py` blocks `file://` URL fetches while emitting dual-audience **PM & Design** and **Dev & QA Parity** HTML/SVG/DOCX/PDF views.
9. **Clean-Room & Safety Non-Goals**
   Strictly limited to authorized open-source functional reimplementation, language porting, and interoperability verification. Explicitly prohibits vulnerability exploitation, access-control/DRM/anti-cheat bypass, memory patching, and unauthorized redistribution of copyrighted UI assets, fonts, or brand trademarks (separated in `04_environment/LICENSING.md`).

---

## 7-Phase Execution Workflow

### Phase 0 — Preflight Doctor, Goal, Mode & Tier Lock
1. `python3 scripts/doctor.py`
2. `python3 scripts/state_manager.py init --workdir <out_dir> --repo <url_or_path> --mode <clean-room|deep> --tier T3 --depth comprehensive --lang en`

### Phase 1 — Deterministic Static Recon, File Census & Release REA Audit
1. (`deep` mode) `python3 scripts/source_map.py <source_dir> --out <out_dir>/.spec-anything/source_map.json --facts <out_dir>/.spec-anything/facts.md`
2. (`deep` mode) `python3 scripts/file_inventory.py <git_repo_dir> <commit_sha> > <out_dir>/03_scope/files_census.json`
3. For `T3`: `python3 scripts/inspect_release.py --archive <release_archive> --binary <extracted_bin> --checksums <checksums_txt> --source <source_dir> --tag <tag> --commit <sha> --backend auto --out <out_dir>/04_environment/release_audit.json`
4. When native binary symbols or IPC dispatch tables require deeper verification in `deep` mode, invoke the optional **Ghidra** (`pyghidra-mcp` / `rea-ghidra`) or **IDA** (`HexRaysSA/ida-mcp` / `idalib`) lanes per `references/adapters/re-backends.md`.

### Phase 2 — Feature Matrix (`03`) & Reproduction Environment (`04`)
- Enumerate atomic features into `03_scope/features.json` (`--max-macro-ratio <= 0.15`) and `03_scope_matrix.md`.
- Record pinned commit, official release SHA-256, REA/decompiler backend provenance, synthetic seeds, test doubles, and code vs. asset licensing in `04_reproduction_env.md` and `04_environment/LICENSING.md`.

### Phase 3 — Parallel Slice Investigation & Isolated Runtime Observation (`05`, `06`, `09`, `10`, `11`)
- Dispatch domain slices via `agents/slice-investigator.md`, `references/adapters/target-adapters.md`, and `references/adapters/re-backends.md`.
- Launch upstream in an isolated temporary directory and loopback port; capture multi-state & multi-viewport UI screenshots (`05`), live `getComputedStyle` design tokens (`11`), ordered runtime/IPC/DB/restart observations (`06_evidence/ledger.jsonl`), machine contracts (`09_contracts/`), and structure-only Mermaid diagrams (`10`).
- When dynamic runtime boundaries (SQLite C-API, ObjC storage, stdio IPC, native trace blocks) require instrumentation on authorized targets, capture read-only traces via `scripts/frida_trace_bridge.py` directly into `06_evidence/ledger.jsonl`.

### Phase 4 — Executable Parity Tests (`07`) & Dual Quality Gate
1. Implement executable parity tests in `07_tests/` that load `06_evidence/ledger.jsonl` directly, pass against the live upstream original first, and accept `--target-url` / candidate path for clean-room reimplementations.
2. Run security and 13-gate validation:
   - `python3 scripts/secret_guard.py <out_dir> --fail-on-hit`
   - `python3 scripts/validate_bundle.py <out_dir> --tier <T1|T2|T3>`
3. Loop back until all gates pass.

### Phase 5 — Hypothesis Resolution & Question Bank Closure
- Resolve source/release/runtime discrepancies with discriminating reproducible inputs; log unresolved ambiguities in `.spec-anything/questions.json` as `abandoned` / `unverified` with concrete re-verification steps.

### Phase 6 — Final Synthesis (`01`, `02`, `08`, `12`), Sealing & Dual-Audience Review Rendering
1. Synthesize `01_PRD.md`, `02_SDD.md`, `08_implementation_blueprint.md`, and `12_implementation_sequence.md` with `[REF: path:start-end]` citations and literal `## Sources Read` sections.
2. Generate `SHA256SUMS.txt` and run `python3 scripts/validate_bundle.py <out_dir> --tier <T1|T2|T3> --verify-checksums`.
3. Render review bundles: `python3 scripts/render_review.py <out_dir> --outdir <out_dir>/review --formats html,docx,pdf`.
4. Mark Phase 6 complete in `.spec-anything/state.json`.
