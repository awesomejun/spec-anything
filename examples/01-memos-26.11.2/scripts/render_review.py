#!/usr/bin/env python3
"""Safe static HTML review bundle renderer for spec-anything.

Absorbs the human-readable review rendering concept from WindowHyun/Reverse_Spec_and_PRD
while enforcing strict security hygiene:
- Zero external scripts or network font loads
- Explicit rejection of file:// URL references inside Markdown inputs
- Inline CSS + inline SVG summary diagram + relative links to 01-12 docs & 05 PNGs
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

FILE_SCHEME_RE = re.compile(r"file://", re.IGNORECASE)


def assert_safe_text(text: str, label: str) -> None:
    if FILE_SCHEME_RE.search(text):
        raise ValueError(f"Blocked forbidden file:// reference inside {label}")


def render_html(bundle_dir: Path) -> str:
    rea = json.loads((bundle_dir / "06_evidence/rea_distribution_summary_v1.0.0.json").read_text(encoding="utf-8"))
    smap = json.loads((bundle_dir / ".spec-anything/source-map.json").read_text(encoding="utf-8"))
    ver = json.loads((bundle_dir / "07_tests/verification_results_v1.0.0.json").read_text(encoding="utf-8"))
    ui = json.loads((bundle_dir / "06_evidence/ui_measurements_v1.0.0.json").read_text(encoding="utf-8"))

    # Check 01..12 markdown files for forbidden file:// URL embeds before rendering metadata
    doc_links = []
    for p in sorted(bundle_dir.glob("[0-1][0-9]_*.md")):
        raw = p.read_text(encoding="utf-8")
        assert_safe_text(raw, p.name)
        first_h1 = next((ln.lstrip("# ").strip() for ln in raw.splitlines() if ln.startswith("# ")), p.name)
        doc_links.append((p.name, first_h1, p.stat().st_size))

    cases_rows = []
    for c in ver.get("cases", []):
        badge = "pass" if c["status"] == "PASS" else "fail"
        cases_rows.append(
            f"<tr><td><code>{html.escape(c['case_id'])}</code></td>"
            f"<td><code>{html.escape(c['feature_id'])}</code></td>"
            f"<td><code>{html.escape(c['evidence_id'])}</code></td>"
            f"<td>{html.escape(c['category'])}</td>"
            f"<td><span class='badge {badge}'>{html.escape(c['status'])}</span></td></tr>"
        )

    ui_cards = []
    for rec in ui:
        ui_cards.append(
            f"<figure class='shot'><img src='05_screenshots/{html.escape(rec['filename'])}' alt='{html.escape(rec['ui_id'])}' loading='lazy'/>"
            f"<figcaption><strong>{html.escape(rec['ui_id'])}</strong> ({html.escape(rec['feature_id'])}) · {html.escape(rec['state'])} · {html.escape(rec['viewport'])}</figcaption></figure>"
        )

    docs_rows = "".join(
        f"<tr><td><code>{html.escape(name)}</code></td><td>{html.escape(title)}</td><td>{sz:,} B</td></tr>"
        for name, title, sz in doc_links
    )

    stats = smap.get("stats", {})
    rel_info = rea["artifacts"]["release_archive"]
    bin_info = rea["artifacts"]["extracted_binary"]

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>spec-anything Review Bundle — usememos/memos 26.11.2</title>
<style>
  :root {{ --bg:#0f172a; --card:#1e293b; --fg:#e2e8f0; --muted:#94a3b8; --accent:#38bdf8; --ok:#22c55e; --bad:#ef4444; --bd:#334155; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--fg); line-height:1.55; padding:28px; }}
  .wrap {{ max-width:1180px; margin:0 auto; }}
  h1 {{ margin:0 0 8px; font-size:26px; color:#f8fafc; }}
  h2 {{ margin:28px 0 12px; font-size:18px; border-left:4px solid var(--accent); padding-left:10px; }}
  .sub {{ color:var(--muted); margin-bottom:20px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; margin:16px 0; }}
  .kpi {{ background:var(--card); border:1px solid var(--bd); border-radius:10px; padding:14px; }}
  .kpi .v {{ font-size:24px; font-weight:700; color:var(--accent); }}
  .kpi .k {{ font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:0.04em; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card); border-radius:10px; overflow:hidden; font-size:13px; }}
  th, td {{ padding:9px 12px; border-bottom:1px solid var(--bd); text-align:left; }}
  th {{ background:#0b1220; color:#cbd5e1; }}
  code {{ background:#0b1220; padding:2px 6px; border-radius:4px; font-size:12px; color:#7dd3fc; }}
  .badge {{ padding:2px 8px; border-radius:999px; font-weight:700; font-size:11px; }}
  .badge.pass {{ background:rgba(34,197,94,0.18); color:#4ade80; }}
  .badge.fail {{ background:rgba(239,68,68,0.18); color:#f87171; }}
  .shots {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:14px; }}
  figure.shot {{ margin:0; background:var(--card); border:1px solid var(--bd); border-radius:10px; padding:10px; }}
  figure.shot img {{ width:100%; height:auto; border-radius:6px; border:1px solid var(--bd); display:block; }}
  figure.shot figcaption {{ font-size:12px; color:var(--muted); margin-top:8px; }}
  .svgbox {{ background:var(--card); border:1px solid var(--bd); border-radius:10px; padding:14px; overflow-x:auto; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>spec-anything Review Bundle: usememos/memos 26.11.2 (MIT)</h1>
  <div class="sub">Pinned Commit: <code>00fcd170281a75fc0e95ec4f2f54f43d32fe81bd</code> · Release Binary SHA-256: <code>{html.escape(bin_info['sha256'][:16])}…</code> · Official Checksums Match: <strong>{rel_info['checksums_match']}</strong></div>

  <div class="grid">
    <div class="kpi"><div class="k">Static Units Extracted</div><div class="v">{stats.get('total_units', 0):,}</div></div>
    <div class="kpi"><div class="k">Files Scanned</div><div class="v">{stats.get('files_scanned', 0):,}</div></div>
    <div class="kpi"><div class="k">UI States Captured (05)</div><div class="v">{len(ui)}</div></div>
    <div class="kpi"><div class="k">Parity Tests Passed (07)</div><div class="v">{ver.get('passed', 0)} / {ver.get('total_cases', 0)}</div></div>
  </div>

  <h2>End-to-End Closed-Loop Verification Flow</h2>
  <div class="svgbox">
    <svg viewBox="0 0 960 110" width="100%" height="110" xmlns="http://www.w3.org/2000/svg">
      <defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8"/></marker></defs>
      <rect x="10" y="25" width="165" height="58" rx="8" fill="#0b1220" stroke="#38bdf8"/><text x="92" y="50" fill="#e2e8f0" font-size="12" text-anchor="middle">Pinned Source +</text><text x="92" y="68" fill="#7dd3fc" font-size="11" text-anchor="middle">Official Release (REA)</text>
      <line x1="175" y1="54" x2="205" y2="54" stroke="#38bdf8" stroke-width="2" marker-end="url(#arr)"/>
      <rect x="208" y="25" width="165" height="58" rx="8" fill="#0b1220" stroke="#38bdf8"/><text x="290" y="50" fill="#e2e8f0" font-size="12" text-anchor="middle">Deterministic Extract</text><text x="290" y="68" fill="#7dd3fc" font-size="11" text-anchor="middle">source-map + 03 IDs</text>
      <line x1="373" y1="54" x2="403" y2="54" stroke="#38bdf8" stroke-width="2" marker-end="url(#arr)"/>
      <rect x="406" y="25" width="165" height="58" rx="8" fill="#0b1220" stroke="#38bdf8"/><text x="488" y="50" fill="#e2e8f0" font-size="12" text-anchor="middle">Isolated Execution</text><text x="488" y="68" fill="#7dd3fc" font-size="11" text-anchor="middle">05 UI + 06 JSONL</text>
      <line x1="571" y1="54" x2="601" y2="54" stroke="#38bdf8" stroke-width="2" marker-end="url(#arr)"/>
      <rect x="604" y="25" width="165" height="58" rx="8" fill="#0b1220" stroke="#38bdf8"/><text x="686" y="50" fill="#e2e8f0" font-size="12" text-anchor="middle">09 Contracts +</text><text x="686" y="68" fill="#7dd3fc" font-size="11" text-anchor="middle">07 Parity Harness</text>
      <line x1="769" y1="54" x2="799" y2="54" stroke="#38bdf8" stroke-width="2" marker-end="url(#arr)"/>
      <rect x="802" y="25" width="148" height="58" rx="8" fill="#0b1220" stroke="#22c55e"/><text x="876" y="50" fill="#4ade80" font-size="12" text-anchor="middle">Dual Quality Gate</text><text x="876" y="68" fill="#86efac" font-size="11" text-anchor="middle">100% PASS + SHA256</text>
    </svg>
  </div>

  <h2>01–12 Fixed Specification Bundle</h2>
  <table><thead><tr><th>File</th><th>Document Title</th><th>Size</th></tr></thead><tbody>{docs_rows}</tbody></table>

  <h2>07 Upstream Parity Verification Results (Directly Driven by 06 JSONL)</h2>
  <table><thead><tr><th>Case</th><th>Feature ID</th><th>Evidence ID</th><th>Category</th><th>Status</th></tr></thead><tbody>{''.join(cases_rows)}</tbody></table>

  <h2>05 Observed UI Baseline Captures</h2>
  <div class="shots">{''.join(ui_cards)}</div>
</div>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle-dir", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    bdir = Path(args.bundle_dir).resolve()
    out = Path(args.output)
    out.write_text(render_html(bdir), encoding="utf-8")
    print(f"Rendered safe HTML review bundle: {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
