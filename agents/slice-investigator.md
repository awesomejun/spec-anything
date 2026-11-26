# Slice Investigator Subagent Protocol

Used in **Phase 3** to investigate one domain slice of `03_scope/features.json` in an isolated context without polluting the coordinator context window.

## Input Contract
Each investigator receives:
1. Assigned `feature_id` list (e.g., `F-004` through `F-009`).
2. Filtered slice of `.spec-anything/source_map.json` and `04_environment/release_audit.json`.
3. Target `output_language` (`en` | `ko` | `ja`) and active `tier` (`T1` | `T2` | `T3`).

## Mandatory Tracing Procedure
For every assigned `feature_id`:
1. **Entry Point**: Identify exact user interaction, CLI flag, HTTP route, IPC channel, or timer trigger with `[REF: path:start-end]`.
2. **Handler & Validation**: Trace request parsing, schema/business validation rules, error status codes, and edge guards.
3. **State & Concurrency**: Record locks, transactions, WAL/isolation behavior, idempotency keys, and cancellation paths.
4. **External & OS Boundary**: Document filesystem, SQLite/DB, subprocess, network, or OS IPC calls. If a path breaks due to plugins, dynamic loading, external APIs, or OS-specific branches, stop at the last verified point and state the exact reason.
5. **Release Alignment (REA)**: Cross-check whether the official release artifact (`04_environment/release_audit.json`) ships the exact same handler/asset or diverges (build flags, stripped debug, embedded SPA assets, enterprise overlays).
6. **Live Verification (`T2`/`T3`)**: Emit reproducible observation entries conforming to `schemas/evidence.schema.json` and append them to the slice evidence draft.

## Severity Escalation (Question Bank Rule)
- **Critical ambiguity** (changes contract/security/persistence): Mark section `[BLOCKED: Q-XXX]` and append a choice-based question to `.spec-anything/questions.json`.
- **Non-critical ambiguity**: Proceed with `[ASSUMED: ...]` + `[CONFIDENCE: MED|LOW]` and log a follow-up question.
- Never silently omit a source file or fabricate behavior absent from code or runtime observation.

## Required Return Structure
- Draft section Markdown with `[REF: path:start-end]` citations and a literal `## Sources Read` list.
- Slice JSONL records conforming to `schemas/evidence.schema.json`.
- Slice contract fragments (OpenAPI paths / JSON Schema definitions / SQL DDL).
- Structure-only Mermaid sequence/state block (no hardcoded colors).
