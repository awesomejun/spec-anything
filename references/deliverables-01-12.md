# Fixed 12-Deliverable Contract (`01`–`12`)

Every `spec-anything` bundle contains the exact 12 numbered deliverables below. No extra numbers (`13+`) may be added. All cross-references bind through `03` Feature IDs (`F-XXX`).

| # | Canonical Slug | Role | Machine Companion | Primary Audience |
|---|---|---|---|---|
| `01` | `01_PRD.md` | User goals, journeys, feature specs, edge cases, acceptance criteria | References `03`, `05`, `07` | PM · Design · Engineering |
| `02` | `02_SDD.md` | Runtime architecture, algorithms, business rules, concurrency, storage, failure & security design | References `03`, `06`, `09`, `10` | Engineering · QA |
| `03` | `03_scope_matrix.md` | Exhaustive feature, menu, screen, setting, shortcut, job, and platform/role branch registry | `03_scope/features.json` | All (Single Foreign Key) |
| `04` | `04_reproduction_env.md` | Pinned commit/tag, official release SHA-256 & REA audit, OS/deps, synthetic seeds, test doubles, licensing | `04_environment/release_audit.json`, `04_environment/LICENSING.md` | Engineering · QA · Legal |
| `05` | `05_ui_reference.md` | Multi-state screenshots (normal, empty, loading, error, disabled/modal), capture conditions, step sequence | `05_ui/screens.json`, `05_ui/screenshots/*.png` | Design · Frontend · QA |
| `06` | `06_behavior_evidence.md` | Observed inputs, state transitions, API responses, event ordering, DB persistence, restart/recovery, limitations | `06_evidence/ledger.jsonl` | Engineering · QA (Oracle Input) |
| `07` | `07_parity_tests.md` | Executable differential test suite reading `06`, runbook, OS branches, visual tolerances, pass/fail/unverified table | `07_tests/verify_parity.py`, `07_tests/verify_visual.py`, `07_tests/parity_report.json` | QA · Reimplementation Agent |
| `08` | `08_implementation_blueprint.md` | Clean-room repo tree, module boundaries, public interfaces, dependency DAG, source → module → test map | — | Engineering · Reimplementation Agent |
| `09` | `09_contracts.md` | Human guide to machine-readable API, event, IPC, and DB contracts with input/output/error examples | `09_contracts/openapi.json`, `09_contracts/*.schema.json`, `09_contracts/schema.sql` | Backend · Frontend · QA |
| `10` | `10_execution_and_state.md` | End-to-end call sequences (UI → handler → storage → update) and normal/error/cancel/retry/recovery state machines (structure-only Mermaid) | — | Engineering |
| `11` | `11_ui_implementation.md` | Screen/component hierarchy, state variants, live computed measurements + source CSS tokens, responsive & asset rules linked to `05` | `11_ui/tokens.json` | Design · Frontend |
| `12` | `12_implementation_sequence.md` | Prerequisite/parallel tracks, first end-to-end vertical slice scope, per-milestone `07` parity pass gates | — | Tech Lead · Reimplementation Agent |

## Conditional `N/A` Policy
If a deliverable genuinely does not apply (for example, `05` and `11` on a pure non-TUI CLI library, or SQL migrations on a stateless tool), keep the numbered markdown file with:
1. Exact reason the deliverable is `N/A` backed by `[REF: ...]`.
2. Conditions under which re-verification would become required (e.g., if a TUI or persistent config is added).

## Dual-Audience Review Views (Optional `scripts/render_review.py`)
- **PM & Design Review Bundle**: Combines `01` PRD + `03` scope summary + `05` visual screenshot gallery + `11` design tokens + SVG user flows.
- **Dev & QA Parity Bundle**: Combines `02` SDD + `04` release REA audit + `06` observed ledger + `07` parity test verdict table + `09` contracts + `10` state diagrams + `08`/`12` implementation plan.
