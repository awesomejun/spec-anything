---
name: spec-anything
description: >
  Turn any open-source GitHub repository and optional authorized official release
  into an evidence-backed, 12-artifact reimplementation specification (01 PRD through
  12 Implementation Sequence) with machine-readable contracts (09), live UI/runtime
  evidence (05, 06), release binary/bundle diffing (REA), and executable differential
  parity tests (07). Use when reverse-specifying an existing repository, porting an
  app to another language or stack, auditing release-vs-source parity, or generating
  verifiable clean-room PRD and SDD deliverables.
argument-hint: <repo_url_or_path> [--release <artifact_path_or_url>] [--tier T1|T2|T3] [--depth outline|comprehensive|interactive] [--lang en|ko|ja] [--render html,docx,pdf]
allowed-tools: >
  Read, Write, Edit, Glob, Grep, Task, AskUserQuestion,
  Bash(python3 */scripts/state_manager.py *),
  Bash(python3 */scripts/source_map.py *),
  Bash(python3 */scripts/file_inventory.py *),
  Bash(python3 */scripts/inspect_release.py *),
  Bash(python3 */scripts/secret_guard.py *),
  Bash(python3 */scripts/validate_bundle.py *),
  Bash(python3 */scripts/render_review.py *),
  Bash(git *), Bash(shasum *), Bash(sqlite3 *)
---

# spec-anything — Evidence-Backed 12-Artifact Reimplementation Spec & Parity Harness

`spec-anything` reverse-engineers any existing open-source repository (and its official release artifact, when authorized) into a **fixed 12-artifact specification (`01`–`12`)** anchored on **Feature IDs (`03`)**, **machine-readable runtime observations (`06` JSONL)**, **machine-readable contracts (`09`)**, and **executable differential parity tests (`07`)** that prove a clean-room reimplementation matches the original.

---

## Core Architecture & Design Principles

1. **Fixed 12-Artifact Taxonomy (No Extra Numbers)**
   Every run produces the exact 12 deliverables (`01` through `12`) defined in `references/deliverables-01-12.md`. Never invent `13+`. When a deliverable genuinely does not apply (for example, UI screenshots on a headless CLI), retain the numbered document with explicit `N/A` rationale and re-verification conditions.
2. **Triangulation Over Static Assumption (REA Discipline)**
   Never record official release behavior by reading public source alone. Cross-check three independent sources whenever available:
   - **Pinned source tree** (`code-verified`)
   - **Official release artifact** (SHA-256, upstream checksums, Electron ASAR/preload/main/IPC boundary, native Mach-O/ELF/PE build metadata & embedded SPA/asset bundles)
   - **Isolated runtime execution** (`observed`: multi-state UI screenshots, HTTP/RPC/SSE/WS streams, SQLite/DB persistence, graceful restart recovery)
   When source, release, and runtime conflict, formulate a hypothesis and resolve it with a reproducible input.
3. **Deterministic Parsers & File Census Before Interpretation**
   Run `scripts/source_map.py`, `scripts/file_inventory.py`, and `scripts/inspect_release.py` before drafting prose. Keep file accounting (tracked git file dispositions), extracted structural units, and executed runtime scenarios separated and reconciled. Never invent routes, settings, menus, APIs, or rules absent from extracted facts or live observations; log a **Loud Warning** when parser coverage is low or syntax is unsupported.
4. **Resumable 7-Phase State Machine (`.spec-anything/state.json`)**
   Persist phase progress, target commit/release digests, execution profile, and unresolved Question Bank entries via `scripts/state_manager.py`. Long sessions support `continue`, `rewind`, and targeted re-runs when upstream commits or releases change.
5. **2D Execution Profile (Observation Tier × Depth Mode)**
   Confirm both dimensions in Phase 0:
   - **Observation Tier**:
     - `T1` (Static): Source extraction + contracts; runtime and release items explicitly marked `unverified`.
     - `T2` (Runtime): Isolated build/run + API/stream/DB observations (`06`) + baseline-verified parity tests (`07`).
     - `T3` (Full Parity): `T2` + official release SHA-256 & binary/bundle REA diff + multi-state UI screenshots (`05`) + computed DOM/CSS tokens (`11`) + visual pixel tolerance verification (`07`).
   - **Depth Mode**: `outline` | `comprehensive` | `interactive`.
6. **5-State Honesty & Single Foreign Key Traceability**
   Every requirement (`03`) and evidence record (`06`) binds on `Feature ID` (`F-XXX`), carries `Evidence ID` (`EV-XXX`), `[REF: path:start-end]` or stable bundle location, artifact SHA-256, and exact status enum:
   `observed` | `code-verified` | `inferred` | `assumed` | `unverified`.
7. **Executable Closed-Loop Parity (`06` → `07`)**
   `07` parity tests MUST read observed inputs, preconditions, and expected outputs directly from `06_evidence/ledger.jsonl`. Verify against the **live upstream original first** (`upstream_baseline` PASS), then run the exact same harness against any clean-room reimplementation (`reimplementation_diff`). Scope of claimed parity is strictly limited to executed cases.
8. **English Machine Layer + Multi-Language Narrative Layer**
   Keep skill instructions, JSON schema keys, ASCII file slugs, Feature/Evidence/Screen/Test IDs, status enums, `[REF: path:start-end]`, `[CONFIDENCE: HIGH|MED|LOW]`, and the literal heading `## Sources Read` in **English forever** so automated validators never break. Render narrative prose in `goal.json.output_language` (`en`, `ko`, or `ja`).
9. **Structure-Only Mermaid Contract**
   Every Mermaid diagram (`10` or other docs) MUST remain structure-only: forbid hardcoded `style ... fill:`, `classDef` colors, `stroke:#...`, `color:#...`, and hex/RGB color literals so light and dark themes render cleanly.
10. **Secret Redaction & SSRF-Safe Rendering**
    Run `scripts/secret_guard.py --fail-on-hit` before sealing deliverables to block credentials and raw JWTs. Any HTML/PDF review renderer (`scripts/render_review.py`) MUST block `file://` URL fetches to prevent local file inclusion from untrusted repository content.
11. **Dual-Audience Delivery From a Single Source of Truth**
    Keep `01`–`12` Markdown/JSON/JSONL/SQL/tests as the canonical engineering source, and use `scripts/render_review.py` to generate dual-reader review artifacts (**PM & Design View**: `01` + `03` + `05` gallery + `11` tokens + SVG flow; **Dev & QA Parity View**: `02` + `04` REA + `06` ledger + `07` verdicts + `09` contracts + `10`/`08`/`12`).
12. **Clean-Room & Safety Non-Goals**
    Strictly limited to authorized open-source functional reimplementation, language porting, and interoperability verification. Explicitly prohibits vulnerability exploitation, access-control/DRM bypass, and unauthorized redistribution of copyrighted UI assets, fonts, or brand trademarks (separated in `04_environment/LICENSING.md`).

---

## 7-Phase Execution Workflow

### Phase 0 — Goal, Scope & Profile Lock
`python3 scripts/state_manager.py init --workdir <out_dir> --repo <url_or_path> --tier T3 --depth comprehensive --lang en`

### Phase 1 — Deterministic Static Recon, File Census & Release REA Audit
1. `python3 scripts/source_map.py <source_dir> --out <out_dir>/.spec-anything/source_map.json --facts <out_dir>/.spec-anything/facts.md`
2. `python3 scripts/file_inventory.py <git_repo_dir> <commit_sha> > <out_dir>/03_scope/files_census.json` (when target is a git checkout; verify dispositions later with `python3 scripts/file_inventory.py <git_repo_dir> <commit_sha> <out_dir>/03_scope/files_census.json`).
3. For `T3`: `python3 scripts/inspect_release.py --archive <release_archive> --binary <extracted_bin> --checksums <checksums_txt> --source <source_dir> --tag <tag> --commit <sha> --out <out_dir>/04_environment/release_audit.json`

### Phase 2 — Feature Matrix (`03`) & Reproduction Environment (`04`)
- Enumerate atomic features into `03_scope/features.json` (`--max-macro-ratio <= 0.15`) and `03_scope_matrix.md`.
- Record pinned commit, official release SHA-256, REA audit summary, synthetic seeds, test doubles, and code vs. asset licensing in `04_reproduction_env.md` and `04_environment/LICENSING.md`.

### Phase 3 — Parallel Slice Investigation & Isolated Runtime Observation (`05`, `06`, `09`, `10`, `11`)
- Dispatch domain slices via `agents/slice-investigator.md` and `references/adapters/target-adapters.md`.
- Launch upstream in an isolated temporary directory and loopback port; capture multi-state UI screenshots (`05`), live `getComputedStyle` design tokens (`11`), ordered runtime/SSE/DB/restart observations (`06_evidence/ledger.jsonl`), machine contracts (`09_contracts/`), and structure-only Mermaid diagrams (`10`).

### Phase 4 — Executable Parity Tests (`07`) & Dual Quality Gate
1. Implement executable parity tests in `07_tests/` that load `06_evidence/ledger.jsonl` directly, pass against the live upstream original first, and accept `--target-url` / candidate path for clean-room reimplementations.
2. Run security and 13-gate validation:
   - `python3 scripts/secret_guard.py <out_dir> --fail-on-hit`
   - `python3 scripts/validate_bundle.py <out_dir> --tier <T1|T2|T3>`
3. Loop back until all gates pass.

### Phase 5 — Conflict Resolution & Question Bank Closure
- Resolve source/release/runtime discrepancies with discriminating reproducible inputs; log unresolved ambiguities in `.spec-anything/questions.json` as `abandoned` / `unverified` with concrete re-verification steps.

### Phase 6 — Final Synthesis (`01`, `02`, `08`, `12`), Sealing & Dual-Audience Review Rendering
1. Synthesize `01_PRD.md`, `02_SDD.md`, `08_implementation_blueprint.md`, and `12_implementation_sequence.md` with `[REF: path:start-end]` citations and literal `## Sources Read` sections.
2. Generate `SHA256SUMS.txt` and run `python3 scripts/validate_bundle.py <out_dir> --tier <T1|T2|T3> --verify-checksums`.
3. Render review bundles: `python3 scripts/render_review.py <out_dir> --outdir <out_dir>/review --formats html,docx,pdf`.
4. Mark Phase 6 complete in `.spec-anything/state.json`.
