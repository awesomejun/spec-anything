# Reverse-Engineering & Instrumentation Backends (Craft Anything · Ghidra · IDA · Frida)

`spec-anything` bridges **source-level extraction** with four complementary reverse-engineering and clean-room observation patterns so agents produce verifiable `04`–`06` ground truth before authoring `01`–`03`, `08`–`12`, and `07` parity tests.

> **Strict Clean-Room Boundary**: Every backend below is authorized solely for open-source functional parity, language porting, binary-to-source provenance checks, and interoperability verification. Vulnerability exploitation, DRM/license bypass, anti-cheat evasion, and memory patching are strictly prohibited.

---

## 1. Clean-Room vs. Deep Operating Modes (Inspired by `storytold/craft-anything`)

Confirm the operating mode in **Phase 0** alongside Observation Tier (`T1`/`T2`/`T3`):

| Mode | Allowed Inputs | Prohibited Inputs | Primary Use Case |
| :--- | :--- | :--- | :--- |
| **`clean-room`** *(black-box)* | Public running UI screenshots (multi-viewport), visible DOM/accessibility text, measured `getComputedStyle` CSS tokens, public HTTP/IPC responses, observed storage/file outputs | Reading proprietary/unlicensed source code, decompiling closed binaries, copying brand logos/fonts | Strict clean-room UI/UX & behavior specification from observable surface only |
| **`deep`** *(authorized open-source / owned)* | Everything in `clean-room` **plus** pinned source tree, official release REA audit (`.dmg`/`.app`/npm/ELF/PE), Ghidra/IDA static decompilation, and read-only Frida dynamic tracing | DRM/auth/access-control bypass, exploit development, trademark/copyrighted asset copying | Full-fidelity open-source reimplementation, porting, and build-vs-source drift detection |

### Operational Discipline Adopted
- **Preflight `doctor`**: Run `python3 scripts/doctor.py` before Phase 1 to verify Python, Playwright, OS binary tools, Ghidra, IDA, and Frida readiness.
- **Hypothesis → Finding → Evidence**: Record unresolved discrepancies as explicit hypotheses in `.spec-anything/questions.json`, test them with reproducible inputs, and promote confirmed behaviors into `06_evidence/ledger.jsonl` with explicit `status`, `artifact_sha256`, and `limitations`.
- **Multi-State & Multi-Width Visual Verification**: Capture not only default desktop light mode, but also dark mode, empty/error/active states, and responsive breakpoints whenever the target supports them.

---

## 2. Ghidra Static Decompilation Lane (`NationalSecurityAgency/ghidra` · `pyghidra-mcp` · `rea-ghidra`)

Use when official release binaries (Mach-O, ELF, PE, firmware, stripped native modules) must be cross-checked against pinned source code or when embedded assets/IPC dispatch tables differ from the repository.

- **Headless CLI**: `analyzeHeadless` (Ghidra 12+, JDK 21/25) or `pyghidra` for batch symbol/call-graph/decompilation extraction.
- **MCP Integration**:
  - `clearbluejar/pyghidra-mcp` (`--transport streamable-http`, supports multi-binary project sessions + optional `--gui` sharing)
  - Built-in `rea-ghidra` MCP tools (`list_segments`, `list_procedures`, `list_names`, `find_xrefs_to_name`, `resolve_native_call_targets`, `read_function_instructions`, `inspect_signature`, `inspect_plist`, `list_architectures`, `demangle_swift`, `inspect_asset_catalog`)
- **What Goes Into `04` / `06` / `09` / `10`**:
  - `04_environment/release_audit.json`: Mach-O/ELF slices, code-signing authorities, entitlements, symbol/export counts, Ghidra build/project provenance.
  - `06_evidence/ledger.jsonl`: Confirmed entrypoints, xrefs, IPC command tables, and resolved call targets (`observation_tool: "ghidra-headless"` or `"rea-ghidra-mcp"`).
  - `09_contracts/` & `10_execution_and_state.md`: Exact binary-verified IPC/RPC command names, struct layouts, and state transitions.

---

## 3. IDA Pro / `idalib` Static Analysis Lane (`HexRaysSA/ida-mcp` · `mrexodia/ida-pro-mcp` · `HexRaysSA/ida-sdk`)

Use when IDA Pro (`9.4+` with `idalib` / `idat`) is licensed and installed on the analyst host.

- **Recommended 2026 Headless Pattern**:
  - Official **Hex-Rays IDA MCP** (`HexRaysSA/ida-mcp`, installed via `uvx ida-hcli mcp install`), running headless `idat`/`idalib` workers rather than legacy GUI-only plugins.
  - Community `mrexodia/ida-pro-mcp` (`idalib-mcp`) multi-session worker API: `idb_open(..., mode="prefer_headless")`, `idb_list()`, `decompile(fn, database=id)`, `xrefs_to(sym, database=id)`, `idb_close(id)`.
- **Read-Only MCP Resources**:
  - `ida://idb/metadata` (arch, image base, file hashes) → `04_environment/release_audit.json`
  - `ida://idb/segments` & `ida://idb/entrypoints` → `04` & `02_SDD.md`
  - `ida://types` (recovered structs, enums, calling conventions) → `09_contracts/`
- **Anti-Hallucination Discipline**:
  - Explicitly verify integer signedness, struct field byte offsets, endianness, and pointer/array boundaries in disassembly before translating pseudo-C into `09_contracts/` schemas or `07_tests/` assertions.

---

## 4. Frida Dynamic Instrumentation Lane (`frida/frida` · `frida/frida-tools` · `frida/frida-gum`)

Use **only on owned or authorized open-source targets** when static analysis cannot resolve dynamic dispatch (Objective-C selectors, Swift runtime calls, C/SQLite queries, native-to-WebView IPC payloads, or runtime file/config mutations).

- **Read-Only Observation Profiles (`scripts/frida_trace_bridge.py`)**:
  - `emit-hook --profile sqlite` — Observes `sqlite3_prepare_v2` / `sqlite3_prepare_v3` SQL queries at runtime.
  - `emit-hook --profile objc-storage` — Observes macOS `NSUserDefaults` preference keys written during UI actions.
  - `emit-hook --profile posix-io` — Observes non-system file paths opened by the target process.
  - `emit-hook --profile ipc` — Observes structured JSON-RPC/IPC frames crossing process stdio boundaries.
- **Structured Evidence Ingestion**:
  - `ingest-jsonl`: Converts Frida `send()` JSON event streams directly into schema-valid `06_evidence/ledger.jsonl` records.
  - `ingest-itrace`: Parses `frida-itrace` binary containers (`"ITR2"` / `"ITRC"` 4-byte magic + big-endian `uint32` `MESSAGE` type `1` and `CHUNK` type `2` framing) and records trace counts, dropped buffer warnings (`itrace:lost`), and SHA-256 digests into `06_evidence/ledger.jsonl`.
  - `self-test`: Offline CI verification of `ITR2` parsing and JSON Schema compliance without requiring root privileges or live process attachment.
