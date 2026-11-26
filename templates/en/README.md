# English Deliverable Templates (`01`–`12`)

When `goal.json.output_language == "en"`, author narrative sections in English while keeping all machine identifiers verbatim:

- Feature IDs: `F-001`, `F-002`, ...
- Evidence IDs: `EV-001`, `EV-002`, ...
- Screenshot IDs: `SCR-001`, `SCR-002`, ...
- Parity Test IDs: `TC-001`, `TC-002`, ...
- Source Citations: `[REF: relative/path.ext:start-end]`
- Evidence Status Enum: `observed` | `code-verified` | `inferred` | `assumed` | `unverified`
- Mandatory Audit Footer Heading: `## Sources Read`
- Structure-Only Mermaid Diagrams: no `style ... fill:`, `classDef` colors, `stroke:#`, or `color:#`

See `examples/01-pocketbase-v0.40.6/` for a live-verified 12-artifact reference bundle.
